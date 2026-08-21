# k-removemark

**Limpia marcas de agua de IA de tus archivos.** Texto, código, imágenes, vídeo, audio y metadatos — todo en tu equipo, sin subir nada a internet.

## 🤖 Para asistentes de IA (protocolo de arranque)

Si eres un asistente de IA (Claude Code, OpenCode, Cursor, Antigravity, Copilot, Codex…) y un usuario te pegó este enlace, sigue estos pasos en orden:

1. **Clona el repositorio:**
   ```bash
   git clone https://github.com/zkak0/k-removemark
   ```
2. **Verifica Python 3.10+** (`python3 --version` o `python --version`). Si falta, instálalo avisando al usuario lo que vas a hacer:
   - Windows: `winget install Python.Python.3.12`
   - macOS: `brew install python3`
   - Linux (Debian/Ubuntu): `sudo apt-get install -y python3`
3. **Ejecuta el instalador** desde la carpeta clonada. Deja la habilidad instalada permanentemente en todos los asistentes detectados:
   - Windows: `.\install.ps1`
   - macOS / Linux: `./install.sh`
4. **Confirma al usuario** en su idioma: *"Instalación completa. Desde ahora solo pídeme 'revisa si esto tiene marca de agua' o 'limpia este documento', sin volver a usar el enlace."*

Si el usuario no quiere instalación permanente, también puedes ejecutar los scripts directamente desde la carpeta clonada:

```bash
python service/scripts/inspect_file.py documento.docx   # inspeccionar
python service/scripts/clean_file.py documento.docx -o documento.cleaned.docx   # limpiar
```

## ¿Qué hace?

Quita las marcas que dejan los generadores de IA (Claude, Gemini/SynthID, OpenAI, LLMs abiertos y generadores chinos) para que tu contenido quede limpio y privado:

| Qué elimina | Cómo |
| --- | --- |
| **Texto y código** | Caracteres invisibles, espacios raros y señales ocultas |
| **Imágenes, vídeo y audio** | Marcas visibles y señales por DSP (en CPU) |
| **Archivos** | C2PA, EXIF, XMP y metadatos de procedencia |

Funciona con PDF, DOCX, XLSX, PPTX, EPUB, ODT, HTML, Markdown, PNG, JPEG, WebP, AVIF, HEIC, BMP, GIF, TIFF, SVG, MP4/MOV, WAV y MP3.

- **Privacidad:** todo ocurre localmente. Nada se envía a la nube.
- **Sin GPU y sin modelos:** 100 % CPU por defecto.
- **Honesto:** informa qué eliminó de verdad y qué fue un intento (mejor esfuerzo).

## Instalación manual (sin asistente)

1. Descarga o clona este repositorio y descomprímelo.
2. Haz doble clic:
   - Windows: `instalar-asistente.bat`
   - macOS: `instalar-asistente.command`

El instalador configura Python si falta y activa la herramienta en todos tus asistentes a la vez.

## Uso diario

Abre tu asistente de IA y pídelo en lenguaje natural:

- *"Revisa si este documento tiene marca de agua de IA"*
- *"Limpia este escrito para que no tenga rastros de inteligencia artificial"*
- *"Quita los metadatos de esta imagen"*

Guía completa para usuarios no técnicos: [`GUIA_USUARIO.md`](GUIA_USUARIO.md)

## Nota honesta

k-removemark elimina de forma verificable los metadatos y los caracteres invisibles. La reescritura de texto marcado estadísticamente es un trabajo de *mejor esfuerzo*: siempre se informa qué se consiguió y qué no.

Usa esta herramienta solo en contenido que te pertenezca o que tengas permiso de procesar. Respeta las leyes locales.

> **Aviso legal (China):** la norma GB 45438-2025 obliga a etiquetar el contenido generado por IA. Eliminar esas etiquetas es ilegal en China. No uses esta herramienta para evadir obligaciones legales ni para ocultar la procedencia de contenido ajeno.
