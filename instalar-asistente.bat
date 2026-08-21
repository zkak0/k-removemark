@echo off
rem Instalador de doble clic (Windows).
rem Configura k-removemark en todos los asistentes de IA detectados
rem (OpenCode, Claude Code, Cursor, Antigravity, Gemini CLI, Copilot, Codex),
rem instala Python si falta y configura Claude Desktop automaticamente.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" -Target auto

echo.
echo ============================================
echo  Instalacion finalizada.
echo  Cierra y vuelve a abrir tu asistente de IA
echo  y ya podras pedirle: "quita las marcas de agua".
echo ============================================
pause
