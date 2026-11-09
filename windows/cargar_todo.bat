@echo off
REM Carga UNA VEZ todo el historial de marcas de ZLink (ultimos 45 dias) en Odoo, en modo real.
cd /d "%~dp0.."
if not exist logs mkdir logs
set DRY_RUN=0
set LOOKBACK_DAYS=45
set SYNC_FROM=2026-01-01
echo Cargando historial de ZLink en Odoo (modo real)...
py -3 sync.py > logs\carga_historial.log 2>&1 || python sync.py > logs\carga_historial.log 2>&1
type logs\carga_historial.log
echo.
echo Copia guardada en logs\carga_historial.log
pause
