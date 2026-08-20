# Cómo contribuir a este proyecto

Gracias por ayudar a mantener la skill precisa y los limpiadores fiables. El proyecto es una skill pequeña de Python (`skills/remove-ai-marks/`) más tests — los PRs enfocados se integran más rápido.

## Quién puede hacer qué

| Acción | Quién |
| --- | --- |
| Abrir issues | Cualquiera |
| Sugerir un release | Cualquiera (usa la plantilla **Sugerencia de release**) |
| Abrir pull requests | Cualquiera (haz fork del repo) |
| Aprobar y fusionar pull requests | Solo el mantenedor (`@zkak0`) |

La rama `main` está protegida. Un cambio requiere un pull request, que pase **CI** (`test`), y una revisión aprobatoria del propietario del código antes de fusionar. Solo el mantenedor puede dar esa aprobación. Los pushes directos a `main` están bloqueados para no administradores.

Para sugerir un release sin cambio de código: abre un issue de **Sugerencia de release**.

## Requisitos previos

- **Python 3.10+** (solo stdlib para los scripts de la skill; backends opcionales de reescritura usan HTTP a Ollama / endpoints compatibles con OpenAI)
- Desde la raíz del repo: `python3 -m pytest -q` debe pasar antes de abrir un PR
- Opcional para revisiones manuales de archivos: [`c2patool`](https://github.com/contentauth/c2pa-rs/tree/main/cli), [`exiftool`](https://exiftool.org/) (PDF)

## Estructura del repositorio

| Ruta | Rol |
| --- | --- |
| `skills/remove-ai-marks/SKILL.md` | Entrada de la skill del agente (flujo de trabajo, ética) — cliente remoto sobre HTTP |
| `skills/remove-ai-marks/references/` | Vendors, clases de marcas, matriz, ética |
| `service/scripts/` | Hooks Layer A/B + limpiadores de imagen/contenedores + `server.py` servicio HTTP |
| `service/Dockerfile*` | Imágenes de contenedor (core + backends opcionales) |
| `compose.yaml` | Levantar stack completo en local |
| `tests/` | Suite pytest y fixtures |
| `.github/workflows/ci.yml` | Job CI `test` |
| `.github/workflows/release-images.yml` | Publicación de imágenes GHCR en tags `v*` |

## Capas (dónde cambiar qué)

1. **Layer A (Unicode / controles de formato)** — scripts deterministas bajo `service/scripts/` (`text_unicode.py`, `clean_text.py`, `inspect_text.py`). Preferir tests con fixtures en `tests/fixtures/`.
2. **Layer B (reescritura estadística)** — guía en `SKILL.md` más `rewrite_text.py` opcional (prompt por defecto; ollama / openai-compatible). Sin modelo incluido. Mantener conciencia ética.
3. **Archivos (C2PA / EXIF / XMP / props)** — `image_meta.py` (PNG/JPEG/AVIF/HEIC/...), `container_meta.py` (SVG/PDF/DOCX/ODT/HTML/MD), `av_meta.py` (MP4/MOV/WAV/MP3), `inspect_file.py` / `clean_file.py` unificados. Preservar cuerpo del documento / píxeles / forma de onda; eliminar solo metadatos de procedencia.

## Checklist para un cambio

- [ ] El comportamiento coincide con `SKILL.md` / `references/removal-matrix.md` cuando sea relevante
- [ ] Tests unitarios actualizados o añadidos bajo `tests/`
- [ ] `python3 -m pytest -q` pasa
- [ ] Documentación actualizada (README y/o referencias de la skill) si cambia comportamiento de cara al usuario
- [ ] Sin refactorizaciones ajenas al fix o feature

## Expectativas del PR

- Mantenerse enfocado y seguir el estilo existente (scripts stdlib-first, flags CLI claros)
- No commitear secretos, archivos privados de usuario, o fixtures binarios grandes salvo que sean necesarios y estén redactados
- Respetar `references/ethics.md`: esta herramienta es para contenido que el usuario posee o está autorizado a procesar

## Comunidad

- [Código de Conducta](CODE_OF_CONDUCT.md) — comportamiento esperado en el proyecto
- [Política de seguridad](SECURITY.md) — cómo reportar vulnerabilidades de forma privada
- Plantillas: [Bug report](.github/ISSUE_TEMPLATE/bug_report.md) y [Feature request](.github/ISSUE_TEMPLATE/feature_request.md)

¿Dudas? Abre un issue describiendo el tipo de entrada (texto / imagen / documento) y qué capa falla o falta.