# Cómo Claude marca el contenido generado por IA

Fuente primaria: [Centro de ayuda de Anthropic](https://support.claude.com/en/articles/16266773-how-claude-marks-ai-generated-content) (Código de prácticas del Artículo 50(2) del EU AI Act).

## Resumen de política

| Tema | Posición de Anthropic |
| --- | --- |
| Modelos nuevos | Marcado para modelos lanzados el **2026-08-02** o después |
| Modelos anteriores | Transición; "en progreso" |
| superficies | API, Claude, Claude Code, Cowork, etiquetas (Tag) |
| Regiones | **Mundial** |
| Detección | Prometida para terceros; docs **próximamente** |

## Mecanismo 1 — marcas de texto incrustadas

- Aplicado a **nivel del modelo** dentro del texto mismo (no en metadatos del archivo).
- Imperceptible; sobrevive a copy-paste; puede sobrevivir a ediciones leves.
- Se debilita con paráfrasis, traducción, edición fuerte, mezcla, texto corto.

**Clase técnica probable** (Anthropic no publicó el algoritmo): marcas estadísticas de **sampling de tokens** (estilo Kirchenbauer / SynthID-Text). Ver `vendor-notes.md` y `mark-classes.md`.

Los scripts de Capa A solo eliminan carriers de **Unicode / homoglifos**. La Capa B (reescritura) ataca las marcas estadísticas.

## Mecanismo 2 — C2PA en archivos

- **Credenciales de Contenido** firmadas en tipos compatibles (ejemplos: `.png`, `.jpg`, `.svg`).
- A prueba de manipulación mientras están presentes; se eliminan con re-encode, scrub de metadatos o muchos pipelines de subida.
- Inspeccionar con `c2patool` cuando esté instalado; eliminar via `clean_image.py` / `clean_file.py` / ExifTool.

## Advertencias (Anthropic)

- Marca detectada ⇒ el contenido **puede haber sido procesado** por Claude — no es prueba de autoría exclusiva.
- Sin marca ≠ origen puramente humano.
- Corrección / traducción / resumen pueden estampar material humano.