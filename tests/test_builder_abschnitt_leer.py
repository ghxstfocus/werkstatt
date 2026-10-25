"""M-450: Leerer Abschnitt -> Builder bricht ab, kein LLM-Aufruf."""
from __future__ import annotations


def test_abschnitt_leer_wenn_datei_nicht_beschrieben():
    """Wenn die Prosa ## -Ueberschriften hat, aber die Datei fehlt: ''."""
    from werkstatt.builder import _architect_abschnitt
    prosa = (
        "## harness/versioning/applier.py\n"
        "Beschreibung Applier.\n"
        "## harness/versioning/__init__.py\n"
        "Beschreibung Init.\n"
    )
    # Datei ist NICHT in der Prosa -> leerer String.
    assert _architect_abschnitt(prosa, "tests/unit/test_foo.py") == ""


def test_abschnitt_ganze_prosa_ohne_ueberschriften():
    """Fallback: keine ## -Ueberschriften -> ganze Prosa."""
    from werkstatt.builder import _architect_abschnitt
    prosa = "Nur ein Absatz ohne Ueberschrift."
    assert _architect_abschnitt(prosa, "irgendeine.py") == prosa


def test_abschnitt_findet_datei_wenn_vorhanden():
    """Wenn die Datei in der Prosa ist: Abschnitt."""
    from werkstatt.builder import _architect_abschnitt
    prosa = (
        "## a.py\n"
        "Text A.\n"
        "## b.py\n"
        "Text B.\n"
    )
    assert _architect_abschnitt(prosa, "b.py") == "Text B."
