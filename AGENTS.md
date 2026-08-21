# AGENTS.md

Instrucciones para agentes de IA que trabajen con este repositorio.

## Qué es

k-removemark elimina marcas de procedencia de IA (Unicode invisible, marcas estadísticas de texto, metadatos C2PA/EXIF/XMP) de texto, código, imágenes, vídeo, audio y documentos. Todo local, en CPU, sin subir nada a internet.

## Protocolo de arranque (cuando un usuario pega este enlace)

1. Clona el repo: `git clone https://github.com/zkak0/k-removemark`
2. Verifica Python 3.10+ (`python3 --version`). Si falta, instálalo avisando al usuario:
   - Windows: `winget install Python.Python.3.12`
   - macOS: `brew install python3`
   - Linux: `sudo apt-get install -y python3`
3. Ejecuta el instalador desde la carpeta clonada:
   - Windows: `.\install.ps1` · macOS/Linux: `./install.sh`

   Copia las habilidades a todos los asistentes detectados (opencode, claude-code, cursor, antigravity, gemini-cli, copilot, codex) y configura Claude Desktop si existe.
4. Dile al usuario que ya puede pedir limpiezas en lenguaje natural sin volver a usar el enlace.

## Cómo funciona

- Las habilidades viven en `skills/remove-ai-marks/` y `skills/clean-user-facing-text/`.
- El motor es el servicio HTTP local `service/scripts/server.py` (solo librería estándar). Arranca solo al primer uso si se usa el servidor MCP (`service/scripts/mcp_server.py`) o se puede iniciar manual: `python service/scripts/server.py`.
- Limpieza directa sin servicio: `python service/scripts/clean_file.py ARCHIVO -o SALIDA`.

## Reglas para agentes

- Inspecciona antes de limpiar (`inspect_file.py` o `/inspect`). No adivines.
- Reporta con honestidad: separa lo verificado (conteos, metadatos eliminados) de lo mejor esfuerzo (reescritura estadística). Nunca afirmes que un detector del fabricante fue derrotado.
- Opera solo sobre contenido propio o autorizado del usuario.
