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

## 3a-2a/Vorlauf — _phase_vorlauf extrahiert (2026-10-21)

Commit: 20f0e7d (refactor, auf origin).
Vorlauf: 5708bcf (M-57 SESSION-BILANZ).

Extraktion: run_phase Z. 2084-2214 (HEAD 5708bcf) ->
`_phase_vorlauf(state, project_name) -> PhaseVorlaufErgebnis | int`
(pipeline.py Z. 2048-2195, 148 Zeilen).
if-state_ref-Guard (Z. 2081-2083) bleibt in run_phase.

Dataclass: PhaseVorlaufErgebnis (werkstatt/state.py)
  state: RunState
  unterbloecke: list
  api_key: str
  max_phase: int
Bewusst NICHT VorlaufErgebnis wiederverwendet (8/10 Felder ungenutzt).

Return-Bilanz NACH (gemessen via ast):
  run_phase       17 (22 - 6 Vorlauf + 1 Verteiler _vl)
  _phase_vorlauf   7 (6 Fail-fast + 1 PhaseVorlaufErgebnis)
  Summe           24 (+2 Extraktions-Artefakte gegen Original 22).

Baseline (HEAD 20f0e7d):
  pytest -q                            1245 passed
  ruff check .                         17 errors
  mypy pipeline.py werkstatt/          9 errors
  pytest tests/test_audit_kinds.py -q  6 passed
  _KATALOG_SOLL                        167.

Zwischenstaende (ehrlich):
  1. Versuch 1: handgeschriebene Kopie, 25 Tests kaputt. Kein Commit.
  2. Versuch 2: wortwoertliche Extraktion, PhaseVorlaufErgebnis-Import
     fehlte -> 23 Tests kaputt. Kein Commit.
  3. Import-Fix: ruff +1 (I001 Import-Sortierung). Kein Commit.
  4. I001-Fix: 1245/17/9 gruen. Commit.

Test-Anpassungen (Kategorie 2): keine.

Rollback-Anker: 20f0e7d (origin).

## 3a-2b/Loop — _phase_unterblock_loop extrahiert (2026-10-22)

Commit: 8e46062 (refactor, auf origin).
Vorlauf: 20f0e7d (3a-2a), ab6f4cd (M-57 SESSION-BILANZ).

Extraktion: run_phase Loop Z. 2242-2430 (HEAD ab6f4cd) ->
`_phase_unterblock_loop(state, project_name, unterbloecke,
max_phase) -> int` (pipeline.py Z. 2198-2400).
4 Parameter (Signatur-Freeze 18c). api_key NICHT in Signatur (A-5).

M-72-Fix:
  rc_unterblock = 0 Vor-Init (Z. 2210).
  return rc_unterblock Z. 2399 (Klasse-4-Fail-closed).
  return rc_unterblock Z. 2400 (Erfolgs-Fallback, ex-return-0).
  Semantik 1:1 zu Original 5708bcf Z. 2404.

Return-Bilanz NACH (9 Funktionen, Liste im Commit-Body):
  _approval_und_human_gate       8
  _basis_gate                    2
  _commit_review_w25_loop        7
  _phase_vorlauf                 7
  _phase_unterblock_loop         6
  _review_verdict_behandlung    16
  _vorlauf_und_state             3
  run_pipeline                  27
  run_phase                     13
  ------------------------------------------------
  Summe                         89.

Baseline (HEAD 8e46062):
  pytest 1245 / ruff 17 / mypy 9 / AST 6 / Katalog 167. Delta 0.

Test-Anpassungen (Kategorie 2, A9-12):
  TestB0cUndBugs::test_rc_14_kein_rollback
  TestW32ContractImLoop::test_schreibe_contract_im_loop
  Beide getsource-Ziel: run_phase -> _phase_unterblock_loop.

Rollback-Anker: 8e46062 (origin).

## 3a-2d/Wiederaufnahme — _phase_wiederaufnahme extrahiert (2026-10-22)

Commit: 00ffb5e (refactor, auf origin).
Vorlauf: 3f98364 (3a-2c).

