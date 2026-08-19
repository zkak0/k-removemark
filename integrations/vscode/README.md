# VS Code (Copilot, Cline, Roo Code)

VS Code no tiene un mecanismo único de skills; depende del asistente instalado:

| Asistente | Dónde van los skills |
| --- | --- |
| GitHub Copilot (VS Code) | `~/.copilot/skills/` (Copilot skills experimental) |
| Cline / Roo Code | `~/.claude/skills/` (formato agentskills) |
| Copilot Chat | Reglas `.mdc` en `.github/copilot-instructions.md` o `/.cursor/rules` (si usas Cursor) |

## Instalación

```bash
./install.sh --target copilot        # ~/.copilot/skills
./install.sh --target claude-code    # para Cline/Roo (~/.claude/skills)
```

## Uso

- **Copilot skills**: invoca el skill por nombre; el skill arranca/usa el
  servicio local HTTP (`make serve`) y respeta `/capabilities`.
- **Cline / Roo**: los skills son archivos de texto que el agente lee; pide
  "usa el skill remove-ai-marks para este archivo".
- **Reglas globales**: añade `alwaysApply` de `.cursor/rules/remove-ai-marks.mdc`
  si quieres limpieza automática al finalizar contenido del usuario.

## Nota

Los skills solo copian archivos y no requieren extensión ni red. El servicio
local es independiente: `python service/scripts/server.py` (ver `docs/PLAN.md`).