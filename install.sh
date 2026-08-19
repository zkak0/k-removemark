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

cat <<'EOF'

Done. Restart your agent. If the local HTTP service is not running, the skill
will tell you how to start it (make serve / docker compose up -d).
EOF