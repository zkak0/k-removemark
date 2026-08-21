# Política de Seguridad

**No abras un issue público para problemas de seguridad.** Repórtalos de forma privada con el botón "Report a vulnerability" de la pestaña Security del repositorio.

Incluye: descripción del problema, impacto y pasos para reproducirlo si es seguro compartirlos.

Lo más importante a reportar en este proyecto:

- Fuga de contenido de archivos de usuario en logs o mensajes de error
- Escritura de archivos fuera de las rutas de salida previstas
- Inyección de comandos al invocar herramientas opcionales (`c2patool`, `exiftool`)

La investigación de buena fe que siga esta política no será perseguida legalmente.
