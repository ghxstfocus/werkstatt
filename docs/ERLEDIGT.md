# Erledigt — Werkstatt

Stand: 2026-10-18
Append-only. Alte Eintraege nicht loeschen.
Bei > 200 Zeilen: aeltere Eintraege ins
`Bau-Handoff-Archiv.md`.

Spalten:
- Block: W-Nummer.
- Status: ✅ verifiziert, 🔧 nachgebessert, ⚠️ Symptom.
- Commit: 7-Zeichen-Hash.
- Tests: Werkstatt-Tests nach dem Block.
- Katalog: Audit-Kinds-Groesse (wo bekannt).

## W1–W35 (Basis, 2026-10-16/17)

| Block | Titel | Status | Commit | Tests | Katalog |
|---|---|---|---|---|---|
| W1 | EXTRACT_PATHS erweitert | ✅ | — | — | — |
| W2 | HARD_RULES_BUILDER verschaerft | ✅ | 0e6c881 | — | — |
| W3+W4 | Planner-Messung + Plan-Korrektur | ✅ | — | 912 | 75 |
| W6a+W6b | read_file-Zeilenbereich | ✅ | e779c77 | — | — |
| W7 | Basis-Gate A/M aus done-Pfaden | ✅ | — | — | — |
| W8 | Commit-Paket-Prompt + Message-Check | ✅ | — | — | — |
| W10 | Message-Check praeziser | ✅ | — | — | — |
| W11 | Unterblock-Isolation | ✅ | — | — | — |
| W13a+b | Anker-Zeilenbereich, Ersatz-Pruefung | ✅ | — | — | — |
| W23 | Kommunikationswege-Audit | ✅ | c3bd4db | — | — |
| W24a | Apply idempotent | ✅ | 4531451 | — | — |
| W25 | Skills-Infrastruktur | ✅ | 317b000 | — | — |
| W25a-e | Basis-Gate Testanzahl | ✅ | 784dd98..dcda015 | — | — |
| W26 | plan.md als Datei | ✅ | 05c817e | — | — |
| W27 | Sprint-Contracts | ✅ | 309aeef | — | — |
| W28a | Judge-Rolle + Reviewer reduziert | ✅ | f122c39 | — | — |
| W28b+c | Review-Loop auf Judge, Antwort-Limit | ✅ | — | — | — |
| W29 | Aggregated Phase-Review | ✅ | 0faa69f | — | — |
| W30 | Loop-Cap-Konsistenz | ✅ | — | — | — |
| W31 | mypy-Fixes | ✅ | — | — | — |
| W32 | schreibe_contract in run_phase-Loop | ✅ | — | — | — |
| W33a | post_apply_messung liest patch-Pfade | ✅ | — | — | — |
| W33b | phase_apply_vor_review | ✅ | 79027d8 | — | — |
| W34a | .werkstatt/ ignorieren (security-ai) | ✅ | 87a2fbe | — | — |
| W34b | _phasen_basis_gate_ok ignoriert .werkstatt/ | ✅ | — | — | — |
| W35a-1 | Planner-Resume (Basis) | ✅ | — | — | — |
| W35a-2 | Planner-Resume (Merge) | ✅ | — | — | — |
| W35a-2d | Suffix-Aufteilung | ✅ | 0aa9943 | — | — |
| W35a-2d-4 | Anzahl-Check bei validiertem Split | ✅ | fe1ae5e | — | — |
| W35a-2d-5 | ID-Check bei validiertem Split | ✅ | b9ddd58 | — | — |
| W35a-2d-6 | Ambig-Check bidirektional | ✅ | e65ca14 | — | — |

## W36–W47 (Modularisierung, 2026-10-17)

