# Guía de usuario — k-removemark

Esta guía está escrita para cualquier persona **sin conocimientos técnicos** (abogados, escritores, estudiantes) que quiera limpiar sus documentos de marcas o rastros dejados por inteligencias artificiales (Claude, ChatGPT, Gemini, etc.).

Todo funciona **en tu propia computadora** y **sin internet**: tus documentos nunca se suben a la nube.

---

## ¿Qué hace esta herramienta?

Elimina, de tus textos y archivos:

- **Caracteres invisibles** que delatan que un texto fue escrito por una IA.
- **Metadatos ocultos** en Word, PDF, imágenes, audio y video (información interna como autor, programa usado, huellas digitales C2PA/EXIF).
- **Marcas visibles** en imágenes (cuando es posible).

Al terminar te entrega el archivo limpio y un **informe honesto** con lo que se eliminó realmente.

---

## Instalación (solo se hace una vez)

### Forma 1 — Pega el enlace en tu asistente de IA (la más simple)

1. Abre tu asistente de IA (Claude Code, OpenCode, Cursor, Antigravity, Copilot…).
2. Pega este enlace y dile:
   > *"Usa este repositorio para revisar y limpiar mis documentos: https://github.com/zkak0/k-removemark"*
3. El asistente hace todo solo: si necesita instalar Python te lo dirá y lo hará, luego deja la herramienta instalada para siempre.
4. Cuando te confirme que terminó, listo. No necesitas el enlace nunca más.

### Forma 2 — Doble clic (si prefieres no usar el asistente para instalar)

1. Descarga el proyecto (botón verde **Code → Download ZIP**) y descomprímelo.
2. Haz doble clic según tu sistema:
   - **Windows:** `instalar-asistente.bat`
   - **Mac:** `instalar-asistente.command`
3. Espera el mensaje *"Instalación finalizada"* y cierra y vuelve a abrir tu asistente.

La herramienta queda instalada **para siempre** en todos los asistentes detectados: OpenCode, Claude Code, Cursor, Antigravity, Gemini CLI, VS Code (Copilot/Cline/Roo), Codex y Claude Desktop.

---

## Uso diario (ya no necesitas el enlace del repositorio)

Abre tu asistente de IA de siempre y pídelo en lenguaje natural, por ejemplo:

- *"Revisa si este documento tiene marca de agua de IA"* + arrastra el archivo.
- *"Limpia este escrito para que no tenga rastros de inteligencia artificial"*.
- *"Quita los metadatos y caracteres invisibles de esta imagen"*.

El asistente reconocerá la petición, usará la herramienta instalada y te devolverá:

1. El archivo o texto **limpio**.
2. Un **resumen** de lo que eliminó y de lo que quedó como "mejor esfuerzo".

---

## Preguntas frecuentes

**¿Necesito Docker?**
No. La herramienta básica funciona solo con Python (el instalador lo gestiona).

**¿Mis documentos salen a internet?**
No. Todo el análisis y limpieza ocurre localmente en tu equipo.

**¿Sirve 100% contra todos los detectores?**
Se elimina de forma verificada lo invisible y los metadatos; la reescritura estadística es de *mejor esfuerzo* y el asistente siempre te dirá qué logró y qué no.

---

## Aviso legal importante

Usa esta herramienta solo en **contenido propio o autorizado**. En China, la norma GB 45438-2025 obliga a etiquetar contenido generado por IA: **eliminar esas etiquetas allí es ilegal**. No uses esta herramienta para ocultar procedencia de contenido ajeno ni para evadir obligaciones legales.
