# Plan / Roadmap

> **Read this first.** This file is the source of truth for what exists, what
> is planned, and what is decided. It is bilingual: English primary, Spanish
> summaries (`ES:` marks Spanish guidance).

Estado / Status: **Fases 1–7 completas** — nombre: `k-removemark`, repo objetivo
`zkak0/k-removemark` (privado, con release `v0.1.0` + GHCR images + CI verde).
Pendiente solo: hacer público cuando el propietario decida (checklist en
`docs/PUBLICAR.md`). 576 tests passing.

---

## 1. Objetivo / Goal

Un repositorio **unificado, multi-vendor y multi-plataforma** que elimine marcas
de agua de IA (texto, código, imágenes visibles e invisibles, vídeo, audio y
metadatos) y que cualquier persona pueda instalar en cualquier agente
(Claude Code, Antigravity 2.0, Cursor, OpenCode, VS Code, Gemini CLI…) **con
solo pegar el link del repositorio**, sin configuración extra.

ES: La meta es que un usuario no técnico pegue la URL del repo en el chat de su
agente, diga "instálalo", y la herramienta funcione — en modo simple (limpieza
a demanda) y en modo automático (revisión permanente).

## 2. Decisiones / Decisions (non-negotiable)

1. **Zero-model-default (ZMD).** Instalación por defecto = 100 % CPU, sin GPU,
   sin descargas de modelos. Solo stdlib + numpy/Pillow/PyWavelets. Los
   backends con modelos (CtrlRegen, reverse-SynthID, MarkDiffusion,
   SynthID-Audio) son opt-ins explícitos, nunca parte del default.
2. **Detector propio.** No dependemos de harness pesados (torch) para detección.
   Implementamos KGW y scoring SynthID-Text en stdlib puro. Sin clave de
   producción (Claude/Gemini) la detección keyed es imposible por diseño —
   ofrecemos algoritmo con clave pluggable + señal heurística sin clave.
3. **El código sabe qué buscar.** Detección algorítmica: hashes de tokens,
   z-scores, DWT/DCT, DSP de fase/notch, reverse alpha blending. Sin "cerebro"
   artificial.
4. **Reporte honesto.** Separar *verificado* (conteos, z-scores, acciones de
   metadata) de *best-effort* (rewrite Layer B). Nunca afirmar que un detector
   de vendor está vencido sin prueba pública.
5. **Sin advertencia de fraude académico.** Solo una nota breve de "contenido
   propio / authorized content" (decisión del propietario del repo).
6. **Documentación bilingüe** (EN primary, ES summaries).
7. **Nombre del repo:** `k-removemark` (elegido por el propietario), en GitHub
   como `zkak0/k-removemark`. Hoy **privado** por decisión del propietario;
   todo listo para publicar (ver `docs/PUBLICAR.md`).

## 3. Fases / Phases

### Fase 1 — Base (DONE ✅)

- [x] Base del proyecto establecida (línea base de tests + org files).
- [x] Verificar entorno: git, Python 3.10+ (probado en 3.15.0a8), node/npx.
- [x] `.venv` + pytest instalado.
- [x] Tests del upstream: **520 passed, 6 skipped** (`pytest`).
- [x] `AGENTS.md` raíz (auto-cargado por Antigravity/Codex/Copilot/Cursor).
- [x] `NOTICE` con atribución de licencias (MIT + Apache-2.0).
- [x] `docs/PLAN.md` (este archivo).

### Fase 2 — Detector propio (DONE ✅)

Nuestro detector keyed y señal sin clave, 100 % CPU, sin LLM.

- [x] `service/scripts/statistical_detector.py`
  - KGW green/red-list sobre tokens whitespace (port de `nullorigin` +
    referencia `jwkirchenbauer/lm-watermarking`), stdlib, sin torch.
  - Scoring SynthID-Text Mean (referencia `google-deepmind/synthid-text`) con
    clave pluggable. Weighted Mean/Bayesian necesitan prior entrenado → fuera
    del ZMD, documentado.
  - Salida: z-score, p-valor, green-fraction, `is_watermarked(threshold)`.
  - Embedders KGW/SynthID-Text Mean (hard red-list / tournament sobre word
    bank, sin modelo) para el harness.
