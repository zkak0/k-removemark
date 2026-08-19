# Integraciones / Integrations

Cada carpeta da instrucciones de instalación específicas por agente. La vía
rápida es usar el auto-instalador desde la raíz del repo:

```bash
./install.sh                  # POSIX: detecta tu agente y copia los skills
.\install.ps1                 # Windows (PowerShell 5.1+)
.\install.ps1 -Target cursor  # fuerza un destino concreto
```

O bien, si tu agente soporta el ecosistema skills (agentskills.io):

```bash
npx skills add <owner>/k-removemark        # instala todos los skills del repo
```

| Agente | Cómo instala | Carpeta |
| --- | --- | --- |
| OpenCode | skills en `~/.config/opencode/skills` | `opencode/` |
| Cursor | skills + reglas `alwaysApply` `.mdc` | `cursor/` |
| Claude Code | plugin marketplace `plugin.json` | `claude-code/` |
| Antigravity 2.0 | plugin `plugin.json` + skills | `antigravity/` |
| VS Code Copilot / Cline / Roo | skills en `.copilot/` / `.claude/skills` | `vscode/` |
| Gemini CLI | skills en `~/.gemini/skills` | `gemini-cli/` |

Todos los instaladores solo copian archivos: sin red, sin node, sin python.
El servicio HTTP local (`service/scripts/server.py`) se arranca aparte con
`make serve` o `docker compose up -d`; los skills lo detectan vía `/capabilities`.

## Regla de oro

Nunca prometas una plataforma sin comprobar `/capabilities` del servicio. La
instalación del skill y el servicio son dos pasos independientes.