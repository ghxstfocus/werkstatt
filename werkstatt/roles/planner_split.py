"""Independent LLM worker for converting Architect prose into a task graph.

The run coordinator supplies one already-budgeted, role-specific prompt packet.
This module cannot retrieve files, call Scout/Architect, or mutate the run plan;
it returns only the Planner-Split response for deterministic validation by the
coordinator.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from hashlib import sha256

PLANNER_SPLIT_SYSTEM = """Du bist ein Task-Zerleger.
Du bekommst den Originalauftrag, eine Architect-Prosa und eine Liste von Dateien.
Leite aus Originalauftrag und Prosa die beobachtbaren Abnahmekriterien fuer
das Gesamtziel ab. Uebernimm explizite Kriterien aus STATUS/ADR; erfinde keine
nicht geforderten Produktanforderungen. Kriterien muessen spaeter durch Tests,
Datei-/API-Verhalten oder explizite Doku-Inhalte pruefbar sein.
Zerlege die Prosa in so viele Sub-Tasks wie noetig (typisch 3-10).
Nicht mehr, nicht weniger als die Aufgabe braucht.

Jeder Sub-Task:
- id: "t1", "t2", ... (aufsteigend)
- name: kurzer Titel (< 50 Zeichen)
- action: "create" | "update" | "read" | "verify"
  - "create": neue Datei anlegen
  - "update": bestehende Datei aendern
  - "read": Task liest nur, aendert KEINE Datei
  - "verify": Task prueft einen Zustand, aendert KEINE Datei.
    `task_files` nennt die zu pruefenden Dateien, `description`
    sagt WAS geprueft wird.
  Hinweis: Verifikations-Aufgaben (nur pruefen, nichts aendern)
  bevorzugt als "verify" klassifizieren. Der deterministische
  Pre-Check im Planner ist die harte Garantie, nicht der Prompt.
- task_files: Liste der Dateien, die dieser Sub-Task aendert
  (max 1 Datei pro Task, wenn moeglich)
- architect_start: ERSTE Zeile des Architect-Abschnitts,
  der zu diesem Task gehoert (woertliches Zitat, z.B. "5. Backup").
  FUER __init__.py-Tasks: verwende den exakten Schritt, z.B.
  "15. In __init__.py: __all__ alphabetisch sortieren".
- architect_ende: LETZTE Zeile des Architect-Abschnitts
  (woertliches Zitat, z.B. "6. Anwenden").
  WICHTIG: architect_start und architect_ende muessen BENACHBARTE
  nummerierte Schritte sein (max 3 Schritte dazwischen).
  Wenn ein Task nur 1 Schritt umfasst, setze start = ende.
- dependencies: Liste von Task-IDs, die vorher fertig sein muessen.
- criterion_refs: Liste der IDs "AC1", "AC2", ... aus der Gesamtplan-Liste.
  Jeder Task muss mindestens ein Kriterium referenzieren; zusammen muessen
  die Tasks jedes Kriterium abdecken. Keine IDs erfinden oder auslassen.
  WANN setzen (Pflicht): Konsequenz-Tasks (Baseline senken, Doku
  die Endzustand prueft, Cross-Role-Tests, Ghost-Entfernung in
  mehreren Dateien) MUESSEN dependencies auf alle Tasks setzen,
  die den Vorbedingungs-Zustand veraendern. Reine Datei-Tasks
  ohne Vorbedingung: leere Liste [].

Gesamtplan:
- akzeptanzkriterien: Liste beobachtbarer Abnahmekriterien fuer den
  Originalauftrag. Nutze den exakten JSON-Schluessel "akzeptanzkriterien".
- Mindestens ein Kriterium, sofern der Auftrag ein veraenderbares Ziel
  enthaelt. Reine Analyseauftraege bekommen Kriterien fuer Belege und
  Ergebnisumfang. Kriterien aus dem Auftrag duerfen nicht still entfallen.

