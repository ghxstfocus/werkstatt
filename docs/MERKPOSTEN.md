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



## Close-Block-Pflicht: stale-Blocker-Check (Erkenntnis 2026-11-05)

**Problem:** Bei OP-135b/OP-137-Close wurden die Blocker-Referenzen
in OP-138, OP-140, OP-141, OP-145 uebersehen. Der stale-Check
schlug danach an. Die Regel (siehe oben §3) war bekannt — sie
wurde nicht angewendet.

**Regel:** Der Close-Block MUSS zwingend enthalten:
1. Vor dem Entfernen des OP-Headers: `grep -rn "blockiert von.*<OP>"`
   oder Python-Check: welche anderen OPs referenzieren <OP>?
2. Diese Referenzen im selben Close-Block bereinigen.
3. `stale-Check` **vor** dem Commit ausfuehren, nicht danach.
4. Wenn stale: **kein Commit** — Fix im gleichen Block.

**Konsequenz bei Verstoss:** Fix-Forward-Commit noetig (extra
Commit + Push). Vermeidbar mit 3 Zeilen Vorsichts-Check.


## Gate-Exit-Codes explizit erzwingen (Erkenntnis 2026-11-05)

**Problem:** Drei Gate-Muster haben in einer Session versagt:
1. `pytest | tail` -> `$?` ist `tail`, immer 0.
2. `python3 -c "..."` ohne `raise SystemExit(1)` -> immer 0.
3. `if [ AFTER == BEFORE ]` -> blockiert Fortschritt.

**Regel:** Jeder Gate-Schritt muss explizit `sys.exit(1)` oder
`raise SystemExit(1)` bei Fehler haben. Kein Vertrauen auf
Rueckgabewerte ohne Pruefung.

**Muster (gut):**
    python3 <<'PY'
    import sys
    if fehler:
        print('FAIL:', ...)
        sys.exit(1)
    print('OK')
    PY
    GATE=$?

**Nicht:**
- `python3 -c "..."` wenn Exit-Code zaehlt
- `if AFTER == BEFORE` — `if AFTER > BEFORE` (Regress)



## Self-Check-Block auf Reasoning-Modellen = CoT-Trigger (Erkenntnis 2026-11-05)

**Problem:** Der v2-Default (Commit `3cdb9e8`) hing einen
`_build_selbst_check_block()` an den Architect-Prompt. Der Block
sagte "vor dem Senden pruefen: ...". Bei `deepseek-reasoner` hat
das den CoT-Modus ausgeloest: 16000 max_tokens wurden mit
Reasoning verbraucht, `content` blieb leer. Der Fallback in
`_ask_llm_impl` akzeptierte dann `reasoning_content` als content
— Denkprotokoll (Englisch, "Let me understand...") landete als
Prosa im Planner-Split. 8 Tasks mit kopiertem Denken.

**Regel:** Bei Reasoning-Modellen (deepseek-reasoner, o1, Claude
mit extended thinking) sind aktive Pruef-Aufforderungen im Prompt
("pruefe vor dem Senden", "denke nochmal nach", "verifiziere")
potenzielle CoT-Trigger. Vor Aktivierung testen: liefert das
Modell noch gefuellten `content`, oder nur `reasoning_content`?
Passive Regeln ("Ausgabe MUSS Format X haben") sind sicher,
aktive Pruef-Aufforderungen nicht.

## Architektur-Doku ist Wahrheit, Code folgt (Erkenntnis 2026-11-05)

**Problem:** `docs/ARCHITECTURE.md:20-22` sagt woertlich:
"Architect: Keine Skills, keine Tools (M-446)". Der Code lud
aber seit 2026-11-03 hartkodiert drei Skills, darunter
`plan-crafting` mit `run_readonly(...)`. Ein einziger
Attribut-Zugriff (`architect_skills_block`) hat den
Regress-Bug maskiert — niemand hat Code und Doku gegeneinander
geprueft.

**Regel:** Wenn Code und Architektur-Doku sich widersprechen,
ist die Doku die Wahrheit. Bei jedem Fix, der einen konkreten
Fehler verhindert (M-446, K51, K52, etc.), zusaetzlich einen
Test anlegen, der das alte Verhalten **verbietet** — nicht nur
einen, der das neue Verhalten prueft. Der Test wird zur
Regress-Schutz-Barriere. Ohne Test kehrt der Bug mit hoher
Wahrscheinlichkeit zurueck (M-446-Regress hat 11 Tage gehalten).

## Reflection-Gate vs. Commit-Gate: `n` bedeutet unterschiedlich (Erkenntnis 2026-11-05)

