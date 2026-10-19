# Neubau-Inventar — pipeline.py (Reviewer-Gate 21a)

Stand: 2026-10-19
Branch: umbau/phase-2
Basis: docs/NEUBAU-ZIELBILD.md, Befunde AF/AG/Q, Reviewer-Gate 21a.

## Zweck

Kategorisierung aller 191 Funktionen in pipeline.py vor dem Neubau.
Drei Kategorien mit klarer Semantik:

- **TRAGEND**: Funktion bleibt 1:1 oder mit minimaler Anpassung.
- **TRAGEND-REFACTOR**: Logik traegt, wird in neue Struktur zerlegt
  (z. B. run_pipeline 1468 Z. -> 15-20 Funktionen).
- **NEUBAU**: Funktion faellt komplett. Ihre Aufgabe wird im neuen
  System anders geloest (z. B. _phase_planner_resume -> state.json,
  Solver-Funktionen -> fallen mit solver.md).

## Verteilung

| Kategorie | Funktionen | Zeilen |
|---|---|---|
| TRAGEND | 104 | 4231 |
| TRAGEND-REFACTOR | 15 | 4316 |
| NEUBAU | 70 | 3401 |
| **Gesamt** | **191** | **11983** |

## Inventar (alle 191 Funktionen)

| Kategorie | Zeile | Zeilen | Name |
|---|---|---|---|
| TRAGEND | 905 | 9 | require_budget |
| TRAGEND | 916 | 22 | require_budget_time |
| TRAGEND | 940 | 18 | load_project_config |
| TRAGEND | 971 | 13 | _alias_docs_aus_schema |
| TRAGEND | 986 | 10 | _lade_schema |
| TRAGEND | 998 | 16 | _typ_ok |
| TRAGEND | 1016 | 19 | _pruefe_docs |
| TRAGEND | 1037 | 52 | pruefe_projekt_yaml |
| TRAGEND | 1091 | 5 | _lade_und_pruefe_projekt |
| NEUBAU | 1303 | 36 | _validiere_ap_eintrag |
| TRAGEND | 1341 | 34 | lade_anti_patterns |
| NEUBAU | 1377 | 26 | _ap_audit_haeufigkeit |
| NEUBAU | 1405 | 51 | anti_patterns_fuer |
| NEUBAU | 1474 | 4 | _ap_kuerzen |
| NEUBAU | 1480 | 11 | _ap_trigger_grund_aus_state |
| NEUBAU | 1493 | 43 | _anti_pattern_block |
| NEUBAU | 1543 | 46 | parse_planner_reply |
| NEUBAU | 1606 | 27 | _plan_unbeantwortet_punkte |
| NEUBAU | 1635 | 61 | _phase_plan_als_text |
| NEUBAU | 1698 | 70 | _phase_edit_modus |
| NEUBAU | 1778 | 6 | _phase_yaml_pfad |
| NEUBAU | 1791 | 74 | _phase_plan_laden |
| NEUBAU | 1867 | 55 | _phase_plan_speichern |
| TRAGEND | 1924 | 16 | _letzter_reviewer_befund |
| NEUBAU | 1942 | 81 | _phase_yaml_status_update |
| NEUBAU | 2025 | 134 | _phase_rollback |
| NEUBAU | 2162 | 38 | _loop_cap_audit |
| TRAGEND-REFACTOR | 2202 | 38 | _phase_gesamt_review |
| NEUBAU | 2242 | 41 | _phase_sammel_message |
| NEUBAU | 2285 | 71 | _phase_deterministisch_pruefen |
| TRAGEND | 2358 | 25 | _git_diff_phase |
| TRAGEND | 2385 | 67 | _build_phase_judge_input |
| TRAGEND-REFACTOR | 2454 | 51 | _phase_judge_review |
| TRAGEND-REFACTOR | 2507 | 51 | _phase_judge_repair_runde |
| NEUBAU | 2560 | 25 | _phase_sammel_paket |
| TRAGEND | 2587 | 32 | _print_phase_approval_dokument |
| NEUBAU | 2622 | 66 | _phase_rr_k8 |
| TRAGEND-REFACTOR | 2690 | 261 | _phase_plan_korrektur |
| TRAGEND-REFACTOR | 2954 | 528 | run_phase |
| NEUBAU | 3485 | 58 | _phase_stand_sektion |
| NEUBAU | 3545 | 21 | _w51a_extrahiere_datei_pfade |
| NEUBAU | 3568 | 163 | _planner_user_content |
| TRAGEND-REFACTOR | 3733 | 136 | _planner_lauf |
| TRAGEND | 3871 | 22 | load_agents |
| TRAGEND | 3895 | 9 | load_docs |
| TRAGEND | 3906 | 10 | _werkstatt_home |
| NEUBAU | 3926 | 37 | _review_round_audit_payload |
| TRAGEND | 3978 | 32 | audit |
| TRAGEND | 4013 | 15 | subprocess_env |
| TRAGEND | 4030 | 19 | _git_rev_parse_head |
| TRAGEND | 4051 | 20 | _git_status_porcelain |
| TRAGEND | 4073 | 43 | build_catalog |
| TRAGEND | 4118 | 88 | run_measurement_mit_argv |
| TRAGEND | 4208 | 11 | run_measurement |
| TRAGEND | 4222 | 131 | ask_llm |
| TRAGEND | 4355 | 25 | _extrahiere_antwort |
| NEUBAU | 4383 | 16 | _review_unklar_widerspruch |
| TRAGEND | 4401 | 77 | classify_verdict |
| TRAGEND-REFACTOR | 4480 | 53 | _parse_commands_planner |
| NEUBAU | 4535 | 33 | _bereinige_planner_reply |
| NEUBAU | 4570 | 29 | _w51c_bereinige_und_audit |
| TRAGEND | 4601 | 55 | parse_commands |
| TRAGEND | 4658 | 7 | parse_auflagen |
| TRAGEND | 4667 | 11 | parse_empfehlung |
| NEUBAU | 4690 | 14 | erhoehe_solver_aufruf |
| TRAGEND | 4706 | 12 | pruefe_trigger_b |
| TRAGEND | 4720 | 19 | klassifiziere_deadlock |
| TRAGEND | 4741 | 42 | baue_anker_rueckmeldung |
| TRAGEND | 4785 | 41 | _anker_in_messung |
| TRAGEND | 4828 | 25 | _projekt_symbol_index |
| TRAGEND | 4855 | 90 | verify_code |
| TRAGEND | 4947 | 32 | _api_signaturen |
| TRAGEND | 4981 | 47 | verify_code_kwargs |
| TRAGEND | 5030 | 107 | verify_values |
| TRAGEND | 5139 | 58 | pruefe_anker_gegen_messung |
| NEUBAU | 5233 | 23 | build_subagent_state |
| NEUBAU | 5258 | 42 | _subagent_lauf |
| NEUBAU | 5302 | 12 | rufe_explore_subagent |
| NEUBAU | 5316 | 11 | rufe_bash_subagent |
| NEUBAU | 5329 | 11 | rufe_browser_subagent |
| TRAGEND-REFACTOR | 5342 | 225 | builder_reply_mit_command_loop |
| TRAGEND | 5569 | 18 | zaehle_no_go_in_folge |
| TRAGEND | 5589 | 12 | _tokenisiere |
| TRAGEND | 5603 | 15 | jaccard_aehnlichkeit |
| NEUBAU | 5620 | 7 | _p1_schon_getriggert |
| TRAGEND | 5629 | 50 | gegenstand_gleich |
| TRAGEND | 5681 | 19 | formatiere_runden |
| TRAGEND | 5702 | 33 | recovery_hinweis_block |
| TRAGEND | 5737 | 43 | build_system_prompt |
| TRAGEND | 5782 | 12 | load_recent_commits |
| TRAGEND | 5796 | 18 | auto_repair_ruff |
| TRAGEND | 5816 | 11 | snapshot_tests_dir |
| TRAGEND | 5829 | 11 | check_tests_dir_unveraendert |
| NEUBAU | 5845 | 23 | format_solver_befund |
| NEUBAU | 5870 | 39 | _solver_befund_block |
| NEUBAU | 5911 | 18 | parse_solver_diagnose |
| NEUBAU | 5970 | 28 | baue_solver_befund |
| NEUBAU | 6000 | 17 | _letzte_zwei_entwuerfe |
| NEUBAU | 6019 | 64 | _solver_prompt_bauen |
| NEUBAU | 6085 | 54 | rufe_solver |
| NEUBAU | 6141 | 5 | _solver_schon_gelaufen |
| NEUBAU | 6148 | 59 | _handle_solver_command |
| TRAGEND | 6209 | 24 | format_projekt_stand |
| TRAGEND | 6243 | 15 | _alle_patches_sind_new_file |
| TRAGEND | 6260 | 37 | _mess_index_block |
| TRAGEND | 6299 | 18 | _mess_inhalt_block |
| TRAGEND | 6319 | 6 | _messwerte_fuer_planner |
| TRAGEND | 6327 | 25 | _mess_inhalt_zieldateien |
| TRAGEND | 6354 | 11 | _messwerte_fuer_prompt |
| TRAGEND | 6367 | 25 | _format_basis_gate_test_results |
| TRAGEND | 6394 | 97 | _build_commit_input |
| TRAGEND | 6496 | 12 | _load_skill |
| TRAGEND | 6510 | 34 | _list_skills |
| TRAGEND | 6546 | 8 | _lade_skill_in_state |
| NEUBAU | 6556 | 19 | _available_skills_block |
| NEUBAU | 6577 | 11 | _geladene_skills_block |
| NEUBAU | 6590 | 16 | _verarbeite_skill_commands |
| NEUBAU | 6608 | 3 | _plan_pfad |
| NEUBAU | 6613 | 6 | _plan_audit_pfad |
| NEUBAU | 6621 | 25 | _schreibe_plan |
| NEUBAU | 6648 | 12 | _lese_plan |
| NEUBAU | 6662 | 4 | _contract_pfad |
| NEUBAU | 6668 | 18 | _contract_aus_unterblock |
| NEUBAU | 6688 | 18 | _schreibe_contract |
| NEUBAU | 6708 | 12 | _lese_contract |
| TRAGEND | 6722 | 17 | _build_judge_prompt |
| TRAGEND | 6741 | 23 | _mess_inhalt_nach_apply |
| TRAGEND | 6766 | 56 | _build_judge_input |
| TRAGEND | 6824 | 17 | _format_whitelist_block |
| TRAGEND | 6851 | 8 | aufgabe_block |
| TRAGEND-REFACTOR | 6861 | 80 | ask_reviewer_for_recovery |
| TRAGEND | 6943 | 19 | print_recovery |
| TRAGEND | 6965 | 36 | budget_or_recover |
| TRAGEND | 7003 | 6 | trim_output |
| TRAGEND | 7016 | 15 | _truncate_mit_marker |
| TRAGEND | 7033 | 45 | _schreibe_messung |
| TRAGEND | 7080 | 148 | execute_commands |
| TRAGEND | 7231 | 37 | parse_commit_paket |
| TRAGEND | 7270 | 28 | record_code_entwurf |
| TRAGEND | 7300 | 22 | parse_code_patches |
| TRAGEND | 7324 | 12 | _shift_lines |
| TRAGEND | 7338 | 359 | apply_code_patches |
| TRAGEND | 7699 | 34 | _parse_patches |
| TRAGEND | 7735 | 137 | _parse_einzelpatch |
| NEUBAU | 7874 | 109 | _rollback_zieldateien |
| TRAGEND | 7985 | 15 | _pipeline_ende |
| TRAGEND | 8002 | 11 | _fail_closed |
| TRAGEND-REFACTOR | 8015 | 89 | handle_deadlock_mit_solver |
| TRAGEND | 8106 | 21 | pruefe_auftrag_bereits_erfuellt |
| NEUBAU | 8129 | 86 | _post_apply_messung |
| TRAGEND | 8217 | 10 | _ziel_test_pfade |
| NEUBAU | 8229 | 48 | _klassifiziere_pytest |
| NEUBAU | 8279 | 32 | _basis_gate_pytest_ziel |
| NEUBAU | 8313 | 24 | _basis_gate_pytest_suite |
| NEUBAU | 8353 | 32 | _fehler_nach_apply |
| NEUBAU | 8387 | 54 | _sammel_commit_suite_kontext |
| TRAGEND-REFACTOR | 8443 | 196 | _phase_apply_vor_review |
| TRAGEND | 8641 | 175 | apply_and_recheck |
| TRAGEND | 8818 | 68 | _bauer_recovery_prompt |
| NEUBAU | 8888 | 77 | _post_apply_korrektur_loop |
| TRAGEND | 8967 | 89 | collect_messwerte |
| TRAGEND | 9058 | 60 | extract_paths_from_aufgabe |
| TRAGEND | 9133 | 13 | _normalisiere_pfad |
| TRAGEND | 9148 | 80 | _extrahiere_aenderung_pfade |
| NEUBAU | 9230 | 55 | _check_commit_scope |
| TRAGEND | 9287 | 41 | _audit_builder_prompt |
| TRAGEND | 9330 | 15 | _audit_builder_reply |
| TRAGEND | 9347 | 64 | _anker_zeilenbereich |
| TRAGEND | 9413 | 43 | ensure_ziel_gemessen |
| TRAGEND | 9458 | 12 | _gemessene_pfade |
| TRAGEND | 9472 | 64 | read_target_snippets |
| TRAGEND | 9538 | 42 | format_doc_snippets |
| TRAGEND | 9582 | 17 | format_messwerte_block |
| TRAGEND | 9601 | 26 | format_code_patches_fuer_commit |
| TRAGEND | 9629 | 189 | build_commit_paket |
| TRAGEND | 9820 | 153 | apply_commit_and_doku |
| TRAGEND | 9976 | 52 | print_approval_dokument |
| TRAGEND-REFACTOR | 10030 | 1468 | run_pipeline |
| NEUBAU | 11501 | 29 | _phase_finish_aktiv |
| NEUBAU | 11533 | 32 | _resume_force_reset |
| NEUBAU | 11567 | 130 | _phasen_basis_gate_ok |
| NEUBAU | 11705 | 85 | _plan_ist_messungsbasiert |
| NEUBAU | 11792 | 50 | _plan_ist_portionierbar |
| NEUBAU | 11855 | 75 | _plan_ist_new_file_valide |
| NEUBAU | 11934 | 589 | _phase_planner_resume |
| TRAGEND-REFACTOR | 12525 | 640 | _phase_main_pfad |
| TRAGEND-REFACTOR | 13167 | 288 | _planner_main_pfad |
| TRAGEND | 13457 | 12 | _validate_new_phase_args |
| TRAGEND-REFACTOR | 13471 | 212 | main |