Regeln:
  - INTERFACE-GRENZE: Jede Task liefert EIN vollstaendiges,
    reviewbares Interface — nicht einen Schritt einer Funktion.
    Beispiel GUT: eine Funktion/Methode komplett (Eingabepruefung,
    Kernlogik, Fehlerbehandlung, Rueckgabe) als EINE Task.
    Beispiel SCHLECHT: Eingabepruefung / Kernlogik / Fehler-
    behandlung als getrennte Tasks fuer dieselbe Funktion.
  - Groesse: 50-150 Zeilen Code pro Task. Zu klein (< 30 Zeilen):
    Reviewer sieht kein Feature. Zu gross (> 200 Zeilen):
    Semantik geht verloren.
  - Eine Datei mit N unabhaengigen Funktionen/Klassen:
    EINE Task pro Einheit, nicht pro Schritt.
  - Eine Datei mit EINER Funktion/Klasse: EINE Task fuer die
    ganze Einheit — nicht in Schritte aufteilen.
  - Keine Test-Dateien (tests/*).
  - DOKU-AUFGABEN: Wenn die Prosa AUSSCHLIESSLICH
    Markdown-Dateien (docs/*.md, README.md) aendert und
    KEINEN Python-Code nennt: Erzeuge GENAU EINEN Task fuer
    die genannte Markdown-Datei. Keine Code-Tasks aus
    Symbolen, die in der Prosa nur als "schon erledigt" oder
    "bereits vorhanden" erwaehnt werden. Beispiel: Prosa sagt
    "in docs/DECISIONS.md Abschnitt 2 praezisieren, kein
    Python-Code" -> Task t1 mit task_files=["docs/DECISIONS.md"],
    action="update", architect_start/ende aus der Prosa.
  - architect_start und architect_ende MUESSEN woertlich in
    der Architect-Prosa vorkommen. Der Loop extrahiert dann
    den Text dazwischen.

Antworte NUR mit JSON:
{
  "akzeptanzkriterien": ["beobachtbares, pruefbares Kriterium"],
  "tasks": [
    {"id": "t1", "name": "...", "action": "update",
     "task_files": ["..."], "architect_start": "...",
     "architect_ende": "...", "dependencies": [],
     "criterion_refs": ["AC1"]},
    ...
  ]
}
Keine Erklaerung, nur JSON."""

PLANNER_SPLIT_SINGLE_SYSTEM = """Du bist ein Task-Zerleger.
Du bekommst EINEN zu grossen Sub-Task (Description > 2000 Zeichen
oder vom Builder als zu gross gemeldet).
Zerlege ihn in 2-3 kleinere Sub-Tasks.

Jeder Sub-Task:
- id: "tN_a", "tN_b", ... (abgeleitet von der Original-ID)
- name: kurzer Titel (< 50 Zeichen)
- action: "update" oder "create"
- task_files: Liste der Dateien (max 1)
- architect_start: ERSTE Zeile des Architect-Abschnitts (woertlich)
- architect_ende: LETZTE Zeile (woertlich, benachbart zu start)
- dependencies: Liste von Task-IDs
- criterion_refs: Erhalte die parent criterion_refs. Verteile sie auf
  die passenden Sub-Tasks; die Gesamtdeckung darf nicht verloren gehen.

Regeln:
  - Jede Sub-Task liefert ein vollstaendiges, reviewbares
    Interface (nicht einen Schritt). Max 3 Sub-Tasks.
  - Groesse: 50-150 Zeilen Code pro Sub-Task.
  - architect_start und architect_ende MUESSEN woertlich
    in der Architect-Prosa vorkommen.

Antworte NUR mit JSON:
{
  "tasks": [
    {"id": "...", "name": "...", "action": "update",
     "task_files": ["..."], "architect_start": "...",
     "architect_ende": "...", "dependencies": []},
    ...
  ]
}
Keine Erklaerung, nur JSON."""



@dataclass(frozen=True)
class PlannerSplitInput:
    """Narrow, hash-bound input contract for one Planner-Split call."""

    api_key: str
    system_prompt: str
    user_prompt: str
    state: object | None
    context_manifest: dict[str, object]


@dataclass(frozen=True)
class PlannerSplitOutput:
    """Raw role response; the caller owns parsing and task-graph validation."""

    ok: bool
    content: str = ""
    error: str = ""


def build_context_manifest(
    *,
    system_prompt: str,
    user_prompt: str,
    key_files: list[str],
    source_evidence: dict[str, object],
    source_context: str,
    sections: list[dict[str, object]],
    scope: str = "task_graph",
    task_id: str | None = None,
) -> dict[str, object]:
    """Fingerprint the exact Planner-Split payload and its evidence packet."""
    manifest: dict[str, object] = {
        "budget_event": "planner_split_context_budget",
        "user_sha256": sha256(user_prompt.encode("utf-8")).hexdigest(),
        "system_sha256": sha256(system_prompt.encode("utf-8")).hexdigest(),
        "scope": scope,
        "system_chars": len(system_prompt),
        "user_chars": len(user_prompt),
        "required_context_complete": True,
        "key_files": key_files[:50],
        "source_evidence": source_evidence,
        "source_evidence_sha256": (
            sha256(source_context.encode("utf-8")).hexdigest()
            if source_context else None
        ),
        "sections": sections,
    }
    if task_id is not None:
        manifest["task_id"] = task_id[:120]
    return manifest


def run_planner_split_role(
    request: PlannerSplitInput,
    *,
    ask_llm_call: Callable[..., object],
    spinner_call: Callable[[str, Callable[[], object]], object],
) -> PlannerSplitOutput:
    """Run only Planner-Split against its explicit prompt and return its reply.

    Runtime state is passed separately for the existing call ledger and exact
    request replay. It is never used to construct or enlarge the role prompt.
    """
    system_prompt = request.system_prompt
    user_prompt = request.user_prompt
    manifest = request.context_manifest
    expected = {
        "system_sha256": sha256(system_prompt.encode("utf-8")).hexdigest(),
        "user_sha256": sha256(user_prompt.encode("utf-8")).hexdigest(),
        "system_chars": len(system_prompt),
        "user_chars": len(user_prompt),
        "scope": manifest.get("scope"),
        "required_context_complete": True,
    }
    scope = manifest.get("scope")
    if scope not in {"task_graph", "single_task"}:
        return PlannerSplitOutput(
            ok=False,
            error="planner_split_scope_invalid",
        )
    if scope == "single_task" and not isinstance(manifest.get("task_id"), str):
        return PlannerSplitOutput(
            ok=False,
            error="planner_split_task_id_missing",
        )
    if any(manifest.get(key) != value for key, value in expected.items()):
        return PlannerSplitOutput(
            ok=False,
            error="planner_split_input_manifest_mismatch",
        )

    reply = spinner_call(
        "Planner-Split",
        lambda: ask_llm_call(
            request.api_key,
            system_prompt,
            user_prompt,
            model="deepseek-chat",
            temperature=0.2,
            max_tokens=8000 if scope == "task_graph" else 4000,
            aufgabe="planner-split",
            state=request.state,
            context_manifest=manifest,
        ),
    )
    if not getattr(reply, "ok", False):
        return PlannerSplitOutput(
            ok=False,
            error=str(getattr(reply, "error", "provider_call_failed")),
        )
    content = getattr(reply, "content", "")
    if not isinstance(content, str) or not content.strip():
        return PlannerSplitOutput(ok=False, error="empty_role_response")
    return PlannerSplitOutput(ok=True, content=content.strip())
