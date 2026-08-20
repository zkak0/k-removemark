---
name: Informe de error
about: Reporta un defecto en k-removemark (limpieza de texto/imagen, docs de la skill, o scripts)
title: "[bug] "
labels: bug
assignees: ""
---

## Qué ocurrió

Una descripción clara del comportamiento inesperado.

## Qué esperabas

Qué debería haber pasado en su lugar.

## Pasos para reproducir

1.
2.
3.

## Entorno

- SO y arquitectura:
- Versión de Python (`python3 --version`):
- Cómo ejecutas la skill (ruta skill de Grok / symlink / solo scripts):
- Herramientas opcionales presentes (`c2patool`, `exiftool`) y versiones si es relevante:

## Tipo de entrada

- [ ] Texto (pegado / `.txt` / `.md` / otro)
- [ ] Imagen (PNG / JPEG)
- [ ] Ambos / directorio en lote
- Capa involucrada: A (Unicode) / B (guía de reescritura) / Archivos (C2PA/metadatos)

## Diagnóstico

Pega la salida CLI relevante (redacta contenido privado):

```bash
SCRIPTS=service/scripts
python3 "$SCRIPTS/inspect_file.py" ruta
# o:
python3 "$SCRIPTS/inspect_text.py" ruta/o/-
python3 "$SCRIPTS/inspect_image.py" imagen.png
```

## Contexto adicional

Archivos de muestra (si se pueden compartir), capturas de pantalla, o issues relacionados. No pegues secretos, documentos privados, o material que no sea tuyo.