- [x] `service/scripts/heuristic_detector.py`
  - Señal sin clave: stylometry (reusa `score_stylometry.py`), burstiness,
    densidad de clichés, repetición de n-gramas.
  - Salida probabilística etiquetada "sospechoso de IA" (`is_suspicious` +
    nivel), `is_watermarked` siempre `False` — nunca "verificado".
- [x] `service/scripts/verify_harness.py`
  - Genera marca sintética (hard red-list sobre whitespace, sin modelo) y mide
    TP/FP/FPR de los detectores + TPR adversarial (ruido de tokens) en CI.
  - Gates: FPR ≤ 0.01, TPR ≥ 0.95, TNR ≥ 0.95. Verificado en local.
  - Falta (Fase 6): integración a `.github/workflows/ci.yml`.
- [x] Tests: `tests/test_statistical_detector.py`, `tests/test_heuristic_detector.py`,
      `tests/test_verify_harness.py` (20 nuevos tests; suite total 540 passed).
- [x] Conectar al servicio HTTP: `text_detectors.py` registra
      `statistical-kgw`, `statistical-synthid-mean`, `heuristic-stylometry`;
      `/capabilities` y `/detect` ya los exponen (fail-soft `_wrap`).
- [x] Seam `claude-text` ya existía (placeholder Anthropic); seam
      `gemini-synthid-text` documentado como re-añadible vía Vertex AI si
      Google vuelve a exponer detección (retirado en la API, ago 2026).

### Fase 3 — Media CPU merge (imagen/vídeo/audio) (DONE ✅)

- [x] `image_watermark.py` (nuevo, stdlib puro + Pillow-opcional): codec PNG
      mínimo propio (zlib), detección de grid brillante (Gemini-sparkle),
      reverse-alpha blending con pattern conocido, scrub de etiqueta de esquina
      (Doubao "AI生成") por interpolación de borde. JPEG/WebP → Pillow si está.
- [x] `clean_audio.py` (nuevo): metadata siempre (`av_meta`); `--dsp` FFT puro
      radix-2 (sin numpy): randomización de fase overlap-add + notch espectral
      del tono dominante sobre WAV PCM 16-bit. Formatos comprimidos: solo
      metadata + nota honesta. Test: energy 440 Hz -99.9 %.
- [x] `clean_video.py` (nuevo): metadata siempre (`av_meta` MP4/MOV);
      `--scrub-visible` frame-wise requiere `ffmpeg` (herramienta opcional) —
      sin ffmpeg degrada a metadata con nota honesta, nunca miente.
- [x] Metadata extra: hints `ai_info`/`aibuildinfo` (TC260 China AIGC) añadidos
      a `image_meta.AI_META_HINTS`.
- [x] Integración HTTP: `/clean` distingue audio/vídeo (`clean_audio`/`clean_video`),
      nuevas opciones `dsp`, `scrub_visible`, `corner`; `/capabilities` reporta
      `media.audio_dsp` y `media.video_scrub` (ffmpeg).
- [x] DWT-DCT (`invisible-watermark`): **opt-in documentado** — necesita numpy +
      PyWavelets, no construibles en este Python 3.15 alpha (sin wheels de C
      ABI); se documenta como dependencia opcional del servicio (requirements).
- [x] Backends GPU (CtrlRegen, reverse-SynthID, MarkDiffusion, SynthID-Audio):
      ya documentados como opt-in; no forman parte del default.
- [x] Tests: `test_image_watermark.py` (7), `test_clean_audio.py` (8),
      `test_clean_video.py` (4); suite total 559 passed.

### Fase 4 — Multi-plataforma (instalación con pegar el link)

- [x] Skills estándar `SKILL.md` (formato agentskills.io) — ya heredado
      (`skills/remove-ai-marks`, `skills/clean-user-facing-text`).
- [x] Publicación `skills.sh`: `package.json` + `skills.json` listan ambos
      skills → `npx skills add <org>/<repo>`.
- [x] `install.sh` (POSIX) y `install.ps1` (PowerShell 5.1+): auto-detectan el
      agente host (`opencode`, `claude-code`, `cursor`, `antigravity`,
      `gemini-cli`, `copilot`, `codex`) y copian los skills; `--target <agente>`
      fuerza uno; `--list`/-List muestra las rutas. Solo copian archivos: sin
      red, sin node, sin python.
- [x] `integrations/` por plataforma: README global + `opencode/`, `cursor/`
      (regla `alwaysApply` `remove-ai-marks.mdc` + README), `claude-code/`
      (`plugin.json` marketplace + README), `antigravity/` (`plugin.json` +
      README), `vscode/` (Copilot/Cline/Roo README), `gemini-cli/` (README).
