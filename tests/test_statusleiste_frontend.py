"""Race guards fuer projektbezogene Statusanzeigen."""
from pathlib import Path


def test_statusleiste_verwirft_verspaetete_pollantworten():
    js = Path("static/statusleiste.js").read_text(encoding="utf-8")
    assert "var ladeGeneration = 0" in js
    assert "generation === ladeGeneration" in js
    assert "projektGeladen === aktuellesProjekt" in js
    assert "function zeige_uebersicht()" in js


def test_projection_statusleiste_zeigt_basis_zeitraum_und_unvollstaendigkeit():
    js = Path("static/statusleiste.js").read_text(encoding="utf-8")
    assert 'd.comparison_basis || "unbekannte Basis"' in js
    assert 'period.from + " bis " + period.to' in js
    assert 'el.textContent = "Proj: unvollständig"' in js
    assert 'd.sqlite_rows_outside_basis || 0' in js
    assert 'el.setAttribute("aria-label", details)' in js


def test_ambient_status_verwirft_verspaetete_pollantworten():
    js = Path("static/ambient_status.js").read_text(encoding="utf-8")
    assert "generation !== ladeGeneration" in js
    assert "projekt !== aktuellesProjekt" in js
    assert "delete el.dataset.runId" in js


def test_home_pausiert_projektbezogene_poller():
    tabs = Path("static/tabs.js").read_text(encoding="utf-8")
    assert '"WerkstattRuns", "WerkstattTimeline", "WerkstattWaterfall", "WerkstattLiveFeed"' in tabs
    for module in ("runs.js", "timeline.js", "waterfall.js", "live_feed.js"):
        js = Path("static", module).read_text(encoding="utf-8")
        assert "zeige_uebersicht" in js
