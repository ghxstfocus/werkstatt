"""OP-301 Frontend-Smoke: HTML-IDs, Icons, JS, Polling, Chat-Naming."""
from pathlib import Path


def _html():
    return Path("static/layout.html").read_text(encoding="utf-8")


def _js():
    return Path("static/ambient_status.js").read_text(encoding="utf-8")


def test_html_hat_alle_ambient_ids():
    html = _html()
    for eid in (
        "ambient-bar", "ambient-loop", "ambient-last-run",
        "ambient-tokens", "ambient-gates",
        "ambient-token-loop", "ambient-token-chat", "ambient-token-sep",
    ):
        assert f'id="{eid}"' in html, f"ID fehlt: {eid}"


def test_js_existiert_und_pollt():
    js = _js()
    assert "setInterval" in js
    assert "/ambient" in js


def test_icons_vorhanden():
    html = _html()
    assert "\u21bb" in html, "Loop-Icon fehlt"
    assert "\u25c6" in html, "Chat-Icon fehlt"


def test_chat_benennung_nicht_assistent():
    """UI sagt 'Chat', nicht 'Assistent' (Verwirrung vermeiden)."""
    html = _html()
    assert "Assistent" not in html, "UI darf nicht 'Assistent' sagen"


def test_loop_bei_0_ausblendbar():
    js = _js()
    assert "loopEl.hidden" in js
    assert "chatEl.hidden" in js


def test_kein_kindisches_emoji():
    html = _html()
    assert "\U0001F916" not in html
    assert "\U0001F4AC" not in html
