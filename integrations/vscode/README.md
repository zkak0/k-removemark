# VS Code (Copilot, Cline, Roo Code)

VS Code no tiene un mecanismo único de skills; depende del asistente instalado:

| Asistente | Dónde van los skills |
| --- | --- |
| GitHub Copilot (VS Code) | `~/.copilot/skills/` (Copilot skills experimental) |
| Cline / Roo Code | `~/.claude/skills/` (formato agentskills) |
| Cursor (reglas always-on) | `.mdc` en `~/.cursor/rules/` — los instala el script con `--target cursor` |

Este repo no escribe instrucciones globales de Copilot Chat; las reglas
always-on de Cursor son el único fichero de reglas que instala el script.

## Instalación

```bash
./install.sh --target copilot        # ~/.copilot/skills
./install.sh --target claude-code    # para Cline/Roo (~/.claude/skills)
```

## Uso

- **Copilot skills**: invoca el skill por nombre; el skill arranca/usa el
  servicio local HTTP (`python service/scripts/server.py`) y respeta `/capabilities`.
- **Cline / Roo**: los skills son archivos de texto que el agente lee; pide
  "usa el skill remove-ai-marks para este archivo".
- **Reglas globales**: el script copia `integrations/cursor/remove-ai-marks.mdc`
  a `~/.cursor/rules/`; edita ahí el `alwaysApply` si quieres limpieza automática
  al finalizar contenido del usuario.

## Nota

Los skills solo copian archivos y no requieren extensión ni red. El servicio
local es independiente: `python service/scripts/server.py`.