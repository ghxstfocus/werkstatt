# Werkstatt

Das Agenten-System. Unabhaengig von jedem Projekt. Es baut Projekte,
aber es gehoert keinem Projekt.

**Ziel:** Das Beste aus Claude Code, Copilot, AutoGen, Swarm und
OpenAI Agents SDK nehmen und ein eigenes Agentensystem bauen.

Kernprinzip: **On-Demand-Messung.** Der Agent entscheidet
selbst, welche Datei er liest, basierend auf der aktuellen
Aufgabe. Kein Pre-Loading des ganzen Repos. Vorbilder:
Claude Code (Read vor Edit), Copilot (Tool Search),
Cursor (semantische Suche), AutoGen (RAG bei Bedarf).
Details: `docs/ARCHITEKTUR.md` Abschnitt 4.7.

**Stand 2026-10-18:**

- Werkstatt: 1166 Tests, ruff 0, mypy 0. HEAD 0df062f.
- security-ai: 1452 Tests. Phase 20a committet (manuell, 560659a).
- Phase 20b (ChangeApplier Audit-Log) offen — Pipeline deadlockt.
  W59 (Read-vor-Edit, Deadlock-Mechanismus) ist der naechste Block.
- 18 Commits vor origin/main.

**Doku:**

- `docs/ARCHITEKTUR.md` — Ziel, Rollen, was funktioniert, was fehlt.
- `docs/OFFENE-BLOECKE.md` — tabellarisch, mit Prioritaet.
- `docs/ROLLEN-AUDIT.md` — Rollen-Stand 2026-10-18 (Update-Sektion 8).
- `docs/WORKFLOW.md` — Pipeline-Ablauf im Detail.
- `Bau-Handoff.md` — aktueller Stand, naechster Schritt.

## Auf einen Blick

    +----------------------------------------------------------+
    |                        MENSCH                             |
    |                  (letzte Instanz, Human-Gate)             |
    +----------------------------------------------------------+
                              |  ^
                              v  |
    +----------------------------------------------------------+
    |                        WERKSTATT                          |
    |                                                           |
    |   +-------------+  Phasenplan   +-------------+          |
    |   |   PLANNER   |-------------->|   BUILDER   |          |
    |   | (Stufe 1/2) |               |(baut Patch) |          |
    |   +-------------+               +-------------+          |
    |                                        |   ^             |
    |                                        v   | Befund      |
    |                                +-------------+           |
    |                                |   SOLVER    |           |
    |                                |  (Diagnose) |           |
    |                                +-------------+           |
    |                                        |                 |
    |                                        v                 |
    |   +-------------+  Contract     +-------------+          |
    |   |    JUDGE    |<--------------|  REVIEWER   |          |
    |   | (pro Patch) |               | (Commit)    |          |
    |   +-------------+               +-------------+          |
    |                                        |                 |
    |                                        v                 |
    |   +-------------+     +-------------+    +------------+   |
    |   | TEST-GEN    |     |  COVERAGE   |    |   CHAOS    |   |
    |   | (LLM)       |     |  (No-LLM)   |    |  (No-LLM)  |   |
    |   +-------------+     +-------------+    +------------+   |
    +----------------------------------------------------------+
                              |
                              v
                     Ziel-Projekt (z. B. security-ai)

## Die sieben Rollen

| Rolle           | Typ               | Adressat              | Aufgabe                          |
|-----------------|-------------------|-----------------------|----------------------------------|
| planner         | LLM (chat)        | builder               | Auftrag (St.1) / Phasenplan (St.2) |
| builder         | LLM (chat)        | Werkstatt-Chat, Solver| Code-Patches bauen               |
| solver          | LLM (chat)        | builder               | woran + wie besser (Skizze)      |
| judge           | LLM (reasoner)    | den Patch             | Contract-Treue, Sicherheit       |
| reviewer        | LLM (reasoner)    | das Commit-Paket      | COMMIT-GO / COMMIT-NO-GO         |
| test_generator  | LLM (chat)        | builder               | Test-Vorschlaege                 |
| coverage, chaos | No-LLM            | —                     | Coverage messen / fuzzen         |

**planner** — formuliert Auftraege (Stufe 1) oder Phasenplaene
(Stufe 2) aus dem Projektzustand. Vorgeschalteter Agent, laeuft
vor Basis-Gate und Builder. Messe-Pflicht vor Planformulierung.

**builder** — baut Code-Patches und Commit-Paket. Baut bei NO-GO
neu. Bei zweimal NO-GO mit gleichem Gegenstand mit Solver-Befund.

**solver** — Unterstuetzung fuer den builder. Wird gerufen, wenn
der judge zweimal NO-GO gibt oder der Builder nicht weiterkommt.
Diagnostiziert: GLEICHER_FEHLER, ANDERER_FEHLER, WIDERSPRUCH,
UNKLAR. Empfiehlt, wie besser. Darf Code als Skizze geben, keine
fertigen Skripte. Adressat ist der builder, nicht der Mensch.
Der Solver-Befund geht in den Builder-Prompt (naechster Neubau).
Der Reviewer sieht nur einen neutralen Hinweis.

**judge** — prueft den angewendeten Patch gegen den Contract.
Frischer Kontext: contract.md, mess_nach.txt, test_results.
Verdict: GO / NO_GO / ESKALATION. Pro Patch im Unterblock.

