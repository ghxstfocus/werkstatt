"""OP-175 Bug B: verify_gleich als Stagnations-Grund.

Loop-Test-6 (18:29): Builder baute 5x neuen Patch, mypy-Fehler
blieb byte-identisch. Der Stagnation-Counter griff nicht, weil
der bestehende Code nur `ruff` und `reviewer_bugs` als Gruende
kannte. Nachfolger: `_verify_fehler_zwischen_runden_gleich`
erkennt gleiche Verify-Fehler zwischen Runden zeilenunabhaengig.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from werkstatt import reflection

_here = Path(__file__).parent
if str(_here) not in _sys.path:
    _sys.path.insert(0, str(_here))
from factories import mk_state  # noqa: E402

# ============ Unit: _fehler_signatur_normalisiert ============

def test_signatur_leer() -> None:
    assert reflection._fehler_signatur_normalisiert([]) == ""


def test_signatur_mypy_gleich_trotz_zeile() -> None:
    e1 = 'mypy_changed: x.py:59: error: "RunState" has no attribute "phase_review_gate_auto"  [attr-defined]'
    e2 = 'mypy_changed: x.py:88: error: "RunState" has no attribute "phase_review_gate_auto"  [attr-defined]'
    assert reflection._fehler_signatur_normalisiert(
        [e1]) == reflection._fehler_signatur_normalisiert([e2])


def test_signatur_mypy_verschiedene_fehler() -> None:
    e1 = 'mypy_changed: x.py:59: error: "RunState" has no attribute "foo"'
    e2 = 'mypy_changed: x.py:59: error: "RunState" has no attribute "bar"'
    assert reflection._fehler_signatur_normalisiert(
        [e1]) != reflection._fehler_signatur_normalisiert([e2])


def test_signatur_ruff_b010() -> None:
    e = 'ruff_changed:  |\nhelp: Replace `setattr` with assignment\nB010 Do not call setattr with a constant attribute value'
    sig = reflection._fehler_signatur_normalisiert([e])
    assert "B010" in sig or "replace" in sig.lower()


def test_signatur_path_mapping_nicht_leer() -> None:
    """path-mapping-Notiz: Signatur darf nicht "" sein, sonst greift
    verify_gleich nicht ueber Format-Wechsel hinweg."""
    e = 'mypy_changed: (also at "werkstatt/phases/review.py")\nwerkstatt/phases/review.py: note: See https://mypy...'
    sig = reflection._fehler_signatur_normalisiert([e])
    assert sig != ""


def test_signatur_dict_form() -> None:
    e = {"stage_id": "mypy_changed", "text": "x.py:1: error: foo"}
    sig = reflection._fehler_signatur_normalisiert([e])
    assert "foo" in sig


# ============ Unit: _verify_fehler_zwischen_runden_gleich ============

def _mk_history_state(tmp_path):
    s = mk_state(project_dir=tmp_path, project_name="t", api_key="x")
    s.reflection_history = []
    s.last_verify_errors = []
    return s


def test_zwischen_runden_gleich_false_ohne_history(tmp_path) -> None:
    s = _mk_history_state(tmp_path)
    assert reflection._verify_fehler_zwischen_runden_gleich(s) is False


def test_zwischen_runden_gleich_false_bei_leer_und_leer(tmp_path) -> None:
    """Beide leer -> kein Grund, Stagnation zu melden."""
    s = _mk_history_state(tmp_path)
    s.reflection_history = [{"runde": 1, "verify_errors": []}]
    s.last_verify_errors = []
    assert reflection._verify_fehler_zwischen_runden_gleich(s) is False


def test_zwischen_runden_gleich_true_bei_identischer_stage(tmp_path) -> None:
    """Spec: stage-basiert. Format-Wechsel path-mapping -> attr-defined
    zaehlt NICHT als neuer Fehler (Loop-Test-6)."""
    s = _mk_history_state(tmp_path)
    s.reflection_history = [{
        "runde": 1,
        "patches_applied": 1,
        "verify_errors": [
            'mypy_changed: (also at "werkstatt/phases/review.py")'
        ],
    }]
    s.last_verify_errors = [
        'mypy_changed: werkstatt/phases/review.py:59: error: attr-defined'
    ]
    assert reflection._verify_fehler_zwischen_runden_gleich(s) is True


def test_zwischen_runden_gleich_false_bei_applied_null(tmp_path) -> None:
    """Spec: applied=0 in Vorrunde -> kein verify_gleich.
    patch_nicht_angewendet ist separater Pfad, keine verify-Stagnation."""
    s = _mk_history_state(tmp_path)
    s.reflection_history = [{
        "runde": 1,
        "patches_applied": 0,
        "verify_errors": ["mypy_changed: x.py:59: error: foo"],
    }]
    s.last_verify_errors = ["mypy_changed: x.py:60: error: foo"]
    assert reflection._verify_fehler_zwischen_runden_gleich(s) is False


def test_zwischen_runden_gleich_false_bei_verschieden(tmp_path) -> None:
    s = _mk_history_state(tmp_path)
    s.reflection_history = [{"runde": 1,
                             "verify_errors": ['mypy_changed: x.py:1: error: foo']}]
    s.last_verify_errors = ['mypy_changed: x.py:1: error: bar']
    assert reflection._verify_fehler_zwischen_runden_gleich(s) is False


# ============ Integration: _reflection_loop mit verify_gleich ============

def _setup_mocks(monkeypatch):
    """Mocks fuer _reflection_loop.

    Wichtig: _reflection_loop importiert run_builder LOKAL aus
    `werkstatt.roles.builder` (Z.373). Nur `reflection.run_builder`
    zu patchen reicht NICHT — die Funktion greift auf den lokalen
    Import. Beide Namen patchen wie test_reflection.py es macht.
    """
    import werkstatt.roles.builder as _builder_mod
    mocks = SimpleNamespace(
        run_builder=MagicMock(return_value=True),
        apply_patches=MagicMock(return_value=(1, [{"file": "x.py"}])),
        ruff_fix=MagicMock(return_value=None),
        audit=MagicMock(),
        log_line=MagicMock(),
    )
    monkeypatch.setattr(_builder_mod, "run_builder",
                        mocks.run_builder, raising=False)
    monkeypatch.setattr(reflection, "run_builder",
                        mocks.run_builder, raising=False)
    monkeypatch.setattr(reflection, "_apply_patches_with_diagnose",
                        mocks.apply_patches, raising=False)
    monkeypatch.setattr(reflection, "_ruff_fix_changed",
                        mocks.ruff_fix, raising=False)
    monkeypatch.setattr(reflection, "audit", mocks.audit, raising=False)
    monkeypatch.setattr(reflection, "log_line", mocks.log_line, raising=False)
    monkeypatch.setattr(reflection, "_diff_hash_for_state",
                        lambda s: "changing_hash", raising=False)
    return mocks


def test_reflection_loop_stagnation_verify_gleich(tmp_path, monkeypatch):
    """Spec: 5 Runden, Builder baut jedes Mal neuen Patch (Hash
    wechselnd), mypy-Fehler bleibt gleich. Stagnation erkennt das
    nach 2 Runden (Runde 3) und bricht ab.

    Loop-Test-6-Muster: 10x mypy attr-defined + 5x applied>0 +
    keine ruff-Befunde + keine reviewer_bugs -> ohne diesen Fix
    laeuft der Loop die vollen 5 Runden."""
    # patches vorab setzen: sonst _patches=[] -> Z.564-566 continue
    # -> History wird nicht geschrieben -> Stagnation nie erreicht.
    # Analog test_reflection_spec_erschoepfung.py.
    s = mk_state(
        api_key="x",
        project_dir=tmp_path,
        project_name="t",
        patches=[{"file": "x.py", "old_string": "a", "new_string": "b"}],
        reviewer_bugs=[],
        last_verify_errors=[],
    )
    s.reflection_history = []
    s.aktuelle_task = {"id": "t1", "task_files": ["x.py"]}
    mocks = _setup_mocks(monkeypatch)

    _fehler = 'mypy_changed: x.py:59: error: attr-defined'
    def _verify_konstant(st, phase=None):
        # Zeilennummer aendert sich bei jedem Patch, Fehler bleibt.
        _runde = len(st.reflection_history) + 1
        st.last_verify_errors = [
            _fehler.replace(":59:", f":{59 + _runde}:")
        ]
        return False
    monkeypatch.setattr(reflection, "_verify_patches",
                        _verify_konstant, raising=False)

    rc = reflection._reflection_loop(s, max_runden=5)

    assert rc is False
    # History-Write ist VOR verify (Z.604 vs Z.625). Erste Runde
    # hat history[0].verify_errors=[] -> stage-gleich matcht erst
    # ab Runde 3. _stagnation>=2 -> Abbruch in Runde 4.
    assert mocks.run_builder.call_count <= 4, (
        f"Loop lief {mocks.run_builder.call_count} Runden, "
        f"erwartet <= 4 (Stagnation nach 2, Startverzoegerung 1 Runde "
        f"durch History-Write-before-Verify)"
    )
    # Mindestens 2 Stagnations-Events mit grund=verify_gleich
    stag_events = [
        c for c in mocks.audit.call_args_list
        if c.args and c.args[0] == "loop_reflection_stagnation_runde"
    ]
    verify_gleich_events = [
        c for c in stag_events
        if len(c.args) > 1 and isinstance(c.args[1], dict)
        and c.args[1].get("grund") == "verify_gleich"
    ]
    assert len(verify_gleich_events) >= 2, (
        f"Nur {len(verify_gleich_events)} verify_gleich-Events; "
        f"alle stag-Events: {[c.args[1] for c in stag_events]}"
    )
    # Spec: Stagnation greift ohne Spec-Widerspruch-Verdacht
    # (STATUS-AK verlangt Abbruch, nicht spec_widerspruch). Der
    # Abbruch erfolgt als normaler Task-Fail (return False).
    assert getattr(s, "spec_widerspruch_erkannt", False) is False
