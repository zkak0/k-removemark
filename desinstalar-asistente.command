#!/bin/bash
# Desinstalador de doble clic (macOS/Linux).
# Elimina las habilidades de todos los asistentes, quita el conector MCP
# de Claude Desktop y detiene el servicio HTTP local.
# No borra este repositorio ni Python.

cd "$(dirname "$0")" || exit 1
chmod +x desinstalar.sh
./desinstalar.sh

echo ""
read -r -p "Presiona Enter para cerrar esta ventana..."
