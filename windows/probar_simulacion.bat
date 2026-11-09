@echo off
REM Prueba sin escribir en Odoo: muestra lo que haria el puente.
cd /d "%~dp0.."
set DRY_RUN=1
py -3 sync.py || python sync.py
pause
