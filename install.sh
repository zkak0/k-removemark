#!/usr/bin/env bash
# One-command installer: copy the skills into whichever AI agent you use.
#
#   ./install.sh                 # detect host agent(s) and install
#   ./install.sh --target cursor # force a target: opencode|claude-code|cursor|
#                                #   antigravity|gemini-cli|copilot|codex|all
#   ./install.sh --list          # show the paths it would use
#
# No network, no node, no python needed: it only copies directories.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS=("remove-ai-marks" "clean-user-facing-text")

# Comprobación e instalación silenciosa de Python si falta (macOS / Linux)
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 no está instalado. Intentando instalarlo automáticamente..."
  if command -v brew >/dev/null 2>&1; then
    brew install python3 && echo "Python 3 se ha instalado correctamente." \
      || echo "AVISO: No se pudo instalar Python con brew. Instálalo desde https://python.org"
  elif command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update -y && sudo apt-get install -y python3 && echo "Python 3 instalado correctamente." \
      || echo "AVISO: Instala Python 3 manualmente desde https://python.org"
  else
    echo "AVISO: No se encontró un gestor de paquetes (brew/apt). Instala Python 3 desde https://python.org"
  fi
fi

TARGET=${1:-auto}
while [ $# -gt 0 ]; do
  case "$1" in
    --target) TARGET="$2"; shift 2 ;;
    --list) TARGET="list" ;;
    *) shift ;;
  esac
done

skill_dest() {
  local agent="$1"
  case "$agent" in
    opencode)   echo "${XDG_CONFIG_HOME:-$HOME/.config}/opencode/skills" ;;
    claude-code) echo "${HOME}/.claude/skills" ;;
    cursor)     echo "${HOME}/.cursor/skills" ;;
    antigravity) echo "${HOME}/.gemini/antigravity/skills" ;;
    gemini-cli) echo "${HOME}/.gemini/skills" ;;
    copilot)    echo "${HOME}/.copilot/skills" ;;
    codex)      echo "${HOME}/.codex/skills" ;;
    *) echo "" ;;
  esac
}

detect_agents() {
  local found=()
  [ -d "$HOME/.claude" ] && found+=("claude-code")
  [ -d "$HOME/.cursor" ] && found+=("cursor")
  [ -d "$HOME/.config/opencode" ] && found+=("opencode")
  [ -d "$HOME/.gemini/antigravity" ] && found+=("antigravity")
  [ -d "$HOME/.gemini" ] && found+=("gemini-cli")
  [ -d "$HOME/.copilot" ] && found+=("copilot")
  [ -d "$HOME/.codex" ] && found+=("codex")
  printf '%s\n' "${found[@]:-}"
}

if [ "$TARGET" = "list" ]; then
  for a in opencode claude-code cursor antigravity gemini-cli copilot codex; do
    echo "$a -> $(skill_dest "$a")"
  done
  exit 0
fi

if [ "$TARGET" = "auto" ]; then
  mapfile -t agents < <(detect_agents)
  if [ "${#agents[@]}" -eq 0 ]; then
    echo "No agent config dir found. Run:  ./install.sh --list"
    echo "Then force a target, e.g.:  ./install.sh --target cursor"
    exit 1
  fi
else
  agents=("$TARGET")
fi

if [ "$TARGET" = "all" ]; then
  agents=(opencode claude-code cursor antigravity gemini-cli copilot codex)
fi

installed=0
for agent in "${agents[@]}"; do
  dest="$(skill_dest "$agent")"
  if [ -z "$dest" ]; then
    echo "unknown target: $agent"
    continue
  fi
  mkdir -p "$dest"
  for s in "${SKILLS[@]}"; do
    if [ -d "$ROOT/skills/$s" ]; then
      cp -R "$ROOT/skills/$s" "$dest/"
      echo "installed skill '$s' -> $dest/$s"
      installed=1
    fi
  done
  # Always-on rules the agent auto-loads.
  if [ -d "$ROOT/integrations/cursor" ] && [ "$agent" = "cursor" ]; then
    mkdir -p "$HOME/.cursor/rules"
    cp "$ROOT/integrations/cursor/"*.mdc "$HOME/.cursor/rules/" 2>/dev/null || true
    echo "installed Cursor rules -> ~/.cursor/rules/"
  fi
done

if [ "$installed" = "0" ]; then
  echo "nothing installed (no skills found?)"
  exit 1
fi

# Autoconfiguración automática para Claude Desktop (servidor MCP) si está instalado
CLAUDE_DIR="${HOME}/Library/Application Support/Claude"
CLAUDE_CFG="${CLAUDE_DIR}/claude_desktop_config.json"
MCP_PATH="${ROOT}/service/scripts/mcp_server.py"
PY_BIN="$(command -v python3 || command -v python || echo python3)"
if [ -d "$CLAUDE_DIR" ]; then
  echo ""
  echo "Configurando conector MCP para Claude Desktop de forma automática..."
  mkdir -p "$CLAUDE_DIR"
  if [ ! -f "$CLAUDE_CFG" ]; then
    printf '{}\n' > "$CLAUDE_CFG"
  fi
  "$PY_BIN" - "$CLAUDE_CFG" "$PY_BIN" "$MCP_PATH" <<'PYEOF'
import json, sys
cfg_path, py_bin, mcp_path = sys.argv[1], sys.argv[2], sys.argv[3]
try:
    with open(cfg_path, encoding="utf-8") as f:
        cfg = json.load(f)
except Exception:
    cfg = {}
cfg.setdefault("mcpServers", {})
cfg["mcpServers"]["k-removemark"] = {"command": py_bin, "args": [mcp_path]}
with open(cfg_path, "w", encoding="utf-8") as f:
    json.dump(cfg, f, indent=2, ensure_ascii=False)
print("Conector MCP de Claude Desktop configurado con éxito.")
PYEOF
fi

# Precalentar el servicio HTTP para que la primera llamada sea instantánea
echo ""
echo "Precalentando servicio HTTP local..."
nohup python3 service/scripts/server.py >/dev/null 2>&1 &
sleep 2
if curl -sf http://127.0.0.1:8765/health >/dev/null 2>&1; then
  echo "Servicio HTTP listo en http://127.0.0.1:8765"
else
  echo "El servicio se iniciara bajo demanda."
fi

cat <<'EOF'

Done. Restart your agent. If the local HTTP service is not running, run:
  python3 service/scripts/server.py

(opcional) Para proteger el servicio HTTP local de accesos no autorizados,
podés setear la variable WATERMARKS_SERVER_API_KEY antes de ejecutar install.sh:
  export WATERMARKS_SERVER_API_KEY="tu-clave-secreta"
  ./install.sh
EOF