**Problem:** Beide Gates zeigen `j/n/a`. Die Semantik ist aber
verschieden:
- Reflection-Gate (nach `reflection_erschoepft`): `n` =
  Patches dieser Task verwerfen, Task als `failed` markieren,
  **Loop laeuft weiter** mit naechster Task.
- Commit-Gate (am Phase-Ende): `n` = Reject, **Loop bricht ab**.

Der User hat das erst durch Beobachtung gelernt (Loop-Test-3:
`n` am Reflection-Gate, Loop lief weiter mit t7/t8 statt
abzubrechen). Das ist eine UX-Falle.

**Regel:** Wenn ein Gate `j/n/a` fragt, muss der Textblock
darueber explizit sagen was `n` **fuer diesen Loop-Zustand**
bedeutet. Formulierung: "n = <konkrete Aktion>". Kein
generisches "n = reject", das ist zweideutig.

## Test-Contract bei Verhaltens-Aenderung (Erkenntnis 2026-11-05)

**Problem:** Der Fallback `content` -> `reasoning_content` in
`_ask_llm_impl` wurde auf fail-loud umgestellt. Aber
`test_reasoning_content_fallback` in
`tests/test_loop_ask_llm.py` prueft noch das ALTE Verhalten.
Beim Pre-Commit-Gate rot, mit unklarer Ursache (PT>0 ohne
Kontext). Nach Umstellung auf `test_reasoning_content_fail_loud`
gruen.

**Regel:** Vor jedem Patch, der eine Verhaltens-Aenderung
durchfuehrt, zuerst `grep -rn '<alter_wert_oder_verhalten>' tests/`
ausfuehren. Wenn ein Test das alte Verhalten prueft, den Test
im selben Patch-Block umstellen. Der Test-Contract ist genauso
verbindlich wie der Produktions-Code-Contract.


## Session 2026-11-05 (Nacht) — 6 Lehren aus OP-136b..OP-143a

Die Nacht-Session: 14 Commits, 6 OPs geschlossen (OP-136b, OP-138,
OP-139, OP-140, OP-144, OP-141-Vorarbeit in 4 Schritten), 1
verworfen (OP-142), 1 teil-erledigt (OP-143a). Sechs Muster sind
in dieser Session mehrfach aufgetreten.

### Muster — sys.modules-Alias statt from X import *

Bei Modul-Umzügen, wo Tests patch.object(module, attr) nutzen:

- from werkstatt.render import * bindet Namens-Kopien. Patches
  wirken nur auf der Kopie, nicht im echten Modul.
- sys.modules[__name__] = werkstatt.render macht beide Namen
  zum selben Objekt. Patches wirken.

Fehlversuche in OP-138, OP-139, OP-140: 3x dieselbe Klasse
übersehen.

### Muster — Namens-Erhalt bei from werkstatt import X

Regex-Umbenennung from werkstatt import loop_renderer ->
from werkstatt import render ist falsch: der lokale Name
loop_renderer fehlt danach, Tests werfen NameError.

Richtig:
- from werkstatt import loop_renderer -> from werkstatt import render as loop_renderer
- from werkstatt import builder -> from werkstatt.roles import builder as builder
- import werkstatt.builder -> import werkstatt.roles.builder as builder

Gleiches gilt für patch.multiple(...) und String-Literale
(rollen.py:prompt_module).

### Muster — _common.py für Modul-Globals

Modul-Globals, die Tests patchen (ask_llm, audit): zentral
in _common.py, Submodule lesen _bglob.X(). Test patcht
_common.X. Direkt-Patch auf Fassade wirkt nicht auf
Submodul-Consumer.

Alias kurz halten (_bglob), NICHT _c: kollidiert mit lokalem
Temp-Var _c in run_builder, wirft F823 Local variable
referenced before assignment.

### Muster — as-Selbst-Alias + ruff --fix --select I

Re-Export-Fassaden (__init__.py):
- from . import _common as _common markiert ruff den Import als
  Re-Export. Kein F401 unused.
- ruff --fix --select I sortiert nur Import-Reihenfolge. NICHT
  ruff --fix . : das löscht F401 unused-Imports und bricht
  Collection, wenn der Import Side-Effects trägt (in dieser
  Session: 6 Collection-Errors durch 115 künstliche Fixes).

### Muster — allow_indirect_imports=true bei import-linter

forbidden-Contracts prüfen transitiv. Wenn die ADR "direkt
nicht importieren" meint (ADR-0013), triggert jeder transitive
Pfad (roles.builder.run -> verify -> loop -> pipeline_phases ->
phases) fälschlich.

