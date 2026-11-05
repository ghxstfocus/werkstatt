# Merkposten — chronologisch, mit Lehre

Stand: 2026-10-22. Diese Datei sammelt Merkposten (M-Nummern), die
aus konkreten Fehlern im Bau-Prozess entstanden sind — mit der
jeweiligen Lehre. Ziel: derselbe Fehler passiert nicht zweimal.

Diese Datei sammelt Prozess-Lehren und fuehrt **keine** Todos.
Verweise auf offene Arbeit gehen an `docs/STATUS.md`, Verweise auf
Abgeschlossenes an `PROGRESS.md`.

Abgenommene Merkposten wandern nicht nach `docs/STATUS.md` (dort
stehen nur offene Punkte), sondern bleiben als Prozess-Lehre hier.

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
Versuch 1). Wortwoertliche Extraktion per `git show :` + Zeilenbereich
= 0 Verhaltensdelta.

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
- `mypy werkstatt/` ist die Baseline, nicht `mypy .`
  (tests/ zaehlt 40 Fehler).
- AST- und Katalog-Test: `pytest tests/test_audit_kinds.py -q` (6 passed)
  + `_KATALOG_SOLL` = 167. "AST+Katalog 14" ist Summen-Konvention,
  kein Messwert.

### Doku-Disziplin
- Nach jedem fertigen Block: Doku-Nachzug (Bau-Handoff, ROADMAP,
  `PROGRESS.md`, `docs/STATUS.md`) + Push. Sonst sammelt sich Rueckstand.
- Commit-Body-VOR-Werte brauchen Vor-Comm-SHA (M-57).
- `PROGRESS.md` nachziehen, wenn neue Commit-Body-VOR-Werte auftauchen.

### Merkposten-Hygiene
- Merkposten sofort eintragen, nicht erst am Session-Ende
  (M-57-Lehre: muehsam rekonstruiert).
- M-Nummern monoton, keine Wiederverwendung.
- Abgenommene Merkposten mit Status + Commit vermerken.

## Verweise

- docs/HANDOFF-BASELINE.md — kanonische Messbefehle.
- docs/archiv/session-bilanz.md — Vor-Comm-SHAs pro Commit.
- docs/STATUS.md — offene Todos.
- docs/archiv/mess-infrastruktur.md — Block M (Mess-Werkzeuge).


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


## Erst messen, dann designen, dann fixen (Lehre 2026-11-04, OP-134..137)

**Regel:** Jede Struktur-OP beginnt mit einer Mess-Phase. Kein Design
ohne vorherige Fakten. Kein Fix ohne reproduzierten Bug.

**Warum:** Am 2026-11-04 wollten wir den Explorer als Ursache fuer
32-Dateien-Plaene identifizieren. Zwei Hypothesen wurden falsch
bestaetigt, weil die Messung nicht sauber war:

1. **Hypothese A** (falsch): Explorer liefert 0 Dateien. Mein Skript
   las `e["payload"]["files"]`, das echte Audit-Feld ist aber flach
   `e["files"]`. Ergebnis: 389x "0 files" — falsch. Tatsaechlich
   liefert der Explorer 33-36 Dateien.
2. **Hypothese B** (falsch): Architect ignoriert explorer_findings.
   Der Architekt liest tatsaechlich `explorer_findings` — aber das
   Feld enthaelt `{git_dirty, pytest_laufzeit_s, ruff_befunde}`,
   nicht die Datei-Liste. Die Dateien stecken in `explorer_context`,
   das der Architect nie liest.

**Die echte Ursache wurde erst nach 3 Messschritten klar.** Zwei
davon waren noetig, um falsche Hypothesen zu widerlegen.

**Konsequenz fuer zukuenftige OPs:**
- OP-Wortlaut MUSS einen Mess-Abschnitt haben, bevor Code geaendert wird.
- Mess-Ergebnis ist Teil des OP-Texts (Zahlen, Verteilungen, Rohdaten).
- Erst nach Messung: Design (OP), dann Fix (OP).
- "Bauchgefuehl" ist kein Messergebnis. Auch nicht, wenn es plausibel klingt.
- Audit-Payloads: IMMER erst ein rohes Event anschauen, dann ein Skript schreiben.

## Struktureller Vertragsmangel (Erkenntnis 2026-11-04)

