#!/bin/bash
# Desinstalador (macOS/Linux): elimina todo lo que instalo k-removemark.
# No borra el repositorio clonado ni Python; solo lo copiado a los asistentes.

skills="remove-ai-marks clean-user-facing-text"
dests=(
  "${HOME}/.config/opencode/skills"
  "${HOME}/.claude/skills"
  "${HOME}/.cursor/skills"
  "${HOME}/.gemini/antigravity/skills"
  "${HOME}/.gemini/skills"
  "${HOME}/.copilot/skills"
  "${HOME}/.codex/skills"
)

for dest in "${dests[@]}"; do
  for s in $skills; do
    if [ -d "${dest}/${s}" ]; then
      rm -rf "${dest:?}/${s}"
      echo "eliminado: ${dest}/${s}"
    fi
  done
done

# Quitar el conector MCP de Claude Desktop si existe
CLAUDE_CFG="${HOME}/Library/Application Support/Claude/claude_desktop_config.json"
[ -f "$CLAUDE_CFG" ] || CLAUDE_CFG="${HOME}/.config/Claude/claude_desktop_config.json"
PY_BIN="$(command -v python3 || command -v python || echo python3)"
if [ -f "$CLAUDE_CFG" ]; then
  "$PY_BIN" - "$CLAUDE_CFG" <<'PYEOF'
import json, sys
cfg_path = sys.argv[1]
try:
    with open(cfg_path, encoding="utf-8") as f:
        cfg = json.load(f)
except Exception:
    cfg = {}
removed = False
servers = cfg.get("mcpServers")
if isinstance(servers, dict) and "k-removemark" in servers:
    del servers["k-removemark"]
    removed = True
    with open(cfg_path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
print("conector MCP eliminado de Claude Desktop" if removed else "sin conector MCP que eliminar")
PYEOF
fi

# Detener el servicio HTTP local si esta corriendo
pkill -f "service/scripts/server.py" 2>/dev/null && echo "servicio HTTP detenido" || true

echo ""
echo "Desinstalacion completa. Reinicia tus asistentes de IA."
