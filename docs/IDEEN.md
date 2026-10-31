# Ideen — Werkstatt

Stand: 2026-10-18
Wunschliste. Kein Plan. Ein Punkt wird zum Auftrag, wenn
der Mensch ihn priorisiert. Erledigte Punkte markieren,
nicht loeschen.

## Ideen 2101-2106

### 2101 — Auto-Repair und Kategorie 3

- Frage (Architekt, 2026-10-12): soll der
  deterministische Auto-Repair (`ruff --fix`,
  `ruff format`) Kategorie-3-Dateien ausschliessen?
- Der Builder-Agent ist NICHT betroffen (er
  repariert nichts, er schlaegt vor).
- Betroffen ist nur `auto_repair_ruff`.
- Heute: `ruff --fix` laeuft ueber alle Dateien,
  keine Kategorie-Pruefung.
- Moegliche Loesung: `file_kategorie_3`-Liste in
  der Projekt-YAML, ruff --fix pro Pfad,
  Kategorie-3-Pfade ausgenommen.
- Erst nach Probebetrieb: messen, ob der
  Auto-Repair tatsaechlich Kategorie-3-Dateien
  anfasst.
- Wann: nach Probebetrieb.
- Kategorie: 3.

### 2102 — Auto-Repair-Markierung im Audit / Approval

- Wenn der Auto-Repair laeuft, wird das im Audit
  sichtbar, welche Dateien geaendert wurden.
- Vorschlag:
  - `auto_repair_ruff` liefert
    `git diff --name-only` (die geaenderten
    Dateien).
  - Audit-Feld erweitert:
    `{"ok": bool,
     "geaenderte_dateien": [...],
     "kategorie3_beruehrt": [...]}`.
  - Approval-Dokument zeigt Warnung bei
    Kategorie-3-Beruehrung.
- Klein, eigenstaendig.
- Wann: naechster Block.
- Kategorie: 2 (Transparenz).

### 2103 — Reviewer-Chat mit Zusammenfassung

- Die Approval-Seite zeigt nur die Kernpunkte.
  Details auf Abruf.
- Der Reviewer-Agent fasst zusammen, was zu
  approven ist.
- Der Nutzer kann interaktiv mit dem Reviewer
  sprechen.
- "Mach alle fertig" als Freigabe-Option.
- Wichtige Fragen vor Bau:
  - Was zeigt die Approval-Seite standardmaessig?
  - Was ist auf Abruf verfuegbar?
  - Wie wird "alle fertig" interpretiert?
  - Was ist die Mindestinformation, die der Nutzer
    gesehen haben muss?
  - Wie bleibt der Reviewer zustandslos, wenn er
    Dialog fuehren soll?
- Drei Varianten:
  - A) Approval-Seite mit Kernpunkten (klein, sofort).
  - B) Reviewer-Zusammenfassung zusaetzlich (mittel).
  - C) Reviewer-Chat mit Dialog (gross).
- Wann: nach Probebetrieb, eigener Block.
- Kategorie: 3.

### 2104 — Supervisor-Rolle

- Neue Rolle: `agents/supervisor.md`.
- Zweck: Ueberblick ueber Projekte und Bloecke.
  Entlastung des Reviewers.
- Nicht: Code-Review, Bauen, Tests. Nur
  Zusammenfassung.
- Zustandslos. Liest audit-logs/, TODO.md,
  Block-Status. Schreibt nichts.
- Nutzung: Block-Ende (kurze Zusammenfassung)
  + Dashboard (auf Abruf).
- Modell: deepseek-chat, Temperature 0.0.
- Rollen-Body muss klarstellen:
  keine Entscheidungen, kein Code-Review.
- Heute gibt es nur ein Ziel-Projekt (security-ai).
  Ein Supervisor hat heute nichts zu koordinieren.
- Wann: nach Probebetrieb, wenn mehrere Projekte
  parallel laufen.
- Kategorie: 3.

### 2105 — Datei-Namenskonvention fuer Ziel-Projekte

- Fuenf Pflicht-Dateien pro Ziel-Projekt:
  - `STATUS.md` — Wo stehen wir jetzt?
  - `TODO.md` — Was ist offen?
  - `DECISIONS.md` — Warum ist es so?
  - `REVIEW_LOG.md` — Was wurde geprueft?
  - `SECURITY_LOG.md` — Was ist sicherheitsrelevant?
- Optional:
  `ARCHITECTURE.md`, `DEPLOYMENT.md`,
  `CONTEXT_PROMPT.md`, `WORKFLOW.md`,
  modulspezifisch (z. B. `NTFY.md`).
- Keine Ueberschneidungen:
  - Offene Punkte NUR in TODO.md.
  - Sicherheitsrelevantes NUR in SECURITY_LOG.md.
  - Pruefergebnisse NUR in REVIEW_LOG.md.
  - STATUS/Phasen NIEMALS mit TODO vermischen.
- Anwendung:
  - Neue Ziel-Projekte: Standard.
  - security-ai: bleibt vorerst bei heutigen
    Namen. Migration spaeter.
- Werkstatt-Doku:
  - `docs/CONVENTIONS.md` (neu) mit vollstaendiger
    Konvention.
  - README kurzer Verweis.
- Wann: vor dem Scaffolder-Block.
- Kategorie: 1 (Werkstatt-Doku).

### 2106 — Scaffolder-Rolle mit Organizer-Modus

- Drei Modi:
  - Modus 1 (scaffold): neues Projekt anlegen.
    Deterministisch, kein LLM. Legt die 5 Pflicht-
    Dateien an. Erster Commit.
  - Modus 2 (organize): bestehendes Projekt
    umstrukturieren. LLM erzeugt Plan, Mensch
    prueft, Skript fuehrt aus.
  - Modus 3 (cleanup, optional): Ueberschneidungen
    finden und aufloesen. Wie Modus 2.
- Sicherheitsgrenzen:
  - Agent liest, schreibt NICHT. Nur Plan (Text).
  - Deterministisches Skript fuehrt aus.
  - Mensch zwischen Plan und Ausfuehrung.
  - `git tag` vor Migration.
  - `git diff` zur Nachpruefung.
  - `git revert` als Rueckrollung.
  - Keine inhaltlichen Aenderungen (nur
    verschieben, nicht umformulieren).
  - Inhalte ohne klare Zuordnung:
    `MIGRATION_NOTES.md` zur manuellen Pruefung.
- Kein unbeaufsichtigter Lauf. Kein Cron.
- Reihenfolge:
  1. 2105 (Konvention definieren).
  2. 2106 (Scaffolder + Organizer bauen).
  3. Migration security-ai (spaeter).
- Modul: `scaffolder.py` in der Werkstatt.
- Wann: nach 2105.
- Kategorie: 3.
