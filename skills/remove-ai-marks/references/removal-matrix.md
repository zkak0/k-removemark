# Matriz de eliminación

| Objetivo | Método | Script / acción | Efectos secundarios | ¿Verificable hoy? |
| --- | --- | --- | --- | --- |
| Unicode invisible / espacios exóticos / bidi / tags | Strip / normalizar | `inspect_text.py`, `clean_text.py`, `clean_file.py` | Mínimos | Sí (reporte de codepoints) |
| Cadencia estilométrica de IA / burstiness / n-gramas (sin LLM) | Puntuación estadística de varianza y cadencia | `score_stylometry.py`, `inspect_text.py --stylometry`, `audit_dir.py --check-stylometry` | Ninguno (solo detección) | Sí (puntuación calibrada + spans de frases) |
| Marca estadística de texto (SynthID-class / Kirchenbauer) | Paráfrasis multipasada / humanizar / back-translate / estructural | Agente Capa B + `rewrite_text.py` opcional | Deriva de significado/estilo | No sin key/detector del fabricante; **harness MarkLLM** (`detect_text_watermark.py`) verifica una configuración específica antes/después |
| C2PA en PNG/JPEG/WebP/AVIF/HEIC | Eliminar APP11 / PNG `caBX` / RIFF `C2PA` / ISOBMFF `jumb` & `uuid` / exiftool | `clean_image.py` | Pierde metadatos de procedencia | Sí |
| Comentario GIF / extensiones XMP | Eliminar 0xFE / extensiones XMP de aplicación (conservar `NETSCAPE2.0`) | `clean_image.py` | Pierde comentarios/XMP de GIF | Sí (re-inspección) |
| TIFF XMP/EXIF/GPS/IPTC/MakerNote (clásico + BigTIFF) | Eliminar tags IFD, zero payloads, conservar offsets de strip | `clean_image.py` | Pierde metadatos TIFF | Sí (re-inspección) |
| Metadatos trailing en BMP | Truncar bytes trailing no-imagen, corregir campo file-size | `clean_image.py` | Elimina metadatos appendados | Sí (re-inspección) |
| EPUB metadata OPF / XHTML meta / multimedia embebida | Scrub OPF, strip XHTML meta/JSON-LD, limpiar multimedia embebida, Capa A (saltar partes encriptadas) | `clean_file.py` | Pierde metadata del libro; reescribe archivo | Sí (re-inspección) |
| SVG metadata / XMP / data URIs embebidas | Eliminar `<metadata>`, xmpmeta; limpiar data URIs embebidas | `clean_file.py` | Pierde metadata SVG; limpia rasters embebidos | Sí (re-inspección) |
| PDF XMP / info | exiftool `-all=` preferido | `clean_file.py` | Pierde metadata PDF; degradado sin exiftool | Parcial |
| DOCX / XLSX / PPTX props / customXml / multimedia embebida | Reescribir zip OOXML, scrub de text runs, limpiar multimedia/ | `clean_file.py` | Pierde props del doc; limpia rasters embebidos | Sí |
| ODT meta:generator | Scrub `meta.xml` | `clean_file.py` | Pierde tag generator | Sí |
| HTML generator / JSON-LD / data URIs embebidas | Strip tags; limpiar data URIs embebidas | `clean_file.py` | Pierde meta; limpia rasters embebidos | Sí |
| Markdown AI frontmatter keys / data URIs embebidas | Eliminar keys; limpiar data URIs embebidas | `clean_file.py` | Pierde keys YAML; limpia rasters embebidos | Sí |
| Marca de agua de imagen por píxeles (SynthID-media / StegaStamp / Tree-Ring / StableSignature) | Regeneración CtrlRegen (backend externo) | `clean_ctrlregen.py` / `clean_image.py --remove-pixel ctrlregen` | Regenera píxeles; cómputo pesado; deriva de detalle en fuerza alta | No sin detector oficial; puntuación reverse-SynthID es un surrogate local; **harness MarkDiffusion same-scheme** (`markdiffusion_harness.py detect`) verifica una configuración Tree-Ring-class antes/después |
| Marca de agua Tree-Ring-class (imagen) | Purificación por difusión — regeneración ciega (backend MarkDiffusion externo) | `clean_image.py --remove-pixel diffusion` | Regeneración ciega; más deriva que CtrlRegen; cómputo pesado | Same-scheme only via el harness MarkDiffusion (no es oráculo de detector de fabricante) |
| Marcas de agua de audio/video (SynthID-media) | — | Fuera de alcance | — | — |
| C2PA soft binding (enlace en contenido a manifiesto remoto) | — | Fuera de alcance (sobrevive a nuestro strip de metadatos) | — | Solo detector de fabricante |
| Backdoors de modelo basadas en datos | — | Fuera de alcance | — | — |

## Pipeline por defecto

1. **Inspeccionar** (`inspect_file.py` o el inspect_* específico).
2. **Limpieza determinista** — Capa A de texto y/o metadatos de contenedor/imagen; para imágenes, opcionalmente agregar eliminación de píxeles (`--remove-pixel ctrlregen`) después del strip de metadatos.
3. **Siempre ofrecer Capa B** de reescritura para prosa (paráfrasis → opcional pasada fuerte: `humanizar` / back-translate / estructural).
4. Preferir un modelo de reescritura **no-origen, abierto** cuando esté disponible (evitar re-estampar).
5. Capa A otra vez después de la reescritura.
6. Reportar: Capa B es mejor esfuerzo; el riesgo residual permanece.
7. **Verificación opcional:** `rewrite_text.py --markllm-scheme kgw|synthid` ejecuta detección MarkLLM antes/después (harness externo `detect_text_watermark.py`) para mostrar que una configuración específica de esquema se limpia. Solo misma configuración; no es oráculo de detector de fabricante.

## Código vs prosa

- **Prosa / Markdown / cuerpo HTML:** A + B completo.
- **Código:** Capa A + formateador; las marcas estadísticas son débiles; ofrecer reescritura de `código` (comentarios/docstrings/texto de literales + renombrado de identificadores locales) con OK explícito del usuario.

## Fortalezas de Capa B

| Fuerza | Cuándo |
| --- | --- |
| `paraphrase` | Default; elección de palabras + reordenamiento de sintaxis |
| `humanize` | Reordenamiento de tokens "escribir como humano" zero-shot |
| `backtranslate` | Reordenamiento de tokens más fuerte via lenguaje pivote |
| `structural` | El más fuerte; más deriva (esquema → prosa humana) |
| `code` | Comentarios/docstrings/texto de literales + renombrado de identificadores locales |

Las marcas de producción frontera son actualmente **token por token** (restricción de streaming); los métodos robustos a nivel de párrafo (SemStamp / PostMark) no están desplegados aún, así que los ataques de clase paráfrasis siguen siendo efectivos hoy.