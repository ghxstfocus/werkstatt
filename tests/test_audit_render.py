"""OP-301+: Audit-Renderer (Icons, Kategorie, State, Grid)."""
from pathlib import Path


def _js():
    return Path("static/audit.js").read_text(encoding="utf-8")


def _css():
    return Path("static/layout.css").read_text(encoding="utf-8")


def test_icon_helper_vorhanden():
    js = _js()
    assert "function _icon(" in js
    assert "function _kategorie(" in js
    assert "function _state(" in js


def test_icon_farben_aus_sem():
    css = _css()
    assert '.audit-history-zeile[data-kat="loop"] .audit-icon' in css
    assert "--sem-active" in css
    assert "--sem-action" in css
    assert "--sem-error" in css
    assert "--sem-ok" in css


def test_audit_kind_nicht_mehr_badge():
    """Badge-Hintergrund weg — keine accent-dim an .audit-kind-Regeln."""
    import re
    css = _css()
    # Kein accent-dim-Hintergrund mehr an .audit-kind*
    treffer = re.findall(r'\.audit-kind[^-a-z][\s\S]{0,200}accent-dim', css)
    assert not treffer, f"accent-dim noch an .audit-kind: {len(treffer)}x"
    assert ".audit-kind-mini" in css


def test_grid_ein_zeilig():
    css = _css()
    assert "grid-template-columns: 46px 18px 1fr 160px" in css


def test_gruppierung_existiert():
    js = _js()
    assert "audit-run-gruppe" in js
    assert "_zeileBauen" in js


def test_expand_existiert():
    js = _js()
    assert "expanded" in js
    css = _css()
    assert ".audit-history-zeile.expanded .audit-detail" in css


def test_zeit_kurzformat():
    """Zeit wird auf HH:MM reduziert."""
    js = _js()
    assert "_zeitKurz" in js
    # JS-Regex: /T(\d{2}:\d{2})/ — als raw-string pruefen
    import re
    m = re.search(r'/T\(\\d\{2\}:\\d\{2\}\)/', js)
    assert m, "Regex /T(\\d{2}:\\d{2})/ nicht in JS"
