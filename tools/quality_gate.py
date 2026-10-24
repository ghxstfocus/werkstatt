"""Quality-Gate: deterministischer Shell-Bypass fuer pytest/ruff/mypy.

Ersetzt LLM-basierte "bitte Tests laufen lassen"-Prompts durch
festen Aufruf mit fixierten Baseline-Werten.

Baseline-Quelle: das BASELINE-Dict unten (einzige lebende Wahrheit).
Historische Doku: docs/HANDOFF-BASELINE.md (seit 2026-10-24 nicht
mehr gepflegt) und docs/BASELINE-2026-10-19.md (Momentaufnahme).

Exit-Codes:
  0 = ok (delta == 0)
  1 = regression (delta != 0)
  2 = Skript-Fehler (Subprozess-Fehler)

Aufruf:
  python3 -m tools.quality_gate [--hook] [--json]
"""
from __future__ import annotations

import argparse
import json

# Recursion Guard (Phase 14): Wenn wir in einem Test laufen,
# sofort ok zurueckgeben, ohne pytest/ruff/mypy aufzurufen.
import os as _os
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

if _os.environ.get("WERKSTATT_IN_TEST") == "1":
    import sys as _sys
    print('{"ok": true, "regression": false, "skipped": "WERKSTATT_IN_TEST=1"}')
    _sys.exit(0)


# Baseline fixiert (Quelle: docs/HANDOFF-BASELINE.md @ ae40f26).
BASELINE = {
    "pytest": 1425,   # pytest -q (M-359b: +1 fail-closed-Test)
    "ruff": 13,       # ruff check .
    "mypy": 8,        # mypy pipeline.py werkstatt/
    "ast": 6,         # pytest tests/test_audit_kinds.py -q
    "katalog": 162,   # _KATALOG_SOLL
}

HEAD = "ae40f26"  # Baseline-Anker (nicht HEAD). Aktueller HEAD wechselt pro Commit.


def _run(cmd: list[str], cwd: Path) -> tuple[int, str]:
    """Fuehrt Kommando aus, liefert (rc, output)."""
    try:
        res = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True,
            timeout=600, check=False,
        )
        return res.returncode, res.stdout + res.stderr
    except subprocess.TimeoutExpired:
        return -1, "TIMEOUT"
    except FileNotFoundError as exc:
        return -1, f"NICHT GEFUNDEN: {exc}"


def _parse_pytest(out: str) -> tuple[int, int]:
    """pytest -q -> (passed, failed)."""
    m = re.search(r"(\d+) passed", out)
    passed = int(m.group(1)) if m else 0
    m = re.search(r"(\d+) failed", out)
    failed = int(m.group(1)) if m else 0
    m = re.search(r"(\d+) error", out)
    errors = int(m.group(1)) if m else 0
    return passed, failed + errors


def _parse_count(out: str, pattern: str) -> int:
    m = re.search(pattern, out)
    return int(m.group(1)) if m else -1


def _git_head(cwd: Path) -> str:
    rc, out = _run(["git", "rev-parse", "--short", "HEAD"], cwd)
    return out.strip() if rc == 0 else "unknown"


def check_all(cwd: Path) -> dict:
    """Fuehrt alle 5 Checks aus, liefert dict."""
    result = {"timestamp": datetime.now(UTC).isoformat(),
              "head": _git_head(cwd),
              "baseline": dict(BASELINE),
              "current": {},
              "delta": {},
              "ok": False,
              "regression": False,
              "fehler": None}

    # pytest
    _rc, out = _run(["pytest", "-q"], cwd)
    passed, failed = _parse_pytest(out)
    result["current"]["pytest"] = {"passed": passed, "failed": failed}
    # M-331: failed zaehlt als Fehler. Sonst ist der Gate fail-open:
    # 1360 passed + 1 failed -> delta=0 -> "ok", obwohl ein Test rot ist.
    result["delta"]["pytest"] = (BASELINE["pytest"] - passed) + failed

    # ruff
    _rc, out = _run(["ruff", "check", "--no-cache", "."], cwd)
    n = _parse_count(out, r"Found (\d+) errors")
    result["current"]["ruff"] = {"errors": n}
    result["delta"]["ruff"] = n - BASELINE["ruff"]

    # mypy
    _rc, out = _run(["mypy", "pipeline.py", "werkstatt/"], cwd)
    n = _parse_count(out, r"Found (\d+) errors")
    result["current"]["mypy"] = {"errors": n}
    result["delta"]["mypy"] = n - BASELINE["mypy"]

    # ast
    _rc, out = _run(
        ["pytest", "tests/test_audit_kinds.py", "-q"], cwd)
    passed, _ = _parse_pytest(out)
    result["current"]["ast"] = {"passed": passed}
    result["delta"]["ast"] = BASELINE["ast"] - passed

    # katalog
    pipeline = cwd / "pipeline.py"
    if pipeline.exists():
        content = pipeline.read_text()
        m = re.search(r"_KATALOG_SOLL\s*=\s*(\d+)", content)
        n = int(m.group(1)) if m else -1
    else:
        n = -1
    result["current"]["katalog"] = {"soll": n}
    result["delta"]["katalog"] = n - BASELINE["katalog"]

    # Regression?
    reg = any(abs(v) > 0 for v in result["delta"].values())
    result["ok"] = not reg
    result["regression"] = reg
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Quality-Gate: pytest/ruff/mypy/AST/Katalog")
    parser.add_argument("--hook", action="store_true",
                        help="Hook-Modus (Logging, keine Verdrahtung)")
    parser.add_argument("--json", action="store_true",
                        help="JSON-Output (Default: lesbar)")
    args = parser.parse_args(argv)

    cwd = Path.cwd()
    try:
        result = check_all(cwd)
    except Exception as exc:  # noqa: BLE001
        print(f"[FAIL] Skript-Fehler: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"HEAD: {result['head']}")
        print(f"Timestamp: {result['timestamp']}")
        for key in ["pytest", "ruff", "mypy", "ast", "katalog"]:
            print(f"  {key}: soll={BASELINE[key]} ist={result['current'][key]} "
                  f"delta={result['delta'][key]}")
        print(f"OK: {result['ok']}  regression: {result['regression']}")

    if args.hook:
        log = cwd / ".werkstatt" / "quality_gate.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("a") as f:
            f.write(json.dumps(result) + "\n")
        print(f"[i] Hook-Log: {log}", file=sys.stderr)

    if result["regression"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
