#!/usr/bin/env python3
"""Watch a folder and clean AI/C2PA provenance marks from files that appear.

Pure-stdlib polling watcher (no `watchdog` dependency): every `--interval`
seconds it rescans the input directory and cleans any file that is new or
whose (size, mtime) changed since last scan.

Cleaning is delegated to `clean_file.py` as a subprocess (same approach as
`clean_staged.py`) so no logic is duplicated here.

Modes:
  * default       : write cleaned copies into `--output`; the original is
                    never touched.
  * `--in-place`  : rewrite files in place (opt-in; only use on a dedicated
                    drop folder you own).

A small state file next to the input dir remembers what has been processed so
a daemon restart does not re-clean everything. Exit 0 = no problems; 1 = at
least one file was cleaned this run.
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import eprint

log = logging.getLogger("watch_folder")

CLEAN_FILE_PY = Path(__file__).resolve().parent / "clean_file.py"
STATE_NAME = "._remove-ai-marks-watch.json"


def _state_path(input_dir: Path) -> Path:
    return input_dir / STATE_NAME


def _load_state(input_dir: Path) -> dict:
    path = _state_path(input_dir)
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return {k: tuple(v) if isinstance(v, list) else v for k, v in data.items()}
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_state(input_dir: Path, state: dict) -> None:
    _state_path(input_dir).write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")


def _signature(path: Path) -> tuple[int, int]:
    st = path.stat()
    return st.st_size, st.st_mtime_ns

def _clean_one(path: Path) -> bool:
    """Returns True if the file was changed by cleaning."""
    proc = subprocess.run(
        [sys.executable, str(CLEAN_FILE_PY), str(path), "--in-place", "--json"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode == 2:
        log.info("skipped (unrecognized format or oversized): %s", path)
        return False
    if not proc.stdout.strip():
        log.info("skipped (no output): %s — %s", path, proc.stderr.strip())
        return False
    try:
        result = json.loads(proc.stdout)
    except json.JSONDecodeError:
        log.info("skipped (bad JSON): %s", path)
        return False
    stats = result.get("stats") or {}
    changed = bool(
        stats.get("removed_count") or stats.get("replaced_count") or result.get("actions")
    )
    return changed

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input", type=Path, help="Folder to watch")
    p.add_argument("-o", "--output", type=Path, help="Where cleaned copies go")
    p.add_argument("--in-place", action="store_true", help="Rewrite files in place")
    p.add_argument("--interval", type=float, default=5.0, help="Poll interval seconds")
    p.add_argument("--once", action="store_true", help="Single scan then exit")
    p.add_argument("--log-file", help="Append log lines to this file")
    args = p.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    if args.log_file:
        fh = logging.FileHandler(args.log_file, encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
        log.addHandler(fh)

    if not args.input.is_dir():
        eprint(f"input is not a directory: {args.input}")
        return 2
    if args.in_place:
        args.output = args.input
    elif args.output is None:
        eprint("need --output DIR (or --in-place)")
        return 2
    args.output.mkdir(parents=True, exist_ok=True)

    state = _load_state(args.input)
    cleaned_any = False

    try:
        while True:
            for path in sorted(args.input.iterdir()):
                if not path.is_file():
                    continue
                if path.name == STATE_NAME:
                    continue
                if path.name.startswith(".") or path.suffix == ".bak":
                    continue
                sig = _signature(path)
                if state.get(str(path)) == sig:
                    continue
                if args.in_place:
                    target = path
                else:
                    target = args.output / path.name
                    try:
                        target.write_bytes(path.read_bytes())
                    except OSError as exc:
                        log.info("copy failed for %s: %s", path.name, exc)
                        continue
                changed = _clean_one(target)
                if changed:
                    cleaned_any = True
                    log.info("cleaned: %s", path.name)
                state[str(path)] = _signature(path)
            _save_state(args.input, state)
            if args.once:
                break
            time.sleep(args.interval)
    except KeyboardInterrupt:
        log.info("stopped")
        _save_state(args.input, state)

    return 1 if cleaned_any else 0


if __name__ == "__main__":
    raise SystemExit(main())
