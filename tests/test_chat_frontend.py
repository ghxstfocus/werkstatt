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
