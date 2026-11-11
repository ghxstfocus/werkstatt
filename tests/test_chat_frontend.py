"""Frontend-Vertrag fuer sichere, lesbare Chat-Markdown-Ausgabe."""
import re
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


def test_session_history_renders_completed_background_turn_pairs() -> None:
    js = _chat_js()
    assert 'kind === "job_turn"' in js
    assert 'p.user_text || ""' in js
    assert 'p.assistant_text || ""' in js


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

def test_reconnect_renders_failed_background_jobs() -> None:
    js = _chat_js()
    start = js.index("function _resumeChatJobs")
    ende = js.index("function _sende", start)
    resume = js[start:ende]
    assert 'item.state === "failed" || item.state === "cancelled"' in resume
    assert re.search(r'_jobFertig\(\s*job,\s*item\.state,\s*""', resume)
    assert "if (aktiveJobs)" in resume

def test_job_polling_is_scoped_to_chat_session() -> None:
    js = _chat_js()
    assert '"?session_id=" + encodeURIComponent(job.sessionId)' in js


def test_chat_can_cancel_background_jobs_without_blocking_composer() -> None:
    js = _chat_js()
    html = Path("static/layout.html").read_text(encoding="utf-8")
    assert 'abbrechenBtn.id = "chat-abbrechen"' in js
    assert '"/cancel"' in js
    assert "function _abbrechenAktiveJobs()" in js
    assert 'state === "cancelled"' in js
    assert 'id="chat-eingabe"' in html



def test_chat_renders_explicit_loop_action_confirmation_card() -> None:
    js = _chat_js()
    assert 'kind === "loop_action_not_started"' in js
    assert '"Nicht gestartet · Ein Loop läuft bereits."' in js
    assert 'function _proposalKarte(proposal, status)' in js
    assert 'button.textContent = decision === "confirm" ? "Bestätigen" : "Ablehnen";' in js
    assert '"/chat/actions/"' in js
    assert 'kind === "loop_action_proposed"' in js
    assert 'proposal.task_preview' in js


def test_selected_debug_mode_is_forwarded_as_debugger_capability():
    js = _chat_js()
    assert 'function _chatRequestMode()' in js
    assert 'uiMode === "debug" ? "debugger" : "read"' in js
    assert 'session_id: sid, message: text, mode: _chatRequestMode()' in js
    assert 'mode: _chatRequestMode(),' in js

def test_welcome_copy_matches_available_loop_capabilities() -> None:
    js = _chat_js()
    assert "startet keine Runs und ändert keinen Code" not in js
    assert "Loop-Aktionen anfordern" in js
    assert "zur Bestätigung." in js
    assert "Code-Patches direkt aus dem Chat sind noch nicht verfügbar." in js






def test_chat_shows_one_temporary_activity_message_and_keeps_tools_out_of_chat() -> None:
    js = _chat_js()
    start = js.index("function _jobAktivitaetStatus")
    end = js.index("function _updateProposalStatus", start)
    activity = js[start:end]
    assert 'card.textContent = text' in activity
    assert 'job.toolCalls.push({name: name || "?", done: false})' in activity
    assert 'createElement("li")' not in activity
    assert 'classList.add("is-working")' in activity

    result_start = js.index("function _jobToolResult")
    result_end = js.index("function _jobFertig", result_start)
    result = js[result_start:result_end]
    assert 'createElement("details")' not in result
    assert 'if (name === "request_loop_action")' in result
    assert 'kind === "tool_call"' not in js[js.index("events.forEach"):js.index("if (!hatNachricht)")]


def test_chat_replaces_activity_with_final_answer_and_has_no_activity_spinner() -> None:
    js = _chat_js()
    start = js.index("function _jobFertig")
    end = js.index("function _handleJobEvent", start)
    finish = js[start:end]
    assert "_renderMarkdown(job.assistantCard, finalText)" in finish
    assert "job.assistantCard.remove()" in finish
    css = _css()
    assert ".chat-msg.assistant.is-working::before" in css
    assert "animation: chat-pulse" not in css
    assert ".chat-activity" not in css


def test_debugger_fix_proposal_shows_hash_and_exact_diff() -> None:
    js = _chat_js()
    assert "proposal.arguments.debugger_fix" in js
    assert '"SHA-256 · "' in js
    assert "diff.textContent = debuggerFix.diff" in js
