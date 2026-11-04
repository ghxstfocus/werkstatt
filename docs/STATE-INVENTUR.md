# State-Inventur (OP-134)

Stand: 2026-11-04. Quelle: `tools/state_inventory.py` (read-only).
Baseline-Check: `python3 tools/state_inventory.py --check`.

**Warum diese Datei existiert:** Inter-Role-Felder im `RunState` sind
historisch gewachsen. Niemand kennt den vollstaendigen Fluss
Explorer->Scout->Architect->Planner->Builder->Reviewer->Reflection.
Ein einziger falscher Feld-Leser (`architect.py:385` liest
`explorer_findings` statt `explorer_context`) hat am 2026-11-04 einen
Loop-Lauf ruiniert, ohne dass es irgendwo auffiel. Diese Datei ist
die Mess-Grundlage fuer OP-135 (Contract-Design), OP-136 (Validierung),
OP-137 (Fix) und OP-145 (Namens-Drift).

## Ueberblick

| Kategorie | Anzahl | Bedeutung |
|---|---:|---|
| **aktiv** | 10 | direkt gelesen + direkt geschrieben |
| **read_only** | 24 | direkt gelesen, nie direkt geschrieben (Config-Input) |
| **write_only** | 16 | geschrieben, nur via `getattr` gelesen |
| **getattr_only** | 7 | nur via `getattr(state, "X")` gelesen |
| **tot** | 47 | weder direkt noch via `getattr` gelesen |
| **deklariert gesamt** | **104** | Felder in `werkstatt/state.py::RunState` |
| **ghost** | 25 | auf `state.X` zugegriffen, nicht in `state.py` deklariert |
| **gesamt (inkl. Ghosts)** | **129** | |

## Handoff-Korrekturen (2026-11-04)

Drei Behauptungen aus Handoff §7/§11 wurden gegen den Code gemessen.

| Handoff-Behauptung | Status | Beleg |
|---|---|---|
| `architect.py:385` liest `explorer_findings` statt `explorer_context` | **bestaetigt** (Symptom) | `architect.py:385`: `_exf = getattr(state, "explorer_findings", None) or {}`. `explorer_context` wird im Architect **nirgends** gelesen. |
| `api_index_cache` ist "toter Cache" | **falsch** | `architect.py:324` + `builder.py:154` lesen via `getattr`. Klassifikation: `write_only` (lebt, aber kein direkter Attribut-Leser). |
| `set_run_id` fehlt in `loop.py` | **falsch** | `loop.py:296` ruft `set_run_id(...)` auf. |

**Zusatzbefund (Handoff §4, nicht §7):** `explorer_context` ist **kein
deklariertes RunState-Feld**. Es wird dynamisch an die Dataclass-Instanz
gehaengt (`pipeline_phases.py:359: state.explorer_context = explorer_result
# type: ignore[attr-defined]`). Der Handoff-Rat "lies `explorer_context`
statt `explorer_findings`" ist nur die halbe Wahrheit: OP-137 muss
`explorer_context` **zuerst deklarieren**, dann im Architect lesen.

## Kategorien (deklarierte Felder)

### aktiv (10)

| Feld | Typ | Leser/Schreiber (Auszug) |
|---|---|---|
| `architect_prosa` | `str` | `planner.py`, `architect.py`, `builder.py` |
| `aufgabe` | `str` | `prompts.py`, `reflection.py`, `loop.py` |
| `builder_feedback` | `str` | `builder.py` |
| `mess_protokoll` | `str` | `agent.py` |
| `patches` | `list[dict[str, object]]` | `committer.py`, `builder.py`, `reflection.py` |
| `project_dir` | `Path` | `agent.py`, `apply_patches.py`, `architect.py` |
| `reflection_history` | `list[dict]` | `reflection.py`, `builder.py` |
| `reviewer_bugs_history` | `list[list[dict]]` | `pipeline_phases.py`, `gates.py`, `reviewer.py` |
| `start_monotonic` | `float` | `measurement.py`, `loop.py`, `orchestrator.py` |
| `tasks` | `list[dict[str, object]]` | `planner.py`, `gates.py`, `pipeline_phases.py` |

### read_only (24)

Config-Input, das nur gelesen wird (Konstruktor setzt sie).

`agents`, `always`, `basis_gate_test_results`, `basis_protokoll`,
`basis_protokoll_nach_apply`, `code_patches`, `commit_paket`, `docs`,
`file_whitelist`, `gelesene_dateien`, `letzter_recovery_vorschlag`,
`mess_protokoll_nach_apply`, `mess_protokoll_veraltet`, `messungen`,
`optional`, `phase_aktiv`, `phase_aktueller_index`, `phase_id`,
`phase_start_head`, `phase_titel`, `phase_unterbloecke`,
`project_name`, `projekt_stand`, `run_id`.