allow_indirect_imports = true pro Contract macht die Regel
präzise.

### Muster — cmd | tail; $? ist tail-rc (4x reproduziert)

Vier Mal in dieser Session: OP-138, OP-139, OP-140, OP-144.
$? nach einer Pipe ist der Exit-Code des letzten Befehls
(tail), nicht des ersten (pytest, ruff, lint-imports).

Richtig:

    pytest -q > /tmp/pt.log 2>&1
    PT=$?
    tail -4 /tmp/pt.log
    echo "pytest rc=$PT"

M-146 verstärken: "> file; rc=$?" statt Pipe.


## mk_state() statt hand-rolled State-Mocks (Erkenntnis 2026-11-06)

**Problem:** Tests bauten ihren State auf drei Wegen:
1. `SimpleNamespace(project_dir=..., aufgabe=...)` — Felder nach Bedarf
2. `class _State: def __init__(self): self.X = ...` — hand-rolled
3. `type("S", (), {"X": ..., "Y": ...})()` — inline type()-Attrappe

Alle drei erlauben **beliebige** Felder und **vergessen** leicht die,
die der Prod-Code liest. Konsequenzen:

- `getattr(state, "X", default)` wird noetig, um Test-Mocks mit
  fehlenden Feldern zu tolerieren. Das maskiert echte Fehler.
- **`mypy` findet Feld-Umbenennungen nicht** — `getattr(state, "alter_name")`
  ist ein String, kein Attribut-Zugriff.
- **Tippfehler in Test-Feldern bleiben unentdeckt** (`apikey` statt `api_key`).
- **Zombie-Felder in Tests** (`explorer_ctx` statt `explorer_context`,
  `plan_gate_errors`, `architect_beschreibung`) — reine Attrappen,
  niemand liest sie, aber sie taeuschen vor, dass etwas passiert.

Live-Messung 2026-11-06: 262/263 `getattr` in Prod beziehen sich
auf deklarierte Felder. Der `getattr` ist reine Verteidigung gegen
Test-Mocks, kein echtes Feature. 5 Test-Dateien mit hand-rolled
`_State`-Klassen sind beim P4a-Versuch mit AttributeError gescheitert.

**Regel:** Test-State ist **immer** `mk_state(**overrides)` aus
`tests/factories.py`. Das liefert vollstaendigen `RunState` mit
Defaults, fail-loud bei unbekanntem Feld (Tippfehler-Schutz).
`SimpleNamespace` bleibt erlaubt, aber **nur** fuer Mock-Bundles
(LLM-Reply, Function-Referenzen) — **nie** als State-Attrappe.

**Siehe:** ADR-0015, OP-174, Commit f91cb1a (hand-rolled Mocks migriert)


## Aus Session 6 (Loop-Test 7, 2026-11-06/07)

### Muster — venv vor jedem pytest/Drift-Check aktivieren

Nach jedem SSH-Reconnect `source .venv/bin/activate`. Der
Prompt-Indikator ist die Klammer `(.venv)` vor dem Hostnamen —
fehlt sie, laeuft System-Python und System-Pytest.

Konkrete Folge in dieser Session:

- `which pytest` zeigt `/usr/bin/pytest` (System 7.2.1) statt
  `.venv/bin/pytest` (8.4.2)
- 7 Collection-Errors in `tests/test_web_*.py` — fastapi und
  uvicorn sind nur im venv installiert
- Drift-Checks laufen mit falschem `sys.path`, Ergebnisse nicht
  vergleichbar mit frueheren Laeufen

Regel: vor jedem `pytest` in einem Block:

    which pytest | grep -q "\.venv" || { echo "venv fehlt"; return 1; }

oder hart: `source .venv/bin/activate` an den Blockanfang.

### Muster — Reviewer-LLM produziert false positives bei AK-Text

Loop-Test 7 (2026-11-06, OP-168b): Reviewer meldete 5 Bugs
(3 HIGH, 2 medium). Messung gegen AK-Text und Code ergab:
nur Test-Luecke berechtigt, 3 HIGH waren false positives.

- Bug 1: "Gate in `_reflection_loop` fehlt" — AK-Text sagt
  explizit `_phase_end_reflection`. Reviewer interpretierte
  den Auftrag semantisch, statt den AK-Text woertlich zu
  lesen.
- Bug 2: "`phase_review_auto = False` vor Gate-Aufruf macht
  `a`-Zweig unwirksam" — Code liest `phase_review_auto` NACH
  dem Gate-Aufruf. Der Reviewer hatte die Code-Stelle falsch
  gelesen.
