#!/bin/bash
# Instalador de doble clic (macOS).
# Configura k-removemark en todos los asistentes de IA detectados
# (OpenCode, Claude Code, Cursor, Antigravity, Gemini CLI, Copilot, Codex),
# instala Python si falta y configura Claude Desktop automaticamente.

cd "$(dirname "$0")" || exit 1
chmod +x install.sh
./install.sh --target auto

echo ""
echo "============================================"
echo " Instalacion finalizada."
echo " Cierra y vuelve a abrir tu asistente de IA"
echo " y ya podras pedirle: \"quita las marcas de agua\"."
echo "============================================"
read -r -p "Presiona Enter para cerrar esta ventana..."