| Block | Titel | Status | Commit | Tests | Katalog |
|---|---|---|---|---|---|
| W36-1b | werkstatt/state.py (restliche Dataclasses) | ✅ | 3cfbb0b | — | — |
| W36-2a | werkstatt/parser.py (Phasen-Parser) | ✅ | d934c11 | — | — |
| W37 | builder.md um 3 Luecken | ✅ | 28b2ecb | — | — |
| W38 | alter_plan im P10-P16-Format | ✅ | 27dd5a2 | — | — |
| W39 | Parser toleranter | ✅ | d342e6f | — | — |
| W40 | judge.md + planner.md Praezisierungen | ✅ | ebb9fed | — | — |
| W41 | classify_verdict akzeptiert NO_GO | ✅ | 6e4926a | — | — |
| W42 | Planner-Resume-Messung | ✅ | 255191b | — | — |
| W43 | new_file-Idempotenz | ✅ | 04eb69f | — | — |
| W44 | Judge-Prompt-Groesse begrenzen | ✅ | 9e26edd | — | — |
| W45 | Planner-Resume zeigt fehlende Dateien | ✅ | e621e24 | — | — |
| W47 | Idempotenz-Check vor Gesamt-Review | ✅ | 8aaa861 | 1102 | — |

## W46–W50 (Judge/Planner-Bugs, 2026-10-18)

| Block | Titel | Status | Commit | Tests | Katalog |
|---|---|---|---|---|---|
| W46 | Judge-Skip bei Doku-Patches/Phasen | ✅ | 38d3960 | 1113 | 107 |
| W48 | Planner-Start bei existierender phase.yaml sperren | 🔧 | 6ba89a6 | 1106 | — |
| W48-A16 | Katalog +2, Print-Statement | 🔧 | 7c46c7b | 1114 | 109 |
| W50 | Planner-Durchfall bei abgeschlossener Phase | 🔧 | 739397f | 1120 | 111 |

## W51a–h (Planner-Mess-Mechanik, 2026-10-18) — Symptom

| Block | Titel | Status | Commit | Tests | Katalog |
|---|---|---|---|---|---|
| W51a | Planner-Prompt MESS-PFLICHT | ⚠️ | 23ce844 | 1122 | 111 |
| W51b | Parser-Sperre new_file existierend | ⚠️ | 7f7f1c5 | 1127 | 113 |
| W51c | Planner-COMMAND-Bereinigung | ⚠️ | 02388fa | 1134 | 115 |
| W51d | Planner-Mess-Mechanik | ⚠️ | 1a64efd | 1139 | 116 |
| W51e | Planner-Loop bricht bei inhaltsleerer Runde | ⚠️ | ae7f5e3 | 1142 | 117 |
| W51f | Planner teilt zu grosse Phasen | ⚠️ | 89818c7 | 1147 | 118 |
| W51g | Planner-Dedup + Format-Fehler-Kontext | ⚠️ | 6a8412b | 1153 | 118 |
| W51h | Plan + COMMANDs im selben Reply | ⚠️ | 8205456 | 1158 | 118 |

## W54a/g/h (Builder-Fixes, 2026-10-18) — Symptom

| Block | Titel | Status | Commit | Tests | Katalog |
|---|---|---|---|---|---|
| W54a | builder.md-Regeln doppelte Imports | ⚠️ | d291c37 | 1161 | 118 |
| W54g | apply_code_patches Ersatz-Duplikate | ⚠️ | 546bc22 | 1165 | 119 |
| W54h | builder.md-Regel Ziel-Klasse | ⚠️ | 00483a1 | 1166 | 119 |

## W60 (Doku-Struktur, 2026-10-18)

| Block | Titel | Status | Commit | Tests | Katalog |
|---|---|---|---|---|---|
| W60 | Doku-Struktur (KONVENTION, ARCHITEKTUR, ROADMAP, OFFENE, ERLEDIGT, IDEEN) | 🔧 | 76c5af5 | 1166 | 119 |

## Phasen

| Phase | Titel | Status | Commit | Tests |
|---|---|---|---|---|
| 1 | Projekt-Schema | ✅ | 406e3cc | — |
| 3a-1 | Anti-Pattern-Bibliothek | ✅ | 1ed875a | — |
| 3a-2 | Anti-Pattern-Katalog | ✅ | 8ed6cd0 | — |
| 3b | Builder-Injektion | ✅ | 04012f6 | — |
| 3c-1 | Reviewer + Solver Injektion | ✅ | 4916b01 | — |
| 3c-1b | Reviewer/Solver-Praezisierung | ✅ | 045556e | — |
| 18 | Guardrails | ✅ | — | — |
| 19 | ChangeApplier + Sofort-Massnahmen | ✅ | 163f29b | 1102 |
| 20a | Change-Modell (Audit-Trail-Felder) | 🔧 | 560659a | 1452 |

