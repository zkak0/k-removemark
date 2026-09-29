#!/usr/bin/env python3
"""Verificacion de integridad del repo: sin dependencias, sin red, sin modelos.

Comprueba que el toolkit esta completo y coherente consigo mismo:

1. Todos los scripts .py compilan.
2. Todos los manifiestos JSON son validos.
3. Las rutas que declaran los manifiestos existen de verdad.
4. El motor Unicode vendido en la skill ligera es identico byte a byte al
   motor del servicio. Cualquier cambio en uno debe aplicarse al otro.
5. Los scripts que los skills documentan existen.

Salida: 0 si todo correcto, 1 si hay fallos. Pensado para CI, para el
instalador y para el propio mantenedor antes de publicar.
"""

from __future__ import annotations

import ast
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "service" / "scripts"
SKILL_LIGHT = ROOT / "skills" / "clean-user-facing-text" / "scripts"

# El motor de la capa A se vende byte a byte dentro de la skill ligera. Solo
# los envoltorios CLI (clean_text.py, inspect_text.py, common.py) pueden
# divergir del servicio.
VENDORED_ENGINE = SKILL_LIGHT / "text_unicode.py"
SERVICE_ENGINE = SCRIPTS / "text_unicode.py"

MANIFESTS = (
    "plugin.json",
    "package.json",
    "skills.json",
    ".claude-plugin/marketplace.json",
    "integrations/antigravity/plugin.json",
    "integrations/claude-code/plugin.json",
)

# Ficheros que el usuario o un agente necesitan en tiempo de ejecucion.
REQUIRED_FILES = (
    "README.md",
    "AGENTS.md",
    "GUIA_USUARIO.md",
    "install.sh",
    "install.ps1",
    "service/scripts/server.py",
    "service/scripts/mcp_server.py",
    "service/scripts/clean_file.py",
    "service/scripts/inspect_file.py",
    "skills/remove-ai-marks/SKILL.md",
    "skills/clean-user-facing-text/SKILL.md",
    "skills/clean-user-facing-text/scripts/clean_text.py",
    "skills/clean-user-facing-text/scripts/inspect_text.py",
    "skills/clean-user-facing-text/scripts/text_unicode.py",
)


# Contenido que realmente se publica (la lista blanca de .gitignore). El
# resto vive solo en la maquina del mantenedor y no llega al repo.
PUBLISHED_TREES = ("service", "skills", "integrations")
PUBLISHED_FILES = (
    "README.md",
    "AGENTS.md",
    "GUIA_USUARIO.md",
    "plugin.json",
    "package.json",
    "skills.json",
    "install.sh",
    "install.ps1",
    "install.sh",
    "desinstalar.sh",
    "desinstalar.ps1",
)


def _fail(msg: str) -> None:
    print(f"  FALLO {msg}")


def _warn(msg: str) -> None:
    print(f"  AVISO {msg}")


def _textos() -> list[tuple[Path, str, bool]]:
    """Devuelve (ruta, texto, publicado) recorriendo todo el arbol.

    Se escanea tambien lo que no se publica (tests, docs internas) para avisar
    al mantenedor, pero solo lo publicado cuenta como fallo.
    """
    publicados: set[Path] = set()
    for arbol in PUBLISHED_TREES:
        base = ROOT / arbol
        if base.is_dir():
            publicados |= {p.resolve() for p in base.rglob("*") if p.is_file()}
    publicados |= {(ROOT / f).resolve() for f in PUBLISHED_FILES if (ROOT / f).is_file()}

    extensiones = {".py", ".md", ".json", ".ps1", ".sh", ".bat", ".command", ".mdc", ".txt"}
    skip_dirs = {".git", ".venv", "__pycache__", "node_modules", ".pytest_cache"}
    salida: list[tuple[Path, str, bool]] = []
    for p in sorted(ROOT.rglob("*")):
        if not p.is_file() or set(p.relative_to(ROOT).parts) & skip_dirs:
            continue
        if p.suffix.lower() not in extensiones:
            continue
        try:
            texto = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        salida.append((p, texto, p.resolve() in publicados))
    return salida