**Das eigentliche Problem ist nicht `architect.py:385`.**
Es ist: Inter-Role-Felder sind historisch gewachsen, niemand kennt
den vollstaendigen Fluss, niemand prueft Schreiber-Leser-Konsistenz.

**Bekannte Beispiele (aus einer schnellen Grep-Inventur):**
- `explorer_context` (33 key_files) wird von Scout + Builder gelesen,
  der Architect liest `explorer_findings` (git_dirty, ruff_befunde).
- `scout_api_auszug` wird geschrieben, gelesen nur vom Architect.
- `architect_prosa` (str) ist der einzige Uebergang Architect -> Planner,
  aber der Planner erwartet Tasks in strukturierter Form, nicht Prosa.
- 47 tote RunState-Felder (Handoff §7) sind noch im Code.

**Loesungsansatz:** State-Contract-Registry analog zu `control/`,
mit Schreiber/Leser/Format/Pflichtfeldern. Fail-loud bei Verstoss.
Siehe OP-134..137.


## AST-Zugriff pro Rolle ist asymmetrisch (Erkenntnis 2026-11-04)

**Beobachtung:** Der Builder hat vollen AST-Zugriff, der Architect nicht.

- Builder nutzt `_ast_block_fuer_zieldatei`, `_finde_modul_pfad`,
  `_hat_symbol`, `_validate_imports_in_patch`.
- Architect nutzt nur `scout_api_auszug` (Symbol-Namen-Liste) und
  `state.api_index_cache` (gebaut via `_baue_api_index`, aber
  **nie in den Prompt gehaengt** — toter Cache).

**Konsequenz:** Der Architect plant Aenderungen, ohne zu wissen ob
Symbole existieren, Signaturen passen, Imports moeglich sind. Der
Builder entdeckt das erst beim `_validate_imports_in_patch` — zu
spaet (Patch abgelehnt, Reflection-Runde verschwendet).

**Prinzip:** Rollen die planen sollten das gleiche Daten-Format
sehen wie Rollen die ausfuehren. Sonst plant man ins Blaue.

**Abgedeckt durch:** OP-134 (Messen), OP-135 (Design), OP-137 (Fix).

## Kategorien write_only vs getattr_only (Erkenntnis 2026-11-04, OP-134)

**Beobachtung:** Beim Messen des `RunState` mit
`tools/state_inventory.py` reicht "gelesen vs. geschrieben" nicht.
Zwei Zwischenkategorien sind noetig:

- **`write_only`** — Feld wird geschrieben, aber nie als direkter
  Attribut-Zugriff (`state.X`) gelesen. Es kann via
  `getattr(state, "X")` gelesen werden, und lebt dann indirekt.
  Beispiel: `api_index_cache` (geschrieben in
  `architect.py:603`, gelesen via `getattr` in `architect.py:324`
  und `builder.py:154`). Handoff-Behauptung "toter Cache" war
  falsch — der Cache lebt.
- **`getattr_only`** — Feld wird NUR via `getattr` gelesen, nie
  als direkter Zugriff. Beispiel: `api_key` — alle Leser nutzen
  `getattr(state, "api_key", "")`.

**Lehre:** Bei der Frage "ist Feld X tot?" reicht ein
Attribut-Grep nicht. `getattr(state, "X", default)`-Muster,
`# type: ignore[attr-defined]`-Marker und Konstruktor-Kwargs
muessen mitgezaehlt werden. Sonst entstehen falsche
Dead-Field-Listen: der Handoff nannte 47 Tote, mein erster
Skript-Lauf (nur direkte Zugriffe) lieferte 54 — die Differenz
waren 7 Felder, die nur via `getattr` leben.

**Regel:** `tools/state_inventory.py --check` ist die Quelle
der Wahrheit fuer Tote/Geister. Jede Handoff-Zahl ohne diesen
Check ist eine Hypothese, kein Messwert.

## OP-Close muss Blocker-Referenzen bereinigen (Erkenntnis 2026-11-04)

**Beobachtung:** Beim Schliessen von OP-134 (Close-Commit `38fc036`)
blieben drei `Blockiert von:`-Felder in `STATUS.md` stehen, die auf
OP-134 zeigten (OP-135, OP-136, OP-138). Jeder Leser dieser OPs
haette angenommen, sie seien noch blockiert — obwohl OP-134 erledigt
war.

