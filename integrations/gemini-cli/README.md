# Gemini CLI

Gemini CLI carga skills desde `~/.gemini/skills/` (formato agentskills.io:
`SKILL.md` con frontmatter `name` + `description`).

## Instalación

```bash
./install.sh --target gemini-cli      # POSIX
.\install.ps1 -Target gemini-cli      # Windows
```

## Uso

Reinicia `gemini`. Pide p. ej.:

- "quita las marcas de agua de este texto"
- "limpia la metadata AI de esta imagen (C2PA/EXIF)"

El skill usa el servicio local HTTP (`make serve`, puerto 8765) y detecta sus
capacidades vía `/capabilities`. Nunca afirma verificación de vendor sin clave.

## Limitaciones honestas

- Texto: Layer A (Unicode invisible) y metadata siempre; Layer B rewrite es
  best-effort y se ofrece antes de tocar el contenido.
- Imagen: metadata y marcas visibles (reverse-alpha, esquina) en CPU; DWT-DCT
  y SynthID requieren backends opt-in.
- Audio/vídeo: metadata siempre; DSP audio solo WAV PCM 16-bit; vídeo visible
  solo con ffmpeg instalado.