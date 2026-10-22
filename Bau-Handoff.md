# Bau-Handoff — Werkstatt

Stand: 2026-10-22 (Aufraeum-Block A, HEAD nach A4-a-2).
Werkstatt-HEAD: ede85cd. Branch: umbau/phase-2 (origin gepusht).
Baseline: pytest 1259 / ruff 16 / mypy 9 / AST 6 / Katalog 162.

Baseline-Definition (verbindlich, sonst reproduziert sich der 7-vs-9-Fehler):
- pytest:      `pytest -q`  (KEIN `python -m pytest` — Binary `python` fehlt)
- ruff:        `ruff check .`
- mypy:        `mypy pipeline.py werkstatt/`   (NICHT `mypy .` — tests/ zaehlt 40 Fehler)
- AST:         AST-Test, 6 passed
- Katalog:     `_KATALOG_SOLL` = 167

## Aktueller Block

3a-3 (_phase_main_pfad, 641 Z., Z. 10360-11000):
641 Z. / 43 Statements / 23 Returns / 5 Parameter.
Aufteilungs-Vorschlag in 3 Sub-Bloecke:
  3a-3a Vorlauf    (body[0]..[21], Z. 10360-10462, ~103 Z.)
  3a-3b Plan-Verarb.(body[22], Z. 10463-10632, ~170 Z.)
  3a-3c Planner-Loop (body[23]..[42], Z. 10635-11000, ~366 Z.)
Deadlock-Kette: 3x run_phase-Aufruf + phase_korrektur_zyklus-
Sicherung in 3a-3c (Vorab-Messung unten).
6 getsource-Tests (Kandidaten Kategorie 2).

Naechster konkreter Schritt: Reviewer-Start-Posting 3a-3
mit Aufteilungs-Vorschlag. Dann 3a-3a.

Rollback-Anker: 416550a. Delta != 0 -> Rollback.

## Abgeschlossen seit letztem Handoff

- 3a-1c-2b (W2-Extraktion): done (277029f + 74ff77d + ac4956f).
  _commit_review_w25_loop, 10 Parameter, Aufruf Z. 8811-8817.
- 3a-1c-3 (C0+C1+C2): done (da67198 + bb919d1 + d06cf23 + fafc5b5).
  _vorlauf_und_state + VorlaufErgebnis, _basis_gate.