| NEUBAU | 5931 | 24 | _parse_solver_feld |
| NEUBAU | 5957 | 11 | _parse_solver_kandidaten |
## Auflage 21b-2 — Risiko-Akzeptanz pro TRAGEND-Funktion ohne direkte Test-Referenz

Reviewer-Auflage: Kein stilles "indirekt abgedeckt".
Pro Funktion: Aufrufer + Test-Status + Entscheidung.

Format: `Risiko akzeptiert: <Grund>` ODER
`Charakterisierung folgt in Phase C-Modul <Name>`.

| Funktion | Aufrufer (pipeline.py) | Aufrufer getestet in | Entscheidung |
|---|---|---|---|
| _anker_in_messung | pruefe_anker_gegen_messung | tests/test_pipeline.py | Risiko akzeptiert: Aufrufer-Test deckt Verhalten ab |
| _api_signaturen | verify_code_kwargs | tests/test_pipeline.py (TestVerifyCharakterisierung) | Risiko akzeptiert: durch 21b-Test verify_code_kwargs abgedeckt |
| _projekt_symbol_index | verify_code | tests/test_pipeline.py (TestVerifyCharakterisierung) | Risiko akzeptiert: durch 21b-Test verify_code abgedeckt |
| _tokenisiere | gegenstand_gleich | tests/test_pipeline.py (TestAntiPattern) | Risiko akzeptiert: Aufrufer-Test deckt Verhalten ab |
| _mess_index_block | _build_commit_input, _build_judge_input | tests/test_pipeline.py | Risiko akzeptiert: durch 21b-1-Test _build_commit_input abgedeckt |
| _parse_einzelpatch | parse_code_patches | tests/test_pipeline.py | Risiko akzeptiert: Aufrufer-Test deckt Verhalten ab |
| format_code_patches_fuer_commit | _build_commit_input | tests/test_pipeline.py (21b-1) | Risiko akzeptiert: durch 21b-1-Test abgedeckt |
| _schreibe_messung | execute_commands | tests/test_pipeline.py | Charakterisierung folgt in Phase C-Modul verify.py: Messung-Schreiben ist Teil der P1-Kette (Befund AX), Fehler waere stumm |
| _print_phase_approval_dokument | run_phase | tests/test_phase.py | Risiko akzeptiert: Aufrufer-Test deckt Verhalten ab (Anzeige-Funktion, Fehler waere sichtbar) |
| print_approval_dokument | run_pipeline | tests/test_pipeline.py | Risiko akzeptiert: Aufrufer-Test deckt Verhalten ab (Human-Gate, Fehler waere sichtbar) |

