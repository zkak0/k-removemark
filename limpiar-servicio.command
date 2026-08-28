#!/bin/bash
# Limpiador del servicio (macOS/Linux).
# Detiene el servicio HTTP local de k-removemark si esta corriendo.
# No borra habilidades ni configuraciones; solo apaga el servidor de fondo.

if pkill -f "service/scripts/server.py" 2>/dev/null; then
  echo "Servicio HTTP detenido."
else
  echo "No habia ningun servicio HTTP corriendo."
fi

read -r -p "Presiona Enter para cerrar esta ventana..."