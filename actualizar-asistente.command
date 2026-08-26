#!/bin/bash
# Actualizador de doble clic (macOS/Linux).
# Descarga la ultima version del repositorio y reinstala las habilidades.

cd "$(dirname "$0")" || exit 1

echo "Actualizando k-removemark..."
if ! git pull --ff-only; then
    echo ""
    echo "No se pudo actualizar automaticamente. Revisa tu conexion o"
    echo "re-clona el repositorio desde GitHub."
    read -r -p "Presiona Enter para cerrar..."
    exit 1
fi

echo ""
chmod +x install.sh
./install.sh --target auto

echo ""
read -r -p "Actualizacion finalizada. Presiona Enter para cerrar..."
