# Notas de fabricantes (público / a nivel de clase)

Esta habilidad apunta a **clases de marcas**, no a detectores privados reverse-engineerados. Los detalles abajo son de docs públicos y la literatura de investigación. Los algoritmos pueden cambiar.

## Modelo de dos capas de la industria (contexto)

La guía de productos y normativa suele enmarcar la divulgación de IA como:

1. **Credenciales de Contenido C2PA** — metadatos firmados, vinculación dura (fáciles de strip; lo que esta habilidad elimina).
2. **Marca de agua imperceptible** (clase SynthID) — sobrevive a strip/subida; incluye **soft binding** que puede re-attachar un manifiesto C2PA remoto.

Ver: [Guía C2PA y SynthID — Institute of AI PM](https://www.institutepm.com/knowledge-hub/ai-content-provenance-watermarking) (enmarque SB 942 / EU AI Act Art. 50). Este proyecto solo implementa el lado **vinculación dura / Unicode / reescritura** de ese stack.

## Anthropic / Claude

- **Marcas de texto incrustadas** a nivel de modelo (imperceptibles; sobreviven a copy-paste). La descripción pública coincide con la clase **sampling estadístico de tokens**, no solo Unicode.
- **Credenciales de Contenido C2PA** en archivos compatibles (ej. PNG, JPEG, SVG).
- Modelos lanzados el **2026-08-02** o después: marcado al lanzamiento; modelos anteriores en transición; **mundial**.
- APIs de detección para terceros: descritas como próximamente.
- Advertencias: marca ⇒ puede haber sido procesado por Claude; sin marca ≠ solo humano; corrección/pep puede estampar material humano.

**Mapeo de la habilidad:** Capa A (higiene Unicode) + Capa B (reescritura) + strip de metadatos de contenedor/imagen C2PA.

Fuente: [Cómo Claude marca el contenido generado por IA](https://support.claude.com/en/articles/16266773-how-claude-marks-ai-generated-content).

## Google Gemini / SynthID-Text

- Paper Nature 2024: *Scalable watermarking for identifying large language model outputs* (SynthID-Text).
- **Watermarking generativo**: modifica el sampling de next-token (Tournament sampling); la detección usa una función de puntuación + key; no necesita el LLM en tiempo de detección.
- El paper también taxonomiza:
  - **Edit-based** (Unicode / reglas de sinónimos) → nuestra Capa A (+ Capa B para sinónimos)
  - **Data-driven / backdoor** (frases trigger) → **fuera de alcance**
  - **Generativo** (sampling) → Capa B mejor esfuerzo
- Produccionizado en sistemas Gemini-scale; el código de investigación abierto existe, pero **las keys de producción no son públicas** — esta habilidad **no** incluye un detector SynthID.
- **Retirado de la API (agosto 2026):** Google confirmó que la API Generative Language ya no watermarks la salida de texto y DETECT_TEXT_WATERMARK es rechazado en modelos (3.x) actuales; "el watermarking nativo de texto no está planeado por el momento" ([Foro AI de Google](https://discuss.ai.google.dev/t/does-gemini-api-text-output-carry-synthid-watermarking-gemini-2-5-flash-lite-gemini-3-1-flash-lite-eu-ai-act-art-50-2/177241/2)). El detector gemini-synthid-text fue **eliminado** por esta razón; un detector de fabricante puede re-agregarse (ej. via Vertex AI) si Google expone detección otra vez.
- Harness de verificación externo opcional: [`THU-BPM/MarkLLM`](https://github.com/THU-BPM/MarkLLM) (Apache-2.0) reimplementa SynthID-Text entre otros esquemas con keys configurables; conectado como `detect_text_watermark.py` / `rewrite_text.py --markllm-scheme`. Solo misma configuración — verifica una marca que generaste bajo una config conocida, no la key de producción de Google.
- Marcas de producción frontera actuales son **token por token** (restricción de streaming); los métodos robustos a nivel de párrafo (SemStamp / PostMark) no están desplegados aún, lo que mantiene efectivos los ataques de clase paráfrasis hoy.
- Referencia externa opcional: [`aloshdenny/reverse-SynthID`](https://github.com/aloshdenny/reverse-SynthID) provee un evaluador de dominio de píxeles reverse-engineerado. **No está incluido** aquí, es mejor esfuerzo y está bajo licencia Research no comercial; no es el detector oficial de Google.
- Eliminación opcional de píxeles: [`mertizci/noai-watermark`](https://github.com/mertizci/noai-watermark)'s perfil CtrlRegen está conectado via `clean_image.py --remove-pixel ctrlregen` / `clean_ctrlregen.py`. **No está incluido** (sin archivo LICENSE → todos los derechos reservados), y ningún detector local certifica el resultado; la verificación oficial de Google es la autoridad final. Para marcas Tree-Ring-class, el harness opcional MarkDiffusion (`markdiffusion_harness.py`, Apache-2.0) agrega un detector same-scheme y un motor de eliminación por regeneración ciega (`--remove-pixel diffusion`) — ver `references/markdiffusion.md`.

**Mapeo de la habilidad:** mismos ataques de reescritura Capa B (paráfrasis / back-translate / estructural) usados en la literatura contra marcas de sampling.

## OpenAI / ChatGPT

- La procedencia pública suele surgir como **etiquetas**, **C2PA / Credenciales de Contenido** en algunas exportaciones multimedia, y divulgación en UI de producto — no una especificación pública de marca de texto sampling comparable a SynthID-Text.
- Tratar **metadatos de archivo / C2PA** como en alcance cuando esté presente; tratar cualquier marca de texto no publicada como la misma clase estadística → solo Capa B, mejor esfuerzo.
- No inventar claims de algoritmos.

**Mapeo de la habilidad:** strip de metadatos de contenedor/imagen + Capa A/B en texto.

## Open-weight / open-LLM (estilo Kirchenbauer)

- Sesgo clásico de sampling green-list / red-list (Kirchenbauer et al.) y variantes.
- Detectable con la **key** y el tokenizer; la eliminación aún depende de paráfrasis fuerte o regeneración.
- Harness externo opcional: `MarkLLM` (`detect_text_watermark.py --scheme kgw`) reproduce detección KGW bajo una config que controlás, para experimentos controlados antes/después.

**Mapeo de la habilidad:** Capa B multipasada; preferir reescritura con una familia de **modelo diferente** cuando sea posible.

## Regla de higiene cross-vendor

| Origen sospechado | Backend de reescritura preferido |
| --- | --- |
| Claude | No-Claude (Ollama local, otra API) |
| Gemini | No-Gemini |
| OpenAI | No-OpenAI |
| Desconocido | Open-weight local si está disponible |

Preferí backends open-weight locales y evitá cualquier fabricante con marcas conocidas, no solo el origen sospechado. Luego re-ejecutá Capa A sobre el texto reescrito.