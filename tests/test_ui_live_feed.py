"""OP-381j Frontend: Live-Feed im Control-Modus.

Source-Scan-Tests. Verhaltens-Verifikation manuell im Browser.
"""
from __future__ import annotations

from pathlib import Path


def _html() -> str:
    return Path("static/layout.html").read_text(encoding="utf-8")


def _css() -> str:
    return Path("static/layout.css").read_text(encoding="utf-8")


def _js() -> str:
    return Path("static/live_feed.js").read_text(encoding="utf-8")


def test_html_hat_live_feed():
    html = _html()
    assert 'id="control-live-feed"' in html
    assert 'data-bereich="live-feed"' in html
    assert "/static/live_feed.js" in html


def test_js_kennt_alle_rollen():
    js = _js()
    for rolle in ("explorer", "builder", "architect", "reflection", "loop"):
        assert f'"{rolle}"' in js, f"Rolle {rolle} fehlt"


def test_js_keine_hex_farben():
    import re
    js = _js()
    hex_matches = re.findall(r"[\"']#[0-9a-fA-F]{3,6}[\"']", js)
    assert not hex_matches, (
        f"live_feed.js darf keine Hex-Farben enthalten: {hex_matches[:3]}"
    )
    assert "var(--sem-" in js


def test_js_zwei_signal():
    """Monoscope-Regel: Status nicht nur Farbe, auch Symbol."""
    js = _js()
    assert "\\u2713" in js or "\u2713" in js, "OK-Symbol fehlt"
    assert "\\u2717" in js or "\u2717" in js, "Fehler-Symbol fehlt"


def test_css_control_modus_zeigt_live_feed():
    """Im Control-Modus: Timeline weg, Live-Feed sichtbar."""
    css = _css()
    assert 'body[data-mode="control"] .bereich.timeline' in css
    assert 'body[data-mode="control"] .live-feed-bereich' in css
    assert ".control-live-feed" in css
    assert ".lf-aktiv" in css
    assert ".lf-step" in css


def test_css_aktiv_puls_accessible():
    css = _css()
    assert "prefers-reduced-motion" in css
    assert "lf-aktiv-pulse" in css


def test_js_pollt_und_reagiert_auf_mode():
    js = _js()
    assert "setInterval" in js
    assert "/live-feed" in js
    assert "werkstatt:mode-change" in js

def test_js_renders_curated_timeline_details_safely():
    js = _js()
    assert 'document.createElement("details")' in js
    assert 'step.decision_summary' in js
    assert 'step.result_summary' in js
    assert 'step.next_step' in js
    assert 'step.task_name' in js
    assert 'Array.isArray(step.evidence)' in js
    assert 'item.textContent = beleg' in js
    assert "details.innerHTML" not in js
