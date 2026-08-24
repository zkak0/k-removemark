# Claude Code (plugin marketplace)

Este `plugin.json` (raíz) expone ambos skills como un plugin instalable:

- `/plugin marketplace add <owner>/k-removemark` — desde la raíz del repo
  (usa `.claude-plugin/marketplace.json`)
- `/plugin install remove-ai-marks` — después de añadir el marketplace

## Instalación manual (sin marketplace)

```bash
# desde la raíz del repo
./install.sh --target claude-code    # POSIX
.\install.ps1 -Target claude-code    # Windows
# copia los skills a ~/.claude/skills/
```

## Requisitos

- El servicio local HTTP (`service/scripts/server.py`) debe estar
  arrancado para que `/remove-ai-marks` funcione de verdad. El skill lo detecta
  vía `/capabilities` y nunca finge.
- Variables de clave estadística: `WATERMARKS_STATISTICAL_KEY` etc. (opcional).

## Comandos del skill

- `/remove-ai-marks`: flujo completo inspección →
  limpieza → informe honesto (verificado vs best-effort).