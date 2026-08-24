---
name: remove-ai-marks
description: >
  Elimina marcas de procedencia de IA multi-vendor: Unicode invisible (Capa A),
  marcas estadísticas de texto por reescritura (Capa B, siempre ofrecer) y
  metadatos C2PA/EXIF/XMP/contenedor en PNG/JPEG/WebP/SVG/PDF/DOCX/ODT/HTML/MD.
  Cubre Claude, Gemini/SynthID, OpenAI y marcas de LLMs abiertos. Usar cuando el
  usuario pida quitar marcas de agua, eliminar C2PA/Credenciales de Contenido,
  limpiar metadatos de IA, quitar Unicode invisible, anti-detectar salida de IA
  o ejecutar /remove-ai-marks.
---

# Eliminar marcas de IA

Higiene anti-detección multi-vendor para **texto** (Unicode + reescritura estadística) y **archivos** (C2PA / metadatos de IA en contenedores comunes).

## Arranque (primera vez que se usa este repositorio)

Si llegaste a este repo porque un usuario pegó el enlace y la habilidad no está instalada permanentemente:

1. Clona el repo: `git clone https://github.com/zkak0/k-removemark`
2. Verifica Python 3.10+ (`python3 --version`). Si falta, instálalo y avisa al usuario lo que estás haciendo:
   - Windows: `winget install Python.Python.3.12` → usa `python`
   - macOS: `brew install python3` → usa `python3`
   - Linux (Debian/Ubuntu): `sudo apt-get install -y python3` → usa `python3`
3. Ejecuta el instalador desde la carpeta clonada (`.\install.ps1` en Windows, `./install.sh` en macOS/Linux). Copia estas habilidades en todos los asistentes detectados.
4. Confirma al usuario que ya puede pedir limpiezas en lenguaje natural sin volver a usar el enlace.

Leer si es necesario:

- `references/mark-classes.md` — Unicode / sampling / C2PA / contenedores
- `references/vendor-notes.md` — Claude, Gemini/SynthID, OpenAI, LLMs abiertos
- `references/removal-matrix.md` — qué capa usar en cada caso
- `references/ethics.md` — uso previsto
- `references/how-claude-marks.md` — detalle específico de Anthropic
- `references/markdiffusion.md` — harness opcional MarkDiffusion para imágenes

Esta habilidad es un **cliente ligero**. Todo el motor de limpieza determinista corre en un servicio HTTP separado (la carpeta `service/` de este repo), así que el agente no necesita Python, venvs ni herramientas de limpieza. Llama al servicio con `curl`; nunca ejecutes scripts de limpieza directamente.

## Acceso al servicio

La URL base viene de `WATERMARKS_SERVICE_URL`, por defecto `http://127.0.0.1:8765`:

```bash
WM="${WATERMARKS_SERVICE_URL:-http://127.0.0.1:8765}"
```

El servicio se arranca bajo demanda por el servidor MCP, o manualmente desde la carpeta del repo. **Siempre verifica primero** y nunca recurras a limpieza local:

```bash
curl -sf "$WM/health"
# {"ok": true, "version": "..."}
```

Si `/health` falla, **ofrece arrancar el servicio tú mismo** antes de rendirte (pregunta al usuario, luego ejecuta):

```bash
# desde la carpeta del repo:
python service/scripts/server.py
```

Luego vuelve a verificar `curl -sf "$WM/health"` hasta que devuelva `{"ok": true, ...}` (unos segundos). Solo si no es posible arrancarlo (no hay checkout, no hay Docker) te detienes y explicas cómo hacerlo.

Instalación única: el repo trae `install.sh` / `install.ps1` que copian estas habilidades en tu agente (`opencode`, `claude-code`, `cursor`, `antigravity`, `gemini-cli`, `copilot`, `codex`), o `npx skills add <owner>/k-removemark`. Los clientes solo-MCP (Claude Desktop, ChatGPT, Zed, Windsurf) pueden ejecutar `service/scripts/mcp_server.py` en su lugar — arranca el servicio bajo demanda.

Si `WATERMARKS_SERVER_API_KEY` está configurado en el servicio, el mismo valor debe estar en el entorno de esta habilidad, y cada petición necesita `-H "Authorization: Bearer $WATERMARKS_SERVER_API_KEY"`.

### Capacidades

```bash
curl -s "$WM/capabilities"
```

