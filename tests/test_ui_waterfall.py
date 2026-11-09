"""OP-381i Frontend: Swimlane-Wasserfall im Control-Modus.

Source-Scan-Tests (kein Browser). Die Verhaltens-Verifikation
(SVG rendert, Balken sichtbar, Farben korrekt) passiert manuell im
Browser — Playwright/Selenium ist nicht installiert (eigener OP).

Verbotenes Verhalten:
- waterfall.js fehlt / hat keine Rollen-Farben
- Control-Modus blendet Timeline NICHT aus (Wasserfall unsichtbar)
- Farben als Hex-Code statt sem-Variablen
"""
from __future__ import annotations

from pathlib import Path


def _html() -> str:
    return Path("static/layout.html").read_text(encoding="utf-8")


def _css() -> str:
    return Path("static/layout.css").read_text(encoding="utf-8")


def _js() -> str:
    return Path("static/waterfall.js").read_text(encoding="utf-8")


def test_waterfall_js_existiert():
    js = _js()
    assert "WerkstattWaterfall" in js
    assert "/swimlane" in js
    assert "setInterval" in js


def test_waterfall_kennt_alle_rollen():
    js = _js()
    for rolle in ("explorer", "builder", "verify", "reviewer", "reflection", "loop"):
        assert f'"{rolle}"' in js, f"Rolle {rolle} fehlt"


def test_waterfall_keine_hex_farben():
    """sem-Variablen, kein Hex-Code im JS (OP-300-Konvention)."""
    js = _js()
    # Suche nach #RRGGBB oder #RGB in String-Literalen
    import re
    hex_matches = re.findall(r"[\"']#[0-9a-fA-F]{3,6}[\"']", js)
    assert not hex_matches, (
        f"waterfall.js darf keine Hex-Farben enthalten: {hex_matches[:3]}"
    )
    # Stattdessen: var(--sem-*)
    assert "var(--sem-" in js


def test_waterfall_two_signal():
    """Monoscope-Regel: Status nicht nur Farbe, auch Symbol."""
    js = _js()
    assert "\\u2713" in js or "\u2713" in js, "OK-Symbol fehlt"
    assert "\\u2717" in js or "\u2717" in js, "Fehler-Symbol fehlt"


def test_html_hat_wasserfall_bereich():
    """Wasserfall-Container im Cockpit (Nachanalyse)."""
    html = _html()
    assert 'id="control-waterfall"' in html
    assert 'class="bereich wasserfall-bereich"' in html
    assert 'data-bereich="wasserfall"' in html
    assert "/static/waterfall.js" in html


def test_css_cockpit_zeigt_wasserfall():
    """OP-381i-Nachtrag 2026-11-09: Wasserfall im Cockpit, nicht Control.

    Control bekommt Live-Feed (OP-381j). Grund: Wasserfall aggregiert
    nach Rolle, zeigt keine Reihenfolge -> ungeeignet fuer 'was laeuft
    jetzt?', gut fuer Nachanalyse.
    """
    css = _css()
    # Wasserfall-Bereich existiert
    assert ".wasserfall-bereich" in css
    # Im Control versteckt
    assert 'body[data-mode="control"] .wasserfall-bereich' in css
    # Cockpit-Grid hat 2 Rows
    assert "grid-template-rows" in css
    assert "wasserfall" in css


def test_css_pulse_accessible():
    """Puls-Animation respektiert prefers-reduced-motion."""
    css = _css()
    assert "prefers-reduced-motion" in css
    assert ".wf-pulse" in css


def test_balken_minimum_breite():
    """Balken >= 8px, damit auch 1s-Events sichtbar sind.

    Live-Bug 2026-11-09: min 2px war zu duenn bei 4min-Runs
    (1s-Event = 2px, nicht klickbar).
    """
    js = _js()
    assert "Math.max(8," in js, "Balken-Minimum muss 8px sein"


def test_fmt_tick_kompakt():
    """Tick-Labels kompakt: 42s statt 42.5s."""
    js = _js()
    assert "function _fmtTick" in js
    # keine 42.5s-Formatierung mehr in Ticks
    # Der Tick-Push nutzt _fmtTick, nicht _fmtDauer
    idx = js.find("_zeitTicks")
    assert idx > 0
    fenster = js[idx:idx + 800]
    assert "_fmtTick" in fenster