## Sitzung 2026-10-18 — Sanierungs-Welle + W52b (A/B)

| Block | Kategorie | Commit | Tests | Katalog |
|---|---|---|---|---|
| B1-Schritt-1 (Audit-Fix) | 1 | 15ce62a | 1169 | 119 |
| W51c-fix (Parser) | 3 | 679251c | 1176 | 119 |
| A1b-fix (Solver-Blindheit) | 3 | 800e924 | 1179 | 119 |
| T-2 (Integrationstest) | 1 | aefecc7 | 1180 | 119 |
| B1 (Leichen) | 3 | 3e1d804 | 1171 | 120 |
| W30-fix (Loop-Cap) | 3 | 5dbbb79 | 1174 | 120 |
| W48-A16-b (AST-Test) | 3 | a074be1 | 1177 | 122 |
| W48-A16-b-2 (Katalog) | 3 | bc69ffc | 1177 | 158 |
| W36-RP (Integrationstest) | 3 | d0233c8 | 1180 | 158 |
| W30-fix-b (max=0) | 2 | ab0f389 | 1181 | 159 |
| W48-A16-b-2-a (solver_max-Merge) | 2 | 70df288 | 1182 | 158 |
| W36-RP-b (subprocess-Schutz) | 2 | 904c0de | 1186 | 158 |
| W25-planner-md (Skills) | 3 | 041c9a3 | 1189 | 158 |
| W52b A/B (On-Demand) | 3 | (offen) | 1189 | 160 |

### Was die Welle geliefert hat

- Drei Integrations-Luecken behoben (W51c, A1b, W30).
- Katalog-Pflege saniert: AST-Test + _KATALOG_SOLL,
  36 fehlende Kinds, 1 Merge.
- 5 Leichen entfernt (B1).
- Integrationstest-Infrastruktur (W36-RP).
- UnboundLocalError behoben (W30-fix-b).
- subprocess-Schutz global (W36-RP-b).
- Skills im Planner-Prompt (W25-planner-md) +
  load_skill-only-Bugfix.
- 47,7M Tokens, 1.468 API-Requests in 3 Tagen
  (Mensch-Messung). Davon ~20 Bloecke gebaut.

### W52b (On-Demand) — offen

- A (messungen_nach_apply): gebaut.
- B (_gemessene_pfade liest Liste): offen.
- C (Anker-Check gegen Datei-Inhalte): offen.
- D (Prompt-Bauer auf Index): offen.
- E (deprecated markieren): offen.

### Naechste Bloecke

- W61 (Rollen-Sanierung): 5 Unterbloecke a-e.
- W-Resume-Fail-Kontext: Fail-Log + Skill.
- W52b C/D/E.

### Sitzung 2026-10-18 (Fortsetzung) — W52b C+D+E, W61, W58

| Block | Titel | Status | Commit | Tests |
|---|---|---|---|---|
| W52b C | Anker-Check gegen Datei-Inhalte | ✅ | e768353 | 1188 |
| W52b D+E | Prompt-Bauer auf Index, mess_protokoll deprecated | ✅ | e2b3ab3 | 1188 |
| W61a-c | Rollen-Trennung, Judge-Labels, Solver-Modell | ✅ | 9ead335 | 1188 |
| W61 | Explore-Ergebnis in state + Builder-Prompt | ✅ | 15c7561 | 1188 |
| W61 | Builder-Prompt erklaert explore vs read_file | ✅ | 2e2c58b | 1188 |
| W61 | read_file auf Zieldateien blockieren (verworfen) | ⚠️ | c32c59d | 1188 |
| W61 | builder.md read_file -> explore | ✅ | ca5c461 | 1188 |
| W61 | Revert read_file-Block (Guard war falsch) | ✅ | 98b9853 | 1188 |
| W61 | Tests auf explore umgestellt | ✅ | da94939 | 1188 |
| W61 | Zieldatei-Volltext im Builder-Prompt | ✅ | 3b907a9 | 1188 |
| W61 | Dedent in _parse_einzelpatch | 🔧 | 9b6d166 | 1188 |
| W61 | Parser-Heuristik + Anker-Check whitespace-tolerant | ✅ | 81efad8 | 1188 |
| W61 | pytest-Measurement (Einzeldatei, 300s) | ✅ | 65d4d07 | 1188 |
| W58 | max_tokens_judge 2048 -> 8192 | ✅ | e2e8b60 | 1188 |

