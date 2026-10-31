"""Scout-Prompt-Haertung: OP-NNN-Disziplin bei vagen Aufgaben.

Whitespace-normalisiert, damit Zeilenumbrueche im Prompt-Text
Tests nicht brechen.
"""
from __future__ import annotations
from pathlib import Path

SCOUT = Path("/opt/werkstatt/werkstatt/scout.py")


def _norm(s: str) -> str:
    return " ".join(s.split())


def _section() -> str:
    src = SCOUT.read_text(encoding="utf-8")
    i = src.find("## OP-NNN-DISZIPLIN")
    j = src.find("## DEIN NACHFOLGER")
    assert i > 0 and j > i
    return src[i:j]


def test_op_disziplin_sektion_existiert():
    src = SCOUT.read_text(encoding="utf-8")
    assert "## OP-NNN-DISZIPLIN" in src


def test_op_disziplin_waehlt_genau_einen():
    s = _norm(_section())
    assert "GENAU EINEN" in s
    assert "NIEMALS zwei oder alle" in s
    assert "ziel" in s
    assert "OP-NNN: <Titel>" in s


def test_op_disziplin_vage_erkannt():
    s = _norm(_section())
    for kw in ("naechster Schritt", "unerledigte", "was ist zu tun",
               "offene Punkte"):
        assert kw in s, f"Vage-Keyword fehlt: {kw}"


def test_op_disziplin_reihenfolge_vor_nachfolger():
    """OP-NNN-DISZIPLIN muss im SCOUT_SYSTEM stehen, nicht im Nachfolger."""
    src = SCOUT.read_text(encoding="utf-8")
    op = src.find("## OP-NNN-DISZIPLIN")
    nf = src.find("## DEIN NACHFOLGER")
    assert op > 0
    assert nf > op
    scout_start = src.find('SCOUT_SYSTEM = """')
    scout_end = src.find('"""', scout_start + 20) + 3
    assert scout_start < op < scout_end


def test_op_disziplin_nicht_vage_klausel():
    """Nicht-vage Aufgaben duerfen OP-NNN ignorieren."""
    s = _norm(_section())
    assert "NICHT vage" in s
    assert "ignoriere OP-NNN" in s