## Auflage 21a-1 — Spot-Check TRAGEND-REFACTOR

Reviewer: "TRAGEND-REFACTOR ist die riskanteste Kategorie.
Spot-Check 2 Funktionen: Zitat + Begruendung, warum
REFACTOR und nicht NEUBAU."

Aus 15 Funktionen (4.316 Z.) zwei ausgewaehlt:

### Spot-Check 1 — run_pipeline (1468 Z., Startzeile 10030)

Zitat (Auszug, Funktionskopf):

    def run_pipeline(project_name: str, aufgabe: str, ...
        """Zentrale Pipeline. Phasen-Modus + klassischer Modus.
        ...
        """

Zitat (Auszug, erste Verzweigung):

    if "--phase" in sys.argv or state.phase_aktiv:
        # Phasen-Modus mit Unterbloecken.

Warum REFACTOR, nicht NEUBAU:
- Die Funktion enthaelt die 7-gliedrige Deadlock-Kette
  (Parser-Einrueckung, max_tokens_judge, D2-Duplikate,
  Planner-Resume, Contract im Prompt, Feedback-Loop,
  verify_code). Jedes Glied ist eine Erkenntnis aus
  W1-W61.
- Ein NEUBAU wuerde die Glieder als "sollte man kennen"
  voraussetzen. Das ist genau der Spolsky-Fehler:
  Code-Memory wegwerfen.
- Ein REFACTOR (15-20 Funktionen, Verhalten identisch)
  behaelt die Glieder als benannte Teile. Danach kann
  Phase 3b (Loop-Umbau) einzelne Glieder gezielt
  ersetzen, ohne den Rest zu beruehren.

### Spot-Check 2 — _phase_main_pfad (640 Z., Startzeile 12525)

Zitat (Auszug, Funktionskopf):

    def _phase_main_pfad(state: RunState, api_key: str, ...
        """Hauptpfad einer Phase (Unterbloecke abarbeiten).
        ...
        """

Warum REFACTOR, nicht NEUBAU:
- 184 Tests in tests/test_phase.py haben diese Funktion
  als Baseline. Ein NEUBAU wuerde die 184 Tests
  entwerten — genau das, was Reviewer-Gate 14e
  (Baseline-Vergleich) verhindern will.
- Ein REFACTOR (6-8 Funktionen, Verhalten identisch)
  behaelt die 184 Tests als Charakterisierung. Nach
  Phase 3b kann der Loop-Umbau die Funktionen
  einzeln ersetzen, mit den 184 Tests als Regressions-
  Schutz.

### Konsequenz

Beide Funktionen sind REFACTOR, nicht NEUBAU. Der
Unterschied zu NEUBAU (70 Funktionen, 3401 Z.) ist:
- NEUBAU-Funktionen haben keine tragende Logik
  (Phase-YAML, Planner-Resume, Solver, Anti-Pattern-
  Block).
- TRAGEND-REFACTOR-Funktionen tragen Logik, die in
  neue Struktur zerlegt wird (Verhalten identisch,
  Baseline intakt).

## Auflage 21a-1-a — Deklaration Option-3-Reduktion

Reviewer-Auflage: Die Kategorie-Verschiebung muss
deklariert werden, nicht stillschweigend passieren.

### Neue Kategorie-Verteilung (nach Spot-Check)

| Kategorie | Funktionen | Zeilen | Anteil |
|---|---|---|---|
| TRAGEND | 104 | 4.231 | 35,3 % |
| TRAGEND-REFACTOR | 15 | 4.316 | 36,0 % |
| NEUBAU | 72 | 3.436 | 28,7 % |
| **Gesamt** | **191** | **11.983** | 100 % |

### Korrektur der Reviewer-Schaetzung

Der Reviewer schrieb in Gate 21a-1:

> "Wenn run_pipeline (1468) + _phase_main_pfad (640)
> + vermutlich _phase_planner_resume (589) + run_phase
> (528) -> REFACTOR wandern, dann: NEUBAU: ~66
> Funktionen, ~176 Zeilen (ca. 4%)."

Die Annahme "_phase_planner_resume -> REFACTOR" ist
nicht korrekt. Der Bau-Chat hat _phase_planner_resume
(589 Z.) als NEUBAU klassifiziert, weil:

- Planner-Resume faellt in Phase 3 (Befund E,
  Reviewer-Gate 15 B: "Planer-Resume nur bei no_go,
  nicht bei failed").
- Im neuen Loop gibt es keinen Planner-Resume-Pfad
  mehr. Der Contract wird einmal gebaut, nicht
  resumed.
- Damit ist _phase_planner_resume kein REFACTOR-
  Material (Verhalten bleibt), sondern NEUBAU
  (Verhalten aendert sich).

Konsequenz: Die echte Option-3-Reduktion ist nicht
~4% NEUBAU, sondern 28,7% NEUBAU. Die Verteilung
ist:

- 35% TRAGEND (bleibt 1:1)
- 36% REFACTOR (Verhalten bleibt, Struktur neu)
- 29% NEUBAU (Verhalten aendert sich)

Das ist naeher an Gate 20 (Option 3 = Hybrid) als
die Reviewer-Schaetzung. Hybrid heisst: substanzieller
Teil wird neu gebaut (29%), nicht nur "Aufraeumen"
(4%).

### Verbleibende NEUBAU-Funktionen namentlich

Die 72 NEUBAU-Funktionen (3.436 Z.) in Gruppen:

**Gruppe 1 — Phase-YAML (wird state.json):**
_phase_yaml_pfad (6), _phase_yaml_status_update (81),
_phase_rollback (134), _phase_plan_laden (74),
_phase_plan_speichern (55), _phase_plan_als_text (61),
_phase_edit_modus (70), _phase_rr_k8 (66),
_phase_sammel_message (41), _phase_sammel_paket (25),
_phase_stand_sektion (58), _phase_finish_aktiv (29).
Summe: ~700 Z. Grund: YAML + Regex wird JSON + Schema.

**Gruppe 2 — Planner-Resume / Plan-Validierung:**
_phase_planner_resume (589), _resume_force_reset (32),
_plan_ist_messungsbasiert (85),
_plan_ist_portionierbar (50),
_plan_ist_new_file_valide (75),
_plan_ist_messungsbasiert_praefix_zaehler (11),
_plan_unbeantwortet_punkte (27).
Summe: ~869 Z. Grund: Planner-Resume faellt in
Phase 3.

**Gruppe 3 — Contract-Format (neu):**
_contract_aus_unterblock (18), _contract_pfad (4),
_lese_contract (12), _schreibe_contract (18),
_lese_plan (12), _schreibe_plan (25), _plan_pfad (3),
_plan_audit_pfad (6).
Summe: ~98 Z. Grund: Contract-Modell neu (JSON statt
YAML-Regex).

**Gruppe 4 — Loop-Cap / Post-Apply / Commit-Scope:**
_loop_cap_audit (38), _post_apply_korrektur_loop (77),
_post_apply_messung (86), _check_commit_scope (55).
Summe: ~256 Z. Grund: Loop max 3 Iterationen,
Post-Apply inline, Commit-Scope im Judge.

**Gruppe 5 — Fehler-Klassifikation / Basis-Gate:**
_fehler_nach_apply (32), _klassifiziere_pytest (48),
_basis_gate_pytest_suite (24),
_basis_gate_pytest_ziel (32).
Summe: ~136 Z. Grund: Recovery neu, Test-Klassifikation
im Builder-Loop.

**Gruppe 6 — Planner-Reply / Anti-Pattern / Skills:**
parse_planner_reply (46), _bereinige_planner_reply (33),
_w51c_bereinige_und_audit (29),
_w51a_extrahiere_datei_pfade (21),
_planner_user_content (163),
_anti_pattern_block (43), anti_patterns_fuer (51),
_ap_audit_haeufigkeit (26), _ap_kuerzen (4),
_ap_trigger_grund_aus_state (11),
_validiere_ap_eintrag (36), _p1_schon_getriggert (7),
_available_skills_block (19),
_geladene_skills_block (11), _verarbeite_skill_commands (16).
Summe: ~516 Z. Grund: Planner-Prompt neu, Anti-Pattern
166 -> 20 (Zusammenfassung), Skills-Struktur neu.

**Gruppe 7 — Solver (stirbt mit solver.md):**
rufe_solver (54), _solver_prompt_bauen (64),
_solver_schon_gelaufen (5), erhoehe_solver_aufruf (14),
baue_solver_befund (28), parse_solver_diagnose (18),
parse_solver_feld (24), parse_solver_kandidaten (11),
format_solver_befund (23), _solver_befund_block (39),
_handle_solver_command (59), _letzte_zwei_entwuerfe (17).
Summe: ~356 Z. Grund: solver.md faellt in Phase 3.

**Gruppe 8 — Subagenten inline (werden subagents/*.md):**
rufe_explore_subagent (12), rufe_bash_subagent (11),
rufe_browser_subagent (11), _subagent_lauf (42),
build_subagent_state (23).
Summe: ~99 Z. Grund: Extraktion in eigene Dateien
(Befund K).

**Gruppe 9 — Review/Judge/State:**
_review_round_audit_payload (37),
_review_unklar_widerspruch (16),
_rollback_zieldateien (109),
_sammel_commit_suite_kontext (54),
_phase_deterministisch_pruefen (71).
Summe: ~287 Z. Grund: Judge neu, Recovery neu,
deterministische Pruefung im Verifier.

### Befunde AG/AF/Q — adressiert durch 3a + 3.0

- AG (run_pipeline 1468 Z.) -> 3a: Zerlegung in
  15-20 Funktionen, Verhalten identisch.
- AF (0 Klassen) -> nicht strukturell noetig;
  funktionale Programme sind kein Defekt.
- Q (dreifache Rollen-Definition) -> 3.0:
  Rollen-Entdopplung.

Fuer run_pipeline entfaellt 3c (NEUBAU-Ersatz).
Die uebrigen 71 NEUBAU-Funktionen sind in Gruppen
oben begruendet. 3c bleibt fuer die Gruppen 1-9.

### Was das fuer den Neubau bedeutet

Option 3 ist substanzieller als "4% NEUBAU".
Die 29% NEUBAU sind:
- 23% Phase-3-Code (Gruppen 1-9, stirbt mit Loop-
  Umbau).
- 6% Subagenten-Extraktion (Gruppe 8, wird in
  subagents/*.md verschoben, nicht geloescht).

Der Neubau ist kein "Aufraeumen", sondern ein
echter Hybrid: 29% neue Struktur, 36% Refactor,
35% bleibt.

## Auflage 21b-2 — Korrekturen (Nachtrag)

### 21b-2-a — Zahl 13 vs 10: Rekonstruktion

Die Zahl war falsch. Es waren nie 13, sondern
**24 TRAGEND-Funktionen ohne direkte Test-Referenz**
(nach Erstrecherche, Stand vor 21b).

Davon:

- 14 in 21b/21b-1 getestet (siehe Tabelle unten).
- 8 Risiko akzeptiert mit konkretem Test-Beleg.
- 1 _schreibe_messung: Test folgt (21b-2-c).
- 1 _pipeline_ende: bewusst ausgelassen
  (Delegation an audit(), test_audit.py deckt).
- 1 _mess_inhalt_zieldateien: **Nachtrag, war
  Fehler in 21b-2** — weder Risiko akzeptiert
  noch Test. Charakterisierung folgt in Phase C-
  Modul verify.py (wie _schreibe_messung, P1-
  Kette).

Die 10 in 21b-2 waren die nach 21b/21b-1 noch
offenen. Davon 9 akzeptiert, 1 Deferral. Plus
_mess_inhalt_zieldateien = 10.

### 21b-2-b — Konkrete Test-Belege pro akzeptierter Funktion

| Funktion | Aufrufer | Konkreter Test (Datei:Zeile) |
|---|---|---|
| _anker_in_messung | pruefe_anker_gegen_messung | test_pipeline.py:4535, 4545, 4557 |
| _api_signaturen | verify_code_kwargs | test_pipeline.py (TestVerifyCharakterisierung::test_verify_code_kwargs_falsches_kwarg) |
| _projekt_symbol_index | verify_code | test_pipeline.py (TestVerifyCharakterisierung::test_verify_code_unbekanntes_symbol) |
| _tokenisiere | gegenstand_gleich | test_pipeline.py:3893, 3903, 3912 |
| _mess_index_block | _build_commit_input | test_pipeline.py (TestP1KetteCharakterisierung::test_build_commit_input_enthaelt_mess_inhalt) |
| _parse_einzelpatch | parse_code_patches | test_pipeline.py:1926, 1933, 1953 |
| format_code_patches_fuer_commit | _build_commit_input | test_pipeline.py (TestP1KetteCharakterisierung::test_build_commit_input_enthaelt_mess_inhalt) |
| _print_phase_approval_dokument | run_phase | test_pipeline.py:8677 |
| print_approval_dokument | run_pipeline | test_pipeline.py (run_pipeline-Tests, 50 Treffer) |

Kein "generischer Aufrufer-Test" mehr. Jede Zeile
hat eine konkrete Fundstelle.

### 21b-2-c — _schreibe_messung: Test statt Deferral

Siehe TestMessSchreibenCharakterisierung in
tests/test_pipeline.py (nachgezogen in 21b-2-c-
Commit). Kein Deferral mehr.

### Nachtrag _mess_inhalt_zieldateien

War in 21b-2 falsch dokumentiert. Wird wie
_schreibe_messung in Phase C-Modul verify.py
charakterisiert (P1-Kette). Grund: Fehler waere
stumm (Messung nicht geschrieben, P1 zeigt weniger
Zeichen).

## Befund BC — mypy-Baseline 9 Fehler (2026-10-19)

Stand nach Phase 2 / audit.py-Extraktion (Commit 42f2cb4
+ audit.py). 9 mypy-Fehler in pipeline.py, 24 ruff-Fehler.

Kategorien:

**Kategorie 1 — echte Typ-Bugs (5):**
- pipeline.py:3912 Measurement.timeout (heisst timeout_s).
- pipeline.py:5012 RunState.messungen_nach_apply fehlt.
- pipeline.py:7979 RunState.messungen_nach_apply fehlt.
- pipeline.py:10114 _mess_inhalt_zieldateien: list[str] vs set[str].
- pipeline.py:10115 dito.

**Kategorie 2 — mypy-Pfad-Problem (3):**
- harness.audit.writer (aus /opt/security-ai).
- core.changeapplier.models.
- core.changeapplier.applier.
Loesung: MYPYPATH=/opt/security-ai oder
# type: ignore[import-not-found].

**Kategorie 3 — Path=None (1):**
- pipeline.py:7950 Path = None.

Ziel Phase 5 (Grounding): mypy als Gate, 0 Fehler.
Nicht Phase-2-Scope. Baseline unveraendert (18g).

## Phase-2-Abnahme — Nachlieferungen N1-N4 + R-3 (2026-10-19)

Reviewer-Gate 18 / Phase-2-Abnahme: BESTAETIGT mit
N1-N4. R-3 (10-Minuten-Pruefung R-A/R-B) erledigt.

### N1 — Baseline pro Modul

| Modul | pytest VOR/NACH | ruff VOR/NACH | mypy VOR/NACH |
|---|---|---|---|
| audit.py (ae32005) | 1217/1217 | 24/23 | 9/9 |
| hard_rules.py (f62834f) | 1217/1217 | 23/18 | 9/9 |
| prompts.py (7f51a63) | 1217/1217 | 18/17 | 9/9 |
| measurement.py (13df6bd) | 1217/1217 | 17/17 | 9/9 |
| commit_input.py + subprocess_env.py (05c4ce9) | 1217/1217 | 17/17 | 9/9 |
| Measurement.timeout-Fix (033378c) | 1217/1218 | 17/17 | 9/8 |
| apply.py (af53336) | 1218/1218 | 17/17 | 8/8 |
| verify.py (ab8631f) | 1218/1218 | 17/17 | 8/8 |

Alle Module Baseline-neutral ausser hard_rules.py
(ruff -5), Measurement.timeout-Fix (mypy -1) und
pytest +1 (Charakterisierung).

### N2 — Befund BV: Scope-Erweiterung commit_input.py

5 Funktionen + 1 Konstante wurden in commit_input.py
mitgenommen, ohne explizite Freigabe:

- _lese_plan (14 Z., Z. 5365-alt)
- _lese_contract (22 Z., Z. 5425-alt)
- _plan_pfad (16 Z., Z. 5333-alt)
- _contract_pfad (8 Z., Z. 5379-alt)
- _git_diff_phase (27 Z., Z. 1534-alt)
- _PHASE_HEADER_COMMIT_REVIEW (4 Z., Z. 5443-alt)

Aufruf-Matrix belegt: nur von commit_input-
Funktionen gerufen (_build_commit_input,
_build_judge_input, _build_phase_judge_input).
Kein Ruf aus prompts.py, keine HARD_RULES_*.
Konsequenz: commit_input.py 410 Z. statt ~284.

### N3 — Befund CB: audit-Mock-Ziel

Grep-Beweis, dass keine Test-Stelle mehr
`patch('pipeline.audit')` fuer apply.py-Aufrufe
nutzt:

Test-Anpassungen (10 Tests + 1 monkeypatch):
- test_w54_c_zwei_normale_patches (Z. 10706)
- test_w54_d_kurzer_ersatz_kein_fail (Z. 10732)
- test_w54_g_a_anker_doppelt (Z. 10774)
- test_w54_g_b_verschiedene_zeilen (Z. 10800)
- test_w54_g_c_lange_zeile_doppelt (Z. 10822)
- test_w54_g_d_kurze_legit_doppelt (Z. 10851)
- test_new_file_angelegt (Z. 5238)
- test_new_file_existiert_fail (Z. 5253)
- test_new_file_whitelist_fail (Z. 5265)
- test_zwei_new_file_gleicher_pfad_fail (Z. 5279)
- test_einrueckung_korrektur_audit (Z. 2118,
  monkeypatch.setattr zusaetzlich werkstatt.apply.audit)

Alle 11 patchen jetzt `werkstatt.apply.audit` oder
`werkstatt.apply.audit`-Attribut. 0 Treffer in
tests/ fuer patch('pipeline.audit') in
apply-Code-Kontext (apply_code_patches).

### N4 — Befund CD: verify.py Funktion-zu-Test

| Funktion | Test |
|---|---|
| verify_code | TestVerifyCharakterisierung::test_verify_code_unbekanntes_symbol |
| verify_code_kwargs | TestVerifyCharakterisierung::test_verify_code_kwargs_falsches_kwarg |
| verify_values | TestVerifyCharakterisierung::test_verify_values_execution_status_falsch + _korrekt |
| _api_signaturen | indirekt via test_verify_code_kwargs_falsches_kwarg |
| _projekt_symbol_index | indirekt via test_verify_code_unbekanntes_symbol |

Ausnahme (342 Z.) gerechtfertigt: alle 5 Funktionen
haben Charakterisierungs-Test oder indirekten Beweis.

### R-3 — 10-Minuten-Pruefung R-A/R-B

R-A: RunState.messungen_nach_apply fehlt (2x):
- pipeline.py:3962 (s.messungen_nach_apply = []).
- pipeline.py:6036 (state.messungen_nach_apply = _neue_messungen).
- Leser in measurement.py:173 nutzt getattr (defensiv).
- Bewertung: Annotation-only. RunState-Feld fehlt
  in werkstatt/state.py. Kein Runtime-Bug (Python
  erlaubt dynamische Attribute). Phase 5.

R-B: Path = None (pipeline.py:6007):
- _mess_dir = Path, in except OSError: _mess_dir = None.
- Guard danach: `if _mess_dir is not None and ok:`
  (Z. 6013).
- Bewertung: Annotation-only. Guard ist da. Fix:
  `_mess_dir: Path | None` deklarieren. Phase 5.

Beide Phase 5 (Annotation-Fixes, kein Runtime-Bug).

### R-3-Nachtrag (2026-10-19, nach P1-Fix 77aed9f)

R-B (Path = None, pipeline.py:6007 alt) ist durch den
P1-Fix behoben: `_mess_dir = None` entfernt, except
OSError gibt `return False` + Audit. mypy 8 -> 7.

R-A (RunState.messungen_nach_apply fehlt, 2x) bleibt
Phase 5. Beide Stellen sind Zuweisungen
(pipeline.py:3962, 6039 neu), Leser in measurement.py
nutzt getattr. Fix: Feld in werkstatt/state.py
deklarieren.

Verbleibende mypy 7:
- 3 import-not-found (verify.py, MYPYPATH).
- 2 RunState.messungen_nach_apply (R-A).
- 2 _mess_inhalt_zieldateien list[str]/set[str].
Alle Phase 5.

### R-3-Nachtrag (2026-10-19, nach P1-Fix 77aed9f)

R-B (Path = None, pipeline.py:6007 alt) ist durch den
P1-Fix behoben: `_mess_dir = None` entfernt, except
OSError gibt `return False` + Audit. mypy 8 -> 7.

R-A (RunState.messungen_nach_apply fehlt, 2x) bleibt
Phase 5. Beide Stellen sind Zuweisungen
(pipeline.py:3962, 6039 neu), Leser in measurement.py
nutzt getattr. Fix: Feld in werkstatt/state.py
deklarieren.

Verbleibende mypy 7:
- 3 import-not-found (verify.py, MYPYPATH).
- 2 RunState.messungen_nach_apply (R-A).
- 2 _mess_inhalt_zieldateien list[str]/set[str].
Alle Phase 5.
