#!/usr/bin/env python3
"""Puente ZLink (ZKTeco) -> Odoo 19 Asistencias.

Lee las marcas del asistómetro desde la Open API de ZLink y las registra como
asistencias (hr.attendance) en Odoo usando la API JSON-2. No modifica el
servidor de Odoo: solo crea/actualiza registros.

Reglas:
- Empleado: el código de persona de ZLink (DNI) se compara con el DNI
  (identification_id), PIN o credencial (barcode) del empleado en Odoo,
  ignorando ceros a la izquierda y caracteres no numéricos.
- Emparejamiento: las marcas de cada persona se ordenan; una marca abre la
  jornada y la siguiente la cierra si ocurre dentro de MAX_SHIFT_HOURS. Así el
  turno noche (7 pm -> 6 am) queda como UNA sola asistencia.
- Marcas repetidas en menos de DEDUP_MINUTES se consideran una sola.
- Idempotente: una asistencia se identifica por empleado + hora exacta de
  entrada; volver a correr no duplica. Las creadas por el puente quedan con
  modo de entrada/salida "Técnico" y solo esas se completan automáticamente.
- No requiere campos nuevos ni cambios en el servidor de Odoo.

Variables de entorno (en GitHub: Settings > Secrets and variables > Actions):
  ZLINK_APP_KEY, ZLINK_APP_SECRET            credenciales de la app de ZLink
  ODOO_URL, ODOO_DB, ODOO_API_KEY            Odoo 19 (API JSON-2)
Opcionales:
  LOOKBACK_DAYS (3)  MAX_SHIFT_HOURS (16)  DEDUP_MINUTES (3)  DRY_RUN (0/1)
  ZLINK_TZ_DEFAULT (-05:00)
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

ZLINK_BASE = "https://zlink-open.minervaiot.com/open-apis"


def env(name, default=None, required=False):
    v = os.environ.get(name, default)
    if required and not v:
        sys.exit(f"Falta la variable de entorno {name}")
    return v


LOOKBACK_DAYS = int(env("LOOKBACK_DAYS", "3"))
MAX_SHIFT = timedelta(hours=float(env("MAX_SHIFT_HOURS", "16")))
DEDUP = timedelta(minutes=float(env("DEDUP_MINUTES", "3")))
DRY_RUN = env("DRY_RUN", "0") == "1"
TZ_DEFAULT = env("ZLINK_TZ_DEFAULT", "-05:00")


# ---------------------------------------------------------------- HTTP
def http_json(url, payload, headers):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method="POST",
                                 headers={"Content-Type": "application/json", **headers})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode() or "null")
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise RuntimeError(f"HTTP {e.code} en {url}: {body[:500]}") from None


# ---------------------------------------------------------------- ZLink
class ZLink:
    def __init__(self, key, secret):
        res = http_json(f"{ZLINK_BASE}/authen/v1/tenantToken/internal",
                        {"appKey": key, "appSecret": secret},
                        {"Accept-Language": "en-US"})
        if res.get("code") != "ZCOP0000":
            raise RuntimeError(f"ZLink token: {res.get('code')} {res.get('message')}")
        self.token = res["data"]["tenantToken"]

    def punches(self, start, end):
        out, page = [], 1
        while True:
            res = http_json(f"{ZLINK_BASE}/att/v1/admin/transactions/search",
                            {"pageNumber": page, "pageSize": 100,
                             "startDate": start.isoformat(), "endDate": end.isoformat(),
                             "deviceSn": "", "employeeIds": [], "departmentIds": []},
                            {"Authorization": f"Bearer {self.token}", "Accept-Language": "en-US"})
            if res.get("code") != "ZCOP0000":
                raise RuntimeError(f"ZLink marcas: {res.get('code')} {res.get('message')}")
            data = res.get("data") or {}
            out.extend(data.get("data") or [])
            if page >= (data.get("totalPages") or 1):
                return out
            page += 1


# ---------------------------------------------------------------- Odoo JSON-2
class Odoo:
    def __init__(self, url, db, key):
        self.url, self.db, self.key = url.rstrip("/"), db, key

    def call(self, model, method, **kw):
        return http_json(f"{self.url}/json/2/{model}/{method}", kw,
                         {"Authorization": f"bearer {self.key}", "X-Odoo-Database": self.db})


# ---------------------------------------------------------------- lógica
def norm_code(v):
    digits = re.sub(r"\D", "", str(v or ""))
    return digits.lstrip("0") or None


def parse_punch(p):
    """Devuelve datetime UTC naive de la marca."""
    tz = (p.get("timezone") or TZ_DEFAULT).strip()
    m = re.fullmatch(r"([+-])(\d{1,2}):?(\d{2})", tz) or re.fullmatch(r"([+-])(\d{1,2}):?(\d{2})", TZ_DEFAULT)
    sign = 1 if m.group(1) == "+" else -1
    offset = timedelta(hours=int(m.group(2)), minutes=int(m.group(3))) * sign
    local = datetime.strptime(p["punchTime"], "%Y-%m-%d %H:%M:%S")
    return (local - offset).replace(tzinfo=None)


def pair_punches(punches):
    """punches: lista de (dt_utc, zlink_id) de UNA persona.
    Devuelve (pares, abierta) donde pares = [(in_dt, in_id, out_dt, out_id)]
    y abierta = (dt, id) de la última marca sin cierre, o None. Las marcas
    huérfanas antiguas (sin cierre en MAX_SHIFT) se devuelven en 'huerfanas'."""
    pts = sorted(punches)
    dedup = []
    for dt, pid in pts:
        if dedup and dt - dedup[-1][0] < DEDUP:
            continue
        dedup.append((dt, pid))
    pairs, orphans, open_ = [], [], None
    for dt, pid in dedup:
        if open_ is None:
            open_ = (dt, pid)
        elif dt - open_[0] <= MAX_SHIFT:
            pairs.append((open_[0], open_[1], dt, pid))
            open_ = None
        else:
            orphans.append(open_)
            open_ = (dt, pid)
    return pairs, open_, orphans


def fmt(dt):
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def main():
    zl = ZLink(env("ZLINK_APP_KEY", required=True), env("ZLINK_APP_SECRET", required=True))
    od = Odoo(env("ODOO_URL", required=True), env("ODOO_DB", required=True), env("ODOO_API_KEY", required=True))

    today = date.today()
    raw = zl.punches(today - timedelta(days=LOOKBACK_DAYS), today)
    raw = [p for p in raw if (p.get("status") or "ACTIVE") != "DELETE"]
    print(f"Marcas leídas de ZLink: {len(raw)}")

    emps = od.call("hr.employee", "search_read", domain=[], fields=["name", "identification_id", "pin", "barcode"],
                   context={"active_test": True})
    by_code = {}
    for e in emps:
        for f in ("identification_id", "pin", "barcode"):
            c = norm_code(e.get(f))
            if c:
                by_code.setdefault(c, set()).add(e["id"])

    per_emp, unknown = defaultdict(list), defaultdict(int)
    for p in raw:
        code = norm_code(p.get("employeeCode"))
        ids = by_code.get(code, set())
        if len(ids) != 1:
            unknown[f"{p.get('employeeCode')} {p.get('firstName') or ''}".strip() + (" (varios empleados)" if ids else "")] += 1
            continue
        per_emp[next(iter(ids))].append((parse_punch(p), str(p["id"])))

    created = updated = skipped = 0
    errors = []
    for emp_id, pts in per_emp.items():
        # Si en Odoo quedó una jornada abierta de una corrida anterior (p. ej. entrada
        # 7 pm de un día fuera de la ventana), se incluye para que la salida la cierre.
        open_att = od.call("hr.attendance", "search_read",
                           domain=[["employee_id", "=", emp_id], ["check_out", "=", False], ["in_mode", "=", "technical"]],
                           fields=["check_in"], limit=1)
        if open_att:
            odt = datetime.strptime(open_att[0]["check_in"], "%Y-%m-%d %H:%M:%S")
            if all(abs(dt - odt) >= DEDUP for dt, _ in pts):
                pts.append((odt, "odoo-abierta"))
        pairs, open_, orphans = pair_punches(pts)
        items = [(i, iid, o, oid) for i, iid, o, oid in pairs]
        if open_:
            items.append((open_[0], open_[1], None, None))
        for in_dt, in_id, out_dt, out_id in items:  # noqa
            existing = od.call("hr.attendance", "search_read",
                               domain=[["employee_id", "=", emp_id], ["check_in", "=", fmt(in_dt)]],
                               fields=["id", "check_out", "in_mode"], limit=1)
            vals = {"employee_id": emp_id, "check_in": fmt(in_dt), "in_mode": "technical"}
            if out_dt:
                vals.update(check_out=fmt(out_dt), out_mode="technical")
            try:
                if existing:
                    rec = existing[0]
                    if out_dt and not rec.get("check_out") and rec.get("in_mode") == "technical":
                        if not DRY_RUN:
                            od.call("hr.attendance", "write", ids=[rec["id"]],
                                    vals={"check_out": fmt(out_dt), "out_mode": "technical"})
                        updated += 1
                    else:
                        skipped += 1
                else:
                    if not DRY_RUN:
                        od.call("hr.attendance", "create", vals_list=[vals])
                    created += 1
            except RuntimeError as ex:
                errors.append(f"empleado {emp_id} entrada {fmt(in_dt)} UTC: {ex}")
        for dt, pid in orphans:
            errors.append(f"empleado {emp_id}: marca sin pareja {fmt(dt)} UTC (id {pid})")

    print(f"Asistencias creadas: {created} · actualizadas: {updated} · sin cambios: {skipped}" + (" [SIMULACIÓN]" if DRY_RUN else ""))
    if unknown:
        print("Marcas de personas sin empleado único en Odoo (revisar DNI):")
        for k, n in sorted(unknown.items()):
            print(f"  - {k}: {n} marca(s)")
    if errors:
        print("Avisos:")
        for e in errors:
            print("  - " + e)


if __name__ == "__main__":
    main()
