"""OP-062f: verify.json-Stage kann explizit als hart markiert werden.

`_stage_ist_hart` klassifiziert per Prefix-Match. `mypy_hart`.startswith
("mypy") ist True -> weich. Eine Stage mit Stage-Fehler wuerde als
Warnung durchgehen und den Loop nicht blockieren. Deshalb braucht
verify.json ein optionales Feld 'hart': true, das die Prefix-
Klassifikation ueberschreibt.
"""
from __future__ import annotations

from pathlib import Path

from werkstatt.verify import _stage_ist_hart


def test_hart_flag_ueberschreibt_mypy_weich() -> None:
    """Stage mit hart=true ist hart, auch wenn ID mit 'mypy' beginnt."""
    stage = {"id": "mypy_changed", "hart": True,
             "command": ["python3", "-m", "mypy", "core/"]}
    assert _stage_ist_hart(stage) is True, (
        "hart=true muss Prefix-Klassifikation ueberschreiben"
    )


def test_ohne_hart_flag_bleibt_prefix_klassifikation() -> None:
    """Ohne hart-Feld: 'mypy' ist weich (alte Klassifikation)."""
    stage = {"id": "mypy_changed",
             "command": ["python3", "-m", "mypy", "core/"]}
    assert _stage_ist_hart(stage) is False, (
        "'mypy'-Prefix bleibt weich ohne hart-Flag"
    )


def test_hart_flag_false_laesst_prefix_gelten() -> None:
    """hart=false: Prefix-Klassifikation gilt weiter (pytest bleibt hart)."""
    stage = {"id": "pytest_changed", "hart": False,
             "command": ["python3", "-m", "pytest"]}
    # pytest ist hart per Prefix; hart=false soll NICHT weich machen
    # (Empfehlung: hart-Feld darf nur verschaerfen, nicht entschaerfen).
    assert _stage_ist_hart(stage) is True, (
        "hart=false darf Prefix-Hart nicht zu weich machen"
    )


def test_hart_flag_rueckwaertskompatibel_mit_string_id() -> None:
    """Alte Aufruf-Stellen mit String-stage_id funktionieren weiter."""
    assert _stage_ist_hart("pytest_full_checks") is True
    assert _stage_ist_hart("ruff_changed") is False
    assert _stage_ist_hart("mypy_changed") is False
