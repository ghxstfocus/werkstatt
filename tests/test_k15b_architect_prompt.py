"""K15b: ARCHITECT_SYSTEM fordert Interface-Grenzen statt Nummerierung."""
from werkstatt.planner import ARCHITECT_SYSTEM


def test_pro_datei_block() -> None:
    assert "PRO DATEI EIN BLOCK" in ARCHITECT_SYSTEM


def test_keine_nummerierten_schritte() -> None:
    assert "NICHT als" in ARCHITECT_SYSTEM
    assert "nummerierte Schritte" in ARCHITECT_SYSTEM


def test_keine_alte_anweisung() -> None:
    assert "Der Planner-Split schneidet die Prosa an diesen" not in ARCHITECT_SYSTEM


def test_groessen_ziel() -> None:
    assert "50-150 Zeilen" in ARCHITECT_SYSTEM


def test_beispiel_gut_und_schlecht() -> None:
    assert "Beispiel GUT" in ARCHITECT_SYSTEM
    assert "Beispiel SCHLECHT" in ARCHITECT_SYSTEM


def test_ein_block_pro_funktion() -> None:
    assert "EIN Block pro Funktion" in ARCHITECT_SYSTEM


def test_generische_beispiele() -> None:
    """Neue Beispiele muessen generisch sein (app/foo.py)."""
    assert "app/foo.py" in ARCHITECT_SYSTEM
    # Altlast in API-STABILITAET (ApplierError) ist erlaubt.