- Bug 5: "Gate im falschen Reject-Pfad" — Code hat dort gar
  kein Gate. Reviewer hatte eine veraltete Diff-Version.

Konsequenzen:

1. **Reviewer-Qualitaet messen**, nicht "hat Bugs gemeldet"
   als Erfolg zaehlen. Praezision/Recall pro Loop-Lauf
   notieren.
2. **Deterministischer Pre-Check** vor Reviewer fuer
   AK-Verletzungen, die per AST/String-Vergleich pruefbar
   sind (z. B. "Nenne die Ziel-Funktion aus dem AK-Text").
3. **Reviewer-Bugs nicht 1:1 als Task-Fail behandeln** —
   mindestens kurz gegen AK-Text und Code pruefen.

Siehe PROGRESS.md-Eintrag "OP-168b abgeschlossen" und
Commit 749172c.

### Muster — state_flow.py --write-baseline schreibt auf stdout

`python3 tools/state_flow.py --write-baseline` gibt den
Baseline-JSON auf **stdout** aus, schreibt nicht in
`tools/state_flow_baseline.json`. Der Help-Text ist
irrefuehrend ("JSON nach stdout" vs. Docstring-Kopf
"JSON nach tools/state_flow_baseline.json (stdout)").

Richtig:

    python3 tools/state_flow.py --write-baseline \
        > tools/state_flow_baseline.json
    python3 tools/state_flow.py --check  # muss gruen sein

Bei Baseline-Aenderung vorher `diff` gegen die alte Datei
laufen — nur additive Aenderungen akzeptieren (neue Felder),
keine Umsortierung durch Format-Wechsel.

## Session 2026-11-08 — UI + Event-Architektur + Multi-Projekt

Diese Session hat die 3XX-UI-Reihe komplett gebaut (OP-300..305),
die Event-Architektur auf CQRS-light umgestellt (OP-319..323) und
Multi-Projekt-Kontext eingefuehrt (ADR-0023). Sechs Lehren, jede aus
einem konkreten Bug.

### Muster — Python-Docstring in JS ist SyntaxError

In `static/tabs.js` stand:

    function neuer_tab(name) {
        """OP-305: Oeffentliche UI-Methode..."""
        ...
    }

Python-Docstrings funktionieren in JavaScript nicht. Der Browser
warf `Uncaught SyntaxError: Unexpected token`. Der Fehler war
unsichtbar bis zum Hard-Refresh, weil der Cache-Buster nicht synchron
erhoeht wurde.

Konsequenz:

1. JS-Files immer mit `node --check <file>` validieren vor Commit.
   Wenn node fehlt: Klammer-Balance-Check in Python (`s.count('{')`).
2. Bei Shell->Python->JS-Kette: `ast.parse()`-Check auf Python-Seite
   hilft nicht. Python-Syntax ist ok, JS-Syntax ist das Problem.
3. Cache-Buster synchron erhoehen — alle Files mit demselben
   Timestamp, sonst laedt der Browser Mix aus alt und neu.

### Muster — if (false) mit Kommentar schluckt function-Definition

