# Publicar el repo (modo público) / Publishing checklist

Cuando el propietario decida hacer el repo público, seguir este checklist.
Solo eso queda pendiente; todo lo demás (release, CI, GHCR, docs) ya está.

---

## 1. Antes de publicar (seguridad)

1. **Revocar el token clásico** `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`
   en https://github.com/settings/tokens (Tokens → Classic → *k-removemark*).
2. Crear un token nuevo **solo para lo que se necesite en el momento**:
   - Publicar → `repo` (o un token fine-grained limitado).
   - Marcar release → `repo`.
   No usar el token clásico de todos-los-scopes de nuevo.
3. Repasar `git log` y que **no haya secretos** en el historial (la clave
   estadística `WATERMARKS_STATISTICAL_KEY` es un secreto del operador, nunca
   del repo).

## 2. Hacer público

1. GitHub web → Settings → General → *Danger Zone* → **Change visibility** → Public.
   (O API: `PATCH /repos/zkak0/k-removemark {"visibility":"public"}`.)
2. Confirmar que **CI corre en verde** sobre `main` (3 OS + lint + verify
   harness).
3. **CodeQL se activa solo** al hacerlo público (el job está condicionado a
   `github.event.repository.visibility == 'public'`). Verificar que el run de
   CodeQL aparece y queda verde (puede tardar en el primer run).

## 3. Después de publicar

1. **Release**: confirmar que `v0.1.0` sigue publicado y apuntando al commit
   correcto. Si hace falta mover el tag: borrar ref remota, recrearla en `main`,
   y **recrear la release** (borrar + crear, porque el tag es anotado).
2. **Badges**: los del README (CI + release) se renderizan solos al ser público.
3. **Topics del repo** (Settings → Topics): `ai-watermark`, `ai-text-detection`,
   `llm-watermark`, `c2pa`, `privacy-tools`, `cli`, `python`. (En privado no se
   ven; añadirlos ahora.)
4. **skills.sh listing**: registrar el repo en skills.sh / el ecosistema de
   skills de agentes para que `npx skills add zkak0/k-removemark` resuelva
   oficialmente. Ver `package.json` (ya tiene `skills` con las entradas).
5. **MCP público**: cualquiera podrá apuntar `mcp_server.py` desde su propio
   checkout o clon; documentar en `integrations/QUICKSTART.md` ya hecho.
6. **GHCR**: los paquetes `ghcr.io/zkak0/k-removemark*` ya están vinculados al
   repo (OCI labels). Al hacer público, la visibilidad de los paquetes pasa a
   pública automáticamente; verificar en Packages.

## 4. Verificación final

- `git ls-remote https://github.com/zkak0/k-removemark` devuelve `main` y `v0.1.0`.
- Actions: CI + release-images verdes; CodeQL verde.
- `npx skills add zkak0/k-removemark` funciona en una máquina limpia.
- Badges del README renderizan.
- Repo público con topics y descripción en español.