**Was diese Sitzung geliefert hat:**

- W52b C+D+E komplett: `mess_protokoll` deprecated,
  `_mess_index_block` (Pointer mit Pfad/SHA/Preview/Datei),
  `_mess_inhalt_zieldateien` (Volltext nur fuer Zieldateien),
  `_mess_inhalt_nach_apply` (strukturiert).
- W61: Judge-Labels im Judge-Loop (vorher Reviewer).
  `solver_model` eigene Rolle. Subagenten (explore aktiv,
  bash/browser vorhanden). `builder.md` read_file -> explore.
- Parser: YAML-Block-Scalar-Heuristik (2 vs. >2 Einrueckung).
  `_anker_in_messung` whitespace-tolerant.
- pytest-Measurement (Einzeldatei, Whitelist, 300s Timeout).
- W58: max_tokens_judge 8192 (Reasoning-Modell hatte kein
  Budget fuer sichtbare Antwort).

**Wichtige Erkenntnis:** Der Deadlock war nicht ein
einzelner Bug, sondern eine Kette:
1. Anker-Check gegen String statt Datei (W52b C).
2. Parser strippt falsche Einrueckung (W61 Parser-Heuristik).
3. Judge antwortet leer (W58).
4. Planner erfindet APIs (AuditWriter.log-Signatur).
5. Builder hat keinen explore-Zugriff (W61 Subagenten).

**Phase 20b (security-ai) ist durch:** U1-U4 done.
Commits 759b9e1, ada910a, 572d881, cba0ee3.
### Sitzung 2026-10-18/19 — W61-Pro, Feedback-Loop, Phase 21

| Block | Titel | Status | Commit |
|---|---|---|---|
| W61 | Planner-Resume nur bei no_go | ✅ | 0beeff2 |
| W61 | failed -> pending (Builder nochmal) | ✅ | 0898faa |
| W61 | Contract im Builder-Prompt | ✅ | 69308d7 |
| W61 | Test-Fehler aus (b)-Gate in Builder-Prompt | ✅ | a3391bc |
| W61 | letzter_test_fehler persistieren | ✅ | 6f6f457 |
| W61-Pro | verify_code (AST-Grounding vor Apply) | ✅ | f3ae1d5 |
| W61-Pro | Katalog +verify_code_befund | ✅ | 6efa322 |
| W61-Pro | verify_code Kwarg-Check (inspect.signature) | ✅ | c846369 |
| W61-Pro | verify_code Test-Bezug-Check | ✅ | d61ce99 |
| W61-Pro | verify_values (Enum-Werte in Assertions) | ✅ | c04848c |
| W61-Pro | verify_values execution_status-Check | ✅ | 25080d2 |
| W61-Pro | _post_apply_messung befuellt messungen_nach_apply | ✅ | 4144076 |
| W61-Pro | execution_status-Regex praezise | ✅ | 9d2b649 |
| W61-Pro | Parser strippt min 2/4 Einrueckung | ✅ | b4e2ad8 |
| W61-Pro | verify_code ignoriert unittest/mock | ✅ | 6027295 |
| W61 | D2-Duplikate pro Paket | ✅ | 0266d3b |
| W61 | Sammel-Commit mit --allow-empty | ✅ | 57940ef |
| W58 | max_tokens_judge 32768 | ✅ | f96ddf9 |
| W61 | Parser Block-Ende per Feld-Token | ✅ | 4648462 |
| W61 | Ersatz-Duplikat-Schwelle 40 -> 50 | ✅ | 9e3e5f0 |
| W61d | builder.md in Phasen-Prompts aufteilen | ✅ | a0ce38d |

**Was diese Sitzung geliefert hat (Pro-System):**

