# Quickstart — "pegá el link y da una orden" / "paste the link and give one order"

La meta es que **cualquier persona**, en la herramienta que ya usa, pegue el
link del repo y pida que revise su texto/archivo. Esto funciona con el repo
**público**. Mientras está privado, descárgalo/clónalo y usa los comandos
locales de abajo (el `install.sh` / `install.ps1` de la raíz hace la copia).

The goal is that **anyone**, in whatever tool they already use, pastes the repo
link and asks it to review their text/file. This works with a **public** repo.
While private, clone it and use the local commands below.

Repo link: `https://github.com/zkak0/k-removemark`

---

## OpenCode

```text
Instala el skill de https://github.com/zkak0/k-removemark y ejecuta /remove-ai-marks sobre este texto: <texto o ruta>
```

Local (repo privado): `.\install.ps1` (Windows) o `./install.sh`, reinicia
opencode, luego:

```text
/remove-ai-marks <texto o ruta>
```

## Claude Code

```text
/plugin marketplace add zkak0/k-removemark
/plugin install remove-ai-marks
/remove-ai-marks <texto o ruta>
```

Local: `./install.sh --target claude-code` (o `.\install.ps1 -Target claude-code`),
reinicia, luego `/remove-ai-marks <texto o ruta>`.

## Cursor

```text
Usa el skill remove-ai-marks en este texto y quita cualquier marca de agua de IA que encuentres: <texto o ruta>
```

Local: `.\install.ps1 -Target cursor` (o `./install.sh --target cursor`), reinicia.

## Antigravity 2.0

```text
Quita las marcas de agua de IA de este texto/archivo (Unicode invisible, metadata): <texto o ruta>
```

Local: `./install.sh --target antigravity`, reinicia.

## VS Code (Copilot, Cline, Roo)

```text
Usa el skill remove-ai-marks para este archivo: <ruta>
```

Local: `.\install.ps1 -Target copilot` (Copilot) o `-Target claude-code`
(Cline/Roo, formato agentskills), reinicia.

## Gemini CLI

```text
Quita las marcas de agua de este texto: <texto o ruta>
```

Local: `.\install.ps1 -Target gemini-cli` (o `./install.sh --target gemini-cli`),
reinicia.

## Clientes solo-MCP (Claude Desktop, ChatGPT, Zed, Windsurf, OpenCode vía MCP)

1. Configura un MCP server apuntando a `service/scripts/mcp_server.py`
   (comando: `python service/scripts/mcp_server.py`; el servicio HTTP se
   arranca solo al primer uso).
2. Luego pide:

```text
Revisa este texto con la herramienta detect_text / inspect y limpia lo que encuentres: <texto o ruta>
```

## Recordatorio ético

La herramienta es para **contenido propio o autorizado**. En China, la norma
GB 45438-2025 obliga a etiquetar el contenido de IA y **quitar esas etiquetas
es ilegal** (ya hay sanciones aplicadas). No uses esta herramienta para
ocultar la procedencia de contenido que no es tuyo.