# Phase 1 — Triage der Test-Suite

Stand: 2026-10-19
Branch: umbau/phase-1
Status: kategorisiert, KEINE Loeschung, KEIN skip, KEIN xfail.
Auflage: Reviewer Gate 15 (B) + Gate 16 (16a, 16b).

## Zweck

Phase 3 (Loop neu) ersetzt einen Teil der Pipeline. Tests, die
diesen Code pruefen, wuerden mit dem Code fallen. Sie werden
hier kategorisiert, damit Phase 3 sie gezielt aufloesen kann,
ohne die Baseline zu zerstoeren (Reviewer-Auflage 14e).

## Buckets

- **Kern bleibt**: Test prueft Verhalten, das in und nach Phase 3
  gleich bleibt (Parser, Anker, Prompt, Infrastruktur, Daten-
  strukturen, Projekt-Config, andere Module).
- **Phase-3-Code**: Test prueft eine Funktion, die in Phase 3
  ersetzt oder entfernt wird. Test bleibt bis Phase 3 gruen,
  wird dann mit dem Code geloescht.

## Verteilung

- Zeilen (`def test_*`): **1186**
- Cases (pytest-collected): **1189**

| Bucket | Zeilen | Cases |
|---|---|---|
| Kern bleibt | 956 | 959 |
| Phase-3-Code | 230 | 230 |

## Nach Datei

| Datei | Zeilen | davon Phase-3 |
|---|---|---|
| test_aggregate.py | 11 | 0 |
| test_anti_patterns.py | 54 | 0 |
| test_audit.py | 3 | 0 |
| test_audit_kinds.py | 6 | 0 |
| test_conftest_subprocess.py | 4 | 0 |
| test_phase.py | 184 | 54 |
| test_pipeline.py | 772 | 160 |
| test_pipeline_integration.py | 8 | 3 |
| test_planner.py | 80 | 13 |
| test_projekt_schema.py | 21 | 0 |
| test_redaction.py | 43 | 0 |

## Phase-3-Code pro Klasse

| Klasse | Phase-3-Tests |
|---|---|
| modul | 49 |
| TestPlannerKorrekturKontext | 11 |
| TestW35a2PlannerResume | 11 |
| TestResumeForce | 9 |
| TestW25FehlerNachApply | 8 |
| TestWEGXP19bP17Format | 8 |
| TestReviewRoundAudit | 7 |
| TestW25Klassifizierung | 7 |
| TestWEGXP19PlanChecks | 7 |
| TestW29Deterministisch | 7 |
| TestW33bApplyVorReview | 7 |
| TestPhaseRollback | 6 |
| TestPhasenBasisGate | 6 |
| TestPostApplyMessung | 6 |
| TestW30LoopCap | 6 |
| TestPhaseKorrekturUnterblockNoGo | 5 |
| TestW3PlannerMessung | 5 |
| TestW25BasisGate | 5 |
| TestW29JudgeVerdict | 5 |
| TestPhaseYamlStatusUpdate | 4 |
| TestPlanKorrekturSchutz | 4 |
| TestCommitPhaseFixes | 4 |
| TestPhasePersistenz | 3 |
| TestW7 | 3 |
| TestFailClosedRollback | 3 |
| TestWEGXP19Anzeige | 3 |
| TestW34bWerkstattAusnahme | 3 |
| TestRunPhaseStartHead | 2 |
| TestPhaseRollbackIntegration | 2 |
| TestPhaseGesamtReview | 2 |
| TestPhaseMainPfadResume | 2 |
| TestSolverBefundBlock | 2 |
| TestUnklarBehandlung | 2 |
| TestW11b | 2 |
| TestW25SammelCommitRecovery | 2 |
| TestW35a1LetzterBefund | 2 |
| TestPlannerStufenPrompt | 2 |
| TestPhaseMainPfad | 1 |
| TestRunPhase | 1 |
| TestEDiffNameOnly | 1 |
| TestW9a | 1 |
| TestA1Final | 1 |
| TestW32ContractImLoop | 1 |
| TestPlannerLauf | 1 |
| TestPlannerUnbeantwortet | 1 |

## Triage-Tabelle (alle Tests)

