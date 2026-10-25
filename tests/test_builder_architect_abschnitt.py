"""M-408c: _architect_abschnitt extrahiert Prosa pro Datei."""
from __future__ import annotations


def test_abschnitt_findet_datei():
    """Bei zwei Dateien in der Prosa wird nur die richtige extrahiert."""
    from werkstatt.builder import _architect_abschnitt
    prosa = (
        "## harness/versioning/applier.py\n"
        "Implementiere apply().\n"
        "\n"
        "## tests/unit/test_change_applier.py\n"
        "Schreibe Tests fuer apply().\n"
    )
    assert _architect_abschnitt(prosa, "harness/versioning/applier.py") == (
        "Implementiere apply()."
    )
    assert _architect_abschnitt(prosa, "tests/unit/test_change_applier.py") == (
        "Schreibe Tests fuer apply()."
    )


def test_abschnitt_fallback_ohne_ueberschrift():
    """Ohne '## <pfad>'-Ueberschrift kommt die ganze Prosa zurueck."""
    from werkstatt.builder import _architect_abschnitt
    prosa = "Nur ein Absatz ohne Ueberschrift."
    assert _architect_abschnitt(prosa, "irgendeine.py") == prosa


def test_abschnitt_letzte_datei_ohne_nachfolger():
    """Die letzte Datei hat keine naechste '## '-Ueberschrift."""
    from werkstatt.builder import _architect_abschnitt
    prosa = (
        "## a.py\n"
        "Text A.\n"
        "## b.py\n"
        "Text B bis zum Ende.\n"
    )
    assert _architect_abschnitt(prosa, "b.py") == "Text B bis zum Ende."
