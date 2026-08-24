# Clases de marcas

## 1. Texto basado en edición (Unicode / reglas)

Caracteres invisibles o casi invisibles, espacios exóticos, controles bidi, caracteres de etiqueta, tablas de sinónimos.

| Tipos de inspección (Capa A) | Ejemplos |
| --- | --- |
| `zwj_family` | ZWSP, ZWNJ, ZWJ, WJ, BOM |
| `bidi` | LRE/RLO/LRI/… |
| `tag_chars` | U+E0001–U+E007F |
| `variation_selector` | VS1–VS256 |
| `private_use` | U+E000–F8FF, U+F0000–FFFFD, U+100000–10FFFD |
| `space` | NBSP, em space, ideographic space |
| `confusable` | Cirílico / Latino ancho completo (agresivo) |

**Eliminación:** `clean_text.py` / Capa A — determinista, verificable.

Los invisibles estructurales se preservan por defecto para no corromper texto real: glue de emoji (ZWJ/VS después de base emoji), uniones de script (ZWNJ/ZWJ inside scripts complejos como persa o devanagari), secuencias de caracteres de etiqueta de bandera, selectores de variante libre de mismo script (selectores de variación libre mongoles después de una letra mongol, vocales inherentes khmer después de una consonante khmer, rellenos jamo hangul en sílaba parcial), y marcas Cf ortográficas árabes/siríacas. Los mismos caracteres entre ASCII plano siguen siendo carriers y se eliminan. Usá `--strip-emoji-glue` para modo paranoico (elimina todos).

Mapea al paper Nature “edit-based watermarking”.

## 2. Texto generativo / estadístico (sampling de tokens)

Sesgo del sampling de next-token hacia una lista verde pseudo-aleatoria / puntuación (Kirchenbauer, SynthID-Text / Tournament sampling, etc.). La señal vive en la **elección de palabras**, no en metadatos.

**Eliminación:** Capa B reescritura (paráfrasis → back-translate → estructural). Mejor esfuerzo; sin certificado oro sin detector/keys del fabricante.

Mapea al método principal del paper Nature (SynthID-Text).

## 3. Data-driven / backdoor

Modelo entrenado o fine-tuneado para que prompts trigger produzcan comportamiento marcado o identificable.

**Fuera de alcance** para esta habilidad (lado del modelo).

## 4. Metadatos de procedencia de archivos (C2PA / EXIF / XMP / props)

Credenciales de Contenido firmadas y etiquetas de generador de IA en contenedores (vinculadas duro al archivo: JUMBF/APP11, chunks PNG, paquetes XMP, props OOXML, etc.).

Modelo de dos capas de la industria (C2PA + SynthID; ver guía Institute of AI PM en referencias del README):

| Capa | Mecanismo | Sobrevive al strip de metadatos? | Este proyecto |
| --- | --- | --- | --- |
| **C2PA hard-bound** | Manifiesto firmado *dentro* del archivo | No — strip/re-encode lo tumba | **En alcance** — `clean_file` / `clean_image` |
| **Soft binding** | Marca de agua imperceptible *en el contenido* que puede resolver a un manifiesto remoto | Sí (por diseño) | **Fuera de alcance** — señal de píxeles/audio/video |
| **SynthID-class standalone** | Marca de agua de píxeles / waveform / token sin necesitar C2PA | Sí para multimedia; texto es más débil | Multimedia fuera; texto → Capa B mejor esfuerzo |

| Formato | Soportado |
| --- | --- |
| PNG / JPEG / WebP | Strip completo (stdlib + exiftool opcional) |
| SVG | Eliminar bloques metadata/XMP |
| PDF | Preferir exiftool; strip XMP stdlib degradado |
| DOCX / ODT | Scrub de props zip XML / customXml |
| HTML | Meta generator / JSON-LD / data-ai* |
| Markdown | Claves AI en YAML frontmatter |

**Eliminación:** `clean_file.py` / `clean_image.py` — generalmente verificable por re-inspección.

**Reporte honesto:** después de un strip exitoso de C2PA, las marcas soft-bound / SynthID de píxeles (si el generador las usó) pueden seguir siendo detectables por herramientas del fabricante (ej. SynthID Detector, sitios de verificación de Credenciales de Contenido).

## 5. Marcas de agua en dominio de píxeles (imagen, audio, video)

Marcas de agua invisibles en multimedia (ej. SynthID para imágenes/audio/video) y C2PA **soft binding** que vive en la señal, no en los metadatos. **Fuera de alcance.**