Extraktion: run_phase body[14]..[19] (HEAD 3f98364,
Z. 2578-2644) -> `_phase_wiederaufnahme(state, project_name,
state_ref, aggregat, wahl, api_key) -> int`.
6 Parameter (M-94/M-98/M-99). 5 Returns.
Rekursion: return run_phase(...). Max 1 Rekursionstiefe
(phase_korrektur_zyklus >= 1 -> return 23).
Doppelte Sicherung: _phase_main_pfad @ 10596/10602.

Test-Anpassung (Kategorie 2, A9-12):
  tests/test_phase.py:1580 test_zyklus_teilt_sich
    Erster Assert: getsource(run_phase) ->
    getsource(_phase_wiederaufnahme). Zweiter bleibt.

Baseline (HEAD 00ffb5e):
  pytest 1245 / ruff 17 / mypy 9 / AST 6 / Katalog 167.
  Delta 0.

Commit-Body 178 Zeilen, 92 Return-Listen.
M-102: 179 war Schaetzwert, tatsaechlich 178.

## 3a-2 GESAMT — komplett (2026-10-22)

Commits: 20f0e7d (2a), 8e46062 (2b), 3f98364 (2c), 00ffb5e (2d).

run_phase: von 528 Z. / 22 Returns auf 4 Verteiler-Returns
  (_vl, _rc_loop, _res_nachlauf, _rc_wdh).

4 neue Funktionen (nicht 9, M-101-Korrektur):
  _phase_vorlauf        (3a-2a, 7 Returns)
  _phase_unterblock_loop (3a-2b, 6 Returns)
  _phase_nachlauf       (3a-2c, 7 Returns)
  _phase_wiederaufnahme (3a-2d, 5 Returns)

2 neue Dataclasses:
  PhaseVorlaufErgebnis  (state, unterbloecke, api_key, max_phase)
  NachlaufErgebnis      (rc, aggregat, wahl)

Return-Bilanz: 87 -> 92 (Delta +5, Extraktions-Artefakte:
  Verteiler + Erfolgs-Fallbacks + Option-D-Returns).

Baseline 1245/17/9/6/167 durchgehend (alle 4 Sub-Bloecke).

## Loop-Neubau (Phase 1-18) — 2026-10-23

| Phase | Titel | Status | Commit |
|---|---|---|---|
| 1 | Strangler-Fig Wrapper | ✅ | 3c82470 |
| 2 | Harte Gates B1+B2 | ✅ | db39459 |
| 3 | Post-Build Gates | ✅ | 3eb5b34 |
| 4 | Reflection-Loop (Aider) | ✅ | 42ac992 |
| 5 | Planner-Agent | ✅ | 264db19 |
| 6 | Builder-Agent (create + update) | ✅ | 67c0def |
| 7a | Happy Path | ✅ | dcc29bd |
| 7c | Autonomer Task-Loop (Claude) | ✅ | 6206d85 |
| 8 | Reviewer-Agent | ✅ | 87546c0 |
| 9 | Reviewer im Loop | ✅ | 4d63d14 |
| 10 | PreToolUse + PostToolUse Hooks | ✅ | 97b2886 |
| 10+11 | Simplify-Hook | ✅ | 01b5647 |
| 14 | Explorer-Subagent | ✅ | ad98bd8 |
| 15 | Multi-Projekt Verify-Contract | ✅ | (in Phase 14-16) |
| 16 | Projekt-Pfad-Aufloesung | ✅ | 324c367 |
| 18 | CI-Optik (loop_renderer) | ✅ | 92eb7c7 |

**Architektur (gemessen 2026-10-23):**
- `pipeline.py`: 11.118 Z. (Fallback).
- `werkstatt/`: 5.027 Z. (Agenten, Loop, State).
- `hooks/`: 281 Z. (Pre/PostToolUse, Simplify, Anti-Patterns).
- Gesamt: 16.426 Z.
- Baseline: 1290 passed / 13 ruff / 8 mypy / 6 AST / 162 Katalog.

