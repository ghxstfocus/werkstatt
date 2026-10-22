# Bau-Handoff — Werkstatt

Stand: 2026-10-21 (Phase 3a, nach 3a-2a).
Werkstatt-HEAD: 20f0e7d. Branch: umbau/phase-2 (origin gepusht).
Baseline: pytest 1245 passed / ruff 17 / mypy 9 (isoliert) / AST 6 / Katalog 167.

Baseline-Definition (verbindlich, sonst reproduziert sich der 7-vs-9-Fehler):
- pytest:      `pytest -q`  (KEIN `python -m pytest` — Binary `python` fehlt)
- ruff:        `ruff check .`
- mypy:        `mypy pipeline.py werkstatt/`   (NICHT `mypy .` — tests/ zaehlt 40 Fehler)
- AST:         AST-Test, 6 passed
- Katalog:     `_KATALOG_SOLL` = 167

## Aktueller Block

3a-2b (Loop, run_phase Z. 2216-2404, 5 Returns): naechster
Block. M-61 (Return-Zaehlung 3a-2c vs 3a-2d) parallel
klaeren — blockierend nur fuer 3a-2c/d, nicht fuer 3a-2b.

Rollback-Anker: 20f0e7d. Delta != 0 -> Rollback, nicht Test anpassen.

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

1. 3a-2b (Loop, Z. 2216-2404, 5 Returns) — naechster Block.
2. 3a-2c (Nachlauf, Z. 2406-2524, 6 Returns; M-61-Klaerung noetig).
3. 3a-2d (Wiederaufnahme+Commit, Z. 2525-2574, 3 Returns).
4. 3a-3 (_phase_main_pfad, 641 Z., Deadlock).
5. 3b (Loop-Umbau; enthaelt C6 + Reviewer-Modus + Quality-Gate).
6. 3c (NEUBAU-Abloesung).

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
