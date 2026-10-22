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
