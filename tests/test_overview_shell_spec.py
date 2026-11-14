"""UI-Vertrag fuer die Workspace-Overview (OP-306b)."""
from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_leerer_tab_storage_oeffnet_werkstatt_uebersicht():
    tabs = _read("static/tabs.js")
    html = _read("static/layout.html")
    assert "if (_gespeicherte.length === 0) {" in tabs
    assert "_zeigeUebersicht();" in tabs
    assert 'id="overview-screen"' in html
    assert 'id="projekt-workspace" hidden' in html


def test_home_navigation_laesst_projekttabs_erhalten():
    tabs = _read("static/tabs.js")
    assert 'homeBtn.addEventListener("click", _zeigeUebersicht)' in tabs
    assert "function _zeigeProjektbereich()" in tabs
    assert "window.WerkstattTabs.oeffne_projekt(name)" in _read("static/overview.js")
    assert "function oeffne_projekt(name)" in tabs


def test_overview_zeigt_run_donut_projektkarten_und_weekly_ranking():
    html = _read("static/layout.html")
    js = _read("static/overview.js")
    backend = _read("werkstatt/web/inspector.py")
    for element_id in ("overview-outcomes", "overview-project-bars",
                       "overview-projects", "overview-top-projects"):
        assert f'id="{element_id}"' in html
    assert "function renderDonut(data)" in js
    assert "function renderProjects(projects)" in js
    assert '"runs_7d_total": runs_7d_total' in backend
    assert '"ergebnisse_30d": gesamt' in backend


def test_overview_verwendet_dom_apis_fuer_projektnamen():
    js = _read("static/overview.js")
    assert "textContent" in js
    assert "innerHTML" not in js


def test_overview_hat_alle_bereiche_und_leerzustand():
    html = _read("static/layout.html")
    js = _read("static/overview.js")
    assert 'id="overview-week-title"' in html
    assert 'id="overview-outcomes"' in html
    assert "Noch keine Werkstatt-Projekte gefunden." in js
    assert "Erstes Projekt anlegen" in js


def test_overview_script_laedt_vor_der_tab_initialisierung():
    html = _read("static/layout.html")
    assert html.index("/static/overview.js") < html.index("/static/tabs.js")


def test_karte_zeigt_runquote_ops_sparkline_und_last_run():
    js = _read("static/overview.js")
    for field in ("runs_30d", "runs_30d_total", "erfolgsquote_30d",
                  "ops_offen", "letzter_run"):
        assert field in js


def test_projektstatus_und_run_outcomes_sind_semantisch_ausgezeichnet():
    css = _read("static/layout.css")
    js = _read("static/overview.js")
    for state in ('data-state="running"', 'data-state="done"',
                  'data-state="failed"'):
        assert state in css
    assert ".overview-donut-success" in css
    assert ".overview-donut-failed" in css
    assert ".overview-donut-aborted" in css
    assert ".overview-donut-unverified" in css
    assert ".overview-project-bar .unverified" in css
    assert '"Herkunft ungeklärt"' in js


def test_starting_state_blockiert_doppelte_startbuttons():
    runs = _read("static/runs.js")
    assert 'control.state === "starting"' in runs
    assert "Loop startet …" in runs
