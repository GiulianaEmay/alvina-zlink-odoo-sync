# Alviña · Puente ZLink → Odoo Asistencias

Lleva las marcas del asistómetro ZKTeco (plataforma **ZKBio Zlink**) a **Asistencias** de Odoo 19
(grupo-alvina.com). **No toca el servidor de Odoo**: no instala módulos ni requiere reinicios; solo crea
asistencias por la API.

Corre en una **PC de la oficina con Windows**, cada 10 minutos, porque ZLink solo acepta llamadas desde
IPs fijas registradas en su lista blanca (GitHub Actions cambia de IP en cada corrida).

## Cómo funciona
1. Pide un token a la Open API de ZLink con la app propia «Odoo Asistencias Alvina» (permisos solo de lectura).
2. Lee las marcas de los últimos 3 días.
3. Encuentra al empleado en Odoo por **DNI** (también PIN o credencial), ignorando ceros a la izquierda.
4. Une cada entrada con la siguiente marca dentro de 16 h → **el turno noche (7 pm → 6 am) es una sola asistencia**.
   Marcas repetidas en menos de 3 min cuentan como una.
5. Crea la asistencia (modo «Técnico») o completa la salida de una que quedó abierta. Si ya existe, no la duplica.
6. El log lista las marcas de personas sin empleado en Odoo para que RR. HH. corrija el DNI.

## Instalación en la PC (Windows)
1. **IP fija**: en ZLink Open Platform → la app → Security Settings → **IP Whitelist**, registrar la IP pública
   de la oficina (se ve en https://api.ipify.org desde esa PC).
2. **Python**: instalar desde https://www.python.org/downloads/ marcando **"Add python.exe to PATH"**.
3. **Archivos**: en GitHub → **Code → Download ZIP**, descomprimir en `C:\AlvinaZlink` (o donde se prefiera).
4. **Claves**: copiar `config.env.ejemplo` como `config.env` y completar `ZLINK_APP_SECRET` y `ODOO_API_KEY`.
   `config.env` no se sube a GitHub.
5. **Prueba**: doble clic en `windows\probar_simulacion.bat`. Muestra lo que haría sin escribir en Odoo.
6. **Programar**: doble clic en `windows\instalar_tarea.bat` (corre cada 10 min con la sesión iniciada).
7. Cuando la simulación esté bien, cambiar `DRY_RUN=1` a `DRY_RUN=0` en `config.env`.

Resultados de cada corrida: `logs\sync.log`. Para detenerlo: `windows\quitar_tarea.bat`.

## Parámetros opcionales (en config.env)
`LOOKBACK_DAYS` (3), `MAX_SHIFT_HOURS` (16), `DEDUP_MINUTES` (3), `ZLINK_TZ_DEFAULT` (-05:00), `DRY_RUN` (0/1).

## Pruebas
`python -m unittest -v test_sync` (también corren en GitHub Actions con *Run workflow*).