- [x] `SKILL.md` actualizado: nota de instalación one-line + campos `media.*`
      de `/capabilities`.
- [x] `AGENTS.md` raíz ya documenta el repo (los agentes lo auto-cargan).

### Fase 5 — Modo automático

- [x] `.pre-commit-hooks.yaml`: `k-removemark-check` (fail) y
      `k-removemark-clean` (auto-fix opt-in) vía `check_staged.py` /
      `clean_staged.py`.
- [x] `clipboard_daemon.py` (port de `antiwatermark`, stdlib-only): monitoriza
      el portapapeles (ctypes Windows, `pbpaste`/`pbcopy` macOS, `xclip`/`xsel`
      Linux), limpia Layer A en local sin servicio; monitor-only por defecto,
      `--auto-clean` opt-in, `--once` para tests/cron.
- [x] `watch_folder.py` (nuevo, stdlib-only, sin `watchdog`): polling de una
      carpeta; limpia archivos nuevos/modificados (estado JSON para no
      re-limpiar tras reinicio); copias limpias a `--output` (default, original
      intacto) o `--in-place` opt-in para drop folder dedicada.
- [x] Reglas siempre-activos: Cursor `remove-ai-marks.mdc` (`.mdc`
      `alwaysApply`), Antigravity `GEMINI.md`, instrucción en `AGENTS.md` de
      aplicar Layer A a la salida del agente con informe honesto.
- [x] Tests: `test_clipboard_daemon.py` (6), `test_watch_folder.py` (6).

### Fase 6 — Calidad continua

- [x] `verify_harness.py` en CI: paso `Detector quality gates` en `ci.yml`
      (ubuntu) con umbrales FPR ≤ 0.01 / TPR ≥ 0.95 / TNR ≥ 0.95 y prueba de
      key-mismatch; target `make verify` en el Makefile.
- [x] Niveles de confianza (`confirmed` / `probable` / `informational` /
      `likely_false_positive`) — heredados en `common.py:325` y usados por
      `/inspect`; los detectores keyed añaden z-score como métrica numérica.
- [x] `docs/synthid-text-benchmark.md` heredado se mantiene (bench opt-in
      contra MarkLLM con `MARKLLM_DIR`).

### Fase 7 — Documentación y publicación

- [x] README actualizado: tarjetas de instalación one-line (`./install.sh`,
      `install.ps1`, `npx skills add`), tabla de capas con visible/DSP, resumen
      bilingüe EN/ES y enlace a la guía no técnica.
- [x] `docs/GUIA.md`: guía no técnica bilingüe (3 pasos, límites honestos,
      privacidad local por defecto).
- [x] Revisión final: `SECURITY.md` y `CONTRIBUTING.md` sin referencias al
      repo upstream; `NOTICE` cubre todos los upstreams fusionados; licencias
      MIT/Apache-2.0 preservadas (Apache-2.0 sin licencia comercial
      nunca se redistribuye).
- [x] Nombre del repo: **`k-removemark`** (elegido por el usuario) — aplicado
      a README (título/badges), `package.json`, imágenes Docker
      (`k-removemark*`, `ghcr.io/zkak0/k-removemark`), pre-commit hook IDs
      (`k-removemark-check`/`clean`), compose, Dockerfiles, release workflow y
      comandos de instalación (`npx skills add zkak0/k-removemark`).
- [x] Publicación técnica hecha: repo `zkak0/k-removemark` (privado) con push,
      release `v0.1.0`, GHCR images (`ghcr.io/zkak0/k-removemark` +
      `markllm-*`/`markdiffusion-*`) y CI verde (3 OS + lint + verify harness).
- [ ] Publicación completa (solo cuando el propietario lo decida):
      volver el repo público, activar CodeQL (auto, hoy se salta en privado),
      badges del README, `skills.sh` listing, topics. Ver `docs/PUBLICAR.md`.

### Fase 8 — v0.2 Mejoras (en curso 🔨)

