# Guía no técnica / Non-technical guide

## Español

**¿Qué hace esto?** Quita las "marcas de agua" que las IAs dejan en el
contenido que generan: letras invisibles en el texto, datos de autoría en las
fotos/PDF (C2PA/EXIF) y otras huellas digitales. Sirve para limpiar contenido
**que tú mismo has generado o tienes autorización para procesar**.

**¿Qué necesito?** Un agente de IA (Cursor, Claude Code, OpenCode, Antigravity,
Gemini CLI, VS Code Copilot…). Nada de tarjetas gráficas, nada de descargas
pesadas: funciona en cualquier ordenador.

**Instalación en 3 pasos:**

1. Descarga/abre la carpeta del proyecto.
2. Ejecuta `.\install.ps1` en Windows, o `./install.sh` en Mac/Linux. Se
   detectará tu agente solo.
3. Reinicia tu agente y escribe: *"quita las marcas de agua de este texto"*
   (o imagen, o archivo).

**¿Es 100 % fiable?** No. El programa es honesto:

- *Verificado*: cosas que realmente se pueden medir (caracteres invisibles
  eliminados, metadatos quitados, número de palabras afectadas).
- *Best-effort*: cosas que intenta mejorar pero no puede garantizar (reescritura
  de texto para reducir marcas estadísticas, limpieza de marcas visibles en
  imágenes, audio y vídeo).

Si algo no se puede garantizar, lo dice. Nunca afirma que un detector oficial
de un vendor ha sido derrotado sin pruebas.

**Privacidad:** por defecto todo ocurre en tu ordenador (servicio local
`http://127.0.0.1:8765`). No se envía nada a ninguna nube a menos que lo
configuren explícitamente.

## English

**What does it do?** It removes the watermarks that AI tools leave on generated
content: invisible characters in text, authorship data in photos/PDFs
(C2PA/EXIF), and other digital fingerprints. Use it to clean content **you
generated yourself or are authorized to process**.

**What do I need?** An AI agent (Cursor, Claude Code, OpenCode, Antigravity,
Gemini CLI, VS Code Copilot, …). No GPU, no heavy downloads — it runs on any
computer.

**Install in 3 steps:**

1. Open the project folder.
2. Run `.\install.ps1` on Windows, or `./install.sh` on macOS/Linux. Your agent
   is detected automatically.
3. Restart your agent and type: *"remove the watermarks from this text"* (or
   image, or file).

**Is it 100 % reliable?** No. The tool is honest:

- *Verified*: things that can actually be measured (invisible characters
  removed, metadata stripped, affected word counts).
- *Best-effort*: things it tries to improve but cannot guarantee (text rewrite
  to reduce statistical marks, visible-mark cleaning on images, audio, video).

If something cannot be guaranteed, it says so. It never claims a vendor's
official detector has been beaten without proof.

**Privacy:** by default everything runs on your computer (local service
`http://127.0.0.1:8765`). Nothing is sent to any cloud unless you explicitly
configure it.