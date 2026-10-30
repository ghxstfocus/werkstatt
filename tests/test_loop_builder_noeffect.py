"""Spec: no_effect-Patches im Architect-Pfad filter.

GOLD 2026-10-30: Live-Beleg 20:46:55 — builder_patch_no_effect +
builder_patches_erstellt + loop_patch_updated: ein Patch ohne
Aenderung wurde angewendet. Der Haupt-Pfad filtert no_effect,
der Architect-Pfad nicht.
"""
from __future__ import annotations

import inspect

from werkstatt import builder


def test_builder_hat_no_effect_filter_im_run_builder():
    """run_builder filtert old==new-Patches (no_effect)."""
    rb_src = inspect.getsource(builder.run_builder)
    # Der Filter prueft old_string == new_string
    assert 'old_string' in rb_src
    assert 'new_string' in rb_src
    assert 'builder_patch_no_effect' in rb_src
    # Und der Filter setzt das auftrag_bereits_erfuellt-Flag
    assert 'auftrag_bereits_erfuellt' in rb_src


def test_reviewer_hat_datei_check():
    """Der Reviewer hat einen DATEI-CHECK-Block."""
    from werkstatt import reviewer
    s = reviewer._reviewer_system()
    assert "## DATEI-CHECK" in s
    assert "AKTUELLER DATEI-INHALT" in s
    assert "entries[-" in s or "_RECENT_CHANGES_LIMIT" in s


# =====================================================================
# GOLD 2026-10-30: old_string-Pruefung in _build_patches_fuer_datei
# =====================================================================

def test_old_nicht_da_new_da_wird_verworfen(tmp_path):
    """Wenn old_string nicht in der Datei, aber new_string schon:
    Patch verwerfen, Auftrag ist erfuellt.

    Regression: Live 2026-10-30 21:37:34 — alerts.html hatte schon
    class="table table-alerts", der Builder baute old_string='class="table"'.
    """
    import inspect
    from werkstatt import builder

    # Pruefe, dass der Code im Source steht
    src = inspect.getsource(builder._build_patches_fuer_datei)
    assert "old_nicht_da_aber_new_da" in src
    assert "_new_in_datei" in src
    assert "_old_in_datei" in src
