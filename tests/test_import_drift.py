"""Smoke-Tests fuer tools/import_drift.py (OP-144)."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
_ROOT = _HERE.parent.parent


def test_wrapper_existiert():
    assert (_ROOT / "tools" / "import_drift.py").is_file()


def test_importlinter_installiert():
    lint = Path(sys.executable).parent / "lint-imports"
    if not lint.exists():
        lint = shutil.which("lint-imports")
    assert lint is not None, "import-linter nicht installiert"


def test_wrapper_ist_gruen():
    r = subprocess.run(
        [sys.executable, str(_ROOT / "tools" / "import_drift.py")],
        cwd=_ROOT, capture_output=True, text=True, check=False,
    )
    assert r.returncode == 0, (
        f"import_drift rc={r.returncode}\n"
        f"stdout: {r.stdout[-500:]}\n"
        f"stderr: {r.stderr[-500:]}"
    )


def test_verify_json_hat_import_drift():
    d = json.loads((_ROOT / ".werkstatt" / "verify.json").read_text())
    ids = {s["id"]: s for s in d["stages"]}
    assert "import_drift" in ids
    assert ids["import_drift"].get("hart") is True
