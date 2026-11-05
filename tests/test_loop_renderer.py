"""Tests fuer werkstatt/loop_renderer.py (M-301 CI-Modus)."""
from __future__ import annotations

import io
import sys
from unittest.mock import patch

from werkstatt.render import emit as _emod
from werkstatt.render import rich as _rmod
from werkstatt.render import tee as _tmod


def test_emit_tty_mode():
    """TTY: plain print ohne Zeitstempel."""
    import werkstatt.render as r
    buf = io.StringIO()
    with patch.object(sys, "stdout", buf), \
         patch.object(_rmod, "IS_CI", False):
        r._emit("test-zeile")
    out = buf.getvalue()
    assert "test-zeile" in out
    assert out.startswith("test-zeile")  # kein Timestamp-Prefix


def test_emit_ci_mode():
    """CI: Timestamp im Output."""
    import werkstatt.render as r
    buf = io.StringIO()
    with patch.object(sys, "stdout", buf), \
         patch.object(_rmod, "IS_CI", True):
        r._emit("test-zeile")
    out = buf.getvalue()
    assert "test-zeile" in out
    assert "[" in out  # Timestamp-Prefix


def test_group_start_end_ci():
    """CI: ::group:: / ::endgroup:: Marker."""
    import werkstatt.render as r
    buf = io.StringIO()
    with patch.object(sys, "stdout", buf), \
         patch.object(_rmod, "IS_CI", True):
        r.group_start("Phase 1: Explorer")
        r.group_end()
    out = buf.getvalue()
    assert "::group::Phase 1: Explorer" in out
    assert "::endgroup::" in out


def test_group_start_end_tty():
    """TTY: keine ::group::-Marker."""
    import werkstatt.render as r
    buf = io.StringIO()
    with patch.object(sys, "stdout", buf), \
         patch.object(_rmod, "IS_CI", False):
        r.group_start("Phase 1: Explorer")
        r.group_end()
    out = buf.getvalue()
    assert "::group::" not in out
    assert "::endgroup::" not in out


def test_heartbeat_ci():
    """CI: Heartbeat-Zeile mit elapsed."""
    import werkstatt.render as r
    buf = io.StringIO()
    with patch.object(sys, "stdout", buf), \
         patch.object(_rmod, "IS_CI", True):
        r.heartbeat("Planner", 42)
    out = buf.getvalue()
    assert "Planner" in out
    assert "42s" in out


def test_step_mit_elapsed():
    """M-302: step() zeigt elapsed_s."""
    import werkstatt.render as r
    buf = io.StringIO()
    with patch.object(sys, "stdout", buf), \
         patch.object(_rmod, "IS_CI", False):
        r.step(1, "Explorer", "3 files", elapsed_s=1.234)
    out = buf.getvalue()
    assert "1.2s" in out


def test_group_nicht_verschachtelt():
    """M-302: group_start/group_end paarweise."""
    import werkstatt.render as r
    buf = io.StringIO()
    with patch.object(sys, "stdout", buf), \
         patch.object(_rmod, "IS_CI", True):
        r.group_start("Phase 1")
        r.group_end()
        r.group_start("Phase 2")
        r.group_end()
    out = buf.getvalue()
    assert out.count("::group::") == 2
    assert out.count("::endgroup::") == 2


# ============================================================
# OP-111 (2026-11-04): _emit_progress-Tests.
# _TEE_STREAM=None ist Pflicht — sonst schreibt der Test in die
# echte Log-Datei (OP-103-Praevention).
# ============================================================


def test_emit_progress_ci_sequenziell():
    """CI: [label] step detail als Zeile."""
    import werkstatt.render as r
    buf = io.StringIO()
    with patch.object(sys, "stdout", buf), \
         patch.object(_tmod, "_TEE_STREAM", None), \
         patch.object(_rmod, "IS_CI", True), \
         patch.object(_rmod, "IS_LIVE", False), \
         patch.object(_emod, "_publish", lambda *a, **kw: None):
        r._emit_progress("Builder", "start", "x.py")
    assert "[Builder] start x.py" in buf.getvalue()


def test_emit_progress_live_ueberschreibt():
    """Live: kein Newline im Output."""
    import werkstatt.render as r
    buf = io.StringIO()
    with patch.object(sys, "stdout", buf), \
         patch.object(_tmod, "_TEE_STREAM", None), \
         patch.object(_rmod, "IS_LIVE", True), \
         patch.object(_emod, "_publish", lambda *a, **kw: None):
        r._emit_progress("Builder", "start", "x.py")
    out = buf.getvalue()
    assert "[Builder] start x.py" in out
    assert "\n" not in out


def test_emit_progress_leerer_step_no_op():
    """Leerer step: kein Output."""
    import werkstatt.render as r
    buf = io.StringIO()
    with patch.object(sys, "stdout", buf), \
         patch.object(_tmod, "_TEE_STREAM", None), \
         patch.object(_rmod, "IS_CI", True), \
         patch.object(_emod, "_publish", lambda *a, **kw: None):
        r._emit_progress("Builder", "")
    assert buf.getvalue() == ""
