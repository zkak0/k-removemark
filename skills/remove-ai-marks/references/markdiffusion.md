# MarkDiffusion (THU-BPM) — referencia

Backend de investigación externo: [`THU-BPM/MarkDiffusion`](https://github.com/THU-BPM/MarkDiffusion) (JMLR; Apache-2.0). Es un toolkit de **watermarking generativo** para modelos de difusión latente — *incrusta* marcas, no las elimina. Este repo lo usa como harness de experimentos controlados y como motor opcional de eliminación por regeneración.

## Qué cubre (solo imágenes)

Nueve algoritmos de imagen en dos categorías:

| Categoría | Algoritmos | Notas |
| --- | --- | --- |
| Basado en patrón | Tree-Ring, Ring-ID, ROBIN, WIND, SFW | Se inyecta un patrón fijo latente/FT en la generación y se invierte para detectar |
| Basado en key | Gaussian-Shading, GaussMarker, PRC, SEAL | Una clave secreta modifica el ruido/latente; la detección necesita la key |

(Los algoritmos de video VideoShield / VideoMark están fuera de alcance para este proyecto.)

## Qué le da al removedor

- **Detector same-scheme** para los algoritmos de arriba via `AutoWatermark.load(...).detect_watermark_in_media()`. Cubre el gap de clase Tree-Ring en `removal-matrix.md`; **no** cubre StegaStamp, StableSignature ni SynthID-media.
- **`DiffusionPurification`** — ataque de regeneración ciega (estilo DiffPure: encode → ruido parcial → reverse-denoise) usable como removedor de marcas de agua de píxeles. Expuesto como `--remove-pixel diffusion` en `clean_image.py`.
- **`NeuralCodecCompression`** — round-trip de codec (compressai). No conectado aquí.

## Limitaciones honestas

1. **Detección es same-scheme y same-model solamente.** La detección por inversión requiere el modelo generador (y para esquemas basados en key, la key). Prueba "esta imagen vino de *este* modelo/config/params" — no certifica que un detector de fabricante falle en una imagen arbitraria. Es la misma advertencia de solo-misma-config que el harness MarkLLM de texto.
2. **`DiffusionPurification` es regeneración ciega.** Reusa el *mismo* pipeline, así que no derrotará una marca de agua robusta a su propio camino de regeneración, y altera el contenido de la imagen (más que CtrlRegen con ControlNet). Fuerza conservadora por defecto (0.3), tratada como motor fallback/comparación, nunca una garantía.
3. **Stack pesado.** torch ≥ 2.4,<2.11 + diffusers + descarga de un modelo Stable Diffusion (~4–10 GB). GPU fuertemente recomendada. Algunos modelos de HF tienen acceso restringido → `HF_TOKEN` (solo env, nunca argv).

## Licencia / higiene

Apache-2.0. Instalado desde PyPI en una versión fijada (`requirements-markdiffusion.txt`) o un checkout editable en un commit fijado (`setup_markdiffusion.sh --checkout`). Nunca incluido en este repo.

## Uso del harness

```bash
SCRIPTS=service/scripts
MD="$HOME/markdiffusion/.venv/bin/python"

"$SCRIPTS/setup_markdiffusion.sh"                     # default pin PyPI
# o: "$SCRIPTS/setup_markdiffusion.sh" --checkout    # clone editable pinado

# 1. marcar una imagen de prueba con un esquema
echo "a red fox in snow" > /tmp/prompt.txt
"$MD" "$SCRIPTS/markdiffusion_harness.py" watermark /tmp/prompt.txt \
  -o /tmp/wm.png -o2 /tmp/plain.png --scheme tr --json

# 2. eliminar (regeneración ciega)
"$MD" "$SCRIPTS/markdiffusion_harness.py" purify /tmp/wm.png \
  -o /tmp/wm.purified.png --purification-strength 0.3 --json

# 3. re-detectar con el MISMO esquema
"$MD" "$SCRIPTS/markdiffusion_harness.py" detect /tmp/wm.purified.png \
  --scheme tr --detector-type l1_distance --json
```

Códigos de salida: 0 ok · 1 error runtime · 2 input inválido · 3 backend no disponible.

## Referencias

- Paper: https://arxiv.org/abs/2509.10569
- Docs: https://markdiffusion.readthedocs.io
- Modelos HF: https://huggingface.co/Generative-Watermark-Toolkits