**Regel:** Bei jedem OP-Close (`STATUS.md`-Eintrag loeschen):
1. `grep -n 'Blockiert von:.*OP-NNN' docs/STATUS.md` gegen den
   geschlossenen OP.
2. Pro Treffer: OP-NNN aus der Liste entfernen, `str.split(",")`
   + filtern + `", ".join(...)` — kein Regex.
3. Wenn Liste leer wird: `—` eintragen.
4. Commit-Body: Vor-/Nach-Liste der geaenderten Zeilen (M-70/M-73).

**Warum das leicht vergessen wird:** DOC_CONVENTIONS §5 sagt nur
"erledigte Punkte aus STATUS.md GELOESCHT" — ueber eingehende
Blocker-Referenzen sagt sie nichts. Das ist eine Konventionsluecke.

**Abgedeckt durch:** OP-134-Close (`38fc036`), dieser Eintrag.

**Abgedeckt durch:** OP-134 (Tool + Baseline), OP-135 (Contract).



## Handoff-Schreiben ist auch eine Mess-Aufgabe (Lehre 2026-11-05)

**Regel:** Jede Behauptung in einem Handoff oder einer OP muss
entweder (a) in der Session, in der sie geschrieben wird,
**nachgemessen** sein, oder (b) explizit als **Hypothese** markiert
sein.

**Warum:** Der Handoff vom 2026-11-04 enthielt drei Fehler, die alle
aus nicht-nachgemessenen Grep-Zahlen oder aus dem Gedaechtnis
rekonstruierten Zusammenhaengen stammten:

1. "api_index_cache wird gebaut, aber nie in den Prompt gehaengt
   (toter Cache in architect.py)" — **falsch.** Der Cache wird in
   architect.py:603 geschrieben und in architect.py:324 /
   builder.py:154 gelesen; der Architect rendert ihn in
   `_planner_system` als AST-Block.
2. "set_run_id fehlt in loop.py" — **falsch.** loop.py:296 ruft
   `set_run_id(...)` auf.
3. "Architect hat keinen AST-Zugriff" — **falsch.** Folgt aus
   Fehler 1: der Architect bekommt AST via `api_index_cache`. Was
   fehlt, ist die **Explorer-Datei-Liste** (`explorer_context`),
   nicht AST.

Zusaetzlich: die Zahl "47 tote RunState-Felder" war zufaellig
richtig, aber nie gemessen. Bei der Nachmessung am 2026-11-05
bestaetigt.

**Konsequenz fuer Handoffs:**

- Bevor eine Behauptung in einen Handoff geht: **einen Befehl**
  laufen lassen, der sie belegt (grep, audit-query, roher Payload).
- Unbelegte Aussagen werden als `(Hypothese: ...)` markiert, nicht
  als Fakt.
- Die Regel "erst messen, dann designen, dann fixen" gilt auch fuer
  den Handoff-Text selbst. Der Handoff ist kein "Session-Ende-
  Freitext", sondern ein Messbericht.

**Negativ-Beispiel dieser Session:** Der Handoff-Schreibende hat
am Session-Ende die Regel auf seine eigene Ausgabe nicht angewandt.
Die OP-134-Nachmessung durch die Folgesession hat drei Fehler
aufgedeckt, die ein einziger zusaetzlicher Grep pro Behauptung
verhindert haette.


## Pre-Commit mit pytest: Exit-Code direkt pruefen, nicht durch Pipe

**Erkenntnis 2026-11-04 (OP-146):** `pytest tests/ -q | tail -3; echo $?`
liefert `$?` von `tail`, nicht von pytest. Der Gate hat 3 Fails durchgelassen
und Commit + Push erlaubt. Der Fehler war nicht im Code, sondern im Gate.

**Regeln:**
- `set -o pipefail` in jedem Block, der pytest piped.
- Oder: `pytest tests/ > /tmp/pt.log 2>&1; PT_EXIT=$?; tail -3 /tmp/pt.log;
  echo PT_EXIT=$PT_EXIT` — niemals `$?` nach einer Pipe auswerten.
- Baseline-Runner (`werkstatt_kontext.py`) nutzt `--ignore=tests/test_shell.py`.
  Wer mit vollem `pytest tests/` vergleicht, misst eine andere Realitaet.