- 3a-1c-4 (C8+C9): done (75f844b Handoff-Refresh, 5762d8e Code).
  _approval_und_human_gate (4 Parameter, 8 Returns).
  C8 = 8819-8854, C9 = 8855-8898. run_pipeline endet 8917.
  Return-Bilanz: 27/3/2/7/8 = 47.
  3 Test-Anpassungen (#1 test_phase.py:804, #5 test_pipeline.py:6324,
  #12 test_pipeline.py:8671) via duale Quelle/Split.
- 3a-2a (Vorlauf): done (20f0e7d).
  _phase_vorlauf(state, project_name) -> PhaseVorlaufErgebnis | int.
  Dataclass PhaseVorlaufErgebnis in werkstatt/state.py
  (state, unterbloecke, api_key, max_phase).
  if-state_ref-Guard bleibt in run_phase.
  Return-Bilanz: run_phase 17, _phase_vorlauf 7, Summe 24
  (+2 Extraktions-Artefakte gegen 22).
  Baseline 1245/17/9 unveraendert.
- 3a-2b (Loop): done (8e46062).
  _phase_unterblock_loop(state, project_name, unterbloecke,
  max_phase) -> int. 4 Parameter (Signatur-Freeze 18c).
  M-72-Fix: rc_unterblock = 0 Vor-Init + return rc_unterblock
  (Z. 2399 Klasse-4 + Z. 2400 Fallback).
  Return-Bilanz: 89 Returns (run_phase 13, loop 6).
  2 Test-Anpassungen (getsource -> _phase_unterblock_loop).
  Baseline 1245/17/9 unveraendert.
- 3a-2d (Wiederaufnahme): done (00ffb5e).
  _phase_wiederaufnahme(state, project_name, state_ref,
  aggregat, wahl, api_key) -> int. 6 Parameter.
  5 Returns. Rekursion max 1 Tiefe.
  Test-Anpassung test_zyklus_teilt_sich (erster Assert).
- 3a-2 GESAMT (20f0e7d + 8e46062 + 3f98364 + 00ffb5e):
  run_phase von 528 Z. / 22 Returns auf 4 Verteiler-Returns.
  4 neue Funktionen: _phase_vorlauf, _phase_unterblock_loop,
  _phase_nachlauf, _phase_wiederaufnahme.
  2 neue Dataclasses: PhaseVorlaufErgebnis, NachlaufErgebnis.
  Return-Bilanz: 87 -> 92 (Delta +5, Extraktions-Artefakte).
  Baseline 1245/17/9 durchgehend.
- C6 (Coverage/Chaos): gestrichen (Durchlauf 48, gehoert zu 3b).

## C8/C9-Grenzen-Korrektur (Reviewer-Auflage A1)

OFFENE-BLOECKE.md Z. 20 war FALSCH. Altes Zitat:
  "C8 Approval Schritt 6 (Z. 8762-8797) offen | C9 Human-Gate
   (Z. 8798-8841) offen"
Real gemessen (HEAD 5e50ea6, SCHRITT-Kommentare + AST):
  SCHRITT 5 (Commit-Review) = Z. 8660  -> C7 (done)
  SCHRITT 6 (Approval+Human-Gate) = Z. 8820 -> C8+C9
  C8 = Z. 8819-8854 (Approval-Dokument + Phasen-Paket-Sammlung)
  C9 = Z. 8855-8898 (Human-Gate, input(), Commit-Entscheidung)
  run_pipeline endet bei Z. 8898 (nicht 8841).
  Bereich 8762-8817 = C7-Rest, nicht C8.
Korrektur ist in docs/OFFENE-BLOECKE.md eingepflegt (Z. 20).

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

- docs/SESSION-BILANZ.md — M-57-Nachweise Body-VOR-Werte pro Commit.
- docs/MESS-INFRASTRUKTUR.md — Recherche und Einordnung Block M (Mess-Infrastruktur, nach 3a-2d vor 3a-3). Explorer-Subagent (W61) als Konsument.

- docs/OFFENE-BLOECKE.md — Todo, chronologisch nach Phasen.
- docs/OFFENE-BLOECKE-ARCHIV.md — Todos vor Umbau.
- docs/ERLEDIGT.md — abgeschlossene Bloecke.
- docs/ROADMAP.md — Phasen-Uebersicht (Stand 3a).
- docs/UEBERGABE-3A-2026-10-19.md — Phase-3a-Uebergabe (Stand
  2026-10-19, ueberholt; neuer Stand ist dieser Handoff).
- docs/NEUBAU-ZIELBILD.md, NEUBAU-INVENTAR.md, NEUBAU-ENTFERNUNG.md.
- docs/ARCHITEKTUR.md, KONVENTION.md, ROLLEN-AUDIT.md, IDEEN.md.

## Naechste Bloecke (Reihenfolge laut ROADMAP.md Z. 217-223)

1. 3a-3 (_phase_main_pfad, 641 Z., Deadlock) — naechster Block.
2. 3b (Loop-Umbau; enthaelt C6 + Reviewer-Modus + Quality-Gate).
3. 3c (NEUBAU-Abloesung).

## Offene Merkposten

- Werkstatt-Entkopplung von security-ai: UEBERFAELLIG laut
  OFFENE-BLOECKE.md Z. 19 (sollte nach 3a-1c-2b, vor 3a-1c-3
  erledigt sein). Kein Blocker fuer 3a-1c-4, aber zeitnah
  einsortieren. Nach 3a-1c-4 als eigenen Block einplanen.
- 3a-1c-2-V2-Groesse (OFFENE-BLOECKE.md Z. 29): V2 = 303 Z.,
  13 Steuerstellen, 12 Parameter. Zerlegung V2a/V2b vor 3b pruefen.
- Struktur-Tests umstellen: Rest-Klassifikation folgt in 3a-1c-4
  (Auflage 2).
- M-57 (Commit-Bezuege pro Body-VOR-Wert): offen aus der Runde
  vor diesem Handoff. Nachziehen vor Session-Abschluss.
- Commit-Body-Lehre (Z. 21): bei Commit-Body-Pruefung ZWEI
  Messungen — git-log-Chronologie + pytest --collect-only auf
  JEDEM Zwischenstand.

## Archiv

Vorheriger Handoff (2026-10-18, W52b) in Bau-Handoff-Archiv.md.
Vorgaenger-Handoff (2026-10-20, 3a-1c-2b "NO-GO") war ueberholt:
3a-1c-2b ist done, 3a-1c-3 ist done, C6 gestrichen.


## 3a-3 — Vorab-Messung (HEAD 416550a)

Gemessen am 2026-10-22. Dient als Startpunkt fuer den naechsten Block.
Naechster Kontext kann direkt hier ansetzen.

### _phase_main_pfad — Signatur + Zeilen

  def Z. 10360..11000 (641 Zeilen).
  positional: ['project_name', 'phasen_text', 'state_ref',
               'resume_force', 'force_new_phase']
  kw-only:    []
  Returns: 23.

### Aufrufer

  Intern:
    Z. 11386: rc = _phase_main_pfad(
    (einziger interner Aufrufer, in main()).
  Tests: 6 getsource-Ziele (siehe unten).

### Top-Level-Statements (43)

  Block A (Vorlauf, body[0]..[21], Z. 10360-10462, ~103 Z.):
    Docstring, api_key, project_dir, Baseline-Gate,
    agents_dir, load_agents, load_docs, file_whitelist,
    build_catalog, planner-config (modus, max_runden),
    plan_vorhanden-Try.

  Block B (Plan-Verarbeitung, body[22], Z. 10463-10632, ~170 Z.):
    if plan_vorhanden is not None:
    Enthaelt Plan-Parsing, Resume-Logik, Unterblock-Init,
    phase_start_head-Setzung, audit-Calls.

  Block C (Planner-Loop, body[23]..[42], Z. 10635-11000, ~366 Z.):
    historie, phase_yaml-Pfad, force_new_phase-Check,
    RunState-Anlage, run_id-Setzung, audit pipeline_start,
    for runde in range(1, planner_max_runden+1):
      -> Planner-Aufruf, run_phase-Aufruf (3x),
         phase_korrektur_zyklus-Sicherung.
    phase_plan_ok-Check, return 0.

### Rekursion + Deadlock-Stellen

  run_phase-Aufrufe in _phase_main_pfad:
    Z. 10617: rc = run_phase(project_name, state, state_ref)
    Z. 10629: rc = run_phase(project_name, state, state_ref)
    Z. 10931: rc = run_phase(
  phase_korrektur_zyklus-Sicherung:
    Z. 10621: if ... and state.phase_korrektur_zyklus < 1:
    Z. 10627: state.phase_korrektur_zyklus += 1
    Z. 10541: audit phase_korrektur_zyklus_vorher: 0

  Deadlock-Kette dreistufig (strukturell):
    run_phase -> _phase_wiederaufnahme -> run_phase
      (Rekursion in 3a-2d, max 1 Tiefe).
    _phase_main_pfad -> run_phase (3x)
      (Sicherung durch phase_korrektur_zyklus < 1
       in _phase_main_pfad Z. 10621).
    Doppelte Sicherung: run_phase-Rekursion UND
      _phase_main_pfad-Sicherung.

### getsource-Tests auf _phase_main_pfad

  tests/test_pipeline.py:7452  inspect.getsource(pipeline._phase_main_pfad)
  tests/test_pipeline.py:7463  inspect.getsource(pipeline._phase_main_pfad)
  tests/test_pipeline.py:7472  inspect.getsource(pipeline._phase_main_pfad)
  tests/test_phase.py:1383     ins.getsource(pipeline._phase_main_pfad)
  tests/test_phase.py:1591     ins.getsource(pipeline._phase_main_pfad)
  tests/test_phase.py:1600     ins.getsource(pipeline._phase_main_pfad)

  6 Kandidaten fuer Test-Anpassungen (Kategorie 2) bei
  Extraktion von Teilen aus _phase_main_pfad.

### Baseline

  pytest 1245 passed / ruff 17 / mypy 9 / AST 6 / Katalog 167.
  Delta 0.

### Aufteilungs-Vorschlag (3 Sub-Bloecke, analog 3a-2)

  Der Block ist mit 641 Z. / 43 Statements / 23 Returns
  zu gross fuer einen Schnitt. Drei natuerliche Sub-Bloecke:

  3a-3a: Vorlauf (body[0]..[21], Z. 10360-10462, ~103 Z.)
    api_key, project_dir, Baseline-Gate, agents, docs,
    file_whitelist, build_catalog, planner-config.
    Neue Funktion: _phase_main_vorlauf(...) -> PhaseMainVorlaufErgebnis | int.

  3a-3b: Plan-Verarbeitung (body[22], Z. 10463-10632, ~170 Z.)
    if plan_vorhanden is not None.
    Neue Funktion: _phase_main_plan_verarbeiten(...) -> ... | int.
    ODER als Teil von 3a-3a belassen (haengt von
    Variablen-Transfer ab, M-94).

  3a-3c: Planner-Loop (body[23]..[42], Z. 10635-11000, ~366 Z.)
    RunState, historie, for runde-Loop mit 3 run_phase-Aufrufen,
    phase_korrektur_zyklus-Sicherung, phase_plan_ok-Check.
    Neue Funktion: _phase_main_planner_loop(...) -> int.
    ODER weiter zerlegt (Loop-Body vs. Loop-Vorbereitung).

  Reihenfolge-Empfehlung: 3a-3a -> 3a-3b -> 3a-3c (wie 3a-2a/b/c/d).
  Deadlock-Analyse (M-65-Muster): vor 3a-3c, weil dort die 3
  run_phase-Aufrufe + phase_korrektur_zyklus-Sicherung liegen.

  Test-Anpassungen: 6 getsource-Tests. Kategorisierung pro Block
  im jeweiligen Start-Posting (a/b/c/d), wie bei 3a-2.

### Naechster Schritt (frische Session)

  1. Reviewer-Start-Posting 3a-3 mit Aufteilungs-Vorschlag.
  2. Nach Freigabe: 3a-3a (Vorlauf), dann 3a-3b, 3a-3c.
  3. 3a-3c: Deadlock-Analyse strukturell + phase_korrektur_zyklus
     zitieren (wie 3a-2d).

