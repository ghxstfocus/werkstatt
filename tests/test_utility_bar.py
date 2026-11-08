"""OP-305: Utility-Bar (Klickwege) + Shift+N Frontend-Smoke."""
from pathlib import Path


def _js():
    return Path("static/utility_bar.js").read_text(encoding="utf-8")


def _html():
    return Path("static/layout.html").read_text(encoding="utf-8")


def _css():
    return Path("static/layout.css").read_text(encoding="utf-8")


def test_buttons_im_html():
    html = _html()
    assert 'id="utility-palette"' in html
    assert 'id="utility-help"' in html


def test_js_hat_handler():
    js = _js()
    assert "_oeffnePalette" in js
    assert "_oeffneHelp" in js
    assert "WerkstattPalette" in js
    assert "WerkstattShortcutHelp" in js


def test_shift_n_handler():
    js = _js()
    assert "e.shiftKey" in js
    assert 'e.key !== "N"' in js
    assert "tab-neu" in js


def test_css_utility_bar():
    css = _css()
    assert ".utility-bar" in css
    assert ".utility-btn" in css


def test_tooltip_auf_plus():
    html = _html()
    assert 'title="Projekt hinzufügen (Shift+N)"' in html
