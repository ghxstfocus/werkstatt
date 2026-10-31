"""Phase 5d — Docs-Prioritaet (DOC_CONVENTIONS.md §6)."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, "/opt/werkstatt")

from werkstatt.orchestrator import (
    _DOCS_PRIORITAET,
    _sortiere_docs_nach_prioritaet,
    load_docs,
)


def test_prioritaetsliste():
    assert _DOCS_PRIORITAET == [
        "entry", "status", "roadmap", "architecture",
        "conventions", "adr_index", "glossary",
    ]


def test_sortierung_entry_vor_rest():
    cfg = {
        "glossary": "g", "adr_index": "a", "architecture": "ar",
        "roadmap": "r", "status": "s", "entry": "e",
    }
    keys = [k for k, _ in _sortiere_docs_nach_prioritaet(cfg)]
    assert keys == [
        "entry", "status", "roadmap", "architecture",
        "adr_index", "glossary",
    ]


def test_sortierung_unbekannte_ans_ende():
    cfg = {"zzz": "z", "entry": "e", "aaa": "a"}
    keys = [k for k, _ in _sortiere_docs_nach_prioritaet(cfg)]
    assert keys[0] == "entry"
    assert keys[-2:] == ["aaa", "zzz"]


def test_load_docs_priorisiert():
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        for n in ("a.md", "b.md", "c.md"):
            (d / n).write_text(n, encoding="utf-8")
        cfg = {"glossary": "a.md", "entry": "c.md", "status": "b.md"}
        docs = load_docs(cfg, d)
        assert list(docs.keys()) == ["entry", "status", "glossary"]