**reviewer** — prueft das Commit-Paket (Message, betroffene
Dateien, git diff). Verdict: COMMIT-GO / COMMIT-NO-GO /
COMMIT-ESKALATION. Am Phasenende. Waehlt Messungen. Loest
nicht, schreibt nichts.

**test_generator** — Test-Vorschlaege bei niedriger Coverage.

**coverage, chaos** — No-LLM. Der Code ruft sie direkt.

## Struktur

    /opt/werkstatt/
    ├── agents/                  Rollen (Markdown + YAML)
    │   ├── planner.md           Planner (Stufe 1/2)
    │   ├── builder.md           Builder (Patches)
    │   ├── solver.md            Solver (Diagnose)
    │   ├── judge.md             Judge (Contract)
    │   ├── reviewer.md          Reviewer (Commit)
    │   ├── test_generator.md    Test-Vorschlaege
    │   ├── coverage.md          Coverage (No-LLM)
    │   └── chaos.md             Chaos (No-LLM)
    ├── projects/                Projekt-Konfigurationen
    │   └── security-ai.yaml
    ├── werkstatt/               Modularisierte Teile (W31-W47)
    │   ├── state.py             RunState, Measurement
    │   └── parser.py            Plan-Parser
    ├── tests/                   Tests der Werkstatt
    ├── docs/                    ARCHITEKTUR, ROLLEN-AUDIT,
    │                            OFFENE-BLOECKE, WORKFLOW
    ├── audit-logs/              JSONL pro Tag
    ├── pipeline.py              Orchestrierung
    ├── redaction.py             Redaction vor LLM-Calls
    ├── Bau-Handoff.md           Einstieg fuer neue Bau-Chats
    └── README.md

## Aufruf

    set -a
    . /opt/<projekt>/.env
    set +a
    cd /opt/<projekt> && \
    runuser -u <projekt-user> -- env DEEPSEEK_API_KEY="$DEEPSEEK_API_KEY" \
      /opt/<projekt>/.venv/bin/python3 \
      /opt/werkstatt/pipeline.py \
      --project <name> \
      "<Block-Auftrag>"

Laeuft NIE als root (Exit 66). Laeuft als Projekt-User (z. B. builder).

## Was ein Block ist

Ein Block: eine Aufgabe, eine Pipeline-Ausfuehrung, ein Approval,
ein Commit. Nach dem Approval endet der Lauf.

    1. Basis-Gate       py_compile, ruff, mypy, test_count,
                        git_status, git_head. Rot = Hard Fail.
    2. Auto-Repair      nur deterministisch (ruff --fix, format).
    3. Reviewer         waehlt optionale Messungen.
    4. Builder          baut Code-Patches.
    5. Review-Schleife  GO / NO-GO / ESKALATION.
                        - NO-GO: Builder baut neu.
                        - 2x NO-GO, gleicher Gegenstand:
                          Solver diagnostiziert -> Builder.
                          Reviewer sieht neutralen Hinweis.
    6. Coverage         + ggf. Test-Generator + Chaos.
    7. Commit-Review    prueft Commit-Paket. Quelle: GEMESSENER
                        INHALT NACH APPLY.
    8. Approval         Reviewer-Argumentation.
    9. Human-Gate       approve / reject / eskalation.
   10. Commit           nur bei approve, Autor ghxstfocus.

## Probebetrieb

Ein Probebetrieb ist NUR ein echter Pipeline-Durchlauf
(pipeline_start + pipeline_ende im Audit-Log, Projekt security-ai).
Manual-Sessions werden NICHT getaggt.

Tags probebetrieb-N liegen im Ziel-Repo (security-ai).

## Sicherheit

- Kein shell=True. Argumentlisten.
- Whitelist-Katalog (always_run, optional_catalog). Unbekannte
  IDs: Ablehnung + Audit.
- read_file nur aus FILE_WHITELIST. Path-Traversal-Schutz.
- Redaction vor jedem LLM-Call. Private IPs bleiben (Auflage 2195).
- Audit-JSONL pro Tag mit project und run_id.
- Fail closed bei fehlender Konfiguration, fehlendem API-Key,
  unbekanntem Projekt.

## Was noch nicht fertig ist

- Solver-Wissensbasis (Block 3): Solver sieht noch nicht dieselbe
  Projekt-Doku wie der Reviewer.
- Solver-Loop (Block 5): heute einmal pro Trigger, geplant 3 Runden.
- Werkstatt-Vertrag: Anker, Auftrag, Patch, Fail, Rollen.
- Approval extern (Datei, Telegram, Dashboard).
- Runner-Daemon.
- Reviewer-Chat im Dashboard.
- Scaffolder.

## Rollen erweitern

1. `agents/<name>.md`: YAML-Frontmatter (name, description, model,
   temperature) + Body (Rolle, Aufgaben, Grenzen, Adressat).
2. In `pipeline.py`: `HARD_RULES_<ROLLE>` + Eintrag in
   `HARD_RULES_BY_ROLE`.
3. Bei Bedarf Aufrufstelle ergaenzen.

Hard Rules in pipeline.py: `HARD_RULES_BASE` (HR1, HR7-HR10),
`HARD_RULES_REVIEWER`, `HARD_RULES_BUILDER`,
`HARD_RULES_TEST_GENERATOR`, `HARD_RULES_SOLVER`.
`build_system_prompt` waehlt anhand des Agent-Namens.
