"""OP-389b: parse_ops muss OP-Suffixe (a/b/c) erkennen.

Verbotenes Verhalten (Live-Bug 2026-11-09 18:58):
- parse_ops findet OP-389b/OP-381b/OP-381c/OP-306a... NICHT
- /start uebergibt leere aufgabe an den Loop
- Loop startet, Explorer findet 0 Dateien (leere Suchbegriffe)
- state_contract_violation explorer->scout ["explorer_context"]
- loop_failed nach 1.6s, 13 Events, kein Task gebaut
- Folge: Roadmap-Block (UI-Modi) blockiert, Control-Modus unerreichbar

Diese Tests verbieten den alten Regex. Inkonsistenz-Beweis: Zeile 77
in derselben Datei nutzt schon OP-\\d+[a-z]? fuer blockiert_von.
"""
from __future__ import annotations

import pytest

from werkstatt.web import inspector


@pytest.fixture
def status_md(tmp_path, monkeypatch):
    """Kleine STATUS.md mit normalen OPs + Sub-OPs."""
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "STATUS.md").write_text(
        """### OP-220: Erfahrungs-Gehirn

- **Status:** open
- **Blockiert von:** —

### OP-220a: erfahrung-Tabelle erweitern

- **Status:** open
- **Blockiert von:** OP-220

### OP-281: Scout-Redundanz

- **Status:** open
- **Blockiert von:** OP-385

### OP-306a: Tab-Persistenz

- **Status:** open
- **Blockiert von:** —

### OP-306b: Workspace-Overview

- **Status:** open
- **Blockiert von:** OP-306a

### OP-306c: Multi-Projekt-Datenquellen

- **Status:** open
- **Blockiert von:** OP-306b

### OP-389b: DRY-Migration WS-Auth

- **Status:** open
- **Blockiert von:** —
""",
        encoding="utf-8",
    )
    return tmp_path


def test_parse_ops_findet_sub_op_389b(status_md):
    """Kernfall: OP-389b muss gefunden werden (Live-Bug)."""
    ops = inspector.parse_ops(status_md)
    ids = {op["id"] for op in ops}
    assert "OP-389b" in ids, (
        f"OP-389b fehlt in parse_ops -> /start bekommt leere Aufgabe "
        f"-> Loop crasht. Gefunden: {sorted(ids)}"
    )


def test_parse_ops_findet_normalen_op_weiterhin(status_md):
    """Regression: normaler OP-220 darf nicht verschwinden."""
    ops = inspector.parse_ops(status_md)
    ids = {op["id"] for op in ops}
    assert "OP-220" in ids
    assert "OP-281" in ids


def test_parse_ops_alle_suffix_varianten(status_md):
    """a/b/c-Suffixe muessen alle erkannt werden (Roadmap-Block)."""
    ops = inspector.parse_ops(status_md)
    ids = {op["id"] for op in ops}
    erwartet = {"OP-220", "OP-220a", "OP-281",
                "OP-306a", "OP-306b", "OP-306c", "OP-389b"}
    fehlend = erwartet - ids
    assert not fehlend, (
        f"Roadmap-Sub-OPs fehlen: {sorted(fehlend)}. "
        f"Gefunden: {sorted(ids)}"
    )


def test_parse_ops_titel_von_sub_op(status_md):
    """Der Titel eines Sub-OPs muss korrekt extrahiert werden."""
    ops = inspector.parse_ops(status_md)
    by_id = {op["id"]: op for op in ops}
    assert by_id["OP-389b"]["titel"].startswith("DRY-Migration")
