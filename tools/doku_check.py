"""Doku-Drift-Checker (deterministisch, kein LLM).

Prueft die letzten N Commits auf Verdacht: Code geaendert ohne Doku-Update.

Regeln:
- Code-Pfade: werkstatt/, hooks/, tools/, static/
- Doku-Pfade: docs/, PROGRESS.md, AGENTS.md, ROADMAP.md, CHANGELOG.md
- Ein Commit ist verdaechtig wenn:
  * Er Code geaendert hat
  * UND er Doku NICHT geaendert hat
  * UND Subject beginnt mit feat(|fix(|chore(|refactor(|perf(
  * UND Subject enthaelt KEIN "(docs)"-Scope

Ausnahmen (kein Verdacht):
- Subject beginnt mit "docs(" oder "test(" oder "ci("
- Subject enthaelt "[skip-doku]" explizit
- Commit ist Merge

Aufruf:
  python3 tools/doku_check.py                     # Report, exit 0
  python3 tools/doku_check.py --strict            # exit 1 bei Verdacht
  python3 tools/doku_check.py --limit 50          # mehr Commits pruefen
  python3 tools/doku_check.py --json              # maschinenlesbar
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

__all__ = ["ist_verdaechtig", "main", "pruefe_commits"]

CODE_PREFIXE = ("werkstatt/", "hooks/", "tools/", "static/")
DOKU_PREFIXE = ("docs/", "PROGRESS.md", "AGENTS.md", "CHANGELOG.md")
CODE_SUBJECT_RE = re.compile(r"^(feat|fix|chore|refactor|perf)\(")
SKIP_SUBJECT_RE = re.compile(r"^(docs|test|ci)\(")
SKIP_TRAILER_RE = re.compile(r"\[skip-doku\]", re.IGNORECASE)


def _git(*args: str, cwd: Path | None = None) -> str:
    result = subprocess.run(
        ["git", *args],
        capture_output=True, text=True, timeout=10,
        cwd=str(cwd) if cwd else None,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {result.stderr.strip()}")
    return result.stdout


def _commit_files(sha: str, cwd: Path | None = None) -> list[str]:
    """Liefert geaenderte Dateien in einem Commit."""
    out = _git("show", "--name-only", "--format=", sha, cwd=cwd)
    return [ln.strip() for ln in out.splitlines() if ln.strip()]


def ist_verdaechtig(subject: str, files: list[str]) -> bool:
    """True = Code geaendert ohne Doku-Update, trotz Code-typischem Subject."""
    if SKIP_TRAILER_RE.search(subject):
        return False
    if SKIP_SUBJECT_RE.match(subject):
        return False
    if not CODE_SUBJECT_RE.match(subject):
        return False
    hat_code = any(f.startswith(CODE_PREFIXE) for f in files)
    if not hat_code:
        return False
    hat_doku = any(f.startswith(DOKU_PREFIXE) for f in files)
    return not hat_doku


def pruefe_commits(limit: int = 20, cwd: Path | None = None) -> list[dict]:
    """Prueft die letzten `limit` Commits, liefert Verdachts-Liste."""
    out = _git("log", f"-{limit}", "--format=%H|%s", cwd=cwd)
    verdacht = []
    for line in out.splitlines():
        if not line.strip():
            continue
        sha, _, subject = line.partition("|")
        files = _commit_files(sha, cwd=cwd)
        if ist_verdaechtig(subject, files):
            verdacht.append({
                "sha": sha[:10],
                "subject": subject,
                "code_files": [f for f in files if f.startswith(CODE_PREFIXE)][:5],
            })
    return verdacht


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Doku-Drift-Checker: prueft ob Code-Commits Doku-Update haben."
    )
    parser.add_argument("--limit", type=int, default=20,
                        help="Anzahl Commits pruefen (default: 20)")
    parser.add_argument("--strict", action="store_true",
                        help="Exit 1 bei Verdacht")
    parser.add_argument("--json", action="store_true",
                        help="JSON-Output")
    args = parser.parse_args(argv)

    try:
        verdacht = pruefe_commits(limit=args.limit)
    except RuntimeError as exc:
        print(f"[FEHLER] {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps({"verdacht": verdacht}, indent=2))
    else:
        if not verdacht:
            print(f"OK: keine Doku-Drift in letzten {args.limit} Commits.")
        else:
            print(f"[WARN] {len(verdacht)} Verdachts-Commit(s) "
                  f"in letzten {args.limit}:")
            for v in verdacht:
                print(f"\n  {v['sha']}  {v['subject']}")
                print(f"    Code geaendert, keine Doku: {v['code_files']}")
            print()
            print("  Fix: docs/STATUS.md, PROGRESS.md oder docs/ROADMAP.md")
            print("  aktualisieren. Oder Subject-Scope 'docs(' verwenden.")
            print("  Oder '[skip-doku]' im Subject bei reinem Code-Refactor.")

    if args.strict and verdacht:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
