# Cursor

Dos mecanismos, ambos `alwaysApply`:

1. **Skills** en `~/.cursor/skills/` (Cursores modernos). El skill
   `remove-ai-marks` activa el flujo completo.
2. **Reglas** en `~/.cursor/rules/*.mdc` (auto-cargadas en cada sesión):
   `remove-ai-marks.mdc` (este repo) aplica la limpieza de marcas sin pedir
   permiso al finalizar contenido del usuario.

## Instalación

```bash
./install.sh --target cursor      # POSIX
.\install.ps1 -Target cursor      # Windows
```

Esto copia los skills a `~/.cursor/skills/` y las reglas `.mdc` a
`~/.cursor/rules/`. Reinicia Cursor.

## Manual

- Skills: mueve `../../skills/remove-ai-marks` a `~/.cursor/skills/`.
- Regla siempre activa: copia `remove-ai-marks.mdc` a `~/.cursor/rules/`
  (los archivos `.mdc` en el proyecto funcionan igual con `alwaysApply: true`).

## Nota

`clean-user-facing-text.mdc` es la regla heredada del skill upstream
`clean-user-facing-text` (higiene de texto natural). Si solo quieres marcas AI,
instala únicamente `remove-ai-marks.mdc`.