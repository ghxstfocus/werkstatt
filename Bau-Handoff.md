# Bau-Handoff — Werkstatt

Stand: 2026-10-24 (Loop-Neubau Phase 1-18, HEAD c55c849).
Werkstatt-HEAD: c55c849. Branch: umbau/phase-2 (origin gepusht).
Baseline: pytest 1290 / ruff 13 / mypy 8 / AST 6 / Katalog 162.

## Loop-Neubau (Phase 1-17) — Status

**HEAD:** 134917d (Phase 17)

**Fertig:**
- Phase 1-2: Strangler-Fig + Gates (Copilot/Codex)
- Phase 3-4: Reflection-Loop (Aider)
- Phase 5: Planner-Agent (Codex Plan Mode)
- Phase 6: Builder-Agent (str_replace, Claude)
- Phase 7: Autonomer Task-Loop (Claude Code)
- Phase 8: Reviewer-Agent (Bug-Check)
- Phase 9: Reviewer im Loop
- Phase 10: PreToolUse + PostToolUse Hooks (Claude/Cursor/Grok)
- Phase 11: Simplify-Hook (Claude /simplify)
- Phase 13: PhaseState (Resume, Decisions, Failures)
- Phase 14: Explorer-Subagent (read-only, JSON)
- Phase 15: Multi-Projekt Verify-Contract (.werkstatt/verify.json)
- Phase 16: Projekt-Pfad-Aufloesung (load_project_config)
- Phase 17: Reviewer im Zielprojekt (Diff) + fail-closed Human-Gate

**Architektur:**
- Werkstatt = zentraler Runner.
- Zielprojekt = .werkstatt/verify.json (WIE verifizieren).
- Werkstatt/projects/<name>.yaml = project_dir (WO).
- Loop ruft: Explorer -> Planner -> Builder -> Hooks -> Reviewer -> Human.

**Baseline:** 1290 passed / 13 ruff / 8 mypy / 6 AST / 162 Katalog.

**Naechster Schritt:** Echter LLM-Test mit security-ai (Phase 14-17 testen).


## Aufraeum-Block A — Status

Siehe docs/AUFRAEUM-UND-LOOP-PLAN.md (Block A-E).
Phase 3a ist komplett (letzter Commit 6e440e6).

- **A1 (Audit-Kinds):** done (929a7e3). Katalog 167 -> 162.
- **A2 (subprocess):** 26/30 gekapselt (git + ruff).
  A2-4 (4 mess) wartet auf M-187 (Key-Env-Entscheid).
- **A3 (Skills):** done (76f4bf1). 14 neue Tests.
- **A4 (Config):** A4-a-1 (b84c3a1), A4-a-2 (c544308) done.
  A4-a-3 (42 config.get -> Properties) offen.
- **A5 (Builder kuerzen):** offen, wird durch A8 ersetzt.
- **A6 (HARD_RULES entdoppeln):** offen.
- **A7 (Doku):** A7-1 (103aac9), A7-2 (bab3150) done.
- **A8 (Trichotomie):** A8-1a-1 (7494ac4) done.
  A8-1a-2 blockiert bis A8-3 (Hooks, _anti_pattern_block).
  A8-1b (execute_commands) offen.
  A8-2 (Orchestrator) offen.
  A8-3 (Hooks) offen.
  A8-4 (CLI) offen.

## Naechster Block

**A8-1b (execute_commands aufteilen)** ODER
**A8-2 (Orchestrator, ~2.000 Z.)**.
Details: docs/AUFRAEUM-UND-LOOP-PLAN.md Block E.

Phase-Modus-Messung 2026-10-22:
  run_phase (75 Z.) + _phase_unterblock_loop (400 Z.)
  + _phase_main_pfad (50 Z.) + _phase_main_planner_loop (310 Z.)
  + Vorlauf (~400 Z.) + run_pipeline (660 Z.) = ~2.000 Z.
  Der Phase-Modus ruft run_pipeline pro Unterblock.
  Alle drei Loop-Ebenen (Block, Phase, Meta) gehoeren in
  werkstatt/orchestrator.py.

## Offene Merkposten

- **M-187 (Key-Env A2-4):** Auftraggeber-Entscheid offen.
- **M-194 (W36-Mock list|tuple):** offen, nicht blockierend.
- **M-203 Stufe 2 (Placeholder-Proxy):** spaeter.

## Top-5-Lehren (Kurzfassung)

Ausfuehrlich: docs/MERKPOSTEN.md, docs/SESSION-BILANZ.md.

1. **Messen vor jedem Block** (M-58 bis M-209). Kein Code-Touch
   ohne read-only Messblock. Zahlen aus Zitat.
2. **Return-Bilanz als Listen**, nicht Summen (M-70/M-73). Jeder
   Return mit Zeile + Wert.
3. **Semantik-Beweis bei Extraktion** (M-72). Jeder Return behaelt
   Wert und Bedingung.
4. **Marker-Zuordnung nur mit Repro** (M-142). Nicht Sichtpruefung.
   Erst "Test rot bei Entfernung", dann Klassifikation.
5. **Kandidaten-Erkennung vollstaendig** (M-202). `grep` nach allen
   String-Vorkommen, nicht nur `audit("literal")`. Kinds koennen
   dynamisch via Variable uebergeben werden.

Baseline-Gruen deckt diese Fehler NICHT auf. Der Messblock deckt
sie alle auf.

## Mess-Skripte — verbindliche Form

**Regel:** Messen vor jedem Block. Kein Code-Touch ohne vorherigen
read-only Messblock. Kein "wird schon passen" — jede Zahl und jede
Aussage muss aus einem Zitat stammen (ast, git show, grep, pytest).