def check_syntax() -> int:
    print("1. Sintaxis de los scripts Python")
    fallos = 0
    for py in sorted(ROOT.rglob("*.py")):
        partes = set(py.relative_to(ROOT).parts)
        if partes & {".venv", "__pycache__", ".git"}:
            continue
        try:
            ast.parse(py.read_text(encoding="utf-8"), filename=str(py))
        except (SyntaxError, UnicodeDecodeError) as e:
            _fail(f"{py.relative_to(ROOT)}: {e}")
            fallos += 1
    print(f"   {'ok' if not fallos else str(fallos) + ' con errores'}")
    return fallos


def check_json() -> int:
    print("2. Manifiestos JSON")
    fallos = 0
    for rel in MANIFESTS:
        p = ROOT / rel
        if not p.is_file():
            _fail(f"{rel}: no existe")
            fallos += 1
            continue
        try:
            json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            _fail(f"{rel}: {e}")
            fallos += 1
    print(f"   {'ok' if not fallos else str(fallos) + ' con errores'}")
    return fallos


def check_manifest_paths() -> int:
    print("3. Rutas declaradas en los manifiestos")
    fallos = 0
    for rel in ("skills.json", "plugin.json", ".claude-plugin/marketplace.json"):
        p = ROOT / rel
        if not p.is_file():
            continue
        datos = json.loads(p.read_text(encoding="utf-8"))
        candidatos: list[str] = []
        for entrada in datos.get("skills", []):
            if isinstance(entrada, str):
                candidatos.append(entrada)
            elif isinstance(entrada, dict) and "source" in entrada:
                candidatos.append(str(entrada["source"]))
        for fuente in candidatos:
            if not (ROOT / fuente).is_dir():
                _fail(f"{rel} -> {fuente}: no existe")
                fallos += 1
    print(f"   {'ok' if not fallos else str(fallos) + ' con errores'}")
    return fallos


def check_required_files() -> int:
    print("4. Ficheros publicados necesarios")
    fallos = 0
    for rel in REQUIRED_FILES:
        if not (ROOT / rel).is_file():
            _fail(f"{rel}: no existe")
            fallos += 1
    print(f"   {'ok' if not fallos else str(fallos) + ' con errores'}")
    return fallos


def check_vendored_engine() -> int:
    print("5. Motor vendido == motor del servicio (byte a byte)")
    if not SERVICE_ENGINE.is_file() or not VENDORED_ENGINE.is_file():
        _fail("falta service/scripts/text_unicode.py o su copia en la skill ligera")
        return 1
    a = hashlib.sha256(SERVICE_ENGINE.read_bytes()).hexdigest()
    b = hashlib.sha256(VENDORED_ENGINE.read_bytes()).hexdigest()
    if a != b:
        _fail(
            "el motor vendido en la skill ligera difiere del motor del servicio "
            f"({b[:12]} != {a[:12]}); copia el de service/scripts/"
        )
        return 1
    print(f"   ok (sha256 {a[:12]})")
    return 0


def check_no_secrets() -> int:
    print("6. Sin tokens de GitHub en el contenido publicado")
    # Los prefijos se componen en runtime para que este propio fichero no
    # coincida consigo mismo al escanearse.
    needles = ("gh" + "p_", "github" + "_pat_", "gho" + "_")
    fallos = avisos = 0
    for p, texto, publicado in _textos():
        if not any(n in texto for n in needles):
            continue
        rel = p.relative_to(ROOT)
        if publicado:
            _fail(f"{rel}: contiene un token de GitHub en contenido publicado")
            fallos += 1
        else:
            _warn(f"{rel}: contiene un token de GitHub (no se publica; borralo igual)")
            avisos += 1
    if not fallos and not avisos:
        print("   ok")
    else:
        print(f"   {fallos} en contenido publicado, {avisos} en ficheros locales")
    return fallos


def main() -> int:
    print("k-removemark: verificacion de integridad\n")
    fallos = 0
    for check in (
        check_syntax,
        check_json,
        check_manifest_paths,
        check_required_files,
        check_vendored_engine,
        check_no_secrets,
    ):
        fallos += check()
        print()
    if fallos:
        print(f"RESULTADO: {fallos} problema(s). No publiques hasta arreglarlos.")
        return 1
    print("RESULTADO: todo correcto.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
