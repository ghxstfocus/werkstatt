"""OP-381c: Gate-Modal (Source-Scan)."""
from __future__ import annotations

from pathlib import Path


def _html() -> str:
    return Path("static/layout.html").read_text(encoding="utf-8")


def _css() -> str:
    return Path("static/layout.css").read_text(encoding="utf-8")


def _js() -> str:
    return Path("static/gate_panel.js").read_text(encoding="utf-8")


def test_html_hat_banner_und_modal():
    html = _html()
    for eid in ("gate-banner", "gate-banner-close", "gate-backdrop",
                "gate-modal", "gate-modal-title", "gate-modal-close",
                "gate-modal-body", "gate-modal-actions"):
        assert f'id="{eid}"' in html, f"ID fehlt: {eid}"


def test_html_alte_aside_weg():
    html = _html()
    assert '<aside class="gate-panel"' not in html


def test_js_kein_draggable():
    js = _js()
    assert "_machDraggable" not in js


def test_js_hat_typ_freitext():
    js = _js()
    assert 'typ === "freitext"' in js
    assert "gm-textarea" in js


def test_js_hat_copy_button():
    js = _js()
    assert "navigator.clipboard" in js
    assert "Als Markdown kopieren" in js


def test_js_hat_escape_und_backdrop():
    js = _js()
    assert '"Escape"' in js
    assert "_schliesseModal" in js


def test_js_nutzt_gate_context():
    js = _js()
    assert "/gate/context" in js
    assert "/api/runs/" in js


def test_css_modal_vollbild():
    css = _css()
    assert ".gate-modal" in css
    assert ".gate-modal-inner" in css
    assert "max-width: 900px" in css
    assert "max-height: 90vh" in css


def test_css_backdrop_blur():
    css = _css()
    assert "backdrop-filter: blur(8px)" in css
    assert "rgba(0, 0, 0, 0.6)" in css


def test_css_animation_scale():
    css = _css()
    assert "scale(0.96)" in css
    assert "180ms" in css


def test_css_banner_pulse():
    css = _css()
    assert ".gate-banner" in css
    assert "gate-banner-pulse" in css


def test_css_actions_sticky():
    css = _css()
    assert ".gate-modal-actions" in css
    assert "position: sticky" in css


def test_css_typ_freitext():
    css = _css()
    assert ".gm-textarea" in css


def test_css_markdown_formatierung():
    css = _css()
    assert ".gm-h2" in css
    assert ".gm-li" in css


def test_css_reduced_motion():
    css = _css()
    idx = css.find("prefers-reduced-motion")
    assert idx > 0
