# Alviña · Puente ZLink → Odoo Asistencias

Lleva las marcas del asistómetro ZKTeco (plataforma **ZKBio Zlink**) a **Asistencias** de Odoo 19
(grupo-alvina.com). Corre solo en GitHub Actions cada 10 minutos. **No toca el servidor de Odoo**:
no instala módulos ni requiere reinicios; solo crea asistencias por la API.

## Cómo funciona
1. Pide un token a la Open API de ZLink con la app propia «Odoo Asistencias Alvina» (permisos solo de lectura).
2. Lee las marcas de los últimos 3 días (`att/v1/admin/transactions/search`).
3. Encuentra al empleado en Odoo por **DNI** (también PIN o credencial), ignorando ceros a la izquierda.
4. Une cada entrada con la siguiente marca dentro de 16 h → **el turno noche (7 pm → 6 am) es una sola asistencia**.
   Marcas repetidas en menos de 3 min cuentan como una.
5. Crea la asistencia (modo «Técnico») o completa la salida de una que quedó abierta. Si ya existe, no la duplica.
6. El registro de cada corrida (pestaña **Actions**) lista las marcas de personas sin empleado en Odoo para que RR. HH. corrija el DNI.

## Configuración (una sola vez)
En el repositorio: **Settings → Secrets and variables → Actions → New repository secret**

| Secret | Valor |
|---|---|
| `ZLINK_APP_KEY` | AppKey de la app en zlink-open.minervaiot.com |
| `ZLINK_APP_SECRET` | AppSecret de la misma app |
| `ODOO_URL` | `https://grupo-alvina.com` |
| `ODOO_DB` | `alvinha_db` |
| `ODOO_API_KEY` | Clave API persistente de un usuario con permiso de administrador de Asistencias y acceso a todas las compañías |

## Primera prueba
**Actions → Sincronizar asistencias ZLink -> Odoo → Run workflow** con *Simulación = 1*: lee y empareja, pero no escribe.
Revisar el registro; si está bien, activar la escritura real: **Settings → Secrets and variables → Actions → pestaña Variables → New repository variable** `DRY_RUN` = `0`.
Hasta entonces la corrida automática de cada 10 minutos solo simula (no escribe en Odoo).

Para pausarlo: **Actions → el workflow → ⋯ → Disable workflow**.

## Parámetros opcionales
`LOOKBACK_DAYS` (3), `MAX_SHIFT_HOURS` (16), `DEDUP_MINUTES` (3), `ZLINK_TZ_DEFAULT` (-05:00), `DRY_RUN` (0/1).

## Pruebas
`python -m unittest -v test_sync`
