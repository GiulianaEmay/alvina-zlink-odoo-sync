@echo off
REM Corre una vez el puente ZLink -> Odoo y guarda el resultado en logs\sync.log
cd /d "%~dp0.."
if not exist logs mkdir logs
py -3 sync.py >> logs\sync.log 2>&1 || python sync.py >> logs\sync.log 2>&1
