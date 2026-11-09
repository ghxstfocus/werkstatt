"""OP-381i: Runs-Sidebar im Control-Modus (togglebar).

Source-Scan-Tests (kein Browser). Live-Verifikation manuell.
"""
from __future__ import annotations

from pathlib import Path


def _html() -> str:
    return Path("static/layout.html").read_text(encoding="utf-8")


def _css() -> str:
    return Path("static/layout.css").read_text(encoding="utf-8")


def _js() -> str:
    return Path("static/mode.js").read_text(encoding="utf-8")


def test_html_hat_runs_toggle():
    html = _html()
    assert 'id="runs-toggle"' in html
    assert 'id="runs-backdrop"' in html
    assert 'data-runs-open="false"' in html


def test_css_schiebt_runs_sidebar():
    css = _css()
    assert 'body[data-mode="control"] .bereich.runs' in css
    assert "translateX(-100%)" in css
    assert 'body[data-mode="control"][data-runs-open="true"]' in css


def test_css_runs_nur_in_control():
    css = _css()
    # Toggle nur im Control sichtbar
    assert 'body[data-mode="control"] .runs-toggle' in css
    assert "display: inline-flex" in css


def test_css_control_grid_ohne_runs():
    """Im Control-Modus: keine Runs-Spalte im Grid."""
    css = _css()
    # Die Regel existiert schon (aus vorherigem Commit):
    assert 'body[data-mode="control"] .layout-grid' in css


def test_js_toggle_runs():
    js = _js()
    assert "function toggleRuns" in js
    assert "_applyRunsOpen" in js
    assert 'data-runs-open' in js


def test_js_r_shortcut():
    js = _js()
    assert '"r"' in js or "'r'" in js
    # nur im Control-Modus
    assert 'data-mode") === "control"' in js or "getAttribute(\"data-mode\")" in js


def test_js_public_api():
    js = _js()
    assert "toggleRuns: toggleRuns" in js
