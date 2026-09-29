#!/usr/bin/env python3
"""Inspecciona texto buscando Unicode invisible / homoglifos de espacio (capa A)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running as script from any cwd
sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import emit_json, read_text_input  # noqa: E402
from text_unicode import human_report, inspect_text  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("path", nargs="?", default="-", help="Ruta del fichero de texto, o - para stdin")
    p.add_argument("--json", action="store_true", help="Informe en JSON")
    p.add_argument(
        "--aggressive",
        action="store_true",
        help="Marcar también los homoglifos latinos / de ancho completo",
    )
    p.add_argument(
        "--strip-emoji-glue",
        action="store_true",
        help="Paranoico: marcar todos los invisibles con función (pegamento de emojis, uniones de escritura, etiquetas de bandera, rellenos/selectores de la misma escritura, Cf ortográficos)",
    )
    p.add_argument(
        "--force-text",
        action="store_true",
        help="Analizar aunque la entrada parezca un contenedor binario",
    )
    args = p.parse_args()

    text = read_text_input(args.path, allow_binary=args.force_text)
    report = inspect_text(
        text,
        aggressive=args.aggressive,
        strip_emoji_glue=args.strip_emoji_glue,
    )
    if args.json:
        emit_json(report.to_dict())
    else:
        print(human_report(report))
    return 0 if report.suspicious_total == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