In `static/tabs.js` stand 72 Zeilen toter Code:

    if (false) {  // deaktiviert: chat.js uebernimmt Form (OP-084)
        chatForm.addEventListener("submit", function (ev) {
        ... 70 Zeilen ...
    });

Der `//`-Kommentar beginnt **innerhalb der if-Klammer** und laeuft bis
zum Zeilenende. Alles nach dem `//` wird geschluckt — inklusive
`chatForm.addEventListener("submit", function (ev) {`. Der Code
darunter referenziert `ev` (undefined), die function-Klammer nie
geschlossen, bis irgendwo ein `});` kommt — dann "Unexpected `)`".

Konsequenz:

1. Toten Code **loeschen**, nicht auskommentieren. `if (false)` ist
   auch toter Code.
2. Bei hartnaeckigen SyntaxErrors: Bracket-Matcher mit
   Kommentar/String-Erkennung (Zustand `normal|line_comment|
   block_comment|string`) laeuft zeichenweise und findet das echte
   Ende.

### Muster — Clone-von-tab-neu bricht insertBefore

OP-305 (Projekt-Anlage) brauchte einen neuen Click-Handler auf dem
`+`-Button. Erster Versuch: `cloneNode(true)` + `replaceChild`, um
den alten prompt-Handler zu entfernen.

`tabs.js` hatte aber eine gespeicherte Referenz `neuBtn` auf das
**Original**-Element. Nach dem Clone zeigt diese Referenz auf ein
entferntes DOM-Element. `leiste.insertBefore(klon, neuBtn)` wirft
`NotFoundError: The node before which the new node is to be inserted
is not a child of this node.`

Konsequenz:

1. Wenn zwei Module dasselbe DOM-Element manipulieren: **niemals
   clone+replace**. Stattdessen `getElementById()` live, oder
   `addEventListener` mit pruefendem Handler (`e.stopImmediatePropagation()`).
2. Bei Aenderungen an einem Element, das andere Module halten:
   `grep` nach dem Element-ID in allen JS-Dateien vor dem Patch.

### Muster — Path("/opt") hardcoded ist untestbar

`parse_ops()` und `/start` hatten `Path("/opt")` fest im Code. Tests
mussten entweder `/opt/<fake>` anlegen (root-only, nicht idempotent)
oder mit `pytest.skip` ausweichen.

Konsequenz:

1. Pfad-Basis als Modul-Konstante deklarieren:
   `_PROJECTS_BASE = Path("/opt")` auf Modul-Ebene.
2. Tests monkeypatchen `_PROJECTS_BASE` auf `tmp_path`.
3. Kein `Path("/opt")` mehr direkt im Produktivcode.

Gilt fuer alle aehnlichen Faelle (`AUDIT_DIR_NAME`, `_werkstatt_home`).

### Muster — Auth-Disable ist _AUTH_DISABLED

Test-Fixture setzte `auth._AUTH_DISABLED_OVERRIDE = True`. Die
Funktion `is_auth_disabled()` liest aber `_AUTH_DISABLED` — anderer
Name, keine Wirkung. Der Test bekam 401 statt 404.

Konsequenz:

1. Vor Test-Fixture: `grep -n "def is_" <modul>.py` — welche API
   liest welche Variable.
2. `monkeypatch.setattr(modul, "_AUTH_DISABLED", True)` statt direkt
   auf private Variablen schreiben. Monkeypatch raeumt nach dem Test
   auf, direktes Setzen nicht.

### Muster — Cache-Buster synchron und Hard-Refresh

Zwei getrennte Bugs an einem Tag:

- `tabs.js?v=alt` aber `project_create.js?v=neu` — Browser lud
  Mix-Version.
- Hard-Refresh (`Strg+Shift+R`) laedt `layout.html` neu, aber
  `<script src="...?v=alt">` zeigt auf alte JS-Version.

Konsequenz:

1. **Alle** Cache-Buster in einer Datei (`layout.html`) mit
   **demselben** Timestamp ersetzen. Nicht pro Datei einzeln.
2. Anti-Cache-Meta-Tags im `<head>`:
   `<meta http-equiv="Cache-Control" content="no-store, must-revalidate">`
3. Bei hartnaeckigen Cache-Problemen: F12 -> Network -> "Disable
   cache" aktivieren, dann Hard-Refresh.
4. `curl -s` von Server-Log pruefen: kommt `GET /static/x.js?v=neu
   HTTP/1.1" 200 OK` oder `304 Not Modified`?

### Session-Kontext

- 31 Commits, 1515 Tests gruen, ruff/mypy clean.
- 8 OPs geschlossen (OP-300..305, OP-319..323), 3 neue OPs
  angelegt (OP-306a/b/c fuer Tab-Persistenz, Projekt-Selector,
  Multi-Projekt-Datenquellen).
- 1 ADR angelegt (0023), 1 ADR (0024) war Basis.
- Alle 3 heutigen SyntaxErrors (Docstring, `if(false)`, Clone) waren
  **erst im Browser sichtbar**, weil node/npm fehlt und JS-Files nie
  statisch validiert werden. Konsequenz fuer die naechste Session:
  `node --check` als Pre-Commit-Step einbauen, oder Python-basierten
  Klammer-Balance-Check als Ersatz.

## Session 2026-11-08 (Nacht) — Projector-Deadlock + Backfill + 6 eigene Fehler

Diese Session hat einen kritischen Deadlock gefunden (Projector stand
seit 15:14 still, UI zeigte 7h alte Daten), 23.289 falsch zugeordnete
Events zurueck-gebackfillt und OP-306b Etappe 1 (Overview-Backend)
gebaut. 11 Commits. Aber auch 6 eigene Fehler — alle derselbe Typ:
Behauptung ohne Messung.

### Fehler-Muster — Commit-Message behauptet Migration, Verifikation kam danach

Bei OP-306c Etappe 1 stand in der Commit-Message "alle 410k Zeilen
bekommen 'werkstatt'". Verifiziert wurde es **nach** dem Commit:
die Live-DB war nicht migriert (der Projector war nie geoeffnet
worden). Ein `python3 -c "from werkstatt.projection import Projector;
Projector()"` **vor** dem Commit haette es gezeigt.

**Regel:** Bei jeder Schema-Migration mit `ALTER TABLE`:
1. `Projector()` **vor** dem Commit aufrufen
2. `PRAGMA table_info(events)` **vor** dem Commit pruefen
3. Erst dann committen

### Fehler-Muster — "Rollback ist gelaufen" war nur ein `echo`

In einem Patch-Block stand:

    else
      echo "Rollback: cp /tmp/... static/tabs.js"
    fi

Das war **Text**, kein ausgefuehrter `cp`. Ich habe das als "Rollback
ist gelaufen" in die Chat-Antwort geschrieben. Falsch. Der Patch war
noch aktiv.

**Regel:** Im Rollback-Zweig **muss** ein echter `cp`-Befehl stehen,
kein `echo`. Nach jedem Block in dem "Rollback" vorkommt: mit
`git status` verifizieren dass der Rollback tatsaechlich gelaufen ist.

### Fehler-Muster — Anker-Einrueckung aus `cat -n` gezaehlt statt gemessen

Bei OP-306b-Etappe-3b-Patch habe ich die Einrueckung des Ziels aus
einer `sed|cat -n`-Ausgabe gezaehlt (16 Space angenommen, real 12).
Anker matchte nicht (`alt=0 neu=0`), Script brach ab, Rollback.

**Regel:** Vor jedem Patch mit variabler Einrueckung:
`sed -n 'X,Yp' datei | cat -A` liefert die **Bytes**. `cat -n`
liefert Zeilennummern-Prefix, kein Byte-Bild. **Immer** `cat -A`.

### Fehler-Muster — `exit` in Bash-Bloecken killt SSH

4x eingebaut heute, 1x hat es die Session gekillt. Merkposten sagt
das seit Monaten. Ich habe es trotzdem gemacht.

**Regel:** Kein `exit` in Bash. Status-Kette mit Variablen:

    STATUS="OK"
    ...
    if [ "$fehler" -ne 0 ]; then STATUS="fail-schritt-2"; fi
    ...
    echo "FINAL: $STATUS"

Block laeuft immer durch, am Ende steht der Status. Nur **eine**
Stelle die wirklich abbricht (Script mit `raise SystemExit(1)` in
Python, aber auch das ist optional — besser: `STATUS` setzen und
Rest skippen mit `if [ "$STATUS" = "OK" ]`).

### Fehler-Muster — "alle Events stammen aus Werkstatt" war Vermutung

In der OP-306c-Migration stand als Begruendung: "alle bisherigen
Events stammen aus Werkstatt". Das war eine **Vermutung**, die
23.289 security-ai-Events ignorierte. Erst Stunden spaeter (nach
Nachfrage vom User) haben wir das entdeckt.

**Regel:** Bei jeder Daten-Migration mit `UPDATE ... SET spalte=const`:
`SELECT spalte_alt, COUNT(*) FROM tabelle GROUP BY spalte_alt` **vor**
dem UPDATE. Auch wenn die Annahme "offensichtlich" erscheint.

### Fehler-Muster — Test-Import lokal vs. Modul

In `tests/test_ambient_aggregation.py` schreiben bestehende Tests
`from werkstatt.web.inspector import aggregate_ambient` **lokal in
der Test-Funktion**. Meine neuen Tests haben das vergessen — `NameError`
beim DIAG. `ast.parse()` validiert Syntax, nicht Namen.

**Regel:** Vor dem Anhaengen neuer Tests an eine bestehende Datei:
`head -20 tests/datei` lesen und das **bestehende Import-Muster**
uebernehmen. Kein Modul-Import raten.

### Was gut war

- **Messblock vor jedem Patch** hat 3x verhindert dass wir auf
  falschen Daten weitergearbeitet haetten (security-ai-Backfill,
  Terminal-Events, Projector-Deadlock)
- **Live-Check vor Commit** hat in OP-306b Etappe 1 einen echten
  Bug aufgedeckt (`aggregate_ambient` filterte nicht auf run_id != '')
- **DB-Backup** in `/tmp/events.db.vor-*` bei jeder Migration —
  haette im Notfall gerettet
- **`_jsonl_files`-Fix** (`*-migrated-*` excluden) war minimal
  und sofort testbar

### Zahlen

- 11 Commits (f5d333a bis cc6de89)
- 1507 → 1544 passed (37 neue Tests)
- 80 → 81 offene OPs (OP-306c, OP-371, OP-373 geschlossen,
  OP-372/374/306b angelegt)
- 23.289 Events backfillt
- 1 Projector-Deadlock behoben (7h Stillstand)
- 6 eigene Fehler, alle dokumentiert

### Live-Test Loop-aus-UI (2026-11-08 23:25) — 4 Bugs auf einmal

Loop aus der UI gestartet (`POST /api/projects/werkstatt/start` mit
`op_id=OP-324`). Der Loop lief korrekt an, schrieb `loop_started`,
`loop_phase`, `loop_plan_shown`, `gate_open` (`plan-4ce22f2a`) und
wartete 5+ Minuten. **Die UI zeigte nichts davon.**

Vier unabhaengige Bugs, alle im UI-Loop-Datenfluss:

1. `_audit_events` liest `ev.get("ts")`, JSONL-Events haben aber
   `"timestamp"` → alle `ts` leer im Gate-Context.
2. `offene_gates: []` obwohl `gate_open` in SQLite (Folgefehler
   oder eigenstaendig — nicht abschliessend geklaert).
3. Ambient zeigt `failed`/`idle`, weil `aggregate_ambient` nur
   `heartbeat` in letzten 60s als running wertet. Bei `gate_bridge.
   wait()` schreibt der Loop aber keinen `heartbeat` — er blockiert.
4. `POST /api/runs/{run_id}/gate` existiert, aber der Subprozess-
   Loop pollt `gate_answered`-Events. Kein Endpoint schreibt sie
   fuer einen laufenden Loop.

**Regel:** Bei jedem "Feature funktioniert"-Test aus der UI:
**zuerst** in DevTools `Network`-Tab schauen, ob Requests
tatsaechlich ankommen. Wenn `POST /start` zurueckkommt mit
`{gestartet: true, pid: ...}`, aber das UI nichts zeigt, ist es
**kein** Backend-Bug, sondern der **UI-zu-Backend**-Datenfluss.

Bei diesem Test war der Beweis der SQLite-`seq`-Vergleich:
vor Klick 788762, nach Klick 788765 (+3 Events). Backend lief,
UI war blind. Ohne diesen Datenbank-Blick waere die Diagnose
"nichts passiert" falsch gewesen.

**Angelegt:** OP-381 (Sammel-OP Loop-UI-Interaktion, 6 Tests
+ Live-Test).

**Konsequenz fuer OP-306 (Mode-Switch/Wasserfall):** OP-306 setzt
auf funktionierendem Loop-UI-Datenfluss auf. OP-381 muss vor
OP-306 gebaut werden.

### Loop-UI Live-Erfolg + Server-Neustart (2026-11-09 23:56)

**Erfolg:** Loop aus der UI gestartet (`POST /start`), Loop lief
Explorer -> Scout -> Architect -> Planner -> **Plan-Gate im Browser
sichtbar**, Klick auf `j — Ja`, `gate_answered` in SQLite. Der
UI-Loop-Datenfluss funktioniert.

**Die richtige Kette (wichtig fuer OP-381b):**

    Architect (Prosa, Freitext)
      -> Planner (macht Splits/Tasks)
      -> Loop zeigt Plan-Gate (j/n/a): "Plan ausfuehren?"
      -> bei n oder Timeout: Reflection fragt Reject-Grund
         (plan_reason-Gate, FREITEXT)
      -> Loop baut mit Grund einen revidierten Plan

  Der Architect-Freitext geht also an den Planner, NICHT durch ein
  UI-Gate. `plan_reason` ist Reflection-Input, nicht Architect-Input.

**Was wir unterwegs gefixt haben (OP-381 A/B/C/D):**

1. `_audit_events` liest `ts`, JSONL hat `timestamp` (A)
2. `_audit_events` liest `-migrated-*` alphabetisch falsch (B)
3. `aggregate_ambient` wertet Gate-Wait nicht als running (C)
4. `_machDraggable` war aufgerufen aber nie definiert (D)

**Der wichtigste Bug war aber ein anderer:** Der **Web-Server
lief 25 Stunden mit altem Python-Code** (PID 3582321 seit gestern
22:00). Alle Backend-Fixes waren committed, aber die HTTP-Antworten
kamen aus dem alten Prozess.

**Regel:** Nach jedem Commit der `werkstatt/web/*.py` beruehrt:
**Server neu starten.** Der Loop laeuft davon unabhaengig, aber
UI-Tests gehen sonst gegen alte Daten.

**Detektions-Muster das geholfen hat:** `curl /api/projects/X/gate/
context` **ohne** Browser. Response mit altem `run_id` (`test-ui-...
statt test-clean-...) = Server-Problem, nicht UI-Problem.

**Was noch fehlt (OP-381b):** Freitext-Gates im UI. `plan_reason`
(Reflection-Reject-Grund) will Freitext, `gate_panel.js` rendert
nur j/n/a-Buttons. Klick auf `j` gibt Reject-Grund "j" oder leer
-> Loop bricht mit `Tasks: 0/7` ab. Live-Beweis: seq 788855 +
788856.

**Konsequenz fuer OP-306 (Mode-Switch):** Erst OP-381b fixen,
dann Mode-Switch. Sonst zeigt der Wasserfall jedes Gate falsch.

### Externer Review als Pflicht nach jeder Code-Session (2026-11-09)

**Beobachtung:** Nach ~6 Stunden eigener Code-Arbeit (OP-381 A/B/C/D
+ Env-Loader + Port-Fix) hat ein externer Reviewer in ~4 Minuten
**5 echte Bugs** gefunden, die ich nicht gesehen habe:

- [P1] WebSocket-Auth-Bypass in /ws/{tab_id} (ws.py:70-88)
- [P1] Git-Diff-Argument-Injection in /diff + chat_tools (ref ungeprueft)
- [P2] /files + /diff ignorieren den Projektnamen (Path hardcoded)
- [P2] loop.py _full_cfg UnboundLocalError bei Config-Fehler
- [P2] loop.py Stash-Verlust bei Exception (kein try/finally)

**Alle 5 waren im Code sichtbar** — Zeile fuer Zeile. Ich habe
sie uebersehen, weil ich fokussiert war auf meinen Auftrag
(immer nur eine Stelle, nie das ganze Bild).

**Regel:** Nach jeder Session mit Code-Aenderungen, die nicht
rein mechanisch sind (Doku, Umbenennungen, kleine Bugfixes):

1. Externen Review laufen lassen (codex, github copilot review,
   oder ein LLM mit vollem Repo-Kontext).
2. Die Befunde pruefen (nicht blind uebernehmen — heute war
   EIN Reviewer-Pfad falsch: "app.py:99-111 Middleware-Skip",
   die Auth-Middleware liegt woanders).
3. Als OPs anlegen, auch wenn "nur P2". Der WebSocket-Bypass
   war P1 und ich habe ihn stundenlang uebersehen.

**Warum das zaehlt:** Der Loop baut auf einer Sicherheitsleine.
Wenn die Leine Luecken hat, ist jeder Selbstverbesserungs-Loop
riskant. Externer Review ist die zweite Leine.

**Angelegt:** OP-389, OP-390, OP-391, OP-392.

### Scout-Kette: Design vs. Praxis (2026-11-09)

**Design:** Explorer -> Scout -> Architect. Scout formt praezisen
Auftrag mit AST, nur relevanten Infos. Architect bekommt diesen
Auftrag als einzigen Input. Sinn: Architect ist der erste echte
Inputgeber fuer die ganze Kette. Je praeziser sein Input, desto
besser die Kette.

**Praxis:** Scout-Prompt fordert den Auftrag schon (SCOUT_SYSTEM
Zeile 1: "Du formulierst einen Auftrag fuer den Architect").
ABER: Architect bekommt ZUSAETZLICH explorer_findings direkt
(architect.py:447-453). 1.020 Findings parallel zum Scout-Output.
Die Verengung durch den Scout ist damit aufgehoben.

Live-Messung 2026-11-09: Architect-Prompt 35.550 prompt-Tokens.
1020 explorer_findings + ast_index 10 Dateien + scout_api_auszug
parallel. Context Rot.

**Erkenntnis:** Ein "Verengungs-Agent" (Scout) nuetzt nur, wenn
der Konsument (Architect) NUR dessen Output bekommt. Sonst:
Parallel-Input = kein Filter. Die Filter-Wirkung wird durch
den zweiten Kanal (explorer_findings direkt) aufgehoben.

**Fix (OP-385):** Scout-Output als einziges Architect-Input.
Explorer-Rohdaten fliessen in Scout (nicht in Architect).
Neues State-Feld `scout_auftrag` als zentraler Kanal.

**Nebenbei-Befund:** Scout-Prompt macht den Auftrag zum Neben-
produkt (90 % Checks, 10 % Auftrag). Bei OP-385 wird das um-
gestellt: Auftrag ist Hauptziel, Checks sekundaer.

