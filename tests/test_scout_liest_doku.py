"""Phase 5c — Scout liest priorisierte Projekt-Doku.

Wirkungspruefung: _docs_prepend wird NACH user_content angehaengt.
"""
from __future__ import annotations
from pathlib import Path

SCOUT = Path("/opt/werkstatt/werkstatt/scout.py")


def test_scout_hat_projekt_doku_sektion():
    src = SCOUT.read_text(encoding="utf-8")
    assert "## PROJEKT-DOKU" in src
    assert "_DOCS_PRIO" in src
    assert "[:4000]" in src


def test_scout_prioritaet_reihenfolge():
    src = SCOUT.read_text(encoding="utf-8")
    prio_start = src.find("_DOCS_PRIO =")
    assert prio_start > 0
    prio_str = src[prio_start:prio_start + 250]
    assert prio_str.find('"entry"') < prio_str.find('"status"')
    assert prio_str.find('"status"') < prio_str.find('"roadmap"')
    assert prio_str.find('"roadmap"') < prio_str.find('"architecture"')


def test_scout_prepend_nach_original():
    """Append muss NACH Original-Zuweisung stehen — sonst wirkungslos."""
    src = SCOUT.read_text(encoding="utf-8")
    assert "_docs_prepend = \"\"" in src, "Init fehlt"
    assert "user_content = _docs_prepend + user_content" in src, "Append fehlt"
    idx_orig = src.find("    user_content = (")
    idx_append = src.find("user_content = _docs_prepend + user_content")
    assert idx_orig > 0
    assert idx_append > idx_orig, (
        f"Append ({idx_append}) muss nach Original ({idx_orig}) stehen"
    )


def test_scout_prepend_wird_im_if_gesetzt():
    """_docs_prepend muss im if-Block gesetzt werden, nicht ausserhalb."""
    src = SCOUT.read_text(encoding="utf-8")
    # Init als ""
    assert '_docs_prepend = ""' in src
    # Zuweisung im if
    assert "        _docs_prepend = (" in src
