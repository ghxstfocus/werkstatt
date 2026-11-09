"""OP-381j-Codex: Live-Feed Polish (Source-Scan)."""
from __future__ import annotations

from pathlib import Path


def _js() -> str:
    return Path("static/live_feed.js").read_text(encoding="utf-8")


def _css() -> str:
    return Path("static/layout.css").read_text(encoding="utf-8")


def test_js_spinner():
    js = _js()
    assert "SPINNER" in js
    assert "\\u280b" in js or "\u280b" in js
    assert "_startSpinner" in js
    assert "_stopSpinner" in js


def test_js_dots():
    js = _js()
    assert "lf-dots" in js
    assert "lf-aktiv-aktion lf-dots" in js


def test_js_wartend():
    js = _js()
    assert "lf-aktiv-wartend" in js
    assert "warte auf" in js


def test_js_just_finished():
    js = _js()
    assert "rolleGeandert" in js
    assert "_just_finished" in js
    assert "unshift" in js


def test_js_steps_limit():
    js = _js()
    assert "STEPS_LIMIT = 8" in js or "STEPS_LIMIT=8" in js


def test_js_spinner_an_mode():
    js = _js()
    assert "_startSpinner();" in js
    assert "_stopSpinner();" in js


def test_js_keine_hex_farben():
    import re
    js = _js()
    hex_matches = re.findall(r"[\"']#[0-9a-fA-F]{3,6}[\"']", js)
    assert not hex_matches, f"Hex-Farben: {hex_matches[:3]}"
    assert "var(--sem-" in js


def test_css_spinner():
    css = _css()
    assert ".lf-spinner" in css
    assert ".lf-spinner-char" in css


def test_css_dots():
    css = _css()
    assert ".lf-dots::after" in css
    assert "@keyframes lf-dots-anim" in css


def test_css_shimmer():
    css = _css()
    assert "lf-shimmer" in css
    assert "linear-gradient" in css


def test_css_aktiv_fade():
    css = _css()
    assert ".lf-aktiv-neu" in css
    assert "lf-aktiv-in" in css


def test_css_step_slide():
    css = _css()
    assert "lf-step-slide-in" in css
    assert ".lf-step-fertig" in css


def test_css_reduced_motion():
    css = _css()
    idx = css.find("prefers-reduced-motion")
    assert idx > 0
