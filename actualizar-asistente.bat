@echo off
rem Actualizador de doble clic (Windows).
rem Descarga la ultima version del repositorio y reinstala las habilidades
rem en todos los asistentes detectados. No toca tus archivos ni configuraciones.

cd /d "%~dp0"

echo Actualizando k-removemark...
git pull --ff-only
if errorlevel 1 (
    echo.
    echo No se pudo actualizar automaticamente. Revisa tu conexion o
    echo re-clona el repositorio desde GitHub.
    pause
    exit /b 1
)

echo.
call "%~dp0instalar-asistente.bat"