Informa qué herramientas opcionales hay server-side (`c2patool`, `exiftool`, `qpdf`), los evaluadores presentes (`scorers.stylometry`, `scorers.synthid`, `scorers.synthid_http`), los detectores de marcas de texto (`text_detectors.markllm`, `text_detectors.claude-text`), el soporte multimedia (`media.audio_dsp`, `media.video_scrub`), y qué backends pesados están configurados (`pixel_backends.ctrlregen`, `pixel_backends.diffusion`, `harnesses.markllm`). **Basá tu recomendación en esto**: solo habla de eliminación de píxeles / evaluación SynthID / detección de vendor cuando el servicio reporte el backend presente.

## API HTTP (curl)

Los cuerpos son JSON con el archivo en **base64**. El agente decodifica el campo `cleaned` y escribe la salida él mismo.

| Método | Ruta | Cuerpo | Devuelve |
| --- | --- | --- | --- |
| GET | `/health` | — | `{"ok": true, "version": ...}` |
| GET | `/capabilities` | — | herramientas / backends opcionales presentes |
| GET | `/openapi.json` | — | spec OpenAPI 3.0.3 dinámica |
| POST | `/inspect` | `{"file": "<base64>", "name": "notas.md"}` | `{"ok", "kind", "suspicious", "report"}` |
| POST | `/detect` | `{"file": "<base64>", "name": "notas.txt"}` | `{"ok", "kind", "detections": [...]}` |
| POST | `/clean` | `{"file": "<base64>", "name": "notas.md", "options": {...}}` | `{"ok", "kind", "cleaned": "<base64>", "report"}` |

`/clean` y `/inspect` enrutan por la extensión del archivo `name` más los bytes; formatos no reconocidos devuelven `kind: "unknown"` (`/inspect`) o 400 (`/clean`). Al escribir un archivo temporal para texto pegado, usá una extensión conocida (`.txt` / `.md`) en el campo `name`.

Las opciones que acepta `/clean`: `nfkc`, `aggressive_homoglyphs` (texto), `keep_non_ai_metadata`, `strip_all_metadata`, `remove_pixel` (`ctrlregen` | `diffusion`) (imágenes), `also_layer_a_text` (contenedores), `detect_before` / `detect_after` (texto e imágenes: ejecuta detección de marcas en la entrada y en la salida limpia, incluido en el reporte).

**Inspeccioná primero** (decidí, no adivines):

```bash
curl -s -X POST "$WM/inspect" -H 'Content-Type: application/json' \
  -d "{\"file\": \"$(base64 < notas.md | tr -d '\n')\", \"name\": \"notas.md\"}"
```

**Limpiar** (texto / imagen / contenedor se detectan automáticamente por nombre + bytes):

```bash
curl -s -X POST "$WM/clean" -H 'Content-Type: application/json' \
  -d "{\"file\": \"$(base64 < notas.md | tr -d '\n')\", \"name\": \"notas.md\"}"
```

Decodificá el `cleaned` base64 a la salida (`*.cleaned.*` por defecto a menos que el usuario pida sobrescribir) y resumí el `report` con honestidad.

(En agentes de Windows, generá base64 con `[Convert]::ToBase64String([IO.File]::ReadAllBytes("notas.md"))`.)

## Ética

Para **contenido propio** o autorizado (privacidad, higiene, investigación). No comercialices resultados como "prueba de redacción humana". Si el usuario quiere fraude académico o evasión ilegal de divulgación, advertí usando `references/ethics.md` y solo realizá la limpieza técnica sobre contenido que le pertenece.

## Flujo de trabajo

### 1. Clasificar la entrada

| Entrada | Rutear |
| --- | --- |
| Texto pegado / portapapeles | archivo temporal → `/inspect` luego `/clean` (texto) |
| `.txt` / código | texto Capa A (+ formateador para código) |
| `.md` / `.html` | limpieza de contenedor (frontmatter/meta) + Capa A |
| `.png` / `.jpg` / `.jpeg` / `.webp` / `.avif` / `.heic` / `.bmp` / `.gif` / `.tiff` | strip de metadatos de imagen (+ scrub opcional de marcas visibles con `image_watermark.py`) |
| `.wav` / `.mp3` / `.m4a` | strip de metadatos de audio (+ `dsp: true` para WAV PCM 16-bit) |
| `.mp4` / `.mov` / `.m4v` | strip de metadatos de video (+ scrub de marcas visibles frame a frame si ffmpeg está presente) |
| `.svg` / `.pdf` / `.docx` / `.epub` / `.odt` | strip de metadatos de contenedor |
| Directorio / sitio web | auditoría agregada por las CLIs del servicio (ver abajo) |