**Neue Agenten:**
- `werkstatt/explorer.py` (89 Z.): read-only Kontext.
- `werkstatt/planner.py` (81 Z.): JSON-Plan.
- `werkstatt/builder.py` (89 Z.): str_replace, create + update.
- `werkstatt/reviewer.py` (103 Z.): Bug-Check.
- `werkstatt/phase_state.py` (137 Z.): Resume, Decisions.
- `werkstatt/loop.py` (447 Z.): Orchestrator.
- `werkstatt/loop_renderer.py` (94 Z.): CI-Optik.

**Neue Hooks:**
- `hooks/pre_tool_use.py` (89 Z.): Waechter (.env, destruktive Kommandos, Datei-Existenz).
- `hooks/post_tool_use.py` (42 Z.): Verifier (Baseline).
- `hooks/simplify.py` (64 Z.): Aufraeumer (Komplexitaet).
- `hooks/anti_patterns.py` (86 Z.): Anti-Patterns.


### M-Nummern-Nachtrag (2026-10-24) — M-283 nachgezogen

Die folgenden 30 M-Nummern sind im Loop-Neubau (Phase 1-18) sowie
in der Aufraeum-Session vergeben und in Commit-Bodies dokumentiert:

M-212, M-213, M-214, M-215, M-217, M-224, M-225, M-227,
M-230, M-231, M-236, M-237, M-240, M-241, M-242, M-243,
M-244, M-246, M-247, M-248, M-255, M-257, M-258, M-259,
M-260, M-261, M-262, M-263, M-264, M-265

M-266 und M-281..M-289 sind im Reviewer-Chat vergeben, aber NICHT
im Loop-Neubau (Phase 1-18) angewandt. M-266 = A8-2-Plan-Korrektur-
Status. M-281..M-289 = Session-Abschluss 2026-10-23/24 (M-281
Baseline-Kette, M-282 Commit-Bodies, M-283 Doku-Nachtrag, M-284
Modul-Signaturen, M-285 PhaseState-Start, M-286..M-289 Abnahme).

M-212..M-280: 39 Nummern nicht vergeben (Skip: M-216, M-218..M-223,
M-226, M-228..M-229, M-232..M-235, M-238..M-239, M-245,
M-249..M-254, M-256, M-266..M-280).

Nachweis: `git log 238e629..c55c849 --format=%B` +
`git log 7494ac4..238e629 --format=%B`.

Abnahme: Reviewer-Session 2026-10-24, M-283.

## A8-Trichotomie (A8-1 + A8-3) — 2026-10-23

| Block | Titel | Status | Commit |
|---|---|---|---|
| A8-1a-1 | ask_llm nach agent.py | ✅ | 7494ac4 |
| A8-1b-0 | 3 Helper + Konstante | ✅ | 9e5346c |
| A8-1b-1a | execute_commands Definition | ✅ | e43b877 |
| A8-1b-0b | Test-Patch-Nachtrag | ✅ | fed2438 |
| A8-1b-1b | execute_commands Umstellung | ✅ | 8fe0e04 |
| A8-1a-2 | build_system_prompt | ✅ | 14bf723 |
| A8-3 | Anti-Pattern-Hook | ✅ | daaba7f |

**A8-2 (Orchestrator):** SKIP (durch Loop-Neubau ersetzt).
**A8-4 (CLI-Wrapper):** SKIP (loop.py ist der neue Einstiegspunkt).

## M-296 — PhaseState-Integration in loop.py (2026-10-24)

run_pipeline_loop nutzt PhaseState als persistente Task-Quelle
mit vollstaendigem Plan-Checkpoint (tasks + tests + akz).
Resume-faehig: Planner wird bei vorhandenem PhaseState
uebersprungen. main() erzeugt PhaseState (load). 2 neue Tests
(test_loop_uses_phase_state, test_loop_resume_nach_unterbrechung).

Baseline: 1293 -> 1295.

## M-298 — Echt-Test + Loop-Fixes (2026-10-24)

Loop laeuft Ende-zu-Ende im echten Zielprojekt (security-ai).
10 Commits, Baseline 1290 -> 1297.

