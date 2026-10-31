"""tests fuer werkstatt/scaffold.py — DOC_CONVENTIONS.md §2."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, "/opt/werkstatt")

from werkstatt.scaffold import (
    PFLICHTDATEIEN,
    scaffold,
    substitute,
)


def test_pflichtdateien_liste():
    assert len(PFLICHTDATEIEN) == 13
    assert "AGENTS.md" in PFLICHTDATEIEN
    assert "docs/STATUS.md" in PFLICHTDATEIEN
    assert "docs/adr/README.md" in PFLICHTDATEIEN
    assert ".werkstatt/verify.json" in PFLICHTDATEIEN


def test_substitute_platzhalter():
    heute = datetime.now(timezone.utc).date().isoformat()
    out = substitute("{{project_name}} / {{project_dir}} / {{date}}",
                     "demo", Path("/tmp/demo"))
    assert "demo" in out
    assert "/tmp/demo" in out
    assert heute in out
    assert "{{" not in out


def test_scaffold_legt_alle_an(tmp_path):
    bericht = scaffold("demo", tmp_path)
    for rel in PFLICHTDATEIEN:
        assert (tmp_path / rel).is_file(), f"fehlt: {rel}"
        assert bericht[rel] == "angelegt"


def test_scaffold_platzhalter_ersetzt(tmp_path):
    scaffold("mein-projekt", tmp_path)
    agents = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "mein-projekt" in agents
    assert str(tmp_path) in agents
    assert "{{" not in agents


def test_scaffold_idempotent(tmp_path):
    scaffold("demo", tmp_path)
    bericht2 = scaffold("demo", tmp_path)
    for rel in PFLICHTDATEIEN:
        assert bericht2[rel] == "uebersprungen"


def test_scaffold_dry_run_schreibt_nichts(tmp_path):
    bericht = scaffold("demo", tmp_path, dry_run=True)
    for rel in PFLICHTDATEIEN:
        assert not (tmp_path / rel).exists()
        assert bericht[rel] == "waere-angelegt"


def test_scaffold_force_ueberschreibt(tmp_path):
    scaffold("demo", tmp_path)
    (tmp_path / "AGENTS.md").write_text("kaputt", encoding="utf-8")
    bericht = scaffold("demo", tmp_path, force=True)
    assert bericht["AGENTS.md"] == "ueberschrieben"
    content = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "kaputt" not in content
    assert "demo" in content


def test_scaffold_verzeichnis_fehlt():
    import pytest
    with pytest.raises(FileNotFoundError):
        scaffold("demo", Path("/tmp/gibt-es-garantiert-nicht-xyz-123"))


def test_verify_json_valide(tmp_path):
    scaffold("demo", tmp_path)
    data = json.loads((tmp_path / ".werkstatt/verify.json").read_text())
    assert "stages" in data
    assert len(data["stages"]) >= 1
    ids = [s["id"] for s in data["stages"]]
    assert "py_compile_changed" in ids
