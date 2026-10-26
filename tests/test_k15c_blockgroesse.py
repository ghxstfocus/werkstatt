"""K15c: Block-Groesse 2500 statt 800/2000."""
from werkstatt.planner import _extrahiere_prosa_abschnitt


def test_2000_zeichen_block_bleibt_vollstaendig() -> None:
    """2500-Grenze: 2000-Zeichen-Block wird NICHT abgeschnitten."""
    start = "Block 1 — Fehler"
    body = "x" * 2000 + "."
    ende = "Block 2 — Konstruktor"
    prosa = f"{start}\n{body}\n{ende}\nInhalt 2."
    out = _extrahiere_prosa_abschnitt(prosa, start, ende)
    assert len(out) > 1900, f"Block zu kurz: {len(out)} Zeichen"
    assert "x" * 500 in out


def test_2500_zeichen_block_bleibt() -> None:
    start = "Start"
    body = "y" * 2400 + "."
    ende = "Ende"
    prosa = f"{start}\n{body}\n{ende}"
    out = _extrahiere_prosa_abschnitt(prosa, start, ende)
    assert len(out) > 2400, f"Block zu kurz: {len(out)} Zeichen"


def test_ueber_2500_wird_gekuerzt() -> None:
    start = "Start"
    body = "z" * 3000 + "."
    ende = "Ende"
    prosa = f"{start}\n{body}\n{ende}"
    out = _extrahiere_prosa_abschnitt(prosa, start, ende)
    assert len(out) <= 2600, f"Block zu lang: {len(out)} Zeichen"


def test_kleiner_block_unveraendert() -> None:
    start = "A"
    body = "kurz"
    ende = "B"
    prosa = f"{start}\n{body}\n{ende}"
    out = _extrahiere_prosa_abschnitt(prosa, start, ende)
    assert "kurz" in out
