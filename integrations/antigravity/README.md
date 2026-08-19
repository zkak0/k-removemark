# Antigravity 2.0

Antigravity 2.0 carga skills desde `~/.gemini/antigravity/skills/` y plugins
`plugin.json`. Este plugin expone ambos skills (ruta relativa al repo).

## Instalación

```bash
./install.sh --target antigravity     # POSIX
.\install.ps1 -Target antigravity     # Windows
```

O copia `../../skills/remove-ai-marks` y `../../skills/clean-user-facing-text`
a `~/.gemini/antigravity/skills/` y el `plugin.json` de esta carpeta a
`~/.gemini/antigravity/plugins/remove-ai-marks/`.

## Uso

Reinicia Antigravity y pide "quita las marcas de agua de este texto/imagen" o
"limpia la metadata AI de este archivo". El skill usa el servicio local
(`make serve`) y reporta honestamente qué fue verificado y qué es best-effort.