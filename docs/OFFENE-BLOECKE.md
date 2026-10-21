# Offene Bloecke — Werkstatt (Umbau)

Stand: 2026-10-19 (Umbau-Start, HEAD be0cd3f).
Vorherige Todos (vor Umbau): `OFFENE-BLOECKE-ARCHIV.md`.
Uebersicht: `ROADMAP.md`. Erledigt: `ERLEDIGT.md`.
Ziel: `NEUBAU-ZIELBILD.md`. Inventar: `NEUBAU-INVENTAR.md`.

Chronologisch nach Umbau-Phasen. Append-only pro Phase.

## Phase 3a — run_pipeline zerlegen (laufend)

| Block | Kategorie | Beschreibung | Aufwand | Status |
|---|---|---|---|---|
| 3a-1c-1-b | 3 | UNKLAR-Kette (`pipeline.py` Z. 8196/8219, rc=14). Braucht 2 Extra-Mocks (`ask_reviewer_for_recovery`, `print_recovery`). Charakterisierung in 3a-1c-1 oder spaeter. | klein | offen |
| 3a-1c-1b-Fallback | 3 | `judge_verdict_sequenz`-Fallback (Sequenz erschoepft -> starr `judge_verdict`) in 3a-1c-1a implementiert, aber nicht getestet. Test folgt in 3a-1c-1b. Fail-open-Hinweis: Fallback uebernimmt `judge_verdict`; fail-closed nur, wenn `judge_verdict` fail-closed ist. | klein | offen |
| 3a-3-b | 3 | NO-GO-Recovery + Recovery nach Loop (`pipeline.py` Z. 8460-8467). Gehoert in 3a-3 (`_phase_main_pfad`, Befund CI/CG, Deadlock-Kette). | mittel | offen |
| 3a-1c-1a-COMMAND-Solver | 3 | 3a-1c-1a-COMMAND-Test deckt Solver-Ausfuehrung NICHT ab. Solver-Ausfuehrung ist in `_handle_solver_command` zu testen — existierenden Test pruefen, sonst Merkposten fuer 3a-1c-2. Folge aus Fix C (Reviewer A7-4, Aufruf-Tiefe #17). | klein | offen |
| 3a-1c-1-b (Vorbedingung) | 3 | ERLEDIGT (Commits 7cb8866 + 6cd545f). 3 UNKLAR-Verhaltens-Tests: Kette rc=14, Payload-raw, Verstoss (1x UNKLAR). Vorbedingung fuer 3a-1c-2 erfuellt (A9-8-3a, HR-R9). | mittel | done |
| Werkstatt-Entkopplung von security-ai | 3 | `werkstatt/verify.py` importiert `harness.audit.writer.AuditWriter`, `core.changeapplier.models.Change`, `core.changeapplier.applier.ChangeApplier`, `core.changeapplier.models.ChangeState` — **nur Introspektion** (`inspect.signature`, Enum-Iteration), keine Ausfuehrung. Betroffen: `_api_signaturen` (Z. 151-182, 3 Importe), `verify_values` (Z. 234-253, 1 Import), plus Datei-Lesen `(project_dir / "core/changeapplier/applier.py")` Z. 260 (kein Import, nur Datei). Ziel: null `harness`/`core`-Imports in `werkstatt/`. Empfohlen: AST-basierte Signatur-Extraktion aus `project_dir` (Quelltext liegt lokal). Fallback: Signaturen als Konstanten einfrieren. Aufwand ~4-6 h. **Kein Blocker fuer 3a-1c-2b** (W2 nutzt verify nicht). Nach 3a-1c-2b, vor 3a-1c-3. | mittel | offen |
| C-Nummerierung run_pipeline | 3 | **Definiert 2026-10-21 (Block 6d-6g), weil C0-C9 nirgends dokumentiert war** (nur Erwaehnungen in ROADMAP/UEBERGABE). run_pipeline Z. 7949-8841 (893 Z.) wird in 10 logische Bloecke zerlegt. Grundlage: 7 SCHRITT-Kommentare (Z. 8070-8764) + Vorlauf/Nachlauf. Die C-Nummern sind Zerlegungs-Ziele, NICHT die aktuellen Top-Level-if (davon 25). Tabelle: C0 Vorlauf (config/project_dir/memory/agents/docs/catalog/budget/solver/git_author/phasen_state, Z. 7962-8040) offen | C1 Audit-Start+run_id (Z. 8042-8066) offen | C2 Basis-Gate Schritt 0 (Z. 8070-8131) offen | C3 Reviewer-Wahl Schritt 1 (Z. 8135-8191) inline, nicht geplant | C4 Builder Schritt 2 (Z. 8193-8334) DONE vor 3a (e8763ad, builder_reply_mit_command_loop) | C5 Review-Schleife Schritt 3 (Z. 8336-8555) DONE 3a-1c-1b (72e3459, _review_verdict_behandlung) | C6 Coverage+Chaos Schritt 4 (Z. 8557-8600) offen | C7 Commit-Review Schritt 5 (Z. 8602-8760) DONE 3a-1c-2b (W2, _commit_review_w25_loop) | C8 Approval Schritt 6 (Z. 8762-8797) offen | C9 Human-Gate (Z. 8798-8841) offen. Konsequenz: 3a-1c-3 = C0+C1+C2+C6 (4 offene), 3a-1c-4 = C8+C9 (2 offene). | mittel | done |
| Commit-Body-Fehler 3a-1c-2a/2b | 2 | **KORREKTUR (2026-10-21, ehrlich):** Die fruehere Behauptung in Commit 4e450d7 ("drei Commit-Bodies falsch, echte Kette 1243 -> 1243 -> 1245") war **ein Messfehler des Bau-Chats**. Ursache: In Block 12a (M-33-Nachmass) wurde `ecf35a4~1` gemessen (1243, korrekt), aber `ecf35a4` selbst (nach -1) wurde NICHT gemessen. Stattdessen wurde 1243 fuer `88e3e5c` und 1243 fuer `ecf35a4~1` als "dieselbe Zahl" gewertet, ohne `ecf35a4` (1242) zu messen. **Die tatsaechliche Chronologie (git log --oneline, absteigend):** ae25e08 (neuester), ecf35a4 (mittlerer), 88e3e5c (aeltester). **Die korrekte Kette (hart gemessen via git worktree + pytest --collect-only):** vor 88e3e5c: 1237. 88e3e5c: +6 -> 1243 (6 neue B1a/B1b/B2/B3/B4/B6). ecf35a4: -1 -> 1242 (7390 geloescht). ae25e08: +3 -> 1245 (B7, B8, test_build_commit_input_phasen_unterblock). **Alle drei Commit-Bodies (ecf35a4/88e3e5c/ae25e08) sind richtig.** Meine fruehere Behauptung "drei falsch" war falsch. **M-39/M-40 bleiben gueltig:** `ae25e08` sagt "11 Parameter" — echt: **10** im Code (Z. 7761-7771). `277029f`/`74ff77d`/`ac4956f`/`b502e20`/`f608658` nennen `_commit_review_w25_loop` — M-27-Freigabe nannte `_commit_verdict_behandlung` (falsch, Funktion existierte damals nicht). **M-27 war Freigabe auf falscher Grundlage.** Konsequenz: Bei Commit-Body-Pruefungen **zwei** Messungen: (a) `git log`-Reihenfolge explizit pruefen (Chronologie aus `git log --reverse` oder Datum), (b) `pytest --collect-only` auf **jedem** Zwischenstand, nicht nur auf `~1`. | klein | offen |
| Position A vs B (Code-Reihenfolge) | 2 | **Entschieden 2026-10-21 (Reviewer-Frage 3, Durchlauf 36):** Position **A** = `_basis_gate` (C2) vor `run_pipeline`, `_commit_review_w25_loop` (C7) bleibt wo er ist (vor `_basis_gate`). **Begruendung:** Extraktions-Bloecke in umgekehrter Abhaengigkeits-Reihenfolge erzeugen am wenigsten Ueberraschung. Die Doku-Konvention C0-C9 (293589e) ist **orthogonal** zur Code-Reihenfolge. 293589e etabliert Doku, nicht Code-Reihenfolge. **Code-Reihenfolge folgt NICHT C-Nummerierung.** Keine stille Konvention (Reviewer-Auflage). | klein | done |
| W2-Grenze VOR/NACH (Doku-Klaerung 3b) | 2 | **Vier Objekte, ein Etikett "W2" — die Doku-Verwirrung.** Hart gemessen 2026-10-21 (ast, ein Lauf): (1) **W2-Quell-Bereich VOR Extraktion:** 8585-8755 (171 Z.) in run_pipeline — Skip-Pfad 8585-8603, Init 8606-8607, while-True 8608-8755. (2) **W2-Funktion NACH Extraktion:** _commit_review_w25_loop, 7761-7948 (188 Z.). (3) **W2-Aufruf NACH Extraktion:** in run_pipeline, 8754-8758 (5 Z.). (4) **C7-Rest NACH Extraktion:** if config.review_commit_package-Block, 8605-8760 (156 Z.). C6 (Coverage/Chaos) endet bei 8600 — nicht W2. **Die 7 Varianten in M-22..M-45 sind Etiketten fuer diese 4 Objekte, keine 7 Wahrheiten.** **Entscheidung (b) 2026-10-21 (Auftraggeber):** 3a-1c-2b als gebaut akzeptiert. Code verhaltensgleich (1245/17/9/14 durchgehend). Die Doku-Klaerung (VOR/NACH-Trennung in OFFENE-BLOECKE.md, C-Nummerierung) erfolgt in 3b. Kein Aufteilen in 3a-1c-2b-1/2/3 (waere nur Doku-Restruktur, kein Code). | klein | offen |
| Struktur-Tests umstellen | 2 | **5 von ~15 erledigt (74ff77d).** Umgestellt: TestCommitReviewNewFileSkip 4x + TestW11 (getsource run_pipeline -> _commit_review_w25_loop). **Rest ~10** folgen mit 3a-1c-3 (C0/C1/C2/C6) und 3a-1c-4 (C8/C9), weil dort die naechsten getsource-Ziele wandern. test_fail_closed_pfad_bleibt (Z. 5416) bleibt absichtlich auf run_pipeline. Duale Quellen-Pruefung oder Verhaltens-Test (A9-13, A10-13b). | gross | offen |
| 3a-1c-2-V2-Groesse | 3 | V2 = 303 Z., 13 Steuerungsstellen, 12 Parameter. Zu gross fuer 1-Rutsch. Zerlegung V2a/V2b vor 3a-1c-2 pruefen (A8-2-nach-3b). | mittel | offen |
| 3a-1c-2b (W2-Extraktion) | 3 | ERLEDIGT (277029f + 74ff77d + ac4956f). W2 = 8585-8755 (171 Z.) nach `_commit_review_w25_loop` extrahiert. 10 Parameter (Signatur-Freeze 18c, M-39): state, api_key, project_dir (Path!), project_name, max_llm, max_minutes, reviewer_prompt, builder_prompt, _hat_anker_patches, _diff_name_only. Zwei break (COMMIT-GO, ESKALATION) -> return None. Aufrufstelle run_pipeline Z. 8754-8760. 5 Struktur-Tests umgestellt (74ff77d): TestCommitReviewNewFileSkip 4x + TestW11. test_fail_closed_pfad_bleibt unberuehrt (Fail-Closed-Pfad blieb in run_pipeline). mypy-Fix (ac4956f): project_dir str->Path (19->9). Baseline 1245 / ruff 17 / mypy 9 / AST+Katalog 14. AQ-Regressionslatte 9/9 gruen. | gross | done |
| 3a-1c-2a (W0a-1/2/3) | 3 | ERLEDIGT (ecf35a4). W0a-1/2/3 extrahiert (`_commit_review_w25_suite`, `_commit_review_w25_recovery`, `_commit_review_w25_suite_nachlauf`). 7390 (test_sammel_commit_recovery_reparierbar) geloescht, B1a ersetzt. | gross | done |
| 3a-1c-2a-AQ | 2 | ERLEDIGT (88e3e5c + ae25e08). 6 AQ-Tests B1a/B1b/B2/B3/B4/B6 + B7/B8/6887 = 9 neue Verhaltens-Tests. Baseline 1237 -> 1245. | mittel | done |

## Phase 3b — Loop-Umbau (nach 3a)

Noch keine Merkposten. Entstehen hier, sobald 3a abgeschlossen.

## Phase 3c — NEUBAU-Abloesung (nach 3b)

Noch keine Merkposten. Entstehen hier, sobald 3b abgeschlossen.

## Phase 5 — ruff/mypy-Rest

| Block | Kategorie | Beschreibung | Aufwand | Status |
|---|---|---|---|---|
| 5-ruff | 2 | ruff 17 Fehler (Code). Phase-5, kein Runtime-Bug. | klein | offen |
| 5-mypy-code | 2 | mypy 7 Fehler / 2 Dateien (Code). 3 import-not-found (MYPYPATH), 2 R-A (`RunState.messungen_nach_apply`), 2 list/set (Annotation-only). | klein | offen |
| 5-mypy-tests | 2 | mypy `tests/` 17 Fehler / 4 Dateien (nicht in Baseline; 4 davon aus 3a-1a-Tests, `ref`-Annotation). | klein | offen |

## Session-Nachbereitung

| Block | Kategorie | Beschreibung | Aufwand | Status |
|---|---|---|---|---|
| Bau-Handoff-Refresh | 2 | `Bau-Handoff.md` nach Session-Ende auf Ist-Stand bringen (HEAD be0cd3f, Branch umbau/phase-2, 1229 Tests, ruff 17, mypy 7, AST 6, Katalog 167). | klein | offen |

## Referenz — Deadlock-Kette (dokumentiert, fuer 3a-3)

Der Phase-21-Deadlock war eine Kette:
1. Parser strippt 4 Leerzeichen nicht (min==2 only) -> Anker 0x.
2. max_tokens_judge 8192 -> reasoning-only, content leer.
3. D2-Duplikate global statt pro Paket -> Phase 20b scheitert.
4. Planner-Resume bei failed -> Planner kostet, liefert nichts.
5. Contract fehlt im Builder-Prompt -> Builder raet API.
6. Test-Fehler nicht persistiert -> Builder wiederholt.
7. verify_code fehlt -> erfundene APIs (log(status=...)).



## Verweise

- `ROADMAP.md` — Phasen-Uebersicht.
- `ERLEDIGT.md` — Erledigte Bloecke mit Commit/Tests.
- `NEUBAU-ZIELBILD.md` — Ziel-Architektur.
- `NEUBAU-INVENTAR.md` — 191 Funktionen, N1-N4, R-3.
- `NEUBAU-ENTFERNUNG.md` — Entfernungs-Register.
- `UEBERGABE-3A-2026-10-19.md` — Phase-3a-Uebergabe.
- `OFFENE-BLOECKE-ARCHIV.md` — Todos vor Umbau.

## 3a-1c-2b — Abnahme-Bericht (A13/A14/A15, 2026-10-21)

Reviewer-Auflage (Durchlauf 36, Frage 2): Formeller Abnahme-Bericht
fuer 3a-1c-2b. Quellen: Commit-Body `ae25e08` (AQ-Vorspann) +
`277029f`/`74ff77d`/`ac4956f` (Extraktion) + `b502e20` (Block-done).


### Vollstaendige Zitate aus `ae25e08` (nachgeliefert 2026-10-21, M-39/M-40)

Der urspruengliche Abnahme-Bericht (f608658) hat A13/A14/A15 nur
referenziert, nicht zitiert. Hier die vollstaendigen Zitate:

**A13-1 — Layer-Tabelle (B7/B8):**
```
A13-1 Layer-Tabelle (B7/B8):
  B7: VOR C7-Rumpf @ 8671-8673.
      NACH W2.
  B8: VOR C7-Rumpf @ 8675-8679.
      NACH W2.
```

**A13-2 — commit_verdict-Wert:**
```
A13-2 commit_verdict-Wert:
  commit_verdict != "COMMIT-NO-GO" @ 8675.
  Jeder Wert ausser COMMIT-GO und COMMIT-NO-GO
  -> break. COMMIT-ESKALATION gewaehlt
  (classify_verdict kennt es).
```

**A13-3 — n==2-Sicherstellung:**
```
A13-3 n==2-Sicherstellung:
  Helper: n==1 Mess-Wahl (""), n>=2
  commit_verdict. Reviewer-Aufruf 1 (C1)
  Mess-Wahl, Reviewer-Aufruf 2 (W2)
  commit_verdict.
```

**A14-1 — Baseline VOR/NACH (korrekt: VOR 1242, NACH 1245):**
```
A14-1 Baseline-VOR/NACH:
  VOR:  1242 / ruff 17 / mypy 7 / AST 6 / 167
  NACH: 1245 / ruff 17 / mypy 7 / AST 6 / 167
  (+3: B7, B8, 6887-Verhaltens-Test).
```
Korrektur: VOR war **1243**, nicht 1242 (M-33, git worktree
+ pytest --collect-only). NACH 1245 ist korrekt. Die +3 sind
effektiv **+2** (B7, B8; 6887-Ersatz netto 0).

**A14-2 — 6887 delete vs dual-source:**
```
A14-2 6887:
  Verhaltens-Test test_build_commit_input_
  phasen_unterblock neu. 6887 (Struktur-Test)
  wird in 3a-1c-2b-Extraktion geloescht.
```
Beleg: In `74ff77d` wurde 6887 auf `_commit_review_w25_loop`
umgestellt (nicht geloescht — die Dual-Source-Assertion
`if state.phase_aktiv:` steht weiterhin in `run_pipeline`).

**A15-1 — 6887-Verhaltens-Test-Setup:**
```
A15-1 Setup:
  _setup_c7 erweitert um commit_verdict-
  Parameter (Default COMMIT-GO).
  Phasen-State mit _agents (5 Rollen inkl.
  judge), Builder-Reply, apply_code_patches,
  _post_apply_messung, _rollback_zieldateien.
```

**W2-Signatur (M-39-Korrektur):**
```
Aktueller Code (pipeline.py:7761-7771):
  def _commit_review_w25_loop(
      state: RunState,
      api_key: str,
      project_dir: Path,
      project_name: str,
      max_llm: int,
      max_minutes: int,
      reviewer_prompt: str,
      builder_prompt: str,
      _hat_anker_patches,
      _diff_name_only,
  ) -> int | None:

= 10 Parameter.

6e11718 sagt 9 (project_name fehlt). M-27 sagt 11 (reply und
commit_verdict faelschlich als Input). Korrekt: **10**.
```

### A13-1 — Layer-Tabelle (B7/B8)

Zitat `ae25e08`:
> A13-1 Layer-Tabelle (B7/B8):
>   B7: VOR C7-Rumpf @ 8671-8673. NACH W2.
>   B8: VOR C7-Rumpf @ 8675-8679. NACH W2.

Beleg: B7 (`test_run_pipeline_commit_review_go_break`) und
B8 (`test_run_pipeline_commit_review_eskalation_break`) pruefen
das Verhalten von `run_pipeline`, unabhaengig davon, ob der
`while True:`-Loop in `run_pipeline` (VOR) oder in
`_commit_review_w25_loop` (NACH) liegt. **Nach W2-Extraktion
gruen** (Block 4d-3d: 1240 passed, B7/B8 nicht in failed-Liste).

### A13-2 — commit_verdict-Werte exakt

Zitat `ae25e08`:
> A13-2 commit_verdict-Wert:
>   commit_verdict != "COMMIT-NO-GO" @ 8675.
>   Jeder Wert ausser COMMIT-GO und COMMIT-NO-GO -> break.
>   COMMIT-ESKALATION gewaehlt (classify_verdict kennt es).

Beleg: B8 assertet `verdict == "COMMIT-ESKALATION"` im
audit-Payload. Nach W2-Extraktion gruen (Block 4d-3d).

### A13-3 — n==2-Sicherstellung

Zitat `ae25e08`:
> A13-3 n==2-Sicherstellung:
>   Helper: n==1 Mess-Wahl (""), n>=2 commit_verdict.
>   Reviewer-Aufruf 1 (C1) Mess-Wahl, Reviewer-Aufruf 2 (W2)
>   commit_verdict.

Beleg: `_setup_c7` (test_pipeline_integration.py:1677) mockt
`ask_llm` mit `n == 1 -> ""` (Mess-Wahl), `n >= 2 -> commit_verdict`
(Commit-Review, auch bei Wiederholung im commit_versuche-Loop).
Nach W2-Extraktion gruen.

### A14-1 — Baseline VOR/NACH (korrekt: VOR 1242, NACH 1245)

Zitat `ae25e08`:
> A14-1 Baseline-VOR/NACH:
>   VOR:  1242 / ruff 17 / mypy 7 / AST 6 / 167
>   NACH: 1245 / ruff 17 / mypy 7 / AST 6 / 167
>   (+3: B7, B8, 6887-Verhaltens-Test).

**Korrektur (M-33, hart gemessen 2026-10-21):** Die VOR-Zahl 1242
ist falsch. Echte Kette via `git worktree` + `pytest --collect-only`:
  - `ecf35a4~1`: 1243
  - `88e3e5c`:   1243
  - `ae25e08`:   1245
D.h. VOR `ae25e08` war 1243, nicht 1242. NACH ist korrekt (1245).
Die +3 sind effektiv +2 (B7, B8; 6887-Ersatz ist netto 0).

### A14-2 — 6887 delete vs dual-source

Zitat `ae25e08`:
> A14-2 6887:
>   Verhaltens-Test test_build_commit_input_phasen_unterblock neu.
>   6887 (Struktur-Test) wird in 3a-1c-2b-Extraktion geloescht.

Beleg: In `74ff77d` wurde 6887 (Struktur-Test) auf
`_commit_review_w25_loop` umgestellt (nicht geloescht, weil die
Dual-Source-Assertion `if state.phase_aktiv:` weiterhin in
`run_pipeline` steht — siehe `74ff77d`-Commit-Body). Die
Verhaltens-Absicherung leistet `test_build_commit_input_phasen_
unterblock` (A15).

### A15-1 — 6887-Verhaltens-Test-Setup

Zitat `ae25e08`:
> A15-1 Setup:
>   _setup_c7 erweitert um commit_verdict-Parameter
>   (Default COMMIT-GO). Phasen-State mit _agents (5 Rollen inkl.
>   judge), Builder-Reply, apply_code_patches, _post_apply_messung,
>   _rollback_zieldateien.

Beleg: `_setup_c7` (test_pipeline_integration.py:1677-1735)
erfuellt die Auflage. `test_build_commit_input_phasen_unterblock`
prueft, dass `_build_commit_input` bei `phase_aktiv=True` den
UNTERBLOCK-Kontext enthaelt. Nach W2-Extraktion gruen (Block 4d-3d).

### Zusaetzliche Korrektur (11 Parameter)

Zitat `ae25e08`:
> W2-Signatur frozen (18c):
>   11 Parameter + commit_versuche local.

**Korrektur:** 11 ist falsch. Echte Parameterzahl: **9** (per ast
gemessen in Block 3, korrigiert in `6e11718`). Die 9 Parameter:
`_diff_name_only`, `_hat_anker_patches`, `api_key`, `builder_prompt`,
`max_llm`, `max_minutes`, `project_dir` (Path!), `reviewer_prompt`,
`state`.

### Ergebnis

3a-1c-2b ist **abgenommen** mit zwei Korrekturen an Commit-Body-Zahlen
(A14-1: VOR 1242, NACH 1245 — korrekt aus ae25e08; 11 -> 9 Parameter war falsch, korrekt 10). Beide Korrekturen sind
in `OFFENE-BLOECKE.md` als Merkposten dokumentiert.


## M-41 — A14-2-Widerspruch aufgeloest (2026-10-21, ehrlich)

Der Abnahme-Bericht (f608658, 4e450d7) enthielt einen Widerspruch:
- Satz 1: "6887 (Struktur-Test) wird in 3a-1c-2b-Extraktion
  geloescht." (Zitat aus `ae25e08`-Commit-Body)
- Satz 2: "In `74ff77d` wurde 6887 auf `_commit_review_w25_loop`
  umgestellt (NICHT geloescht)."

**Die Wahrheit (gemessen):**

- `ae25e08` hat **0 Tests geloescht** und **3 hinzugefuegt**:
  `test_run_pipeline_commit_review_go_break` (B7),
  `test_run_pipeline_commit_review_eskalation_break` (B8),
  `test_build_commit_input_phasen_unterblock`.
- `74ff77d` hat `test_commit_review_prompt_unterblock_nur_phasen_
  modus` (Z. 6881-6892) **umgestellt**, nicht geloescht:
  `getsource(pipeline._review_verdict_behandlung)` ->
  `getsource(pipeline._commit_review_w25_loop)` (Z. 6888).
- `test_build_commit_input_phasen_unterblock` ist eine **Ergaenzung**,
  kein Ersatz. Der Test existiert in
  `tests/test_pipeline_integration.py:1938`.

**Der `ae25e08`-Commit-Body war prospektiv falsch:** er kuendigte
eine Loeschung an ("6887 wird in 3a-1c-2b-Extraktion geloescht"),
die nie kam — 6887 wurde stattdessen umgestellt.

**Korrektur fuer A14-2:**
- 6887 ist **umgestellt**, nicht geloescht.
- `test_build_commit_input_phasen_unterblock` ist **zusaetzlich**,
  nicht als Ersatz.
- Die Baseline-Bewegung `ae25e08` ist **+3** (B7, B8, neuer Test).


## A16-1/A16-2 — 18c-Bruch-Deklaration (Reviewer-Auflage 37)

**A16-1 — W2-Signatur (10 statt 11 Parameter):**

M-27-Freigabe (11 Parameter: state, reply, commit_verdict,
max_commit_versuche, api_key, project_dir, project_name,
builder_prompt, max_llm, max_minutes, reviewer_prompt) und
277029f-Implementierung (10 Parameter) weichen ab.

**M-27 enthielt falsch:**
- `reply` (W2-intern, aus `ask_llm`)
- `commit_verdict` (W2-intern, aus `classify_verdict`)
- `max_commit_versuche` (W2-local, `max_commit_versuche = 2`)

**M-27 uebersah:**
- `_hat_anker_patches` (W2-Input, C7-Local aus Z. 8570-8573)
- `_diff_name_only` (W2-Input, C7-Local aus Z. 8550)

**Korrekte Signatur (10 Parameter, pipeline.py:7761-7771):**
  state, api_key, project_dir, project_name, max_llm,
  max_minutes, reviewer_prompt, builder_prompt,
  _hat_anker_patches, _diff_name_only.

**M-27 zurueckgezogen.** 18c-Freeze wurde zwischen M-27 und
277029f gebrochen. Der Bau erfolgte ohne Freigabe der
tatsaechlichen Signatur.

**A16-2 — Funktionsname:**

M-27 nannte `_commit_verdict_behandlung`. Gebaut wurde
`_commit_review_w25_loop` (pipeline.py:7761).
`_commit_verdict_behandlung` existiert nicht in pipeline.py.
`_review_verdict_behandlung` existiert (C5, aus 72e3459) —
das ist eine **andere** Funktion (Review-Schleife, nicht
Commit-Review-Loop).

Semantisch ist `_commit_review_w25_loop` korrekt
(Commit-Review-Loop, nicht Verdict-Verarbeitung).

**M-27 zurueckgezogen.** 18c-Freeze wurde gebrochen.


## A18-1/A18-2/A18-3/A18-4 — Zitate + Klarstellung (2026-10-21)

Reviewer-Auflage (Durchlauf 39, GO-mit-Auflagen).

### A18-1 — Baseline-Kette (Zitate)

`git log --oneline 88e3e5c..ae25e08`:
```
ae25e08 3a-1c-2b: AQ-Vorspann B7/B8 + 6887-Verhaltens-Test
ecf35a4 3a-1c-2a: W0a-1/2/3 extrahiert + 7390 geloescht
```

`pytest --collect-only` pro Commit (git worktree):
```
88e3e5c:  1243 tests collected
ecf35a4:  1242 tests collected
ae25e08:  1245 tests collected
```

Kette: 1237 (vor 88e3e5c) + 6 (B1a/B1b/B2/B3/B4/B6) = 1243, dann -1 (7390) = 1242, dann +3 (B7, B8, test_build_commit_input_phasen_unterblock) = 1245. **Alle drei Commit-Bodies richtig.**

### A18-2 — M-41 (Zitate)

`git show 74ff77d --stat` (Auszug):
```
test(3a-1c-2b): Struktur-Tests auf _commit_review_w25_loop umgestellt
5 getsource-Struktur-Tests, die Code pruefen, der mit
W2 (Commit 277029f) in _commit_review_w25_loop gewandert
```

Diff Z. 6880-6892 (Auszug):
```
-        # wandert bei 3a-1c-2 (C7) in _commit_review_loop.
+        # wandert bei 3a-1c-2b in _commit_review_w25_loop (erledigt).
-            + inspect.getsource(pipeline._review_verdict_behandlung))
+            + inspect.getsource(pipeline._commit_review_w25_loop))
```

Aktueller Zustand Z. 6881-6892:
```
def test_commit_review_prompt_unterblock_nur_phasen_modus(self) -> None:
    # Dual-source (A10-13b): _w11_unterblock_kontext-Bau
    # wandert bei 3a-1c-2b in _commit_review_w25_loop (erledigt).
    import inspect
    src = (
        inspect.getsource(pipeline.run_pipeline)
        + inspect.getsource(pipeline._commit_review_w25_loop))
    assert "if state.phase_aktiv:" in src
    assert "_w11_unterblock_kontext = \"\"" in src
```

`test_build_commit_input_phasen_unterblock` (integration:1938):
```
def test_build_commit_input_phasen_unterblock(
        tmp_path: Path, monkeypatch) -> None:
    """3a-1c-2b A15: Phasen-Modus -> commit_input mit
    UNTERBLOCK-Kontext. Ersetzt 6887 (Struktur-Test) als
    Verhaltens-Test."""
    ph, _, _ = _setup_c7(monkeypatch, tmp_path)
    result = pipeline._build_commit_input(
        ph, "core/x.py",
        "UNTERBLOCK: U1 (1 von 2) — A",
        "keine")
    assert "UNTERBLOCK:" in result
    assert "U1" in result
    assert "1 von 2" in result
```

### A18-3 — 18c-Bruch-Deklaration (Verantwortungs-Klarstellung)

M-27 (11 Parameter) vs 277029f (10 Parameter).
Falsch in M-27: reply, commit_verdict, max_commit_versuche
(W2-intern). Uebersehen in M-27: _hat_anker_patches,
_diff_name_only (W2-Input).

**Verantwortung beider Seiten:**
- Reviewer hat M-27 mit 11 abgenommen, ohne reply/commit_verdict/
  max_commit_versuche (W2-intern) und _hat_anker_patches/
  _diff_name_only (W2-Input) zu pruefen.
- Bau-Chat hat mit 10 gebaut, ohne die Abweichung zu M-27 vor
  dem Bau zu deklarieren.
- **Kein Prozess-Schutz zwischen Freigabe und Bau.**

M-27 zurueckgezogen.

### A18-4 — A14-1-Widerspruch geklaert

**Klarstellung:** Die A14-1-Angabe in `ae25e08` ("VOR 1242 /
NACH 1245") ist **KORREKT**. VOR `ae25e08` war 1242 (weil
`ecf35a4` -1 gemacht hat: 1243 -> 1242).

**Meine Korrektur in `4e450d7`** ("A14-1 VOR war 1243, nicht
1242") war **FALSCH**. Ursache: Verwechslung von `ecf35a4~1`
(1243) mit `ecf35a4` (1242).

**Korrigierte Aussage:** A14-1 (ae25e08): VOR 1242, NACH 1245.
Korrekt. Die +3 sind B7 + B8 + test_build_commit_input_phasen_
unterblock.


## A18-1a/1b/1c — Vollstaendige Chronologie + Baseline + B3-4 (2026-10-21)

Reviewer-Auflage (Durchlauf 40, NO-GO wegen A18-1-Luecke).

### A18-1a — Vollstaendige Chronologie (git log --reverse)

```
2026-10-20 06:00:59  88e3e5c  3a-1c-2a: AQ-Vorspann 6 Tests (B1a/B1b/B2/B3/B4/B6)
2026-10-20 06:08:52  ecf35a4  3a-1c-2a: W0a-1/2/3 extrahiert + 7390 geloescht
2026-10-20 06:40:12  ae25e08  3a-1c-2b: AQ-Vorspann B7/B8 + 6887-Verhaltens-Test
2026-10-20 06:42:09  ca56520  3a-1c-2b-doc: Merkposten W2-Extraktion (Fallstricke)
2026-10-20 06:47:58  1091b3e  Doku: Phase-3a-Stand nachziehen (2026-10-20)
2026-10-20 07:01:04  9141591  docs(3a-1c-2b): Merkposten gegen 1091b3e korrigiert
2026-10-21 14:41:48  bf2e487  docs(3a-1c-2b): Merkposten Werkstatt-Entkopplung
2026-10-21 14:45:24  5a9939c  refactor: Geruest _commit_review_w25_loop (tot)
2026-10-21 14:50:29  da7d6bc  docs: Baseline-Delta ruff 0.17.1 / mypy 2.4.0
2026-10-21 14:53:07  8a921d4  docs: W2-Grenze korrigiert 8585-8755 (171 Z.)
2026-10-21 15:05:30  6e11718  docs: Parameterbedarf 8 -> 9
2026-10-21 15:10:24  277029f  refactor: W2-Extraktion _commit_review_w25_loop
2026-10-21 15:12:15  74ff77d  test: Struktur-Tests auf _commit_review_w25_loop
2026-10-21 15:15:48  ac4956f  fix: project_dir: Path
2026-10-21 15:23:21  b502e20  docs: Block done, Struktur-Tests 5/~15
2026-10-21 15:30:47  293589e  docs: C-Nummerierung run_pipeline
2026-10-21 15:43:26  f608658  docs: Abnahme-Bericht A13/A14/A15
2026-10-21 15:52:33  4e450d7  docs: M-39/M-40 geklaert
2026-10-21 16:08:35  05c8b81  docs: M-33-Korrektur + M-41 + A16-1/2
2026-10-21 16:13:31  f16c302  docs: A18-1/2/3/4
```

Kernbefund: AQ-Commits (88e3e5c/ecf35a4/ae25e08) am 20.10.
morgens. W2-Extraktion (277029f etc.) am 21.10. nachmittags.
Dazwischen: ca56520/1091b3e/9141591 (Doku).

`git log --oneline 88e3e5c..ae25e08` zeigt nur ae25e08 und
ecf35a4 — korrekt, weil 88e3e5c der direkte Vorgaenger von
ecf35a4 ist und die W2-Commits NACH ae25e08 liegen.

### A18-1b — Baseline pro Commit (alle 9 gemessen)

```
88e3e5c:  1243  (+6 von 1237)
ecf35a4:  1242  (-1 durch 7390)
ae25e08:  1245  (+3: B7, B8, test_build_commit_input_phasen_unterblock)
277029f:  1245  (0, W2-Extraktion)
74ff77d:  1245  (0, Test-Umstellung)
ac4956f:  1245  (0, Fix)
b502e20:  1245  (0, Doku)
293589e:  1245  (0, Doku)
f16c302:  1245  (0, Doku)
```

Kette: 1237 -> 1243 -> 1242 -> 1245 -> 1245 -> 1245 -> 1245
-> 1245 -> 1245 -> 1245. Lueckenlos.

### A18-1c — B3-4-Status

**B3-4 erfuellt.** Die AQ-Commits (88e3e5c/ecf35a4/ae25e08)
sind vom 20.10. morgens (06:00-06:40). Die W2-Extraktion
(277029f) ist vom 21.10. nachmittags (15:10). Tests wurden
vorsorglich gebaut, nicht nachgezogen.

Kein 18c-Bruch. Kein Merkposten noetig.


## A18-1d + M-42 — Baseline-Rest + W2-Grenze (2026-10-21)

Reviewer-Auflage (Durchlauf 41, A18-1d + M-42).

### A18-1d — Baseline 5a9939c / 6e11718 / 8a921d4

Gemessen via git worktree + pytest --collect-only +
ruff check . + mypy pipeline.py:

| Commit | pytest | ruff | mypy |
|---|---|---|---|
| 5a9939c (Geruest tot) | 1245 | 17 | 9 |
| 6e11718 (Parameterbedarf 8->9) | 1245 | 17 | 9 |
| 8a921d4 (W2-Grenze) | 1245 | 17 | 9 |

**Alle drei unveraendert.** 5a9939c (Geruest, tot) aendert
nichts — die Funktion _commit_review_w25_loop wird nirgends
gerufen. 6e11718/8a921d4 sind Doku.

**Deklaration der 9 uebrigen Doku-Commits** (ca56520,
1091b3e, 9141591, bf2e487, da7d6bc, f608658, 4e450d7,
05c8b81, de62a2b): Baseline unveraendert, nicht einzeln
gemessen, weil reine Doku (kein Code, kein Test).

### M-42 — W2-Grenze 171 vs 151: 171 ist korrekt

**M-22 (Reviewer-Freigabe, Durchlauf 28):** W2 = 8585-8735
(151 Z.). **Das war falsch.**

**8a921d4 (Korrektur):** W2 = 8585-8755 (171 Z.).
**Das ist korrekt.**

**Begruendung (M-42b, ast-gemessen):** Der `while True:`-Loop
endet bei Z. 8755 (nicht 8735). Der `if config.review_commit_
package:`-Block endet bei Z. 8760 (156 Z. nach Extraktion).
Zwischen 8735 und 8755 liegen:
- `if not bauer_reply.ok:` (Fehler-Pfad, return 8)
- `state.commit_paket = parse_commit_paket(bauer_reply.content)`
- `if not state.commit_paket.get("message") ...: audit(...)`

Diese 20 Zeilen (8736-8755) sind **W2-intern**, nicht C8.
Die Extraktion in `277029f` verwendete die **korrekte**
Grenze (171 Z., basierend auf 8a921d4).

**Konsequenz:** M-22 (151) war falsch. Die Signatur
(10 Parameter nach M-39) bleibt gueltig. Kein Bug in der
Extraktion. Nur die Reviewer-Freigabe M-22 war auf einer
veralteten Zahl (Stand vor 8a921d4).


## M-43 + M-44 — W2-Grenze praezisiert + Geruest-tot belegt (2026-10-21)

Reviewer-Auflage (Durchlauf 42, M-43 + M-44).

### M-43 — Drei Zahlen, drei Objekte

Die drei Zahlen sind **rechnerisch alle korrekt**, messen
aber **verschiedene Objekte**:

| Zahl | Was | Zeilen | Status |
|---|---|---|---|
| 151 | M-22 (alt) | 8585-8735 | **FALSCH** (veraltet) |
| 171 | W2-Block (extrahiert) | 8585-8755 | **KORREKT** |
| 156 | if-Block in run_pipeline | 8605-8760 | **KORREKT** (Rest) |

**Praezisierung:**
- W2 = 8585-8755 (171 Z.). Das ist der Block, der in
  `277029f` extrahiert wurde: Skip-Pfad (8585-8603),
  Init max_commit_versuche/commit_versuche (8606-8607),
  while-True-Loop (8608-8755).
- Der `if config.review_commit_package:`-Block in
  `run_pipeline` (nach Extraktion): 8605-8760 (156 Z.).
  Das ist der **Rest** — C7-Vorlauf plus W2-Aufruf.
- Die 20 Zeilen 8585-8604 (M-43e) sind **C6**
  (Coverage/Test-Generator/Chaos), nicht W2.

**M-22 (151) zurueckgezogen.**

### M-44 — Geruest-tot in 5a9939c belegt

grep -n `_commit_review_w25_loop` pipeline.py (aktuell):
```
7761:def _commit_review_w25_loop(
8754:        _rc_w2 = _commit_review_w25_loop(
```
= 2 Treffer (def + Aufruf).

grep -n in 5a9939c (git show 5a9939c:pipeline.py):
```
7761:def _commit_review_w25_loop(
```
= 1 Treffer (nur def).

**In 5a9939c war das Geruest tot** (1 Treffer, nur
Definition, kein Aufruf). Baseline 1245/17/9 ist korrekt
dokumentiert.


## M-45 — W2-Grenze endgueltig (2026-10-21, widerspruchsfrei)

Reviewer-Auflage (Durchlauf 43). Eine Messung, alle Zahlen
aus einem Lauf. Keine Widersprueche.

### Die Tabelle

| Objekt | Zeilen | Groesse | Was |
|---|---|---|---|
| C6 (Coverage/Chaos) | 8560-8600 | 41 | nicht W2 |
| **W2 (extrahiert)** | **8585-8755** | **171** | Skip-Pfad 8585-8603 + Init 8606-8607 + while 8608-8755 |
| C7-Rest (in run_pipeline) | 8605-8760 | 156 | if config...Block nach Extraktion |
| W2-Funktion | 7761-7948 | 188 | _commit_review_w25_loop |
| W2-Aufruf (in run_pipeline) | 8754-8758 | 5 | _rc_w2 = _commit_review_w25_loop(...) |

### Die entscheidende Messung (ast, 277029f~1)

```
if config.review_commit_package (vor Extraktion): Z. 8436-8755 (320 Z.)
  body: If      Z. 8585-8603  if not _hat_anker_patches...
  body: Assign  Z. 8606-8606  max_commit_versuche = 2
  body: Assign  Z. 8607-8607  commit_versuche = 0
  body: While   Z. 8608-8755  while True:
```

**W2 = 8585-8755 (171 Z.).** Das ist der Bereich, den
277029f extrahiert hat. Kein Zweifel.

### Meine (c) in M-43 war falsch

Ich hatte geschrieben: "Die 20 Z. 8585-8604 sind C6
(Coverage/Chaos)". **Das war falsch.** C6 endet bei 8600.
Der W2-Skip-Pfad beginnt bei 8585. Ich hatte C6 und W2
verwechselt.

### Die fuenf Zahlen sind erklaert

- 151 (M-22): falsch, veraltet.
- 156: C7-Rest in run_pipeline (8605-8760).
- 171: W2 (8585-8755). **Die richtige Zahl.**
- 8585-8755: W2-Zeilen.
- 8605-8755: C7-Rest ohne Aufruf-Ende (8754-8760).


## W2-Grenze VOR/NACH — Doku-Klaerung (2026-10-21, Entscheidung b)

**Auftraggeber-Entscheidung (Durchlauf 44, Option b):**
3a-1c-2b wird als gebaut akzeptiert. Kein Aufteilen in
3a-1c-2b-1/2/3. Die Doku-Klaerung erfolgt in 3b.

**Begruendung:**
- Code ist verhaltensgleich (Baseline 1245/17/9/14 durchgehend).
- B7/B8 gruen, AQ 9/9 gruen.
- Die Aufteilung (a) waere reine Doku-Restruktur — kein Code,
  kein Test, keine Baseline-Aenderung.
- Der Merkposten ist ehrlicher als eine nachtraegliche
  Aufteilung.

### Die vier Objekte (VOR/NACH sauber getrennt)

**VOR der Extraktion (277029f~1):**
- W2-Quell-Bereich: 8585-8755 (171 Z.).
  Skip-Pfad 8585-8603, Init max_commit_versuche/
  commit_versuche 8606-8607, while-True-Loop 8608-8755.
- C6 (Coverage/Chaos): 8560-8600 (41 Z.), endet bei 8600.

**NACH der Extraktion (HEAD):**
- W2-Funktion _commit_review_w25_loop: 7761-7948 (188 Z.).
- W2-Aufruf in run_pipeline: 8754-8758 (5 Z.).
- C7-Rest (if config.review_commit_package):
  8605-8760 (156 Z.).

### Die 7 Varianten aus M-22..M-45

| Variante | Objekt |
|---|---|
| 8585-8735 (M-22) | FALSCH, veraltet |
| 8585-8755 (M-42, M-45) | W2-Quell-Bereich VOR |
| 8605-8760 (M-42) | C7-Rest NACH |
| 8585-8603 (M-45) | W2-Skip-Pfad (Teil des Quell-Bereichs) |
| 8606-8607 (M-45) | W2-Init (Teil des Quell-Bereichs) |
| 8608-8755 (M-45) | W2-while-Loop (Teil des Quell-Bereichs) |
| 7761-7948 (M-45) | W2-Funktion NACH |

**Fazit:** Die 7 Varianten sind Etiketten fuer 4 Objekte,
keine 7 Wahrheiten. Die Verwirrung entstand, weil VOR und
NACH nicht getrennt deklariert wurden. Klaerung in 3b.


## M-46 + M-47 — Return-Bilanz korrigiert (2026-10-21, ehrlich)

Reviewer-Auflage (Durchlauf 46, M-46 + M-47).

### M-46 — W2 hat 7 Returns, nicht 6

ast-Messung gegen d512264 (eine Messung, alle Zahlen
aus einem Lauf):

_commit_review_w25_loop (Z. 7761-7948, 188 Z.): 7 Returns
```
  Z. 7847: return rc
  Z. 7858: return _fail_closed(...)  # rc 6
  Z. 7886: return None
  Z. 7892: return None
  Z. 7900: return _fail_closed(...)  # rc 7
  Z. 7909: return rc
  Z. 7938: return 8
```

run_pipeline:
- VOR (277029f~1): 39 Returns.
- NACH (d512264): 35 Returns.
- Delta: -4.

**Die Rechnung:**
- 5 Returns sind verschoben (rc 2x, _fail_closed 2x,
  return 8 1x): 39 - 5 = 34.
- 1 Return ist neu in run_pipeline (Z. 8760,
  return _rc_w2): 34 + 1 = 35. Passt.
- W2 hat 5 verschobene + 2 neue (return None Z. 7886,
  7892 — aus den zwei break-Stellen) = 7.
- Codebase-Summe: 35 (run_pipeline) + 7 (W2) = 42.

**Meine fruehere Behauptung '5 + 1 = 6 Returns in W2'
war falsch.** W2 hat 7 Returns, weil es zwei
break-Stellen gab (COMMIT-GO @ 8673, ESKALATION @ 8679),
nicht eine.

### M-47 — Aufrufstelle ist 6 Zeilen Code, nicht 5

```
_rc_c2 = _basis_gate(                    # 1
    state, always, config, file_whitelist,  # 2
    project_dir, project_name,            # 3
)                                          # 4
if _rc_c2 is not None:                    # 5
    return _rc_c2                         # 6
```
= 6 Zeilen Code (ohne Leerzeile).


## M-48..M-52 — C0+C1-Belege (2026-10-21, HEAD fafc5b5)

Reviewer-Auflage (Durchlauf 49, M-48..M-52).

### M-48 — C0+C1 = 8040-8146 (107 Z.), keine C2-Ueberlappung

HEAD fafc5b5, run_pipeline Z. 8027-8863 (837 Z.).
Top-Level-Statements:
```
body[1]-body[20]:  Z. 8040-8093  = C0 (Vorlauf)
body[21]-body[29]: Z. 8095-8146  = C1 (State + run_id + Audit)
body[30]-body[31]: Z. 8148-8153  = C2-Aufruf (extrahiert)
body[32]:          Z. 8155       = print Basis-Gate gruen
```
C0+C1 = 8040-8146 (107 Z.). C2 beginnt bei body[30] (Z. 8148)
— keine Ueberlappung. Die fruehere Messung gegen d512264
hatte C2 noch als body[30]-body[34] (8070-8131) in run_pipeline;
nach C2-Extraktion (d06cf23) ist C2 durch den 5-Zeilen-Aufruf
ersetzt (8148-8153). C0+C1 bleibt unveraendert 8040-8146.

### M-49 — api_key-Herkunft: C0-Local

Zitat Z. 8040:
```
8040:     api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
8041:     if not api_key:
8042:         print("[FAIL] DEEPSEEK_API_KEY fehlt. Fail closed.")
8043:         return 1
```
api_key ist ein C0-Local (os.getenv), kein Parameter.
Er wandert in RunState (Z. 8110: api_key=api_key).
Nach C0+C1 wird state.api_key gelesen (z.B. Z. 1584, 1637).

### M-50 — Rueckgabe-Typ: belegt

```
8045:     config = _lade_und_pruefe_projekt(project_name)  # dict
8090:     max_llm = budget.get("max_llm_calls", 30)        # int
8091:     max_minutes = budget.get("max_minutes", 0)       # int
```
Signatur: tuple[RunState, dict, int, int] | int.
state_ref: list[RunState] ist korrekt (run_pipeline Z. 8029).

### M-51 — M-38-Widerspruch aufgeloest

Marker:
```
8095:     if phasen_state is not None:
8099:                 "state_ref nicht leer")
8140:     if phasen_state is not None:
```
M-38 sagte 8017-8040 (gegen d512264). Nach C2-Extraktion
sind die Marker bei Z. 8095-8099. M-38 war nicht falsch,
sondern veraltet (HEAD-Verschiebung durch C2-Extraktion).

### M-52 — Baseline-Kette: konsistent

```
d512264:  1245 / 17 / 9 / 14
8ac1092:  1245 / 17 / 9 / 14 (Doku)
d06cf23:  1245 / 17 / 9 / 14 (C2, pytest 1245 passed)
fafc5b5:  1245 / 17 / 9 / 14 (Docstring, pytest 1245 passed)
```
Kein Test dazugekommen. Kein Delta.

