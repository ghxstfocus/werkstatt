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
| Commit-Body-Fehler 3a-1c-2a/2b | 2 | **Drei Commit-Bodies mit falschen Baseline-Zahlen** (hart gemessen 2026-10-21 via `git worktree` + `pytest --collect-only`): `ecf35a4` sagt "1243 -> 1242", echt: **1243 -> 1243** (netto 0, die 7390-Loeschung wurde durch +1 in anderer Datei kompensiert). `88e3e5c` sagt "1237 -> 1243 (+6)", echt: **1243 -> 1243** (die 6 B1a/B1b/B2/B3/B4/B6 ersetzen 6 alte Struktur-Tests, keine Addition). `ae25e08` sagt "1242 -> 1245 (+3)", echt: **1243 -> 1245 (+2)** (B7, B8; 6887-Ersatz ist netto 0). **Echte Kette: 1243 -> 1243 -> 1245.** Zusaetzlich: `ae25e08` sagt "W2-Signatur frozen (18c): 11 Parameter", echt: **9 Parameter** (korrigiert in 6e11718, Block 3). Konsequenz: Commit-Body-Baseline-Zahlen kuenftig **vor** dem Commit mit `pytest --collect-only` messen, nicht schaetzen (Reviewer-Muster "Zahl aus Chat-Gedaechtnis", UEBERGABE-3A-2026-10-19.md). Kein Blocker fuer C2-Start, aber Pflicht-Reparatur im C2-doc-Commit. | klein | offen |
| Position A vs B (Code-Reihenfolge) | 2 | **Entschieden 2026-10-21 (Reviewer-Frage 3, Durchlauf 36):** Position **A** = `_basis_gate` (C2) vor `run_pipeline`, `_commit_review_w25_loop` (C7) bleibt wo er ist (vor `_basis_gate`). **Begruendung:** Extraktions-Bloecke in umgekehrter Abhaengigkeits-Reihenfolge erzeugen am wenigsten Ueberraschung. Die Doku-Konvention C0-C9 (293589e) ist **orthogonal** zur Code-Reihenfolge. 293589e etabliert Doku, nicht Code-Reihenfolge. **Code-Reihenfolge folgt NICHT C-Nummerierung.** Keine stille Konvention (Reviewer-Auflage). | klein | done |
| Struktur-Tests umstellen | 2 | **5 von ~15 erledigt (74ff77d).** Umgestellt: TestCommitReviewNewFileSkip 4x + TestW11 (getsource run_pipeline -> _commit_review_w25_loop). **Rest ~10** folgen mit 3a-1c-3 (C0/C1/C2/C6) und 3a-1c-4 (C8/C9), weil dort die naechsten getsource-Ziele wandern. test_fail_closed_pfad_bleibt (Z. 5416) bleibt absichtlich auf run_pipeline. Duale Quellen-Pruefung oder Verhaltens-Test (A9-13, A10-13b). | gross | offen |
| 3a-1c-2-V2-Groesse | 3 | V2 = 303 Z., 13 Steuerungsstellen, 12 Parameter. Zu gross fuer 1-Rutsch. Zerlegung V2a/V2b vor 3a-1c-2 pruefen (A8-2-nach-3b). | mittel | offen |
| 3a-1c-2b (W2-Extraktion) | 3 | ERLEDIGT (277029f + 74ff77d + ac4956f). W2 = 8585-8755 (171 Z.) nach `_commit_review_w25_loop` extrahiert. 9 Parameter (Signatur-Freeze 18c): _diff_name_only, _hat_anker_patches, api_key, builder_prompt, max_llm, max_minutes, project_dir (Path!), reviewer_prompt, state. Zwei break (COMMIT-GO, ESKALATION) -> return None. Aufrufstelle run_pipeline Z. 8754-8760. 5 Struktur-Tests umgestellt (74ff77d): TestCommitReviewNewFileSkip 4x + TestW11. test_fail_closed_pfad_bleibt unberuehrt (Fail-Closed-Pfad blieb in run_pipeline). mypy-Fix (ac4956f): project_dir str->Path (19->9). Baseline 1245 / ruff 17 / mypy 9 / AST+Katalog 14. AQ-Regressionslatte 9/9 gruen. | gross | done |
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

### A14-1 — Baseline VOR/NACH

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
(A14-1: 1242 -> 1243; 11 -> 9 Parameter). Beide Korrekturen sind
in `OFFENE-BLOECKE.md` als Merkposten dokumentiert.

