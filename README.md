# k-removemark

**Limpia marcas de agua de IA de tus archivos.** Texto, código, imágenes, vídeo,
audio y metadatos — todo en tu equipo, sin subir nada a internet.

[![CI](https://github.com/zkak0/k-removemark/actions/workflows/ci.yml/badge.svg)](https://github.com/zkak0/k-removemark/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/zkak0/k-removemark)](https://github.com/zkak0/k-removemark/releases)

## ¿Qué hace?

Quita las marcas que dejan los generadores de IA (Claude, Gemini/SynthID, OpenAI,
LLMs abiertos y generadores chinos) para que tu contenido quede limpio y privado:

| Qué elimina | Cómo |
| --- | --- |
| **Texto y código** | Caracteres invisibles, espacios raros y señales ocultas |
| **Imágenes, vídeo y audio** | Marcas visibles y señales por DSP (en CPU) |
| **Archivos** | C2PA, EXIF, XMP y metadatos de procedencia |

Funciona con PDF, DOCX, XLSX, PPTX, EPUB, ODT, HTML, Markdown, PNG, JPEG, WebP,
AVIF, HEIC, BMP, GIF, TIFF, SVG, MP4/MOV, WAV y MP3.

## Beneficios

- **Privacidad:** elimina la "etiqueta" de IA de tu contenido.
- **Para contenido tuyo:** borradores, manuscritos o material que estés
  autorizado a procesar.
- **Sin GPU y sin modelos:** 100 % CPU por defecto. Nada se envía a la nube.
- **Fácil de usar:** un comando para instalarlo en tu agente y listo.
- **Honesto:** te informa qué eliminó de verdad y qué fue un intento
  (mejor esfuerzo).

## Instalación (skill para tu agente)

Funciona con opencode, Claude Code, Cursor, Antigravity, Gemini CLI, Copilot y
Codex.

```bash
# Opción 1 — en un solo comando:
npx skills add zkak0/k-removemark

# Opción 2 — instalador automático:
./install.sh              # macOS / Linux
.\install.ps1             # Windows
```

Después pide a tu agente *"quita las marcas de agua"*.

### Servicio local (opcional)

El servicio es un servidor HTTP ligero en Python 3.10+ (solo librería estándar,
sin dependencias ni Docker):

```bash
make serve                # http://127.0.0.1:8765
```

## Uso rápido

```bash
SCRIPTS=service/scripts

# Inspeccionar un archivo
python3 "$SCRIPTS/inspect_file.py" draft.md

# Limpiar texto, imagen o documento
python3 "$SCRIPTS/clean_file.py" draft.md -o draft.cleaned.md
python3 "$SCRIPTS/clean_file.py" photo.png -o photo.cleaned.png
python3 "$SCRIPTS/clean_file.py" notas.docx -o notas.cleaned.docx
```

## Docker

```bash
make docker-core-build
docker compose up -d      # servicio HTTP en http://127.0.0.1:8765
```

## Nota honesta

k-removemark elimina de forma verificable los metadatos y los caracteres
invisibles. La reescritura de texto marcado estadísticamente es un trabajo de
*mejor esfuerzo*: siempre se informa qué se consiguió y qué no.

Usa esta herramienta solo en contenido que te pertenezca o que tengas permiso
de procesar. Respeta las leyes locales.

## Documentación

- **Guía no técnica (español):** [`docs/GUIA.md`](docs/GUIA.md)
- Skill: [`skills/remove-ai-marks/`](skills/remove-ai-marks/)
- Servicio: [`service/`](service/)

## Pruebas

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest   # o: make test
```

## Historial

### v0.1.0 — primera versión

- Detección estadística de marcas de texto (KGW y SynthID-Text) con clave.
- Limpieza de metadatos y marcas visibles en imágenes, vídeo y audio (CPU).
- Skill de agente e instaladores para opencode, Cursor, Claude Code, etc.
- Modo automático: hooks de pre-commit, portapapeles y carpeta vigilada.
- Informe honesto: separa lo verificado de lo que es mejor esfuerzo.