**Form:** Ein Block, ein Skript. Nicht mehrere kleine Schnipsel,
sondern ein zusammenhaengender Bash-Block mit klaren Sektionen.
Diese Form hat sich in der Session 2026-10-21/22 bewaehrt (M-58 bis
M-75 aufgedeckt, Fehler verhindert).

### Sektionen-Struktur

  0) Zustand        HEAD, origin, Branch, Tree-Sauberkeit
  1..N) Messung /   je nach Block: Anker, Returns, state.X, Tests,
       Aenderung     Baseline, Diff, Commit, Push
  Baseline          pytest -q / ruff / mypy / AST / Katalog
  Commit-Entscheidung   bei Baseline-Gruen: Commit, sonst Warnung
  Read-Back         git show --stat + git log -1 + status
  FERTIG            "Bitte Ausgabe zuruecksenden"

### Haertung (Pflicht)

- `set -u` am Anfang (oder `set -eu`, wenn kein Fehlerpfad
  erwartet wird).
- `cd /opt/werkstatt || exit 1`.
- `python3` statt `python` (Binary `python` fehlt).
- `pytest -q` statt `python -m pytest`.
- ruff-Match: `grep -oE "Found [0-9]+ errors"`, NICHT
  `grep -q "Found 17 errors"` (die letzte Zeile ist die
  `[*] fixable`-Zeile).
- mypy: `mypy pipeline.py werkstatt/` (Baseline 9), NICHT `mypy .`
  (tests/ zaehlt 40 Fehler).
- AST- und Katalog-Test: `pytest tests/test_audit_kinds.py -q`
  (6 passed) + `_KATALOG_SOLL` = 167.

### Extraktion (Code-Touch)

- Wortwoertlich per `git show <ref>:pipeline.py` + Zeilenbereich.
  KEINE handgeschriebene Kopie (3a-2a-Versuch 1: 25 Tests kaputt).
- Loop-Selektor per Zeilenbereich oder Groesse, NICHT "erster
  for-Loop in node.body" (3a-2b-Versuch 1: falscher Loop).
- Neue Imports per `ast`-Sortierung einfuegen, nicht "nach letztem
  bekannten Feld" (I001).
- mypy-Fallback: `return 0` oder `return rc_unterblock` (semantisch
  korrekt), NICHT `raise RuntimeError` (killt Tests).
- Nach Extraktion: Return-Bilanz als Listen (M-70/M-73), Semantik-
  Beweis (M-72), Herkunft neuer Returns (M-74).

### Rollback

- NIE implizit `git reset --hard` im Skript, ausser als explizite
  Rollback-Funktion mit Grund.
- Vor jedem Reset: Arbeitsstaende nach `.werkstatt/tmp-<block>-<ts>/`
  sichern, wenn nicht-trivial.
- Baseline-Anker immer im Handoff nennen.

### Entscheidung

- Jeder Block endet mit **einer klaren Entscheidung**: Commit +
  Push, oder Warnung + Diff sichtbar lassen, oder Rollback mit
  Grund.
- Kein "vielleicht spaeter" — Zwischenstaende ohne Commit werden
  entweder korrigiert oder verworfen.

### Warum diese Form funktioniert

Die Werkstatt hat in 3a-1c-4 und 3a-2a/b mehrere Fehler gehabt, die
durch die Messbloecke aufgedeckt wurden, nicht durch Tests:

- M-58 (Return-Verteilung 3a-2d: 3 statt 2)
- M-59 (state.phase_korrektur_zyklus angeblich geteilt)
- M-60 (VorlaufErgebnis-Namenskonflikt)
- M-61/M-63 (Return-Zaehlung 3a-2c: 6 vs 7)
- M-62 (_phase_vorlauf 6 vs 7 Returns)
- M-64 (2 unkategorisierte Returns)
- M-65 (rc_unterblock-Herkunft)
- M-66 (Summe 22 vs 24)
- M-68 (run_phase vs run_pipeline verwechselt)
- M-72 (return 0 vs return rc_unterblock — Fail-open)
- M-74 (Herkunft 2399)

Baseline-Gruen (1245 Tests) hat KEINEN dieser Fehler aufgedeckt.
Der Messblock hat sie alle aufgedeckt. Deshalb: **Messen vor jedem
Block.**


## Verweise

- docs/INDEX.md — Doku-Einstieg (Diaetaxis: Tutorial, How-to,
  Reference, Explanation, ADR, Glossar).
- docs/AUFRAEUM-UND-LOOP-PLAN.md — Aufraeum- und Loop-Umbau-Plan
  (Block A-E; E = Pipeline-Trichotomie A8).
- docs/MERKPOSTEN.md — M-Nummern, chronologisch mit Lehre.
- docs/SESSION-BILANZ.md — M-57-Nachweise Body-VOR-Werte pro Commit.
- docs/HANDOFF-BASELINE.md — Baseline-Definition.
- docs/OFFENE-BLOECKE.md — Todo, chronologisch nach Phasen.
- docs/ERLEDIGT.md — abgeschlossene Bloecke.
- docs/ROADMAP.md — Phasen-Uebersicht.
- docs/KEY-ARCHITEKTUR.md — SOPS + age Setup.
- docs/adr/ — Architecture Decision Records.
- docs/NEUBAU-ZIELBILD.md, NEUBAU-INVENTAR.md, NEUBAU-ENTFERNUNG.md.
- docs/ARCHITEKTUR.md, KONVENTION.md, ROLLEN-AUDIT.md.
- AGENTS.md — Einstiegspunkt (Befehle, Struktur, Regeln).

## Archiv

Vorheriger Handoff (2026-10-22, 3a-3 komplett) im
Bau-Handoff-Archiv.md (Anhang).
Vorherige Uebergaenge (2026-10-18 W52b, 2026-10-20 3a-1c-2b
"NO-GO") sind ueberholt.
