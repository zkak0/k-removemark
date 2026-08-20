# Política de Seguridad

## Versiones soportadas

Las correcciones de seguridad se aplican al código más reciente en la rama `main` y al GitHub Release más reciente (cuando existan releases). Tags antiguos no se mantienen.

## Reportar una vulnerabilidad

**No abras un issue público para problemas de seguridad.**

Reporta vulnerabilidades de forma privada mediante **GitHub Security Advisories** — usa el botón "Report a vulnerability" en la pestaña Security del repositorio.

Incluye:

- Una descripción del problema y su impacto
- Pasos para reproducir o prueba de concepto cuando sea seguro compartirla
- Versión o commit afectado si se conoce

## Qué esperar

- Confirmación cuando un mantenedor haya visto el reporte
- Una evaluación inicial de severidad y alcance
- Un cronograma coordinado de corrección y divulgación cuando el reporte sea válido

No tomaremos acciones legales contra investigación de buena fe que siga esta política y evite daño a la privacidad, interrupción del servicio o destrucción de datos.

## Notas de alcance para este proyecto

Este proyecto es una skill de agente local y un conjunto de scripts Python que inspeccionan y limpian archivos de texto e imagen. Los reportes que más importan incluyen:

- Recorrido de ruta (path traversal) o escrituras inseguras fuera de las rutas de salida previstas
- Inyección de comandos al invocar herramientas opcionales (`c2patool`, `exiftool`)
- Fallos del parser o agotamiento de recursos en imágenes/texto diseñados que afecten al host más allá del fallo normal del proceso
- Fuga accidental de contenidos de archivos de usuario en logs, mensajes de error o diagnósticos que viajen con la skill

## Fuera de alcance (salvo que causen impacto de seguridad concreto en este proyecto)

- Eludir marcas de procedencia de IA para fraude, evasión de copyright o incumplimiento ilegal de divulgación (ver skill `references/ethics.md`)
- Problemas solo en herramientas de terceros (`c2patool`, `exiftool`, agentes)
- Ingeniería social contra usuarios individuales

## Divulgación preferentemente privada

Tras publicar una corrección, podemos acreditar a los reportadores que deseen crédito público. No publiques detalles de explotación hasta que haya una release corregida disponible, salvo que acordemos lo contrario.