"""Runs-Frontend: Loop-Status, Steuerung und Feedback."""
from pathlib import Path


def _js():
    return Path("static/runs.js").read_text(encoding="utf-8")


def _css():
    return Path("static/layout.css").read_text(encoding="utf-8")


def test_js_fetcht_run_status():
    js = _js()
    assert "/ops/run-status" in js
    assert "_rendere(ops, runStatus, loopControl)" in js or "_rendere(_letzteOps, rs, _loopControl)" in js


def test_js_hat_start_stop():
    js = _js()
    assert "_klickAktion" in js
    # Aktion ist Variable (start/stop), URL wird dynamisch gebaut
    assert '"start"' in js or "'start'" in js
    assert '"stop"' in js or "'stop'" in js
    assert '"pause"' in js or "'pause'" in js
    assert '"resume"' in js or "'resume'" in js
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

def test_blockierte_ops_haben_keinen_startknopf():
    js = _js()
    assert 'op.status === "open" && !op.blockiert_von' in js
    assert 'btn.disabled = true' in js
    assert 'btn.dataset.action = "blocked"' in js


def test_js_fetcht_loop_status_und_zeigt_aktionsfeedback():
    js = _js()
    assert 'base + "/loop"' in js
    assert 'setAttribute("aria-live", "polite")' in js
    assert "fehlgeschlagen:" in js
    assert "erfolgreich." in js


def test_css_hat_loop_control_bar():
    css = _css()
    assert ".runs-control" in css
    assert '.runs-action-btn[data-action="pause"]' in css
