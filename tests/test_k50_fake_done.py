"""K50: Fake-Done-Schutz bei Reviewer-Reject.

In 22:17 (2026-10-28) wurde ein Task als task_ok markiert, obwohl
der Builder-Patch nie angewandt wurde (loop_patch_old_string_not_found).
Ursache: _hat_patch prueft bool(state.patches), nicht ob Patches
wirklich angewandt wurden. K50 fuehrt state.applied_count ein und
_patches_wirklich_angewendet(state) als zentralen Check.
"""

from types import SimpleNamespace

from werkstatt.loop import _patches_wirklich_angewendet


def test_hat_patch_false_when_zero_applied():
    """patches truthy, applied_count 0 -> fail-closed False."""
    state = SimpleNamespace(
        patches=[{"file": "x.py", "old_string": "a", "new_string": "b"}],
        applied_count=0,
    )
    assert _patches_wirklich_angewendet(state) is False


def test_hat_patch_true_when_applied():
    """patches truthy, applied_count > 0 -> True."""
    state = SimpleNamespace(
        patches=[{"file": "x.py", "old_string": "a", "new_string": "b"}],
        applied_count=2,
    )
    assert _patches_wirklich_angewendet(state) is True


def test_hat_patch_false_when_no_patches():
    """patches leer -> False, unabhaengig von applied_count."""
    state = SimpleNamespace(patches=[], applied_count=3)
    assert _patches_wirklich_angewendet(state) is False


def test_hat_patch_false_when_applied_count_missing():
    """applied_count NICHT gesetzt -> fail-closed False.

    Regression: in K50 war der Default None (fail-open). K50b hat
    ihn auf 0 (fail-closed) gedreht. Dieser Test schuetzt die
    Korrektur.
    """
    state = SimpleNamespace(
        patches=[{"file": "x.py", "old_string": "a", "new_string": "b"}],
        # applied_count absichtlich NICHT gesetzt
    )
    assert _patches_wirklich_angewendet(state) is False