| Commit | Titel | Zweck |
|---|---|---|
| 28c1e1c | feat(loop): loop_fallback-Audit | HR-R9: Fallback sichtbar |
| 4e1a72f | feat(loop): CLI-Einstieg | main() mit argparse |
| bd74558 | feat(loop): main() erzeugt RunState | Kein Fallback mehr |
| e008aed | fix(loop): 3 ruff-Regression | I001 + S110/BLE001 |
| d0ca166 | feat(builder+loop): on-demand Zieldatei | Profi-Ansatz, Post-Apply |
| eecd15a | fix(builder): key_files dict vs str | TypeError-Fix |

Vorangegangene Commits (M-295/M-296):
  061667a, 4e1a72f, 51ba780, 4d6a5b7, df71204

**Echt-Test-Ergebnis (security-ai, 2026-10-24, HEAD eecd15a):**
- loop_fallback: 0 (Delta 0)
- loop_task_start: +1, loop_task_ok: +1
- loop_patch_updated: +1 (erster erfolgreicher Patch)
- loop_erfolg: +1, loop_human_gate_approved: +1
- README.md: +2 Zeilen ("Loop-Test 2026-10-24")
- Werkstatt-Baseline: 1297/13/8/6/162 unveraendert.

**Damit bewiesen:** Der Loop laeuft Ende-zu-Ende im echten
Zielprojekt. Explorer, Planner, Builder, Reviewer, Human-Gate
greifen zusammen. Der Builder schreibt tatsaechlich.

**Profi-Muster (recherchiert, bestaetigt):**
- Explorer = Wegweiser (key_files), nicht Inhalt.
- Builder liest Zieldatei on-demand (max 5 Dateien).
- Post-Apply-Verifikation (new_str in target.read_text()).
- old_string_not_found -> Reflection (nicht stumm weiter).
- init_new-Fallback bei plan_ok=True (M-298b-Realbug).

**Baseline:** 1297.

## M-306-RERUN-5 bis M-317 — Loop-Komplexitaet (2026-10-24)

Reihe von Echt-Tests und Fixes fuer Loop-Komplexitaet,
Reviewer-Blindheit, Fallback-Haenger und Idempotenz.

### Commits (chronologisch, 6aa1e78..HEAD)

| SHA | Titel | Zweck |
|---|---|---|
| 595b8e7 | feat(loop): Phasen-Hierarchie + phase_state im Prompt + Resume (M-310) | planner liest phase_state, resume_failed |
| 7fbd883 | docs: M-312 + M-313 als Merkposten | Architektur + Projektstruktur geplant |
| b7b5e34 | fix(reviewer+loop): untracked-Diff + Reflection-Kontext (M-314) | Reviewer sah neue Dateien nicht |
| 4102c8e | fix(loop): Fallback fail-closed statt pytest/ruff (M-315) | Fallback rief volle Suite -> 10-Min-Haenger |
| 549f20f | feat(builder+loop): Idempotenz-Check (M-316) | Fail-open bei update-Tasks |
| (neu) | fix(builder): action=read/create/update (M-317) | Idempotenz nur bei create |

### M-306-RERUN-5 (2026-10-24): Erster echter Code-Lauf

**Aufgabe:** `core/checks/__init__.py` mit `check_port(port: int) -> bool` + Tests.

**Ergebnis:**
- Planner: 5 Tasks (2 read-only + 1 write + 2 weitere).
- Builder: 2 neue Dateien (`core/checks/__init__.py`,
  `tests/unit/test_checks.py`).
- Tests: 3 passed.
- Reviewer: rejected, bugs=2 — "Datei fehlt im Diff".
- Loop-RC: 1 (fail-closed nach Reflection).

**Befund:** Reviewer sah untracked-Dateien nicht
(`git diff HEAD`).

### M-306-RERUN-6/7 (2026-10-24): Fallback-Haenger

**Befund 1 (RERUN-6):** Loop blockierte 10+ Min in
`_verify_patches`. Ursache: `verify.json` fehlte
(durch M-310-Aufraeumen `rm -rf .werkstatt/`
geloescht). Fallback rief `pytest -q` (volle Suite).

**Fix (M-315):** `verify.json` neu angelegt +
Fallback fail-closed auf `py_compile`.

