"""Phase 5c — Scout liest priorisierte Projekt-Doku (PROJEKT-DOKU-Sektion).

Der Test prueft WIRKUNG: der Block muss NACH der user_content-Zuweisung
stehen und user_content ergaenzen. Sonst wird er ueberschrieben.
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
    prio_str = src[prio_start:prio_start + 200]
    assert prio_str.find('"entry"') < prio_str.find('"status"')
    assert prio_str.find('"status"') < prio_str.find('"roadmap"')
    assert prio_str.find('"roadmap"') < prio_str.find('"architecture"')


def test_scout_block_nach_user_content():
    """Kritisch: PROJEKT-DOKU muss user_content NACH der Original-Zuweisung ergaenzen."""
    lines = SCOUT.read_text(encoding="utf-8").split("\n")
    uc_line = None
    doku_block_line = None
    for i, ln in enumerate(lines):
        if uc_line is None and ln.strip().startswith("user_content = "):
            uc_line = i + 1
        if doku_block_line is None and "## PROJEKT-DOKU" in ln:
            doku_block_line = i + 1
    assert uc_line, "user_content-Zuweisung nicht gefunden"
    assert doku_block_line, "PROJEKT-DOKU-Block nicht gefunden"
    assert doku_block_line > uc_line, (
        f"PROJEKT-DOKU-Block (Z.{doku_block_line}) muss NACH der "
        f"user_content-Zuweisung (Z.{uc_line}) stehen — sonst wird er ueberschrieben."
    )


def test_scout_ergaenzt_user_content():
    """Der Block muss user_content nachtraeglich modifizieren."""
    src = SCOUT.read_text(encoding="utf-8")
    assert "user_content = (" in src
    # Ergaenzungsform: user_content = "..." + ... + user_content
    import re
    m = re.search(
        r'user_content = \(\s*\n(?:[^)]*\n)*?[^)]*\+ user_content',
        src,
    )
    assert m, "user_content wird nicht um PROJEKT-DOKU ergaenzt"
