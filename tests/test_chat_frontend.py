"""Frontend-Vertrag fuer sichere, lesbare Chat-Markdown-Ausgabe."""
from pathlib import Path


def _chat_js() -> str:
    return Path("static/chat.js").read_text(encoding="utf-8")


def _css() -> str:
    return Path("static/layout.css").read_text(encoding="utf-8")


def test_assistant_nachrichten_werden_als_markdown_gerendert() -> None:
    js = _chat_js()
    assert "function _renderMarkdown(root, markdown)" in js
    assert 'if (rolle === "assistant") _renderMarkdown(k, text);' in js
    assert "_renderMarkdown(zustand.aktuelleKarte, voll || zustand.streamBuf);" in js


def test_markdown_renderer_verwendet_dom_und_keine_html_injektion() -> None:
    js = _chat_js()
    start = js.index("function _inlineMarkdown")
    ende = js.index("function _karte", start)
    renderer = js[start:ende]
    assert "document.createTextNode" in renderer
    assert "textContent" in renderer
    assert "innerHTML" not in renderer
    assert 'url.protocol === "http:" || url.protocol === "https:"' in renderer


def test_chat_typografie_trennt_fliesstext_und_code() -> None:
    css = _css()
    assert ".chat-nachrichten > .chat-msg" in css
    assert "font-family: var(--font-sans" in css
    assert ".chat-msg.assistant pre code" in css
    assert "font-family: var(--font-mono" in css


def test_chat_hydriert_aktiven_tab_beim_hard_reload():
    js = _chat_js()
    assert "zustand.initialisiert" in js
    assert 'document.querySelector(".tab.ist-aktiv")' in js
    assert "setze_chat(aktiverTab.dataset.projekt)" in js


def test_chat_eingabe_nutzt_ganze_composer_breite():
    css = _css()
    assert ".chat-composer { width: 100%; min-width: 0; }" in css
    assert "#chat-eingabe" in css
    assert "width: 100%;" in css
    assert "box-sizing: border-box;" in css
