@echo off
rem Desinstalador de doble clic (Windows).
rem Elimina las habilidades de todos los asistentes, quita el conector MCP
rem de Claude Desktop y detiene el servicio HTTP local.
rem No borra este repositorio ni Python.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0desinstalar.ps1"

echo.
pause
