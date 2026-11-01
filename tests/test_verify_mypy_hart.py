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


# ═══════════════════════════════════════════════════════════════
# OP-062f End-to-End: mypy-Stage mit hart=true landet in _hart
# ═══════════════════════════════════════════════════════════════


def test_verify_patches_soft_mypy_hart_landet_in_hart(
    tmp_path: Path, monkeypatch,
) -> None:
    """Stage mypy_changed hart=true: Stage-Fehler zaehlt als hart, nicht weich."""
    from types import SimpleNamespace
    from werkstatt import verify as verify_mod

    # Fake-state: nur noetige Felder.
    state = SimpleNamespace()
    state.project_dir = tmp_path
    state.project_name = "p"
    state.last_verify_errors = []
    state.last_verify_hart_stages = set()
    state.changed_files = ["core/x.py"]

    # _verify_patches mocken: setzt Fehler + hart_stage_set wie _verify_patches.
    def _fake_verify(state_arg, phase=None):
        state_arg.last_verify_errors = [
            "mypy_changed: core/x.py:80: error: unsupported operand",
        ]
        state_arg.last_verify_hart_stages = {"mypy_changed"}
        return False

    monkeypatch.setattr(verify_mod, "_verify_patches", _fake_verify)

    ok, weich = verify_mod._verify_patches_soft(state, phase="post_build")

    # mypy_changed ist hart -> ok=False, keine weichen Fehler
    assert ok is False, f"erwartet ok=False, war {ok}"
    assert weich == [], f"erwartet weich=[], war {weich}"
    assert state.last_verify_errors, (
        "harte Errors muessen in last_verify_errors bleiben"
    )
    assert any("mypy" in e for e in state.last_verify_errors)


def test_verify_patches_soft_mypy_ohne_hart_bleibt_weich(
    tmp_path: Path, monkeypatch,
) -> None:
    """Stage mypy_changed ohne hart-Feld: Prefix-Match -> weich (alt)."""
    from types import SimpleNamespace
    from werkstatt import verify as verify_mod

    state = SimpleNamespace()
    state.project_dir = tmp_path
    state.project_name = "p"
    state.last_verify_errors = []
    state.last_verify_hart_stages = set()
    state.changed_files = ["core/x.py"]

    def _fake_verify(state_arg, phase=None):
        state_arg.last_verify_errors = [
            "mypy_changed: core/x.py:80: error: unsupported operand",
        ]
        # KEIN hart_stage-Eintrag -> Prefix-Match
        state_arg.last_verify_hart_stages = set()
        return False

    monkeypatch.setattr(verify_mod, "_verify_patches", _fake_verify)

    ok, weich = verify_mod._verify_patches_soft(state, phase="post_build")

    # mypy ohne hart-Flag -> weich -> ok=True, in weich
    assert ok is True, f"erwartet ok=True, war {ok}"
    assert weich, "weiche Errors sollten in weich landen"