Das Pro-System ist der AgentSeed/Keystone-Ansatz:
Grounding vor dem Schreiben, nicht Prompt-Tuning.

- **verify_code** (AST-Grounding): Vor jedem Apply
  werden Patch-Anker/Ersatz gegen den Projekt-
  Symbol-Index geprueft. Erfundene APIs (z.B.
  `log(status=...)`) werden gefangen, BEVOR der
  Patch angewendet wird.
- **verify_code_kwargs**: `inspect.signature` prueft
  Kwargs gegen echte API-Signaturen. `log(change_id=...)`
  -> Befund „kennt kein Kwarg".
- **verify_values**: Enum-Werte in Assertions gegen
  echte ChangeState-Werte + execution_status-Werte
  aus dem Applier-Code.
- **Test-Bezug-Check**: Patch-Anker gegen
  `failed_test_ids`. Patch am falschen Test -> Befund.
- **Feedback-Loop**: `letzter_test_fehler` persistiert
  in phase.yaml, im Builder-Prompt gerendert.
- **failed -> pending**: Builder-Problem (Test rot),
  Plan gueltig. Planner-Resume nur bei no_go.

**Wichtige Erkenntnisse:**

1. Der Loop war nicht ein Bug, sondern eine Kette:
   Parser-Einrueckung, max_tokens_judge, D2-Duplikate,
   Planner-Resume, Contract im Prompt, Feedback-Loop,
   verify_code.
2. Der Builder braucht die **echte** API-Signatur,
   nicht Contract-Prosa. `verify_code` + `verify_values`
   liefern das.
3. Contract und Realitaet widersprechen sich oft
   (z.B. execution_status="applied" vs "OK").
   verify_code findet das.
4. `_post_apply_messung` schrieb nur String, nicht
   Liste. Der Judge sah 579 statt 6854 Zeichen.

**Phase 21 (security-ai):** U1 (Tests fuer Audit-Log
APPLIED) ist im Feedback-Loop gebaut, 13 Tests gruen.
Der Commit-Review-Judge eskaliert noch (Messlage
unvollstaendig, siehe OFFENE-BLOECKE).



## 3a-1c-2a — W0a-1/2/3 extrahiert (2026-10-20)

Commits: 88e3e5c (AQ-Vorspann 6 Tests), ecf35a4 (W0a-1/2/3 extrahiert),
ae25e08 (B7/B8 + 6887-Verhaltens-Test).

W0a-1 _commit_review_w25_suite: erster W25-Suite-Lauf.
W0a-2 _commit_review_w25_recovery: Recovery bei rotem Suite.
W0a-3 _commit_review_w25_suite_nachlauf: zweiter Suite-Lauf.

7390 (test_sammel_commit_recovery_reparierbar) geloescht (A12-2),
B1a ersetzt Recovery-Absicherung als Verhaltens-Test.

Baseline: 1237 -> 1245 (+8 Tests: B1a/B1b/B2/B3/B4/B6/B7/B8 + 6887).
ruff 17, mypy 7, AST 6, Katalog 167.

## 3a-1c-2b — W2-Extraktion (2026-10-21)

Commits: ca66927 (Entscheidung b), d512264 (Zeile-26-Korrektur),
277029f (W2-Extraktion), 74ff77d (Struktur-Tests), ac4956f
(project_dir-Fix), b502e20 (Block-done), + 13 Doku-Commits
(M-32..M-55, A13..A22).

W2 = 8585-8755 (171 Z.) nach _commit_review_w25_loop extrahiert.
10 Parameter (M-39): state, api_key, project_dir, project_name,
max_llm, max_minutes, reviewer_prompt, builder_prompt,
_hat_anker_patches, _diff_name_only.
Zwei break (COMMIT-GO, ESKALATION) -> return None.
5 Struktur-Tests umgestellt (74ff77d).
mypy-Fix (ac4956f): project_dir str->Path (19->9).

Baseline 1245 / ruff 17 / mypy 9 / AST+Katalog 14.
AQ-Regressionslatte 9/9 gruen.

Entscheidung (b) Durchlauf 44: 3a-1c-2b als gebaut
akzeptiert. W2-Grenze VOR/NACH in OFFENE-BLOECKE.md
Zeile 23 dokumentiert. Doku-Klaerung in 3b.


