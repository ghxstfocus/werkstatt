"""OP-305: Projekt-Anlage API + Modal Frontend-Smoke."""
from pathlib import Path


def _html():
    return Path("static/layout.html").read_text(encoding="utf-8")


def _js():
    return Path("static/project_create.js").read_text(encoding="utf-8")


def _api():
    return Path("werkstatt/web/app.py").read_text(encoding="utf-8")


def test_endpoint_registriert():
    from werkstatt.web import app as web_app
    routes = [r.path for r in web_app.app.routes if hasattr(r, "path")]
    assert "/api/projects/create" in routes


def test_endpoint_hat_validation():
    src = _api()
    # Name-Regex, Pfad-Pflicht, mkdir, scaffold
    assert "_re.fullmatch" in src
    assert "startswith(\"/opt/\")" in src
    assert "Zielverzeichnis nicht leer" in src
    assert "scaffold(name, projekt_dir)" in src


def test_html_hat_modal():
    html = _html()
    assert 'id="project-create-overlay"' in html
    assert 'id="project-create-name"' in html
    assert 'id="project-create-pfad"' in html
    assert 'id="project-create-submit"' in html


def test_js_hat_api_call():
    js = _js()
    assert "/api/projects/create" in js
    assert "WerkstattTabs" in js


def test_js_hat_auto_pfad():
    js = _js()
    assert "_autoPfad" in js
    assert "/opt/" in js


def test_shift_n_zu_alt_n():
    """Der neue Shortcut ist Alt+N, nicht Shift+N (Chrome-Konflikt).

    e.shiftKey darf im Guard stehen (verhindert Shift+Alt+N), aber
    nicht im Match — sonst wäre es wieder Shift-basiert.
    """
    js = Path("static/utility_bar.js").read_text(encoding="utf-8")
    assert "e.altKey" in js
    # shiftKey darf NICHT der Trigger sein (kein "if (e.shiftKey)" ohne altKey)
    assert "if (!e.altKey" in js or "if (e.altKey" in js
