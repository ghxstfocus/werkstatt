# Merkposten — chronologisch, mit Lehre

Stand: 2026-10-22. Diese Datei sammelt Merkposten (M-Nummern), die
aus konkreten Fehlern im Bau-Prozess entstanden sind — mit der
jeweiligen Lehre. Ziel: derselbe Fehler passiert nicht zweimal.

Abgenommene Merkposten bleiben hier (nicht in OFFENE-BLOECKE.md
verschoben), weil sie Prozess-Lehren sind, keine Todos.

## Aus 3a-2a (Vorlauf, 20f0e7d)

### M-70 — Return-Bilanz als Listen, nicht als Summen
Commit-Body-Pflicht. Wer eine Funktion extrahiert, zaehlt die
Returns ALLER betroffenen Funktionen und dokumentiert sie
vollstaendig mit Zeile + Wert. Summen ("89 Returns") sind kein
Ersatz, weil sie Zuordnungsfehler verdecken.

### M-73 — Return-Listen im Commit-Body
Verschaerfung von M-70. Der Commit-Body MUSS die Listen enthalten,
nicht nur "vollstaendig im Body" behaupten. Sonst ist die Abnahme
nicht pruefbar.

### M-71 — Prognose-Korrektur explizit deklarieren
Wenn die gemessene Return-Zahl von der Prognose abweicht: Delta
begruenden, nicht stillschweigend korrigieren. Beispiel 3a-2b:
Prognose 88, gemessen 89, +1 durch zwei rc_unterblock-Returns
(Klasse-4 + Erfolgs-Fallback).

### M-72 — Semantik-Aequivalenz belegen, nicht behaupten
"1:1 zum Original" ist eine Behauptung. Beweis: Zitat der
Original-Zeilen + AST-Diff der Returns. Bei 3a-2b war "return 0"
ein Fail-open (maskiert rc-Werte 5/9/11/18/20/21), erst der Fix
auf "return rc_unterblock" mit Vor-Init war semantisch 1:1.

### M-74 — Herkunft neuer Returns pruefen
Bei Extraktion: Woher kommt jeder Return in der neuen Funktion?
Original (Zeile zitieren) oder neu eingefuehrt (begruenden)?
3a-2b: Z. 2399 = Original (ab6f4cd Z. 2430), Z. 2400 = neu
(ex-return-0, mypy-Fallback).

### M-75 — Commit-Body-Pflichten VOR Push erfuellen
Wenn der Reviewer Commit-Body-Pflichten formuliert: pruefen, ob
sie erfuellt sind, BEVOR gepusht wird. Sonst Amend (aendert SHA),
nicht neu committen (unnoetige History).

## Aus 3a-2b (Loop, 8e46062)

### Prozess-Lehre — `return 0` statt `raise RuntimeError`
mypy "Missing return statement" im Loop-Body: `return 0` als
Fallback ist semantisch korrekt (Erfolgs-Pfad). `raise
RuntimeError` killt 19 Tests, weil der Pfad erreichbar ist.

### Prozess-Lehre — Loop-Selektor per Groesse oder Zeilenbereich
"Erster for-Loop in node.body" ist falsch, wenn mehrere Loops
existieren. 3a-2b: zwei Loops in run_phase (Z. 2242-2430
Unterblock, Z. 2508-2524 Approval). Selektor:
`stmt.lineno < 2400 < stmt.end_lineno` oder
`(stmt.end_lineno - stmt.lineno) > 100`.

### Prozess-Lehre — Wortwoertliche Extraktion per `git show`
Handgeschriebene Kopie des Loop-Bodys = 25 Tests kaputt (3a-2a
Versuch 1). Wortwoertliche Extraktion per `git show <ref>:pipeline.py`
+ Zeilenbereich = 0 Verhaltensdelta.

### Prozess-Lehre — Import-Sortierung per `ast`
Neue Imports nicht "nach letztem bekannten Feld" einfuegen, sondern
alphabetisch sortiert. Sonst I001-Fehler (ruff).
Beispiel 3a-2a: PhaseVorlaufErgebnis nach RecoveryVorschlag
statt davor.

## Aus dem Prozess (Session-Regeln)

### Tooling
- `python` fehlt auf dem System. `python3` verwenden.
- `pytest` als Entry-Point (`/usr/bin/pytest`), nicht `python -m pytest`.
- `ruff check .` — Match auf `Found [0-9]+ errors` (mit `grep -oE`),
  nicht auf die letzte Zeile (`[*] fixable …`).
- `mypy pipeline.py werkstatt/` ist die Baseline, nicht `mypy .`
  (tests/ zaehlt 40 Fehler).
- AST- und Katalog-Test: `pytest tests/test_audit_kinds.py -q` (6 passed)
  + `_KATALOG_SOLL` = 167. "AST+Katalog 14" ist Summen-Konvention,
  kein Messwert.

### Doku-Disziplin
- Nach jedem fertigen Block: Doku-Nachzug (Bau-Handoff, ROADMAP,
  ERLEDIGT, OFFENE-BLOECKE) + Push. Sonst sammelt sich Rueckstand.
