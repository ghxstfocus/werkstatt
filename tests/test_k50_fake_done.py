"""K50: Fake-Done-Schutz bei Reviewer-Reject.

In 22:17 (2026-10-28) wurde ein Task als task_ok markiert, obwohl
der Builder-Patch nie angewandt wurde (loop_patch_old_string_not_found).
Ursache: _hat_patch prueft bool(state.patches), nicht ob Patches
wirklich angewandt wurden. K50 fuehrt state.applied_count ein und
_patches_wirklich_angewendet(state) als zentralen Check.
"""

import sys
from pathlib import Path

from werkstatt.loop import _patches_wirklich_angewendet

_here = Path(__file__).parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))
from factories import mk_state  # noqa: E402


def test_hat_patch_false_when_zero_applied():
    """patches truthy, applied_count 0 -> fail-closed False."""
    state = mk_state(
        patches=[{"file": "x.py", "old_string": "a", "new_string": "b"}],
        applied_count=0,
    )
    assert _patches_wirklich_angewendet(state) is False


def test_hat_patch_true_when_applied():
    """patches truthy, applied_count > 0 -> True."""
    state = mk_state(
        patches=[{"file": "x.py", "old_string": "a", "new_string": "b"}],
        applied_count=2,
    )
    assert _patches_wirklich_angewendet(state) is True


def test_hat_patch_false_when_no_patches():
    """patches leer -> False, unabhaengig von applied_count."""
    state = mk_state(patches=[], applied_count=3)
    assert _patches_wirklich_angewendet(state) is False


def test_hat_patch_false_when_applied_count_missing():
    """applied_count NICHT gesetzt -> fail-closed False.

    Regression: in K50 war der Default None (fail-open). K50b hat
    ihn auf 0 (fail-closed) gedreht. Dieser Test schuetzt die
    Korrektur.
    """
    state = mk_state(
        patches=[{"file": "x.py", "old_string": "a", "new_string": "b"}],
    )
    # OP-174 P3: mk_state() setzt applied_count=0 (RunState-Default).
    # Um den "Feld fehlt"-Fall explizit zu testen, entfernen wir das
    # Attribut nach mk_state() — das simuliert "Feld nicht deklariert",
    # das _patches_wirklich_angewendet robust behandeln muss.
    delattr(state, "applied_count")
    assert _patches_wirklich_angewendet(state) is False
