"""Scout-Prompt-Haertung: OP-NNN-Disziplin bei vagen Aufgaben."""
from __future__ import annotations
from pathlib import Path

SCOUT = Path("/opt/werkstatt/werkstatt/scout.py")


def test_op_disziplin_sektion_existiert():
    src = SCOUT.read_text(encoding="utf-8")
    assert "## OP-NNN-DISZIPLIN" in src


def test_op_disziplin_waehlt_genau_einen():
    src = SCOUT.read_text(encoding="utf-8")
    i = src.find("## OP-NNN-DISZIPLIN")
    j = src.find("## DEIN NACHFOLGER")
    assert i > 0 and j > i
    section = src[i:j]
    assert "GENAU EINEN" in section
    assert "NIEMALS zwei oder alle" in section
    assert "ziel" in section
    assert "OP-NNN: <Titel>" in section


def test_op_disziplin_vage_erkannt():
    src = SCOUT.read_text(encoding="utf-8")
    i = src.find("## OP-NNN-DISZIPLIN")
    j = src.find("## DEIN NACHFOLGER")
    section = src[i:j]
    for kw in ("naechster Schritt", "unerledigte", "was ist zu tun",
               "offene Punkte"):
        assert kw in section, f"Vage-Keyword fehlt: {kw}"


def test_op_disziplin_reihenfolge_vor_nachfolger():
    """OP-NNN-DISZIPLIN muss im SCOUT_SYSTEM stehen, nicht im Nachfolger."""
    src = SCOUT.read_text(encoding="utf-8")
    op = src.find("## OP-NNN-DISZIPLIN")
    nf = src.find("## DEIN NACHFOLGER")
    assert op > 0
    assert nf > op
    # Bereich zwischen den Markern ist im SCOUT_SYSTEM-String
    # (SCOUT_SYSTEM = startet bei Zeile 34, endet mit schliessendem """)
    scout_start = src.find('SCOUT_SYSTEM = """')
    scout_end = src.find('"""', scout_start + 20) + 3
    assert scout_start < op < scout_end


def test_op_disziplin_nicht_vage_klausel():
    """Nicht-vage Aufgaben duerfen OP-NNN ignorieren."""
    src = SCOUT.read_text(encoding="utf-8")
    i = src.find("## OP-NNN-DISZIPLIN")
    j = src.find("## DEIN NACHFOLGER")
    section = src[i:j]
    assert "NICHT vage" in section
    assert "ignoriere OP-NNN" in section