### write_only (16)

Geschrieben, aber nur via `getattr(state, "X")` gelesen.

`akzeptanzkriterien`, `api_index_cache`, `architect_skills_block`,
`auftrag_bereits_erfuellt_bestaetigt`, `auftrag_bereits_erfuellt_quelle`,
`explorer_findings`, `last_reject_kind`, `last_reject_reason`,
`llm_calls`, `patches_aktuell_runde`, `phasen`, `planner_skills_block`,
`preflight_fehler`, `reflection_skill_body`, `reviewer_bugs`,
`scout_api_auszug`.

### getattr_only (7)

Nur via `getattr(state, "X")` gelesen, keine direkte Attribut-Leser.

`_w51g_gemessen`, `api_key`, `follow_up_fehler`, `geladene_skills`,
`git_author_email`, `git_author_name`, `max_total_llm_s`.

### tot (47) — Delete-Kandidaten

**User-Entscheidung 2026-11-04:** "Solver sowie nie befuellt und gelesen
sind Altlasten und koennen weg da sie noch an einem alten Monolithen
hingen und jetzt outgesourced wurden."

Gruppiert:

**Solver-Altlast (5):**
`solver_aufrufe`, `solver_befunde`, `solver_config`, `solver_model`,
`solver_trigger_quellen`.

**Config-Attrappen (12):**
`builder_model`, `builder_temp`, `judge_model`, `planner_model`,
`planner_modus`, `reviewer_recovery_model`, `reviewer_verdict_model`,
`test_gen_model`, `llm_timeout_s`, `max_tokens_builder`,
`max_tokens_judge`, `max_tokens_planner`, `max_tokens_reviewer`,
`max_tokens_solver`, `max_total_llm_s`.
Hinweis: Config-Werte werden ueber andere Pfade (Config, Environment)
gelesen — diese RunState-Felder sind Attrappen. **OP-135 muss entscheiden:**
loeschen oder an `Config` binden.

**Konstruktor-Arg, nie gelesen (4):**
`agent_docs`, `block_id`, `budget`, `start_ts`.
Werden in `RunState(...)` gesetzt, aber nirgends im Code gelesen.
**OP-135:** entweder loeschen oder fuer Debug/Audit behalten.

**Nie befuellt, nie gelesen (26):**
`anker_fehler_in_folge`, `auflagen_log`, `blocker_fehler`,
`code_entwurf`, `code_entwurf_historie`, `commands_log`, `commit_review`,
`coverage_pct`, `empfehlung_log`, `ignore_fehler`,
`letzte_anker_fehler`, `letzte_builder_frage`, `letzte_ersatz_fehler`,
`letzte_explore_ergebnisse`, `letzte_reviewer_antwort`,
`letzter_patch_wirkungslos`, `letzter_plan_fehler`, `letzter_test_fehler`,
`phase_commit_pakete`, `phase_korrektur_zyklus`, `planner_resume_anzahl`,
`planner_runden`, `review_runden`, `test_vorschlaege`.

### ghost (25) — Stille Degradierungen

Auf `state.X` zugegriffen, nicht in `state.py` deklariert.
**Kern-OP-134-Akzeptanz: "Mindestens 3 stille Degradierungen
dokumentieren." Hier sind 25.**

**Explorer-Pfad (3):**
`explorer_context`, `explorer_pytest_laufzeit_s`, `explorer_ruff_befunde`.
`explorer_context` (Datei-Liste) ist der zentrale OP-137-Bug.

**Reflection-Pfad (8):**
`_reflection_bug_sigs_vorher`, `_reflection_diff_hash`,
`applied_count`, `aktuelle_task`, `last_verify_errors`,
`reflection_phase`, `reviewer_stagnation_false_positive`,
`spec_widerspruch_erkannt`.
Konsequenz fuer OP-139 (`control/reflection.py`-Split): Reflection-Logik
baut auf undeklarierten Feldern — vor dem Split **deklarieren**.

**Pipeline-Glue (9):**
`auto_approve`, `phase_review_uebersprungen`,
`progress_written_at_commit`, `reflection_erschoepft`,
`reviewer_deterministic_fail`, `scout_bereits_erfuellt`,
`split_failure_grund`, `tasks_ok_counter`, `tests`.

**Namens-Drift (2) — Bug-Kandidat fuer OP-145:**
`auftrag_bereits_erfuellt` (ghost) ist gelesen in `builder.py`,
`gates.py`, `pipeline_phases.py`.
`auftrag_bereits_erfuellt_bestaetigt` (deklariert, write_only) wird von
diesen Stellen **nicht** gelesen.
Zwei Felder fuer dasselbe Konzept, eines deklariert, eines nicht.

