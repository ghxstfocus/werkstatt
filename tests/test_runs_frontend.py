"""OP-303 Frontend-Smoke: runs.js run-status + Start/Stop."""
from pathlib import Path


def _js():
    return Path("static/runs.js").read_text(encoding="utf-8")


def _css():
    return Path("static/layout.css").read_text(encoding="utf-8")


def test_js_fetcht_run_status():
    js = _js()
    assert "/ops/run-status" in js
    assert "_rendere(ops, runStatus)" in js or "_rendere(_letzteOps, rs)" in js


def test_js_hat_start_stop():
    js = _js()
    assert "_klickAktion" in js
    # Aktion ist Variable (start/stop), URL wird dynamisch gebaut
    assert '"start"' in js or "'start'" in js
    assert '"stop"' in js or "'stop'" in js
    assert '"/" + aktion' in js or "'/'" in js or 'aktion' in js


def test_js_pollt_5s():
    js = _js()
    assert "5000" in js


def test_css_hat_badge_und_button():
    css = _css()
    assert ".runs-run-badge" in css
    assert ".runs-action-btn" in css
    assert '.runs-action-btn[data-action="stop"]' in css


def test_css_hat_running_state():
    css = _css()
    assert '.runs-eintrag[data-run-state="running"]' in css


def test_pfeil_und_stop_symbole():
    js = _js()
    # Play U+25B6, Stop U+25A0
    assert "\\u25b6" in js or "\u25b6" in js
    assert "\\u25a0" in js or "\u25a0" in js


