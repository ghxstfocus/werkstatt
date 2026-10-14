# Werkstatt

Das Agenten-System. Unabhaengig von jedem Projekt. Es baut Projekte,
aber es gehoert keinem Projekt.

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
    |   +-------------+    Auftrag    +-------------------+    |
    |   | Werkstatt-  |-------------->|      BUILDER      |    |
    |   |   Chat      |               |  (baut Patches)   |    |
    |   +-------------+               +-------------------+    |
    |         |                              |   ^             |
    |         | Reviewer-Block               v   | Befund      |
    |         v                       +-------------+          |
    |   +-------------+  NO-GO-Paar   |   SOLVER    |          |
    |   |  REVIEWER   |-------------->|  (Diagnose, |          |
    |   | (bewertet)  |               |   Skizze)   |          |
    |   +-------------+               +-------------+          |
    |         |                                                 |
    |         | GO / NO-GO / ESKALATION                         |
    |         v                                                 |
    |   +-------------+     +-------------+    +------------+   |
    |   | TEST-GEN    |     |  COVERAGE   |    |   CHAOS    |   |
    |   | (LLM)       |     |  (No-LLM)   |    |  (No-LLM)  |   |
    |   +-------------+     +-------------+    +------------+   |
    +----------------------------------------------------------+
                              |
                              v
                     Ziel-Projekt (z. B. security-ai)

## Die sechs Rollen

| Rolle           | Typ               | Adressat              | Aufgabe                          |
|-----------------|-------------------|-----------------------|----------------------------------|
| reviewer        | LLM (reasoner)    | das Ergebnis          | bewerten: GO/NO-GO/ESKALATION    |
| builder         | LLM (chat)        | Werkstatt-Chat, Solver| Code-Patches bauen               |
| solver          | LLM (chat)        | builder               | woran + wie besser (Skizze)      |
| test_generator  | LLM (chat)        | builder               | Test-Vorschlaege                 |
| coverage        | No-LLM            | —                     | Coverage messen                  |
| chaos           | No-LLM            | —                     | Extremwerte fuzzen               |

**reviewer** — prueft Code, Commit-Message, Doku. Waehlt Messungen.
Loest nicht. Schreibt nichts.

**builder** — baut Code-Patches und Commit-Paket. Baut bei NO-GO neu.
Baut bei zweimal NO-GO mit gleichem Gegenstand mit Solver-Befund.

**solver** — Unterstuetzung fuer den builder. Wird gerufen, wenn der
reviewer zweimal NO-GO gibt. Diagnostiziert: GLEICHER_FEHLER,
ANDERER_FEHLER, WIDERSPRUCH, UNKLAR. Empfiehlt, wie besser. Darf
Code als Skizze geben, keine fertigen Skripte. Bewertet nicht.
Adressat ist der builder, nicht der Mensch.

Der Solver-Befund geht in den Builder-Prompt (naechster Neubau).
Der Reviewer sieht nur einen neutralen Hinweis.

**test_generator** — Test-Vorschlaege bei niedriger Coverage.

**coverage, chaos** — No-LLM. Der Code ruft sie direkt.

## Struktur

    /opt/werkstatt/
    ├── agents/                  Rollen (Markdown + YAML)
    │   ├── reviewer.md
    │   ├── builder.md
    │   ├── solver.md
    │   ├── test_generator.md
    │   ├── coverage.md
    │   └── chaos.md
    ├── projects/                Projekt-Konfigurationen
    │   └── security-ai.yaml
    ├── tests/                   Tests der Werkstatt
    ├── docs/                    WORKFLOW, ROADMAP, PROTOKOLL
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
