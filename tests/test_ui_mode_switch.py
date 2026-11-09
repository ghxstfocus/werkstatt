"""OP-306a: UI-Modi (Cockpit / Control / Debug) — Source-Scan-Tests.

Verhaltens-Tests sind ohne Playwright/Selenium nicht moeglich (nicht
installiert, eigener OP). Diese Tests locken die SPEC-Kontrakte:

- mode.js existiert, enthaelt alle 3 Modi, persistiert in localStorage
- layout.html hat data-mode-Attribut + mode-switch-Buttons + Script-Tag
- layout.css hat 3 Grid-Varianten via [data-mode="..."]

Der Live-Test (Shift+Space, Klick auf Buttons, Reload-Persistenz) ist
manuell im Browser, siehe ADR-0022 AK (b)+(c)+(d).
"""
from __future__ import annotations

from pathlib import Path


def _html() -> str:
    return Path("static/layout.html").read_text(encoding="utf-8")


def _css() -> str:
    return Path("static/layout.css").read_text(encoding="utf-8")


def _js() -> str:
    return Path("static/mode.js").read_text(encoding="utf-8")


def test_mode_js_existiert_und_hat_alle_modi():
    js = _js()
    for m in ("cockpit", "control", "debug"):
        assert f'"{m}"' in js, f"Modus {m} fehlt in mode.js"
    assert "localStorage" in js
    assert "Shift" in js or "shiftKey" in js
    assert "werkstatt:mode-change" in js


def test_html_hat_mode_switch():
    html = _html()
    assert 'data-mode="cockpit"' in html, "body braucht data-mode=default"
    assert 'id="mode-switch"' in html
    for m in ("cockpit", "control", "debug"):
        assert f'data-mode-btn="{m}"' in html, f"Button fuer {m} fehlt"
    assert '/static/mode.js' in html, "mode.js muss eingebunden sein"


def test_css_hat_drei_grid_varianten():
    css = _css()
    for m in ("cockpit", "control", "debug"):
        assert f'body[data-mode="{m}"]' in css, f"Grid-Variante fuer {m} fehlt"


def test_css_mode_switch_sichtbar():
    css = _css()
    assert ".mode-switch" in css
    assert ".mode-btn.aktiv" in css


def test_mode_js_url_parameter():
    """?mode=control Deep-Link (lesen + schreiben + default-delete)."""
    js = _js()
    assert "URLSearchParams" in js
    assert '.get("mode")' in js
    assert '.set("mode"' in js
    assert '.delete("mode")' in js


def test_mode_js_direkt_tasten():
    """1/2/3 als Direkt-Shortcuts."""
    js = _js()
    assert 'e.key === "1"' in js
    assert 'e.key === "2"' in js
    assert 'e.key === "3"' in js


def test_mode_js_nicht_in_input():
    """Tasten nicht abfangen, wenn Input/Textarea fokussiert."""
    js = _js()
    assert 'tag === "INPUT"' in js or "TEXTAREA" in js