- Commit-Body-VOR-Werte brauchen Vor-Comm-SHA (M-57).
- SESSION-BILANZ.md nachziehen, wenn neue Commit-Body-VOR-Werte
  auftauchen.

### Merkposten-Hygiene
- Merkposten sofort eintragen, nicht erst am Session-Ende
  (M-57-Lehre: muehsam rekonstruiert).
- M-Nummern monoton, keine Wiederverwendung.
- Abgenommene Merkposten mit Status + Commit vermerken.

## Verweise

- docs/HANDOFF-BASELINE.md — kanonische Messbefehle.
- docs/SESSION-BILANZ.md — Vor-Comm-SHAs pro Commit.
- docs/OFFENE-BLOECKE.md — offene Todos.
- docs/MESS-INFRASTRUKTUR.md — Block M (Mess-Werkzeuge).


## Aus 3a-2c/3a-2d (2026-10-22)

### M-94 — Variablen-Transfer bei Extraktion
Vor dem Code-Touch pruefen: welche Variablen definiert
der zu extrahierende Block, welche werden in nachfolgenden
Statements gelesen? Zitat pro Variable (Zeile + Definition).
Beispiel 3a-2d: aggregat @ 2575, wahl @ 2576, state_ref
@ 2616/2618/2639, api_key @ 2551. Ohne Transfer-Check
NameError wie bei 3a-2c (M-83).

### M-95 — HEAD-Bezug der body-Indizes
body[i]-Zaehlungen sind HEAD-abhaengig. Nach jeder
Extraktion verschieben sich die Indizes. Im Commit-Body
explizit: "body[14]..[19] gegen HEAD 3f98364" statt
nur "body[14]..[19]".

### M-96 — Off-by-N in Zeilen-Zitaten
Zitat "return 23 @ 2596" war Off-by-6 (Pruefzeile 2596,
Return 2602). Bei jedem Return-Zitat: Zeile der
Pruefbedingung UND Zeile des Returns getrennt zitieren.

### M-97 — Return-Listen VOR als Listen
M-70/M-73 gilt auch fuer den VOR-Stand. "run_phase 8
Returns, _phase_nachlauf 7 Returns" ist keine Liste.
Erst "Z. 2549: _vl, Z. 2558: _rc_loop, ...".

### M-98 — api_key-Herkunft pruefen
"api_key @ 2606 (nur _phase_plan_korrektur)" ist
Behauptung. Signatur der aufgerufenen Funktion pruefen:
_phase_plan_korrektur(project_name, state, api_key) ->
3. Positionsargument -> api_key bleibt Parameter.

### M-99 — state_ref-Vorkommen zaehlen
4 Treffer, aber 1 ist Kommentar (# state_ref leeren).
Echte Vorkommen: 2616 (clear), 2618 (Argument),
2639 (append). Bei jedem "Nx gelesen" einzelne Zeilen
mit Zweck zitieren.

### M-100 — Uebergangs-Grenze zweier Bloecke
body[13] (wahl = _res_nachlauf.wahl) bleibt in run_phase,
body[14] (if wahl in n) beginnt 3a-2d. Die Werte aus
body[12]/[13] fliessen in body[14]. Grenze explizit
zitieren, nicht nur "ab 2578".

### M-101 — "neue Funktionen" zaehlen
3a-2 legte 4 neue Funktionen an (2a/b/c/d) + 2
Dataclasses. Meine Aussage "9 neue Funktionen" war
falsch (zaehlte bestehende mit). Bei Extraktions-Bloecken:
nur die im Block tatsaechlich neu angelegten Funktionen
zaehlen.

### M-102 — Body-Zeilen-Widerspruch
179 (Schaetzwert) vs 178 (gemessen). Body-Laenge immer
aus `git log -1 --format='%B' | wc -l` zitieren, nie
schaetzen.

### M-323b — Phasen-Checkpoints
`_verify_patches(state, phase="phase_end")` nach jeder logischen
Phase. Aktuell: Phasen sind nur Gruppierung, kein Checkpoint.
Nach der letzten Phase: Vollsuite + Reflection.

### M-341 — Explorer überspringen
Explorer ruft `0 files` (M-338 zu strikt). Wenn der Planner
`task_files` gesetzt hat, ist der Explorer redundant. Loop
sollte `loop_explorer_skipped` auditieren statt `0 files`.

### M-344 — PROGRESS.md mit Phasen-Header
`_progress.append` schreibt pro Task. Sollte pro Phase einen
Header setzen (`## Phase p1: Bestandsaufnahme`).

### M-319 — Patch-Typ aus Datei-Existenz
Größtenteils durch M-337 gelöst (Builder nutzt nur `_zieldatei`
+ `action`). Verbleibend: `_get_git_diff` im Reviewer könnte
create/update aus Datei-Existenz ableiten.

### M-320 — phase_state.save() bei Loop-Abbruch
Bei `return 1` fehlt `phase_state.save()`. Resume nach
Abbruch unmöglich.