El servicio enruta por extensión de archivo primero, luego por bytes mágicos, así que generalmente solo envías el archivo.

### 2. Inspeccionar primero

```bash
curl -s -X POST "$WM/inspect" -H 'Content-Type: application/json' \
  -d "{\"file\": \"$(base64 < ruta | tr -d '\n')\", \"name\": \"$(basename ruta)\"}"
```

Mostrá un resumen corto (puntos de código sospechosos; flags C2PA/IA; etiquetas de confianza `confirmed` / `probable` / `informational` / `likely_false_positive`).

La detección opcional de píxeles (puntuación SynthID) y la eliminación de píxeles (CtrlRegen / DiffusionPurification) y los harnesses MarkDiffusion/MarkLLM son backends pesados externos. Corren en contenedores opcionales del servicio o checkouts del host — consultá `/capabilities` antes de prometerlos, y nunca fingas que un detector local es un detector oficial del fabricante.

### 2b. Detección de marcas antes/después (cuando esté configurado)

Cuando `/capabilities` reporte un detector (`text_detectors.markllm`) o un evaluador de imágenes (`scorers.synthid_http` / `scorers.synthid`), medí el resultado detectando antes y después de la limpieza:

```bash
curl -s -X POST "$WM/detect" -H 'Content-Type: application/json' \
  -d '{"file": "'"$(base64 -w0 notas.txt)"'", "name": "notas.txt"}'
```

O incluí la detección en la limpieza: `/clean` con `{"options": {"detect_before": true, "detect_after": true}}` devuelve `text_detectors.before/after` (texto) o `synthid_before/synthid_after` (imágenes) en el reporte. MarkLLM es solo para la misma configuración de investigación; el detector de Claude no es público aún. (Google retiró su detector SynthID-text de la API en agosto de 2026 — ver `references/vendor-notes.md`.)

### 3. Limpieza determinista (siempre para entradas compatibles)

**Cualquier archivo soportado (unificado):**

```bash
curl -s -X POST "$WM/clean" -H 'Content-Type: application/json' \
  -d "{\"file\": \"$(base64 < ENTRADA | tr -d '\n')\", \"name\": \"$(basename ENTRADA)\"}"
```

Decodificá `cleaned` → `SALIDA` (`*.cleaned.*` a menos que el usuario pidió sobrescribir). Re-inspeccioná el resultado cuando el riesgo residual importe.

PDF necesita `exiftool` + `qpdf` server-side para un strip real; el reporte nota un resultado degradado (mejor esfuerzo) cuando falta alguno — consultá `/capabilities`.

**Imágenes — eliminación opcional de píxeles:** solo cuando `capabilities.pixel_backends` diga que el backend está presente:

```bash
curl -s -X POST "$WM/clean" -H 'Content-Type: application/json' \
  -d "{\"file\": \"$(base64 < foto.png | tr -d '\n')\", \"name\": \"foto.png\", \
       \"options\": {\"remove_pixel\": \"ctrlregen\"}}"
```

### 4. Capa B — siempre ofrecer reescritura (prosa)

Después de la Capa A, **siempre proponé** una pasada de reducción de marcas estadísticas para contenido en lenguaje natural. No la saltees silenciosamente.

El servicio **no** tiene un modelo de reescritura — **vos** sos el modelo de reescritura. Ejecutá los prompts de abajo con un modelo **≠ origen sospechado** (texto de Claude → no Claude; Gemini → no Gemini; etc.). Preferí modelos abiertos locales y evitá cualquier vendor con marcas conocidas.

Receta multipasada:

1. Limpieza Capa A (vía `/clean`)
2. Parafraseo (default) — elección de palabras + reordenamiento de sintaxis: cambiá el orden de cláusulas, conectores, palabras de transición y límites de oraciones; reemplazá palabras de contenido y función donde el significado lo permita; preservá hechos, números, nombres, IDs técnicos
3. Pasada fuerte opcional — `humanizar` (prosa natural humana), back-translate, o esquema estructural → regeneración
4. Capa A otra vez sobre el resultado (`/clean`)
5. Reportá el riesgo residual honestamente (texto corto/muy predecible = menor; prosa larga de alta entropía = mayor)

