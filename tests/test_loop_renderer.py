"""Tests fuer werkstatt/loop_renderer.py (M-301 CI-Modus)."""
from __future__ import annotations

import io
import sys
from unittest.mock import patch


def test_emit_tty_mode():
    """TTY: plain print ohne Zeitstempel."""
    import werkstatt.loop_renderer as r
    buf = io.StringIO()
    with patch.object(sys, "stdout", buf), \
         patch.object(r, "IS_CI", False):
        r._emit("test-zeile")
    out = buf.getvalue()
    assert "test-zeile" in out
    assert out.startswith("test-zeile")  # kein Timestamp-Prefix


def test_emit_ci_mode():
    """CI: Timestamp im Output."""
    import werkstatt.loop_renderer as r
    buf = io.StringIO()
    with patch.object(sys, "stdout", buf), \
         patch.object(r, "IS_CI", True):
        r._emit("test-zeile")
    out = buf.getvalue()
    assert "test-zeile" in out
    assert "[" in out  # Timestamp-Prefix


def test_group_start_end_ci():
    """CI: ::group:: / ::endgroup:: Marker."""
    import werkstatt.loop_renderer as r
    buf = io.StringIO()
    with patch.object(sys, "stdout", buf), \
         patch.object(r, "IS_CI", True):
        r.group_start("Phase 1: Explorer")
        r.group_end()
    out = buf.getvalue()
    assert "::group::Phase 1: Explorer" in out
    assert "::endgroup::" in out


def test_group_start_end_tty():
    """TTY: keine ::group::-Marker."""
    import werkstatt.loop_renderer as r
    buf = io.StringIO()
    with patch.object(sys, "stdout", buf), \
         patch.object(r, "IS_CI", False):
        r.group_start("Phase 1: Explorer")
        r.group_end()
    out = buf.getvalue()
    assert "::group::" not in out
    assert "::endgroup::" not in out


def test_heartbeat_ci():
    """CI: Heartbeat-Zeile mit elapsed."""
    import werkstatt.loop_renderer as r
    buf = io.StringIO()
    with patch.object(sys, "stdout", buf), \
         patch.object(r, "IS_CI", True):
        r.heartbeat("Planner", 42)
    out = buf.getvalue()
    assert "Planner" in out
    assert "42s" in out


def test_step_mit_elapsed():
    """M-302: step() zeigt elapsed_s."""
    import werkstatt.loop_renderer as r
    buf = io.StringIO()
    with patch.object(sys, "stdout", buf), \
         patch.object(r, "IS_CI", False):
        r.step(1, "Explorer", "3 files", elapsed_s=1.234)
    out = buf.getvalue()
    assert "1.2s" in out


def test_group_nicht_verschachtelt():
    """M-302: group_start/group_end paarweise."""
    import werkstatt.loop_renderer as r
    buf = io.StringIO()
    with patch.object(sys, "stdout", buf), \
         patch.object(r, "IS_CI", True):
        r.group_start("Phase 1")
        r.group_end()
        r.group_start("Phase 2")
        r.group_end()
    out = buf.getvalue()
    assert out.count("::group::") == 2
    assert out.count("::endgroup::") == 2
