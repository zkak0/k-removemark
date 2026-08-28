@echo off
rem Limpiador del servicio (Windows).
rem Detiene el servicio HTTP local de k-removemark si esta corriendo.
rem No borra habilidades ni configuraciones; solo apaga el servidor de fondo.

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -match 'server\.py' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }; Write-Host 'Servicio HTTP detenido (si estaba corriendo).'"

echo.
pause