**Archivos de código:** Preferí formateador (`prettier`, `black`, `gofmt`, …) + Capa A. Ofrecé una pasada de reescritura de código (comentarios/docstrings/texto de literales + renombrado de identificadores locales) con OK explícito del usuario, ya que renombrar identificadores es adyacente al comportamiento.

### Auditorías agregadas (directorios / sitios web)

Ejecutá la CLI de auditoría desde un checkout local del repo:

```bash
python3 service/scripts/audit_dir.py DIR --json
```

Códigos de salida de auditoría (igual en `--json`, `--sarif` y salida humana): `0` sin hallazgos accionables, `1` hallazgos accionables, `2` error de uso/negativa, `3` **escaneo parcial** (algunos archivos o URLs no se pudieron escanear — tratar como inconcluso; la auditoría fue incompleta, no limpia).

### 5. Reporte

Siempre declará:

- Qué eliminó la Capa A / limpieza de contenedor de forma **verificable** (conteos, acciones) — del `report`.
- Qué hizo la Capa B (mejor esfuerzo estadístico; **no puede reclamar "indetectable" oficial**). El riesgo residual es menor para texto corto/muy predecible y mayor para prosa larga de alta entropía.
- Fuera de alcance: SynthID de píxeles/audio/video (**basado en modelo**), **C2PA soft binding**, detectores de clave secreta, backdoors de entrenamiento. Las marcas visibles/metadatos de audio/video SÍ están en alcance (strip de metadatos siempre; DSP de audio en WAV; scrub de video requiere ffmpeg).
- Soft binding / marcas multimedia pueden seguir siendo detectables por herramientas del fabricante después del strip.
- Preferí escribir `*.cleaned.*` a menos que el usuario pidió sobrescribir.
- Ética: contenido propio / sin teatro de cumplimiento.

## Limitaciones

- La Capa A **no** elimina marcas de sampling de tokens.
- La Capa B no se puede verificar en oro sin detectores/keys del fabricante. Los harnesses opcionales MarkLLM/MarkDiffusion verifican una configuración específica antes/después, pero solo para la misma configuración y no son un oráculo de detección oficial.
- El strip de PDF es mejor esfuerzo sin `exiftool`, e incompleto sin `qpdf` server-side.
- Las marcas de **imagen** en dominio de píxeles se pueden eliminar opcionalmente con el backend CtrlRegen (`remove_pixel: ctrlregen`) o DiffusionPurification de MarkDiffusion (`remove_pixel: diffusion`); ambos son pesados, alteran la imagen y necesitan el backend presente (`/capabilities`).
- **Audio** (`.wav/.mp3/.m4a`) y **video** (`.mp4/.mov`): `/clean` siempre hace strip de metadatos (stdlib). DSP de audio (`dsp: true`) phase-randomiza PCM WAV 16-bit y aplica notch al tono dominante — mejor esfuerzo, no es una derrota del vendor; los formatos comprimidos son solo metadatos. El scrub de marcas visibles frame a frame en video (`scrub_visible: true`, `corner` opcional) requiere ffmpeg y es mejor esfuerzo.
- Las marcas SynthID basadas en modelo en píxeles/audio/video están fuera del alcance del camino por defecto (documentados opt-ins GPU).
- El evaluador reverse-SynthID es externo, mejor esfuerzo y bajo licencia Research no comercial; no es un detector oficial de Google. Google retiró su detector oficial SynthID-text de la API en agosto de 2026, así que solo queda el harness MarkLLM de misma configuración. La API de detección de Claude fue anunciada pero aún no es pública — el detector `claude-text` reporta no disponible hasta que salga.
- **C2PA soft binding** (marca de contenido que se re-enlaza a un manifiesto remoto después del strip de metadatos) está fuera de alcance — el strip de C2PA hard-bound no la limpia.
- Las marcas basadas en datos/backdoor (frases trigger) están fuera de alcance.

## Servicio no accesible?

Si `$WM/health` falla: decile al usuario que el servicio está caído y cómo arrancarlo (`python service/scripts/server.py` desde el checkout del repo). No intentés limpiar localmente — esta habilidad no contiene código de limpieza.