**Befund 2 (RERUN-7):** 3/5 Tasks gruen, Code + Tests
funktionieren (Reviewer approved, 21 Tests gruen),
aber t4 "tests schreiben" findet nichts zu tun
(`builder_keine_patches`). Ursache: t3 hat in EINEM
LLM-Call BEIDE Dateien erstellt.

**Fix (M-316):** Idempotenz-Check (py_compile) bei
existierender Zieldatei.

### M-306-RERUN-8 (2026-10-24): M-317 Fail-open

**Aufgabe:** `check_port_range` hinzufuegen (update-Task).

**Ergebnis:**
- t3 "check_port_range implementieren":
  `builder_nichts_zu_tun` (Datei syntaktisch ok,
  aber Funktion fehlt).
- Reviewer: rejected, bugs=2 — "check_port_range fehlt".
- Loop-RC: 1 (fail-closed nach Reflection).

**Befund:** py_compile prueft Syntax, nicht Content.
Bei update-Tasks ist py_compile immer ok ->
fail-open.

**Fix (M-317):** action unterscheidet read/create/
update. Idempotenz-Check NUR bei create.

### Wirkende Fixes (M-310..M-317)

- **M-310:** Phasen-Hierarchie (parent_id) + Planner
  liest phase_state + resume_failed.
- **M-314:** Reviewer sieht untracked-Dateien
  (`git ls-files --others`).
- **M-315:** Fallback fail-closed (py_compile) statt
  pytest/ruff.
- **M-316:** Idempotenz-Check via py_compile.
- **M-317:** action read/create/update, Idempotenz
  nur bei create.

### Chef-Mandat D (Echt-Test security-ai, Original)

**Status:** TEILWEISE. Loop baut funktionierenden
Code, Tests gruen, Reviewer bestaetigt Code
(RERUN-7). Vollstaendig nach RERUN-9 (update-Task
mit M-317-Fix).

### Test-Bilanz

Baseline 1337 -> 1345 (M-310..M-317).


---

## M-322 bis M-343c — Loop-Haertung (2026-10-24)

22 strukturelle Fixes fuer den Loop-Neubau. Ziel: Der Loop
soll echte Phasen-Aufgaben Ende-zu-Ende loesen, ohne
fail-open und ohne halluzinierte Builder-Patches.

### Commits (chronologisch)

| SHA | Titel | Zweck |
|---|---|---|
| `3f615af` | feat(verify): Platzhalter, Erfolgs-Audit, phase_end (M-322) | {changed_files}-Platzhalter |
| `8f31fdf` | chore(verify): verify.json mit changed-scope | Zielprojekt-Contract |
| `3abe09b` | fix(loop): Reflection im Zielprojekt-Kontext (M-326) | git apply im Zielprojekt |
| `3abb3fb` | fix(loop): Reflection-Patch anwendbar (M-328) | Patch-Pfad prozess-sicher |
| `f8becb8` | fix(loop): Reflection nutzt Builder (M-329) | search/replace statt git apply |
| `d504c77` | feat(loop): Hooks in Reflection (M-330) | pre_tool_use/post_tool_use/simplify |
| `b9aea97` | fix(gate): quality_gate prueft failed (M-331) | Fail-closed Gate |
| `a8db21c` | test(gate): Fail-closed-Tests (M-331b) | 3 Tests |
| `4dc6a86` | feat(builder): keine halluzinierten Imports (M-333) | Import-Regeln + Projekt-Imports |
| `42671d2` | feat(hooks): pre_tool_use prueft Imports (M-334a) | Deterministisch |
| `fee2bb6` | refactor(hooks): post_tool_use entfernt (M-334b) | Prueft falsches Projekt |
| `87c7ed8` | feat(builder): task_files aus Planner priorisieren (M-335) | M-317-Feature verdrahtet |
| `74cc816` | fix(builder): Ordner in task_files aufloesen (M-336) | core/checks/ -> __init__.py |
| `e005513` | feat(builder): strukturelle Begrenzung (M-337) | Zieldatei + action erzwungen |
| `5f4e500` | fix(explorer+planner+builder): Kontext-Begrenzung (M-337-b/c/d) | Strukturelle Filter |
| `badb75d` | fix(verify): py_compile nur auf .py-Dateien (M-340) | {changed_py_files} |
| `8a71eb0` | fix(loop): pytest ist das letzte Wort (M-343c) | Reviewer-Reject ignorieren bei pytest-gruen |

