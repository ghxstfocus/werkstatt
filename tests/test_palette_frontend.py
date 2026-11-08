"""OP-302: Palette Frontend-Smoke."""
from pathlib import Path


def _js():
    return Path("static/palette.js").read_text(encoding="utf-8")


def _html():
    return Path("static/layout.html").read_text(encoding="utf-8")


def _css():
    return Path("static/layout.css").read_text(encoding="utf-8")


def test_html_hat_overlay():
    html = _html()
    assert 'id="palette-overlay"' in html
    assert 'id="palette-input"' in html
    assert 'id="palette-treffer"' in html


def test_js_hat_keyboard_handler():
    js = _js()
    assert "ctrlKey" in js
    assert "metaKey" in js
    assert 'e.key === "k"' in js
    assert 'e.key === "Escape"' in js
    assert 'e.key === "Enter"' in js


def test_js_hat_navigation_und_aktionen():
    js = _js()
    assert "ArrowDown" in js
    assert "ArrowUp" in js
    assert "_ausfuehren" in js
    assert "start_op" in js


def test_js_fetcht_palette_endpoint():
    js = _js()
    # URL wird dynamisch gebaut: _baseUrl() + "?q=" + query
    assert "/palette" in js
    assert "?q=" in js


def test_css_hat_overlay():
    css = _css()
    assert ".palette-overlay" in css
    assert ".palette-overlay.offen" in css
    assert ".palette-treffer-zeile.aktiv" in css


def test_keine_kindischen_emojis():
    html = _html()
    assert "\U0001F916" not in html
    assert "\U0001F4AC" not in html
