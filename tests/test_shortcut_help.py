"""OP-304: Shortcut-Help-Overlay Frontend-Smoke."""
from pathlib import Path


def _js():
    return Path("static/shortcut_help.js").read_text(encoding="utf-8")


def _html():
    return Path("static/layout.html").read_text(encoding="utf-8")


def _css():
    return Path("static/layout.css").read_text(encoding="utf-8")


def test_overlay_existiert_im_html():
    html = _html()
    assert 'id="shortcut-help-overlay"' in html
    assert 'id="shortcut-help-close"' in html


def test_js_hat_fragezeichen_handler():
    js = _js()
    assert 'e.key === "?"' in js
    assert "_inInputFeld" in js


def test_js_hat_oeffnen_schliessen():
    js = _js()
    assert "WerkstattShortcutHelp" in js
    assert "oeffnen" in js
    assert "schliessen" in js


def test_css_hat_overlay():
    css = _css()
    assert ".shortcut-help-overlay" in css
    assert ".shortcut-help-overlay.offen" in css


def test_kbd_styling():
    css = _css()
    assert ".shortcut-help-keys kbd" in css


def test_keine_escapes():
    js = _js()
    import re
    treffer = re.findall(r"\\\\u[0-9a-fA-F]{4}", js)
    assert not treffer, f"Escapes gefunden: {treffer[:3]}"