### Beweis: RERUN-23 und RERUN-24

Beide Läufe: **Loop-RC=0**, 7/7 Tasks, 4 Phasen.
- RERUN-23: `core/checks/__init__.py` +115, 53 Tests grün.
- RERUN-24: `core/checks/__init__.py` +85/-25, 53 Tests grün.

### Baseline

VOR: 1367/13/8/6/162.
NACH: 1401/13/8/6/162.

### Offen

- M-323b: Phasen-Checkpoints (`phase_end` pro Phase).
- M-341: Explorer überspringen bei `task_files`.
- M-344: `PROGRESS.md` mit Phasen-Header.


## M-352..M-360 (Loop-Durchbruch, 2026-10-24)

- **M-352** (a5b986a): Idempotenz NUR bei create + Datei existiert.
  M-318 war zu locker. Tests angepasst.
- **M-353** (a5b986a): Rollback auf sauberen Tree (M-356 korrigiert
  die Semantik).
- **M-355** (b844ab8): Loop-Idempotenz-Check entfernt. Builder
  entscheidet.
- **M-355b** (403823d): run_builder=False -> sofort return 1.
  Kein 45s-Durchfall mehr.
- **M-356** (b844ab8): Rollback immer auf start-HEAD.
- **M-357** (9b31ec8): _run_with_progress re-raised Exceptions ->
  jetzt False, damit der Fehlerpfad greift.
- **M-358/M-358b** (9b31ec8): Footer mit echten Task-Zahlen aus
  state.tasks_ok_counter.
- **M-359** (9b31ec8): Reviewer-Reject + pytest gruen reicht nicht
  mehr, wenn kein Patch angewendet wurde. Fail-closed.
- **M-360** (f4e45ed): create + Datei fehlt -> Zieldatei aus
  task_files, LLM legt sie an.

**Beweis:** RERUN-38, 8/8 Tasks, LOOP_RC=0, echte Aenderung
(harness/audit/writer.py, Owner-Check). Zielprojekt committed
2a0a284.

## M-338-Fix..M-385 (Skillsystem, 2026-10-25)

Der Loop hat jetzt ein vollstaendiges Skillsystem mit
deterministischer Messung. RERUN-48 ist der erste
vollstaendig erfolgreiche Lauf.

- **M-338-Fix:** Explorer-Prompt: "Messe. Rate nicht."
- **M-373:** Explorer-Messung deterministisch (`_messen()`,
  `_extract_dateien()`).
- **M-374:** SkillLoader (`werkstatt/skills.py`) + Tool-Klassen
  (`werkstatt/tools.py`) + Meta-Skill `using-werkstatt`.
- **M-375:** Planner liest `state.explorer_context`.
- **M-376:** Explorer-Dateien Pflicht im Planner
  (`<measured_files>` + `<pflicht>` + `<erinnerung>`).
- **M-377:** Live-Spinner idempotent (kein LiveError).
- **M-378:** `ruff_changed`-Stage in `verify.json`.
- **M-380:** Reviewer ignoriert Loop-Doku.
- **M-381:** patch-format-Skill: `# noqa` nur entfernen, wenn
  Code nicht absichtlich ist.
- **M-382:** `_get_git_diff` schliesst `PROGRESS.md` aus.
- **M-383:** Builder-Reflection: bei RUF100 `# noqa` BEHALTEN.
- **M-384:** Reviewer STRIKT: PROGRESS.md nicht bewerten.
- **M-385:** `RUF100` in `per-file-ignores` fuer Tests
  (DTZ-Entfernung in Ruff 0.17).

**Beweis:** RERUN-48, 1/1 Tasks, LOOP_RC=0, ruff 1->0.
Zielprojekt committed `c0216d2`.