| Datei | Zeile | Klasse | Test | Cases | Bucket | Begruendung |
|---|---|---|---|---|---|---|
| test_aggregate.py | 61 | TestIstWerkstattCommit | test_test_workbench | 1 | Kern bleibt | testet anderes Modul (test_aggregate.py) |
| test_aggregate.py | 65 | TestIstWerkstattCommit | test_fix_workbench | 1 | Kern bleibt | testet anderes Modul (test_aggregate.py) |
| test_aggregate.py | 69 | TestIstWerkstattCommit | test_docs_workbench | 1 | Kern bleibt | testet anderes Modul (test_aggregate.py) |
| test_aggregate.py | 73 | TestIstWerkstattCommit | test_menschlicher_commit | 1 | Kern bleibt | testet anderes Modul (test_aggregate.py) |
| test_aggregate.py | 77 | TestIstWerkstattCommit | test_workbench_im_body | 1 | Kern bleibt | testet anderes Modul (test_aggregate.py) |
| test_aggregate.py | 84 | TestSammleProjektStand | test_pfad_existiert_nicht | 1 | Kern bleibt | testet anderes Modul (test_aggregate.py) |
| test_aggregate.py | 90 | TestSammleProjektStand | test_mit_commits | 1 | Kern bleibt | testet anderes Modul (test_aggregate.py) |
| test_aggregate.py | 102 | TestSammleProjektStand | test_quelle_werkstatt | 1 | Kern bleibt | testet anderes Modul (test_aggregate.py) |
| test_aggregate.py | 125 | TestYamlQuote | test_einfacher_string | 1 | Kern bleibt | testet anderes Modul (test_aggregate.py) |
| test_aggregate.py | 128 | TestYamlQuote | test_mit_doppelpunkt | 1 | Kern bleibt | testet anderes Modul (test_aggregate.py) |
| test_aggregate.py | 132 | TestYamlQuote | test_mit_newline | 1 | Kern bleibt | testet anderes Modul (test_aggregate.py) |
| test_anti_patterns.py | 31 | TestKatalog | test_katalog_laedt | 1 | Kern bleibt | testet anderes Modul (test_anti_patterns.py) |
| test_anti_patterns.py | 36 | TestKatalog | test_alle_pflichtfelder_gesetzt | 1 | Kern bleibt | testet anderes Modul (test_anti_patterns.py) |
| test_anti_patterns.py | 42 | TestKatalog | test_ids_eindeutig | 1 | Kern bleibt | testet anderes Modul (test_anti_patterns.py) |
| test_anti_patterns.py | 47 | TestKatalog | test_id_format | 1 | Kern bleibt | testet anderes Modul (test_anti_patterns.py) |
| test_anti_patterns.py | 52 | TestKatalog | test_rollen_erlaubt_und_nicht_leer | 1 | Kern bleibt | testet anderes Modul (test_anti_patterns.py) |
| test_anti_patterns.py | 59 | TestKatalog | test_kategorie_1_2_3 | 1 | Kern bleibt | testet anderes Modul (test_anti_patterns.py) |
| test_anti_patterns.py | 64 | TestKatalog | test_audit_kinds_bekannt | 1 | Kern bleibt | testet anderes Modul (test_anti_patterns.py) |
| test_anti_patterns.py | 71 | TestKatalog | test_trigger_gruende_bekannt | 1 | Kern bleibt | testet anderes Modul (test_anti_patterns.py) |
| test_anti_patterns.py | 84 | TestRolle | test_builder_limit_3 | 1 | Kern bleibt | testet anderes Modul (test_anti_patterns.py) |
| test_anti_patterns.py | 88 | TestRolle | test_builder_enthaelt_anker_eintraege | 1 | Kern bleibt | testet anderes Modul (test_anti_patterns.py) |
| test_anti_patterns.py | 94 | TestRolle | test_reviewer_limit_3 | 1 | Kern bleibt | testet anderes Modul (test_anti_patterns.py) |
| test_anti_patterns.py | 98 | TestRolle | test_test_generator_sieht_4_eintraege | 1 | Kern bleibt | testet anderes Modul (test_anti_patterns.py) |
| test_anti_patterns.py | 109 | TestRolle | test_solver_hat_6_eintraege | 1 | Kern bleibt | testet anderes Modul (test_anti_patterns.py) |
| test_anti_patterns.py | 123 | TestRolle | test_unbekannte_rolle_leer | 1 | Kern bleibt | testet anderes Modul (test_anti_patterns.py) |
| test_anti_patterns.py | 133 | TestLimit | test_limit_default_3 | 1 | Kern bleibt | testet anderes Modul (test_anti_patterns.py) |
| test_anti_patterns.py | 137 | TestLimit | test_limit_1 | 1 | Kern bleibt | testet anderes Modul (test_anti_patterns.py) |
| test_anti_patterns.py | 141 | TestLimit | test_limit_groesser_anzahl | 1 | Kern bleibt | testet anderes Modul (test_anti_patterns.py) |
| test_anti_patterns.py | 151 | TestTrigger | test_fallback_eintrag_wird_immer_gezeigt | 1 | Kern bleibt | testet anderes Modul (test_anti_patterns.py) |
| test_anti_patterns.py | 160 | TestTrigger | test_eintrag_mit_trigger_nur_wenn_passend | 1 | Kern bleibt | testet anderes Modul (test_anti_patterns.py) |
| test_anti_patterns.py | 176 | TestSortierung | test_ap_anker_dekorator_oben | 1 | Kern bleibt | testet anderes Modul (test_anti_patterns.py) |
| test_anti_patterns.py | 184 | TestSortierung | test_reihenfolge_stabil | 1 | Kern bleibt | testet anderes Modul (test_anti_patterns.py) |
| test_anti_patterns.py | 195 | TestValidierung | test_ungueltige_id_wird_abgewiesen | 1 | Kern bleibt | testet anderes Modul (test_anti_patterns.py) |
| test_anti_patterns.py | 204 | TestValidierung | test_leere_rollen_werden_abgewiesen | 1 | Kern bleibt | testet anderes Modul (test_anti_patterns.py) |
| test_anti_patterns.py | 213 | TestValidierung | test_unbekannte_rolle_abgewiesen | 1 | Kern bleibt | testet anderes Modul (test_anti_patterns.py) |
| test_anti_patterns.py | 222 | TestValidierung | test_unbekannte_kategorie_abgewiesen | 1 | Kern bleibt | testet anderes Modul (test_anti_patterns.py) |
| test_anti_patterns.py | 231 | TestValidierung | test_unbekanntes_audit_kind_abgewiesen | 1 | Kern bleibt | testet anderes Modul (test_anti_patterns.py) |
| test_anti_patterns.py | 241 | TestValidierung | test_unbekannter_trigger_grund_abgewiesen | 1 | Kern bleibt | testet anderes Modul (test_anti_patterns.py) |
| test_anti_patterns.py | 251 | TestValidierung | test_fehlendes_pflichtfeld_abgewiesen | 1 | Kern bleibt | testet anderes Modul (test_anti_patterns.py) |
| test_anti_patterns.py | 284 | TestAntiPatternBlock | test_leer_bei_unbekannter_rolle | 1 | Kern bleibt | testet anderes Modul (test_anti_patterns.py) |
| test_anti_patterns.py | 291 | TestAntiPatternBlock | test_leer_bei_trigger_ohne_passende_spezifische | 1 | Kern bleibt | testet anderes Modul (test_anti_patterns.py) |
| test_anti_patterns.py | 300 | TestAntiPatternBlock | test_mit_anker_fehler_enthaelt_block | 1 | Kern bleibt | testet anderes Modul (test_anti_patterns.py) |
| test_anti_patterns.py | 309 | TestAntiPatternBlock | test_ohne_trigger_grund_zeigt_fallback | 1 | Kern bleibt | testet anderes Modul (test_anti_patterns.py) |
| test_anti_patterns.py | 322 | TestAntiPatternBlock | test_trigger_grund_filtert | 1 | Kern bleibt | testet anderes Modul (test_anti_patterns.py) |
| test_anti_patterns.py | 336 | TestAntiPatternBlock | test_spezifisch_vor_fallback | 1 | Kern bleibt | testet anderes Modul (test_anti_patterns.py) |
| test_anti_patterns.py | 344 | TestAntiPatternBlock | test_ohne_spezifische_fallback_greift | 1 | Kern bleibt | testet anderes Modul (test_anti_patterns.py) |
| test_anti_patterns.py | 353 | TestAntiPatternBlock | test_ohne_trigger_grund_nach_haeufigkeit | 1 | Kern bleibt | testet anderes Modul (test_anti_patterns.py) |
| test_anti_patterns.py | 361 | TestAntiPatternBlock | test_max_3_eintraege | 1 | Kern bleibt | testet anderes Modul (test_anti_patterns.py) |
| test_anti_patterns.py | 369 | TestAntiPatternBlock | test_trigger_grund_aus_state | 1 | Kern bleibt | testet anderes Modul (test_anti_patterns.py) |
| test_anti_patterns.py | 375 | TestAntiPatternBlock | test_trigger_grund_prioritaet | 1 | Kern bleibt | testet anderes Modul (test_anti_patterns.py) |
| test_anti_patterns.py | 384 | TestAntiPatternBlock | test_trigger_grund_leer_ergibt_none | 1 | Kern bleibt | testet anderes Modul (test_anti_patterns.py) |
| test_anti_patterns.py | 389 | TestAntiPatternBlock | test_kuerzung_bei_500_zeichen | 1 | Kern bleibt | testet anderes Modul (test_anti_patterns.py) |
| test_anti_patterns.py | 395 | TestAntiPatternBlock | test_keine_kuerzung_bei_kurz | 1 | Kern bleibt | testet anderes Modul (test_anti_patterns.py) |
| test_anti_patterns.py | 421 | TestBaueAnkerRueckmeldungMitAP | test_ohne_fehler_leer | 1 | Kern bleibt | testet anderes Modul (test_anti_patterns.py) |
| test_anti_patterns.py | 425 | TestBaueAnkerRueckmeldungMitAP | test_mit_fehler_enthaelt_ap_block | 1 | Kern bleibt | testet anderes Modul (test_anti_patterns.py) |
| test_anti_patterns.py | 463 | TestReviewerInjektion | test_reviewer_mit_state_enthaelt_ap_block | 1 | Kern bleibt | testet anderes Modul (test_anti_patterns.py) |
| test_anti_patterns.py | 469 | TestReviewerInjektion | test_reviewer_ohne_state_kein_ap_block | 1 | Kern bleibt | testet anderes Modul (test_anti_patterns.py) |
| test_anti_patterns.py | 474 | TestReviewerInjektion | test_reviewer_mit_mit_anti_patterns_false | 1 | Kern bleibt | testet anderes Modul (test_anti_patterns.py) |
| test_anti_patterns.py | 481 | TestReviewerInjektion | test_builder_mit_state_kein_ap_block | 1 | Kern bleibt | testet anderes Modul (test_anti_patterns.py) |
| test_anti_patterns.py | 489 | TestReviewerInjektion | test_solver_mit_state_kein_ap_block | 1 | Kern bleibt | testet anderes Modul (test_anti_patterns.py) |
| test_anti_patterns.py | 497 | TestReviewerInjektion | test_reviewer_ap_block_max_3 | 1 | Kern bleibt | testet anderes Modul (test_anti_patterns.py) |
| test_anti_patterns.py | 528 | TestSolverInjektion | test_rufe_solver_signatur_hat_trigger_grund | 1 | Kern bleibt | testet anderes Modul (test_anti_patterns.py) |
| test_anti_patterns.py | 536 | TestSolverInjektion | test_anti_pattern_block_mit_aufrufer | 1 | Kern bleibt | testet anderes Modul (test_anti_patterns.py) |
| test_anti_patterns.py | 548 | TestSolverInjektion | test_solver_rolle_hat_6_kandidaten | 1 | Kern bleibt | testet anderes Modul (test_anti_patterns.py) |
| test_anti_patterns.py | 559 | TestSolverInjektion | test_solver_trigger_grund_none_fallback | 1 | Kern bleibt | testet anderes Modul (test_anti_patterns.py) |
| test_audit.py | 19 | modul | test_audit_erkennt_callback_als_argument | 1 | Kern bleibt | testet anderes Modul (test_audit.py) |
| test_audit.py | 35 | modul | test_audit_erkennt_s_praefix | 1 | Kern bleibt | testet anderes Modul (test_audit.py) |
| test_audit.py | 48 | modul | test_audit_erkennt_tote_funktion | 1 | Kern bleibt | testet anderes Modul (test_audit.py) |
| test_audit_kinds.py | 142 | modul | test_audit_kinds_alle_aufrufe_registriert | 1 | Kern bleibt | testet anderes Modul (test_audit_kinds.py) |
| test_audit_kinds.py | 160 | modul | test_audit_kind_nicht_registriert_wird_erkannt | 1 | Kern bleibt | testet anderes Modul (test_audit_kinds.py) |
| test_audit_kinds.py | 171 | modul | test_audit_kind_im_kommentar_nicht_erkannt | 1 | Kern bleibt | testet anderes Modul (test_audit_kinds.py) |
| test_audit_kinds.py | 183 | modul | test_audit_dynamische_werte_aufgeloest | 1 | Kern bleibt | testet anderes Modul (test_audit_kinds.py) |
| test_audit_kinds.py | 214 | modul | test_audit_kinds_kein_attribute_aufruf | 1 | Kern bleibt | testet anderes Modul (test_audit_kinds.py) |
| test_audit_kinds.py | 233 | modul | test_katalog_anzahl_matcht_soll | 1 | Kern bleibt | testet anderes Modul (test_audit_kinds.py) |
| test_conftest_subprocess.py | 19 | modul | test_gefaehrliches_subprocess_wird_blockiert | 1 | Kern bleibt | testet anderes Modul (test_conftest_subprocess.py) |
| test_conftest_subprocess.py | 25 | modul | test_legitimes_subprocess_wird_erlaubt | 1 | Kern bleibt | testet anderes Modul (test_conftest_subprocess.py) |
| test_conftest_subprocess.py | 38 | modul | test_sudo_wrapper_wird_blockiert | 1 | Kern bleibt | testet anderes Modul (test_conftest_subprocess.py) |
| test_conftest_subprocess.py | 45 | modul | test_bash_c_wird_blockiert | 1 | Kern bleibt | testet anderes Modul (test_conftest_subprocess.py) |
| test_phase.py | 32 | TestPhaseMainPfad | test_funktion_existiert | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_phase.py | 35 | TestPhaseMainPfad | test_signatur | 1 | Phase-3-Code | ruft _phase_main_pfad |
| test_phase.py | 48 | TestAuditKinds | test_phase_plan_erstellt_vorhanden | 1 | Kern bleibt | ruft _AUDIT_KINDS_BEKANNT |
| test_phase.py | 51 | TestAuditKinds | test_phase_plan_parse_failed_vorhanden | 1 | Kern bleibt | ruft _AUDIT_KINDS_BEKANNT |
| test_phase.py | 54 | TestAuditKinds | test_phase_plan_verworfen_vorhanden | 1 | Kern bleibt | ruft _AUDIT_KINDS_BEKANNT |
| test_phase.py | 57 | TestAuditKinds | test_phase_plan_editiert_vorhanden | 1 | Kern bleibt | ruft _AUDIT_KINDS_BEKANNT |
| test_phase.py | 66 | TestMainPhaseZweig | test_leerer_phasentext_rc_65 | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_phase.py | 79 | TestMainPhaseZweig | test_konflikt_phase_planner_rc_65 | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_phase.py | 107 | TestPhasePlanAlsText | test_funktion_existiert | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_phase.py | 110 | TestPhasePlanAlsText | test_signatur | 1 | Kern bleibt | ruft _phase_plan_als_text |
| test_phase.py | 115 | TestPhasePlanAlsText | test_roundtrip_einfach | 1 | Kern bleibt | ruft _parse_phase_plan, _phase_plan_als_text |
| test_phase.py | 129 | TestPhasePlanAlsText | test_roundtrip_mit_bindestrich_im_titel | 1 | Kern bleibt | ruft _parse_phase_plan, _phase_plan_als_text |
| test_phase.py | 145 | TestPhasePlanAlsText | test_roundtrip_mit_trailing_newline | 1 | Kern bleibt | ruft _parse_phase_plan, _phase_plan_als_text |
| test_phase.py | 160 | TestPhasePlanAlsText | test_fehlende_unterpunkte | 1 | Kern bleibt | ruft _phase_plan_als_text |
| test_phase.py | 174 | TestPhasePlanAlsText | test_fehlende_runden | 1 | Kern bleibt | ruft _phase_plan_als_text |
| test_phase.py | 194 | TestPhaseEditModus | test_funktion_existiert | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_phase.py | 197 | TestPhaseEditModus | test_signatur | 1 | Kern bleibt | ruft _phase_edit_modus |
| test_phase.py | 257 | TestPhaseYamlStatusUpdate | test_funktion_existiert | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_phase.py | 260 | TestPhaseYamlStatusUpdate | test_setzt_status | 1 | Phase-3-Code | ruft _phase_plan_laden, _phase_yaml_status_update |
| test_phase.py | 272 | TestPhaseYamlStatusUpdate | test_unbekannter_status_valueerror | 1 | Phase-3-Code | ruft _phase_yaml_status_update |
| test_phase.py | 284 | TestPhaseYamlStatusUpdate | test_fehlende_datei_valueerror | 1 | Phase-3-Code | ruft _phase_yaml_status_update |
| test_phase.py | 295 | TestPhaseYamlStatusUpdate | test_unbekannte_unterblock_id_valueerror | 1 | Phase-3-Code | ruft _phase_yaml_status_update |
| test_phase.py | 359 | TestRunPhase | test_funktion_existiert | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_phase.py | 362 | TestRunPhase | test_signatur | 1 | Kern bleibt | ruft run_phase |
| test_phase.py | 368 | TestRunPhase | test_loop_zwei_unterbloecke | 1 | Phase-3-Code | ruft _phase_plan_laden |
| test_phase.py | 393 | TestRunPhase | test_leerer_plan_fail_closed | 1 | Kern bleibt | ruft run_phase |
| test_phase.py | 402 | TestRunPhase | test_fehlende_phase_yaml_fail_closed | 1 | Kern bleibt | ruft run_phase |
| test_phase.py | 410 | TestRunPhase | test_idempotenz_alle_done | 1 | Kern bleibt | ruft run_phase |
| test_phase.py | 427 | TestRunPhase | test_no_go_fail_closed | 1 | Kern bleibt | ruft run_phase |
| test_phase.py | 438 | TestRunPhase | test_audit_kinds_im_log | 1 | Kern bleibt | ruft run_phase |
| test_phase.py | 473 | TestGitHelpers | test_rev_parse_existiert | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_phase.py | 476 | TestGitHelpers | test_status_porcelain_existiert | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_phase.py | 479 | TestGitHelpers | test_rev_parse_kein_repo_gibt_leer | 1 | Kern bleibt | ruft _git_rev_parse_head |
| test_phase.py | 484 | TestGitHelpers | test_status_porcelain_kein_repo_gibt_sentinel | 1 | Kern bleibt | ruft _git_status_porcelain |
| test_phase.py | 496 | TestPhaseRollback | test_funktion_existiert | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_phase.py | 499 | TestPhaseRollback | test_signatur | 1 | Phase-3-Code | ruft _phase_rollback |
| test_phase.py | 509 | TestPhaseRollback | test_leerer_start_head_fail_closed | 1 | Phase-3-Code | ruft _phase_rollback |
| test_phase.py | 524 | TestPhaseRollback | test_head_abweichend_kein_reset | 1 | Phase-3-Code | ruft _phase_rollback |
| test_phase.py | 539 | TestPhaseRollback | test_status_schmutzig_kein_reset | 1 | Phase-3-Code | ruft _phase_rollback |
| test_phase.py | 556 | TestPhaseRollback | test_erfolg_reset_und_clean | 1 | Phase-3-Code | ruft _phase_rollback |
| test_phase.py | 588 | TestPhaseRollback | test_exception_im_reset_fail_closed | 1 | Phase-3-Code | ruft _phase_rollback |
| test_phase.py | 611 | TestRunPhaseStartHead | test_setzt_head_wenn_leer | 1 | Phase-3-Code | ruft _phase_plan_laden |
| test_phase.py | 638 | TestRunPhaseStartHead | test_yaml_gewinnt_wenn_gesetzt | 1 | Phase-3-Code | ruft _phase_plan_laden, _phase_plan_speichern |
| test_phase.py | 668 | TestRunPhaseStartHead | test_inkonsistenz_fail_closed | 1 | Kern bleibt | ruft run_phase |
| test_phase.py | 706 | TestPhaseRollbackIntegration | test_head_abweichend_kein_reset | 1 | Phase-3-Code | ruft _phase_rollback |
| test_phase.py | 747 | TestPhaseRollbackIntegration | test_status_schmutzig_kein_reset | 1 | Phase-3-Code | ruft _phase_rollback |
| test_phase.py | 781 | TestRunPipelineSignatur | test_phasen_state_ist_keyword_only | 1 | Kern bleibt | ruft run_pipeline |
| test_phase.py | 788 | TestRunPipelineSignatur | test_state_ref_nicht_phasen_state | 1 | Kern bleibt | ruft run_pipeline |
| test_phase.py | 796 | TestRunPipelinePhasenModus | test_guard_quelle_vorhanden | 1 | Kern bleibt | ruft run_pipeline |
| test_phase.py | 804 | TestRunPipelinePhasenModus | test_phasen_modus_quelle_vorhanden | 1 | Kern bleibt | ruft run_pipeline |
| test_phase.py | 829 | TestRunPhaseRcKlassen | test_klasse_1_erfolg_mit_paket | 1 | Kern bleibt | ruft run_phase |
| test_phase.py | 852 | TestRunPhaseRcKlassen | test_klasse_2_b2_ohne_paket | 1 | Kern bleibt | ruft run_phase |
| test_phase.py | 870 | TestRunPhaseRcKlassen | test_klasse_3_rc_15_kein_rollback | 1 | Kern bleibt | ruft run_phase |
| test_phase.py | 890 | TestRunPhaseRcKlassen | test_klasse_4_rc_11_mit_rollback | 1 | Kern bleibt | ruft run_phase |
| test_phase.py | 908 | TestRunPhaseRcKlassen | test_klasse_4_rc_21_mit_rollback | 1 | Kern bleibt | ruft run_phase |
| test_phase.py | 925 | TestRunPhaseRcKlassen | test_exception_im_run_pipeline | 1 | Kern bleibt | ruft run_phase |
| test_phase.py | 947 | TestRunPhaseGuards | test_state_ref_nicht_leer_wirft | 1 | Kern bleibt | ruft run_phase |
| test_phase.py | 961 | TestRunPhaseGuards | test_run_pipeline_vertragsbruch | 1 | Kern bleibt | ruft RunState, run_phase |
| test_phase.py | 995 | TestPhaseGesamtReview | test_aggregat_2_pakete | 1 | Phase-3-Code | ruft _phase_gesamt_review |
| test_phase.py | 1012 | TestPhaseGesamtReview | test_aggregat_mit_duplikat | 1 | Phase-3-Code | ruft _phase_gesamt_review |
| test_phase.py | 1026 | TestPhaseSammelPaket | test_sammel_union | 1 | Kern bleibt | ruft _phase_sammel_paket |
| test_phase.py | 1044 | TestPhaseSammelPaket | test_message_b2_zeile | 1 | Kern bleibt | ruft _phase_sammel_message |
| test_phase.py | 1068 | TestPhaseApproval | test_approval_j_commit | 1 | Kern bleibt | ruft run_phase |
| test_phase.py | 1091 | TestPhaseApproval | test_approval_n_rollback | 1 | Kern bleibt | ruft run_phase |
| test_phase.py | 1113 | TestPhaseApproval | test_commit_fail_rc_20 | 1 | Kern bleibt | ruft run_phase |
| test_phase.py | 1129 | TestPhaseApproval | test_keine_pakete_b2_only | 1 | Kern bleibt | ruft run_phase |
| test_phase.py | 1147 | TestPhaseApproval | test_ungueltige_eingabe_fail_closed | 1 | Kern bleibt | ruft run_phase |
| test_phase.py | 1173 | TestPhaseBudget | test_budget_ende_rc_13 | 1 | Kern bleibt | ruft run_phase |
| test_phase.py | 1188 | TestPhaseBudget | test_budget_genug | 1 | Kern bleibt | ruft run_phase |
| test_phase.py | 1207 | TestPhaseBudget | test_budget_null_kein_deckel | 1 | Kern bleibt | ruft run_phase |
| test_phase.py | 1238 | TestPhasePlanKorrektur | test_korrektur_max_1_zyklus | 1 | Kern bleibt | ruft run_phase |
| test_phase.py | 1260 | TestPhasePlanKorrektur | test_korrektur_failed_rc_23 | 1 | Kern bleibt | ruft run_phase |
| test_phase.py | 1288 | TestPhaseRrK8 | test_abbrechen | 1 | Kern bleibt | ruft _phase_rr_k8 |
| test_phase.py | 1295 | TestPhaseRrK8 | test_neu_starten | 1 | Kern bleibt | ruft _phase_rr_k8 |
| test_phase.py | 1302 | TestPhaseRrK8 | test_eof_abbrechen | 1 | Kern bleibt | ruft _phase_rr_k8 |
| test_phase.py | 1316 | TestPlannerKorrekturKontext | test_user_content_mit_kontext | 1 | Phase-3-Code | ruft _planner_user_content |
| test_phase.py | 1329 | TestPlannerKorrekturKontext | test_user_content_ohne_kontext | 1 | Phase-3-Code | ruft _planner_user_content |
| test_phase.py | 1339 | TestRunPhaseDoneSkip | test_done_wird_uebersprungen | 1 | Kern bleibt | ruft run_phase |
| test_phase.py | 1370 | TestPhaseMainPfadResume | test_resume_ohne_plan_planner_gerufen | 1 | Phase-3-Code | ruft _phase_main_pfad |
| test_phase.py | 1380 | TestPhaseMainPfadResume | test_finish_aktiv_helper_existiert | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_phase.py | 1383 | TestPhaseMainPfadResume | test_finish_setzt_aktiv_false | 1 | Phase-3-Code | ruft _phase_plan_laden |
| test_phase.py | 1400 | TestPhaseMainPfadResume | test_finish_rc_nicht_null_noop | 1 | Kern bleibt | ruft _phase_finish_aktiv |
| test_phase.py | 1413 | TestPhaseMainPfadResume | test_finish_phase_aktiv_false_noop | 1 | Kern bleibt | ruft _phase_finish_aktiv |
| test_phase.py | 1431 | TestSolverBefundBlock | test_leerer_state_leerer_block | 1 | Phase-3-Code | ruft _solver_befund_block |
| test_phase.py | 1436 | TestSolverBefundBlock | test_marker_text_enthaelt_praezisierung | 1 | Phase-3-Code | ruft _solver_befund_block |
| test_phase.py | 1450 | TestAuditBuilderPromptSolverFeld | test_audit_enthaelt_solver_feld | 1 | Kern bleibt | ruft _audit_builder_prompt |
| test_phase.py | 1460 | TestParseCommandsFrage | test_run_hat_typ_run | 1 | Kern bleibt | ruft parse_commands |
| test_phase.py | 1468 | TestParseCommandsFrage | test_frage_reviewer_erkannt | 1 | Kern bleibt | ruft parse_commands |
| test_phase.py | 1475 | TestParseCommandsFrage | test_mehrere_fragen_konkateniert | 1 | Kern bleibt | ruft parse_commands |
| test_phase.py | 1486 | TestParseCommandsFrage | test_gemischt_run_und_frage | 1 | Kern bleibt | ruft parse_commands |
| test_phase.py | 1496 | TestParseCommandsFrage | test_run_ohne_praefix_verworfen | 1 | Kern bleibt | ruft parse_commands |
| test_phase.py | 1503 | TestBuilderFrageReviewerLoop | test_frage_reviewer_kein_deadlock | 1 | Kern bleibt | ruft builder_reply_mit_command_loop |
| test_phase.py | 1519 | TestAntwortModus | test_classify_verdict_erkennt_antwort | 1 | Kern bleibt | ruft classify_verdict |
| test_phase.py | 1523 | TestAntwortModus | test_classify_verdict_antwort_mit_punkt | 1 | Kern bleibt | ruft classify_verdict |
| test_phase.py | 1527 | TestAntwortModus | test_classify_verdict_go_unveraendert | 1 | Kern bleibt | ruft classify_verdict |
| test_phase.py | 1532 | TestAntwortModus | test_extrahiere_antwort | 1 | Kern bleibt | ruft _extrahiere_antwort |
| test_phase.py | 1538 | TestAntwortModus | test_extrahiere_antwort_leer | 1 | Kern bleibt | ruft _extrahiere_antwort |
| test_phase.py | 1541 | TestAntwortModus | test_extrahiere_antwort_inline | 1 | Kern bleibt | ruft _extrahiere_antwort |
| test_phase.py | 1548 | TestHardRules | test_reviewer_r8_vorhanden | 1 | Kern bleibt | ruft HARD_RULES_REVIEWER |
| test_phase.py | 1552 | TestHardRules | test_builder_b11_vorhanden | 1 | Kern bleibt | ruft HARD_RULES_BUILDER |
| test_phase.py | 1561 | TestPhaseKorrekturUnterblockNoGo | test_runstate_feld_existiert | 1 | Kern bleibt | ruft RunState |
| test_phase.py | 1567 | TestPhaseKorrekturUnterblockNoGo | test_r9_in_hard_rules | 1 | Kern bleibt | ruft HARD_RULES_REVIEWER |
| test_phase.py | 1573 | TestPhaseKorrekturUnterblockNoGo | test_zyklus_teilt_sich | 1 | Phase-3-Code | ruft _phase_main_pfad |
| test_phase.py | 1582 | TestPhaseKorrekturUnterblockNoGo | test_korrektur_startet_nach_rc15 | 1 | Phase-3-Code | ruft _phase_main_pfad |
| test_phase.py | 1592 | TestPhaseKorrekturUnterblockNoGo | test_kontext_enthaelt_reviewer_befund | 1 | Phase-3-Code | ruft _phase_plan_korrektur |
| test_phase.py | 1597 | TestPhaseKorrekturUnterblockNoGo | test_pakete_reset_nach_korrektur | 1 | Phase-3-Code | ruft _phase_plan_korrektur |
| test_phase.py | 1602 | TestPhaseKorrekturUnterblockNoGo | test_audit_payload_grund | 1 | Phase-3-Code | ruft _phase_plan_korrektur |
| test_phase.py | 1613 | TestNewFilePrompt | test_builder_md_enthaelt_new_file | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_phase.py | 1619 | TestNewFilePrompt | test_builder_md_platzhalter_verbot | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_phase.py | 1625 | TestNewFilePrompt | test_judge_md_enthaelt_contract | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_phase.py | 1632 | TestNewFilePrompt | test_hard_rules_builder_b12 | 1 | Kern bleibt | ruft HARD_RULES_BUILDER |
| test_phase.py | 1636 | TestNewFilePrompt | test_hard_rules_reviewer_r10 | 1 | Kern bleibt | ruft HARD_RULES_REVIEWER |
| test_phase.py | 1640 | TestNewFilePrompt | test_r10_verweist_auf_r5_ausnahme | 1 | Kern bleibt | ruft HARD_RULES_REVIEWER |
| test_phase.py | 1645 | TestNewFilePrompt | test_r10_verbietet_write_file | 1 | Kern bleibt | ruft HARD_RULES_REVIEWER |
| test_phase.py | 1659 | TestRollenAuditA | test_reviewer_kein_alter_abschnitt | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_phase.py | 1662 | TestRollenAuditA | test_reviewer_kein_security_review_log | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_phase.py | 1665 | TestRollenAuditA | test_judge_hat_security_log | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_phase.py | 1670 | TestRollenAuditA | test_judge_hat_r10_hinweis | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_phase.py | 1675 | TestRollenAuditA | test_builder_hat_git_ls_files | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_phase.py | 1679 | TestRollenAuditA | test_builder_kein_warte_satz | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_phase.py | 1683 | TestRollenAuditA | test_builder_hat_vorgaenger_hash | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_phase.py | 1687 | TestRollenAuditA | test_builder_einrueckung_roh | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_phase.py | 1698 | TestRollenAuditA | test_hash_regel_judge | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_phase.py | 1703 | TestRollenAuditA | test_build_system_prompt_reviewer_kein_alt | 1 | Kern bleibt | ruft build_system_prompt, load_agents |
| test_phase.py | 1709 | TestRollenAuditA | test_build_system_prompt_reviewer_hat_antwort | 1 | Kern bleibt | ruft build_system_prompt, load_agents |
| test_phase.py | 1715 | TestRollenAuditA | test_build_system_prompt_builder_kein_warte | 1 | Kern bleibt | ruft build_system_prompt, load_agents |
| test_phase.py | 1731 | TestRollenAuditB | test_solver_md_dasselbe_wissen | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_phase.py | 1734 | TestRollenAuditB | test_solver_md_doch_geht | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_phase.py | 1738 | TestRollenAuditB | test_solver_md_praeziseren_auftrag | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_phase.py | 1741 | TestRollenAuditB | test_solver_md_trigger_anker | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_phase.py | 1744 | TestRollenAuditB | test_solver_md_trigger_rueckfrage | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_phase.py | 1747 | TestRollenAuditB | test_solver_md_trigger_wirkungslos | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_phase.py | 1750 | TestRollenAuditB | test_solver_md_trigger_p1 | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_phase.py | 1753 | TestRollenAuditB | test_solver_md_kein_falscher_trigger | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_phase.py | 1762 | TestRollenAuditB | test_build_system_prompt_solver_hat_trigger | 1 | Kern bleibt | ruft build_system_prompt, load_agents |
| test_phase.py | 1772 | TestTriggerKonsistenz | test_trigger_grund_werte_konsistent | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_phase.py | 1801 | TestTriggerKonsistenz | test_b2_abschnitt_erhalten | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_phase.py | 1814 | TestStateAufgabePhasenModus | test_quelle_setzt_aufgabe | 1 | Kern bleibt | ruft run_pipeline |
| test_phase.py | 1820 | TestStateAufgabePhasenModus | test_quelle_audit_phase_felder | 1 | Kern bleibt | ruft run_pipeline |
| test_phase.py | 1838 | TestBuilderFormatWichtigBlock | test_typ_new_file_im_wichtig_block | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_phase.py | 1851 | TestBuilderFormatWichtigBlock | test_typ_patch_im_wichtig_block | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_phase.py | 1858 | TestBuilderFormatWichtigBlock | test_platzhalter_verbot_im_wichtig_block | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_phase.py | 1866 | TestBuilderFormatWichtigBlock | test_read_file_hinweis_im_wichtig_block | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_phase.py | 1874 | TestBuilderFormatWichtigBlock | test_verweise_im_wichtig_block | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_phase.py | 1882 | TestBuilderFormatWichtigBlock | test_build_system_prompt_beide_formate | 1 | Kern bleibt | ruft build_system_prompt, load_agents |
| test_phase.py | 1895 | TestAnkerPruefungNewFile | test_new_file_wird_uebersprungen | 1 | Kern bleibt | ruft pruefe_anker_gegen_messung |
| test_phase.py | 1906 | TestAnkerPruefungNewFile | test_leerer_anker_patch_bleibt_fehler | 1 | Kern bleibt | ruft pruefe_anker_gegen_messung |
| test_phase.py | 1920 | TestAnkerPruefungNewFile | test_falscher_anker_bleibt_fehler | 1 | Kern bleibt | ruft pruefe_anker_gegen_messung |
| test_phase.py | 1934 | TestAnkerPruefungNewFile | test_gemischt_new_file_und_patch | 1 | Kern bleibt | ruft pruefe_anker_gegen_messung |
| test_phase.py | 1955 | TestPostApplyKorrektur | test_aufrufer_hat_rc19_zweig | 1 | Kern bleibt | ruft run_pipeline |
| test_phase.py | 1963 | TestPostApplyKorrektur | test_funktion_existiert | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_phase.py | 1967 | TestPostApplyKorrektur | test_apply_and_recheck_gibt_19 | 1 | Kern bleibt | ruft apply_and_recheck |
| test_phase.py | 1973 | TestPostApplyKorrektur | test_state_feld_vorhanden | 1 | Kern bleibt | ruft RunState |
| test_phase.py | 1979 | TestPostApplyKorrektur | test_bauer_recovery_prompt_typ_patch | 1 | Kern bleibt | ruft RunState, _bauer_recovery_prompt |
| test_phase.py | 1997 | TestPostApplyKorrektur | test_bauer_recovery_prompt_mit_vorschlag | 1 | Kern bleibt | ruft RecoveryVorschlag, RunState |
| test_phase.py | 2033 | TestResumeForce | test_no_go_wird_pending | 1 | Phase-3-Code | ruft _resume_force_reset |
| test_phase.py | 2043 | TestResumeForce | test_failed_wird_pending | 1 | Phase-3-Code | ruft _resume_force_reset |
| test_phase.py | 2051 | TestResumeForce | test_done_bleibt_done | 1 | Phase-3-Code | ruft _resume_force_reset |
| test_phase.py | 2063 | TestResumeForce | test_pending_bleibt_pending | 1 | Phase-3-Code | ruft _resume_force_reset |
| test_phase.py | 2071 | TestResumeForce | test_ohne_no_go_wirkungslos | 1 | Phase-3-Code | ruft _resume_force_reset |
| test_phase.py | 2080 | TestResumeForce | test_phase_start_head_unveraendert | 1 | Phase-3-Code | ruft _resume_force_reset |
| test_phase.py | 2088 | TestResumeForce | test_kandidaten_liste | 1 | Phase-3-Code | ruft _resume_force_reset |
| test_phase.py | 2100 | TestResumeForce | test_leerer_plan | 1 | Phase-3-Code | ruft _resume_force_reset |
| test_phase.py | 2106 | TestResumeForce | test_nicht_dict_uebersprungen | 1 | Phase-3-Code | ruft _resume_force_reset |
| test_phase.py | 2121 | TestResumeForceCli | test_resume_force_ohne_phase_fail | 1 | Kern bleibt | ruft main |
| test_phase.py | 2129 | TestResumeForceCli | test_resume_force_mit_phase_erlaubt | 1 | Kern bleibt | ruft main |
| test_phase.py | 2149 | TestPhasePersistenz | test_yaml_status_update_schreibt_commit_paket | 1 | Phase-3-Code | ruft _phase_yaml_status_update |
| test_phase.py | 2169 | TestPhasePersistenz | test_yaml_status_update_ohne_paket | 1 | Phase-3-Code | ruft _phase_yaml_status_update |
| test_phase.py | 2183 | TestPhasePersistenz | test_message_wird_gekuerzt | 1 | Phase-3-Code | ruft _phase_yaml_status_update |
| test_phase.py | 2198 | TestPhasePersistenz | test_restore_mehrere_done_unterbloecke | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_phase.py | 2231 | TestPhasePersistenz | test_restore_ignoriert_done_ohne_dateien | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_phase.py | 2298 | TestPhasenBasisGate | test_clean_git | 1 | Phase-3-Code | ruft _phasen_basis_gate_ok |
| test_phase.py | 2310 | TestPhasenBasisGate | test_untracked_ohne_phase_yaml_fail | 1 | Phase-3-Code | ruft _phasen_basis_gate_ok |
| test_phase.py | 2323 | TestPhasenBasisGate | test_untracked_in_done_paket_ok | 1 | Phase-3-Code | ruft _phasen_basis_gate_ok |
| test_phase.py | 2344 | TestPhasenBasisGate | test_untracked_fremd_fail | 1 | Phase-3-Code | ruft _phasen_basis_gate_ok |
| test_phase.py | 2359 | TestPhasenBasisGate | test_modified_fail | 1 | Phase-3-Code | ruft _phasen_basis_gate_ok |
| test_phase.py | 2392 | TestPhasenBasisGate | test_mehrere_done_pakete | 1 | Phase-3-Code | ruft _phasen_basis_gate_ok |
| test_phase.py | 2478 | TestPlanKorrekturSchutz | test_done_unterblock_bleibt_done | 1 | Phase-3-Code | ruft _phase_plan_korrektur |
| test_phase.py | 2521 | TestPlanKorrekturSchutz | test_anzahl_geaendert_fail | 1 | Phase-3-Code | ruft _phase_plan_korrektur |
| test_phase.py | 2547 | TestPlanKorrekturSchutz | test_id_geaendert_fail | 1 | Phase-3-Code | ruft _phase_plan_korrektur |
| test_phase.py | 2570 | TestPlanKorrekturSchutz | test_alter_plan_enthaelt_unterpunkte | 1 | Phase-3-Code | ruft _phase_plan_korrektur |
| test_phase.py | 2607 | TestW7 | test_intent_to_add_done_pfad_ok | 1 | Phase-3-Code | ruft _phasen_basis_gate_ok |
| test_phase.py | 2615 | TestW7 | test_modified_done_pfad_ok | 1 | Phase-3-Code | ruft _phasen_basis_gate_ok |
| test_phase.py | 2620 | TestW7 | test_fremd_mod_fail_closed | 1 | Phase-3-Code | ruft _phasen_basis_gate_ok |
| test_pipeline.py | 3799 | modul | test_zaehle_no_go_in_folge_leer | 1 | Kern bleibt | ruft zaehle_no_go_in_folge |
| test_pipeline.py | 3804 | modul | test_zaehle_no_go_in_folge_ein_go | 1 | Kern bleibt | ruft zaehle_no_go_in_folge |
| test_pipeline.py | 3809 | modul | test_zaehle_no_go_in_folge_zwei_no_go | 1 | Kern bleibt | ruft zaehle_no_go_in_folge |
| test_pipeline.py | 3815 | modul | test_zaehle_no_go_in_folge_unterbrochen_durch_go | 1 | Kern bleibt | ruft zaehle_no_go_in_folge |
| test_pipeline.py | 3825 | modul | test_zaehle_no_go_in_folge_drei_no_go | 1 | Kern bleibt | ruft zaehle_no_go_in_folge |
| test_pipeline.py | 3835 | modul | test_recovery_marker_nach_zwei_no_go | 1 | Kern bleibt | ruft zaehle_no_go_in_folge |
| test_pipeline.py | 3848 | modul | test_recovery_marker_nach_einer_no_go | 1 | Kern bleibt | ruft zaehle_no_go_in_folge |
| test_pipeline.py | 3857 | modul | test_recovery_hinweis_block_ohne_befund | 1 | Kern bleibt | ruft recovery_hinweis_block |
| test_pipeline.py | 3867 | modul | test_jaccard_identische_texte | 1 | Kern bleibt | ruft jaccard_aehnlichkeit |
| test_pipeline.py | 3872 | modul | test_jaccard_leere_texte | 1 | Kern bleibt | ruft jaccard_aehnlichkeit |
| test_pipeline.py | 3876 | modul | test_jaccard_teilueberlappung | 1 | Kern bleibt | ruft jaccard_aehnlichkeit |
| test_pipeline.py | 3884 | modul | test_jaccard_stopwoerter_entfernt | 1 | Kern bleibt | ruft jaccard_aehnlichkeit |
| test_pipeline.py | 3890 | modul | test_gegenstand_gleich_zu_wenig_runden | 1 | Kern bleibt | ruft P1_GRUND_KEIN_KEIN_PAAR, gegenstand_gleich |
| test_pipeline.py | 3898 | modul | test_gegenstand_gleich_leer | 1 | Kern bleibt | ruft P1_GRUND_KEIN_LEER, gegenstand_gleich |
| test_pipeline.py | 3907 | modul | test_gegenstand_gleich_zu_kurz | 1 | Kern bleibt | ruft P1_GRUND_KEIN_ZU_KURZ, gegenstand_gleich |
| test_pipeline.py | 3916 | modul | test_gegenstand_gleich_ueber_schwelle | 1 | Kern bleibt | ruft P1_GRUND_GETRIGGERT, gegenstand_gleich |
| test_pipeline.py | 3929 | modul | test_gegenstand_gleich_unter_schwelle | 1 | Kern bleibt | ruft P1_GRUND_KEIN_JACCARD, gegenstand_gleich |
| test_pipeline.py | 3944 | modul | test_gegenstand_gleich_schon_getriggert | 1 | Kern bleibt | ruft P1_GRUND_KEIN_SCHON, gegenstand_gleich |
| test_pipeline.py | 3956 | modul | test_parse_solver_diagnose_gleicher_fehler | 1 | Kern bleibt | ruft SolverDiagnose, parse_solver_diagnose |
| test_pipeline.py | 3962 | modul | test_parse_solver_diagnose_anderer_fehler | 1 | Kern bleibt | ruft SolverDiagnose, parse_solver_diagnose |
| test_pipeline.py | 3968 | modul | test_parse_solver_diagnose_widerspruch | 1 | Kern bleibt | ruft SolverDiagnose, parse_solver_diagnose |
| test_pipeline.py | 3974 | modul | test_parse_solver_diagnose_unklar | 1 | Kern bleibt | ruft SolverDiagnose, parse_solver_diagnose |
| test_pipeline.py | 3980 | modul | test_parse_solver_diagnose_fallback_unklar | 1 | Kern bleibt | ruft SolverDiagnose, parse_solver_diagnose |
| test_pipeline.py | 3985 | modul | test_parse_solver_diagnose_bei_leerem_text | 1 | Kern bleibt | ruft SolverDiagnose, parse_solver_diagnose |
| test_pipeline.py | 3990 | modul | test_baue_solver_befund_gleicher_fehler | 1 | Kern bleibt | ruft SolverDiagnose, baue_solver_befund |
| test_pipeline.py | 3999 | modul | test_baue_solver_befund_anderer_fehler | 1 | Kern bleibt | ruft SolverDiagnose, baue_solver_befund |
| test_pipeline.py | 4008 | modul | test_baue_solver_befund_unvollstaendig | 1 | Kern bleibt | ruft baue_solver_befund |
| test_pipeline.py | 4015 | modul | test_recovery_hinweis_block_default_parameter | 1 | Kern bleibt | ruft recovery_hinweis_block |
| test_pipeline.py | 4022 | modul | test_recovery_hinweis_block_mit_befund | 1 | Kern bleibt | ruft recovery_hinweis_block |
| test_pipeline.py | 4035 | modul | test_recovery_hinweis_block_leer | 1 | Kern bleibt | ruft recovery_hinweis_block |
| test_pipeline.py | 4040 | modul | test_recovery_hinweis_block_mehrere_runden | 1 | Kern bleibt | ruft recovery_hinweis_block |
| test_pipeline.py | 4052 | modul | test_recovery_hinweis_block_befund_und_kein_recovery | 1 | Kern bleibt | ruft recovery_hinweis_block |
| test_pipeline.py | 4060 | modul | test_solver_befund_block_ohne_befund | 1 | Phase-3-Code | ruft _solver_befund_block |
| test_pipeline.py | 4071 | modul | test_solver_befund_block_mit_befund | 1 | Phase-3-Code | ruft _solver_befund_block |
| test_pipeline.py | 4088 | modul | test_solver_befund_block_unvollstaendig | 1 | Phase-3-Code | ruft _solver_befund_block |
| test_pipeline.py | 4103 | modul | test_solver_befund_block_bei_zwei_befunden | 1 | Phase-3-Code | ruft _solver_befund_block |
| test_pipeline.py | 4124 | modul | test_solver_befund_block_bei_zwei_befunden_letzter_unvollstaendig | 1 | Phase-3-Code | ruft _solver_befund_block |
| test_pipeline.py | 4141 | modul | test_format_solver_befund_unberuehrt | 1 | Kern bleibt | ruft SolverBefund, SolverDiagnose |
| test_pipeline.py | 4151 | modul | test_recovery_hinweis_block_ohne_recovery | 1 | Kern bleibt | ruft recovery_hinweis_block |
| test_pipeline.py | 4156 | modul | test_letzte_zwei_entwuerfe | 1 | Kern bleibt | ruft Path, RunState |
| test_pipeline.py | 4177 | modul | test_a1b_fix_solver_sieht_historie | 1 | Phase-3-Code | ruft _solver_prompt_bauen |
| test_pipeline.py | 4195 | modul | test_a1b_fix_recovery_wird_ausgeblendet | 1 | Kern bleibt | ruft _letzte_zwei_entwuerfe, record_code_entwurf |
| test_pipeline.py | 4213 | modul | test_a1b_fix_recovery_only_zeigt_keine_historie | 1 | Phase-3-Code | ruft _solver_prompt_bauen |
| test_pipeline.py | 4229 | modul | test_a1b_fix_post_apply_korrektur_loop_recovery | 1 | Phase-3-Code | ruft _post_apply_korrektur_loop |
| test_pipeline.py | 4268 | modul | test_handle_solver_command_erfolg | 1 | Phase-3-Code | ruft _handle_solver_command |
| test_pipeline.py | 4290 | modul | test_handle_solver_command_duplikat | 1 | Phase-3-Code | ruft _handle_solver_command |
| test_pipeline.py | 4315 | modul | test_handle_solver_command_fail_llm | 1 | Phase-3-Code | ruft _handle_solver_command |
| test_pipeline.py | 4333 | modul | test_handle_solver_command_arg_zu_lang_gekuerzt | 1 | Phase-3-Code | ruft _handle_solver_command |
| test_pipeline.py | 4358 | modul | test_handle_solver_command_arg_leer | 1 | Phase-3-Code | ruft _handle_solver_command |
| test_pipeline.py | 4381 | modul | test_solver_prompt_mit_grund | 1 | Phase-3-Code | ruft _solver_prompt_bauen |
| test_pipeline.py | 4390 | modul | test_solver_prompt_ohne_grund | 1 | Phase-3-Code | ruft _solver_prompt_bauen |
| test_pipeline.py | 4399 | modul | test_agent_docs_solver_enthaelt_reviewer_keys | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_pipeline.py | 4410 | modul | test_agent_docs_solver_enthaelt_projektwissen | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_pipeline.py | 4429 | modul | test_solver_system_prompt_enthaelt_alle_doku_keys | 1 | Kern bleibt | ruft build_system_prompt |
| test_pipeline.py | 4444 | modul | test_solver_agent_docs_leer_ergibt_kein_projekt_doku_block | 1 | Kern bleibt | ruft build_system_prompt |
| test_pipeline.py | 4450 | modul | test_max_solver_runden_default_3 | 1 | Kern bleibt | ruft MAX_SOLVER_RUNDEN_DEFAULT |
| test_pipeline.py | 4455 | modul | test_max_solver_runden_yaml_override | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_pipeline.py | 4464 | modul | test_max_solver_runden_blockt_nach_3 | 1 | Kern bleibt | ruft MAX_SOLVER_RUNDEN_DEFAULT |
| test_pipeline.py | 4474 | modul | test_solver_prompt_ohne_historie_bei_runde_1 | 1 | Phase-3-Code | ruft _solver_prompt_bauen |
| test_pipeline.py | 4482 | modul | test_solver_prompt_enthaelt_historie_bei_runde_2 | 1 | Phase-3-Code | ruft _solver_prompt_bauen |
| test_pipeline.py | 4532 | modul | test_pruefe_anker_gegen_messung_alle_ok | 1 | Kern bleibt | ruft pruefe_anker_gegen_messung |
| test_pipeline.py | 4539 | modul | test_pruefe_anker_gegen_messung_einer_fehlt | 1 | Kern bleibt | ruft pruefe_anker_gegen_messung |
| test_pipeline.py | 4554 | modul | test_pruefe_anker_gegen_messung_leer | 1 | Kern bleibt | ruft pruefe_anker_gegen_messung |
| test_pipeline.py | 4563 | modul | test_pruefe_anker_gegen_messung_shift_akzeptiert | 1 | Kern bleibt | ruft pruefe_anker_gegen_messung |
| test_pipeline.py | 4577 | modul | test_pruefe_anker_gegen_messung_leerer_anmelder_anmelder | 1 | Kern bleibt | ruft pruefe_anker_gegen_messung |
| test_pipeline.py | 4590 | modul | test_baue_anker_rueckmeldung_leer | 1 | Kern bleibt | ruft baue_anker_rueckmeldung |
| test_pipeline.py | 4596 | modul | test_baue_anker_rueckmeldung_mit_einem_anker | 1 | Kern bleibt | ruft baue_anker_rueckmeldung |
| test_pipeline.py | 4606 | modul | test_baue_anker_rueckmeldung_mit_ersatz | 1 | Kern bleibt | ruft baue_anker_rueckmeldung |
| test_pipeline.py | 4614 | modul | test_baue_anker_rueckmeldung_max_5 | 1 | Kern bleibt | ruft baue_anker_rueckmeldung |
| test_pipeline.py | 4625 | modul | test_anker_fehler_in_folge_initial_null | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_pipeline.py | 4631 | modul | test_letzte_anker_fehler_initial_leer | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_pipeline.py | 4640 | modul | test_klassifiziere_deadlock_anker | 1 | Kern bleibt | ruft klassifiziere_deadlock |
| test_pipeline.py | 4648 | modul | test_klassifiziere_deadlock_ersatz | 1 | Kern bleibt | ruft klassifiziere_deadlock |
| test_pipeline.py | 4656 | modul | test_klassifiziere_deadlock_rueckfrage | 1 | Kern bleibt | ruft klassifiziere_deadlock |
| test_pipeline.py | 4663 | modul | test_klassifiziere_deadlock_leer | 1 | Kern bleibt | ruft klassifiziere_deadlock |
| test_pipeline.py | 4669 | modul | test_klassifiziere_deadlock_patch_vorhanden | 1 | Kern bleibt | ruft klassifiziere_deadlock |
| test_pipeline.py | 4680 | modul | test_pruefe_trigger_b_bei_patch_mit_frage_im_fuss | 1 | Kern bleibt | ruft pruefe_trigger_b |
| test_pipeline.py | 4689 | modul | test_pruefe_trigger_b_bei_patch_ohne_frage | 1 | Kern bleibt | ruft pruefe_trigger_b |
| test_pipeline.py | 4695 | modul | test_pruefe_trigger_b_bei_langer_antwort_ohne_frage | 1 | Kern bleibt | ruft pruefe_trigger_b |
| test_pipeline.py | 4701 | modul | test_pruefe_trigger_b_bei_frage_ohne_inhaltswort | 1 | Kern bleibt | ruft pruefe_trigger_b |
| test_pipeline.py | 4707 | modul | test_pruefe_trigger_b_bei_frage_im_mittelteil | 1 | Kern bleibt | ruft pruefe_trigger_b |
| test_pipeline.py | 4713 | modul | test_erlaubte_solver_quellen_enthaelt_neue | 1 | Kern bleibt | ruft ERLAUBTE_SOLVER_QUELLEN |
| test_pipeline.py | 4719 | modul | test_inhaltswoerter_liste_vorhanden | 1 | Kern bleibt | ruft INHALTSWOERTER_TRIGGER_B |
| test_pipeline.py | 4726 | modul | test_pruefe_anker_wirkungslos_erkannt | 1 | Kern bleibt | ruft pruefe_anker_gegen_messung |
| test_pipeline.py | 4736 | modul | test_pruefe_anker_mit_trailing_whitespace_ist_wirkungslos | 1 | Kern bleibt | ruft pruefe_anker_gegen_messung |
| test_pipeline.py | 4746 | modul | test_pruefe_anker_leer_bleibt_leer | 1 | Kern bleibt | ruft pruefe_anker_gegen_messung |
| test_pipeline.py | 4754 | modul | test_pruefe_anker_wirkungslos_hat_einen_grund_pro_patch | 1 | Kern bleibt | ruft pruefe_anker_gegen_messung |
| test_pipeline.py | 4762 | modul | test_pruefe_anker_wirksamer_patch_kein_fehler | 1 | Kern bleibt | ruft pruefe_anker_gegen_messung |
| test_pipeline.py | 4772 | modul | test_letzter_patch_wirkungslos_initial_false | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_pipeline.py | 4778 | modul | test_wirkungslos_setzt_flag_im_loop | 1 | Kern bleibt | ruft pruefe_anker_gegen_messung |
| test_pipeline.py | 4788 | modul | test_nicht_wirkungslos_setzt_flag_nicht | 1 | Kern bleibt | ruft pruefe_anker_gegen_messung |
| test_pipeline.py | 4798 | modul | test_erlaubte_quelle_wirkungsloser_patch | 1 | Kern bleibt | ruft ERLAUBTE_SOLVER_QUELLEN |
| test_pipeline.py | 4803 | modul | test_wirkungslos_flag_ist_trigger_c_vorbedingung | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_pipeline.py | 4813 | modul | test_auftrag_bereits_erfuellt_mit_bestaetigung | 1 | Kern bleibt | ruft SolverBefund, SolverDiagnose |
| test_pipeline.py | 4826 | modul | test_auftrag_bereits_erfuellt_ohne_flag | 1 | Kern bleibt | ruft SolverBefund, SolverDiagnose |
| test_pipeline.py | 4837 | modul | test_auftrag_bereits_erfuellt_ohne_solver | 1 | Kern bleibt | ruft pruefe_auftrag_bereits_erfuellt |
| test_pipeline.py | 4845 | modul | test_auftrag_bereits_erfuellt_mit_widerspruch | 1 | Kern bleibt | ruft SolverBefund, SolverDiagnose |
| test_pipeline.py | 4857 | modul | test_auftrag_bereits_erfuellt_ohne_quelle | 1 | Kern bleibt | ruft SolverBefund, SolverDiagnose |
| test_pipeline.py | 4870 | modul | test_erhoehe_solver_aufruf_unter_limit | 1 | Kern bleibt | ruft erhoehe_solver_aufruf |
| test_pipeline.py | 4878 | modul | test_erhoehe_solver_aufruf_am_limit | 1 | Kern bleibt | ruft erhoehe_solver_aufruf |
| test_pipeline.py | 4886 | modul | test_bestaetigung_erfordert_vollstaendigen_befund | 1 | Kern bleibt | ruft SolverBefund, SolverDiagnose |
| test_pipeline.py | 4900 | modul | test_bestaetigung_unklar_ist_keine | 1 | Kern bleibt | ruft SolverBefund, SolverDiagnose |
| test_pipeline.py | 4914 | modul | test_solver_prompt_enthaelt_auftrag_erfuellt_hinweis | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_pipeline.py | 4923 | modul | test_solver_md_enthaelt_gemessenen_inhalt_erwaehnung | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_pipeline.py | 4933 | modul | test_solver_prompt_enthaelt_auftrag | 1 | Phase-3-Code | ruft _solver_prompt_bauen |
| test_pipeline.py | 4942 | modul | test_solver_prompt_auftrag_vor_no_go | 1 | Phase-3-Code | ruft _solver_prompt_bauen |
| test_pipeline.py | 4954 | modul | test_solver_prompt_auftrag_leer | 1 | Phase-3-Code | ruft _solver_prompt_bauen |
| test_pipeline.py | 4964 | modul | test_format_projekt_stand_leer | 1 | Kern bleibt | ruft format_projekt_stand |
| test_pipeline.py | 4971 | modul | test_format_projekt_stand_mit_commits | 1 | Kern bleibt | ruft format_projekt_stand |
| test_pipeline.py | 4991 | modul | test_format_projekt_stand_max_5 | 1 | Kern bleibt | ruft format_projekt_stand |
| test_pipeline.py | 5007 | modul | test_projekt_stand_im_builder_prompt | 1 | Kern bleibt | ruft format_projekt_stand |
| test_pipeline.py | 5023 | modul | test_projekt_stand_nach_auftrag_im_solver | 1 | Phase-3-Code | ruft _solver_prompt_bauen |
| test_pipeline.py | 5041 | modul | test_solver_schon_gelaufen | 1 | Kern bleibt | ruft SolverBefund, SolverDiagnose |
| test_pipeline.py | 5067 | modul | test_mess_protokoll_veraltet_default_false | 1 | Kern bleibt | ruft RunState |
| test_pipeline.py | 5078 | modul | test_mess_protokoll_nicht_mutiert_von_veraltet_flag | 1 | Kern bleibt | ruft RunState |
| test_pipeline.py | 5091 | modul | test_nach_apply_block_leer_bleibt_weg | 1 | Kern bleibt | ruft RunState |
| test_pipeline.py | 5117 | modul | test_nach_apply_block_erscheint_bei_inhalt | 1 | Kern bleibt | ruft RunState |
| test_pipeline.py | 5136 | modul | test_prompt_phase1_vor_erstem_apply_kein_header | 1 | Kern bleibt | ruft RunState |
| test_pipeline.py | 9568 | modul | test_w46b_1_doku_only_skip | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_pipeline.py | 9580 | modul | test_w46b_2_code_patch_kein_skip | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_pipeline.py | 9588 | modul | test_w46b_3_mischform_kein_skip | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_pipeline.py | 9599 | modul | test_w46b_4_null_passed_skip | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_pipeline.py | 9611 | modul | test_w46c_1_doku_phase_skip | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_pipeline.py | 9620 | modul | test_w46c_2_repair_runde_gleiche_bedingung | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_pipeline.py | 9632 | modul | test_w46_katalog_107 | 1 | Kern bleibt | ruft _AUDIT_KINDS_BEKANNT |
| test_pipeline.py | 9639 | modul | test_w48_e_katalog_kinds | 1 | Kern bleibt | ruft _AUDIT_KINDS_BEKANNT |
| test_pipeline.py | 9646 | modul | test_w50_a_block_ohne_flag | 1 | Phase-3-Code | ruft _phase_main_pfad |
| test_pipeline.py | 9685 | modul | test_w50_b_keine_yaml_planner_laeuft | 1 | Phase-3-Code | ruft _phase_main_pfad |
| test_pipeline.py | 9712 | modul | test_w50_c_phase_aktiv_resume_pfad | 1 | Phase-3-Code | ruft _phase_main_pfad |
| test_pipeline.py | 9752 | modul | test_w50_d_flag_durchlassen | 1 | Phase-3-Code | ruft _phase_main_pfad |
| test_pipeline.py | 9793 | modul | test_w50_e_flag_ohne_yaml | 1 | Phase-3-Code | ruft _phase_main_pfad |
| test_pipeline.py | 9827 | modul | test_w50_f_new_phase_ohne_phase_failt | 1 | Kern bleibt | ruft _validate_new_phase_args |
| test_pipeline.py | 9838 | modul | test_w51a_struktur | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_pipeline.py | 9848 | modul | test_w51a_extrahiere_datei_pfade | 1 | Kern bleibt | ruft _w51a_extrahiere_datei_pfade |
| test_pipeline.py | 9856 | modul | test_w51b_new_file_existiert | 1 | Phase-3-Code | ruft _plan_ist_new_file_valide |
| test_pipeline.py | 9872 | modul | test_w51b_new_file_nicht_existiert | 1 | Phase-3-Code | ruft _plan_ist_new_file_valide |
| test_pipeline.py | 9886 | modul | test_w51b_patch_ok | 1 | Phase-3-Code | ruft _plan_ist_new_file_valide |
| test_pipeline.py | 9901 | modul | test_w51b_werkstatt_pfad_fail | 1 | Phase-3-Code | ruft _plan_ist_new_file_valide |
| test_pipeline.py | 9916 | modul | test_w51b_pfad_escape_fail | 1 | Phase-3-Code | ruft _plan_ist_new_file_valide |
| test_pipeline.py | 9932 | modul | test_w51c_a_struktur | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_pipeline.py | 9943 | modul | test_w51c_b_bereinigt_messungen | 1 | Kern bleibt | ruft _bereinige_planner_reply |
| test_pipeline.py | 9958 | modul | test_w51c_c_parse_planner_mit_praefix | 1 | Kern bleibt | ruft _parse_commands_planner |
| test_pipeline.py | 9970 | modul | test_w51c_d_fallback_ohne_klammer | 1 | Kern bleibt | ruft _bereinige_planner_reply |
| test_pipeline.py | 9982 | modul | test_w51c_e_gemessener_inhalt | 1 | Kern bleibt | ruft _bereinige_planner_reply |
| test_pipeline.py | 10000 | modul | test_w51c_f_katalog_115 | 1 | Kern bleibt | ruft _AUDIT_KINDS_BEKANNT |
| test_pipeline.py | 10008 | modul | test_w51c_g_command_block_in_plan_gemeldet | 1 | Kern bleibt | ruft _bereinige_planner_reply |
| test_pipeline.py | 10022 | modul | test_w51c_fix_planner_nutzt_planner_parser | 1 | Phase-3-Code | ruft _planner_lauf |
| test_pipeline.py | 10062 | modul | test_w51c_fix_planner_verwirft_unerlaubte_commands | 4 | Kern bleibt | ruft _parse_commands_planner |
| test_pipeline.py | 10070 | modul | test_w51c_fix_planner_erkennt_load_skill | 1 | Kern bleibt | ruft _parse_commands_planner |
| test_pipeline.py | 10078 | modul | test_w51c_fix_planner_read_file_ok | 1 | Kern bleibt | ruft _parse_commands_planner |
| test_pipeline.py | 10085 | modul | test_w51d_a2_beide_zustaende | 1 | Phase-3-Code | ruft _planner_user_content |
| test_pipeline.py | 10105 | modul | test_w51d_b_struktur | 1 | Kern bleibt | ruft MAX_PROTOKOLL_PER_COMMAND_READ_FILE, MAX_PROTOKOLL_TOTAL |
| test_pipeline.py | 10113 | modul | test_w51d_c_planner_md_genau_einmal | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_pipeline.py | 10137 | modul | test_w51d_b_verhalten_planner_vs_builder | 1 | Kern bleibt | ruft execute_commands |
| test_pipeline.py | 10166 | modul | test_w51d_d_limit_audit | 1 | Kern bleibt | ruft _PLANNER_PROTOKOLL_TOTAL, execute_commands |
| test_pipeline.py | 10198 | modul | test_w51e_a_runde_ohne_neue_messung | 1 | Phase-3-Code | ruft _planner_lauf |
| test_pipeline.py | 10246 | modul | test_w51e_a_variante_runde1_ohne_command | 1 | Phase-3-Code | ruft _planner_lauf |
| test_pipeline.py | 10269 | modul | test_w51e_b_regression_plan_in_runde2 | 1 | Phase-3-Code | ruft _planner_lauf |
| test_pipeline.py | 10301 | modul | test_w51f_a_struktur | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_pipeline.py | 10325 | modul | test_w51f_b_zu_viele_unterbloecke | 1 | Phase-3-Code | ruft _plan_ist_portionierbar |
| test_pipeline.py | 10334 | modul | test_w51f_c_zu_viele_dateien | 1 | Phase-3-Code | ruft _plan_ist_portionierbar |
| test_pipeline.py | 10343 | modul | test_w51f_d_gruen | 1 | Phase-3-Code | ruft _plan_ist_portionierbar |
| test_pipeline.py | 10351 | modul | test_w51f_f_katalog_118 | 1 | Kern bleibt | ruft _AUDIT_KINDS_BEKANNT |
| test_pipeline.py | 10372 | modul | test_w51g_a_dedup | 1 | Kern bleibt | ruft execute_commands |
| test_pipeline.py | 10391 | modul | test_w51g_b_kontext | 1 | Phase-3-Code | ruft _planner_user_content |
| test_pipeline.py | 10403 | modul | test_w51g_b_leer | 1 | Phase-3-Code | ruft _planner_user_content |
| test_pipeline.py | 10412 | modul | test_w51g_c_lebenszyklus | 1 | Kern bleibt | ruft _parse_phase_plan |
| test_pipeline.py | 10431 | modul | test_w51g_d_nicht_read_file | 1 | Kern bleibt | ruft execute_commands |
| test_pipeline.py | 10454 | modul | test_w51g_e_scope | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_pipeline.py | 10489 | modul | test_w51h_a_plan_und_command | 1 | Phase-3-Code | ruft _planner_lauf |
| test_pipeline.py | 10520 | modul | test_w51h_b_nur_command | 1 | Phase-3-Code | ruft _planner_lauf |
| test_pipeline.py | 10556 | modul | test_w51h_c_plan_ohne_command | 1 | Phase-3-Code | ruft _planner_lauf |
| test_pipeline.py | 10576 | modul | test_w51h_d_plan_format_fehler | 1 | Phase-3-Code | ruft _planner_lauf |
| test_pipeline.py | 10622 | modul | test_w51h_e_vor_w51e | 1 | Phase-3-Code | ruft _planner_lauf |
| test_pipeline.py | 10669 | modul | test_w54_a_builder_md | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_pipeline.py | 10680 | modul | test_w54_c_zwei_normale_patches | 1 | Kern bleibt | ruft apply_code_patches |
| test_pipeline.py | 10705 | modul | test_w54_d_kurzer_ersatz_kein_fail | 1 | Kern bleibt | ruft apply_code_patches |
| test_pipeline.py | 10748 | modul | test_w54_g_a_anker_doppelt | 1 | Kern bleibt | ruft apply_code_patches |
| test_pipeline.py | 10776 | modul | test_w54_g_b_verschiedene_zeilen | 1 | Kern bleibt | ruft apply_code_patches |
| test_pipeline.py | 10800 | modul | test_w54_g_c_lange_zeile_doppelt | 1 | Kern bleibt | ruft apply_code_patches |
| test_pipeline.py | 10824 | modul | test_w54_g_d_kurze_legit_doppelt | 1 | Kern bleibt | ruft apply_code_patches |
| test_pipeline.py | 10850 | modul | test_w54_h_a_builder_md | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_pipeline.py | 64 | TestLoadProjectConfig | test_loads_valid_config | 1 | Kern bleibt | ruft load_project_config |
| test_pipeline.py | 74 | TestLoadProjectConfig | test_fails_on_unknown_project | 1 | Kern bleibt | ruft load_project_config |
| test_pipeline.py | 79 | TestLoadProjectConfig | test_fails_on_empty_name | 1 | Kern bleibt | ruft load_project_config |
| test_pipeline.py | 84 | TestLoadProjectConfig | test_fails_on_path_traversal | 1 | Kern bleibt | ruft load_project_config |
| test_pipeline.py | 89 | TestLoadProjectConfig | test_fails_on_slash_in_name | 1 | Kern bleibt | ruft load_project_config |
| test_pipeline.py | 100 | TestParseCommands | test_parses_valid_command | 1 | Kern bleibt | ruft parse_commands |
| test_pipeline.py | 107 | TestParseCommands | test_parses_valid_command_with_arg | 1 | Kern bleibt | ruft parse_commands |
| test_pipeline.py | 114 | TestParseCommands | test_ignores_lines_without_command_prefix | 1 | Kern bleibt | ruft parse_commands |
| test_pipeline.py | 118 | TestParseCommands | test_ignores_non_run_commands | 1 | Kern bleibt | ruft parse_commands |
| test_pipeline.py | 122 | TestParseCommands | test_parses_multiple_commands | 1 | Kern bleibt | ruft parse_commands |
| test_pipeline.py | 129 | TestParseCommands | test_arg_is_always_str | 1 | Kern bleibt | ruft parse_commands |
| test_pipeline.py | 143 | TestClassifyVerdict | test_go | 1 | Kern bleibt | ruft classify_verdict |
| test_pipeline.py | 146 | TestClassifyVerdict | test_go_with_leading_whitespace | 1 | Kern bleibt | ruft classify_verdict |
| test_pipeline.py | 149 | TestClassifyVerdict | test_no_go | 1 | Kern bleibt | ruft classify_verdict |
| test_pipeline.py | 152 | TestClassifyVerdict | test_eskalation | 1 | Kern bleibt | ruft classify_verdict |
| test_pipeline.py | 155 | TestClassifyVerdict | test_commit_go | 1 | Kern bleibt | ruft classify_verdict |
| test_pipeline.py | 158 | TestClassifyVerdict | test_commit_no_go | 1 | Kern bleibt | ruft classify_verdict |
| test_pipeline.py | 161 | TestClassifyVerdict | test_command | 1 | Kern bleibt | ruft classify_verdict |
| test_pipeline.py | 164 | TestClassifyVerdict | test_unknown | 1 | Kern bleibt | ruft classify_verdict |
| test_pipeline.py | 167 | TestClassifyVerdict | test_unknown_with_irrelevant_text | 1 | Kern bleibt | ruft classify_verdict |
| test_pipeline.py | 170 | TestClassifyVerdict | test_go_after_many_inhalt_lines | 1 | Kern bleibt | ruft classify_verdict |
| test_pipeline.py | 175 | TestClassifyVerdict | test_go_after_few_empty_lines | 1 | Kern bleibt | ruft classify_verdict |
| test_pipeline.py | 180 | TestClassifyVerdict | test_go_at_line_15 | 1 | Kern bleibt | ruft classify_verdict |
| test_pipeline.py | 186 | TestClassifyVerdict | test_go_at_line_16 | 1 | Kern bleibt | ruft classify_verdict |
| test_pipeline.py | 196 | TestClassifyVerdict | test_go_mit_punkt | 1 | Kern bleibt | ruft classify_verdict |
| test_pipeline.py | 199 | TestClassifyVerdict | test_go_mit_doppelpunkt | 1 | Kern bleibt | ruft classify_verdict |
| test_pipeline.py | 202 | TestClassifyVerdict | test_no_go_mit_doppelpunkt | 1 | Kern bleibt | ruft classify_verdict |
| test_pipeline.py | 205 | TestClassifyVerdict | test_no_go_mit_punkt | 1 | Kern bleibt | ruft classify_verdict |
| test_pipeline.py | 208 | TestClassifyVerdict | test_eskalation_mit_ausrufezeichen | 1 | Kern bleibt | ruft classify_verdict |
| test_pipeline.py | 211 | TestClassifyVerdict | test_eskalation_mit_fragezeichen | 1 | Kern bleibt | ruft classify_verdict |
| test_pipeline.py | 214 | TestClassifyVerdict | test_commit_go_mit_punkt | 1 | Kern bleibt | ruft classify_verdict |
| test_pipeline.py | 217 | TestClassifyVerdict | test_commit_no_go_mit_doppelpunkt | 1 | Kern bleibt | ruft classify_verdict |
| test_pipeline.py | 221 | TestClassifyVerdict | test_bindestrich_wird_nicht_zerlegt | 1 | Kern bleibt | ruft classify_verdict |
| test_pipeline.py | 225 | TestClassifyVerdict | test_go_mit_klammer | 1 | Kern bleibt | ruft classify_verdict |
| test_pipeline.py | 234 | TestParseAuflagen | test_parses_a_prefix | 1 | Kern bleibt | ruft parse_auflagen |
| test_pipeline.py | 241 | TestParseAuflagen | test_parses_number_without_prefix | 1 | Kern bleibt | ruft parse_auflagen |
| test_pipeline.py | 247 | TestParseAuflagen | test_ignores_unrelated_text | 1 | Kern bleibt | ruft parse_auflagen |
| test_pipeline.py | 250 | TestParseAuflagen | test_ignores_empty | 1 | Kern bleibt | ruft parse_auflagen |
| test_pipeline.py | 259 | TestTrimOutput | test_short_text_unchanged | 1 | Kern bleibt | ruft trim_output |
| test_pipeline.py | 263 | TestTrimOutput | test_long_text_truncated | 1 | Kern bleibt | ruft trim_output |
| test_pipeline.py | 270 | TestTrimOutput | test_exact_boundary | 1 | Kern bleibt | ruft trim_output |
| test_pipeline.py | 303 | TestParseCommitPaket | test_parses_full_paket | 1 | Kern bleibt | ruft parse_commit_paket |
| test_pipeline.py | 321 | TestParseCommitPaket | test_empty_text | 1 | Kern bleibt | ruft parse_commit_paket |
| test_pipeline.py | 327 | TestParseCommitPaket | test_zwei_patches_in_einer_antwort | 1 | Kern bleibt | ruft parse_commit_paket |
| test_pipeline.py | 351 | TestParseCommitPaket | test_anker_leer_patch_verworfen | 1 | Kern bleibt | ruft parse_commit_paket |
| test_pipeline.py | 364 | TestParseCommitPaket | test_mehrzeiliger_ersatz | 1 | Kern bleibt | ruft parse_commit_paket |
| test_pipeline.py | 381 | TestParseCommitPaket | test_mehrzeiliger_anker | 1 | Kern bleibt | ruft parse_commit_paket |
| test_pipeline.py | 401 | TestParseCommitPaket | test_leerer_ersatz_erlaubt | 1 | Kern bleibt | ruft parse_commit_paket |
| test_pipeline.py | 415 | TestParseCommitPaket | test_tab_einrueckung_verworfen | 1 | Kern bleibt | ruft parse_commit_paket |
| test_pipeline.py | 435 | TestParseEmpfehlung | test_parses_all_fields | 1 | Kern bleibt | ruft parse_empfehlung |
| test_pipeline.py | 446 | TestParseEmpfehlung | test_empty | 1 | Kern bleibt | ruft parse_empfehlung |
| test_pipeline.py | 463 | TestExecuteCommands | test_unknown_id_rejected | 1 | Kern bleibt | ruft execute_commands |
| test_pipeline.py | 486 | TestExecuteCommands | test_known_id_executed | 1 | Kern bleibt | ruft Measurement, execute_commands |
| test_pipeline.py | 513 | TestExecuteCommands | test_arg_not_str_rejected | 1 | Kern bleibt | ruft Measurement, execute_commands |
| test_pipeline.py | 539 | TestExecuteCommands | test_quelle_invalid_marked | 1 | Kern bleibt | ruft Measurement, execute_commands |
| test_pipeline.py | 563 | TestExecuteCommands | test_mess_protokoll_grows | 1 | Kern bleibt | ruft Measurement, execute_commands |
| test_pipeline.py | 580 | TestExecuteCommands | test_empty_commands_no_effect | 1 | Kern bleibt | ruft execute_commands |
| test_pipeline.py | 594 | TestExecuteCommands | test_id_not_str_rejected | 1 | Kern bleibt | ruft execute_commands |
| test_pipeline.py | 640 | TestApplyCommitAndDoku | test_keine_dateien_abbruch | 1 | Kern bleibt | ruft apply_commit_and_doku |
| test_pipeline.py | 647 | TestApplyCommitAndDoku | test_datei_nicht_in_whitelist | 1 | Kern bleibt | ruft apply_commit_and_doku |
| test_pipeline.py | 655 | TestApplyCommitAndDoku | test_datei_existiert_nicht | 1 | Kern bleibt | ruft apply_commit_and_doku |
| test_pipeline.py | 662 | TestApplyCommitAndDoku | test_doku_datei_fehlt | 1 | Kern bleibt | ruft apply_commit_and_doku |
| test_pipeline.py | 673 | TestApplyCommitAndDoku | test_anker_kommt_null_mal | 1 | Kern bleibt | ruft apply_commit_and_doku |
| test_pipeline.py | 687 | TestApplyCommitAndDoku | test_anker_kommt_zweimal_vor | 1 | Kern bleibt | ruft apply_commit_and_doku |
| test_pipeline.py | 701 | TestApplyCommitAndDoku | test_erfolg_mit_doku_patch | 1 | Kern bleibt | ruft apply_commit_and_doku |
| test_pipeline.py | 738 | TestApplyCommitAndDoku | test_doku_patch_nicht_geschrieben_wenn_datei_fehlt | 1 | Kern bleibt | ruft apply_commit_and_doku |
| test_pipeline.py | 759 | TestApplyCommitAndDoku | test_doku_patch_nicht_geschrieben_wenn_anker_fehlt | 1 | Kern bleibt | ruft apply_commit_and_doku |
| test_pipeline.py | 779 | TestApplyCommitAndDoku | test_doku_patch_rollback_wenn_git_add_fehlt | 1 | Kern bleibt | ruft apply_commit_and_doku |
| test_pipeline.py | 814 | TestApplyCommitAndDoku | test_doku_patch_rollback_wenn_git_commit_fehlt | 1 | Kern bleibt | ruft apply_commit_and_doku |
| test_pipeline.py | 849 | TestApplyCommitAndDoku | test_erfolg_ohne_doku_patch | 1 | Kern bleibt | ruft apply_commit_and_doku |
| test_pipeline.py | 874 | TestSnapshotTestsDir | test_leeres_verzeichnis_kein_snapshot | 1 | Kern bleibt | ruft snapshot_tests_dir |
| test_pipeline.py | 879 | TestSnapshotTestsDir | test_leeres_tests_verzeichnis | 1 | Kern bleibt | ruft snapshot_tests_dir |
| test_pipeline.py | 885 | TestSnapshotTestsDir | test_eine_datei | 1 | Kern bleibt | ruft snapshot_tests_dir |
| test_pipeline.py | 893 | TestSnapshotTestsDir | test_mehrere_dateien_inkl_unterordner | 1 | Kern bleibt | ruft snapshot_tests_dir |
| test_pipeline.py | 905 | TestSnapshotTestsDir | test_nicht_py_dateien_ignoriert | 1 | Kern bleibt | ruft snapshot_tests_dir |
| test_pipeline.py | 921 | TestCheckTestsDirUnveraendert | test_keine_aenderung_ok | 1 | Kern bleibt | ruft check_tests_dir_unveraendert, snapshot_tests_dir |
| test_pipeline.py | 930 | TestCheckTestsDirUnveraendert | test_datei_geloescht_nicht_ok | 1 | Kern bleibt | ruft check_tests_dir_unveraendert, snapshot_tests_dir |
| test_pipeline.py | 942 | TestCheckTestsDirUnveraendert | test_datei_kleiner_nicht_ok | 1 | Kern bleibt | ruft check_tests_dir_unveraendert, snapshot_tests_dir |
| test_pipeline.py | 954 | TestCheckTestsDirUnveraendert | test_datei_groesser_ok | 1 | Kern bleibt | ruft check_tests_dir_unveraendert, snapshot_tests_dir |
| test_pipeline.py | 965 | TestCheckTestsDirUnveraendert | test_neue_datei_ok | 1 | Kern bleibt | ruft check_tests_dir_unveraendert, snapshot_tests_dir |
| test_pipeline.py | 976 | TestCheckTestsDirUnveraendert | test_zwei_probleme | 1 | Kern bleibt | ruft check_tests_dir_unveraendert, snapshot_tests_dir |
| test_pipeline.py | 992 | TestCheckTestsDirUnveraendert | test_leerer_snapshot_ok | 1 | Kern bleibt | ruft check_tests_dir_unveraendert |
| test_pipeline.py | 1011 | TestSubprocessEnv | test_env_does_not_contain_api_key | 1 | Kern bleibt | ruft subprocess_env |
| test_pipeline.py | 1019 | TestSubprocessEnv | test_env_contains_path | 1 | Kern bleibt | ruft subprocess_env |
| test_pipeline.py | 1025 | TestSubprocessEnv | test_env_does_not_contain_unknown_var | 1 | Kern bleibt | ruft subprocess_env |
| test_pipeline.py | 1035 | TestSubprocessEnv | test_subprocess_run_uses_clean_env | 1 | Kern bleibt | ruft Measurement, run_measurement |
| test_pipeline.py | 1092 | TestAskLlmRetry | test_200_kein_retry | 1 | Kern bleibt | ruft ask_llm, requests |
| test_pipeline.py | 1113 | TestAskLlmRetry | test_401_kein_retry | 1 | Kern bleibt | ruft ask_llm, requests |
| test_pipeline.py | 1135 | TestAskLlmRetry | test_429_dann_200 | 1 | Kern bleibt | ruft ask_llm, requests |
| test_pipeline.py | 1163 | TestAskLlmRetry | test_500_500_kein_dritter_versuch | 1 | Kern bleibt | ruft ask_llm, requests |
| test_pipeline.py | 1186 | TestAskLlmRetry | test_connection_error_retry | 1 | Kern bleibt | ruft ask_llm, requests |
| test_pipeline.py | 1238 | TestAskLlmUserContentMaxLen | test_kuerzt_nicht_bei_10k_zeichen | 1 | Kern bleibt | ruft ask_llm |
| test_pipeline.py | 1252 | TestAskLlmUserContentMaxLen | test_kuerzt_bei_ueber_100k | 1 | Kern bleibt | ruft ask_llm |
| test_pipeline.py | 1264 | TestAskLlmUserContentMaxLen | test_redaction_greift_weiterhin | 1 | Kern bleibt | ruft ask_llm |
| test_pipeline.py | 1320 | TestRecoveryBlock | test_frage_an_menschen_default_leer | 1 | Kern bleibt | ruft RecoveryVorschlag |
| test_pipeline.py | 1324 | TestRecoveryBlock | test_parser_erkennt_frage_an_menschen | 1 | Kern bleibt | ruft ask_reviewer_for_recovery |
| test_pipeline.py | 1341 | TestRecoveryBlock | test_parser_ohne_frage_an_menschen | 1 | Kern bleibt | ruft ask_reviewer_for_recovery |
| test_pipeline.py | 1350 | TestRecoveryBlock | test_print_recovery_zeigt_frage | 1 | Kern bleibt | ruft RecoveryVorschlag, print_recovery |
| test_pipeline.py | 1365 | TestRecoveryBlock | test_print_recovery_ohne_frage | 1 | Kern bleibt | ruft RecoveryVorschlag, print_recovery |
| test_pipeline.py | 1389 | TestAudit | test_schreibt_in_werkstatt_audit_dir | 1 | Kern bleibt | ruft audit |
| test_pipeline.py | 1405 | TestAudit | test_project_feld_bleibt | 1 | Kern bleibt | ruft audit |
| test_pipeline.py | 1421 | TestAudit | test_mkdir_legt_fehlendes_verzeichnis_an | 1 | Kern bleibt | ruft audit |
| test_pipeline.py | 1446 | TestRootGuard | test_getuid_0_ergibt_exit_66 | 1 | Kern bleibt | ruft main, os |
| test_pipeline.py | 1455 | TestRootGuard | test_getuser_root_ergibt_exit_66 | 1 | Kern bleibt | ruft main, os |
| test_pipeline.py | 1466 | TestRootGuard | test_getuser_fehler_kein_absturz | 1 | Kern bleibt | ruft main, os |
| test_pipeline.py | 1496 | TestBudgetTime | test_zeitbudget_deaktiviert_max_0 | 1 | Kern bleibt | ruft require_budget_time, time |
| test_pipeline.py | 1506 | TestBudgetTime | test_zeitbudget_ok_unter_limit | 1 | Kern bleibt | ruft require_budget_time, time |
| test_pipeline.py | 1517 | TestBudgetTime | test_zeitbudget_erschoepft | 1 | Kern bleibt | ruft BudgetExhausted, require_budget_time |
| test_pipeline.py | 1528 | TestBudgetTime | test_zeitbudget_grenze_genau | 1 | Kern bleibt | ruft require_budget_time, time |
| test_pipeline.py | 1539 | TestBudgetTime | test_budget_or_recover_zeit | 1 | Kern bleibt | ruft RecoveryVorschlag, budget_or_recover |
| test_pipeline.py | 1574 | TestBudgetTime | test_budget_or_recover_nennt_dimension | 1 | Kern bleibt | ruft RecoveryVorschlag, budget_or_recover |
| test_pipeline.py | 1618 | TestBudgetRecovery | test_budget_exhausted_recovery_bei_commit_review | 1 | Kern bleibt | ruft RecoveryVorschlag, budget_or_recover |
| test_pipeline.py | 1647 | TestBudgetRecovery | test_budget_exhausted_recovery_konsistent | 1 | Kern bleibt | ruft RecoveryVorschlag, budget_or_recover |
| test_pipeline.py | 1691 | TestBudgetRecovery | test_budget_recovery_wird_auditiert | 1 | Kern bleibt | ruft RecoveryVorschlag, budget_or_recover |
| test_pipeline.py | 1786 | TestCollectMesswerte | test_collect_messwerte_aus_protokoll | 1 | Kern bleibt | ruft collect_messwerte |
| test_pipeline.py | 1797 | TestCollectMesswerte | test_collect_messwerte_fallback | 1 | Kern bleibt | ruft collect_messwerte |
| test_pipeline.py | 1808 | TestCollectMesswerte | test_collect_messwerte_rc_parsing | 1 | Kern bleibt | ruft collect_messwerte |
| test_pipeline.py | 1825 | TestCollectMesswerte | test_git_status_geaendert | 1 | Kern bleibt | ruft collect_messwerte |
| test_pipeline.py | 1842 | TestCollectMesswerte | test_format_messwerte_block | 1 | Kern bleibt | ruft format_messwerte_block |
| test_pipeline.py | 1857 | TestCollectMesswerte | test_format_messwerte_block_fallback | 1 | Kern bleibt | ruft format_messwerte_block |
| test_pipeline.py | 1870 | TestCollectMesswerte | test_format_doc_snippets_mit_docs | 1 | Kern bleibt | ruft format_doc_snippets |
| test_pipeline.py | 1883 | TestCollectMesswerte | test_format_doc_snippets_leer | 1 | Kern bleibt | ruft format_doc_snippets |
| test_pipeline.py | 1888 | TestCollectMesswerte | test_format_doc_snippets_kuerzt | 1 | Kern bleibt | ruft format_doc_snippets |
| test_pipeline.py | 1902 | TestCollectMesswerte | test_format_doc_snippets_redigiert | 1 | Kern bleibt | ruft format_doc_snippets |
| test_pipeline.py | 1916 | TestParseCodePatches | test_parse_code_patches_ok | 1 | Kern bleibt | ruft parse_code_patches |
| test_pipeline.py | 1932 | TestParseCodePatches | test_parse_code_patches_leer | 1 | Kern bleibt | ruft parse_code_patches |
| test_pipeline.py | 1936 | TestParseCodePatches | test_parse_code_patches_mehrere | 1 | Kern bleibt | ruft parse_code_patches |
| test_pipeline.py | 1958 | TestParseCodePatches | test_parse_code_patches_anker_leer_verworfen | 1 | Kern bleibt | ruft parse_code_patches |
| test_pipeline.py | 1974 | TestApplyCodePatches | test_apply_ok | 1 | Kern bleibt | ruft apply_code_patches |
| test_pipeline.py | 1987 | TestApplyCodePatches | test_apply_anker_fehlt | 1 | Kern bleibt | ruft apply_code_patches |
| test_pipeline.py | 2000 | TestApplyCodePatches | test_apply_whitelist_fail | 1 | Kern bleibt | ruft apply_code_patches |
| test_pipeline.py | 2012 | TestApplyCodePatches | test_apply_pfad_doppelt | 1 | Kern bleibt | ruft apply_code_patches |
| test_pipeline.py | 2027 | TestApplyCodePatches | test_apply_mehrere_patches | 1 | Kern bleibt | ruft apply_code_patches |
| test_pipeline.py | 2045 | TestApplyCodePatches | test_apply_dry_run_schreibt_nicht | 1 | Kern bleibt | ruft apply_code_patches |
| test_pipeline.py | 2058 | TestApplyCodePatches | test_apply_leer_fail | 1 | Kern bleibt | ruft apply_code_patches |
| test_pipeline.py | 2065 | TestApplyCodePatches | test_shift_lines | 1 | Kern bleibt | ruft _shift_lines |
| test_pipeline.py | 2070 | TestApplyCodePatches | test_einrueckung_korrektur_greift | 1 | Kern bleibt | ruft apply_code_patches |
| test_pipeline.py | 2100 | TestApplyCodePatches | test_einrueckung_korrektur_audit | 1 | Kern bleibt | ruft apply_code_patches |
| test_pipeline.py | 2126 | TestApplyCodePatches | test_einrueckung_korrektur_fail_bei_2x | 1 | Kern bleibt | ruft apply_code_patches |
| test_pipeline.py | 2145 | TestApplyCodePatches | test_apply_zwei_patches_gleiche_datei | 1 | Kern bleibt | ruft apply_code_patches |
| test_pipeline.py | 2179 | TestApplyCodePatches | test_apply_zwei_patches_gleicher_anker_fail | 1 | Kern bleibt | ruft apply_code_patches |
| test_pipeline.py | 2199 | TestApplyCodePatches | test_apply_anker_muss_im_urstand_sein | 1 | Kern bleibt | ruft apply_code_patches |
| test_pipeline.py | 2228 | TestApplyCodePatches | test_apply_commit_msg_in_git | 1 | Kern bleibt | ruft apply_commit_and_doku |
| test_pipeline.py | 2300 | TestApplyAndRecheck | test_erfolg | 1 | Kern bleibt | ruft apply_and_recheck |
| test_pipeline.py | 2318 | TestApplyAndRecheck | test_keine_patches_16 | 1 | Kern bleibt | ruft apply_and_recheck |
| test_pipeline.py | 2326 | TestApplyAndRecheck | test_apply_fail_17 | 1 | Kern bleibt | ruft apply_and_recheck |
| test_pipeline.py | 2342 | TestApplyAndRecheck | test_recheck_rot_19 | 1 | Kern bleibt | ruft RecoveryVorschlag, apply_and_recheck |
| test_pipeline.py | 2377 | TestExtractPaths | test_findet_pfade | 1 | Kern bleibt | ruft extract_paths_from_aufgabe |
| test_pipeline.py | 2387 | TestExtractPaths | test_filtert_whitelist | 1 | Kern bleibt | ruft extract_paths_from_aufgabe |
| test_pipeline.py | 2396 | TestExtractPaths | test_filtert_nicht_existierend | 1 | Kern bleibt | ruft extract_paths_from_aufgabe |
| test_pipeline.py | 2402 | TestExtractPaths | test_dedupliziert | 1 | Kern bleibt | ruft extract_paths_from_aufgabe |
| test_pipeline.py | 2411 | TestExtractPaths | test_leere_aufgabe | 1 | Kern bleibt | ruft extract_paths_from_aufgabe |
| test_pipeline.py | 2417 | TestExtractPaths | test_w1_import_notation | 1 | Kern bleibt | ruft extract_paths_from_aufgabe |
| test_pipeline.py | 2424 | TestExtractPaths | test_w1_sql_endung | 1 | Kern bleibt | ruft extract_paths_from_aufgabe |
| test_pipeline.py | 2431 | TestExtractPaths | test_w1_neue_datei | 1 | Kern bleibt | ruft extract_paths_from_aufgabe |
| test_pipeline.py | 2440 | TestExtractPaths | test_w1_elternverzeichnis_fehlt | 1 | Kern bleibt | ruft extract_paths_from_aufgabe |
| test_pipeline.py | 2448 | TestExtractPaths | test_w1_stdlib_ignoriert | 1 | Kern bleibt | ruft extract_paths_from_aufgabe |
| test_pipeline.py | 2455 | TestExtractPaths | test_w1_pathlib_ignoriert | 1 | Kern bleibt | ruft extract_paths_from_aufgabe |
| test_pipeline.py | 2462 | TestExtractPaths | test_w1_mehrere_endungen | 1 | Kern bleibt | ruft extract_paths_from_aufgabe |
| test_pipeline.py | 2476 | TestReadTargetSnippets | test_liefert_ausschnitt | 1 | Kern bleibt | ruft read_target_snippets |
| test_pipeline.py | 2487 | TestReadTargetSnippets | test_nicht_whitelist | 1 | Kern bleibt | ruft read_target_snippets |
| test_pipeline.py | 2495 | TestReadTargetSnippets | test_datei_fehlt | 1 | Kern bleibt | ruft read_target_snippets |
| test_pipeline.py | 2500 | TestReadTargetSnippets | test_redigiert | 1 | Kern bleibt | ruft read_target_snippets |
| test_pipeline.py | 2508 | TestReadTargetSnippets | test_keine_pfade | 1 | Kern bleibt | ruft read_target_snippets |
| test_pipeline.py | 2512 | TestReadTargetSnippets | test_user_prompt_ohne_anker_beispiel | 1 | Kern bleibt | ruft __file__ |
| test_pipeline.py | 2567 | TestBuildSystemPrompt | test_base_immer_enthalten | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_pipeline.py | 2575 | TestBuildSystemPrompt | test_reviewer_enthaelt_r1_bis_r6 | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_pipeline.py | 2588 | TestBuildSystemPrompt | test_builder_enthaelt_b1_bis_b10 | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_pipeline.py | 2595 | TestBuildSystemPrompt | test_test_generator_enthaelt_t1_bis_t4 | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_pipeline.py | 2601 | TestBuildSystemPrompt | test_kein_monolith_hard_rules | 1 | Kern bleibt | ruft HARD_RULES |
| test_pipeline.py | 2606 | TestBuildSystemPrompt | test_reviewer_prompt_enthaelt_keine_builder_regeln | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_pipeline.py | 2613 | TestBuildSystemPrompt | test_builder_prompt_enthaelt_keine_reviewer_regeln | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_pipeline.py | 2629 | TestKuerzungsMarker | test_read_target_snippets_marker_vollstaendig | 1 | Kern bleibt | ruft read_target_snippets |
| test_pipeline.py | 2640 | TestKuerzungsMarker | test_read_target_snippets_marker_gekuerzt | 1 | Kern bleibt | ruft read_target_snippets |
| test_pipeline.py | 2652 | TestKuerzungsMarker | test_read_target_snippets_marker_enthaelt_pfad | 1 | Kern bleibt | ruft read_target_snippets |
| test_pipeline.py | 2661 | TestKuerzungsMarker | test_read_target_snippets_gekuerzt_marker_enthaelt_command | 1 | Kern bleibt | ruft read_target_snippets |
| test_pipeline.py | 2670 | TestKuerzungsMarker | test_read_target_snippets_grenze_exakt_max_len | 1 | Kern bleibt | ruft read_target_snippets |
| test_pipeline.py | 2681 | TestKuerzungsMarker | test_read_target_snippets_grenze_max_len_plus_eins | 1 | Kern bleibt | ruft read_target_snippets |
| test_pipeline.py | 2692 | TestKuerzungsMarker | test_format_doc_snippets_marker_vollstaendig | 1 | Kern bleibt | ruft format_doc_snippets |
| test_pipeline.py | 2698 | TestKuerzungsMarker | test_format_doc_snippets_marker_gekuerzt | 1 | Kern bleibt | ruft format_doc_snippets |
| test_pipeline.py | 2721 | TestBuilderCommandLoop | test_builder_command_wird_ausgefuehrt | 1 | Kern bleibt | ruft LLMReply, builder_reply_mit_command_loop |
| test_pipeline.py | 2755 | TestBuilderCommandLoop | test_builder_command_leere_liste_wie_bisher | 1 | Kern bleibt | ruft LLMReply, builder_reply_mit_command_loop |
| test_pipeline.py | 2784 | TestBuilderCommandLoop | test_builder_command_max_runden_erreicht | 1 | Kern bleibt | ruft LLMReply, RecoveryVorschlag |
| test_pipeline.py | 2822 | TestBuilderCommandLoop | test_builder_command_kein_endlosloop | 1 | Kern bleibt | ruft LLMReply, RecoveryVorschlag |
| test_pipeline.py | 2851 | TestBuilderCommandLoop | test_builder_command_quelle_marker_builder | 1 | Kern bleibt | ruft ERLAUBTE_QUELLEN |
| test_pipeline.py | 2855 | TestBuilderCommandLoop | test_builder_command_recovery_art | 1 | Kern bleibt | ruft LLMReply, ask_reviewer_for_recovery |
| test_pipeline.py | 2870 | TestBuilderCommandLoop | test_builder_command_unbekannte_id_abgelehnt | 1 | Kern bleibt | ruft execute_commands |
| test_pipeline.py | 2888 | TestBuilderCommandLoop | test_builder_command_read_file_im_optional_catalog | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_pipeline.py | 2907 | TestBuilderMdKuerzung | test_builder_md_enthaelt_kuerzungs_marker | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_pipeline.py | 2914 | TestBuilderMdKuerzung | test_builder_md_kein_widerspruch | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_pipeline.py | 2919 | TestBuilderMdKuerzung | test_builder_md_kuerzungs_marker_abschnitt | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_pipeline.py | 2931 | TestFehlerMarker | test_execute_commands_markiert_fehler | 1 | Kern bleibt | ruft Measurement, execute_commands |
| test_pipeline.py | 2947 | TestFehlerMarker | test_execute_commands_fehler_kategorie | 1 | Kern bleibt | ruft Measurement, execute_commands |
| test_pipeline.py | 2967 | TestBuilderCommandDeadlockWiederholung | test_builder_command_wiederholter_fehler_deadlock | 1 | Kern bleibt | ruft LLMReply, Measurement |
| test_pipeline.py | 2999 | TestBuilderCommandDeadlockWiederholung | test_builder_command_deadlock_audit | 1 | Kern bleibt | ruft LLMReply, Measurement |
| test_pipeline.py | 3040 | TestBuilderMdPfadRegel | test_builder_md_pfad_regel | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_pipeline.py | 3055 | TestGemessenerInhalt | test_builder_prompt_enthaelt_gemessenen_inhalt_nach_zieldateien | 1 | Kern bleibt | ruft run_pipeline |
| test_pipeline.py | 3077 | TestGemessenerInhalt | test_reviewer_prompt_enthaelt_gemessenen_inhalt_vor_zieldateien | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_pipeline.py | 3091 | TestGemessenerInhalt | test_ziel_snippets_ersetzt_wenn_gemessen_vollstaendig | 1 | Kern bleibt | ruft read_target_snippets |
| test_pipeline.py | 3105 | TestGemessenerInhalt | test_ziel_snippets_bleibt_wenn_nicht_gemessen | 1 | Kern bleibt | ruft read_target_snippets |
| test_pipeline.py | 3116 | TestGemessenerInhalt | test_builder_md_gemessener_inhalt_verbindlich | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_pipeline.py | 3123 | TestGemessenerInhalt | test_judge_gemessener_inhalt_verbindlich | 1 | Kern bleibt | ruft HARD_RULES_JUDGE |
| test_pipeline.py | 3128 | TestGemessenerInhalt | test_gemessene_pfade_hilfsfunktion | 1 | Kern bleibt | ruft _gemessene_pfade |
| test_pipeline.py | 3136 | TestGemessenerInhalt | test_builder_command_loop_prompt_fresh | 1 | Kern bleibt | ruft LLMReply, Measurement |
| test_pipeline.py | 3186 | TestGemessenerInhalt | test_builder_prompt_gemessener_inhalt_aktualisiert_sich | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_pipeline.py | 3195 | TestGemessenerInhalt | test_gemessene_pfade_leer | 1 | Kern bleibt | ruft _gemessene_pfade |
| test_pipeline.py | 3199 | TestGemessenerInhalt | test_gemessene_pfade_mit_read_file | 1 | Kern bleibt | ruft _gemessene_pfade |
| test_pipeline.py | 3204 | TestGemessenerInhalt | test_gemessene_pfade_ignoriert_andere_commands | 1 | Kern bleibt | ruft _gemessene_pfade |
| test_pipeline.py | 3208 | TestGemessenerInhalt | test_builder_md_prioritaet_einmal | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_pipeline.py | 3214 | TestGemessenerInhalt | test_builder_md_hinweis_2191 | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_pipeline.py | 3219 | TestGemessenerInhalt | test_workflow_dreiklang | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_pipeline.py | 3234 | TestEnsureZielGemessen | test_ensure_ziel_gemessen_liest_bei_fehlend | 1 | Kern bleibt | ruft Measurement, ensure_ziel_gemessen |
| test_pipeline.py | 3256 | TestEnsureZielGemessen | test_ensure_ziel_gemessen_ueberspringt_bereits_gemessen | 1 | Kern bleibt | ruft ensure_ziel_gemessen |
| test_pipeline.py | 3273 | TestEnsureZielGemessen | test_ensure_ziel_gemessen_kein_zielpfad | 1 | Kern bleibt | ruft ensure_ziel_gemessen |
| test_pipeline.py | 3288 | TestEnsureZielGemessen | test_pipeline_auto_in_erlaubten_quellen | 1 | Kern bleibt | ruft ERLAUBTE_QUELLEN |
| test_pipeline.py | 3291 | TestEnsureZielGemessen | test_builder_md_werkstatt_misst_auto | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_pipeline.py | 3296 | TestEnsureZielGemessen | test_workflow_werkstatt_als_messender | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_pipeline.py | 3302 | TestEnsureZielGemessen | test_ensure_ziel_gemessen_bei_vollstaendigem_read_file | 1 | Kern bleibt | ruft ensure_ziel_gemessen |
| test_pipeline.py | 3340 | TestAuditDebug | test_builder_prompt_gebaut | 1 | Kern bleibt | ruft _audit_builder_prompt |
| test_pipeline.py | 3364 | TestAuditDebug | test_builder_reply_erhalten | 1 | Kern bleibt | ruft _audit_builder_reply |
| test_pipeline.py | 3383 | TestAuditDebug | test_workflow_audit_debug | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_pipeline.py | 3398 | TestCollectMesswerteNachApply | test_collect_messwerte_liest_nach_apply | 1 | Kern bleibt | ruft collect_messwerte |
| test_pipeline.py | 3411 | TestCollectMesswerteNachApply | test_collect_messwerte_ohne_nach_apply | 1 | Kern bleibt | ruft collect_messwerte |
| test_pipeline.py | 3421 | TestCollectMesswerteNachApply | test_collect_messwerte_leer | 1 | Kern bleibt | ruft collect_messwerte |
| test_pipeline.py | 3428 | TestCollectMesswerteNachApply | test_collect_messwerte_vor_und_nach_gefuellt | 1 | Kern bleibt | ruft collect_messwerte |
| test_pipeline.py | 3449 | TestFailClosedRollback | test_rollback_bei_keinem_patch | 1 | Phase-3-Code | ruft _rollback_zieldateien |
| test_pipeline.py | 3467 | TestFailClosedRollback | test_rollback_bei_recheck_rot | 1 | Phase-3-Code | ruft _rollback_zieldateien |
| test_pipeline.py | 3494 | TestFailClosedRollback | test_rollback_bei_apply_fail_idempotent | 1 | Phase-3-Code | ruft _rollback_zieldateien |
| test_pipeline.py | 3519 | TestFailClosedRollback | test_fail_closed_ruft_rollback | 1 | Kern bleibt | ruft _fail_closed |
| test_pipeline.py | 3550 | TestCollectMesswerteFormate | test_collect_messwerte_kuerzungsformat | 1 | Kern bleibt | ruft collect_messwerte |
| test_pipeline.py | 3563 | TestCollectMesswerteFormate | test_collect_messwerte_altes_format | 1 | Kern bleibt | ruft collect_messwerte |
| test_pipeline.py | 3576 | TestCollectMesswerteFormate | test_collect_messwerte_leer | 1 | Kern bleibt | ruft collect_messwerte |
| test_pipeline.py | 3581 | TestCollectMesswerteFormate | test_collect_messwerte_py_compile_alt_format | 1 | Kern bleibt | ruft collect_messwerte |
| test_pipeline.py | 3601 | TestRecoveryZustand | test_formatiere_runden_ohne_recovery | 1 | Kern bleibt | ruft formatiere_runden |
| test_pipeline.py | 3613 | TestRecoveryZustand | test_formatiere_runden_mit_recovery | 1 | Kern bleibt | ruft formatiere_runden |
| test_pipeline.py | 3624 | TestRecoveryZustand | test_formatiere_runden_leer | 1 | Kern bleibt | ruft formatiere_runden |
| test_pipeline.py | 3628 | TestRecoveryZustand | test_recovery_hinweis_block_leer | 1 | Kern bleibt | ruft recovery_hinweis_block |
| test_pipeline.py | 3632 | TestRecoveryZustand | test_recovery_hinweis_block_normal | 1 | Kern bleibt | ruft recovery_hinweis_block |
| test_pipeline.py | 3638 | TestRecoveryZustand | test_recovery_hinweis_block_aktiv | 1 | Kern bleibt | ruft recovery_hinweis_block |
| test_pipeline.py | 3662 | TestCodeEntwurfHistorie | test_historie_leer_initial | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_pipeline.py | 3666 | TestCodeEntwurfHistorie | test_historie_zwei_setzungen | 1 | Kern bleibt | ruft record_code_entwurf |
| test_pipeline.py | 3677 | TestCodeEntwurfHistorie | test_historie_kuerzung | 1 | Kern bleibt | ruft record_code_entwurf |
| test_pipeline.py | 3684 | TestCodeEntwurfHistorie | test_historie_recovery_phase | 1 | Kern bleibt | ruft record_code_entwurf |
| test_pipeline.py | 3699 | TestMaxLlmCallsDefault | test_pipeline_default_max_llm_calls_30 | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_pipeline.py | 3715 | TestSolverBefund | test_solver_diagnose_enum_werte | 1 | Kern bleibt | ruft SolverDiagnose |
| test_pipeline.py | 3725 | TestSolverBefund | test_solver_befund_leer_defaults | 1 | Kern bleibt | ruft SolverBefund, SolverDiagnose |
| test_pipeline.py | 3734 | TestSolverBefund | test_ist_vollstaendig_gleicher_fehler | 1 | Kern bleibt | ruft SolverBefund, SolverDiagnose |
| test_pipeline.py | 3743 | TestSolverBefund | test_ist_vollstaendig_anderer_fehler | 1 | Kern bleibt | ruft SolverBefund, SolverDiagnose |
| test_pipeline.py | 3749 | TestSolverBefund | test_ist_vollstaendig_widerspruch | 1 | Kern bleibt | ruft SolverBefund, SolverDiagnose |
| test_pipeline.py | 3755 | TestSolverBefund | test_ist_vollstaendig_unklar | 1 | Kern bleibt | ruft SolverBefund, SolverDiagnose |
| test_pipeline.py | 3761 | TestSolverBefund | test_format_solver_befund_vollstaendig | 1 | Kern bleibt | ruft SolverBefund, SolverDiagnose |
| test_pipeline.py | 3772 | TestSolverBefund | test_format_solver_befund_leere_felder | 1 | Kern bleibt | ruft SolverBefund, SolverDiagnose |
| test_pipeline.py | 3781 | TestSolverBefund | test_format_solver_befund_unvollstaendig | 1 | Kern bleibt | ruft SolverBefund, SolverDiagnose |
| test_pipeline.py | 3788 | TestSolverBefund | test_runstate_solver_befunde_leer_initial | 1 | Kern bleibt | ruft RunState |
| test_pipeline.py | 5156 | TestParseNewFilePatch | test_new_file_erkannt | 1 | Kern bleibt | ruft _parse_patches |
| test_pipeline.py | 5172 | TestParseNewFilePatch | test_new_file_mit_anker_verworfen | 1 | Kern bleibt | ruft _parse_patches |
| test_pipeline.py | 5186 | TestParseNewFilePatch | test_typ_unbekannt_verworfen | 1 | Kern bleibt | ruft _parse_patches |
| test_pipeline.py | 5198 | TestParseNewFilePatch | test_patch_ohne_typ_bleibt_patch | 1 | Kern bleibt | ruft _parse_patches |
| test_pipeline.py | 5223 | TestApplyNewFile | test_new_file_angelegt | 1 | Kern bleibt | ruft apply_code_patches |
| test_pipeline.py | 5236 | TestApplyNewFile | test_new_file_existiert_fail | 1 | Kern bleibt | ruft apply_code_patches |
| test_pipeline.py | 5250 | TestApplyNewFile | test_new_file_whitelist_fail | 1 | Kern bleibt | ruft apply_code_patches |
| test_pipeline.py | 5262 | TestApplyNewFile | test_zwei_new_file_gleicher_pfad_fail | 1 | Kern bleibt | ruft apply_code_patches |
| test_pipeline.py | 5288 | TestReviewRoundAudit | test_no_go_schreibt_raw | 1 | Phase-3-Code | ruft _review_round_audit_payload |
| test_pipeline.py | 5297 | TestReviewRoundAudit | test_go_schreibt_raw | 1 | Phase-3-Code | ruft _review_round_audit_payload |
| test_pipeline.py | 5305 | TestReviewRoundAudit | test_redaction_greift | 1 | Phase-3-Code | ruft _review_round_audit_payload |
| test_pipeline.py | 5316 | TestReviewRoundAudit | test_kappung_unter_grenze | 1 | Phase-3-Code | ruft _review_round_audit_payload |
| test_pipeline.py | 5323 | TestReviewRoundAudit | test_kappung_ueber_grenze | 1 | Phase-3-Code | ruft _review_round_audit_payload |
| test_pipeline.py | 5333 | TestReviewRoundAudit | test_kappung_genau_grenze | 1 | Phase-3-Code | ruft _review_round_audit_payload |
| test_pipeline.py | 5341 | TestReviewRoundAudit | test_kein_neuer_audit_kind | 1 | Kern bleibt | ruft _AUDIT_KINDS_BEKANNT |
| test_pipeline.py | 5356 | TestReviewRoundAudit | test_state_unredacted | 1 | Kern bleibt | ruft run_pipeline |
| test_pipeline.py | 5365 | TestReviewRoundAudit | test_drei_laengen | 1 | Phase-3-Code | ruft _review_round_audit_payload |
| test_pipeline.py | 5385 | TestCommitReviewNewFileSkip | test_kein_neuer_audit_kind_ist_62 | 1 | Kern bleibt | ruft _AUDIT_KINDS_BEKANNT |
| test_pipeline.py | 5391 | TestCommitReviewNewFileSkip | test_skip_wenn_nur_new_file | 1 | Kern bleibt | ruft run_pipeline |
| test_pipeline.py | 5401 | TestCommitReviewNewFileSkip | test_fail_closed_pfad_bleibt | 1 | Kern bleibt | ruft run_pipeline |
| test_pipeline.py | 5411 | TestCommitReviewNewFileSkip | test_console_text_differenziert | 1 | Kern bleibt | ruft run_pipeline |
| test_pipeline.py | 5418 | TestCommitReviewNewFileSkip | test_anzahl_new_file_berechnet | 1 | Kern bleibt | ruft run_pipeline |
| test_pipeline.py | 5424 | TestCommitReviewNewFileSkip | test_payload_felder | 1 | Kern bleibt | ruft run_pipeline |
| test_pipeline.py | 5460 | TestPostApplyMessung | test_leere_code_patches | 1 | Phase-3-Code | ruft _post_apply_messung |
| test_pipeline.py | 5467 | TestPostApplyMessung | test_nur_patch_wird_jetzt_gelesen | 1 | Phase-3-Code | ruft _post_apply_messung |
| test_pipeline.py | 5488 | TestPostApplyMessung | test_new_file_wird_gelesen | 1 | Phase-3-Code | ruft _post_apply_messung |
| test_pipeline.py | 5504 | TestPostApplyMessung | test_read_file_nicht_im_katalog | 1 | Phase-3-Code | ruft _post_apply_messung |
| test_pipeline.py | 5521 | TestPostApplyMessung | test_mixed_new_file_und_patch | 1 | Phase-3-Code | ruft _post_apply_messung |
| test_pipeline.py | 5543 | TestPostApplyMessung | test_nur_patch_regression_new_file | 1 | Phase-3-Code | ruft _post_apply_messung |
| test_pipeline.py | 5560 | TestPostApplyMessung | test_commit_review_nutzt_neuen_kanal | 1 | Kern bleibt | ruft _build_commit_input |
| test_pipeline.py | 5573 | TestPostApplyMessung | test_aufruf_in_apply_and_recheck | 1 | Kern bleibt | ruft apply_and_recheck |
| test_pipeline.py | 5598 | TestRecoveryPromptFix | test_fallback_rohantwort_wenn_diagnose_leer | 1 | Kern bleibt | ruft RecoveryVorschlag, _bauer_recovery_prompt |
| test_pipeline.py | 5611 | TestRecoveryPromptFix | test_diagnose_vorhanden_kein_fallback | 1 | Kern bleibt | ruft RecoveryVorschlag, _bauer_recovery_prompt |
| test_pipeline.py | 5624 | TestRecoveryPromptFix | test_messblock_nach_apply_im_prompt | 1 | Kern bleibt | ruft RecoveryVorschlag, _bauer_recovery_prompt |
| test_pipeline.py | 5641 | TestRecoveryPromptFix | test_messblock_leer_zeigt_platzhalter | 1 | Kern bleibt | ruft RecoveryVorschlag, _bauer_recovery_prompt |
| test_pipeline.py | 5654 | TestRecoveryPromptFix | test_rohantwort_wird_redacted | 1 | Kern bleibt | ruft RecoveryVorschlag, _bauer_recovery_prompt |
| test_pipeline.py | 5674 | TestTruncateMitMarker | test_kurz_bleibt_unveraendert | 1 | Kern bleibt | ruft _truncate_mit_marker |
| test_pipeline.py | 5679 | TestTruncateMitMarker | test_genau_grenze_kein_marker | 1 | Kern bleibt | ruft _truncate_mit_marker |
| test_pipeline.py | 5685 | TestTruncateMitMarker | test_ueber_grenze_marker | 1 | Kern bleibt | ruft _truncate_mit_marker |
| test_pipeline.py | 5692 | TestTruncateMitMarker | test_konstante_vorhanden | 1 | Kern bleibt | ruft _REVIEWER_KONTEXT_MAX |
| test_pipeline.py | 5702 | TestFormatWhitelistBlock | test_leere_liste | 1 | Kern bleibt | ruft _format_whitelist_block |
| test_pipeline.py | 5707 | TestFormatWhitelistBlock | test_mit_pfaden | 1 | Kern bleibt | ruft _format_whitelist_block |
| test_pipeline.py | 5716 | TestFormatWhitelistBlock | test_marker_am_ende | 1 | Kern bleibt | ruft _format_whitelist_block |
| test_pipeline.py | 5720 | TestFormatWhitelistBlock | test_block_enden_mit_doppel_newline | 1 | Kern bleibt | ruft _format_whitelist_block |
| test_pipeline.py | 5724 | TestFormatWhitelistBlock | test_aufgabe_block_unveraendert | 1 | Kern bleibt | ruft aufgabe_block |
| test_pipeline.py | 5731 | TestFormatWhitelistBlock | test_reviewer_prompt_bauer_nutzt_block | 1 | Kern bleibt | ruft ask_reviewer_for_recovery, run_pipeline |
| test_pipeline.py | 5752 | TestRollenKalibrierung | test_builder_md_spec_treue | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_pipeline.py | 5758 | TestRollenKalibrierung | test_builder_md_solver_befund | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_pipeline.py | 5763 | TestRollenKalibrierung | test_judge_md_sachfaden | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_pipeline.py | 5771 | TestRollenKalibrierung | test_hard_rules_builder_b13 | 1 | Kern bleibt | ruft HARD_RULES_BUILDER |
| test_pipeline.py | 5776 | TestRollenKalibrierung | test_hard_rules_builder_b14 | 1 | Kern bleibt | ruft HARD_RULES_BUILDER |
| test_pipeline.py | 5780 | TestRollenKalibrierung | test_hard_rules_reviewer_r11 | 1 | Kern bleibt | ruft HARD_RULES_REVIEWER |
| test_pipeline.py | 5785 | TestRollenKalibrierung | test_build_system_prompt_builder | 1 | Kern bleibt | ruft build_system_prompt |
| test_pipeline.py | 5795 | TestRollenKalibrierung | test_build_system_prompt_reviewer | 1 | Kern bleibt | ruft build_system_prompt |
| test_pipeline.py | 5831 | TestNewFileMarker | test_marker_konstante | 1 | Kern bleibt | ruft _NEW_FILE_MARKER |
| test_pipeline.py | 5835 | TestNewFileMarker | test_alle_patches_new_file_true | 1 | Kern bleibt | ruft _alle_patches_sind_new_file |
| test_pipeline.py | 5840 | TestNewFileMarker | test_alle_patches_new_file_false_patch | 1 | Kern bleibt | ruft _alle_patches_sind_new_file |
| test_pipeline.py | 5845 | TestNewFileMarker | test_alle_patches_new_file_false_leer | 1 | Kern bleibt | ruft _alle_patches_sind_new_file |
| test_pipeline.py | 5852 | TestNewFileMarker | test_messwerte_prompt_marker_bei_new_file | 1 | Kern bleibt | ruft _messwerte_fuer_prompt |
| test_pipeline.py | 5858 | TestNewFileMarker | test_messwerte_prompt_keine_bei_patch | 1 | Kern bleibt | ruft _messwerte_fuer_prompt |
| test_pipeline.py | 5864 | TestNewFileMarker | test_messwerte_prompt_index_statt_volltext | 1 | Kern bleibt | ruft _messwerte_fuer_prompt |
| test_pipeline.py | 5881 | TestNewFileMarker | test_hard_rules_builder_b15 | 1 | Kern bleibt | ruft HARD_RULES_BUILDER |
| test_pipeline.py | 5885 | TestNewFileMarker | test_hard_rules_reviewer_r12 | 1 | Kern bleibt | ruft HARD_RULES_REVIEWER |
| test_pipeline.py | 5889 | TestNewFileMarker | test_build_system_prompt_builder_b15 | 1 | Kern bleibt | ruft build_system_prompt |
| test_pipeline.py | 5895 | TestNewFileMarker | test_build_system_prompt_reviewer_r12 | 1 | Kern bleibt | ruft build_system_prompt |
| test_pipeline.py | 5901 | TestNewFileMarker | test_agents_builder_md_new_file | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_pipeline.py | 5907 | TestNewFileMarker | test_agents_judge_md_pruefung | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_pipeline.py | 5921 | TestPhasenHeader | test_konstante_code_review | 1 | Kern bleibt | ruft _PHASE_HEADER_CODE_REVIEW |
| test_pipeline.py | 5926 | TestPhasenHeader | test_konstante_commit_review | 1 | Kern bleibt | ruft _PHASE_HEADER_COMMIT_REVIEW |
| test_pipeline.py | 5931 | TestPhasenHeader | test_hard_rules_reviewer_phasen_header | 1 | Kern bleibt | ruft HARD_RULES_REVIEWER |
| test_pipeline.py | 5936 | TestPhasenHeader | test_hard_rules_r13 | 1 | Kern bleibt | ruft HARD_RULES_REVIEWER |
| test_pipeline.py | 5941 | TestPhasenHeader | test_hard_rules_r14 | 1 | Kern bleibt | ruft HARD_RULES_REVIEWER |
| test_pipeline.py | 5945 | TestPhasenHeader | test_r9_eskalation | 1 | Kern bleibt | ruft HARD_RULES_REVIEWER |
| test_pipeline.py | 5956 | TestPhasenHeader | test_r11_eskalation_bezug | 1 | Kern bleibt | ruft HARD_RULES_REVIEWER |
| test_pipeline.py | 5960 | TestPhasenHeader | test_hard_rules_reviewer_verdict_konsistenz | 1 | Kern bleibt | ruft HARD_RULES_REVIEWER |
| test_pipeline.py | 5965 | TestPhasenHeader | test_hard_rules_reviewer_eskalation_vs_no_go | 1 | Kern bleibt | ruft HARD_RULES_REVIEWER |
| test_pipeline.py | 5969 | TestPhasenHeader | test_build_system_prompt_reviewer_enthaelt_r13_r14 | 1 | Kern bleibt | ruft build_system_prompt |
| test_pipeline.py | 5982 | TestUnklarBehandlung | test_reviewer_r15_im_prompt | 1 | Kern bleibt | ruft HARD_RULES_REVIEWER |
| test_pipeline.py | 5987 | TestUnklarBehandlung | test_reviewer_r15_nur_bei_new_file | 1 | Kern bleibt | ruft HARD_RULES_REVIEWER |
| test_pipeline.py | 5991 | TestUnklarBehandlung | test_reviewer_r15_widerspruchs_format | 1 | Kern bleibt | ruft HARD_RULES_REVIEWER |
| test_pipeline.py | 5996 | TestUnklarBehandlung | test_reviewer_r15_querverweis_r12 | 1 | Kern bleibt | ruft HARD_RULES_REVIEWER |
| test_pipeline.py | 6001 | TestUnklarBehandlung | test_solver_s10_im_prompt | 1 | Kern bleibt | ruft HARD_RULES_SOLVER |
| test_pipeline.py | 6006 | TestUnklarBehandlung | test_solver_s10_nur_bei_new_file | 1 | Kern bleibt | ruft HARD_RULES_SOLVER |
| test_pipeline.py | 6011 | TestUnklarBehandlung | test_parser_widerspruch_erkannt | 1 | Phase-3-Code | ruft _review_unklar_widerspruch |
| test_pipeline.py | 6015 | TestUnklarBehandlung | test_parser_widerspruch_fehlt | 1 | Phase-3-Code | ruft _review_unklar_widerspruch |
| test_pipeline.py | 6019 | TestUnklarBehandlung | test_audit_kinds_existieren | 1 | Kern bleibt | ruft _AUDIT_KINDS_BEKANNT |
| test_pipeline.py | 6025 | TestUnklarBehandlung | test_unklar_zweig_im_loop | 1 | Kern bleibt | ruft run_pipeline |
| test_pipeline.py | 6033 | TestUnklarBehandlung | test_eskalation_rc_14 | 1 | Kern bleibt | ruft run_pipeline |
| test_pipeline.py | 6047 | TestB0cUndBugs | test_classify_go_am_ende | 1 | Kern bleibt | ruft classify_verdict |
| test_pipeline.py | 6052 | TestB0cUndBugs | test_classify_no_go_am_ende | 1 | Kern bleibt | ruft classify_verdict |
| test_pipeline.py | 6056 | TestB0cUndBugs | test_classify_anfang_gewinnt | 1 | Kern bleibt | ruft classify_verdict |
| test_pipeline.py | 6061 | TestB0cUndBugs | test_classify_unklar_bleibt_unklar | 1 | Kern bleibt | ruft classify_verdict |
| test_pipeline.py | 6065 | TestB0cUndBugs | test_unklar_eskalation_mit_raw | 1 | Kern bleibt | ruft run_pipeline |
| test_pipeline.py | 6074 | TestB0cUndBugs | test_rc_14_kein_rollback | 1 | Kern bleibt | ruft run_phase |
| test_pipeline.py | 6092 | TestAskLlmTimeout | test_ask_llm_timeout_ist_tupel | 1 | Kern bleibt | ruft ask_llm |
| test_pipeline.py | 6098 | TestAskLlmTimeout | test_ask_llm_retry_prueft_deadline | 1 | Kern bleibt | ruft ask_llm |
| test_pipeline.py | 6104 | TestAskLlmTimeout | test_ask_llm_gesamt_timeout_greift | 1 | Kern bleibt | ruft ask_llm |
| test_pipeline.py | 6110 | TestAskLlmTimeout | test_runstate_max_total_llm_s_default | 1 | Kern bleibt | ruft RunState |
| test_pipeline.py | 6120 | TestAskLlmTimeout | test_audit_kind_llm_timeout_gesamt_existiert | 1 | Kern bleibt | ruft _AUDIT_KINDS_BEKANNT |
| test_pipeline.py | 6126 | TestAskLlmTimeout | test_ask_llm_timeout_audit_enthaelt_modell | 1 | Kern bleibt | ruft ask_llm |
| test_pipeline.py | 6133 | TestAskLlmTimeout | test_ask_llm_read_timeout_adaptiv | 1 | Kern bleibt | ruft ask_llm |
| test_pipeline.py | 6138 | TestAskLlmTimeout | test_ask_llm_deadline_kein_zweiter_versuch | 1 | Kern bleibt | ruft ask_llm |
| test_pipeline.py | 6149 | TestAskLlmTimeout | test_ask_llm_aufgabe_parameter | 1 | Kern bleibt | ruft ask_llm |
| test_pipeline.py | 6160 | TestCommitPhaseFixes | test_rollback_git_status_uall | 1 | Phase-3-Code | ruft _rollback_zieldateien |
| test_pipeline.py | 6165 | TestCommitPhaseFixes | test_rollback_findet_datei_in_neuem_verzeichnis | 1 | Phase-3-Code | ruft _rollback_zieldateien |
| test_pipeline.py | 6171 | TestCommitPhaseFixes | test_add_n_und_rollback_status_sauber | 1 | Phase-3-Code | ruft _rollback_zieldateien |
| test_pipeline.py | 6181 | TestCommitPhaseFixes | test_rollback_reset_head_vor_unlink | 1 | Phase-3-Code | ruft _rollback_zieldateien |
| test_pipeline.py | 6188 | TestCommitPhaseFixes | test_git_add_intent_nach_apply | 1 | Kern bleibt | ruft apply_and_recheck |
| test_pipeline.py | 6194 | TestCommitPhaseFixes | test_git_add_intent_nur_new_file | 1 | Kern bleibt | ruft apply_and_recheck |
| test_pipeline.py | 6199 | TestCommitPhaseFixes | test_git_add_intent_audit | 1 | Kern bleibt | ruft _AUDIT_KINDS_BEKANNT |
| test_pipeline.py | 6203 | TestCommitPhaseFixes | test_git_add_intent_failed_fail_closed | 1 | Kern bleibt | ruft apply_and_recheck |
| test_pipeline.py | 6212 | TestCommitPhaseFixes | test_git_add_n_mit_normalisiertem_pfad | 1 | Kern bleibt | ruft apply_and_recheck |
| test_pipeline.py | 6220 | TestCommitPhaseFixes | test_collect_messwerte_git_head_fallback | 1 | Kern bleibt | ruft collect_messwerte |
| test_pipeline.py | 6227 | TestCommitPhaseFixes | test_collect_messwerte_git_head_primaer | 1 | Kern bleibt | ruft collect_messwerte |
| test_pipeline.py | 6239 | TestB0c2MarkdownEnde | test_go_in_markdown_fett | 1 | Kern bleibt | ruft classify_verdict |
| test_pipeline.py | 6243 | TestB0c2MarkdownEnde | test_go_nicht_letzte_zeile | 1 | Kern bleibt | ruft classify_verdict |
| test_pipeline.py | 6249 | TestB0c2MarkdownEnde | test_go_mit_backtick | 1 | Kern bleibt | ruft classify_verdict |
| test_pipeline.py | 6253 | TestB0c2MarkdownEnde | test_no_go_markdown | 1 | Kern bleibt | ruft classify_verdict |
| test_pipeline.py | 6257 | TestB0c2MarkdownEnde | test_go_in_satz_zaehlt_nicht | 1 | Kern bleibt | ruft classify_verdict |
| test_pipeline.py | 6261 | TestB0c2MarkdownEnde | test_go_nach_sechs_zeilen_nicht | 1 | Kern bleibt | ruft classify_verdict |
| test_pipeline.py | 6274 | TestCommitPaketScope | test_build_commit_paket_zieldateien_aus_patches | 1 | Kern bleibt | ruft build_commit_paket |
| test_pipeline.py | 6280 | TestCommitPaketScope | test_build_commit_paket_zieldateien_leer | 1 | Kern bleibt | ruft build_commit_paket |
| test_pipeline.py | 6285 | TestCommitPaketScope | test_build_commit_paket_prompt_scope_hinweis | 1 | Kern bleibt | ruft build_commit_paket |
| test_pipeline.py | 6290 | TestCommitPaketScope | test_d3_ueberschreibt_halluzination | 1 | Kern bleibt | ruft run_pipeline |
| test_pipeline.py | 6297 | TestCommitPaketScope | test_d3_b2_fall_leere_liste | 1 | Kern bleibt | ruft run_pipeline |
| test_pipeline.py | 6305 | TestCommitPaketScope | test_d3_nicht_im_nicht_phasen_modus | 1 | Kern bleibt | ruft run_pipeline |
| test_pipeline.py | 6314 | TestCommitPaketScope | test_d3_vor_phase_commit_pakete_append | 1 | Kern bleibt | ruft run_pipeline |
| test_pipeline.py | 6322 | TestCommitPaketScope | test_audit_kind_existiert | 1 | Kern bleibt | ruft _AUDIT_KINDS_BEKANNT |
| test_pipeline.py | 6326 | TestCommitPaketScope | test_d3_ziel_pfade_aus_code_patches | 1 | Kern bleibt | ruft run_pipeline |
| test_pipeline.py | 6341 | TestEDiffNameOnly | test_commit_input_enthaelt_diff_name_only | 1 | Kern bleibt | ruft _build_commit_input |
| test_pipeline.py | 6346 | TestEDiffNameOnly | test_commit_input_ruft_git_diff_name_only | 1 | Kern bleibt | ruft run_pipeline |
| test_pipeline.py | 6351 | TestEDiffNameOnly | test_commit_input_diff_vor_code_patches | 1 | Kern bleibt | ruft _build_commit_input |
| test_pipeline.py | 6358 | TestEDiffNameOnly | test_diff_name_only_leer_zeigt_keine | 1 | Kern bleibt | ruft run_pipeline |
| test_pipeline.py | 6364 | TestEDiffNameOnly | test_diff_name_only_fehler_fail_closed | 1 | Kern bleibt | ruft run_pipeline |
| test_pipeline.py | 6373 | TestEDiffNameOnly | test_r16_entfernt_im_reviewer_prompt | 1 | Kern bleibt | ruft HARD_RULES_REVIEWER |
| test_pipeline.py | 6377 | TestEDiffNameOnly | test_r16_teilmenge_bei_phasen_modus | 1 | Phase-3-Code | ruft _check_commit_scope |
| test_pipeline.py | 6384 | TestEDiffNameOnly | test_audit_kinds_commit_review_diff | 1 | Kern bleibt | ruft _AUDIT_KINDS_BEKANNT |
| test_pipeline.py | 6396 | TestW2BuilderRules | test_b4_zwei_klassen | 1 | Kern bleibt | ruft HARD_RULES_BUILDER |
| test_pipeline.py | 6401 | TestW2BuilderRules | test_b13b_im_prompt | 1 | Kern bleibt | ruft HARD_RULES_BUILDER |
| test_pipeline.py | 6405 | TestW2BuilderRules | test_b13b_datei_existenz_wortlaut | 1 | Kern bleibt | ruft HARD_RULES_BUILDER |
| test_pipeline.py | 6411 | TestW2BuilderRules | test_b13b_frage_reviewer_format | 1 | Kern bleibt | ruft HARD_RULES_BUILDER |
| test_pipeline.py | 6415 | TestW2BuilderRules | test_b13b_nicht_fuer_signaturen | 1 | Kern bleibt | ruft HARD_RULES_BUILDER |
| test_pipeline.py | 6426 | TestW3PlannerMessung | test_p19_im_planner_prompt | 1 | Kern bleibt | ruft HARD_RULES_PLANNER_STUFE2 |
| test_pipeline.py | 6429 | TestW3PlannerMessung | test_p19_nennt_read_file | 1 | Kern bleibt | ruft HARD_RULES_PLANNER_STUFE2 |
| test_pipeline.py | 6436 | TestW3PlannerMessung | test_p19_nicht_in_stufe1 | 1 | Kern bleibt | ruft HARD_RULES_PLANNER_STUFE1 |
| test_pipeline.py | 6439 | TestW3PlannerMessung | test_planner_command_loop_im_code | 1 | Phase-3-Code | ruft _planner_lauf |
| test_pipeline.py | 6446 | TestW3PlannerMessung | test_planner_command_loop_max_runden | 1 | Phase-3-Code | ruft _planner_lauf |
| test_pipeline.py | 6452 | TestW3PlannerMessung | test_planner_user_content_hat_messwerte | 1 | Phase-3-Code | ruft _planner_user_content |
| test_pipeline.py | 6457 | TestW3PlannerMessung | test_planner_in_erlaubte_quellen | 1 | Kern bleibt | ruft ERLAUBTE_QUELLEN |
| test_pipeline.py | 6460 | TestW3PlannerMessung | test_p9strich_verweist_auf_p19 | 1 | Kern bleibt | ruft HARD_RULES_PLANNER_STUFE2 |
| test_pipeline.py | 6464 | TestW3PlannerMessung | test_p18_hat_sechste_punkt | 1 | Kern bleibt | ruft HARD_RULES_PLANNER_STUFE2 |
| test_pipeline.py | 6472 | TestW3PlannerMessung | test_planner_lauf_signatur_max_runden | 1 | Phase-3-Code | ruft _planner_lauf |
| test_pipeline.py | 6477 | TestW3PlannerMessung | test_audit_kind_planner_command_max_runden | 1 | Kern bleibt | ruft _AUDIT_KINDS_BEKANNT |
| test_pipeline.py | 6481 | TestW3PlannerMessung | test_planner_user_content_state_optional | 1 | Phase-3-Code | ruft _planner_user_content |
| test_pipeline.py | 6493 | TestW6a | test_diagnose_regex_ignoriert_stdout | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_pipeline.py | 6519 | TestW6a | test_read_file_konstante_existiert | 1 | Kern bleibt | ruft MAX_PROTOKOLL_PER_COMMAND_READ_FILE |
| test_pipeline.py | 6522 | TestW6a | test_total_konstante_150k | 1 | Kern bleibt | ruft MAX_PROTOKOLL_TOTAL |
| test_pipeline.py | 6525 | TestW6a | test_trim_output_mit_grenze | 1 | Kern bleibt | ruft trim_output |
| test_pipeline.py | 6530 | TestW6a | test_read_file_grenze_20k | 1 | Kern bleibt | ruft execute_commands |
| test_pipeline.py | 6542 | TestW6b | test_anker_zeilenbereich_findet_an_zeile | 1 | Kern bleibt | ruft _anker_zeilenbereich |
| test_pipeline.py | 6557 | TestW6b | test_anker_zeilenbereich_kein_anker | 1 | Kern bleibt | ruft _anker_zeilenbereich |
| test_pipeline.py | 6563 | TestW6b | test_read_file_zeilenbereich_klassisch | 1 | Kern bleibt | ruft Measurement, run_measurement_mit_argv |
| test_pipeline.py | 6574 | TestW6b | test_read_file_zeilenbereich_sed | 1 | Kern bleibt | ruft Measurement, run_measurement_mit_argv |
| test_pipeline.py | 6586 | TestW6b | test_ensure_ziel_gemessen_signatur_aufgabe | 1 | Kern bleibt | ruft ensure_ziel_gemessen |
| test_pipeline.py | 6591 | TestW6b | test_ensure_ziel_gemessen_nutzt_anker | 1 | Kern bleibt | ruft ensure_ziel_gemessen |
| test_pipeline.py | 6597 | TestW6b | test_parse_commands_read_file_zeilenbereich | 1 | Kern bleibt | ruft parse_commands |
| test_pipeline.py | 6604 | TestW6b | test_anker_zeilenbereich_clamp_start | 1 | Kern bleibt | ruft _anker_zeilenbereich |
| test_pipeline.py | 6631 | TestW8 | test_git_status_gefiltert_im_code | 1 | Kern bleibt | ruft build_commit_paket |
| test_pipeline.py | 6637 | TestW8 | test_git_status_filter_logik | 1 | Kern bleibt | ruft build_commit_paket |
| test_pipeline.py | 6644 | TestW8 | test_message_sanity_check_im_code | 1 | Kern bleibt | ruft run_pipeline |
| test_pipeline.py | 6652 | TestW8 | test_message_regex_endungen | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_pipeline.py | 6667 | TestW8 | test_commit_paket_gebaut_audit_kind | 1 | Kern bleibt | ruft _AUDIT_KINDS_BEKANNT |
| test_pipeline.py | 6671 | TestW8 | test_commit_message_diskrepanz_audit_kind | 1 | Kern bleibt | ruft _AUDIT_KINDS_BEKANNT |
| test_pipeline.py | 6675 | TestW8 | test_r16_entfernt | 1 | Kern bleibt | ruft HARD_RULES_REVIEWER |
| test_pipeline.py | 6686 | TestW8b | test_prompt_verbietet_fremde_pfade | 1 | Kern bleibt | ruft build_commit_paket |
| test_pipeline.py | 6692 | TestW8b | test_prompt_positiv_format | 1 | Kern bleibt | ruft build_commit_paket |
| test_pipeline.py | 6704 | TestW9a | test_commit_review_prompt_message_marker | 1 | Kern bleibt | ruft _build_commit_input |
| test_pipeline.py | 6710 | TestW9a | test_konsistenz_mit_bestehenden_markern | 1 | Phase-3-Code | ruft _planner_user_content |
| test_pipeline.py | 6722 | TestW10 | test_aenderung_block_extraktion | 1 | Kern bleibt | ruft _extrahiere_aenderung_pfade |
| test_pipeline.py | 6735 | TestW10 | test_referenzen_ignoriert | 1 | Kern bleibt | ruft _extrahiere_aenderung_pfade |
| test_pipeline.py | 6750 | TestW10 | test_mehrere_aenderung_pfade | 1 | Kern bleibt | ruft _extrahiere_aenderung_pfade |
| test_pipeline.py | 6761 | TestW10 | test_kein_aenderung_block_fail_closed | 1 | Kern bleibt | ruft _extrahiere_aenderung_pfade |
| test_pipeline.py | 6766 | TestW10 | test_aenderung_ohne_bullets_fail_closed | 1 | Kern bleibt | ruft _extrahiere_aenderung_pfade |
| test_pipeline.py | 6774 | TestW10 | test_umlaut_variante_erkannt | 1 | Kern bleibt | ruft _extrahiere_aenderung_pfade |
| test_pipeline.py | 6787 | TestW10 | test_pfad_normalisierung | 1 | Kern bleibt | ruft _normalisiere_pfad |
| test_pipeline.py | 6794 | TestW10 | test_audit_kind_commit_message_diskrepanz_existiert | 1 | Kern bleibt | ruft _AUDIT_KINDS_BEKANNT |
| test_pipeline.py | 6804 | TestW10b | test_aenderung_block_fliesstext_fallback | 1 | Kern bleibt | ruft _extrahiere_aenderung_pfade |
| test_pipeline.py | 6817 | TestW10b | test_aenderung_block_fliesstext_mit_referenz | 1 | Kern bleibt | ruft _extrahiere_aenderung_pfade |
| test_pipeline.py | 6840 | TestW11 | test_r17_im_prompt | 1 | Kern bleibt | ruft HARD_RULES_REVIEWER |
| test_pipeline.py | 6845 | TestW11 | test_r17_nur_phasen_modus | 1 | Kern bleibt | ruft HARD_RULES_REVIEWER |
| test_pipeline.py | 6850 | TestW11 | test_r17_new_file_ohne_registrierung_ok | 1 | Kern bleibt | ruft HARD_RULES_REVIEWER |
| test_pipeline.py | 6855 | TestW11 | test_r17_verweist_auf_r11_r16 | 1 | Kern bleibt | ruft HARD_RULES_REVIEWER |
| test_pipeline.py | 6860 | TestW11 | test_r17_ausnahme_auftrag_nennt_pfad | 1 | Kern bleibt | ruft HARD_RULES_REVIEWER |
| test_pipeline.py | 6866 | TestW11 | test_r17_hinweis_statt_no_go | 1 | Kern bleibt | ruft HARD_RULES_REVIEWER |
| test_pipeline.py | 6871 | TestW11 | test_commit_review_prompt_unterblock_kontext | 1 | Kern bleibt | ruft run_pipeline |
| test_pipeline.py | 6878 | TestW11 | test_commit_review_prompt_unterblock_nur_phasen_modus | 1 | Kern bleibt | ruft run_pipeline |
| test_pipeline.py | 6886 | TestW11 | test_r16_nicht_mehr_im_prompt | 1 | Kern bleibt | ruft HARD_RULES_REVIEWER |
| test_pipeline.py | 6901 | TestW10c | test_app_py_ohne_pfad_ignoriert | 1 | Kern bleibt | ruft _extrahiere_aenderung_pfade |
| test_pipeline.py | 6911 | TestW10c | test_app_py_mit_pfad_gezaehlt | 1 | Kern bleibt | ruft _extrahiere_aenderung_pfade |
| test_pipeline.py | 6930 | TestA1Final | test_check_commit_scope_vor_reviewer | 1 | Kern bleibt | ruft run_pipeline |
| test_pipeline.py | 6938 | TestA1Final | test_commit_scope_fail_closed | 1 | Phase-3-Code | ruft _check_commit_scope |
| test_pipeline.py | 6944 | TestA1Final | test_r5_nicht_mehr_im_prompt | 1 | Kern bleibt | ruft HARD_RULES_REVIEWER |
| test_pipeline.py | 6949 | TestA1Final | test_r16_nicht_mehr_im_prompt | 1 | Kern bleibt | ruft HARD_RULES_REVIEWER |
| test_pipeline.py | 6954 | TestA1Final | test_hard_rules_reviewer_anzahl_16 | 1 | Kern bleibt | ruft HARD_RULES_REVIEWER |
| test_pipeline.py | 6961 | TestA1Final | test_r12_r15_schon_im_prompt | 1 | Kern bleibt | ruft HARD_RULES_REVIEWER |
| test_pipeline.py | 6974 | TestW13a | test_anker_zeilenbereich_mit_literal_n | 1 | Kern bleibt | ruft _anker_zeilenbereich |
| test_pipeline.py | 7025 | TestW13a | test_anker_zeilenbereich_mit_echtem_newline | 1 | Kern bleibt | ruft _anker_zeilenbereich |
| test_pipeline.py | 7049 | TestW13b | test_ersatz_fehler_nicht_mehr_geprueft | 1 | Kern bleibt | ruft builder_reply_mit_command_loop |
| test_pipeline.py | 7067 | TestW11b | test_check_commit_scope_liest_git_status | 1 | Phase-3-Code | ruft _check_commit_scope |
| test_pipeline.py | 7073 | TestW11b | test_check_commit_scope_untracked_akzeptiert | 1 | Phase-3-Code | ruft _check_commit_scope |
| test_pipeline.py | 7089 | TestW25Klassifizierung | test_klassifiziere_gruen | 1 | Phase-3-Code | ruft _klassifiziere_pytest |
| test_pipeline.py | 7098 | TestW25Klassifizierung | test_klassifiziere_test_failures | 1 | Phase-3-Code | ruft _klassifiziere_pytest |
| test_pipeline.py | 7115 | TestW25Klassifizierung | test_klassifiziere_failed_ids_limit | 1 | Phase-3-Code | ruft _klassifiziere_pytest |
| test_pipeline.py | 7126 | TestW25Klassifizierung | test_klassifiziere_collection_error | 1 | Phase-3-Code | ruft _klassifiziere_pytest |
| test_pipeline.py | 7133 | TestW25Klassifizierung | test_klassifiziere_no_tests | 1 | Phase-3-Code | ruft _klassifiziere_pytest |
| test_pipeline.py | 7138 | TestW25Klassifizierung | test_klassifiziere_unknown | 1 | Phase-3-Code | ruft _klassifiziere_pytest |
| test_pipeline.py | 7143 | TestW25Klassifizierung | test_klassifiziere_timeout | 1 | Phase-3-Code | ruft _klassifiziere_pytest |
| test_pipeline.py | 7155 | TestW25ZielPfade | test_ziel_test_pfade_filter | 1 | Kern bleibt | ruft _ziel_test_pfade |
| test_pipeline.py | 7172 | TestW25ZielPfade | test_ziel_test_pfade_leer | 1 | Kern bleibt | ruft _ziel_test_pfade |
| test_pipeline.py | 7180 | TestW25ZielPfade | test_ziel_test_pfade_nicht_dict | 1 | Kern bleibt | ruft _ziel_test_pfade |
| test_pipeline.py | 7196 | TestW25BasisGate | test_basis_gate_pytest_ziel_rot | 1 | Phase-3-Code | ruft _basis_gate_pytest_ziel |
| test_pipeline.py | 7212 | TestW25BasisGate | test_basis_gate_pytest_ziel_gruen | 1 | Phase-3-Code | ruft _basis_gate_pytest_ziel |
| test_pipeline.py | 7227 | TestW25BasisGate | test_basis_gate_pytest_ziel_timeout | 1 | Phase-3-Code | ruft _basis_gate_pytest_ziel |
| test_pipeline.py | 7238 | TestW25BasisGate | test_basis_gate_pytest_suite_gruen | 1 | Phase-3-Code | ruft _basis_gate_pytest_suite |
| test_pipeline.py | 7252 | TestW25BasisGate | test_basis_gate_pytest_suite_rot | 1 | Phase-3-Code | ruft _basis_gate_pytest_suite |
| test_pipeline.py | 7283 | TestW25FehlerNachApply | test_none_nicht_reparierbar | 1 | Phase-3-Code | ruft _fehler_nach_apply |
| test_pipeline.py | 7286 | TestW25FehlerNachApply | test_leer_nicht_reparierbar | 1 | Phase-3-Code | ruft _fehler_nach_apply |
| test_pipeline.py | 7290 | TestW25FehlerNachApply | test_nur_diagnose_reparierbar | 1 | Phase-3-Code | ruft _fehler_nach_apply |
| test_pipeline.py | 7294 | TestW25FehlerNachApply | test_nur_plan_reparierbar | 1 | Phase-3-Code | ruft _fehler_nach_apply |
| test_pipeline.py | 7299 | TestW25FehlerNachApply | test_marker_frueherer_unterblock | 1 | Phase-3-Code | ruft _fehler_nach_apply |
| test_pipeline.py | 7303 | TestW25FehlerNachApply | test_marker_case_insensitive | 1 | Phase-3-Code | ruft _fehler_nach_apply |
| test_pipeline.py | 7308 | TestW25FehlerNachApply | test_marker_bereits_done | 1 | Phase-3-Code | ruft _fehler_nach_apply |
| test_pipeline.py | 7313 | TestW25FehlerNachApply | test_ohne_marker_reparierbar | 1 | Phase-3-Code | ruft _fehler_nach_apply |
| test_pipeline.py | 7338 | TestW25SammelCommitRecovery | test_sammel_commit_recovery_reparierbar | 1 | Phase-3-Code | ruft _fehler_nach_apply, _klassifiziere_pytest |
| test_pipeline.py | 7400 | TestW25SammelCommitRecovery | test_sammel_commit_recovery_nicht_reparierbar | 1 | Phase-3-Code | ruft _fehler_nach_apply |
| test_pipeline.py | 7421 | TestWEGXP19PlanChecks | test_plan_ist_messungsbasiert_ok_anker | 1 | Phase-3-Code | ruft _plan_ist_messungsbasiert |
| test_pipeline.py | 7432 | TestWEGXP19PlanChecks | test_plan_ist_messungsbasiert_ok_neu | 1 | Phase-3-Code | ruft _plan_ist_messungsbasiert |
| test_pipeline.py | 7443 | TestWEGXP19PlanChecks | test_plan_ist_messungsbasiert_ohne_anker | 1 | Phase-3-Code | ruft _plan_ist_messungsbasiert |
| test_pipeline.py | 7454 | TestWEGXP19PlanChecks | test_plan_ist_messungsbasiert_case_insensitive | 1 | Phase-3-Code | ruft _plan_ist_messungsbasiert |
| test_pipeline.py | 7465 | TestWEGXP19PlanChecks | test_plan_ist_portionierbar_ok | 1 | Phase-3-Code | ruft _plan_ist_portionierbar |
| test_pipeline.py | 7474 | TestWEGXP19PlanChecks | test_plan_ist_portionierbar_zu_gross | 1 | Phase-3-Code | ruft _plan_ist_portionierbar |
| test_pipeline.py | 7485 | TestWEGXP19PlanChecks | test_plan_ist_portionierbar_max_7 | 1 | Phase-3-Code | ruft _plan_ist_portionierbar |
| test_pipeline.py | 7505 | TestWEGXP19Anzeige | test_anzeige_marker_im_source | 1 | Phase-3-Code | ruft _phase_main_pfad |
| test_pipeline.py | 7517 | TestWEGXP19Anzeige | test_fail_closed_marker_im_source | 1 | Phase-3-Code | ruft _phase_main_pfad |
| test_pipeline.py | 7526 | TestWEGXP19Anzeige | test_fail_closed_konsole_hinweis | 1 | Phase-3-Code | ruft _phase_main_pfad |
| test_pipeline.py | 7544 | TestWEGXP19bP17Format | test_p17_format_neu_ok | 1 | Phase-3-Code | ruft _plan_ist_messungsbasiert |
| test_pipeline.py | 7554 | TestWEGXP19bP17Format | test_p17_format_patch_ok | 1 | Phase-3-Code | ruft _plan_ist_messungsbasiert |
| test_pipeline.py | 7563 | TestWEGXP19bP17Format | test_p17_aktion_ohne_space | 1 | Phase-3-Code | ruft _plan_ist_messungsbasiert |
| test_pipeline.py | 7573 | TestWEGXP19bP17Format | test_p17_ohne_signatur_fail | 1 | Phase-3-Code | ruft _plan_ist_messungsbasiert |
| test_pipeline.py | 7584 | TestWEGXP19bP17Format | test_p17_patch_ohne_anker_fail | 1 | Phase-3-Code | ruft _plan_ist_messungsbasiert |
| test_pipeline.py | 7594 | TestWEGXP19bP17Format | test_test_ohne_datei_fail | 1 | Phase-3-Code | ruft _plan_ist_messungsbasiert |
| test_pipeline.py | 7603 | TestWEGXP19bP17Format | test_praefix_backward_ok | 1 | Phase-3-Code | ruft _plan_ist_messungsbasiert, _plan_ist_messungsbasiert_praefix_zaehler |
| test_pipeline.py | 7611 | TestWEGXP19bP17Format | test_praefix_zaehler_null_bei_p17 | 1 | Phase-3-Code | ruft _plan_ist_messungsbasiert, _plan_ist_messungsbasiert_praefix_zaehler |
| test_pipeline.py | 7635 | TestSANAProjektkonfig | test_agent_docs_keine_grossen_dateien | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_pipeline.py | 7664 | TestSANAProjektkonfig | test_kein_decisions_oder_security_log_in_agent_docs | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_pipeline.py | 7682 | TestW23CommitReviewPrompt | test_commit_review_prompt_nach_apply_verbindlich | 1 | Kern bleibt | ruft _build_commit_input |
| test_pipeline.py | 7715 | TestW23CommitReviewPrompt | test_commit_review_prompt_bei_apply_leer | 1 | Kern bleibt | ruft _build_commit_input |
| test_pipeline.py | 7734 | TestW23CommitReviewPrompt | test_format_basis_gate_test_results | 1 | Kern bleibt | ruft _format_basis_gate_test_results |
| test_pipeline.py | 7766 | TestW24aIdempotenz | test_patch_bereits_angewendet_skip | 1 | Kern bleibt | ruft apply_code_patches |
| test_pipeline.py | 7787 | TestW24aIdempotenz | test_patch_ambig_fail_closed | 1 | Kern bleibt | ruft apply_code_patches |
| test_pipeline.py | 7807 | TestW24aIdempotenz | test_patch_normal_apply | 1 | Kern bleibt | ruft apply_code_patches |
| test_pipeline.py | 7826 | TestW24aIdempotenz | test_patch_anker_fehlt_fail_closed | 1 | Kern bleibt | ruft apply_code_patches |
| test_pipeline.py | 7849 | TestW25Skills | test_available_skills_block_enthaelt_12 | 1 | Kern bleibt | ruft _available_skills_block |
| test_pipeline.py | 7861 | TestW25Skills | test_geladene_skills_injiziert | 1 | Kern bleibt | ruft _geladene_skills_block, _lade_skill_in_state |
| test_pipeline.py | 7871 | TestW25Skills | test_multiple_skills_injiziert | 1 | Kern bleibt | ruft _geladene_skills_block, _lade_skill_in_state |
| test_pipeline.py | 7890 | TestW26PlanMd | test_schreibe_plan_legt_zwei_dateien_an | 1 | Kern bleibt | ruft _plan_audit_pfad, _plan_pfad |
| test_pipeline.py | 7908 | TestW26PlanMd | test_lese_plan_liefert_inhalt | 1 | Kern bleibt | ruft _lese_plan, _schreibe_plan |
| test_pipeline.py | 7918 | TestW26PlanMd | test_lese_plan_leer_wenn_nicht_vorhanden | 1 | Kern bleibt | ruft _lese_plan |
| test_pipeline.py | 7929 | TestW27Contracts | test_contract_pfad | 1 | Kern bleibt | ruft _contract_pfad |
| test_pipeline.py | 7937 | TestW27Contracts | test_schreibe_contract_und_lese | 1 | Kern bleibt | ruft _contract_pfad, _lese_contract |
| test_pipeline.py | 7958 | TestW27Contracts | test_lese_contract_leer | 1 | Kern bleibt | ruft _lese_contract |
| test_pipeline.py | 7968 | TestW28bReviewLoopJudge | test_judge_prompt_hat_contract | 1 | Kern bleibt | ruft _build_judge_prompt |
| test_pipeline.py | 7975 | TestW28bReviewLoopJudge | test_judge_input_hat_contract | 1 | Kern bleibt | ruft _build_judge_input, _schreibe_contract |
| test_pipeline.py | 7996 | TestW28bReviewLoopJudge | test_max_review_rounds_ist_2 | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_pipeline.py | 8004 | TestW28bReviewLoopJudge | test_judge_model_ist_konfiguriert | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_pipeline.py | 8014 | TestW28cAntwortLimit | test_ask_llm_hat_max_tokens | 1 | Kern bleibt | ruft ask_llm |
| test_pipeline.py | 8021 | TestW28cAntwortLimit | test_runstate_max_tokens_felder | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_pipeline.py | 8031 | TestW28cAntwortLimit | test_security_ai_yaml_max_tokens | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_pipeline.py | 8042 | TestW28cAntwortLimit | test_hard_rules_antwort_format | 1 | Kern bleibt | ruft HARD_RULES_BUILDER, HARD_RULES_JUDGE |
| test_pipeline.py | 8067 | TestW29Deterministisch | test_d1_offene_unterbloecke_fail | 1 | Phase-3-Code | ruft _phase_deterministisch_pruefen, _phase_gesamt_review |
| test_pipeline.py | 8087 | TestW29Deterministisch | test_d2_duplikate_im_paket_fail | 1 | Phase-3-Code | ruft _phase_deterministisch_pruefen, _phase_gesamt_review |
| test_pipeline.py | 8109 | TestW29Deterministisch | test_d2_duplikate_ueber_pakete_ok | 1 | Phase-3-Code | ruft _phase_gesamt_review |
| test_pipeline.py | 8125 | TestW29Deterministisch | test_d3_whitelist_fail | 1 | Phase-3-Code | ruft _phase_deterministisch_pruefen, _phase_gesamt_review |
| test_pipeline.py | 8143 | TestW29Deterministisch | test_d4_waisen_datei_fail | 1 | Phase-3-Code | ruft _phase_deterministisch_pruefen, _phase_gesamt_review |
| test_pipeline.py | 8170 | TestW29Deterministisch | test_d5_tote_datei_fail | 1 | Phase-3-Code | ruft _phase_deterministisch_pruefen, _phase_gesamt_review |
| test_pipeline.py | 8190 | TestW29Deterministisch | test_gruen_alle_ok | 1 | Phase-3-Code | ruft _phase_deterministisch_pruefen, _phase_gesamt_review |
| test_pipeline.py | 8211 | TestW29JudgePrompt | test_build_phase_judge_input_enthaelt_plan | 1 | Kern bleibt | ruft _build_phase_judge_input, _plan_pfad |
| test_pipeline.py | 8237 | TestW29JudgePrompt | test_build_phase_judge_input_enthaelt_diff | 1 | Kern bleibt | ruft _build_phase_judge_input |
| test_pipeline.py | 8258 | TestW29JudgePrompt | test_build_phase_judge_input_enthaelt_tests | 1 | Kern bleibt | ruft _build_phase_judge_input |
| test_pipeline.py | 8293 | TestW29JudgeVerdict | test_judge_go | 1 | Phase-3-Code | ruft _phase_judge_review |
| test_pipeline.py | 8308 | TestW29JudgeVerdict | test_judge_no_go | 1 | Phase-3-Code | ruft _phase_judge_review |
| test_pipeline.py | 8323 | TestW29JudgeVerdict | test_judge_llm_fehler | 1 | Phase-3-Code | ruft _phase_judge_review |
| test_pipeline.py | 8343 | TestW29JudgeVerdict | test_repair_go | 1 | Phase-3-Code | ruft _phase_judge_repair_runde |
| test_pipeline.py | 8358 | TestW29JudgeVerdict | test_repair_no_go | 1 | Phase-3-Code | ruft _phase_judge_repair_runde |
| test_pipeline.py | 8384 | TestW30LoopCap | test_review_loop_cap_erreicht | 1 | Phase-3-Code | ruft _loop_cap_audit |
| test_pipeline.py | 8401 | TestW30LoopCap | test_korrektur_loop_cap_erreicht | 1 | Phase-3-Code | ruft _loop_cap_audit |
| test_pipeline.py | 8415 | TestW30LoopCap | test_solver_loop_cap_erreicht | 1 | Phase-3-Code | ruft _loop_cap_audit |
| test_pipeline.py | 8429 | TestW30LoopCap | test_cap_nicht_erreicht_bei_gleichheit | 1 | Phase-3-Code | ruft _loop_cap_audit |
| test_pipeline.py | 8442 | TestW30LoopCap | test_config_liest_max_review_aus_yaml | 1 | Kern bleibt | ruft run_pipeline |
| test_pipeline.py | 8451 | TestW30LoopCap | test_yaml_code_defaults_gleich | 1 | Kern bleibt | ruft run_pipeline |
| test_pipeline.py | 8462 | TestW30LoopCap | test_loop_cap_erreicht_audit_event | 1 | Kern bleibt | ruft _AUDIT_KINDS_BEKANNT |
| test_pipeline.py | 8468 | TestW30LoopCap | test_korrektur_runde_unterschied_dokumentiert | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_pipeline.py | 8485 | TestW30LoopCap | test_w30_fix_planner_loop_cap_audit | 1 | Phase-3-Code | ruft _planner_lauf |
| test_pipeline.py | 8509 | TestW30LoopCap | test_w30_fix_builder_loop_cap_audit | 1 | Kern bleibt | ruft builder_reply_mit_command_loop |
| test_pipeline.py | 8563 | TestW30LoopCap | test_w30_fix_post_apply_loop_cap_audit | 1 | Phase-3-Code | ruft _post_apply_korrektur_loop |
| test_pipeline.py | 8591 | TestW32ContractImLoop | test_schreibe_contract_im_loop | 1 | Kern bleibt | ruft run_phase |
| test_pipeline.py | 8609 | TestW32ContractImLoop | test_contract_existiert_nach_loop | 1 | Phase-3-Code | ruft _phase_plan_speichern |
| test_pipeline.py | 8719 | TestW33bApplyVorReview | test_phase_apply_vor_review_reihenfolge | 1 | Kern bleibt | ruft run_pipeline |
| test_pipeline.py | 8732 | TestW33bApplyVorReview | test_nicht_phasen_modus_unveraendert | 1 | Kern bleibt | ruft run_pipeline |
| test_pipeline.py | 8741 | TestW33bApplyVorReview | test_phase_apply_vor_review_fehlschlag | 1 | Phase-3-Code | ruft _phase_apply_vor_review |
| test_pipeline.py | 8756 | TestW33bApplyVorReview | test_phase_apply_vor_review_mess_nach | 1 | Phase-3-Code | ruft _phase_apply_vor_review |
| test_pipeline.py | 8770 | TestW33bApplyVorReview | test_phase_apply_vor_review_veraltet_flag | 1 | Phase-3-Code | ruft _phase_apply_vor_review |
| test_pipeline.py | 8783 | TestW33bApplyVorReview | test_phase_apply_vor_review_mess_nach_patch | 1 | Phase-3-Code | ruft _phase_apply_vor_review |
| test_pipeline.py | 8802 | TestW33bApplyVorReview | test_phase_apply_vor_review_basis_gate_ziel | 1 | Phase-3-Code | ruft _phase_apply_vor_review |
| test_pipeline.py | 8838 | TestW33bApplyVorReview | test_phase_apply_vor_review_basis_gate_rot | 1 | Phase-3-Code | ruft _phase_apply_vor_review |
| test_pipeline.py | 8863 | TestW33bApplyVorReview | test_post_apply_messung_guard_warnung | 1 | Phase-3-Code | ruft _phase_apply_vor_review |
| test_pipeline.py | 8923 | TestW34bWerkstattAusnahme | test_basis_gate_ignoriert_werkstatt_pfad | 1 | Phase-3-Code | ruft _phasen_basis_gate_ok |
| test_pipeline.py | 8947 | TestW34bWerkstattAusnahme | test_basis_gate_fail_closed_bei_fremdem_untracked | 1 | Phase-3-Code | ruft _phasen_basis_gate_ok |
| test_pipeline.py | 8968 | TestW34bWerkstattAusnahme | test_basis_gate_werkstatt_und_fremd_gemischt | 1 | Phase-3-Code | ruft _phasen_basis_gate_ok |
| test_pipeline.py | 9023 | TestW35a1LetzterBefund | test_no_go_schreibt_letzter_befund | 1 | Phase-3-Code | ruft _phase_plan_laden, _phase_yaml_status_update |
| test_pipeline.py | 9037 | TestW35a1LetzterBefund | test_done_loescht_letzter_befund | 1 | Phase-3-Code | ruft _phase_plan_laden, _phase_yaml_status_update |
| test_pipeline.py | 9080 | TestW35a2PlannerResume | test_resume_bei_no_go | 1 | Phase-3-Code | ruft _phase_plan_speichern, _phase_planner_resume |
| test_pipeline.py | 9131 | TestW35a2PlannerResume | test_kein_resume_bei_alle_done | 1 | Phase-3-Code | ruft _phase_planner_resume |
| test_pipeline.py | 9146 | TestW35a2PlannerResume | test_cap_erreicht | 1 | Phase-3-Code | ruft _phase_planner_resume |
| test_pipeline.py | 9167 | TestW35a2PlannerResume | test_solver_z2a_nicht_gerufen | 1 | Phase-3-Code | ruft _phase_planner_resume |
| test_pipeline.py | 9188 | TestW35a2PlannerResume | test_solver_z2b_ohne_befund | 1 | Phase-3-Code | ruft _phase_planner_resume |
| test_pipeline.py | 9211 | TestW35a2PlannerResume | test_z4_befund_ohne_trigger | 1 | Phase-3-Code | ruft _phase_planner_resume |
| test_pipeline.py | 9236 | TestW35a2PlannerResume | test_planner_none_fail_closed | 1 | Phase-3-Code | ruft _phase_plan_speichern, _phase_planner_resume |
| test_pipeline.py | 9269 | TestW35a2PlannerResume | test_merge_done_bleibt_erhalten | 1 | Phase-3-Code | ruft _phase_plan_laden, _phase_plan_speichern |
| test_pipeline.py | 9328 | TestW35a2PlannerResume | test_merge_struktur_verletzt | 1 | Phase-3-Code | ruft _phase_plan_speichern, _phase_planner_resume |
| test_pipeline.py | 9380 | TestW35a2PlannerResume | test_solver_z3_gueltiger_befund | 1 | Phase-3-Code | ruft _phase_plan_speichern, _phase_planner_resume |
| test_pipeline.py | 9438 | TestW35a2PlannerResume | test_solver_z3_kaputter_befund | 1 | Phase-3-Code | ruft _phase_planner_resume |
| test_pipeline.py | 9467 | TestW35a2PlannerResume | test_w48_planner_blockiert_aktive_phase | 1 | Kern bleibt | ruft _AUDIT_KINDS_BEKANNT |
| test_pipeline.py | 9483 | TestW35a2PlannerResume | test_w48_planner_blockiert_abgeschlossene_phase | 1 | Kern bleibt | ruft _AUDIT_KINDS_BEKANNT |
| test_pipeline.py | 9499 | TestW35a2PlannerResume | test_w48_planner_ohne_phase_yaml_frei | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_pipeline.py | 9516 | TestW35a2PlannerResume | test_w48_direkter_planner_aufruf_blockiert | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_pipeline_integration.py | 385 | modul | test_t1_builder_lauf_befuellt_historie | 1 | Kern bleibt | ruft run_pipeline |
| test_pipeline_integration.py | 416 | modul | test_t2_apply_befuellt_mess_nach | 1 | Kern bleibt | ruft run_pipeline |
| test_pipeline_integration.py | 443 | modul | test_t3_review_loop_akkumuliert_verdicts | 1 | Kern bleibt | ruft run_pipeline |
| test_pipeline_integration.py | 470 | modul | test_w30_fix_b_max_builder_runden_null | 1 | Kern bleibt | ruft builder_reply_mit_command_loop |
| test_pipeline_integration.py | 520 | modul | test_solver_max_runden_erreicht_payload | 1 | Kern bleibt | ruft handle_deadlock_mit_solver |
| test_pipeline_integration.py | 566 | modul | test_w25_planner_prompt_enthaelt_skills | 1 | Phase-3-Code | ruft _planner_user_content |
| test_pipeline_integration.py | 579 | modul | test_w25_planner_prompt_enthaelt_geladene_skills | 1 | Phase-3-Code | ruft _planner_user_content |
| test_pipeline_integration.py | 592 | modul | test_w25_planner_load_skill_e2e | 1 | Phase-3-Code | ruft _planner_lauf |
| test_planner.py | 26 | TestPraefixe | test_praefixe_konstant | 1 | Kern bleibt | ruft PLANNER_BLOCK_PRAEFIXE |
| test_planner.py | 31 | TestPraefixe | test_praefixe_ist_tupel | 1 | Kern bleibt | ruft PLANNER_BLOCK_PRAEFIXE |
| test_planner.py | 40 | TestParser | test_auftrag_gueltig | 1 | Kern bleibt | ruft parse_planner_reply |
| test_planner.py | 55 | TestParser | test_alle_praefixe_erkannt | 1 | Kern bleibt | ruft PLANNER_BLOCK_PRAEFIXE, parse_planner_reply |
| test_planner.py | 62 | TestParser | test_unbekanntes_praefix_ungueltig | 1 | Kern bleibt | ruft parse_planner_reply |
| test_planner.py | 67 | TestParser | test_ohne_praefix_ungueltig | 1 | Kern bleibt | ruft parse_planner_reply |
| test_planner.py | 72 | TestParser | test_rueckfrage | 1 | Kern bleibt | ruft parse_planner_reply |
| test_planner.py | 78 | TestParser | test_leer_ungueltig | 1 | Kern bleibt | ruft parse_planner_reply |
| test_planner.py | 82 | TestParser | test_whitespace_ungueltig | 1 | Kern bleibt | ruft parse_planner_reply |
| test_planner.py | 86 | TestParser | test_freitext_ungueltig | 1 | Kern bleibt | ruft parse_planner_reply |
| test_planner.py | 91 | TestParser | test_praefix_case_insensitive | 1 | Kern bleibt | ruft parse_planner_reply |
| test_planner.py | 98 | TestParser | test_text_feld_immer_gesetzt | 1 | Kern bleibt | ruft parse_planner_reply |
| test_planner.py | 109 | TestRolle | test_planner_rolle_geladen | 1 | Kern bleibt | ruft load_agents |
| test_planner.py | 114 | TestRolle | test_planner_hard_rules_verfuegbar | 1 | Kern bleibt | ruft HARD_RULES_PLANNER |
| test_planner.py | 119 | TestRolle | test_planner_in_mapping | 1 | Kern bleibt | ruft HARD_RULES_BY_ROLE, HARD_RULES_PLANNER |
| test_planner.py | 130 | TestPlannerLauf | test_planner_lauf_signatur | 1 | Phase-3-Code | ruft _planner_lauf |
| test_planner.py | 153 | TestMain | test_planner_main_pfad_existiert | 1 | Kern bleibt | ruft _planner_main_pfad |
| test_planner.py | 166 | TestRunState | test_planner_felder_vorhanden | 1 | Kern bleibt | ruft RunState |
| test_planner.py | 173 | TestRunState | test_defaults | 1 | Kern bleibt | ruft RunState |
| test_planner.py | 190 | TestPlannerStufenPrompt | test_body_enthaelt_stufe_1_sektion | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_planner.py | 194 | TestPlannerStufenPrompt | test_body_enthaelt_stufe_2_sektion | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_planner.py | 198 | TestPlannerStufenPrompt | test_prompt_stufe_1_enthaelt_p3 | 1 | Kern bleibt | ruft build_system_prompt |
| test_planner.py | 205 | TestPlannerStufenPrompt | test_prompt_stufe_2_enthaelt_p3strich | 1 | Kern bleibt | ruft build_system_prompt |
| test_planner.py | 214 | TestPlannerStufenPrompt | test_prompt_stufe_2_enthaelt_nicht_original_p3 | 1 | Kern bleibt | ruft build_system_prompt |
| test_planner.py | 222 | TestPlannerStufenPrompt | test_prompt_default_ist_stufe_1 | 1 | Kern bleibt | ruft build_system_prompt |
| test_planner.py | 230 | TestPlannerStufenPrompt | test_user_content_stufe_2 | 1 | Phase-3-Code | ruft _planner_user_content |
| test_planner.py | 237 | TestPlannerStufenPrompt | test_user_content_stufe_1 | 1 | Phase-3-Code | ruft _planner_user_content |
| test_planner.py | 249 | TestPlannerRolleGroesse | test_stufe2_hat_p15 | 1 | Kern bleibt | ruft HARD_RULES_PLANNER_STUFE2 |
| test_planner.py | 252 | TestPlannerRolleGroesse | test_stufe2_hat_p16 | 1 | Kern bleibt | ruft HARD_RULES_PLANNER_STUFE2 |
| test_planner.py | 255 | TestPlannerRolleGroesse | test_stufe2_p15_zieldateien | 1 | Kern bleibt | ruft HARD_RULES_PLANNER_STUFE2 |
| test_planner.py | 258 | TestPlannerRolleGroesse | test_stufe2_p16_praefix_neu | 1 | Kern bleibt | ruft HARD_RULES_PLANNER_STUFE2 |
| test_planner.py | 261 | TestPlannerRolleGroesse | test_stufe1_kein_p15 | 1 | Kern bleibt | ruft HARD_RULES_PLANNER_STUFE1 |
| test_planner.py | 264 | TestPlannerRolleGroesse | test_stufe1_kein_p16 | 1 | Kern bleibt | ruft HARD_RULES_PLANNER_STUFE1 |
| test_planner.py | 267 | TestPlannerRolleGroesse | test_stufe1_unveraendert | 1 | Kern bleibt | ruft HARD_RULES_PLANNER_STUFE1 |
| test_planner.py | 273 | TestPlannerRolleGroesse | test_stufe2_p10_p14_unveraendert | 1 | Kern bleibt | ruft HARD_RULES_PLANNER_STUFE2 |
| test_planner.py | 279 | TestPlannerRolleGroesse | test_stufe2_hat_refactoring_ausnahme | 1 | Kern bleibt | ruft HARD_RULES_PLANNER_STUFE2 |
| test_planner.py | 282 | TestPlannerRolleGroesse | test_planner_md_zerlegst | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_planner.py | 288 | TestPlannerRolleGroesse | test_planner_md_baubare | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_planner.py | 294 | TestPlannerRolleGroesse | test_planner_md_rolle_stufe_1 | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_planner.py | 300 | TestPlannerRolleGroesse | test_planner_md_rolle_stufe_2 | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_planner.py | 306 | TestPlannerRolleGroesse | test_planner_md_guter_plan | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_planner.py | 312 | TestPlannerRolleGroesse | test_planner_md_schlechter_plan | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_planner.py | 318 | TestPlannerRolleGroesse | test_build_system_prompt_stufe2_hat_p15 | 1 | Kern bleibt | ruft build_system_prompt, load_agents |
| test_planner.py | 327 | TestPlannerRolleGroesse | test_build_system_prompt_stufe1_kein_p15 | 1 | Kern bleibt | ruft build_system_prompt, load_agents |
| test_planner.py | 341 | TestPlannerPraezision | test_stufe2_hat_p17 | 1 | Kern bleibt | ruft HARD_RULES_PLANNER_STUFE2 |
| test_planner.py | 344 | TestPlannerPraezision | test_stufe2_hat_p18 | 1 | Kern bleibt | ruft HARD_RULES_PLANNER_STUFE2 |
| test_planner.py | 347 | TestPlannerPraezision | test_stufe2_p15_unterpunkt_regel | 1 | Kern bleibt | ruft HARD_RULES_PLANNER_STUFE2 |
| test_planner.py | 351 | TestPlannerPraezision | test_stufe2_p15_atomar_ausnahme | 1 | Kern bleibt | ruft HARD_RULES_PLANNER_STUFE2 |
| test_planner.py | 355 | TestPlannerPraezision | test_stufe2_p15_datei_regel | 1 | Kern bleibt | ruft HARD_RULES_PLANNER_STUFE2 |
| test_planner.py | 360 | TestPlannerPraezision | test_stufe2_p17_signatur_tiefe | 1 | Kern bleibt | ruft HARD_RULES_PLANNER_STUFE2 |
| test_planner.py | 366 | TestPlannerPraezision | test_stufe2_p17_gut_schlecht_beispiel | 1 | Kern bleibt | ruft HARD_RULES_PLANNER_STUFE2 |
| test_planner.py | 372 | TestPlannerPraezision | test_stufe1_kein_p17_p18 | 1 | Kern bleibt | ruft HARD_RULES_PLANNER_STUFE1 |
| test_planner.py | 377 | TestPlannerPraezision | test_stufe2_p9strich_verweist_auf_p18 | 1 | Kern bleibt | ruft HARD_RULES_PLANNER_STUFE2 |
| test_planner.py | 382 | TestPlannerPraezision | test_planner_md_p18_sektion | 1 | Kern bleibt | reine Berechnung/Datenstruktur, kein pipeline-Aufruf |
| test_planner.py | 389 | TestPlannerPraezision | test_build_system_prompt_stufe2_hat_p17 | 1 | Kern bleibt | ruft build_system_prompt, load_agents |
| test_planner.py | 425 | TestPlannerKorrekturKontext | test_user_content_reviewer_befund_marker | 1 | Phase-3-Code | ruft _planner_user_content |
| test_planner.py | 433 | TestPlannerKorrekturKontext | test_user_content_reviewer_befund_leer_kein_marker | 1 | Phase-3-Code | ruft _planner_user_content |
| test_planner.py | 440 | TestPlannerKorrekturKontext | test_user_content_reviewer_befund_nicht_gekuerzt | 1 | Phase-3-Code | ruft _planner_user_content |
| test_planner.py | 448 | TestPlannerKorrekturKontext | test_user_content_p10_p18_im_abschluss | 1 | Phase-3-Code | ruft _planner_user_content |
| test_planner.py | 456 | TestPlannerKorrekturKontext | test_user_content_phase_stand_sektion | 1 | Phase-3-Code | ruft _planner_user_content |
| test_planner.py | 465 | TestPlannerKorrekturKontext | test_user_content_phase_stand_naechster_hinweis | 1 | Phase-3-Code | ruft _planner_user_content |
| test_planner.py | 476 | TestPlannerKorrekturKontext | test_user_content_phase_stand_none_keine_sektion | 1 | Phase-3-Code | ruft _planner_user_content |
| test_planner.py | 482 | TestPlannerKorrekturKontext | test_user_content_phase_stand_alle_done_fallback | 1 | Phase-3-Code | ruft _planner_user_content |
| test_planner.py | 493 | TestPlannerKorrekturKontext | test_phase_stand_sektion_letzter_befund_gekuerzt | 1 | Kern bleibt | ruft _phase_stand_sektion |
| test_planner.py | 501 | TestPlannerKorrekturKontext | test_planner_lauf_reicht_phase_stand_durch | 1 | Phase-3-Code | ruft _planner_lauf |
| test_planner.py | 522 | TestPlannerUnbeantwortet | test_plan_unbeantwortet_punkte_leer | 1 | Kern bleibt | ruft _plan_unbeantwortet_punkte |
| test_planner.py | 526 | TestPlannerUnbeantwortet | test_plan_unbeantwortet_punkte_einer | 1 | Kern bleibt | ruft _plan_unbeantwortet_punkte |
| test_planner.py | 533 | TestPlannerUnbeantwortet | test_plan_unbeantwortet_punkte_mehrere_gleicher_ub | 1 | Kern bleibt | ruft _plan_unbeantwortet_punkte |
| test_planner.py | 540 | TestPlannerUnbeantwortet | test_plan_unbeantwortet_punkte_mehrere_unterbloecke | 1 | Kern bleibt | ruft _plan_unbeantwortet_punkte |
| test_planner.py | 550 | TestPlannerUnbeantwortet | test_plan_unbeantwortet_punkte_case_sensitive | 1 | Kern bleibt | ruft _plan_unbeantwortet_punkte |
| test_planner.py | 556 | TestPlannerUnbeantwortet | test_konstante_unbeantwortet_praefix_existiert | 1 | Kern bleibt | ruft _UNBEANTWORTET_PRAEFIX |
| test_planner.py | 559 | TestPlannerUnbeantwortet | test_audit_kind_phase_plan_unbeantwortet_existiert | 1 | Kern bleibt | ruft _AUDIT_KINDS_BEKANNT |
| test_planner.py | 564 | TestPlannerUnbeantwortet | test_parse_phase_plan_unveraendert_durch_unbeantwortet | 1 | Kern bleibt | ruft _parse_phase_plan |
| test_planner.py | 577 | TestPlannerUnbeantwortet | test_unbeantwortet_wird_nicht_gespeichert | 1 | Phase-3-Code | ruft _phase_plan_korrektur |
| test_planner.py | 614 | TestPlannerStruktur | test_phase_stand_sektion_struktur_hinweis | 1 | Kern bleibt | ruft _phase_stand_sektion |
| test_planner.py | 618 | TestPlannerStruktur | test_phase_stand_sektion_nur_inhalt_aendern | 1 | Kern bleibt | ruft _phase_stand_sektion |
| test_planner.py | 622 | TestPlannerStruktur | test_phase_stand_sektion_alle_unterbloecke | 1 | Kern bleibt | ruft _phase_stand_sektion |
| test_planner.py | 627 | TestPlannerStruktur | test_phase_stand_sektion_generisch | 1 | Kern bleibt | ruft _phase_stand_sektion |
| test_planner.py | 633 | TestPlannerStruktur | test_phase_stand_sektion_fallback_unveraendert | 1 | Kern bleibt | ruft _phase_stand_sektion |
| test_planner.py | 642 | TestPlannerStruktur | test_p18_struktur_reihenfolge | 1 | Kern bleibt | ruft HARD_RULES_PLANNER_STUFE2 |
| test_projekt_schema.py | 51 | TestPflichtfelder | test_leere_config_meldet_pflichtfelder | 1 | Kern bleibt | testet anderes Modul (test_projekt_schema.py) |
| test_projekt_schema.py | 56 | TestPflichtfelder | test_gueltige_config_keine_meldungen | 1 | Kern bleibt | testet anderes Modul (test_projekt_schema.py) |
| test_projekt_schema.py | 61 | TestPflichtfelder | test_fehlendes_docs_decisions | 1 | Kern bleibt | testet anderes Modul (test_projekt_schema.py) |
| test_projekt_schema.py | 73 | TestUnbekannteFelder | test_unbekanntes_top_feld | 1 | Kern bleibt | testet anderes Modul (test_projekt_schema.py) |
| test_projekt_schema.py | 79 | TestUnbekannteFelder | test_unbekannter_docs_schluessel | 1 | Kern bleibt | testet anderes Modul (test_projekt_schema.py) |
| test_projekt_schema.py | 91 | TestAliase | test_agents_dir_aliased_zu_project_agents_dir | 1 | Kern bleibt | testet anderes Modul (test_projekt_schema.py) |
| test_projekt_schema.py | 98 | TestAliase | test_docs_handoff_aliased_zu_reviewer | 1 | Kern bleibt | testet anderes Modul (test_projekt_schema.py) |
| test_projekt_schema.py | 105 | TestAliase | test_docs_context_prompt_aliased_zu_context | 1 | Kern bleibt | testet anderes Modul (test_projekt_schema.py) |
| test_projekt_schema.py | 112 | TestAliase | test_alias_ueberschreibt_nicht_bestehendes_ziel | 1 | Kern bleibt | testet anderes Modul (test_projekt_schema.py) |
| test_projekt_schema.py | 127 | TestDefaults | test_budget_default_wird_gesetzt | 1 | Kern bleibt | testet anderes Modul (test_projekt_schema.py) |
| test_projekt_schema.py | 133 | TestDefaults | test_solver_default_wird_gesetzt | 1 | Kern bleibt | testet anderes Modul (test_projekt_schema.py) |
| test_projekt_schema.py | 139 | TestDefaults | test_default_ueberschreibt_nicht | 1 | Kern bleibt | testet anderes Modul (test_projekt_schema.py) |
| test_projekt_schema.py | 151 | TestModi | test_warn_modus_blockiert_nicht | 1 | Kern bleibt | testet anderes Modul (test_projekt_schema.py) |
| test_projekt_schema.py | 155 | TestModi | test_fail_modus_exit_2 | 1 | Kern bleibt | testet anderes Modul (test_projekt_schema.py) |
| test_projekt_schema.py | 160 | TestModi | test_fail_modus_gueltige_config | 1 | Kern bleibt | testet anderes Modul (test_projekt_schema.py) |
| test_projekt_schema.py | 171 | TestTypen | test_project_muss_str_sein | 1 | Kern bleibt | testet anderes Modul (test_projekt_schema.py) |
| test_projekt_schema.py | 177 | TestTypen | test_require_human_approval_muss_bool_sein | 1 | Kern bleibt | testet anderes Modul (test_projekt_schema.py) |
| test_projekt_schema.py | 184 | TestTypen | test_always_run_muss_list_str_sein | 1 | Kern bleibt | testet anderes Modul (test_projekt_schema.py) |
| test_projekt_schema.py | 195 | TestP2aSchemaFelder | test_schema_planner_phasen_modus | 1 | Kern bleibt | testet anderes Modul (test_projekt_schema.py) |
| test_projekt_schema.py | 207 | TestP2aSchemaFelder | test_schema_budget_max_llm_calls_phase | 1 | Kern bleibt | testet anderes Modul (test_projekt_schema.py) |
| test_projekt_schema.py | 219 | TestP2aSchemaFelder | test_security_ai_yaml_hat_phasen_modus | 1 | Kern bleibt | testet anderes Modul (test_projekt_schema.py) |
| test_redaction.py | 21 | TestRedactSecrets | test_ipv4_masked | 1 | Kern bleibt | testet anderes Modul (test_redaction.py) |
| test_redaction.py | 26 | TestRedactSecrets | test_ipv6_masked | 1 | Kern bleibt | testet anderes Modul (test_redaction.py) |
| test_redaction.py | 32 | TestRedactSecrets | test_mac_masked | 1 | Kern bleibt | testet anderes Modul (test_redaction.py) |
| test_redaction.py | 37 | TestRedactSecrets | test_api_key_masked | 1 | Kern bleibt | testet anderes Modul (test_redaction.py) |
| test_redaction.py | 42 | TestRedactSecrets | test_aws_key_masked | 1 | Kern bleibt | testet anderes Modul (test_redaction.py) |
| test_redaction.py | 47 | TestRedactSecrets | test_github_token_masked | 1 | Kern bleibt | testet anderes Modul (test_redaction.py) |
| test_redaction.py | 52 | TestRedactSecrets | test_bearer_token_masked | 1 | Kern bleibt | testet anderes Modul (test_redaction.py) |
| test_redaction.py | 57 | TestRedactSecrets | test_long_hex_masked | 1 | Kern bleibt | testet anderes Modul (test_redaction.py) |
| test_redaction.py | 62 | TestRedactSecrets | test_clean_text_unchanged | 1 | Kern bleibt | testet anderes Modul (test_redaction.py) |
| test_redaction.py | 67 | TestRedactSecrets | test_not_string_fail_closed | 1 | Kern bleibt | testet anderes Modul (test_redaction.py) |
| test_redaction.py | 74 | TestRedactText | test_control_chars_removed | 1 | Kern bleibt | testet anderes Modul (test_redaction.py) |
| test_redaction.py | 81 | TestRedactText | test_injection_marker_masked | 1 | Kern bleibt | testet anderes Modul (test_redaction.py) |
| test_redaction.py | 86 | TestRedactText | test_system_prefix_masked | 1 | Kern bleibt | testet anderes Modul (test_redaction.py) |
| test_redaction.py | 91 | TestRedactText | test_im_start_marker_masked | 1 | Kern bleibt | testet anderes Modul (test_redaction.py) |
| test_redaction.py | 96 | TestRedactText | test_max_len_truncates | 1 | Kern bleibt | testet anderes Modul (test_redaction.py) |
| test_redaction.py | 102 | TestRedactText | test_max_len_zu_klein_wirft_fehler | 1 | Kern bleibt | testet anderes Modul (test_redaction.py) |
| test_redaction.py | 107 | TestRedactText | test_max_len_0_wirft_fehler | 1 | Kern bleibt | testet anderes Modul (test_redaction.py) |
| test_redaction.py | 112 | TestRedactText | test_max_len_gleich_platzhalterlaenge | 1 | Kern bleibt | testet anderes Modul (test_redaction.py) |
| test_redaction.py | 119 | TestRedactText | test_max_len_10_kurzer_text_ok | 1 | Kern bleibt | testet anderes Modul (test_redaction.py) |
| test_redaction.py | 125 | TestRedactText | test_clean_text_unchanged | 1 | Kern bleibt | testet anderes Modul (test_redaction.py) |
| test_redaction.py | 130 | TestRedactText | test_not_string_fail_closed | 1 | Kern bleibt | testet anderes Modul (test_redaction.py) |
| test_redaction.py | 143 | TestRedactField | test_ipv4_masked | 1 | Kern bleibt | testet anderes Modul (test_redaction.py) |
| test_redaction.py | 148 | TestRedactField | test_mac_masked | 1 | Kern bleibt | testet anderes Modul (test_redaction.py) |
| test_redaction.py | 153 | TestRedactField | test_key_masked | 1 | Kern bleibt | testet anderes Modul (test_redaction.py) |
| test_redaction.py | 158 | TestRedactField | test_injection_masked | 1 | Kern bleibt | testet anderes Modul (test_redaction.py) |
| test_redaction.py | 163 | TestRedactField | test_none_fail_closed_but_not_marked | 1 | Kern bleibt | testet anderes Modul (test_redaction.py) |
| test_redaction.py | 171 | TestRedactField | test_int_stringified | 1 | Kern bleibt | testet anderes Modul (test_redaction.py) |
| test_redaction.py | 176 | TestRedactField | test_dict_fail_closed | 1 | Kern bleibt | testet anderes Modul (test_redaction.py) |
| test_redaction.py | 188 | TestRedactMapping | test_ipv4_in_mapping | 1 | Kern bleibt | testet anderes Modul (test_redaction.py) |
| test_redaction.py | 193 | TestRedactMapping | test_mac_in_mapping | 1 | Kern bleibt | testet anderes Modul (test_redaction.py) |
| test_redaction.py | 198 | TestRedactMapping | test_key_in_mapping | 1 | Kern bleibt | testet anderes Modul (test_redaction.py) |
| test_redaction.py | 203 | TestRedactMapping | test_injection_in_mapping | 1 | Kern bleibt | testet anderes Modul (test_redaction.py) |
| test_redaction.py | 208 | TestRedactMapping | test_clean_mapping_unchanged | 1 | Kern bleibt | testet anderes Modul (test_redaction.py) |
| test_redaction.py | 213 | TestRedactMapping | test_non_string_keys_removed | 1 | Kern bleibt | testet anderes Modul (test_redaction.py) |
| test_redaction.py | 221 | TestRedactAll | test_combined_ip_and_injection | 1 | Kern bleibt | testet anderes Modul (test_redaction.py) |
| test_redaction.py | 228 | TestRedactAll | test_clean_unchanged | 1 | Kern bleibt | testet anderes Modul (test_redaction.py) |
| test_redaction.py | 236 | TestRedactionConstants | test_max_field_len_defined | 1 | Kern bleibt | testet anderes Modul (test_redaction.py) |
| test_redaction.py | 239 | TestRedactionConstants | test_all_exports | 1 | Kern bleibt | testet anderes Modul (test_redaction.py) |
| test_redaction.py | 250 | TestPrivateIpsBleiben | test_ipv4_privat_bleibt | 1 | Kern bleibt | testet anderes Modul (test_redaction.py) |
| test_redaction.py | 257 | TestPrivateIpsBleiben | test_ipv6_privat_bleibt | 1 | Kern bleibt | testet anderes Modul (test_redaction.py) |
| test_redaction.py | 262 | TestPrivateIpsBleiben | test_ipv4_oeffentlich_bleibt_maskiert | 1 | Kern bleibt | testet anderes Modul (test_redaction.py) |
| test_redaction.py | 268 | TestPrivateIpsBleiben | test_wurde_flag_bei_privater_ip | 1 | Kern bleibt | testet anderes Modul (test_redaction.py) |
| test_redaction.py | 272 | TestPrivateIpsBleiben | test_grenzfaelle | 1 | Kern bleibt | testet anderes Modul (test_redaction.py) |
