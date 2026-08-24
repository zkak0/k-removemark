# OpenCode

OpenCode carga skills desde los directorios `skills/` del proyecto o desde
`~/.config/opencode/skills` (global).

## Instalación

```bash
# desde la raíz del repo (auto-detecta opencode si está configurado)
./install.sh                 # o .\install.ps1 en Windows
# o forzado:
./install.sh --target opencode

# alternativa con el ecosistema skills:
npx skills add <owner>/k-removemark
```

## Uso

Reinicia opencode y pide algo como:

- "quita las marcas de agua de este texto"
- "limpia la metadata AI de esta imagen"
- "ejecuta /remove-ai-marks"

El skill habla con el servicio local HTTP en `http://127.0.0.1:8765`
(arranca con `python service/scripts/server.py`). Si el servicio no está, el skill lo explica.

## Configuración opcional

Los parámetros del detector estadístico se pasan por variables de entorno del
servicio (ver `service/scripts/statistical_detector.py`): `WATERMARKS_STATISTICAL_KEY`,
`WATERMARKS_STATISTICAL_GAMMA`, `WATERMARKS_STATISTICAL_THRESHOLD`.