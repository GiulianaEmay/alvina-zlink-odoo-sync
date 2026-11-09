@echo off
REM Programa el puente para que corra cada 10 minutos en esta PC.
cd /d "%~dp0.."
if not exist config.env (
  echo Falta config.env. Copia config.env.ejemplo como config.env y completa las claves.
  pause
  exit /b 1
)
schtasks /Create /TN "Alvina ZLink a Odoo" /TR "\"%~dp0run_sync.bat\"" /SC MINUTE /MO 10 /F
echo.
echo Listo. La tarea "Alvina ZLink a Odoo" corre cada 10 minutos mientras esta PC este prendida y con la sesion iniciada.
echo Resultados en: %cd%\logs\sync.log
pause
