"""Prompt-Bau (Phase 2 / Gate 18, 2026-10-19).

Aus pipeline.py extrahiert (Befund BO/BP, Reviewer-A:
8 Funktionen, build_system_prompt bleibt in pipeline.py
wegen _anti_pattern_block-Anker).

Enthaelt:
- _build_judge_prompt
- _format_whitelist_block
- _bauer_recovery_prompt
- format_doc_snippets
- format_projekt_stand
- aufgabe_block
- formatiere_runden
- recovery_hinweis_block

Nicht hier (Phase 3b/6):
- build_system_prompt: ruft _anti_pattern_block.
- _anti_pattern_block: Phase 3b, Hooks ersetzen.

Siehe docs/NEUBAU-ENTFERNUNG.md.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import redaction
from werkstatt.hard_rules import HARD_RULES_BASE, HARD_RULES_JUDGE

if TYPE_CHECKING:
    from werkstatt.state import RunState


def formatiere_runden(review_runden: list[dict[str, Any]]) -> str:
    """Auflage 2183 A1a: formatiert review_runden.

    Liefert einen Block fuer den Reviewer-Prompt.
    Leerer String, wenn keine Runden vorhanden sind.
    Recovery-Runden erhalten den Marker RECOVERY.
    """
    if not review_runden:
        return ""
    zeilen = ["BISHERIGE RUNDEN:"]
    for r in review_runden:
        raw = r.get("raw", "")
        if len(raw) > 1500:
            raw = raw[:1500] + " [... gekuerzt ...]"
        mark = "RECOVERY - " if r.get("recovery") else ""
        zeilen.append(
            f"[ROUND {r['runde']} - {mark}{r['verdict']}]")
        zeilen.append(raw)
    return "\n".join(zeilen) + "\n\n"


def recovery_hinweis_block(
        review_runden: list[dict[str, Any]],
        hat_befund: bool = False) -> str:
    """Auflage 2183 A1a + Block 2a (W6/W7).

    Liefert den Block, wenn die letzte Runde recovery=True
    trug. Sonst leerer String.

    Kein Befund-Text mehr. Nur ein neutraler Hinweis,
    dass ein Solver-Befund existierte. Der Befund-Text
    geht an den Builder-Agenten (siehe _solver_befund_block).
    """
    if not review_runden:
        return ""
    if not review_runden[-1].get("recovery"):
        return ""
    if hat_befund:
        return (
            "## RECOVERY-RUNDE\n"
            "Diese Runde folgte auf einen Solver-Befund.\n"
            "Der Befund ist dem Builder-Agenten bekannt,\n"
            "nicht dir. Du bewertest das Ergebnis, nicht\n"
            "den Befund. Bewerte den Patch inhaltlich\n"
            "(R1-R7).\n"
            "Wenn der Patch den Solver-Befund nicht\n"
            "umsetzt, aber inhaltlich korrekt ist:\n"
            "Bewerte ihn trotzdem als korrekt.\n\n"
        )
    return (
        "## RECOVERY-RUNDE\n"
        "Dies ist eine Recovery-Runde ohne Solver-\n"
        "Befund. Pruefe den Code wie sonst (R1-R7).\n\n"
    )


def format_projekt_stand(state: RunState) -> str:
    """A2: formatiert den Projekt-Stand als Prompt-Block.

    Liefert "" wenn kein projekt_stand vorliegt (UU6).
    Max 5 Commits (UU8).
    """
    ps = state.projekt_stand or {}
    commits = ps.get("letzte_commits", [])
    if not commits:
        return ""
    zeilen = ["## PROJEKT-STAND (letzte Commits)"]
    for c in commits[:5]:
        h = c.get("hash", "")
        # datum kann datetime sein (yaml.safe_load).
        d = str(c.get("datum", ""))[:10]
        q = c.get("quelle", "")
        m = c.get("message", "")
        zeilen.append(f"- {h} ({d}, {q}) {m}")
        dateien = c.get("dateien", [])
        if dateien:
            zeilen.append(
                "  Dateien: " + ", ".join(dateien))
    zeilen.append("")
    return "\n".join(zeilen)


def _build_judge_prompt(state: RunState) -> str:
    """W28b2: baut den Judge-System-Prompt.

    Frischer Kontext: judge.md + HARD_RULES_BASE +
    HARD_RULES_JUDGE. Fallback auf reviewer, wenn
    judge fehlt.
    """
    agent = state.agents.get("judge")
    if agent is None:
        agent = state.agents.get("reviewer")
    if agent is None:
        return HARD_RULES_BASE + HARD_RULES_JUDGE
    body = agent.get("body", "")
    return (
        body + "\n\n"
        + HARD_RULES_BASE + "\n\n"
        + HARD_RULES_JUDGE)


def _format_whitelist_block(
        file_whitelist: list[str]) -> str:
    """Whitelist-Prompt-A2 (2026-10-16): zeigt die
    aktuelle file_whitelist im Prompt an.

    Damit sieht der Reviewer (und der Builder),
    welche Pfade freigegeben sind.
    """
    if not file_whitelist:
        return (
            "=== FILE-WHITELIST ===\n"
            "(keine Pfade freigegeben)\n"
            "=== /FILE-WHITELIST ===\n\n")
    return (
        "=== FILE-WHITELIST (erlaubte Pfade) ===\n"
        + "\n".join(file_whitelist)
        + "\n=== /FILE-WHITELIST ===\n\n")


def aufgabe_block(state: RunState) -> str:
    """Auflage 2154: zentrale Formatierung des Auftrags.

    Liefert "AUFGABE: <auftrag>\n\n". Wird in allen
    Reviewer- und Builder-Prompts verwendet, damit
    der Auftrag konsistent ist.
    """
    return f"AUFGABE: {state.aufgabe}\n\n"


def _bauer_recovery_prompt(state: RunState) -> str:
    """Post-Apply-Fix 2026-10-16: Prompt fuer die
    Builder-Korrektur-Runde nach Post-Apply-Basis-
    Gate-Fehler.

    Enthaelt:
      - Reviewer-Diagnose.
      - Reviewer-Reparaturplan.
      - Post-Apply-Basis-Gate-Protokoll.
      - Auftrag: korrigiere mit typ: patch.
    """
    v = state.letzter_recovery_vorschlag
    diagnose = ""
    reparaturplan = ""
    if v is not None:
        diagnose = getattr(v, "diagnose", "") or ""
        plan_liste = getattr(v, "reparaturplan", []) or []
        reparaturplan = "\n".join(
            f"  {i+1}. {p}" for i, p in enumerate(plan_liste))
        # A1 (2026-10-16): Fallback auf rohantwort.
        # ask_reviewer_for_recovery fuellt nur rohantwort
        # (Z. 4359), diagnose/reparaturplan bleiben leer.
        if not diagnose and not reparaturplan:
            _roh = getattr(v, "rohantwort", "") or ""
            _roh_red, _ = redaction.redact_all(
                _roh, max_len=100000)
            diagnose = _roh_red
    # A2 (2026-10-16): GEMESSENER INHALT (nach Apply)
    # vor den Reviewer-Text.
    _mess_nach = state.mess_protokoll_nach_apply or ""
    if not _mess_nach:
        _mess_nach = "(keine Messung nach Apply)"
    # WEG-X-P22a: Strukturierte Test-Ergebnisse.
    _test_block = ""
    if state.basis_gate_test_results:
        _teile: list[str] = []
        for _tr in state.basis_gate_test_results:
            _teile.append(
                f"--- {_tr['scope']} ---\n"
                f"  exit_code: {_tr['exit_code']}\n"
                f"  klassifizierung: "
                f"{_tr['klassifizierung']}\n"
                f"  failed: {_tr['failed_count']}, "
                f"passed: {_tr['passed_count']}\n"
                f"  failed_test_ids: "
                f"{_tr['failed_test_ids']}\n")
        _test_block = "\n".join(_teile)
    else:
        _test_block = "(keine strukturierten Test-Ergebnisse)\n"
    return (
        "=== POST-APPLY-BASIS-GATE ROT ===\n"
        "Die bereits angewendeten Patches haben das\n"
        "Basis-Gate (nach Apply) rot gemacht.\n\n"
        "GEMESSENER INHALT (nach Apply):\n"
        f"{_mess_nach}\n\n"
        f"Reviewer-Diagnose:\n{diagnose}\n\n"
        f"Reviewer-Reparaturplan:\n{reparaturplan}\n\n"
        "Basis-Gate-Protokoll (nach Apply, VOLL):\n"
        f"{state.basis_protokoll_nach_apply}\n\n"
        "STRUKTURIERTE TEST-ERGEBNISSE (nach Apply):\n"
        f"{_test_block}\n"
        "=== AUFTRAG ===\n"
        "Korrigiere die bereits angewendeten Patches.\n"
        "Die Dateien existieren jetzt - verwende\n"
        "typ: patch (NICHT typ: new_file).\n"
        "Liefere strukturierte Code-Patches im Format\n"
        "PATCH-BEGINN/PATCH-ENDE.\n"
    )


def format_doc_snippets(docs: dict[str, str],
                        max_len: int = 3000) -> str:
    """Auflage 2142: Ausschnitte aus den Doku-Dateien fuer den Builder.

    Der Builder braucht konkrete Anker-Texte aus den
    Zieldateien, um gueltige Doku-Patches zu bauen.
    Ohne diese Ausschnitte liefert er eine Rueckfrage
    (Befund S aus Probebetrieb 10).

    Pro Datei: max_len Zeichen Anfang. Redaction zuerst
    (Secrets-Schutz), max_len=100000 damit die Grenze
    nicht durch Redaction weiter gekuerzt wird.
    """
    if not docs:
        return "(keine Doku geladen)"
    teile = ["DOKU-AUSSCHNITTE (Auszug aus den Zieldateien):"]
    for key, inhalt in docs.items():
        total = len(inhalt)
        gekuerzt = total > max_len
        ausschnitt = inhalt[:max_len]
        ausschnitt, _ = redaction.redact_all(
            ausschnitt, max_len=100000)
        if gekuerzt:
            kopf = (
                f"--- {key} (Zeichen 1-{max_len} von {total}, "
                f"GEKUERZT) ---"
            )
        else:
            kopf = (
                f"--- {key} (Zeichen 1-{total} von {total}, "
                f"vollstaendig) ---"
            )
        teile.append(kopf)
        teile.append(ausschnitt)
        if gekuerzt:
            rest = total - max_len
            teile.append(
                f"\n[... AUSSCHNITT GEKUERZT. {rest} weitere "
                f"Zeichen. Fuer die vollstaendige Doku: "
                f"COMMAND: RUN read_file {key}]"
            )
    return "\n".join(teile)


