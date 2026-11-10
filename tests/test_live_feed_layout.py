"""OP-394 Frontend-Layout: Steps oben, Aktiv+Naechster unten.

Der Test prueft per Source-Scan der static/live_feed.js, dass die
Reihenfolge im DOM-Aufbau korrekt ist (Steps vor Aktiv).
"""
from __future__ import annotations

from pathlib import Path


def _js() -> str:
    return Path("static/live_feed.js").read_text(encoding="utf-8")


def test_steps_vor_aktiv():
    """Steps werden VOR Aktiv-Block eingefuegt (oben Verlauf, unten Jetzt)."""
    s = _js()
    # Beide appendChild-Aufrufe muessen da sein
    assert "container.appendChild(stepsBox);" in s
    assert "container.appendChild(_renderAktiv(" in s
    # Position: stepsBox-Einfuegung VOR Aktiv-Einfuegung
    pos_steps = s.find("container.appendChild(stepsBox);")
    pos_aktiv = s.find("container.appendChild(_renderAktiv(")
    assert pos_steps > 0 and pos_aktiv > 0, "beide appendChild fehlen"
    assert pos_steps < pos_aktiv, (
        f"Steps ({pos_steps}) muessen VOR Aktiv ({pos_aktiv}) stehen"
    )


def test_auto_scroll_nach_aktiv():
    """Auto-Scroll ans Ende ist implementiert (Aktiv-Block bleibt sichtbar)."""
    s = _js()
    assert "_warUnten" in s, "Auto-Scroll-Marker fehlt"
    assert "container.scrollTop = container.scrollHeight" in s


def test_gerade_fertig_hat_haekchen():
    """gerade_fertig rendert Haekchen statt Spinner."""
    s = _js()
    assert "gerade_fertig" in s, "gerade_fertig-Branch fehlt"
    assert "lf-aktiv-fertig" in s, "CSS-Klasse fehlt im JS"
