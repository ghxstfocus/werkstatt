# Werkstatt

Das Agenten-System. Unabhaengig von jedem Projekt. Es baut Projekte,
aber es gehoert keinem Projekt.

## Was ist das hier

Die Werkstatt enthaelt Rollen (Reviewer, Builder, Test-Generator,
Coverage, Chaos), eine Pipeline, die diese Rollen orchestriert, und
pro Projekt eine Konfiguration, die sagt, wo das Projekt liegt und
welche Doku es hat.

Der Reviewer ist der oberste Entscheidungstraeger in einem Block.
Der Mensch ist die letzte Instanz (Approval-Gate). Der Builder baut.
Die Werkstatt selbst trifft keine Entscheidungen — sie setzt um, was
der Reviewer entscheidet, und wartet an jedem schreibenden Schritt
auf den Menschen.

## Struktur

    /opt/werkstatt/
    ├── agents/                  Rollen-Definitionen (Markdown + YAML)
    │   ├── reviewer.md
    │   ├── builder.md
    │   ├── test_generator.md
    │   ├── coverage.md
    │   └── chaos.md
    ├── projects/                Projekt-Konfigurationen
    │   └── security-ai.yaml
    ├── tests/                   Tests der Werkstatt
    │   └── test_pipeline.py
    ├── pipeline.py              Orchestrierung
    ├── redaction.py             Redaction vor jedem LLM-Call
    ├── .gitignore
    └── README.md

## Aufruf

    cd /opt/<projekt>
    DEEPSEEK_API_KEY=sk-... \
      runuser -u <projekt-user> -- /opt/security-ai/.venv/bin/python3 \
      /opt/werkstatt/pipeline.py --project <name> "<Block-Beschreibung>"

Beispiel fuer Security AI:

    cd /opt/security-ai
    DEEPSEEK_API_KEY=sk-... \
      runuser -u security-ai -- /opt/security-ai/.venv/bin/python3 \
      /opt/werkstatt/pipeline.py --project security-ai "Punkt 58 Schritt 6"

## Ausfuehrungsregel

Die Pipeline darf NICHT als root laufen. Als root wuerden Audit-Logs
root:root gehoeren und der Service-User koennte sie nicht mehr lesen
(vgl. SECURITY_REVIEW_LOG Punkt 12). Als Guard ist im Code verankert:
aktueller User == "root" -> Exit 66.

Die Pipeline laeuft als Projekt-User (z. B. security-ai, xyapp).

## Was ein Block ist

Ein Block ist eine logische Einheit: eine Aufgabe, eine Pipeline-
Ausfuehrung, ein Approval, ein Commit. Nach dem Approval endet der
Lauf. Der naechste Block wird vom Menschen oder (spaeter) vom
Reviewer bestimmt.

Der Ablauf:

1. Basis-Gate (py_compile, ruff, mypy, test_count, git_status, git_head)
   laeuft immer. Wenn eines rot ist: Hard Fail, Block startet nicht.
2. Auto-Repair (nur deterministisch: ruff --fix, ruff format).
3. Reviewer waehlt optionale Messungen (COMMAND: RUN <id>).
4. Builder baut Code-Entwurf.
5. Review-Schleife: GO / NO-GO / ESKALATION.
6. Coverage + ggf. Test-Generator + Chaos-Agent.
7. Commit-Review (Phase 2): Prueft Commit-Message, Dateien, Doku-Patches.
8. Approval-Dokument mit vollstaendiger Reviewer-Argumentation.
9. Human-Gate: approve / reject / eskalation.
10. Commit (nur bei approve) mit Autor ghxstfocus.

## Sicherheit

- Kein shell=True. Argumentlisten.
- Whitelist-Katalog: nur was in always_run oder optional_catalog steht,
  darf ausgefuehrt werden. Unbekannte IDs: Ablehnung + Audit.
- read_file nur aus FILE_WHITELIST.
- Path-Traversal-Schutz.
- Redaction vor jedem LLM-Call (IPs, MACs, Keys, Prompt-Injection-Marker).
- Audit-JSONL pro Tag, jeder Eintrag mit project-Feld.
- Fail closed bei fehlender Konfiguration, fehlendem API-Key, unbekanntem
  Projekt.

## Was noch nicht fertig ist

- Approval-System (kommt, /opt/werkstatt/approvals/).
- Runner-Daemon (kommt, fuer Start aus dem Dashboard).
- Reviewer-Chat im Dashboard (kommt).
- Scaffolder (kommt, legt Projekt-Grundstock an).
- Der Reviewer wird spaeter auch "welcher Block als naechstes"
  entscheiden koennen.

## Rollen erweitern

Eine neue Rolle anlegen:

1. Datei `agents/<name>.md` schreiben. YAML-Frontmatter mit
   `name`, `description`, `model`, `temperature`. Danach
   Body mit Rolle, Aufgaben, Grenzen.
2. In `pipeline.py` bei Bedarf eine Aufrufstelle ergaenzen.

Die Hard Rules (HR1-HR10) sind im Rollen-Kern jedes Agenten
enthalten, nicht in der Projekt-Doku. Sie gelten in jedem Projekt.
