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


def test_chat_job_status_unterscheidet_chatantwort_vom_loopauftrag() -> None:
    js = _chat_js()
    assert '"Chat-Antwort wird erstellt · läuft im Hintergrund."' in js
    assert '"Chat-Antwort abgebrochen."' in js
    assert '"Chat-Anfrage konnte nicht angenommen werden: "' in js


def test_chat_asset_urls_haben_einen_cache_bust() -> None:
    html = Path("static/layout.html").read_text(encoding="utf-8")
    assert re.search(r'/static/chat\.js\?v=[0-9]+', html)
    assert re.search(r'/static/live_feed\.js\?v=[0-9]+', html)
    assert "/static/chat.js?v=202611121845" not in html
    assert "/static/live_feed.js?v=202611121845" not in html


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
    assert 'kind === "loop_action_queued"' in js
    assert 'data.state === "queued"' in js
    assert '"Nicht gestartet · Ein Loop läuft bereits."' in js
    assert 'function _proposalKarte(proposal, status)' in js
    assert 'button.textContent = decision === "confirm" ? "Bestätigen" : "Ablehnen";' in js
    assert '"/chat/actions/"' in js
    assert 'kind === "loop_action_proposed"' in js
    assert 'proposal.task_preview' in js


def test_loop_action_card_renders_from_live_and_legacy_tool_results() -> None:
    js = _chat_js()
    assert 'function _verarbeiteLoopActionErgebnis(name, content)' in js
    assert '_verarbeiteLoopActionErgebnis(obj.name || "", obj.content || "")' in js
    assert '_verarbeiteLoopActionErgebnis(name, content)' in js
    assert '(data.action_proposals || []).forEach(function (proposal)' in js
    result_start = js.index("function _jobToolResult")
    result_end = js.index("function _jobFertig", result_start)
    result = js[result_start:result_end]
    assert "_verarbeiteLoopActionErgebnis(name, content);" in result
    assert result.index("_verarbeiteLoopActionErgebnis(name, content);") > result.index("for (var i")


def test_chat_surfaces_followup_checkpoint_receipt() -> None:
    js = _chat_js()
    assert 'kind === "loop_followup_checkpointed"' in js
    assert '"Aufgenommen · Einordnung ausstehend"' in js
    assert '_karte("assistant", p.detail' in js


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
    assert 'classList.toggle("is-working", status === "running")' in activity

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


def test_assistant_antworten_ohne_blase_nutzer_in_blase() -> None:
    css = _css()
    assert ".chat-nachrichten > .chat-msg.user {" in css
    assert "border-radius: 18px 18px 5px 18px;" in css
    assert ".chat-nachrichten > .chat-msg.assistant {" in css
    assert "background: transparent;" in css
    assert "body[data-mode=\"control\"] .bereich.chat .chat-nachrichten > .chat-msg.assistant" in css


def test_chat_composer_hat_einen_fokusrahmen_und_setzt_sich_zurueck() -> None:
    css = _css()
    js = _chat_js()
    focus_start = css.index(".chat-composer:focus-within {", css.rfind("/* Eingabe:"))
    focus_end = css.index("}", focus_start)
    focus_rule = css[focus_start:focus_end]
    assert "box-shadow: none;" in focus_rule
    assert 'eingabe.style.height = "auto";' in js[js.index('eingabe.value = "";'):js.index("_sende(text);", js.index('eingabe.value = "";'))]
    assert "resize: none;" in css[css.rfind("/* Eingabe:"):]


def test_assistant_text_bleibt_auf_lesbarer_spaltenbreite() -> None:
    css = _css()
    start = css.rindex("/* Assistant-Text bleibt linksbuendig und bekommt eine ruhige Lesebreite. */")
    regel = css[start:]
    assert "width: min(100%, 68ch);" in regel
    assert "max-width: 68ch;" in regel
    assert "margin-left: 0;" in regel
    assert "margin-right: auto;" in regel


def test_nutzer_bubble_rechtsbuendig_kompakt_ausrichten() -> None:
    css = _css()
    start = css.rindex("/* Nutzer-Bubbles rechtsbuendig halten und kompakt begrenzen. */")
    regel = css[start:]
    assert "align-self: flex-end;" in regel
    assert "max-width: min(64%, 68ch);" in regel
    assert "margin-right: 0;" in regel
    assert "margin-left: auto;" in regel
    assert "max-width: 92%;" in regel



def test_chat_replays_one_temporary_live_loop_activity() -> None:
    js = _chat_js()
    assert '"/api/projects/" + encodeURIComponent(projekt) + "/loop"' in js
    assert '"/live-feed?run_id="' in js
    assert 'node.className = "chat-msg assistant chat-loop-activity is-working"' in js
    assert "node.textContent = text" in js
    assert "_loopAktivitaetEntfernen();" in js
    assert "zustand.loopActivityGeneration" in js

    css = _css()
    assert ".chat-nachrichten > .chat-loop-activity {" in css
    assert "border-left: 2px solid var(--accent);" in css
