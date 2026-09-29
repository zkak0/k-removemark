#!/usr/bin/env python3
"""Elimina Unicode invisible / normaliza espacios homoglifos (capa A)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import backup_path, cleaned_path, eprint, read_text_input, write_text_output  # noqa: E402
from text_unicode import clean_text  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("path", nargs="?", default="-", help="Ruta del fichero de texto, o - para stdin")
    p.add_argument("-o", "--output", help="Ruta de salida (por defecto stdout o *.cleaned.*)")
    p.add_argument("--nfkc", action="store_true", help="Aplicar normalización Unicode NFKC tras la limpieza")
    p.add_argument(
        "--aggressive-homoglyphs",
        action="store_true",
        help="Convertir los homoglifos latinos cirílicos/de ancho completo a ASCII",
    )
    p.add_argument(
        "--no-normalize-spaces",
        action="store_true",
        help="No reescribir los espacios exóticos a U+0020",
    )
    p.add_argument(
        "--strip-emoji-glue",
        action="store_true",
        help="Paranoico: eliminar también los invisibles con función (pegamento de emojis, uniones de escritura, etiquetas de bandera, rellenos/selectores de la misma escritura, Cf ortográficos)",
    )
    p.add_argument(
        "--strip-bidi",
        action="store_true",
        help="Eliminar también las marcas de dirección (LRM, RLM, LRE…RLO, LRI…PDI). Rompe el texto de derecha a izquierda: revisa antes de usarlo en árabe o hebreo",
    )
    p.add_argument("--stats", action="store_true", help="Imprimir las estadísticas en JSON por stderr")
    p.add_argument(
        "--force-text",
        action="store_true",
        help="Limpiar aunque la entrada parezca un contenedor binario "
        "(reescribe los bytes y corromperá el archivo)",
    )
    p.add_argument(
        "--in-place",
        action="store_true",
        help="Sobrescribir el archivo de entrada (crea una copia .bak)",
    )
    args = p.parse_args()

    text = read_text_input(args.path, allow_binary=args.force_text)
    cleaned, stats = clean_text(
        text,
        nfkc=args.nfkc,
        aggressive_homoglyphs=args.aggressive_homoglyphs,
        normalize_spaces=not args.no_normalize_spaces,
        strip_emoji_glue=args.strip_emoji_glue,
        strip_bidi=args.strip_bidi,
    )

    out = args.output
    if args.in_place:
        if args.path in (None, "-"):
            eprint("--in-place requires a file path")
            return 2
        src = Path(args.path)
        bak = backup_path(src)
        out = str(src)
    elif out is None and args.path not in (None, "-"):
        out = str(cleaned_path(Path(args.path)))

    write_text_output(cleaned, out)

    if args.stats:
        eprint(json.dumps(stats, indent=2, ensure_ascii=False))
    else:
        eprint(
            f"removed={stats['removed_count']} replaced={stats['replaced_count']} "
            f"len {stats['input_length']}->{stats['output_length']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