## 3a-1c-3/C2 — Basis-Gate extrahiert (2026-10-21)

Commits: d06cf23 (C2-Extraktion), fafc5b5 (A17-1
Docstring-Update).

C2 = 8041-8147 (107 Z. nach C0+C1-Verschiebung) ->
_basis_gate (6 Parameter: state, always, config,
file_whitelist, project_dir, project_name).
Position A: _basis_gate vor _commit_review_w25_loop.
Rueckgabe: return 11 bei rot, return None bei gruen.

Baseline 1245 / ruff 17 / mypy 9 / AST+Katalog 14.
Verhaltens-Test test_run_pipeline_basis_gate_rot gruen.


## 3a-1c-3/C0+C1 — Vorlauf+State extrahiert (2026-10-21)

Commits: da67198 (VorlaufErgebnis-Dataclass), bb919d1
(C0+C1-Extraktion), 44eaedc (A22-2-Nach-Liste).

C0+C1 = 8041-8147 (107 Z.) -> _vorlauf_und_state.
VorlaufErgebnis-Dataclass (10 Felder): state, config,
budget, max_llm, max_minutes, project_dir, file_whitelist,
api_key, always, optional.
docs/agents fallen weg (in state.docs/state.agents).

Signatur: -> VorlaufErgebnis | int.
Return: int bei api_key-leer (1) oder memory-korrupt (3).
5 Test-Anpassungen (A9-12): test_guard_quelle_vorhanden,
test_quelle_setzt_aufgabe, test_quelle_audit_phase_felder,
test_config_liest_max_review_aus_yaml,
test_yaml_code_defaults_gleich.

Baseline 1245 / ruff 17 / mypy 9 / AST+Katalog 14.
Return-Bilanz: run_pipeline 34, _vorlauf_und_state 3,
_basis_gate 2, W2 7 = 46 (A22-2-Nach-Liste).


## C6 (Coverage/Chaos) — GESTRICHEN (2026-10-21)

Auftraggeber-Entscheid Durchlauf 48: C6 ist keine
einheitliche Extraktion. Enthaelt:
- Coverage-Messung (execute_commands)
- Test-Generator-Aufruf (state.agents["test_generator"],
  echte Rolle)
- Chaos-Messung (execute_commands)

Kein einheitliches Extraktions-Ziel. Gehoert zu 3b
(Rollen-Reduktion).

Konsequenz: 3a-1c-3 = C0+C1 + C2 (beide done).
C6 bleibt in run_pipeline.


## 3a-1c-4/C8+C9 — Approval+Human-Gate extrahiert (2026-10-21)

Commit: 5762d8e (refactor, auf origin).
Vorlauf: 75f844b (Handoff-Refresh + C8/C9-Grenzen-Korrektur, Doku).

Extraktion: run_pipeline Z. 8819-8898 (Endstand HEAD 75f844b)
-> `_approval_und_human_gate(state, project_dir, project_name, config)
-> int` (pipeline.py Z. 8155-8247, 93 Zeilen).
C8 = 8819-8854 (Approval + Phasen-Paket-Sammlung).
C9 = 8855-8898 (Human-Gate input(), commit-Entscheidung).
Variante A: alle 8 Returns wandern (5x 0, 1x 20, 1x 21, 1x 0).

Return-Bilanz NACH (gemessen via ast):
  run_pipeline               27
  _vorlauf_und_state          3
  _basis_gate                 2
  _commit_review_w25_loop     7
  _approval_und_human_gate    8
  Summe                      47.

Baseline (HEAD 5762d8e):
  pytest -q                            1245 passed
  ruff check .                         17 errors
  mypy pipeline.py werkstatt/          9 errors
  pytest tests/test_audit_kinds.py -q  6 passed
  _KATALOG_SOLL                        167.

Test-Anpassungen (Kategorie 2, A9-12-deklariert):
  #1 tests/test_phase.py:804-811   (duale Quelle)
  #5 tests/test_pipeline.py:6324   (Split)
  #12 tests/test_pipeline.py:8671  (duale Quelle)

Rollback-Anker: 5762d8e (origin).
