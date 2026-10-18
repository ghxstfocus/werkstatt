# Bau-Handoff — Werkstatt

Stand: 2026-10-18 (nach Sanierungs-Welle + W52b Schritt A/B)
Werkstatt-HEAD: <nach Commit>
security-ai-HEAD: 759b9e1 (Phase 20b-U1)
Branch: main (beide Repos)
Tests (Werkstatt): 1189 passed
ruff --no-cache: 0
mypy pipeline.py: 0
Katalog (Audit-Kinds): 160
Tests (security-ai): 1452 passed

## Verweise

- `docs/OFFENE-BLOECKE.md` — Todo, priorisiert (P1/P2/P3).
- `docs/ERLEDIGT.md` — Erledigte Bloecke W1-W52b mit Commit/Tests.
- `docs/ROADMAP.md` — Uebersicht Phasen/W-Bloecke.
- `docs/ARCHITEKTUR.md` — Ziel, Rollen, Luecken (§4.7 On-Demand).
- `docs/KONVENTION.md` — Ordnerstruktur, Datei-Namen.
- `docs/ROLLEN-AUDIT.md` — Rollen-Stand (Sektion 8).
- `docs/IDEEN.md` — Wunschliste.

## Aktueller Bau-Block: W52b (On-Demand-Messung)

**Ziel:** `mess_protokoll` (String) raus. `state.messungen`
(Liste von Datei-Referenzen) + `.werkstatt/<run_id>/
messungen/<sha1>.txt` + `index.json` rein. Alle Prompt-
Bauer geben Index + Pfade, nicht den String. Der Agent
liest selbst per `read_file`.

**Gebaut (Schritt A + B):**
- `state.Messung` (dataclass): pfad, sha1, mtime,
  groesse, quelle, datei.
- `state.messungen: list[Messung]`.
- `state.messungen_nach_apply: list[Messung]`.
- `state.gelesene_dateien: dict[str, float]` (W59).
- `_schreibe_messung` (pipeline.py): schreibt Datei
  nach `.werkstatt/<run_id>/messungen/<sha1>.txt`,
  haengt an `state.messungen`, setzt
  `state.gelesene_dateien[pfad] = mtime`.
- `execute_commands`: ruft `_schreibe_messung`
  statt `state.mess_protokoll +=`.
- `_post_apply_messung`: fuellt `messungen_nach_apply`.
- `apply_code_patches`: W59-Check (Pfad in
  `gelesene_dateien`, mtime unveraendert).
  mtime-Update nach jedem `write_text` (A-W59-3).
- Katalog +2: `patch_ohne_messung`,
  `patch_datei_geaendert_seit_messung`.
- Tests: 1189 passed (26 `_setze_gelesen`-Aufrufe
  in test_pipeline.py).

**Offen (Schritt C + D + E):**
- **C** (W59-Kern): `pruefe_anker_gegen_messung`
  prueft gegen `state.mess_protokoll` (String).
  Umbau: gegen `state.messungen` (Datei-Inhalte).
  Z. 4805, 4738, 4742.
- **D** (gross): Prompt-Bauer auf Index umstellen.
  `_messwerte_fuer_prompt` (Z. 5660),
  `_messwerte_fuer_planner` (Z. 5646),
  `_build_judge_input` (Z. 6067),
  `_build_commit_input` (Z. 5736-5752),
  `_planner_user_content` (Z. 3656-3659),
  Builder-Prompt (Z. 9492, 9599, 9936, 9980).
  Ziel: Index-Block statt String.
- **E** (klein): `mess_protokoll` deprecated
  markieren, Bestandsleser dokumentieren.
- **`_gemessene_pfade`** (Z. 8624): parst String.
  Umbau: liest `state.messungen`.
- **`state.messungen_nach_apply`** muss noch in
  `_build_judge_input` genutzt werden (Schritt D).

## Naechster Block nach W52b: W61 (Rollen-Sanierung)

**Ziel:** Jede Rolle eine Aufgabe, ein Prompt,
ein Modell. Reviewer macht 3 Aufgaben
(Mess-Wahl, Commit-Review, Recovery). Judge
macht 2 (Patch, Repair). Solver nutzt
`reviewer_verdict_model` (kein `solver_model`).

**Befund (docs/ROLLEN-AUDIT.md Sektion 8):**
- `reviewer.md` 56 Z.: Mess-Wahl + Commit +
  Recovery. Ziel: < 100 Z., nur Commit-Review.
- `judge.md` 90 Z.: Patch + Repair. Ziel:
  < 150 Z., nur Patch.
- `_phase_judge_repair_runde` (Z. 2519):
  Judge repariert. Widerspruch.
- `rufe_solver` (Z. 5505): `reviewer_verdict_model`.
  `solver_model` fehlt in state.py.
- `builder.md` 647 Z.: Ziel < 300.
- `planner.md` 299 Z.: Ziel < 150.

## Naechster Block nach W61: W-Resume-Fail-Kontext

**Ziel:** Planner bekommt beim Resume den
Fail-Kontext (Test-Output, rote Tests, letzter
Patch, Recovery-Vorschlag) und liefert einen
begruendeten Plan. Neuer Skill `fail-recovery`.

**Befund:**
- `_phase_yaml_status_update` (Z. 1932):
  `letzter_befund` nur bei `no_go`, nicht bei
  `failed` (Z. 1989-1994).
- `basis_gate_test_result` (Z. 7663,
  `phase_apply`): kein `raw_tail`,
  keine `failed_test_ids`.
- `_phase_planner_resume` (Z. 10938):
  reicht `letzter_befund` nicht in den
  Planner-Prompt.
- Reviewer-Recovery (Z. 6139): antwortet leer
  (max_tokens_reviewer 1024, reviewer.md 56 Z.).

## Wichtige Merkposten

- W59-Schritt-C: Anker-Check gegen Datei-Inhalte.
- W52b-Schritt-D: Prompt-Bauer auf Index.
- W61: Rollen-Sanierung (5 Unterbloecke: a-e).
- W-Resume-Fail-Kontext: Fail-Log + Skill.
- W36-RP-a: Helper-Wartbarkeit.
- W36-RP-b-os: os.system/os.popen (0 Treffer).
- W48-A16-b-2-a-b: solver_max-Co-occur-Beleg.
- W59-2: W13b-W59-Interaktion.

## Archiv

Der vorherige Handoff (2026-10-18, 60 Zeilen)
ist in `Bau-Handoff-Archiv.md` archiviert.
Enthaelt: W1-W48, Sanierungs-Welle W51c-W30-fix.