- [x] Fix: variable de API key unificada (`WATERMARKS_SERVER_API_KEY`) en server y skill.
- [x] Fix: Makefile `smoke-markdiffusion` (cerraba mal el `fi`, rompía `bench-synthid-text`).
- [x] Fix: `docs/windows-autostart.md` (nombre de tarea unificado).
- [x] Fix: `clipboard_daemon.py` — backend `xsel` real (antes detectaba xsel y usaba xclip).
- [x] Fix: test inestable de redirect (espera acotada en vez de `sleep(0.2)`).
- [x] Fix: `tests/test_clean_audio.py` escribía un WAV `unused` en la raíz del repo.
- [x] Plugin: `plugin.json` raíz + `.claude-plugin/marketplace.json` (ruta de marketplace de Claude Code).
- [x] Tests: paridad funcional de scripts vendored + coherencia de variable de API key.
- [x] MCP server (`service/scripts/mcp_server.py`) para clientes solo-MCP (Claude Desktop, ChatGPT, Zed, Windsurf).
- [x] Auto-arranque del servicio HTTP desde el skill (si `/health` falla).
- [x] `.opencode/` con `opencode.json` (skills + MCP).
- [x] Plantillas "una orden" por herramienta + README de acceso desde cualquier herramienta.
- [x] Detección de marcas JSON AIGC (norma china GB 45438-2025) + advertencia legal.
- [x] Detector bayesiano SynthID-Text (stdlib) como alternativa al mean-score.
- [x] Esquemas MarkLLM extra expuestos (Unigram + EXP-edit en stdlib; **EWD/SWEET son opt-ins con modelo**, documentados, no-ZMD).
- [x] Heurística multilingüe (español + chino).
- [x] Audio comprimido (MP3/M4A vía ffmpeg, `--transcode`) + detector de ritmo periódico Morse-like (`--scan-pulses`).
- [x] Vídeo: opción `--scrub-audio` (DSP de la pista de audio vía ffmpeg).
- [ ] CI: pip-audit sobre los 5 requirements, pin de torch en ctrlregen, job Python 3.13.
- [ ] Portapapeles reforzado (auto-clean + verificación).

## 4. Matriz de cobertura / Coverage matrix

| Canal / Channel | Default (CPU, sin modelos) | Opt-in (GPU/descarga) |
| --- | --- | --- |
| Texto Unicode (Layer A) | ✅ stdlib (heredado) | — |
| Texto estadístico keyed (KGW/SynthID-text) | ✅ **nuevo** stdlib (KGW, SynthID mean/bayes, Unigram, EXP) | EWD/SWEET: opt-in con modelo (MarkLLM) |
| Texto: señal sin clave | ✅ **nuevo** heurísticas | — |
| Texto: remoción (Layer B) | ✅ prompts + rewrite (heredado) | — |
| Código (comentarios/IDs) | ✅ formatter + prompts (heredado) | — |
| Imagen visible (sparkle/"AI生成") | ✅ stdlib PNG + Pillow-opcional (reverse-alpha, corner scrub) | — |
| Imagen invisible DWT-DCT/TrustMark | 🔜 opt-in documentado (numpy+PyWavelets, no build en este env) | — |
| Imagen SynthID pixel | — | ✅ reverse-SynthID / CtrlRegen |
| Vídeo visible | ✅ metadata + frame scrub (ffmpeg opcional) | — |
| Audio | ✅ metadata + DSP stdlib (WAV 16-bit PCM) | ✅ SynthID-Audio (modelo) |
| C2PA/EXIF/XMP/IPTC/TC260 | ✅ stdlib (heredado) | — |

Vendors: Claude · Gemini/SynthID · OpenAI · xAI Grok · Meta · open-LLM (KGW) ·
Adobe Firefly · Midjourney · Stable Diffusion/FLUX · Microsoft Designer/Copilot ·
Doubao/Kling/Qwen/Jimeng/Tencent/Baidu (China AIGC).

## 5. Límites honestos / Honest limits

- Sin la clave secreta de Claude/Gemini producción, **nadie** puede certificar
  detección de su marca de texto (propiedad de seguridad, no limitación de
  esfuerzo). Ofrecemos: algoritmo keyed con clave pluggable + señal heurística
  sin clave + seam de API oficial cuando exista.
- Stripping de C2PA hard-bound no limpia soft-binding (marca de contenido).
- La remoción de marcas de píxeles (SynthID-class) requiere regeneración
  (GPU). Se documenta como tal.

## 6. Referencias / References

- Atribuciones y licencias de componentes: ver `NOTICE`.
- Skills estándar: https://agentskills.io · CLI: https://skills.sh
- Antigravity skills/plugins: https://antigravity.google/docs/skills/