## pytest-Gate: Exit-Code ohne Pipe (Erkenntnis 2026-11-05)

**Problem:** `pytest tests/ -q 2>&1 | tail -3; echo $?` liefert den
Exit-Code von `tail`, nicht von `pytest`. Dreimal in einer Session
passiert. Der Gate hat 6 rote Tests durchgelassen, dann 3 rote Tests,
dann 1 roten Test — alle als "gruen" markiert.

**Regel:**
    pytest tests/ -q > /tmp/pt.log 2>&1
    PT=$?
    tail -3 /tmp/pt.log
    echo "PT=$PT"
**Niemals** `pytest | tail` mit `$?` auswerten. Drei Zeilen statt
einer, aber zuverlaessig.

## Heredoc in `if/else`-Block — Finger weg (Erkenntnis 2026-11-05)

**Problem:** `python3 <<'PY' ... PY` innerhalb eines `if [ ... ] ... else`
haengt den User in einem `>`-Prompt. Der Copy-Paste faengt dann alle
`>`-Praefixe ein und macht die Ausgabe unlesbar.

**Regel:** Kein Heredoc in `if`/`else`. Entweder:
- Heredoc in einem separaten Block (kein `if`/`else` drum)
- Oder `&&`-Kette mit Einzelbefehlen (sed, chmod, ...)

## Idempotente Patch-Bloecke (Erkenntnis 2026-11-05)

**Problem:** Ein Loesch-Block mit `assert s.count(old) == 1` crasht beim
zweiten Lauf, weil beim ersten Lauf schon entfernt.

**Regel:** Jeder Patch-Block prueft VOR dem Schreiben:
- `c_old == N and c_new == 0` -> applizieren
- `c_old == 0 and c_new == N` -> skip (schon erledigt)
- sonst: fail mit klarer Meldung

## Anker-Eindeutigkeit: `\n`-Prefix (Erkenntnis 2026-11-05)

**Problem:** Ein 12-Space-String (`            tests=...`) ist ein
**Substring** eines 16-Space-Strings (`                tests=...`).
`str.replace(old, new, 1)` findet dann 2 Treffer im gleichen File.

**Regel:** Bei mehrzeiligen Ankern mit variabler Einrueckung:
`"\n" + old` als Suchstring verwenden. Damit ist der Anker an den
Zeilenanfang gebunden und eindeutig.

## Test-Mocks: SimpleNamespace statt `class _St:` (Erkenntnis 2026-11-05)

**Problem:** `class _St: api_index_cache = {...}` als Mock loest
RUF012 aus (mutable default).

**Regel:**
    from types import SimpleNamespace
    st = SimpleNamespace(
        api_index_cache={...},
        docs={},
    )
Weniger Boilerplate, RUF012-frei, direkt lesbar.

## ruff-Baseline: AFTER <= BEFORE ist OK (Erkenntnis 2026-11-05)

**Problem:** Das Gate `if AFTER == BEFORE` blockiert Commits, wenn
die Baseline **sinkt** (weil ein unused-import entfernt wurde).

**Regel:** Baseline-Vergleich **vor** und **nach** Patch:
- `BEFORE`: das ist die Baseline.
- `AFTER`: nur **neue** Fehler blockieren.
- `AFTER < BEFORE`: Fortschritt, OK.
- `AFTER > BEFORE`: Regress, STOP.

Pre-existing Baseline in Prod-Dateien ist kein Blocker.

## Cleanup-Zombie: Commit-Labels ohne STATUS-Header (Erkenntnis 2026-11-05)

**Problem:** Commit-Messages tragen Labels (`OP-161`, `OP-150`, ...),
die nie als OP-Header in STATUS.md existierten. Die Arbeit ist
committet und dokumentiert (PROGRESS + Delete-Zone), aber der
OP-Lifecycle (open -> close) fehlt.

**Regel:** Fuer **jedes** Commit-Paar (Work + Close) muss ein
STATUS.md-Header existieren. Wenn nicht: in PROGRESS klarstellen
("OP-161 war Label, gehoert zu OP-135b Stufe 2").

Alternativ: statt Labels freie Commit-Messages ohne OP-Prefix
verwenden, wenn die Arbeit kein eigenes OP verdient.