**Sonstige (3):**
`baseline_gruen`, `last_planner_info`, `last_verify_hart_stages`,
`messungen_nach_apply`.

## Daten-Form pro Rolle (gemessen)

**Was bekommt der Architect als Prompt-Input?**

| Feld | Typ | Im Architect-Prompt? | Quelle |
|---|---|---|---|
| `explorer_findings` | dict (`pytest_laufzeit_s`, `ruff_befunde`, ...) | **ja** | `architect.py:385-392` |
| `scout_api_auszug` | dict (Symbol-Namen-Liste) | **ja** | `architect.py:395-402` |
| `api_index_cache` | dict (AST-Info pro Modul) | **ja**, via `getattr` | `architect.py:322-324` |
| `explorer_context` | dict (Datei-Liste + Previews) | **nein** | kein Zugriff in `architect.py` |
| OP-Felder aus `docs/status` | dict (maschinenlesbar) | **ja** | `architect.py:302-312` |

**Architect hat AST-Zugriff im Prompt — ueber `api_index_cache`.**
`api_index_cache` wird in `run_architect` (`architect.py:601-603`)
via `_baue_api_index(pd)` gebaut und in `_planner_system`
(`architect.py:312`) gelesen. Ab `architect.py:340` wird er als
strukturierter AST-Block formatiert (pro Modul `### <pfad>`,
`__all__`, `def`-Signaturen, `class` + `def`-Methoden) und via
`parts.append("\n".join(_ast_lines))` (Z. ~356) an den Prompt
angehaengt. Der Architect sieht also:
- `explorer_findings` (ruff-Befunde, pytest-Laufzeit) — Z. 385
- `scout_api_auszug` (Symbol-Namen-Liste) — Z. 395
- `api_index_cache` als AST-Block (Signaturen, Klassen, Methoden) — Z. 324
- **NICHT** `explorer_context` (Datei-Liste + Previews)

**Was fehlt, ist also nicht AST — es ist die Explorer-Datei-Liste.**
Der Builder hat beides (AST via `api_index_cache` UND Datei-Liste via
`explorer_context`, `builder.py:154` + `builder.py:1305`), der
Architect nur AST + ruff-Befunde + scout-Symbole.

**Was bekommt der Builder?**

| Feld | Im Builder-Prompt? | Quelle |
|---|---|---|
| `explorer_context` | **ja**, via `getattr` | `builder.py:1305` |
| `explorer_findings` | **ja** | `builder.py:907` |
| `api_index_cache` | **ja**, via `getattr` | `builder.py:154` |
| `scout_api_auszug` | **ja** | `builder.py` (Prompt-Block) |

**Der Builder sieht mehr als der Architect.** Das ist die
AST-Asymmetrie aus MERKPOSTEN.md, bestaetigt.

**Planner + Scout** lesen `explorer_context` via `getattr`
(`planner.py:1502`, `scout.py:669-673`).

## Offene Fragen fuer OP-137

1. **Woher kommt `explorer_ctx` als Parameter von
   `_planner_system` (`architect.py:312`)?** `run_architect` bekommt
   ihn von wo? Die Datei-Liste steckt in `state.explorer_context`,
   das der Architect aber nicht liest.
2. **Warum liest Architect `explorer_findings` (ruff-Befunde) aber
   nicht `explorer_context` (Datei-Liste)?** Vermutung: Reihenfolge im
   Code — Explorer-Welle E hat `explorer_findings` eingefuehrt,
   `explorer_context` kam spaeter (Welle H?) und wurde im Architect
   nicht nachgezogen.
3. **Landet `api_index_cache` tatsaechlich im Architect-Prompt?**
   `architect.py:322-324` liest ihn; ob daraus Prompt-Text wird, ist
   aus dem `sed`-Ausschnitt nicht belegbar.
4. **`auftrag_bereits_erfuellt` vs `_bestaetigt`:** welches Feld
   gewinnt im Konflikt? **OP-145.**

## Verweise

- `tools/state_inventory.py` — Quelle der Kategorien (read-only)
- `tests/test_state_inventory.py` — Smoke-Tests + Baseline
- `docs/MERKPOSTEN.md` — "Erst messen, dann designen, dann fixen"
- `docs/adr/ADR-0012-vier-strukturmuster.md` — Muster 3 (implizite Vertraege)
- OP-134 (diese Messung), OP-135 (Design), OP-136 (Validierung),
  OP-137 (Fix `architect.py` + `explorer_context` deklarieren),
  OP-145 (Namens-Drift `auftrag_bereits_erfuellt`)
