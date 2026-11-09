# Fortschritt — Werkstatt

Append-only. Was hier steht, ist erledigt. Offene Punkte: `docs/STATUS.md`.


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


## M-441..M-476 (ADaPT, Doku, 2026-10-25)

Der Loop ist nach 30+ Fixes Ende-zu-Ende gruen.
RERUN-80: ChangeApplier.apply/rollback implementiert (237 Zeilen),
6/6 Tasks approved, LOOP_RC=0.

### Loop-Architektur

- **M-441:** Divergenz-Check (`loop_reviewer_divergenz`).
- **M-442:** Architect-Modell Env-Var (`WERKSTATT_ARCHITECT_MODEL`).
- **M-443:** venv-Python (`_venv_env`, `_resolve_venv_cmd`).
- **M-444:** Import-Validierung Modul (`_validate_imports_in_patch`).
- **M-444b:** Symbol-Validierung + Feedback-Loop.
- **M-444c:** Ganzer Patch (old_string + new_string).
- **M-445:** Reasoning-Architect (`deepseek-reasoner`).
- **M-446:** Architect-Prompt ohne Skills (kein DSML).
- **M-447:** Architect `max_tokens=16000`.
- **M-448:** Reviewer Diff-Limit 500k.
- **M-449:** Tests out-of-scope (Architect beschreibt keine Tests).
- **M-450:** Leerer Architect-Abschnitt -> kein Patch.
- **M-451:** stdlib Top-Level + Cross-File-Importe.
- **M-453:** Architect immer + Planner-Split (architect_start/ende).
- **M-454:** "so viele Sub-Tasks wie noetig" (statt 3-5).
- **M-455:** `_with_spinner` (Architect, Planner-Split, Builder, Reviewer).
- **M-456:** Render-API (`log_line`, `task_started`, `task_done`, `summary`).
- **M-458:** Architect-Prosa im Panel (`state.architect_prosa`).
- **M-459:** Reviewer prueft Task-Description, nicht Gesamtaufgabe.
- **M-460:** Architect-Zitat programmatisch (Marker).
- **M-461:** `_extrahiere_prosa_abschnitt` (woertliche Marker).
- **M-462:** Architect liefert numerierte Schritte.
- **M-463:** Robuste Marker-Suche (Backticks, 800-Zeichen-Limit).
- **M-464:** Marker max 3 Schritte / 800 Zeichen.
- **M-465:** Planner-Split `max_tokens=8000`.
- **M-466:** Builder-Feedback (Reviewer-Bugs im Prompt).
- **M-467:** ruff --fix + Circuit Breaker (`loop_reflection_stagnation`).
- **M-468:** Fallback auf 800 Zeichen.
- **M-469:** Rekursive Zerlegung (ADaPT).
- **M-470:** Schritt-Anzahl-Pruefung.
- **M-471:** Bullets zaehlen zur Komplexitaet.
- **M-472:** ADaPT On-Demand-Zerlegung (`_split_task_on_demand`).
- **M-473:** `while`-Loop statt `for` (Sub-Tasks werden gebaut).
- **M-474:** ADaPT bei `reviewer_high_bug_fail_closed`.
- **M-475:** `get_next_task` liefert nur `pending`.
- **M-476:** `phase_end` nach `human_gate` + `verify.json` fester Command.

### RERUN-Ergebnisse

- **RERUN-65:** 3/7 Tasks, Reviewer prueft Gesamtaufgabe.
- **RERUN-66:** 3/7 Tasks, `handler(change)` statt `handler.backup(change)`.
- **RERUN-67:** 1 Task, Planner-Split JSON abgeschnitten.
- **RERUN-68:** 2/12 Tasks, Reviewer prueft Tasks 5-20.
- **RERUN-69:** 5/10 Tasks, desc_len=3680 fuer t6.
- **RERUN-70:** 1 Task, `planner_split_json_fehler`.
- **RERUN-71:** 2/9 Tasks, `register_handler` prueft nur 2 Methoden.
- **RERUN-72:** 4/9 Tasks, `rollback` High-Bug.
- **RERUN-73:** 1/10 Tasks, `S110`/`BLE001` Ruff-Fehler.
- **RERUN-74:** 8 Tasks, `t2` desc_len=10373.
- **RERUN-75:** 8 Tasks, `t5` 9 Unterpunkte.
- **RERUN-76:** 9 Tasks, `t5` 5 Schritte.
- **RERUN-77:** 6 Tasks, ADaPT (`Split-t3`) aber Loop springt zu `t4`.
- **RERUN-78:** 4/9 Tasks, ADaPT (`Split-t5`) aber Loop haengt.
- **RERUN-79:** Endlosschleife (26+ Tasks, `Split-t1` immer wieder).
- **RERUN-80:** 6/6 Tasks approved, LOOP_RC=0. ChangeApplier gebaut.

### Baseline

- **Tests:** 1448 passed (Baseline 1448).
- **Ruff:** 13 errors (Baseline 13).
- **Mypy:** 11 errors (Baseline 11).
- **AST:** 6 passed.
- **Katalog:** 162.

## 2026-10-29 — Gold-Umbau + P0/P1 (K19 erledigt)

### Gold-Umbau (Commit `2c4703d`)

- **Architect-Prosa:** freie Prosa mit `## <pfad>`-Ueberschriften statt
  Tool-Use-Loop.
- **Planner-Split:** `_zerlege_in_sub_tasks` (JSON) zerlegt in Tasks.
- **Scout-Agent:** `_baue_api_index` (AST-basiert, deterministisch),
  `_format_api_index_for_prompt`, `_finde_api`, `_run_scout`,
  Widerspruchs-Check (API-Index vs. Auftrag).
- **Prompt-Audit (P0-P3):** `_BUILDER_SCHNITTSTELLE`,
  `_REVIEWER_SCHNITTSTELLE`, `_SCOUT_NACHFOLGER_BLOCK`,
  `## GOLD: SCOUT-KONTEXT`, `PLANNER_SYSTEM`-else-Zweig entfernt.
- **Reviewer Diff-Check (P0):** prueft jede `-`-Zeile gegen Zieldatei;
  HIGH-Bug bei entferntem Aufruf, ueberschriebener Funktion, erfundener API.
- **Import-Validierung (`996d616`):** `_validate_imports_in_patch` im
  klassischen Builder-Pfad.

### P0/P1 (K19) — Commit `aa7881f` + `c13bb8a`

**K19** aus `OFFENE-BLOECKE.md`:
*"Builder setzt Task-Anforderungen nur teilweise um (Builder sinngemaess,
Reviewer woertlich). Fix-Kandidaten: Builder-Prompt-Praezision / Checkliste."*

**Fix-Ansatz (deterministisch, nicht Prompt-Bastelei):**

- **`_segmentiere_nach_pfad(prosa)`** (`aa7881f`, planner.py):
  zerlegt Architect-Prosa an `## <pfad>`-Ueberschriften. Fallback in
  `_zerlege_in_sub_tasks` und `_llm_split_einzel_task`, wenn
  `architect_start` fehlt. Ersetzt P0 "`PLANNER_SPLIT_SYSTEM` an
  Gold-Format anpassen" — die Prompt-Aenderung ist nicht mehr noetig.
- **`## FUNKTION-WAHL`** in `BUILDER_SYSTEM` (`aa7881f`): waehlt die
  in der Task genannte Funktion, nicht die "aehnlichste". Explizit
  fuer `_section_timeline` vs. `_section_timeline_entries`.
- **`## SEMANTIK-CHECK`** in `REVIEWER_SYSTEM` (`aa7881f`): HIGH-Bug,
  wenn der Diff eine andere Funktion nutzt, als die Task nennt, oder
  eine Funktion ohne Task-Auftrag aendert.
- **`_filtere_auf_funktionen(abschnitt, task_text)`** (`c13bb8a`,
  builder.py): schneidet den Architect-Abschnitt auf die in der Task
  genannten Funktionen zu, bevor er in den Builder-Prompt geht.
  Ohne diese Funktion sah der Builder alle Funktionen aus dem
  Datei-Abschnitt und baute sie um — auch die, die die Task nicht
  nannte. Mit Filter sieht er nur die Zielfunktion.
- **Aufrufer** (`c13bb8a`): `_architect_abschnitt(..., task_text=...)`
  in `_build_patches_fuer_datei` (Hauptaufruf und Gold-Fallback).

### RERUN-Ergebnis (2026-10-29 20:16)

- **Aufgabe:** `_section_timeline_entries` absteigend nach Score
  sortieren (nur diese Funktion, nur `routes_state.py`).
- **Plan:** 1 Task / 1 Datei.
- **Builder:** 1.2s, 1 Patch.
- **Reviewer:** 1.7s, **approved** (1. Durchlauf, keine Reflection).
- **Task-Status:** **1/1 approved**, LOOP_RC=0.
- **Patch:** 5 Zeilen (`entries = sorted(..., reverse=True)`),
  **kein** Umbau von `_format_timeline_ts`, **kein** `ts_display`/
  `ts_iso`. `_filtere_auf_funktionen` hat gegriffen.
- **Zielprojekt-Commits:** `81f74e7` (CSS+JS, Altlast vom Handoff),
  `7a46d5e` (Sortierung).

### Baseline (2026-10-29 nach P0/P1)

- **Tests:** 1622 passed, 5 skipped.
- **Ruff:** planner.py 3, builder.py 2, reviewer.py 0 (Baseline 5).
- **RERUN-Erfolgsquote:** 1/1 (der Test-Task).

---

---

## 2026-10-29 — M-487 (Human-Gate committet)

### Was

Der Loop committet nach explizitem `j` am Human-Gate **selbst**.
Vorher: `✓ LOOP ERFOLGREICH` gemeldet, aber Aenderungen blieben
uncommittet im Zielprojekt liegen (Vorschlagsgenerator).

### Fix (Commit `31c6ff3`)

- Neue Funktion `_committe_zielprojekt(state)` in `werkstatt/loop.py`:
  1. `git status --porcelain` im Zielprojekt.
  2. Bei Aenderungen: `git add -A`.
  3. `git commit` mit Autorschaft `state.git_author_name` /
     `state.git_author_email` (Default `builder <builder@security-ai.local>`).
  4. `git rev-parse HEAD` fuer den SHA.
  Fail-closed: Bei Git-Fehler `(False, fehlertext)`.
- `_human_gate`-`j`-Zweig ruft `_committe_zielprojekt` auf.
  Bei Fehler -> `return 1` (Loop bricht ab, kein falsches `✓`).
- **Nur bei explizitem `j`.** Auto-Approve (`require_human_approval=false`,
  `WERKSTATT_IN_TEST=1`) committet **nicht**.
- 4 Audit-Events: `loop_human_gate_committed` (Erfolg),
  `loop_human_gate_commit_skip` (nichts zu tun),
  `loop_human_gate_commit_fehler` (Git-Fehler),
  `loop_human_gate_commit_abort` (Aufrufer entscheidet Abbruch).

### Betriebs-Voraussetzung (Zielprojekt)

`.git/` muss vom Loop-User (`security-ai`) beschreibbar sein.
Konkret:

- `.git/` auf `builder:builder`, setgid `drwxrwsr-x` (neue Dateien
  erben Gruppe `builder`).
- `security-ai` ist in Gruppe `builder`.
- Keine `root:root`-Dateien mehr in `.git/` — vorher per
  `find .git -user root -exec chown builder:builder {} +` bereinigt.

Ohne diese Rechte failt der Commit mit `git add rc=128: index.lock
Keine Berechtigung`. Der Loop meldet dann `✗ LOOP FEHLGESCHLAGEN`
(fail-closed, kein falsches `✓`).

### RERUN-Beleg (2026-10-29 20:36)

- Aufgabe: Docstring-Marker in `_timeline_get` (`routes_state.py`).
- 1 Task / 1 Datei.
- Builder 1.4s, Reviewer 1.4s, Phase-Review 1.3s.
- Human-Gate `j` -> `Commit: 4e860c3`, `✓ LOOP ERFOLGREICH`.
- Zielprojekt-Commit `4e860c3` **automatisch**, ohne manuellen
  Eingriff, mit Message `chore(werkstatt): … RERUN (M-487,
  human_gate committet selbst).`

### Offen

- `status: completed` in `phase_state.py` wird weiterhin **nicht**
  gesetzt (gehoert zu M-488).
- `git push` nach origin bleibt manuell (kein Teil von M-487).

---

---

## 2026-10-30 — MESS-1 + planner-Cleanup + pipeline._KATALOG_SOLL

### MESS-1 — Prompt-Laengen messbar (`b3b9511`)

- `LLMReply` (state.py) um `system_len: int`, `user_len: int` erweitert.
- `ask_llm` (agent.py): alle 7 `return LLMReply(...)`-Pfade fuellen
  die Laengen; zusaetzlich `audit("llm_call", {agent, model,
  system_len, user_len, max_tokens})`, wenn `state` gesetzt.
- `llm_call` in `_AUDIT_KINDS_BEKANNT` (audit.py) + `_KATALOG_SOLL`
  162 -> 163 (pipeline.py).
- **Prompt-Dump (optional):** `WERKSTATT_PROMPT_DUMP=1` schreibt pro
  LLM-Call die wortwoertlichen System- und User-Prompts nach
  `/tmp/werkstatt-prompts/<agent>_<ts>_<suffix>_{system,user,meta}.txt`.
  Kein Effekt, wenn die Env-Var nicht gesetzt ist.

### planner.py-Cleanup (`c9821bb`)

- Toten Block in `_planner_system` entfernt (Zeilen 881-973,
  93 Zeilen): `<doku_verbot>`, `<datei_pruefung>`, `<task_groesse>`,
  `<tools>`, Skill-Laden (`load_all_skills`, `load_skill_by_name`),
  `<erinnerung>`. Wurde nie erreicht (`return` davor).
- `PLANNER_SYSTEM` deprecatet (6-Zeilen-Kommentar, Inhalt
  unveraendert). Grund: `_planner_system` gibt nur `ARCHITECT_SYSTEM`
  zurueck; `PLANNER_SYSTEM` wird nicht mehr ans LLM gesendet. Bleibt
  aber im Modul, weil `test_builder_agent.py::test_planner_prompt_m339`
  und `test_loop.py::test_planner_prompt_phasen_pflicht` den Inhalt
  pruefen (Regressionsschutz bis Planner-Split umgestellt).
- Unbenutzte Imports entfernt: `load_skill_by_name`, `run_readonly`,
  `load_all_skills`. Ruff planner.py 3 -> 1.

### Ruff-Baseline (Stand 2026-10-30)

| Datei | Errors | Delta |
|---|---|---|
| loop.py | 7 | 0 |
| planner.py | 1 | **-2** |
| builder.py | 2 | 0 (SIM102, SIM103 alt) |
| reviewer.py | 0 | 0 |
| explorer.py | 0 | 0 |
| pipeline.py | 2 | +2 (neu erfasst, PIE810 + F841) |
| **Gesamt** | **12** | 0 |

`pipeline.py` ist in der Baseline **neu erfasst** — vorher nicht
gemessen, weil als "zu loeschen" gefuehrt. Siehe `M-345`.

### Tests

- 1622 passed, 5 skipped (unveraendert).

### Was aufgefallen ist

- **Commit `b3b9511` (MESS-1) enthaelt auch `pipeline._KATALOG_SOLL`
  und `planner.py`-Cleanup** — der `git reset --soft` hatte alle
  Aenderungen im Index, `git add` pro Datei hat die anderen nicht
  entfernt. Funktional korrekt, Commit-Message unvollstaendig.
  Beim naechsten Mal: `git reset HEAD` + `git add` pro Commit-Gruppe.
- **`pipeline.py`-Migration (M-345) ist Tages- bis Wochenaufgabe,
  nicht "Block".** 146 Symbole, 182 Tests.

---

---

## 2026-10-30 — Loop-Neubau (pipeline.py entfernt)

### Was

Der Monolith `pipeline.py` (11.119 Zeilen) und die alte
`pipeline`-Test-Suite (~28.000 Zeilen) sind entfernt. Der Loop
laeuft ausschliesslich ueber `werkstatt/*.py`.

### Commits

- `513ab55` — `build_system_prompt` ohne `mit_anti_patterns`-Parameter.
- `a9abe5b` — 2 `mit_anti_patterns`-Tests entfernt.
- `0bcc732` — 5 Test-Dateien + Anti-Pattern-Hook + Katalog entfernt (17.473 Z.).
- `f163f33` — `patch(pipeline.*)`-Aufrufe entfernt (wirkungslos).
- `07a4de6` — `pipeline.py` + 3 Tests + Anti-Pattern-Code (12.401 Z.).

### Entfernt

| Datei | Zeilen | Grund |
|---|---|---|
| `pipeline.py` | 11.119 | Monolith, produktiv tot |
| `tests/test_pipeline.py` | 11.377 | testet `pipeline`-Interna |
| `tests/test_pipeline_integration.py` | 1.958 | dito |
| `tests/test_phase.py` | 2.637 | testet `pipeline`-Phasen |
| `tests/test_planner.py` | 649 | 70% `pipeline`-Planner-Logik |
| `tests/test_anti_patterns.py` | 549 | Anti-Pattern tot |
| `tests/test_hooks_anti_patterns.py` | 58 | Anti-Pattern tot |
| `tests/test_audit_kinds.py` | 268 | testet `pipeline.py` |
| `tests/test_projekt_schema.py` | 227 | testet `pipeline.pruefe_projekt_yaml` |
| `hooks/anti_patterns.py` | ~90 | kein Aufrufer |
| `anti-patterns/katalog.yaml` | 22 KB | kein Konsument |
| `anti-patterns/README.md` | 4 KB | dito |
| `werkstatt/agent.py:_anti_pattern_block` | 69 | kein Aufrufer |
| `werkstatt/audit.py:_ap_audit_haeufigkeit` | 26 | kein Aufrufer |
| `tests/conftest.py:ap_block_inprocess` | 39 | testet toten Code |

### Neue Baseline

- **Tests:** 432 passed, 5 skipped (vorher: 1620).
- **Ruff gesamt:** 13 Errors ueber alle `werkstatt/*.py`.
- **Test-Dateien:** 60 (vorher: 68).

### Was jetzt kommt

1. **Loop-Weg-Tests** — neue Test-Suite als Spec, nicht als Historie:
   Explorer, Scout, Architect, Planner-Split, Builder, Reviewer,
   Human-Gate, Phasen, Fail-Closed, Redaction.
2. **Security-Audit** — wenn der Loop produktiv ist.
3. **Push** — 31 Commits.

---


## 2026-10-31T20:19:05+00:00 -- OP-034: pytest_regression am phase_end
- **Status:** done
- **Beleg:** Commits f37d5ae, ee95412, 7a4ba7a, 19098e4. pytest_regression-Stage in verify.json (Werkstatt, Template, security-ai). phase=phase_end (1x pro Loop statt pro Task). Per-Stage timeout konfigurierbar (default 300s, security-ai 900s).

## 2026-10-31T20:19:05+00:00 -- OP-036: Duplikat-Check in progress.append
- **Status:** done
- **Beleg:** Commit a965810. progress.append prueft Signatur (name, status, info) vor dem Schreiben. Root-Cause (mehrfache _task_ende-Aufrufe) bleibt als OP-040 offen.
## 2026-10-31T21:58:41+00:00 -- OP-040: Idempotenz-Guard in _task_ende
- **Status:** done
- **Beleg:** Commit ca9c010. _task_ende prueft vor dem Schreiben den Task-Status (done/failed -> skip + Audit-Event 'loop_task_ende_skip'). Sicherheitsnetz fuer den Live-Test-5-Befund (patch_write_failed + reviewer_rejected_no_patch in derselben Sekunde). 5 neue Tests. Root-Cause-Aufraeumen in pipeline_phases.py (continue nach jedem Fehlerpfad) bleibt als OP-006-Folge offen.
## 2026-11-01T09:13:25+00:00 -- Abschluss 2026-11-01: 6 OPs erledigt

### OP-038: Commit-Message nach Conventional Commits
- **Status:** done

### OP-042: glossary.md entstaubt
- **Status:** done

### OP-043: HANDOFF-BASELINE.md als historisch markiert
- **Status:** done

### OP-047: Tote Doku-Links repariert
- **Status:** done

### OP-053: git_author aus Manifest
- **Status:** done
- **Beleg:** Commit 1407739. loop.py liest projects/<name>.yaml.git_author.
## 2026-11-01T09:14:43+00:00 -- OP-044: docs/CONVENTIONS.md entstauben
- **Status:** done
- **Beleg:** Commit 69a58ca.
- **Aenderungen:** 9 Ersetzungen (KONVENTION.md -> CONVENTIONS.md,
  ARCHITEKTUR.md -> ARCHITECTURE.md, OFFENE-BLOECKE.md -> STATUS.md,
  ERLEDIGT.md -> PROGRESS.md, pipeline.py -> werkstatt/loop.py,
  Referenztabelle auf 2026-10-31 aktualisiert).
## 2026-11-01T09:29:21+00:00 -- OP-054: auftrag_bereits_erfuellt-False-Positive
- **Status:** done
- **Beleg:** Commit b795e14.
- **Befund:** Live-Test 5 v2 (security-ai): t2 (_insert_device_history
  mit Duplikatschutz) wurde als done via auftrag_bereits_erfuellt
  markiert, obwohl der Ist-Zustand eine doppelte Methodendefinition
  hatte.
- **Fix:** no_effect-Filter in _build_patches_fuer_datei prueft vor
  Flag-Setzen, ob old_string im Datei-Ist-Zustand mehrfach vorkommt.
  Bei Duplikat-Anker: kein Flag, Audit-Event builder_patch_duplicate_anchor,
  Builder gibt False zurueck -> Task failed.
- **Neuer Audit-Kind:** builder_patch_duplicate_anchor.
- **Tests:** 4 neue in tests/test_builder_duplicate_anchor.py.

## 2026-11-01T12:28:16+00:00 -- OP-048: Deterministischer Doku-Nachzug Ebene 1
- **Status:** done
- **Info:** Commit 73f3156. _committe_zielprojekt ruft _status_md_op_entfernen + _progress_op_done + _delete_zone_op_append, wenn WERKSTATT_DOKU_NACHZUG=1 und Aufgabe OP-NNN nennt. Skip bei fehlendem OP-NNN, fehlender STATUS.md oder fehlendem Block (Audit doku_nachzug_skip).

## 2026-11-01T12:28:16+00:00 -- OP-055: STATUS.md Kennzahlen deterministisch (HEAD)
- **Status:** done
- **Info:** Commit 73f3156. _update_kennzahlen ersetzt HEAD-Zeile aus git rev-parse --short HEAD. Tests/ruff/mypy als Follow-up offen (blockiert von OP-039, pytest-Recollect ~30-60s/Loop-Lauf).

## 2026-11-01T12:28:16+00:00 -- OP-056: CHANGELOG.md aus Commit-Message
- **Status:** done
- **Info:** Commit 73f3156. _update_changelog fügt Zeile unter '## [Unreleased]' ein, nur wenn Datei existiert. Format: '- <OP-NNN>: <subject>'.

## 2026-11-01T12:28:16+00:00 -- OP-057: Architecture-Drift-Warnung
- **Status:** done
- **Info:** Commit 73f3156. _architecture_drift_check meldet audit('committer_architecture_drift') wenn .py neu/geloescht ohne docs/ARCHITECTURE.md-Aenderung. Kein Auto-Fix (Warnung).

## 2026-11-01T12:28:16+00:00 -- OP-058: ADR-Mini-Phase (partial)
- **Status:** done
- **Info:** Commit 73f3156. _adr_mini_phase in gates.py:_human_gate, NACH approve, VOR _committe_zielprojekt. Deterministisches Template (kein LLM-Client gefunden — Follow-up). WERKSTATT_ADR_MINI=1.


## 2026-11-01T14:49:09+00:00 -- OP-059: reviewer_rejected-False-Positive
- **Status:** done (partial)
- **Info:** Commit 05162e7. reflection.py: _diff_hash_for_state + false_positive-Erkennung im _applied==0-Block. Bei unveraendertem Diff vor/nach Builder, applied_count>0, leerem echten verify_errors und gruenem Verify: audit 'reviewer_stagnation_false_positive' + return True. pipeline_phases.py setzt _reflection_diff_hash vor Reflexion und ueberspringt den zweiten run_reviewer-Call, wenn state.reviewer_stagnation_false_positive gesetzt ist. Tests: tests/test_reviewer_false_positive.py (3 Faelle) + tests/test_reviewer_false_positive_aufrufer.py (2 Faelle), Baseline 40 passed. Abweichung zur Spec: Punkt 2 'human_review bei fehlendem deterministischen Check' nicht gebaut — bei rotem Verify bleibt es beim alten reflection-Pfad, kein false_positive. M-059-Nachtrag offen: human_review-Zweig + Human-Gate-Hinweistext (Spec-Punkt 3).

## 2026-11-01T15:04:43+00:00 -- OP-060a: Patch-Diagnose bei Nicht-Anwendung (Reflection)
- **Status:** done (partial)
- **Info:** Commit ce5939f. apply_patches.py: _diagnose_patch(content, old, new) liefert {grund, old_string_len, vorkommen} mit grund in {leer, kein_match, mehrdeutig, no_effect, ok}. _apply_patches_with_diagnose ist die neue Hauptfunktion (Rueckgabe (int, list[dict])), _apply_patches_with_hooks bleibt Wrapper fuer Rueckwaerts-Kompatibilitaet. reflection.py ruft diagnose-Variante und auditiert 'loop_reflection_patch_unwirksam' mit diagnosen-Liste. K30-Kompatibilitaet: bei kein_match zusaetzlich 'loop_patch_old_string_not_found' (bestehende Tests). Tests: tests/test_reflection_diagnose.py (10 Faelle). Baseline 1032 passed, 5 skipped. Spec-Abweichung: OP-060 Punkt 2 (human_review) und Punkt 3 (Duplikat-Anker-Regeneration) nicht gebaut — als OP-060b in STATUS.md.

## 2026-11-01T15:11:59+00:00 -- OP-061: builder_failed-Zustandsverwirrung (Task-Runner)
- **Status:** done
- **Info:** Commit 05bb2b2. Fix A (Pre-Reviewer-Patch-Fail): bei loop_patch_old_string_not_found vor fail _reflection_loop + auftrag_bereits_erfuellt-Flag + Verify pruefen. Bei gruenem Verify Task done via auftrag_bereits_erfuellt_pre_reviewer. Fix B (Builder-Fail): bei run_builder=False pruefen, ob prior done-Task dieselbe task_files[0]-Datei geschrieben hat + Verify gruen -> Task done via builder_patch_bereits_erfuellt. Neuer Audit-Kind builder_patch_bereits_erfuellt. Tests: tests/test_builder_failed_ohne_grund.py (4 Faelle). Baseline 1036 passed, 5 skipped. Live-Beleg OP-002b3 13:22 t2: Code war 2/3 korrekt (t1-Patch wirksam), Anzeige sagte 1/3 done, 2 failed. Nach Fix: t2 done via builder_patch_bereits_erfuellt.

## 2026-11-01T15:46:07+00:00 -- OP-059b: false_positive _hash_ref-Bedingung entfernt
- **Status:** done
- **Info:** Commit 1f83014. Loop-Validierung 15:16 OP-002b3 t2 zeigte Restluecke: mein OP-059-Fix (05162e7) pruefte _hash_nachher == _hash_ref und blockierte die false_positive-Erkennung, wenn Runde 1 tatsaechlich wirksam war (Hash geaendert) und Runde 2 idempotent ist (Hash vor==nach). Fix: _hash_ref-Bedingung entfernt. _hash_vorher == _hash_nachher + applied_vorher > 0 + leere echte errors + Verify gruen reichen als Idempotenz-Beweis. Test: test_false_positive_nach_wirksamer_erster_runde. Baseline 1037 passed, 5 skipped. Live-Beleg: Loop-Diff war produktionsreif (11 Tests gruen, als d611e2b in security-ai committet).

## 2026-11-01T17:06:52+00:00 -- Session-Ehrlichkeit: Fehldiagnose OP-062 korrigiert
- **Status:** done
- **Info:** Die urspruengliche OP-062-Anlage ('Reviewer-Payloads leer') war eine Fehldiagnose. Messung zeigt: die Audit-Payloads sind vollstaendig (4x reviewer_bug mit description/severity/file, 3x reviewer_phase_rejected mit bugs-Liste). Die Fehldiagnose entstand durch fehlerhafte Payload-Ausgabe in der Diagnose-Session (leere payload-Felder durch meine Extraktion, nicht durch den Code). Echte Befunde:
1. Redaction (`agent.py:98-99`) laeuft auf LLM-Prompts und anonymisiert IPs als `[IPV4]`. Der Phase-End-Reviewer sieht im Test-Code zwei verschiedene IPs als `[IPV4]` und `[IPV4]` — semantisch identisch. Er urteilt rational korrekt auf Basis falscher Eingabe: 'Test ruft zweimal dieselbe IP auf'. Der Test im Repo ist gruen. Neue OP-062a.
2. Der Human-Gate-Render zeigt nur Task-Status + Diff-Stat, nicht Scout-Findings, Reviewer-Bugs pro Task, Reflexions-Runden oder Phase-End-Review-Bugs. Neue OP-062b.
Narrativ-Korrektur: 'Loop baut produktionsreifen Code, nur Anzeige luegt' war falsch. Der Phase-End-Reviewer hat recht — er sieht nur falsche Eingabe. d611e2b (Loop-Diff) ist inhaltlich OK (Test gruen, Task-Reviewer-Bugs im finalen Diff behoben), aber der Commit-Text 'nur die Anzeige luegt' ist irrefuehrend. Kein Revert noetig, aber bei naechster Bearbeitung von d611e2b pruefen, ob alle Task-Reviewer-Bugs (insb. try/except-Reichweite) wirklich adressiert sind.

## 2026-11-01T17:18:17+00:00 -- OP-062a: redact-Parameter fuer Code-Pruef-LLMs
- **Status:** done
- **Info:** Commit HEAD. ask_llm bekommt redact: bool = True (Default Datenschutz-konservativ). Builder, Task-Reviewer und Phase-End-Reviewer rufen mit redact=False — sie pruefen Code semantisch und brauchen echte Werte. Private IPs (10/8, 172.16/12, 192.168/16, 127/8) werden auch bei redact=True nicht maskiert, oeffentliche IPs (1.1.1.1, 8.8.8.8) schon. Live-Beleg 15:16 OP-002b3: Phase-End-Reviewer sah '[IPV4]' und '[IPV4]', meldete 'Test ruft zweimal dieselbe IP auf', rejected 3x -> rc=1. Test im Repo war gruen. Tests: tests/test_reviewer_redaction.py (5 Faelle). Baseline 1042 passed, 5 skipped.

## 2026-11-01T17:21:50+00:00 -- OP-062b: Human-Gate zeigt Architect-Plan + Reviewer-Bugs + Reflexionen
- **Status:** done
- **Info:** Commit HEAD. gates.py: neue pure Funktion _human_gate_body(state) rendert aus state.architect_prosa, state.reviewer_bugs_history (letzte Runde) und state.reflection_history (Runde N, X Patches, Y Fehler, Z Bugs). _human_gate ruft sie auf und haengt den Block vor 'Aenderungen im Zielprojekt'. Leerer State -> leerer String. Scout-Marker '[atomarer Plan vom Scout]' wird als solcher gekennzeichnet. Live-Beleg 15:16: Mensch am Gate sah nur Task-Status + Diff-Stat, obwohl 4 reviewer_bugs, 2 Reflexions-Runden und 3 Phase-End-Rejects im Audit standen. Tests: tests/test_human_gate_render.py (5 Faelle). Baseline 1047 passed, 5 skipped.

## 2026-11-01T17:36:55+00:00 -- OP-062c: Human-Gate-Politur (partial)
- **Status:** done (partial)
- **Info:** Commit 83a0407. Drei Fixes: (1) Bug-Sync — _human_gate_body markiert History-Bugs als 'vermutlich behoben', wenn state.reviewer_bugs leer ist (letzter Call gruen); run_phase_end_review leert reviewer_bugs bei Approval. (2) Reflexions-Runden — reflection_history bekommt task_id-Feld, Render zeigt 't2 Runde 1' statt 'Runde 1'. (3) Hunk-Summary — neue Funktion _diff_hunk_summary extrahiert pro Datei die @@-Header. Tests: 4 neue in tests/test_human_gate_render.py. Baseline 1051 passed, 5 skipped. **Partial:** Hunk-Summary ist noch nicht in _human_gate verdrahtet (die Diff-Anzeige bei >2000 Zeichen zeigt weiter '(Diff zu gross)') — als OP-062d angelegt, weil die Verdrahtung subprocess-Mock-Test braucht. OP-062c macht nur den State/Render-Teil, OP-062d die Diff-Anzeige.

## 2026-11-01T17:38:10+00:00 -- OP-062d: Hunk-Summary im Human-Gate verdrahtet
- **Status:** done
- **Info:** Commit HEAD. _human_gate ruft bei Diff >2000 Zeichen _diff_hunk_summary auf, zeigt pro Datei die @@-Header statt nur '(Diff zu gross)'. Der Mensch am Gate sieht jetzt die Diff-Struktur direkt, ohne in die Shell zu wechseln. Test: test_human_gate_zeigt_hunk_summary_bei_grossem_diff (subprocess.run gemockt, input()->'j', panel_diff capture). Baseline 1052 passed, 5 skipped.

## 2026-11-01T17:40:48+00:00 -- OP-063: Loop-PROGRESS + Commit-Message-Qualitaet
- **Status:** done
- **Info:** Commit HEAD. Drei Fixes: (1) task_runner.py fuehrt _hat_op_nnn(state) ein; _task_ende skippt _progress.append bei OP-NNN (sonst 4 leere Task-Eintraege pro Multi-Task-Lauf). (2) committer.py: _committe_zielprojekt erkennt OP-NNN in Delete-Zone-Tabelle, wenn _status_md_op_entfernen fehlschlaegt (Body schon entfernt) — dann Retry von _progress_op_done mit Audit doku_nachzug_delete_zone_retry. (3) committer.py: neue _build_commit_subject(aufgabe, op_nnn) schneidet an Wortgrenze, OP-NNN als Praefix. Tests: tests/test_progress_loop_quality.py (4 Faelle). Baseline 1056 passed, 5 skipped.

## 2026-11-01T17:53:36+00:00 -- OP-062e: Human-Gate zeigt Nullfall klar
- **Status:** done
- **Info:** Commit HEAD. Drei Fixes: (1) _human_gate_body prueft state.auftrag_bereits_erfuellt und zeigt Block '## Erfuellt ohne Aenderung'. (2) _human_gate_body prueft state.phase_review_uebersprungen und zeigt '## Phase-End-Review (uebersprungen: <grund>)'. (3) pipeline_phases.py setzt bei keine_patches_alle_done das Flag. Tests: 3 neue in tests/test_human_gate_render.py. Baseline 1059 passed, 5 skipped. Live-Beleg 17:45 OP-002b3: 1/1 done, rc=0, keine Aenderungen — aber der Mensch sah keinen Grund.

## 2026-11-01T18:14:25+00:00 -- OP-063b: OP-NNN-Doppelung + Subject-Limit
- **Status:** done
- **Info:** Commit HEAD. Zwei Fixes: (1) _progress_op_done strippt doppelten OP-Praefix idempotent (vorher 'OP-004: OP-004:'). (2) _build_commit_subject rechnet OP-Praefix ins 60-Zeichen-Limit ein, damit Subject+Typ+Scope <= 72 bleiben. Tests: 2 neue in tests/test_progress_loop_quality.py. Baseline 1061 passed, 5 skipped. Live-Beleg 10799ed (17:58 OP-004).

## 2026-11-01T18:16:04+00:00 -- OP-062f: hart-Flag fuer verify.json-Stage
- **Status:** done
- **Info:** Commit HEAD. _stage_ist_hart akzeptiert dict (neben str). Optionales Feld 'hart': true ueberschreibt Prefix-Klassifikation. 'hart': false entschaerft NICHT (Prefix gilt weiter, Feld darf nur verschaerfen). Live-Beleg 17:58 OP-004: 'mypy_hart'.startswith('mypy') = True -> weich -> Stage-Fehler blockierte nicht. Tests: tests/test_verify_mypy_hart.py (4 Faelle). Baseline 1065 passed, 5 skipped. Naechster Schritt: security-ai/.werkstatt/verify.json bekommt eine harte mypy-Stage, dann OP-004 erneut im Loop bauen lassen.

## 2026-11-01T18:31:49+00:00 -- OP-062g: Scout-Pfad-Anzeige
- **Status:** done
- **Info:** Commit HEAD. pipeline_phases.py setzt state.scout_bereits_erfuellt=True bei Scout-Erkennung, gates.py _human_gate_body rendert '## Erfuellt ohne Aenderung (Scout)'. Live-Beleg Loop-6 18:25: Panel zeigte nur '(keine Aenderungen)' ohne Kontext. Test: test_human_gate_body_zeigt_scout_skip. Baseline 1071 passed.

## 2026-11-01T18:31:49+00:00 -- OP-060b: human_review-Status (partial)
- **Status:** partial
- **Info:** Commit HEAD. phase_state.mark_human_review() + _propagate_failed_to_parents ignoriert human_review-Kinder + _task_ende(human_review=True)-Parameter + Idempotenz-Guard. Tests: tests/test_human_review_status.py (3 Faelle). Nachtrag HEAD: _phase_tasks_loop ruft jetzt human_review bei spec_widerspruch_erkannt. **Rest:** _phase_finalize rc=2 + Human-Gate [~]-Render.

## 2026-11-01T18:36:07+00:00 -- OP-059c: Spec-Widerspruch-Heuristik
- **Status:** done
- **Info:** Commit HEAD. Neue Funktion _bug_text_deutet_spec_widerspruch prueft Bug-Texte auf Marker 'Task fordert/verlangt' + 'Der Diff macht'. Bei Treffer in beiden Stagnation-Abort-Pfaden: audit loop_reflection_spec_widerspruch + return True. Bei generischen Bugs: alter Pfad. Erster Fix-Ansatz (Bug-2x ohne Marker) verworfen, weil zu aggressiv. Tests: test_reflection_spec_widerspruch.py (2 Faelle). Live-Beleg Loop-5 18:20 OP-004. Baseline 1073 passed.

## 2026-11-01T18:44:36+00:00 -- OP-060b: human_review-Status (done)
- **Status:** done
- **Info:** Commit HEAD. Kompletter human_review-Status: phase_state.mark_human_review + _task_ende(human_review=True) + _propagate_failed_to_parents ignoriert human_review-Kinder + _phase_tasks_loop human_review=True bei spec_widerspruch_erkannt + _phase_finalize rc=2 + Human-Gate [~]-Render. Audit-Kind loop_human_review_offen. Tests: test_human_review_status.py (5 Faelle). Baseline 1075 passed. Loop-Stagnations-Ausweg komplett: OP-059c erkennt Spec-Widerspruch -> OP-060b setzt human_review -> rc=2 -> Mensch entscheidet.

## 2026-11-01T19:08:39+00:00 -- OP-064a: Sticky-Veto
- **Status:** done
- **Info:** Commit HEAD. phase_state.mark_vetoed + ist_vetoed. verdict orthogonal zu status (sonst Idempotenz-Guard-Konflikt). mark_done hebt Veto auf (Mensch). task_runner._task_ende: Veto-Guard -> mark_human_review statt mark_done bei vetoed. pipeline_phases._phase_tasks_loop: nach Reflection VOR False-Positive-Pfad pruefen, ob spec_widerspruch_erkannt -> mark_vetoed + human_review + Audit, kein 2. Reviewer-Call. Tests: tests/test_sticky_veto.py (4 Faelle, Test 4 echter Loop-Mock). Baseline 1087 passed. Live-Beleg Testrunde 3 (18:54 OP-004): Veto haette den type:ignore-Approval blockiert. Erster Baustein von OP-064 (Completion-Gate-Architektur). Naechste Bausteine: 064b (Antipattern-Scanner), 064c (StuckDetector), 064d (Red-to-Green), 064e (Spec-Pre-Flight), 064f (Feature-JSON).
## 2026-11-02T08:45:57+00:00 -- Neue Funktion _stage_anzahl in verify.py
- **Status:** done

## 2026-11-02T08:46:02+00:00 -- __all__ in verify.py ergaenzen
- **Status:** done

## 2026-11-02T08:46:19+00:00 -- Test test_stage_anzahl in test_loop.py
- **Status:** done

## 2026-11-02T08:48:11+00:00 -- Phase abgeschlossen: werkstatt
- **Status:** phase_ende
- **Info:** tasks_ok=3/3

## 2026-11-02T09:23:18+00:00 -- Docstring _verify_patches ergänzen
- **Status:** done

## 2026-11-02T09:23:52+00:00 -- Phase abgeschlossen: werkstatt
- **Status:** phase_ende
- **Info:** tasks_ok=1/1

## 2026-11-02T09:51:55+00:00 -- AST-Check _pruefe_audit_signatur in antipattern.py
- **Status:** failed
- **Info:** reviewer_rejected

## 2026-11-02T09:52:03+00:00 -- Tests fuer audit_signature in test_antipattern.py
- **Status:** failed
- **Info:** post_build_verify_failed

## 2026-11-02T11:39:43+00:00 -- Tests fuer Heartbeat anlegen
- **Status:** done

## 2026-11-02T12:13:20+00:00 -- Neue Funktion _stage_ids in verify.py
- **Status:** done

## 2026-11-02T12:13:35+00:00 -- Test test_stage_ids in test_loop.py
- **Status:** done

## 2026-11-02T12:14:49+00:00 -- Phase abgeschlossen: werkstatt
- **Status:** phase_ende
- **Info:** tasks_ok=2/2

## 2026-11-02T13:12:19+00:00 -- Neue Funktion _stage_count_by_phase
- **Status:** done

## 2026-11-02T13:12:35+00:00 -- Test test_stage_count_by_phase und Import
- **Status:** done

## 2026-11-02T18:04:05+00:00 -- Phase abgeschlossen: werkstatt
- **Status:** phase_ende
- **Info:** rc=1 tasks_ok=0/1

## 2026-11-02T18:35:44+00:00 -- Phase abgeschlossen: werkstatt
- **Status:** phase_ende
- **Info:** rc=1 tasks_ok=6/8

## 2026-11-02T20:03:00+00:00 -- Phase abgeschlossen: werkstatt
- **Status:** phase_ende
- **Info:** rc=1 tasks_ok=3/4


## 2026-11-02T22:00:00+00:00 -- Manuelle Fixes + OP-Bereinigung (Nachtrag)
- **Status:** done
- **Info:** 19 OPs aus STATUS.md gelöscht (§5-Konvention). Der Loop
  hat diese Fixes nicht gesehen (manuelle Commits), deshalb hier als
  konsolidierter Nachtrag mit Verweis auf git log.
- **OPs done:** 066 (Reviewer-Tree), 067 (pytest_changed), 072 (UI-
  Zerlegung), 074 (FastAPI-Backend), 075 (Terminal-Proxy), 076 (Chat),
  077 (Audit-Panel), 078 (UI-Layout), 079 (Markdown-Hunk), 080
  (Python-PATCHES)
- **OPs wontfix:** 003 (security-ai), 026 (Prompt-Block ist Skill),
  030-033 (Duplikate zu 074-078), 039+041 (security-ai), 065 (Modell-
  Latenz)
- **Strukturelle Fixes (in git log):** verify_classify.py + Pre-Gate,
  Architect-Konsistenz-Check, mypy als Verify-Stage, venv-Setup,
  Skills-Welle-Aufräumarbeiten
- **Verweis:** `git log --since="2026-11-02 00:00" --until="2026-11-03 00:00"`

## 2026-11-02T22:11:13+00:00 -- OP-081: Deterministische Diagnose in Reflection (manuell)
- **Status:** done
- **Commit:** 355ba51
- **Info:** Die Reflection rief bei jedem Verify-Fehler blind den
  Builder (LLM) erneut. Bekannte deterministische Fehlerklassen wurden
  nicht erkannt, kosteten 3-5 LLM-Runden (Beleg OP-082-Lauf: 5 Runden
  LLM-Raten bei NameError + Directory-not-found).
- **Neu:** `werkstatt/diagnose.py` mit `_diagnose_import_fehlt`,
  `_diagnose_pfad_not_found`, `_deterministische_diagnose`. Hook in
  `reflection._reflection_loop` vor `run_builder`: bei Match wird der
  deterministische Patch angewendet und die Runde per continue beendet.
- **Wiederverwendet:** `_apply_patches_with_diagnose`, `_setze_runde_patches`,
  `last_verify_errors`. Kein neuer Loop, keine Duplikation.
- **Tests:** `tests/test_diagnose.py` — 6 Szenarien.
- **Baseline nach Commit:** pytest 1175, ruff 179, mypy 18.
- **Nicht abgedeckt** (separate OP-Kandidaten):
  - Re-Export-Kill bei `--fix`
  - Monkeypatch-Ziel-Kill bei `--fix`
  - Test blockiert auf `receive_json` ohne Endpoint-Response

## 2026-11-02T22:13:51+00:00 -- OP-082: Dashboard-Verdrahtung (manuell nach Loop-Fix)
- **Status:** done
- **Commit:** 7d59278
- **Info:** Loop-Build in 5 Runden gescheitert an drei deterministischen
  Fehlern (fehlende Imports, falscher static_dir-Pfad, blockierender
  test_ws_terminal). Manuell gefixt.
  - app.py: `from werkstatt.web import ws, chat, audit_panel,
    terminal_proxy` + FastAPI-StaticFiles/FileResponse/Path.
  - static_dir: `Path(__file__).resolve().parent.parent.parent / "static"`
    (Layout/CSS/JS liegen in /opt/werkstatt/static/, nicht im Modul).
  - test_ws_terminal: blockierendes `receive_json()` entfernt — Endpoint
    sendet keine Antwort auf Client-Nachrichten.
- **Tests:** 5 Szenarien in tests/test_web_integration.py.
- **Anlass für OP-081:** Diese drei Fehlerklassen sind deterministisch
  prüfbar. Siehe Commit 355ba51 (werkstatt/diagnose.py).

## 2026-11-03T12:33:23+00:00 -- OP-083: Dashboard Live-Daten (done)
- **Status:** done
- **Commits:** 67eebf7, a16dcf2, 55964ca, afcfd55, 696e22c, 9384aac, da0258b, 5d8c149, 997fb07, 2f53975, 33e3f01
- **Info:** OP-083 hatte drei Punkte (a) WS-Terminal Datei-Tailing, (b) Chat-Fetch statt Demo, (c) tabs.js Panel-Bindung. Alle drei umgesetzt, plus erweitert:
  - PTY-Terminal (xterm.js + /ws/shell + bash -l -i) statt nur Render-Mitschnitt. Im Browser verifiziert: ls, cd, Ctrl+C.
  - Tee-Log: loop_renderer._emit_raw + log_line schreiben ANSI-frei in logs/loop-render-YYYY-MM-DD.log, terminal_proxy streamt Render-Zeilen.
  - Route-Kollision /ws/shell vs /ws/{tab_id} gefixt (shell.router vor ws.router).
  - Shell-Toggle-Bug nach Schliessen-und-Oeffnen (init_xterm idempotent).
  - Paste im xterm via Ctrl+V/Rechtsklick/Shift+Insert (Browser Ctrl+Shift+V funktioniert ohnehin).
- **Tests:** tests/test_shell.py (2 smoke + 3 slow), test_web_integration.py, test_web_live.py.
- **Baseline danach:** pytest 1193 (not slow), ruff 186, mypy 27.

## 2026-11-03T12:33:23+00:00 -- Manuelle Session 2026-11-02/03 (Auth, UI, Diagnose, Skills, AST)
- **Status:** done
- **Info:** Ad-hoc-Arbeit ohne eigene OPs. Konsolidierter Nachtrag mit Commit-Verweis.
- **Verweis:** git log --since=2026-11-02 --until=2026-11-04
- **Auth** (7ee750a, 9cf8a48): werkstatt/web/auth.py — Single-Token, Cookie httponly+samesite=strict+secure-wenn-HTTPS, WS-Handshake-Check is_authed_ws, Login-Page, /api/auth/login+logout, __main__ warnt bei 0.0.0.0 ohne HTTPS. tests/test_auth.py 13 Szenarien.
- **Diagnose-Fallback** (c8b0aec): werkstatt/diagnose.py _deterministische_diagnose scannt alle .py wenn state.patches leer, _finde_import_quelle unterscheidet Modul vs. Symbol. Hook in reflection._reflection_loop vor run_builder. _module_exists in hooks/pre_tool_use erkennt package-relative Imports.
- **Skills-Matrix** (104008b): planner, reflection, architect laden jetzt rollen-spezifische Skills (waren vorher leer). builder und reviewer waren schon vollstaendig. Neue state-Felder: planner_skills_block, reflection_skill_body, architect_skills_block.
- **AST-Verkabelung** (792b31b): run_architect befuellt state.api_index_cache via scout._baue_api_index. _planner_system baut DATEI-STRUKTUR (AST)-Block fuer key_files. _build_patches_fuer_datei haengt ZIELDATEI-STRUKTUR (AST) an.
- **quality_gate re-baseline** (42a25e8, 355ba51): BASELINE nachgezogen, mypy-Scope werkstatt/ statt ., ast/katalog-Skip wenn Datei fehlt, pytest -m 'not slow' fuer Gate-Runs.
- **DeepSeek-Look** (f30a13d): static/layout.css komplett neu (~380 Z., CSS-Variablen), chat.css Bubbles, audit.js data-kind fuer Kategorie-Farben.
- **Tee-Log** (2f53975, 33e3f01): loop_renderer._emit_raw + log_line schreiben ANSI-frei in logs/loop-render-DATUM.log. terminal_proxy streamt Render-Zeilen. Browser zeigt 1:1 SSH-Output.

## 2026-11-03T13:41:47+00:00 -- OP-084 + OP-085: Chat-Backend + Chat-Agent (done)
- **Status:** done
- **Commits:** 82502f0, e016f68, 61912bc, 98a53d3, [LLM-First]
- **OP-084 (Chat-Backend):** POST /api/chat liefert antwort-Feld,
  'starte Loop mit OP-NNN' triggert subprocess, offene-OP-Liste
  aus STATUS.md. Frontend rendert antwort als pre-wrap Bubble.
- **OP-085 (Chat-Agent):** LLM-First mit Function-Calling
  (DeepSeek). Tools: list_open_ops, read_file, grep, shell_exec,
  measure_status, start_loop. Max 5 Runden. Shell-Exec: PTY-Inject
  bei Einzeiler, sonst subprocess.run (Mehrzeiler/Heredoc immer
  subprocess).
- **Test-Anpassung:** test_post_chat_antwort_feld mockt jetzt
  _deepseek_chat statt Live-LLM. In Test-Umgebung kein Key nötig.
- **Hinweis:** LLM-First ersetzt Pattern-Fast-Path für freie
  Fragen — natürliche Sprache ('Was ist die nächste OP') geht
  jetzt durch Tool-Calling, nicht durch Regex.

## 2026-11-03T13:49:30+00:00 -- OP-045: WORKFLOW.md geloescht
- **Status:** done (statt entstauben)
- **Begruendung:** docs/WORKFLOW.md war nicht in DOC_CONVENTIONS §2
  als Pflichtdatei gelistet. 696 Zeilen veralteter Pipeline-Ablauf
  (pipeline.py existiert nicht mehr). Wird nicht gepflegt seit
  2026-10-31.
- **Aenderungen:** docs/WORKFLOW.md git-rm. OP-045 aus STATUS
  entfernt. Referenzen in docs/index.md (1) und docs/CONVENTIONS.md
  (4) bereinigt. Delete-Zone-Eintrag in STATUS.md.
- **Nicht geaendert:** docs/IDEEN.md (Wunschliste, nicht Pflicht),
  docs/archiv/bau-handoff-archiv.md (Historie), audit/ (generiert).
- **OP-046 bleibt offen** — betrifft andere Dateien (PLANNER-KONZEPT,
  ROLLEN-AUDIT, MERKPOSTEN), separate Aufgabe.
## 2026-11-03T15:47:46+00:00 -- Phase abgeschlossen: werkstatt
- **Status:** phase_ende
- **Info:** tasks_ok=0/3


## 2026-11-03 -- OP-046 abgeschlossen: Doku-Entstaubung

- **Dateien:** docs/PLANNER-KONZEPT.md, docs/ROLLEN-AUDIT.md, docs/MERKPOSTEN.md
- **Aenderungen:** pipeline.py → werkstatt.loop (CLI), HARD_RULES_* → werkstatt/hard_rules.py,
  ARCHITEKTUR.md → ARCHITECTURE.md, tote Archiv-Links aktualisiert.
- **Abnahme:** `grep -c "pipeline.py\|ARCHITEKTUR.md\|OFFENE-BLOECKE.md\|ERLEDIGT.md"` = 0 pro Datei.
- **Hinweis:** Loop-Lauf 6826cb9 hat nur t1 committet (doku-filter `same_act=True`
  zu aggressiv, filtert Tasks ueber mehrere .md-Dateien weg); Rest manuell nachgezogen.
## 2026-11-03T17:34:06+00:00 -- Phase abgeschlossen: werkstatt
- **Status:** phase_ende
- **Info:** rc=1 tasks_ok=2/4

## 2026-11-03T19:23:57+00:00 -- Phase abgeschlossen: werkstatt
- **Status:** phase_ende
- **Info:** tasks_ok=1/3

## 2026-11-03T19:49:14+00:00 -- Phase abgeschlossen: werkstatt
- **Status:** phase_ende
- **Info:** tasks_ok=1/2

## 2026-11-03T23:21:27+00:00 -- Phase abgeschlossen: werkstatt
- **Status:** phase_ende
- **Info:** tasks_ok=2/3

## 2026-11-04T13:27:25+00:00 -- Phase abgeschlossen: werkstatt
- **Status:** phase_ende
- **Info:** tasks_ok=2/4


## 2026-11-04 -- OP-134 abgeschlossen: State-Inventur (MESS-OP)

- **Status:** done (Work-Commit 7177f16)
- **Dateien:** tools/state_inventory.py (neu), tests/test_state_inventory.py (neu), docs/STATE-INVENTUR.md (neu)
- **Aenderungen:** Read-only AST-Messung fuer RunState. Kategorien:
  aktiv (10), read_only (24), write_only (16), getattr_only (7),
  tot (47), ghosts (25). Baseline-Check via `--check`,
  Parser-Smoke-Tests (3).
- **Messbefunde gegen Handoff §7/§11:**
  - `architect.py:385` liest `explorer_findings` — bestaetigt
  - `api_index_cache` "toter Cache" — WIDERLEGT (write_only,
    gelesen via getattr in `architect.py:324` + `builder.py:154`)
  - `set_run_id` fehlt in `loop.py` — WIDERLEGT (`loop.py:296`)
  - `explorer_context` ist Ghost (nicht deklariert) — Zusatzbefund
  - Architect HAT AST-Zugriff via `api_index_cache`
    (AST-Block ab `architect.py:340-356`)
- **Abnahme:** pytest 1241 passed, 5 skipped;
  state_inventory --check EXIT=0; audit_drift EXIT=0;
  control_drift EXIT=0.
- **Nachfolge-OPs:** OP-145 (Namens-Drift, bereits offen),
  OP-135/136/137 (Contract), OP-138..144 (Splits).

## 2026-11-05 -- OP-135a abgeschlossen: State-Contract-Design

- **Status:** done (Work-Commit 35c2aa3)
- **Dateien:** werkstatt/state_contracts.py (neu),
  docs/STATE-CONTRACTS.md (neu), tests/test_state_contracts.py (neu),
  werkstatt/state.py (Property-Views), werkstatt/explorer.py
  (_git_dirty + Diagnostics-Befuellung)
- **Aenderungen:** 5 Dataclasses (ExplorerOutput, ExplorerDiagnostics,
  ScoutOutput, ArchitectOutput, PlannerOutput) + KeyFile + Contract
  (Registry). ContractDict-Mixin fuer dict-artigen Zugriff. 5
  read-only Property-Views auf RunState mit Lazy-Imports.
- **Design-Entscheidungen:**
  - ScoutOutput.widersprueche NICHT deklariert (existiert nur als
    Audit-Event planner_scout_api_widerspruch).
  - ArchitectOutput.zieldateien NICHT deklariert (existiert nur
    implizit in architect_prosa-Parsing). Beide waeren derselbe
    Fehler wie explorer_findings (deklariert, aber tot).
  - RunState-Felder bleiben im Konstruktor (Property-View ist
    verlustfrei, MESS-2: 0 Tests mit RunState(tasks=...)).
  - explorer_diagnostics wird ab jetzt im deterministischen
    Explorer-Pfad befuellt (state.explorer_findings = {...} nach
    _messen()) — Voraussetzung fuer OP-136.
- **Abnahme:** pytest 1248 passed, 5 skipped; state_inventory
  --check EXIT=0; audit_drift EXIT=0; control_drift EXIT=0.
- **Nachfolge-OPs:** OP-135b (RunState-Migration), OP-136
  (Validierung), OP-137 (Fix architect.py), OP-145 (Namens-Drift).

## 2026-11-04 -- OP-146 abgeschlossen: Stale Blocker-Referenzen bereinigt

- **Status:** done (Work-Commit 44b4350)
- **Dateien:** `docs/STATUS.md` (11 Blockiert-von-Felder bereinigt,
  OP-113a angelegt, 2 Kosmetik-Fixes), `PROGRESS.md`
- **Aenderungen:**
  - Stale `Blockiert-von` bereinigt: OP-092, 096, 098, 100, 105, 106,
    123, 124, 127, 133, 142 (11 OPs)
  - OP-113a als eigener Header angelegt (ADR-0010, Voraussetzung fuer
    OP-129/130/113i)
  - Kosmetik: OP-112 `-` -> `—`, OP-125 `-` -> `—`
- **Stale-Check:** 0 stale nach Patch (vorher 14 OPs mit 18 Refs)
- **Abnahme (offizieller Runner, ohne tests/test_shell.py):**
  pytest 1255 passed, 5 skipped; audit_drift OK; control_drift OK;
  state_inventory OK
- **Nicht Teil der Baseline:** `tests/test_shell.py` zeigt 3 fails
  (W36-RP-Guard blockiert `/bin/bash -l -i` in PTY-Tests) —
  reproduziert auf parent `6624954`, pre-existing, siehe OP-148.
- **Nachfolge-OPs:** UI-Kette (OP-124/126/127/128/131/132) entblockt.
  OP-129/130/113i warten auf OP-113a (via OP-113).

## 2026-11-04 -- OP-150 abgeschlossen: control/reflection.py geloescht

- **Status:** done (Work-Commit 1752d76)
- **Dateien:** `werkstatt/control/reflection.py` (geloescht),
  `docs/STATUS.md` (Delete-Zone), `PROGRESS.md`
- **Befund:** `werkstatt/control/reflection.py` war byte-identisch zu
  `werkstatt/reflection.py` (MD5 `1ffea26252c1425ae9476c069d981ea8`)
  und wurde von nichts importiert. OP-104 hatte den Zombie als
  "wortgleiche Kopie" angelegt, die geplante Aufrufer-Migration
  (OP-106) hat nie stattgefunden.
- **Aenderung:** Zombie-Datei geloescht. `control/__init__.py` und
  `control/registry.py` referenzierten sie nicht (Registry zeigt auf
  `werkstatt.reflection`, nicht `werkstatt.control.reflection`).
- **Nicht betroffen:** `tests/test_planner.py:65-69` enthaelt nur
  String-Literale ("kopiere ... nach werkstatt/control/reflection.py")
  als Fixture-Daten fuer den Planner-Parser, keinen Import.
- **Abnahme (offizieller Runner, ohne tests/test_shell.py):**
  pytest 1255 passed, 5 skipped; audit_drift OK; control_drift OK;
  state_inventory OK
- **Nachfolge-OPs:** OP-106 (Aufrufer-Migration) ist faktisch
  erledigt — heute existiert nur noch `werkstatt.reflection`.

## 2026-11-04 -- OP-148 abgeschlossen: test_shell.py 3 PTY-Tests auf skip

- **Status:** done (Work-Commit 547eab0)
- **Dateien:** `tests/test_shell.py`
- **Problem:** 3 PTY-Tests (`test_shell_echo_liefert_antwort`,
  `test_shell_pwd_zeigt_cwd`, `test_shell_resize_event`) riefen echten
  `subprocess.Popen(['/bin/bash', '-l', '-i'])` auf und wurden von
  `tests/conftest.py::_no_gefaehrliche_subprocess` (W36-RP-Guard)
  blockiert. `@pytest.mark.slow` war reine Doku (pytest.ini hatte
  kein `addopts = -m "not slow"`).
- **Aenderung:** 3 Tests von `@pytest.mark.slow` auf
  `@pytest.mark.skip(reason=...)` umgestellt. Die Tests bleiben als
  Dokumentation im Code (zeigen die manuelle Browser-Verifikation),
  laufen aber nicht mehr automatisch.
- **Abnahme:**
  - `pytest tests/test_shell.py` -> 2 passed, 3 skipped
  - `pytest tests/` (voller Lauf, ohne --ignore) -> 1257 passed,
    8 skipped, 0 failed
  - audit_drift OK; control_drift OK; state_inventory OK
- **Baseline-Effekt:** `werkstatt_kontext.py` kann optional das
  `--ignore=tests/test_shell.py` weglassen — dann Baseline-Zahl
  `1257 passed, 8 skipped`. Dieses Tool wurde NICHT angepasst
  (separate Entscheidung).

## 2026-11-04 -- OP-149 abgeschlossen: pytest_regression auf changed_py_files

- **Status:** done (Work-Commit 11f02b1)
- **Dateien:** `.werkstatt/verify.json`,
  `werkstatt/templates/.werkstatt/verify.json`,
  `tests/test_verify_regression.py`
- **Cross-Repo:** `security-ai/.werkstatt/verify.json` geaendert
  im separaten Repo (Commit ebc7c46, github.com:ghxstfocus/security-ai).
  `test_verify_regression.py` prueft alle drei Pfade (templates,
  werkstatt/.werkstatt, security-ai/.werkstatt) auf Konsistenz —
  Cross-Repo-Patch noetig, damit der Contract-Test gruen bleibt.
- **Problem:** `pytest_regression` (voller Lauf) lief nur bei
  `changed_non_test_py_files`. Bei reinen Test-Aenderungen (oder
  Code+Test-Kombinationen) lief der volle Lauf nicht. Regression-
  Risiko: modifizierter Test bricht anderen Test, ohne dass es auffaellt.
- **Aenderung:** `requires` von `"{changed_non_test_py_files}"` auf
  `"{changed_py_files}"` in allen drei `verify.json`-Pfaden.
  Damit laeuft `pytest_regression` bei JEDER .py-Aenderung.
  Redundanz zu `pytest_changed` bei Test-Aenderungen ist gewollt
  (Sicherheitsnetz).
- **Lehre (MERKPOSTEN-Kandidat):** Contract-Tests, die Shipped-
  Configs asserten, muessen vor dem Patch `grep -rn '<alter-wert>'
  tests/` durchlaufen. Zusaetzlich: ein Test kann MEHRERE Pfade
  pruefen (hier 3 × verify.json) — Kontext lesen, nicht nur Treffer
  zaehlen.
- **Abnahme:** pytest 1257 passed 8 skipped (Werkstatt);
  audit_drift OK; control_drift OK; state_inventory OK

## 2026-11-05 -- OP-135b abgeschlossen: RunState-Contract deklariert

- **Status:** done (Work-Commits 171b10d + 4824c45)
- **Dateien:** `werkstatt/state.py`, `tools/state_inventory.py`,
  `docs/STATE-INVENTUR.md`, `werkstatt/planner.py`,
  `werkstatt/builder.py`, `werkstatt/scout.py`,
  `werkstatt/architect.py`, `werkstatt/gates.py`,
  `werkstatt/pipeline_phases.py`, `werkstatt/task_runner.py`,
  `tests/test_state_inventory.py`, `tests/test_gates.py`,
  `tests/test_loop_resume_from_phase_state.py`,
  `tests/test_planner_atomarer_plan.py`
- **Problem:** 2 Contract-Felder (`explorer_context`, `tests`) waren
  Ghosts (dynamisch an die Dataclass-Instanz gehaengt, nicht
  deklariert). Property-Views griffen per `getattr`, Aufrufer
  ebenfalls.
- **Aenderung Stufe 1 (171b10d):**
  - `explorer_context: dict` und `tests: list` als Dataclass-Felder.
  - Property-Views `explorer_output`/`planner_output` direkt.
  - `BASELINE_GEISTER` 25 -> 23.
- **Aenderung Stufe 2 (4824c45, Commit-Label "OP-161"):**
  - 15 `getattr(state, "X", fallback)` -> `state.X` (Contract-Felder
    direkt gelesen, Fallback-Werte per `or`-Operator erhalten).
  - Test-Anpassungen: SimpleNamespace-Stubs um fehlende Felder
    erweitert (6 Tests).
  - `test_state_inventory.py`: `explorer_context`-Kategorie
    `write_only` -> `aktiv`.
  - ruff-Baseline sinkt 21 -> 17 (unused-import-Removal).
- **Nicht in OP-135b:** die restlichen 23 Ghosts
  (`last_verify_errors`, `spec_widerspruch_erkannt`, etc.) —
  eigene OPs.
- **Abnahme:** 1259 passed, 8 skipped; audit_drift OK;
  control_drift OK; state_inventory OK (23/47/7).
- **Hinweis:** Commit-Label "OP-161" existierte nie als
  STATUS-Header. Arbeit gehoert zu OP-135b Stufe 2
  (Akzeptanzkriterium "Aufrufer lesen die neuen Namen").

## 2026-11-05 -- OP-137 abgeschlossen: AST-Block liest file-Feld

- **Status:** done (Work-Commit dbaa40b)
- **Dateien:** `werkstatt/architect.py`,
  `tests/test_architect_prompt_v2.py`
- **Problem:** Der eigentliche OP-119-Bug war nicht
  `architect.py:385` (`explorer_findings` statt
  `explorer_context`) — der `_planner_system`-Code enthaelt
  bereits einen `<measured_files>`-Block mit allen key_files-Namen.
  Der Bug war: `_kf_paths` liest `pfad`/`path` aus den key_files,
  die aber `file` heissen. Konsequenz: `_kf_paths` immer leer ->
  AST-Block nie gebaut -> Architect sieht keine Funktions-/Klassen-
  Struktur, nur Dateinamen.
- **Aenderung:**
  - `_kf_paths` liest `file`, `pfad`, `path` (Fallback-Kette).
  - Key-files werden nach `confidence` sortiert
    (high -> medium -> low -> default), damit bei >10 Dateien
    die wichtigsten im AST-Block landen statt zufaellig 10.
- **Tests (neu):**
  - `test_planner_system_liest_file_feld` — Regression: AST-Block
    enthaelt die Datei aus dem `file`-Feld.
  - `test_planner_system_sortiert_nach_confidence` — Sortierung
    high vor medium vor low.
- **Nicht in OP-137:** die 5 zusaetzlichen Akzeptanzkriterien aus
  dem alten OP-Text (Cross-Role-Smoke x3, `_format_explorer_findings`-
  Erweiterung, `ast_block_fuer_zieldatei` im Architect,
  Feld-Umbenennung auf `explorer_output`). Alle durch existierenden
  Code abgedeckt (gemessen 2026-11-05).
- **Abnahme:** 1259 passed, 8 skipped; audit_drift OK;
  control_drift OK; state_inventory OK.

## 2026-11-05 -- OP-136a abgeschlossen: Contract-Validierung explorer->scout + planner->builder

- **Status:** done (Work-Commit b77ee26)
- **Dateien:** `werkstatt/pipeline_phases.py`,
  `tests/test_pipeline_contract.py` (neu), `tests/test_loop.py`
- **Problem:** `validate_transition` (aus frueherer Session) existierte,
  wurde aber nirgends im Pipeline-Code gerufen. Contract-Verletzungen
  (leerer `explorer_context`, leerer `planner_output`) liefen stumm
  durch und brachen erst spaeter mit unklaren Symptomen ab.
- **Aenderung:**
  - `_validate_contract_safe(von, zu, state, pd, pn)`: Wrapper um
    `validate_transition` mit audit-Fallback.
  - Wiring 1 (`explorer->scout`): greift wenn `state.tasks` leer
    und nicht `auftrag_bereits_erfuellt`. Fail-loud mit rc=1.
  - Wiring 2 (`planner->builder`): greift wenn Tasks gefuellt und
    nicht `auftrag_bereits_erfuellt`. Fail-loud mit rc=1.
  - `_state`-Helper in `tests/test_loop.py` befuellt `explorer_context`
    mit Default (Tests koennen `explorer_ctx={}` setzen, um den Fail
    zu provozieren).
- **Tests:**
  - `tests/test_pipeline_contract.py`: 3 neue Tests
    (ok, leer fail, unbekannter Uebergang noop).
- **Nicht in OP-136a:** die internen Uebergaenge scout->architect,
  architect->planner-split (verschachtelt in `run_planner`) und
  `tools/state_drift.py` — bleiben in OP-136b.
- **Abnahme:** 1262 passed, 8 skipped; audit_drift OK;
  control_drift OK; state_inventory OK.

## 2026-11-05 -- OP-164 abgeschlossen: Reviewer versteht Rename-Aufgaben

- **Status:** done (Commit 2dde8cd)
- **Dateien:** `werkstatt/reviewer.py`,
  `tests/test_reviewer_rename.py` (neu)
- **Problem:** `REVIEWER_SYSTEM` behandelte jede `-`-Zeile mit
  bestehender Zuweisung/Funktion als HIGH-Bug. Bei Rename-Aufgaben
  ist das die Aufgabe selbst. Loop-Test-3: t3 (builder.py) sollte
  `auftrag_bereits_erfuellt` umbenennen, Reviewer meldete 3x HIGH
  "Bestehende Zuweisung entfernt", 5 Reflection-Runden, human_review.
- **Aenderung:**
  - `REVIEWER_SYSTEM`: neuer Abschnitt "RENAME-AUSNAHME (2026-11-05,
    OP-164)" direkt vor "## Severity-Level". `-`-Zeile mit altem
    Namen ist OK, wenn im selben Diff-Hunk eine `+`-Zeile mit
    anderem Identifier steht und die Task-Beschreibung Rename-Marker
    ("umbenennen", "rename", "ersetzen durch") enthaelt.
  - `_filter_rename_false_positives(bugs, diff, task_desc)`: neuer
    deterministischer Post-Processor. Splittet Diff an
    `^@@ `-Hunks, prueft fuer jeden HIGH-Bug mit
    "Bestehende Zuweisung/Funktion X entfernt" ob im selben Hunk
    eine `-`-Zeile mit `X` UND eine `+`-Zeile mit anderem Identifier
    steht. Bei Match: severity -> medium, description erweitert um
    "[OP-164: Rename erkannt, +-Zeile im Hunk]".
  - `run_reviewer`: Aufruf nach JSON-Parse. `_rename_filtered =
    _bugs_high_before - _bugs_high_after`, `approved` neu berechnet
    wenn gefiltert und keine HIGH mehr uebrig.
  - `reviewer_result`-Payload um `rename_filtered` erweitert
    (additiv, kein neuer Audit-Kind, Katalog bleibt unveraendert).
- **Tests (neu):**
  - `test_rename_ok` — Rename-OK: `-alt +neu` im selben Hunk,
    task_desc "umbenennen" -> medium, approved=True.
  - `test_rename_fehler` — Rename-Fehler: `-alt` ohne `+neu` im
    selben Hunk -> HIGH, approved=False.
  - `test_kein_rename_kontext` — kein Rename-Marker in task_desc
    -> HIGH bleibt HIGH.
- **Nicht in OP-164:** semantische Multi-Hunk-Renames (nur
  gleicher Hunk), nicht-Rename-Bugs mit "entfernt"-Wortlaut.
  Bewusst eng gehalten.
- **Abnahme:** 1274 passed, 8 skipped; audit_drift OK;
  control_drift OK; state_inventory OK.


## 2026-11-05 -- OP-163 abgeschlossen: Planner-Dependencies durchgesetzt

- **Status:** done (Commit 9797b31)
- **Dateien:** `werkstatt/planner.py` (`PLANNER_SPLIT_SYSTEM`),
  `werkstatt/phase_state.py` (`get_next_task`, `mark_blocked`,
  `_unmet_dependencies`), `werkstatt/pipeline_phases.py`
  (`_phase_tasks_loop` Loop-Ende), `werkstatt/audit.py` (Katalog),
  `tests/test_loop_task_dependencies.py` (neu)
- **Problem:** Planner-Split kannte `dependencies` als Feld, aber
  der Prompt sagte nicht WANN setzen. Der Loop pruefte
  `dependencies` nicht durch. Loop-Test-3: t6 (state_inventory
  Baseline 23->22) startete, obwohl t3 (builder.py) mit
  human_review endete. 5 Reflection-Runden, Erschoepfung.
- **Aenderung:**
  - `PLANNER_SPLIT_SYSTEM`: explizite Pflicht-Regel. Konsequenz-
    Tasks (Baseline senken, Doku die Endzustand prueft, Cross-
    Role-Tests, Ghost-Entfernung in mehreren Dateien) MUESSEN
    `dependencies` auf alle Tasks setzen, die den Vorbedingungs-
    Zustand aendern. Reine Datei-Tasks: leere Liste [].
  - `PhaseState.get_next_task`: filtert Tasks mit unerfuellten
    `dependencies` (status != "done") dynamisch raus. Pruefung
    bei jedem Aufruf gegen den aktuellen `data["tasks"]`-Stand.
  - `PhaseState.mark_blocked(task_id, grund)`: setzt status
    "blocked" + failure "blocked: deps:<ids>".
  - `PhaseState._unmet_dependencies(task)`: liefert Liste der
    unerfuellten dependency-IDs (fehlend oder status != "done").
  - `_phase_tasks_loop` Loop-Ende: wenn `get_next_task` None
    liefert, alle verbliebenen `pending`-Tasks auf
    unerfuellte Deps pruefen, `mark_blocked` + `audit` +
    `save()`. Kein Reflection-Versuch, Loop laeuft weiter mit
    naechster unabhaengigen Task.
  - `audit.py`-Katalog: neuer Kind `loop_task_blocked`
    (fehlte sonst -> audit_drift rot).
- **Tests (neu):**
  - `test_task_mit_unerfuellten_deps_wird_skipped` — t1 (pending,
    dep=t2) + t2 (failed) -> get_next_task None, t1 blockiert.
  - `test_task_nach_erfuellter_dep_laeuft` — t1 (pending, dep=t2)
    + t2 (done) -> t1 wird ausgeliefert.
- **Nicht in OP-163:** Human-Gate-Anpassung am Phase-Ende (User
  sieht blocked-Tasks in der Task-Liste, kein separater Prompt
  noetig). Kann nach Loop-Test-4 nachgezogen werden. Bestehende
  implizite File-Dependency (`_pruefe_prior_failed_dependency`)
  bleibt unveraendert — orthogonal zum neuen expliziten Feld.
- **Abnahme:** 1276 passed, 8 skipped; audit_drift OK;
  control_drift OK; state_inventory OK.


## 2026-11-05 -- OP-165 abgeschlossen: contract_check pro Task

- **Status:** done (Commit f73dde5)
- **Dateien:** `werkstatt/verify.py` (Platzhalter `{task_files}`),
  `tools/state_inventory.py` (`--changed`-Modus + `ghosts_in_files`),
  `.werkstatt/verify.json` (Stage `contract_check`, hart),
  `werkstatt/templates/.werkstatt/verify.json` (Stage `contract_check`,
  weich), `tests/test_verify_contract_stage.py` (neu)
- **Problem:** Contract-Aenderungen (z.B. Feld-Rename) wurden nur
  am Ende geprueft. Zwischenschritte (`planner.py`,
  `pipeline_phases.py`) konnten unvollstaendig umbenannt bleiben,
  ohne dass es auffiel. Loop-Test-3: t4 + t5 als "task ok",
  obwohl `state_inventory` noch Ghost-Reste zeigte
  (`auftrag_bereits_erfuellt` in `pipeline_phases.py` + `planner.py`).
- **Aenderung:**
  - `_expand_cmd_placeholders` in `verify.py`: neuer Platzhalter
    `{task_files}`. Quelle ist `state.aktuelle_task["task_files"]`
    (pro Task, NICHT kumulativ). Leer -> `return None` = Skip,
    verhindert Fehlfeuer bei Tasks ohne Zieldatei.
  - `state_inventory.py`: neue Funktion `ghosts_in_files(files)`
    filtert `scanne_zugriffe`-Ergebnis auf die übergebenen Pfade und
    prueft gegen `BASELINE_GEISTER`. Neue CLI `--changed FILE...`
    (nargs=*) ruft sie, Exit 1 bei Treffer.
  - `scanne_zugriffe(files=None)`: optionaler `files`-Parameter,
    damit `--changed` nur die relevanten Dateien parst (Performance,
    keine Semantik-Aenderung).
  - `.werkstatt/verify.json`: Stage `contract_check` vor
    `pytest_regression`, `command: [..., "--changed", "{task_files}"]`,
    `phase: post_build`, `hart: true`.
  - `werkstatt/templates/.werkstatt/verify.json`: gleiche Stage,
    aber `hart: false`. Grund: Template-Zielprojekte haben
    `tools/state_inventory.py` nicht, mit `hart: true` wuerde die
    Stage in jedem fremden Projekt fail-loud blocken. Die Haerte
    ist werkstatt-spezifisch, das Muster bleibt sichtbar.
- **Tests (neu):**
  - `test_ghost_in_datei_failt` — Datei mit Ghost-Zugriff ->
    Treffer-Liste enthaelt den Feldnamen.
  - `test_datei_ohne_ghost_ok` — Datei ohne Ghost-Zugriff ->
    leere Liste.
- **Nicht in OP-165:** Human-Gate-Anpassung am Phase-Ende
  (contract_check greift pro Task via `_v_hart_ok=False` ->
  bestehender Fail-Pfad in `_phase_tasks_loop`); semantische
  Pruefung (Type-Check, Doku-Konsistenz). Bewusst nur
  Ghost-Feld-Attribut-Zugriffe.
- **Abnahme:** 1278 passed, 8 skipped; audit_drift OK;
  control_drift OK; state_inventory OK.


## 2026-11-05 -- Loop-Test-4 (OP-145 live) -- Messbericht

- **Status:** Fehlschlag fuer 2/3 OPs. Kein Close, keine Feier.
- **Ausgangslage:** 948ba9c (3 neue OPs aus Session 1: OP-163, OP-164,
  OP-165). Ziel war, alle drei live gegen OP-145 zu validieren.
- **Verlauf:** Loop gestartet mit `--fresh --aufgabe "$(OP-145-Block)"`.
  Plan-Gate: 8 Tasks (t1-t8). Loop bis Phase-End, dann
  `LOOP FEHLGESCHLAGEN Tasks: 3/8` nach 3 Phase-Review-Runden.
  3 Commits mit doppeltem Subject: `fix(werkstatt): OP-145: ### OP-145:
  Namens-Drift`. Working Tree nach Loop: 8 Files dirty (+91/-27).
  Rollback auf 948ba9c durchgefuehrt (Loop-Spur im Reflog).
- **Live-Ergebnis pro OP:**
  - **OP-165 (contract_check):** wirkt. Stage lief bei jedem Task
    mit 0s und ohne Fehlmeldung im Erfolgsfall.
  - **OP-163 (Planner-Dependencies):** wirkt **nicht**. Audit-Event
    `planner_split` (14:17:47) zeigt `deps=[]` bei allen 8 Tasks.
    Prompt-Regel (Z. 293-296) wurde vom Split-LLM ignoriert.
    `get_next_task`-Filter greift ins Leere. Nachfolger: **OP-163b**.
  - **OP-164 (Rename-Filter):** wirkt **nicht**. Der Live-Beleg
    triggert den `AUFTRAG-TREUE-CHECK`-Block (Z. 165-179), nicht
    den GOLD-Diff-Block, den OP-164 gepatcht hat. Zwei Bug-Klassen:
    Wert statt Feldname, type-ignore Over-Delivery. Nachfolger:
    **OP-164b**.
- **Weitere Befunde (5 neue OPs):**
  - **OP-166:** `last_verify_errors` kumulativ -> 2 verify-Fehler in
    jeder Reflection-Runde, Builder kann sie nicht loesen.
  - **OP-167:** PhaseState `7 done + 1 human_review` vs. Loop-Footer
    `3/8` -- Zaehler-Diskrepanz.
  - **OP-168:** Phase-4-Review 3 Runden ohne Human-Gate, dann
    LOOP FEHLGESCHLAGEN bei dirty Tree.
  - **OP-169** (closed b11637b): Commit-Subject-Header `### ` nicht
    gestrippt vor `startswith(op_nnn)`-Check.
  - **OP-171** (closed b11637b): `planner_split`-Event loggte `deps`
    nicht -- Loop-Test-4 war blind fuer die Dep-Frage.
- **Lehre:** Unit-Tests gruen != live wirksam. Bei Struktur-OPs
  (Prompt-Regeln, Reflection, Phase-Review) reicht ein Test der
  neuen Funktion nicht -- es braucht einen Test, der die alte
  Wirkungslosigkeit reproduziert. Sonst kehrt der Bug zurueck.
- **Abnahme:** 1281 passed, 8 skipped; audit_drift OK;
  control_drift OK; state_inventory OK.

## 2026-11-05 -- OP-167 abgeschlossen: tasks_ok_counter in 2 Erfolgs-Pfaden

- **Status:** done (Commit a3a538b)
- **Dateien:** `werkstatt/pipeline_phases.py`,
  `tests/test_task_ok_counter_guard.py` (neu)
- **Problem:** Loop-Test-8 (2026-11-05): t3 und t4 waren ueber den
  Reflection-Pfad `done`, aber `state.tasks_ok_counter` blieb 0.
  Footer zeigte `Tasks: 0/8`, `_failed = 8 - 0 = 8`. PhaseState
  zeigte 2 done, 1 failed, 1 human_review, 4 blocked.
- **Messung:** `_task_ende(ok=True)` wird an 7 Stellen gerufen. 5
  davon haben `tasks_ok += 1` + `state.tasks_ok_counter = tasks_ok`.
  Zwei hatten es nicht:
  - **Z. 1051** (Reflection-OK-Pfad): ohne Counter. Das war der
    Loop-Test-8-Bug.
  - **Z. 1302** (Reflection-Erschoepft-Gate-approve-Pfad): ohne
    Counter. Zweiter Bug, gefunden durch den Guard-Test.
- **Aenderung:**
  - Z. 1051 + Z. 1302: `tasks_ok += 1` + `state.tasks_ok_counter
    = tasks_ok` direkt vor `_task_ende(ok=True)`.
  - `tests/test_task_ok_counter_guard.py` (neu): AST-basierter
    Guard-Test. Parst `pipeline_phases.py`, findet alle
    `_task_ende(..., ok=True, ...)`-Aufrufe, prueft dass in den
    10 Zeilen davor `tasks_ok += 1` ODER `tasks_ok_counter =`
    steht. Der zweite Sonderfall (`skip_plan_gate`, Z. 563)
    setzt `tasks_ok = 1` + Counter explizit — wird akzeptiert.
- **Abweichung vom OP-Text:** OP-167 forderte
  `tests/test_task_counter_sync.py`. Umgesetzt als
  `tests/test_task_ok_counter_guard.py` — der Guard-Name ist
  praeziser, weil er die Regel (jeder `_task_ende(ok=True)` MUSS
  Counter setzen) formuliert, nicht nur die konkrete Pfad-Situation.
- **Warum der Guard-Test wichtig ist:** Der Fix allein (Z. 1051)
  haette Loop-Test-8 gruen gemacht. Aber ohne Guard-Test waere
  Z. 1302 unentdeckt geblieben — und jeder neue Erfolgs-Pfad
  haette denselben Bug reproduzieren koennen. Der Guard-Test
  ist die Regress-Barriere.
- **Nicht in OP-167:** `_task_ende` zentralisiert den Counter
  nicht (das waere ein 7-Stellen-Umbau + Test-Bruch-Risiko).
  Der Guard-Test faengt zukuenftige Regresse stattdessen.
- **Abnahme:** 1302 passed, 8 skipped; audit_drift OK;
  control_drift OK; state_inventory OK.


### 2026-11-05 — OP-136b: State-Drift-Tool + 3 Registry-Checks

**Was gebaut:**
- `tools/state_drift.py` (neu): 3 Konsistenz-Checks zwischen
  `CONTRACTS`, `TRANSITIONS` und `RunState`-Properties.
- `Contract.transition_frei: bool = False` (neues Feld, fail-closed).
- `TRANSITIONS["scout->architect"]` um `("explorer_diagnostics", "auto")`
  erweitert — der Architect braucht `explorer_findings` (via Property),
  wurde bisher aber nicht validiert.
- `planner.py`: `_validate_contract_or_audit`-Helper; ruft
  `validate_transition("scout", "architect", ...)` vor `run_architect`
  und `validate_transition("architect", "planner", ...)` nach
  `run_architect`. Heute No-Op (auto-Regeln bzw. Pflichtfeld bereits
  durch `run_architect`-return garantiert), aber verdrahtet.
- `verify.json` (root + template): `state_drift`-Stage `hart: true`.
- `docs/STATUS.md`: OP-136b-Wortlaut korrigiert — alte Formulierung
  "jedes RunState-Feld in CONTRACTS/intern" war stale (`CONTRACTS`
  hat kein `felder`-Feld, `TRANSITIONS` ist die echte
  Feld-Referenz-Registry).

**Design-Entscheidung waehrend Bau:**
- Erste Skizze "4 Checks" auf 3 reduziert: `_PROP_NAME` ist privat,
  Check 2 (CONTRACTS→_PROP_NAME) verworfen. Die Konsistenz ist durch
  Check 1 (CONTRACTS→@property) + regulaeren Test abgedeckt.
- `explorer_diagnostics` bekommt `TRANSITIONS`-Eintrag `"auto"`
  statt `transition_frei=True`: es ist ein echter Inter-Role-Contract
  (Explorer→Architect), nur der Trigger darf fehlen.

**Baseline-Hinweis:**
- Kontext-Block sagt ruff 193, tatsaechlich gemessen 206 (vor Commit).
  Differenz +13 durch fruehere Commits, nicht durch diesen Commit.
  Baseline-Hygiene ist ein separater OP-Kandidat.

**Abnahme:**
- 1305 passed, 5 skipped (5 neue in `tests/test_state_drift.py`).
- audit_drift OK, control_drift OK, state_inventory OK,
  state_drift OK.
- Work-Commit bfd38e9, Close-Commit c327d10, Progress-Nachtrag folgt.

- OP-138 und OP-141: Blocker "OP-136b" entfernt, jetzt frei.


### 2026-11-05 — OP-138: render/-Split (loop_renderer.py)

**Neue Struktur:**
- werkstatt/render/tee.py       (73 Z.) _TEE_STREAM, _TEE_LOCK, _ANSI_RE,
                                  set_tee_stream, _tee, _TeeWriter
- werkstatt/render/rich.py      (83 Z.) RENDER_MODE, IS_CI, IS_LIVE,
                                  USE_COLOR, Farben, _use_rich, _console,
                                  rich-Imports
- werkstatt/render/emit.py      (200 Z.) _emit_raw, _progress_write, _emit,
                                  _publish, _PROJECT_CTX, TerminalEmitter,
                                  _EMITTERS, get_emitter
- werkstatt/render/spinner.py   (142 Z.) _live, _spinner_text, _live_lock,
                                  spinner_start/update/stop, _with_spinner
- werkstatt/render/progress.py  (90 Z.) _PROGRESS_STATE, _PROGRESS_LOCK,
                                  _LAST_HEARTBEAT, _emit_progress, heartbeat,
                                  progress_task, _null_progress
- werkstatt/render/tasks.py     (236 Z.) TOTAL_PHASES, header, step, task*,
                                  hook, patch, footer, group_start/end,
                                  log_line, task_started, task_done,
                                  status_header, summary, _timestamp
- werkstatt/render/plan.py      (139 Z.) panel_plan, _emit_wrapped,
                                  _render_plan_plain/rich, panel_diff, plan
- werkstatt/render/__init__.py  (108 Z.) Re-Export-Hub (keine Funktionslogik)
- werkstatt/loop_renderer.py    (24 Z.) sys.modules-Alias auf werkstatt.render

**Phasen (Commits):**
- f36cbef Phase 1: Modul-Umzug nach werkstatt/render/ (byte-identisch)
- 0093405 Phase 2a: tee.py + rich.py
- ea55514 Phase 2b-1: emit.py + ruff-Baseline-Cleanup
- 66147b5 Phase 2b-2: spinner.py + progress.py
- b6f75db Phase 2c: tasks.py + plan.py + _with_spinner + Hub-__init__

**Ehrliche Abweichungen vom OP-Text:**

1. **`loop_renderer.py` = `sys.modules`-Alias, nicht `from werkstatt.render import *`:**
   Tests patchen Modul-Attribute (`patch.object(loop_renderer, "_publish", ...)`)
   und conftest rebindet Globals (`_PROGRESS_OPEN = False`). Mit
   `from import *` bindet das Proxy-Modul Namens-Kopien; Patches und
   Rebindings waeren stumm tot. Der Alias macht beide Modul-Namen zum
   selben Objekt — Patches wirken. Phase 1 ohne Alias: 6 Tests rot.

2. **10 Test-Anpassungen in `test_loop_renderer.py` (OP forderte "gruen ohne Aenderung"):**
   `patch.object(r, "IS_CI", ...)` → `patch.object(_rmod, "IS_CI", ...)`,
   `patch.object(r, "_TEE_STREAM", ...)` → `_tmod`, 3x `_publish` → `_emod`.
   Grund: Pythons `from .rich import IS_CI` bindet Namens-Kopie. Submodule
   lesen `_rich.IS_CI` als Modul-Attribut; Patches muessen auf das
   tatsaechliche Modul zeigen. `test_human_gate_render.py` (patch auf
   `loop_renderer.panel_diff`) bleibt unveraendert wegen Alias.

3. **`tasks.py` hat 236 Zeilen (OP forderte < 200):**
   17 oeffentliche Funktionen + Konstanten + Timestamp. Aufteilung in
   `tasks_log.py` / `tasks_state.py` waere kuenstlich — Tasks sind eine
   API-Familie. Bewusste Akzeptanz-Abweichung.

4. **ruff-Baseline 193 → 203 (Kontext-Block war stale):**
   Vor dieser Session: gemessene 206. Phase 1 (Modul-Umzug) brachte
   +5 Altlast-Fehler ohne ruff-Cleanup im Pre-Commit. Phase 2b-1 hat
   das korrigiert (−6). Netto: 203 nach Phase 2c.
   Restliche 203 sind Altlast aus frueheren Commits, dokumentiert fuer
   separaten Baseline-Hygiene-OP.

**Aufrufer-Migration — bewusst NICHT in OP-138:**
9 Files (loop.py, pipeline_phases.py, agent.py, verify.py, gates.py,
planner.py, reflection.py, reviewer.py, web/audit_panel.py,
web/terminal_proxy.py) importieren weiter aus `werkstatt.loop_renderer`.
Der Alias haelt sie funktional. Migration gehoert in **OP-143**
(`cli/` + Re-Export-Bereinigung).

**Abnahme:**
- 1305 passed, 5 skipped (5 neue in test_state_drift.py, unveraendert).
- ruff . = 203 (<= 203 akzeptiert).
- audit_drift OK, control_drift OK, state_inventory OK, state_drift OK.
- Work-Commits: f36cbef, 0093405, ea55514, 66147b5, b6f75db.
- Close-Commit folgt.

- OP-139 (`phases/`-Split) und OP-140 (`builder/`-Split) frei.


### 2026-11-05 — OP-139: phases/-Split (pipeline_phases.py)

**Neue Struktur:**
- werkstatt/phases/_common.py    (262 Z.) 24 Lazy-Stubs auf
                                  werkstatt.loop.* + 6 Helper
- werkstatt/phases/explorer.py   (240 Z.) _phase_explorer_and_setup
- werkstatt/phases/plan.py       (327 Z.) _phase_plan_and_preflight
- werkstatt/phases/tasks.py      (846 Z.) _phase_tasks_loop
- werkstatt/phases/review.py     ( 82 Z.) _phase_review_gate
- werkstatt/phases/finalize.py   (169 Z.) _phase_finalize
- werkstatt/phases/__init__.py   ( 59 Z.) Fassade mit Re-Exports
                                  + Modul-Refs (_explorer_mod, ...)
- werkstatt/pipeline_phases.py   ( 22 Z.) sys.modules-Alias

**Phasen (Commits):**
- 750f681 Phase 1: Modul-Umzug (byte-identisch + Alias)
- d0d18cc Phase 2a: _common.py (Stubs + Helper zentral)
- d41233f Phase 2b: 5 Phasen-Submodule

**Ehrliche Abweichungen vom OP-Text:**

1. **`pipeline_phases.py` = `sys.modules`-Alias, nicht `from phases import *`:**
   Analog zu OP-138. Tests patchen Modul-Attribute
   (patch.object(pp, ...)) und erwarten, dass bare Namen im Body
   mitgepatcht werden. Alias macht beide Modul-Namen zum selben
   Objekt. Aufloesung in OP-143 (Re-Export-Bereinigung).

2. **`tasks.py` = 846 Zeilen (OP forderte implizit <200 wie OP-138):**
   _phase_tasks_loop ist 803 Zeilen — nicht aufteilbar ohne
   Verhaltensaenderung. Aufteilung waere ein eigener Folge-OP
   (Refactor innerhalb der Phase). Aktuell 1 Funktion = 1 Datei.

3. **3 AST-Guard-Tests muessen angepasst werden:**
   test_loop_task_fail_continue.py (2x),
   test_loop_reflection_no_apply.py (1x),
   test_loop_reviewer_deterministic.py (1x).
   Path(_pp.__file__).read_text() ->
   "\n".join(Path(m.__file__).read_text() for m in
   [_pp._explorer_mod, _pp._plan_mod, _pp._tasks_mod,
    _pp._review_mod, _pp._finalize_mod])
   Grund: OP-Text forderte 'bestehende test_loop*.py bleiben gruen
   ohne Aenderung'. Stale — die Tests scannen raw-Quelltext und
   muessen nach Datei-Split alle Phasen-Dateien durchsuchen.
   Marker (z.B. failure='reviewer_*' in tasks, pre_build-verify
   in plan) verteilen sich.

4. **Fassade exportiert Modul-Refs `_explorer_mod` etc.:**
   Nicht im OP-Text, aber fuer AST-Guard-Tests notwendig.
   Sauberer als 5x `__code__.co_filename` in jedem Test.

**Zirkularitaet geprueft:**
- phases/_common.py importiert nicht phases/* (nur reviewer, state)
- phases/{explorer,plan,tasks,review,finalize}.py importieren
  ._common + werkstatt.{state,phase_state,antipattern,reviewer,
  verify_classify,render}
- finalize.py importiert .review (einzige Phasen-Kreuzabhaengigkeit)
- phases/__init__.py importiert alle Phasen + ._common
- Kein Zirkel beim Modul-Load.

**Abnahme:**
- 1305 passed, 5 skipped.
- ruff . = 201 (2 unter Baseline 203 — durch Header-Extraktion
  sind phase_state/RunState nicht mehr in der Fassade).
- audit_drift OK, control_drift OK, state_inventory OK, state_drift OK.
- Work-Commits: 750f681, d0d18cc, d41233f.
- Close-Commit folgt.

- OP-140 (`builder/`-Split), OP-142 (`web/routes/`), OP-144
  (import-linter) frei.
- OP-143 (`cli/` + Re-Export-Bereinigung) ist jetzt entblockt —
  dort wird pipeline_phases.py-Alias + loop_renderer.py-Alias
  aufgeloest.


### 2026-11-05 — OP-140: roles/builder/-Split (builder.py)

**Neue Struktur:**
- werkstatt/roles/builder/ast.py       (114 Z.) Projekt-Python-Scan,
                                        Symbol-Checks
- werkstatt/roles/builder/prompt.py    (166 Z.) BUILDER_SYSTEM +
                                        Prompt-Bau
- werkstatt/roles/builder/validate.py  (128 Z.) Import-Validierung
- werkstatt/roles/builder/patch.py     (313 Z.) Aider-Patch-
                                        Normalisierung
- werkstatt/roles/builder/run.py       (972 Z.) _build_patches_fuer_datei
                                        + run_builder
- werkstatt/roles/builder/_common.py   ( 11 Z.) ask_llm, audit
- werkstatt/roles/builder/__init__.py  ( 82 Z.) Fassade
- werkstatt/builder.py                 ( 20 Z.) sys.modules-Alias

**Phasen (Commits):**
- f5f36d9 Phase 1: Modul-Umzug (byte-identisch + Alias)
- 6334d80 Phase 2b: 5 Submodule + _common

**Ehrliche Abweichungen vom OP-Text:**

1. **`builder.py` = `sys.modules`-Alias, nicht `from roles.builder
   import *`:** 26 Files importieren `from werkstatt.builder import X`,
   Tests patchen Modul-Attribute. Alias macht beide Namen zum selben
   Objekt. Aufloesung in OP-143.

2. **`_common.py` zusaetzlich eingefuehrt:**
   - `ask_llm`, `audit` zentral, damit Tests sie patchen koennen
   - Alias in patch.py/run.py: `_bglob` (bewusst NICHT `_c` — kollidiert
     mit lokalem Temp-Var `_c` in run_builder, F823 verhindert)

3. **4 Test-Files muessen angepasst werden (OP-Text nennt nur
   test_builder.py):**
   - test_builder_agent.py (33x): werkstatt.builder.ask_llm/audit →
     werkstatt.roles.builder._common.ask_llm/audit
   - test_k48_aider_patch.py (4x): dito
   - test_builder_module_hint.py (1x): patch.object(_b, "ask_llm") →
     patch.object(_b._common, "ask_llm")
   - test_builder_create_prompt.py (1x): dito
   Grund: Tests patchen Modul-Attribute. ask_llm/audit leben jetzt in
   `_common.py`; Submodule lesen `_bglob.ask_llm()`. Patch auf Fassade
   wirkt nicht auf Submodul-Consumer.

4. **`run.py` = 972 Zeilen** (436 + 509 + Header). OP-Text fordert
   die Aufteilung so; `_build_patches_fuer_datei` und `run_builder`
   sind eine untrennbare API (LLM + Patch-Apply + Progress).

**Fassade-Re-Exports mit as-alias-Pattern + `from . import _common as
_common`:** der Selbst-Alias markiert ruff den Modul-Import als
Re-Export (kein F401). `ruff --fix --select I` sortiert nur die
Import-Reihenfolge, laesst Re-Exports unangetastet.

**OP-137-Asymmetrie geloest:** Der Architect kann jetzt
`from werkstatt.roles.builder.ast import _ast_block_fuer_zieldatei`
nutzen, ohne den ganzen Builder zu ziehen.

**Abnahme:**
- 1305 passed, 5 skipped.
- ruff . = 198 (5 migrierte Baseline-Fehler in roles/builder/:
  SIM102, SIM103, B023, 2x S110; Netto 201 → 198 durch Fassade-
  Schrumpfung).
- audit_drift OK, control_drift OK, state_inventory OK, state_drift OK.
- Work-Commits: f5f36d9, 6334d80.
- Close-Commit folgt.

- OP-141 (`state/`-Split) und OP-142 (`web/routes/`) frei.
- OP-143 (`cli/` + Re-Export-Bereinigung): drei Aliase aufzuloesen
  (loop_renderer.py, pipeline_phases.py, builder.py).


### 2026-11-05 — OP-142: verworfen (kein Duplikationsbedarf)

**OP-Text forderte:** `web/routes/` Submodul-Split (projekte, runs,
events, gates, chat), `app.py` < 100 Zeilen, `shell.py` +
`terminal_proxy.py` zu `web/terminal.py` konsolidieren.

**Messung ergab:**

1. **`shell.py` und `terminal_proxy.py` sind keine Duplikate.**
   - `shell.py` (355 Z.): PTY-Session via `subprocess` + `pty`,
     `@router.websocket("/ws/shell")`, `PTYSession`-Klasse.
   - `terminal_proxy.py` (367 Z.): Log-Tailing (`audit-logs/`,
     `render-logs/`), `@router.websocket("/ws/terminal/{project}")`,
     `_tail_poll_queue`/`_tail_poll_render_log`.
   - **Top-Level-Schnittmenge:** nur `__all__` und `router`
     (Standard-Boilerplate).
   - **Zeilen-Schnittmenge:** 17 Zeilen — davon 6 Imports, 4
     triviale Returns, 3 Except-Klauseln, `await websocket.accept()`,
     `await websocket.close()`, `from __future__`. **Null
     fachliche Duplikation.**

2. **`app.py` (200 Zeilen) hat keine Routen-Dekoratoren im
   Top-Level.** Routen kommen über `module.register(app)` bzw.
   `app.include_router(module.router)`. Die 3 inline `@app.post`
   in `create_app()` (project_state/start/stop, ~30 Zeilen)
   koennten ausgelagert werden — spart 30 Zeilen auf Kosten
   einer weiteren Datei. Kein echter Strukturgewinn.

3. **5 neue `routes/`-Wrapper waeren Anti-Pattern.** `routes/chat.py`
   wuerde `chat.py` re-exportieren, `routes/events.py` wuerde
   `audit_panel.py` re-exportieren. Mehr Nesting, keine
   Klarheit. Widerspricht dem eigentlichen Ziel
   "Wiring klarer zu debuggen".

**Entscheidung:** OP verworfen. `shell.py` und `terminal_proxy.py`
bleiben getrennt — sie loesen verschiedene Probleme. Keine
`routes/`-Wrapper. `app.py` bleibt ~200 Zeilen (Komposition,
keine Routen).

**Delete-Zone-Status:** superseded (durch Messung widerlegt).

**Was der nächste Chat stattdessen angehen sollte:**
- OP-143 (`cli/` + 3 sys.modules-Aliase aufloesen:
  loop_renderer.py, pipeline_phases.py, builder.py) — echte
  Struktur-Verbesserung
- OP-144 (import-linter als Post-Build-Stage) — echte
  Struktur-Verbesserung
- OP-141-Modul-Split (state/) — nach OP-141-Vorarbeit jetzt
  ehrlich machbar (~2-3h)

Baseline unveraendert: 1271 passed, 8 skipped; ruff 197.
Kein Code geaendert, nur STATUS.md + PROGRESS.md.

OP: OP-142 (verworfen)


### 2026-11-05 — OP-144: import-linter als Post-Build-Stage

**Neue Struktur:**
- pyproject.toml: [tool.importlinter] mit 3 forbidden-Contracts
- tools/import_drift.py: Wrapper um lint-imports --no-cache
- tests/test_import_drift.py: 4 Smoke-Tests
- .werkstatt/verify.json: import_drift-Stage hart=true, nach
  control_drift
- werkstatt/roles/__init__.py: aus OP-140 nachgezogen

**3 Layer-Regeln (allow_indirect_imports = true pro Contract):**
1. werkstatt.render importiert NICHT direkt:
   phases, roles, web (Leaf-Schicht)
2. werkstatt.roles.builder importiert NICHT direkt:
   phases, web (Rollen kennen keine Phasen)
3. werkstatt.phases importiert NICHT direkt: web
   (Phasen kennen kein Web-Frontend)

**Warum allow_indirect_imports = true:**
ADR-0013 fordert "Rollen kennen keine Phasen direkt".
Der transitive Weg roles.builder.run -> verify -> loop ->
pipeline_phases -> phases ist der Verify-Mechanismus, kein
Rollen-Import von Phasen. Wenn das als Verletzung zaehlte,
muesste builder.run ohne verify laufen — Funktionsbruch.
Mit 'nur direkte Importe' ist die Regel praezise und
durchsetzbar.

**Echter Fund beim Erstlauf:**
import-linter deckte einen Strukturmangel aus OP-140 auf:
werkstatt/roles/__init__.py fehlte (nur
werkstatt/roles/builder/__init__.py angelegt). Python toleriert
das als Namespace-Package, grimp/import-linter nicht.
Nachgezogen — genau der Zweck des Tools: strukturelle
Schlampereien aufdecken, die bei Einzeldatei-Betrachtung
unsichtbar bleiben.

**Bewusst narrow statt voller ADR-0013:**
domain/ und infra/ existieren noch nicht. Nach OP-141 (state/)
und OP-143 (cli/) kommen die restlichen Regeln dazu (roles
kennen nur domain+infra, web kennt nicht roles direkt,
domain/infra importieren nur paths).

**Bekannte Grenze:**
Die 3 Regeln pruefen NICHT:
- Zirkelimporte zwischen Modulen ausserhalb dieser Pakete
- `werkstatt.*`-Top-Level-Module untereinander (loop, planner,
  builder als Flach-Module ohne Layer-Zuordnung)
Das kommt mit OP-143 (cli/ + Re-Export-Bereinigung), wo
loop.py aus dem Root in cli/ wandert.

**Sinn des Tools gegen Fehlerklasse aus dieser Session:**
Der bash-Fehler 'cmd | tail; $? liefert tail-rc' trat in dieser
Session 4x auf (OP-138, OP-139, OP-140, OP-144).
import_drift.py ist reines Python + subprocess.run(check=False),
$? wird nie durch Pipe verfaelscht. Das ist strukturelle
Absicherung gegen eine konkrete Fehlerklasse.

**Abnahme:**
- 1275 passed, 8 skipped.
- ruff . = 197 (unveraendert).
- audit_drift OK, control_drift OK, state_inventory OK,
  state_drift OK, state_flow OK, import_drift OK.
- Commit 30eef6e.

- Alle 6 Drift-Checks gruen.
- 9 verify.json-Stages (control_drift + state_drift + import_drift
  als harte Stages).


### 2026-11-06 — OP-166: last_verify_errors pro Task zuruecksetzen (Close)

**Work-Commit:** a720fe0 (`fix(loop): OP-166 — per-Task-State-Reset`)

**Ist-Stand (gemessen 2026-11-06):**

- `_reset_task_state` in `werkstatt/phases/_common.py:223`, gerufen
  aus `werkstatt/phases/tasks.py:107` **vor** jedem Task-Start.
  Setzt `last_verify_errors = []` und `reviewer_bugs = []`.
- `_verify_patches_soft` wird in `phases/tasks.py:522` gerufen —
  also **nach** dem Reset. Reihenfolge korrekt.
- `tests/test_verify_errors_reset.py` mit 4 Tests (collection
  RC=0, alle gruen).
- Akzeptanz (b) — Stage-Filter in `_verify_patches_soft` — **nicht
  implementiert**.

**Entscheidung zu AK (b):**

AK (b) wird **nicht** implementiert. Begruendung: `reflection.py:394-403`
(K50-Bug-C) haelt `last_verify_errors` bewusst kumulativ **innerhalb**
einer Task, damit mehrtaegige Reflection-Runden die vorherigen Fehler
nicht verlieren. Der Docstring von `_reset_task_state` dokumentiert
diese Semantik explizit:

> "Reset nur bei Task-Start. Innerhalb einer Task bleiben Fehler
> kumulativ (K50-Bug-C in reflection.py:394-403), damit
> Reflection-Runden zusammenhaengen."

Ein Stage-Filter in `_verify_patches_soft` waere entweder redundant
(weil `_reset_task_state` schon Task-Grenzen zieht) oder wuerde
K50-Bug-C regressen (Reflection saehe bei der 2. Runde die Fehler
der 1. Runde nicht mehr).

Die Task-Isolation ist durch (a) vollstaendig sichergestellt.
`test_zwei_task_isolation` belegt das deterministisch.

**Nebenbeobachtung (nicht Teil dieser OP):**

`tools/state_flow.py --field last_verify_errors` klassifiziert das
Feld als Risiko **HOCH**: 3 Writer ohne Contract, 6
getattr-only-Reader, 0 Reader mit Contract. Eine
State-Contract-Ergaenzung fuer `last_verify_errors` waere sinnvoll —
Vorschlag: OP-136c nach OP-136a/b-Muster. **Nicht hier geloest.**

**Entblockt:** OP-164b (Reviewer AUFTRAG-TREUE-Check bei
Rename-Aufgaben). Der Live-Test war zuvor nicht aussagekraeftig,
weil kumulative `last_verify_errors` den Effekt des
Auftrag-Treue-Filters maskieren konnten.

**Art der Aenderung:** nur `docs/STATUS.md` + `PROGRESS.md`. Kein Code.

**Baseline 2026-11-06 (vor Close-Commit):**
- pytest: 1273 passed, 5 skipped (Kontext-Block §5)
- ruff: 118 (gemessen 2026-11-06, `ruff check .`)
- Alle Drift-Checks gruen


### 2026-11-06 — OP-145 verworfen (wontfix) — neue OP-145b angelegt

**Messung 2026-11-06 (vor Design):**

Drei Felder mit unterschiedlicher Semantik, kein Alias:

| Feld | Zeile | Rolle |
|---|---|---|
| `auftrag_bereits_erfuellt` | state.py:256 | "ein Pfad hat es erkannt" |
| `auftrag_bereits_erfuellt_bestaetigt` | state.py:147 | "deterministisch bewiesen" |
| `auftrag_bereits_erfuellt_quelle` | state.py:148 | welcher Pfad |

Writer-Pfade (5):
- `planner:deterministic_precheck` -> T/T (planner.py:1450-1452)
- `planner:scout_llm_urteil` -> T/F (planner.py:1830-1832)
- `builder:llm_keine_patches` -> T/F (builder/run.py:353-355)
- `builder:old_nicht_da_aber_new_da` -> T/T (builder/run.py:452-454)
- `builder:alle_patches_no_effect` -> T/F (builder/run.py:921-923)

Reader-Muster (2):
- `tasks.py:218`: verlangt `_erfuellt` UND `_bestaetigt` (Task-Done)
- `plan.py:99,109` + `explorer.py:176` + `gates.py:435` +
  `builder/run.py:857`: lesen nur `_erfuellt` (skip plan gate)

`state_flow` zeigt fuer alle drei: Risiko HOCH (multi-writer(2-4),
keine Contracts).

**OP-145-Text war stale:**

- "nicht in state.py deklariert" -> falsch, `state.py:256`
  deklariert seit Commit 37ebf1e.
- "STATE-INVENTUR fuehrt als Ghost" -> falsch,
  `BASELINE_GEISTER = frozenset()` seit 37ebf1e (0 Geister).
- "24 Geister nach Rename" -> falsch, war 0 vorher, bleibt 0.

**Warum wontfix statt Rename:**

Die OP-145-AK forderte `_erfuellt` -> `_bestaetigt` umbenennen.
Das haette den Scout-Pfad (`planner.py:1830`) regressen:
Scout setzt bewusst `_erfuellt=True, _bestaetigt=False`, damit
`plan.py:109` (skip plan gate) triggert, aber `tasks.py:218`
(Task-Done) NICHT. Beim Rename waeren beide True -> falsches
Task-Done bei bloßer Scout-LLM-Vermutung.

**Nachfolger: OP-145b**

Statt Rename: State-Contract fuer die Familie. Ein zentraler
Writer-Helper `setze_auftrag_bereits_erfuellt(state, quelle,
bestaetigt)` ersetzt die 5 verstreuten Writer-Stellen. Doku
in `docs/STATE-INVENTUR.md`. Tests decken die 5 Kombinationen
und die 2 Reader-Muster ab.

**Kein Code geaendert.** Nur STATUS.md + PROGRESS.md.

**Baseline 2026-11-06 (vor diesem Commit):**
- pytest: 1275 passed, 8 skipped
- ruff: 118 (gemessen 2026-11-06, `ruff check .`)
- Alle Drift-Checks gruen


### 2026-11-06 — OP-168 als done geschlossen (Teilfix), OP-168b angelegt

**Befund 2026-11-06:**

`_phase_review_gate` existiert (`phases/review.py:11`) und ist
verdrahtet (`phases/finalize.py:117`), 6 Tests gruen. Was fehlt:
das Gate sitzt **nach** `_phase_end_reflection`, nicht zwischen
den internen Runden. Der Docstring von `_phase_review_gate`
markiert das selbst:

> "Teilfix: Gate sitzt NACH _phase_end_reflection, nicht
> zwischen den internen Runden. Vollstaendig: OP-168b."

**AK-Bewertung OP-168:**

| AK | Status |
|---|---|
| (b) Gate vor LOOP FEHLGESCHLAGEN | erfuellt (`finalize.py:117`) |
| (b) Gate `n` -> Loop endet sauber | erfuellt (`test_n_gibt_1`) |
| (a) Gate zwischen jeder Reflection-Runde | **fehlt** |

Da die verbleibende Arbeit in OP-168b passt und der Code selbst
schon auf OP-168b verweist: OP-168 auf `done`, OP-168b neu.

**Nachfolger: OP-168b**

Ruft `_phase_review_gate` zusaetzlich in `_phase_end_reflection`
nach jeder Reject-Runde. Ergaenzt 2 Smoke-Tests in
`tests/test_phase_review_gate.py`. Blockiert nicht.

**Test-Contract-Check:** `grep -rn 'OP-168' werkstatt/ tests/`
ergab 4 Treffer — alle Docstrings/Kommentare, keine Assertion
haengt an der OP-Nummer. Patch ist safe.

**Dry-Run-Fehler in Block C (dokumentiert):**

Erster Patch-Versuch verwendete `op168_block + "\n\n\n### OP-160:"`
als after_anchor. Falsch: OP-168 ist der **letzte** OP vor der
Delete-Zone. OP-160 und alle anderen OPs kommen **nach** der
Delete-Zone. Korrektur: `after_anchor = op168_block + "\n\n\n## Delete-Zone"`.
Der Dry-Run hat den Fehler gefangen, bevor irgendetwas geschrieben
wurde — genau der Zweck.

**Kein Code geaendert.** Nur STATUS.md + PROGRESS.md.

**Baseline 2026-11-06 (vor diesem Commit):**
- pytest: 1279 passed, 8 skipped
- ruff: 118 (gemessen `ruff check .`, `grep -- '-->'` zaehlt)
- Alle Drift-Checks gruen
## 2026-11-06T11:51:18+00:00 -- Phase abgeschlossen: werkstatt
- **Status:** phase_ende
- **Info:** tasks_ok=4/6

## 2026-11-06T11:52:42+00:00 -- Phase abgeschlossen: werkstatt
- **Status:** phase_ende
- **Info:** tasks_ok=5/6



### 2026-11-06 — Messung: Verify→Builder-Kette (OP-172)

**Kontext:** Nach ruff=0 + mypy=0 + alle Verify-Stages hart
(8c52cf3, b950b97) ist die Frage: **sieht der Builder die
Fehler auch, wenn ein Gate blockt?**

**Messung (read-only, kein Loop-Lauf):**

Drei Einschränkungen in der Kette Verify→State→Builder:

| Stelle | Code | Problem |
|---|---|---|
| `verify.py:479` | `_out[-500:]` | nimmt **letzte** 500 Zeichen = Statistik, nicht Fehler |
| `run.py:149` | `[:5]` | nur erste 5 Fehler |
| `run.py:149` | `[:500]` | pro Error auf 500 gekuerzt |

**Kette funktioniert strukturell:**
- `verify.py:492` → `state.last_verify_errors = list(errors)`
- `run.py:147-156` → `## VERIFY-FEHLER`-Block im Builder-Prompt
- `run.py:249-250` → `_format_repair_hint(...)` Klassifikation

**Kette funktioniert NICHT vollstaendig:**
- Bei mypy mit 20 Fehlern: Builder sieht 5
- Bei ruff `Found N errors`: `[-500:]` schneidet Fehler weg
- Bei langen mypy-Tracebacks: 500-Zeichen-Limit

**Konsequenz:** Gate blockt (gut), aber Builder bekommt
nicht genug Info zum Reparieren. Er ratet aus der Statistik.

**Folge-OP:** OP-172 — Verify→Builder-Kette verbessern.
Prioritaet hoch, weil ohne diesen Fix die Reflection-Runden
zwar laufen, aber nicht sinnvoll reparieren koennen.


### 2026-11-06 — OP-173 angelegt: Spec-Tests (RunState-Factory)

**Messung:**

- **262/263** `getattr(state, ...)`-Stellen in Prod beziehen
  sich auf DEKLARIERTE RunState-Felder (`state_inventory
  --check` bestaetigt 0 Ghost).
- **167 Test-Dateien** nutzen `SimpleNamespace` statt `RunState`.
- **28 `# type: ignore[attr-defined]`** in Prod bleiben noetig,
  weil `getattr` in Tests noetig ist.

**Kernproblem:**

Der `getattr`-Wald ist **notwendige Test-Kompatibilitaets-
Infrastruktur**, aber er kompromittiert die Test-Qualitaet:
Tests sagen nicht aus, welches Spec-Verhalten sie erzwingen,
sondern nur "dieser Codepfad laeuft ohne AttributeError".

**Profi-Ansatz:**

1. `RunState` mit Defaults fuer alle Pflichtfelder
2. `tests/factories.py::mk_state(**overrides) -> RunState`
3. 167 Test-Dateien migrieren
4. 262 `getattr` in Prod → `state.x` (mypy prueft dann)
5. Spec-Review der 20 wichtigsten Tests

**Aufwand:** 3-4 Sessions, ~13-15h.

**Warum jetzt:** Nach ruff=0, mypy=0, Verify-Kette hart ist
der Test-Unterbau die naechste Vertrauensstufe. Ohne
Spec-Tests testet der Loop gegen Attrappen — jeder weitere
Eingriff baut auf wackeligem Fundament.


### 2026-11-06 — OP-174 angelegt: Spec-Tests

Messung: 262/263 getattr in Prod deklariert (0 Ghosts),
167 Test-Dateien mit SimpleNamespace. Der getattr-Wald ist
Test-Kompatibilitaet, aber er kompromittiert Spec-Qualitaet.

OP-174 definiert P1-P6: RunState-Defaults, mk_state-Factory,
167 Tests migrieren, 262 getattr rueckbauen, 20 Spec-Reviews.
Aufwand ~13-15h.


### 2026-11-06 — OP-175: Loop-Test 6 zeigte 4 Bugs

Loop-Test 6 (18:27-18:31) mit OP-168b als Aufgabe: 0/4 Tasks,
4 Reviewer-Bugs, 5-Runden-Stagnation, kein Commit.

**4 bestaetigte Bugs:** Planner-Rueckwaerts-Deps (A),
5-Runden-Stagnation (B), Phase-Review-Kontext (C), Zombie-Feld
per setattr (D). Bug E (Verify-Stages 0s) **widerlegt** —
`_expand_cmd_placeholders` funktioniert korrekt, mein Test war
falsch (Datei existierte nicht).

**Erfolge trotz Muell:** 9/9 Verify-Stages hart griffen — nichts
committet. Reviewer hat D als medium-Bug gefangen. Ohne die
heutige Arbeit (ruff/mypy=0, ADR-0015) waere Muell in HEAD.

**Naechster Chat:** OP-175 als Auftrag, Reihenfolge A → C → B → D → E.
Bug E ist Investigation, kein Fix.

### 2026-11-06 — OP-175 abgeschlossen: 3 von 5 Bugs gefixt, 1 verworfen, 1 zurueckgezogen

Mit OP-175 als Auftrag gemessen und gefixt. Urspruengliches
Ziel (4 Bugs + 1 Investigation) hat die Messung nicht
bestaetigt — nur A, B, C blieben nach Messung uebrig.

Commits:
- 2538174 fix(phases): Bug C — Message 3 -> 2 Runden
- 6aa8694 fix(planner): Bug A — Topo-Sort nach deps
- f204965 fix(reflection): Bug B — verify_gleich als Stagnations-Grund

Bug D verworfen: Loop-Log 18:29:44 zeigt ruff B010 —
mypy+ruff+spec_widerspruch haben den Agent-Patch gefangen,
kein Repo-Bug. Haertung als OP-176 angelegt.
Bug E zurueckgezogen: 46 loop_verify-Events am Tag, 0s
korrekt (Heartbeat feuert erst ab 30s), Bug war Fehlmessung.

Was bleibt: OP-168b (Gate zwischen Task-Reflection-Runden)
ist weiterhin offen — Bug C im STATUS hatte das mit dem
Message-Bug vermischt. Loop-Test 7 kann jetzt laufen.

## 2026-11-06T19:55:52+00:00 -- Phase abgeschlossen: werkstatt
- **Status:** phase_ende
- **Info:** rc=1 tasks_ok=2/5


### 2026-11-06 — OP-168b abgeschlossen: Gate in _phase_end_reflection

Loop-Test 7 (18:27–19:55) mit OP-168b als Aufgabe. Reviewer hat 5 Bugs gemeldet, davon 3 HIGH — Messung zeigt: nur Test-Luecke berechtigt. Bugs 1/2/5 waren false positives (Reviewer interpretierte AK-Text falsch, Code liest `phase_review_auto` nach Gate-Aufruf statt davor).

Live-Beweise aus Loop-Test 7 fuer OP-175-Fixes:
- Bug A (Topo-Sort): 5 Tasks korrekt sortiert, keine Zyklen
- Bug B (verify_gleich): Stagnation-Abbruch nach 2 Runden (Loop-Log 19:44:44→19:44:46)
- Bug C (Message): "nach 2 Runden erschoepft" statt 3
- OP-172 bestaetigt: Verify meldet truncated `statt.reflection"` statt des echten mypy-Fehlers

Commit c713033: phase_review_auto + Gate in _phase_end_reflection. State_flow_baseline um phase_review_auto erweitert. Test-Spec 2 Smoke-Tests (test_reflection_reject_ruft_gate, test_gate_n_bricht_reflection_ab).

Bewusste Scope-Grenze: Task-Reflection-Gate in `_reflection_loop` ist NICHT umgesetzt — OP-Text nennt `_phase_end_reflection` als Ziel. Falls das spaeter gewuenscht wird, eigene OP.

Lehre: `pytest` ohne aktiviertes venv lief System-Pytest 7.2.1, fastapi fehlt dort → 7 Collection-Errors. Siehe Merkposten.

### 2026-11-07 — OP-178 abgeschlossen: Registry-Migration aller Aufrufer

ADR-0014 dokumentierte die Registry als Single Source of Truth, aber nur `architect.py` nutzte sie (Messblock 23). Migration in 3 Commits:

- **0388d1b** — planner/builder/reviewer/reflection: eigene Ladelogik durch `ROLLEN[name].lade_skills()` ersetzt. Verhaltensneutral.
- **8954f83** — Alias-Cleanup: `_ROLLEN_plan`/`_ROLLEN_b`/`_ROLLEN_r` durch direkten `ROLLEN`-Import ersetzt, damit Migration-Test greift.
- **5a5c941** — Explorer migriert + `systematic-debugging` raus. Explorer laedt nur noch `using-werkstatt`. `SKILL.md`-Frontmatter auf `rollen: [builder]` korrigiert.

Neuer Test `test_rollen_registry_migration.py`: AST-Scan ueber `werkstatt/` prueft, dass jede Rolle mit nicht-leeren `skills` oder `skill_filter_rolle` mindestens einen `ROLLEN[name]`-Zugriff hat. Failt bei kuenftigen Rollen, die die Registry umgehen.

Verhaltensaenderung Explorer: `systematic-debugging` gehoert semantisch zum geplanten Debugger (OP-128/OP-160), nicht zum Datei-Sucher. Test `test_explorer_system_kein_systematic_debugging` verbietet die alte Zuordnung. Loest ADR-0014-Offen-Absatz fuer 5 Aufrufer ein.

### 2026-11-07 — OP-176 abgeschlossen: contract_check-Haertung (Loop-Test 8)

**Loop-Test 8 (11:50-11:58)**: erster durchgelaufener Loop seit Tagen. 2/2 Tasks, Phase-Review approved, Commit `7eab26d` mit 192 Zeilen.

Der Loop baute eigenstaendig:
- `tools/contract_check.py` — `_state_felder()` + `_pruefe_setattr_aufrufe()` (AST-Walk, 64 Zeilen)
- `tests/test_contract_check_setattr.py` — 3 Unit-Tests (48 Zeilen)
- `tools/state_inventory.py` — Wiring ueber `--changed`-Pfad (31 Zeilen)
- `tests/test_verify_contract_stage.py` — 2 Integration-Tests fuer Ende-zu-Ende-Wiring (49 Zeilen)

Das Wiring und die Integration-Tests habe ich waehrend der `e`-Phase am Human-Gate ergaenzt (Commit-Message erwaehnt nur "Loop-Auftrag", 192 Zeilen im Diff). Der Loop hatte den Kern gebaut, aber vergessen an `state_inventory.py --changed` anzuschliessen — der Architect-Plan hat das Wiring implizit gelassen, ich habe es im `e`-Pfad nachgezogen.

**Bug D aus OP-175** (Agent versuchte `setattr(state, "phase_review_gate_auto", True)` mit nicht-deklariertem Feld) ist ab jetzt deterministisch gefangen — vorher nur durch ruff-Regel B010, also Zufall. Der AST-Walk prueft gegen `RunState.__dataclass_fields__`.

**Loop-Test 8 bewies:**
- Planner baut kleine Tasks (2) bei kleiner OP
- Builder + Reflection greifen (keine Fails → keine Reflection-Runde noetig)
- Phase-Review approved (Reviewer qualifizierte Bugs korrekt)
- Commit-Gate funktioniert (kein Auto-Approve)
- Audit-Kette vollstaendig: `reviewer_result` → `loop_phase approved` → `loop_human_gate_committed`

**Was noch fehlt:** Loop committet lokal, pusht nicht. Der Push muss manuell erfolgen — mache ich hier mit.

### 2026-11-07 — Loop-Test 9: AUFRUFER-PFLICHT greift, drei Bugs aufgedeckt

**Loop-Lauf (12:14-12:16, OP-181)**: 4 Tasks geplant, t1 gebaut, t2-t4 blocked. Phase-Review rejected (korrekt: t2/t3/t4 fehlen). Loop nach 5 Reflection-Runden abgebrochen (spec_widerspruch_erschoepft). Commit `7eab26d` **nicht** erstellt.

**Positiv:**
- AUFRUFER-PFLICHT aus Block 39b hat gegriffen: der Architect-Plan nannte den Aufrufer fuer `_pruefe_neue_module_genutzt` explizit in t3 (run_reviewer-Integration).
- OP-172-Fehlerkern-Extraktion funktioniert: der echte mypy-Fehler (`Duplicate module named werkstatt.reviewer`) ist jetzt sichtbar, nicht truncated.
- Bug-B (verify_gleich) hat nach Runde 3 den ersten Stagnations-Counter gesetzt.

**Drei aufgedeckte Bugs:**
1. **`_expand_cmd_placeholders` dedupliziert nicht.** Nach 5 Reflection-Runden hatte `state.patches` 5x `werkstatt/reviewer.py`. `mypy {changed_py_files}` expandierte zu 5 Argumenten, mypy meldete `Duplicate module named werkstatt.reviewer`. Kuenstlicher Fehler, nie behebbar. **Gefixt** (`dict.fromkeys`), 3 Tests.
2. **Katalog-Drift.** Builder baute `audit("reviewer_dead_code_parse_fehler")` ohne Eintrag in `_AUDIT_KINDS_BEKANNT`. `test_audit_warnung.py` hat es gefangen. **Gefixt** in audit.py.
3. **Bug-B-Luecke.** `verify_gleich` greift nicht bei alternierenden Fehlern (Stage-Sets wechseln PIE810 <-> Duplicate <-> beide). Counter sprang 1->0->1 statt 1->2->abort. **Als OP-182 angelegt.**

**Working Tree nach Loop-Abbruch committet in **einem** Commit:**
- t1-Feature (vom Loop gebaut, 101 Zeilen)
- verify.py Dedupe-Fix
- audit.py Katalog-Fix
- 3 Tests

OP-181 bleibt `partial`: t1 done, t2-t4 offen (Wiring in run_reviewer, REVIEWER_SYSTEM-Erweiterung, Tests). Naechster Loop-Lauf mit OP-181 in kompletter Form oder Loop-Test 10 mit anderer OP.


### 2026-11-07 — OP-182 abgeschlossen: verify_alternierend als Stagnations-Grund

Loop-Test 9 (2026-11-07 12:14-12:16) hatte 5 Reflection-Runden statt 2
gebraucht. Ursache gemessen: Verify-Fehler wechselten zwischen Runden
(ruff PIE810 / mypy Duplicate / beide). `_verify_fehler_zwischen_runden_gleich`
(OP-175 Bug B) vergleicht Stage-Sets mit exakter Gleichheit — bei
Alternation kein Match, Counter sprang 1->0->1 und die Erschoepfung-Heuristik
feuerte statt des Stagnation-Abbruchs.

Reproduktion vor Fix: `test_reflection_alternierende_fehler_stagniert`
in `tests/test_reflection_stagnation_verify.py` FAILte mit `assert True is
False` (Loop gab True zurueck via `spec_widerspruch_erschoepft`).

Fix in `werkstatt/reflection.py` (Commit `4de3a65`):

- Neue Funktion `_verify_fehler_alternierend(state)`: vergleicht
  Signatur-Sets via `_fehler_signatur_normalisiert`, True bei
  nicht-leerem Schnitt UND verschiedenen Sets (Alternative 2 aus dem
  OP-Text, weil zeilenunabhaengig und praeziser als Stage-Set-Overlap).
- Neuer Zweig in `_reflection_loop`: `elif _verify_fehler_alternierend(state):`
  setzt `_stagnation_grund = "verify_alternierend"`.
- Option Y: `_is_spec` wird bei `grund == "verify_alternierend"`
  uebersprungen — Alternation ist kein Spec-Widerspruch-Signal, sondern
  echter Task-Fail. Damit landet der Loop bei normalem `return False`
  statt `spec_widerspruch_erkannt=True`.

Tests:
- 5 Unit-Tests fuer `_verify_fehler_alternierend` (keine History,
  identisch, disjoint, overlap, applied=0).
- Integrationstest `test_reflection_alternierende_fehler_stagniert`
  (5 Runden, call_count<=4, spec_widerspruch_erkannt False).

Konsequenz: 3 Builder-Aufrufe statt 5 im Loop-Test-9-Szenario.
Voller pytest-Lauf: 1338 passed, 8 skipped. ruff/mypy sauber.
## 2026-11-07T13:23:18+00:00 -- Phase abgeschlossen: werkstatt
- **Status:** phase_ende
- **Info:** tasks_ok=1/4



### 2026-11-07 — OP-181 abgeschlossen: Reviewer-Dead-Code-Erkennung

Loop-Lauf 13:23 (OP-181 als Auftrag) baute t1 (REVIEWER_SYSTEM um
`DEAD-CODE-CHECK`-Abschnitt erweitert, Commit `9b700e3`), brach dann
ab: t2 war als Verifikations-Task formuliert (`_pruefe_neue_module_genutzt
auf Soll-Stand pruefen`), Planner waehlte `action: update`, Builder
setzte `auftrag_bereits_erfuellt`, Reviewer meldete HIGH-Bug
"Task-Beschreibung verlangt explizit die Funktion". Reflexion
lief 2 Runden (OP-182-Fix hat den 5-Runden-Reflex verhindert),
dann Human-Gate reject -> Loop-Ende nach 1/4 Tasks.

Manueller Nachzug in Commit `fdb01df`:

- **t3 (Wiring):** `run_reviewer` ruft
  `_pruefe_neue_module_genutzt(pd, diff)` nach
  `_filter_auftrag_treue_false_positives` und vor
  `audit("reviewer_result", ...)`. HIGH-Bug aus dem Pre-Check setzt
  `approved=False`. Merge nach den LLM-Filtern, damit
  Prompt-Heuristiken deterministische Befunde nicht wegfiltern.
- **t4 (Tests):** `tests/test_reviewer_dead_code.py` mit 3
  AK-(c)-Tests (neues Modul + nur Test-Import -> HIGH;
  neues Modul + werkstatt-Import -> kein Bug; bestehendes Modul
  geaendert -> skip) + AST-Wiring-Test
  `test_run_reviewer_ruft_pre_check_auf` (analog
  `test_rollen_registry_migration.py`).

Der AST-Wiring-Test ist eine begruendete AK-Erweiterung, keine
Scope-Ausweitung: Loop-Test 9 hat gezeigt, dass eine Funktion ohne
Aufrufer toter Code ist — genau das Anti-Pattern, das OP-181
aufdecken soll. Ohne den Test kehrt der Bug bei Refactors zurueck
(M-446-Lehre).

Pre-Commit-Gates: pytest 1342 passed, 8 skipped; ruff 0; mypy 0;
audit_drift / control_drift / state_inventory OK.

**Stufe-2-Kandidaten (aus diesem Lauf):**

- Planner-Task-Typ "pruefe/verifiziere X" braucht eigenes
  `action: verify` (kein Diff erwartet). Ohne diese Erweiterung
  verbrennt jeder Loop-Lauf mit Verifikations-Tasks 2 Reflection-
  Runden + 1 Reviewer-False-Positive.
- Loop schreibt in PROGRESS.md mit Format
  `## 2026-11-07T13:23:18+00:00 -- Phase abgeschlossen: ...`,
  nicht `### YYYY-MM-DD — OP-NNN abgeschlossen`. Format-Bruch.
- Loop committet lokal, pusht nicht (Konvention, aber Reibung im
  Workflow — manueller Push noetig).


### 2026-11-07 — Stufe-2-Planung: 3 OPs aus Loop-Test 10 angelegt

Loop-Lauf 13:23 (OP-181) hat drei strukturelle Schwaechen gezeigt,
die als OPs angelegt wurden:

- **OP-183** Planner-Task-Typ `action: verify` (hoechster Hebel).
  Verifikations-Tasks („pruefe X") werden vom Planner als `update`
  klassifiziert -> Builder setzt `auftrag_bereits_erfuellt` ->
  Reviewer meldet HIGH-Bug -> 2 Reflection-Runden + Loop-Abbruch.
  Fix: neuer Task-Typ ohne Builder-Pflicht.
- **OP-184** Loop-PROGRESS.md-Format. Der Loop schreibt
  `## ISO-Timestamp -- Phase abgeschlossen: <proj>` (M-307b), der
  Mensch `### YYYY-MM-DD — OP-NNN abgeschlossen`. Zwei Formate in
  einer Datei. Fix: OP-Extraktion aus `state.aufgabe`, analoger
  Header.
- **OP-185** Loop-Push-Option. `grep 'git push' werkstatt/` ist
  leer, Push ist komplett manuell. Fix: `--auto-push` (Default aus)
  + `--no-push`, Audit-Event bei Fehler, Loop bricht nicht ab.

**Nicht angelegt, aber vermerkt:** Loop schreibt `state.aufgabe`
nicht in den Phasen-Ende-Progress, daher ist OP-183 erst der
Voraussetzungs-Fix fuer aussagekraeftige Loop-Progress-Eintraege.
OP-184 setzt auf dem Ergebnis von OP-183 auf.

**Loop-Test 10 (nach OP-183):** Verifikations-Task + Bau-Task
in einer OP, Erwartung 3/3 done, keine Reflection-Runde, Commit.
Kandidat: OP-086 (Doku-Drift als Verify-Gate).


### 2026-11-07 — OP-187: Dependency-Hybrid im Planner

User-Anforderung aus Loop-Test 10: "Wenn der Architect
Abhaengigkeiten deklariert, muss der Planner diese auch in den
Tasks so planen."

Fix:

- `_check_explicit_keine_in_prosa`: erkennt explizite
  `- (keine)` im Architect-Block 5.
- `_leite_deps_deterministisch`: Architect-Aussage anwenden
  (Multi-File), Heuristik ergaenzend fuer Tasks OHNE
  Architect-Aussage, explizite `(keine)` stoppt Heuristik.
- Fallback-Pfad (JSON-Split-Fehler) ruft
  `_leite_deps_deterministisch` + `_topo_sort_tasks` auf.

Tests: `tests/test_planner_deps_hybrid.py` (10 Unit-Tests).

**Lehre:** Der LLM-Split ist eine Quelle, nicht die einzige. Wenn
er scheitert, muss der Fallback-Pfad dieselben Nachbearbeitungen
(Deps, Topo-Sort) durchlaufen — sonst sind Architect-Aussagen
still verloren.
## 2026-11-07T15:27:23+00:00 -- Phase abgeschlossen: werkstatt
- **Status:** phase_ende
- **Info:** tasks_ok=3/4



### 2026-11-07 — OP-183 abgeschlossen: Planner-Task-Typ `action: verify`

Loop-Lauf 15:24 hat t1-t3 + 3 von 4 Tests gebaut (Commit `c3e308f`):

- **t1** (Planner): `_ist_verify_task(name, description) -> bool` als
  deterministischer Pre-Check gegen die vier Marker `pruefe`,
  `verifiziere`, `stelle sicher`, `check`. `PLANNER_SPLIT_SYSTEM`
  um vierten Action-Wert `verify` erweitert (4 statt 3 Actions).
  `_korrigiere_aktion`-Vorspann ruft den Pre-Check vor der
  LLM-Korrektur — die Klassifikation kann nicht überschrieben werden.
- **t2** (`phases/tasks.py`): verify-Zweig in `_phase_tasks_loop`
  direkt nach `_is_read`. Ruft `_verify_patches` + `run_reviewer`,
  **nicht** `run_builder`. Kein neues Audit-Event (Katalog-Drift
  vermieden — der bestehende `loop_task_start`-Event reicht).
- **t3** (`reviewer.py`): `_filter_auftrag_treue_false_positives` um
  optionalen `action`-Parameter erweitert. Bei `action="verify"`
  werden Bugs der Form "Diff fehlt Datei X" / "Task verlangt
  Funktion Y, Diff hat sie nicht" rausgefiltert — bei Verify-Tasks
  sind das korrekte Beobachtungen, keine Bugs. `_reviewer_system`
  hängt bei `action="verify"` einen VERIFY-TASK-Block mit
  Diff-Erwartung: leer vor den Standard-Prompt.

**t4-Problem (3/4 Tests grün):** `test_verify_setzt_kein_auftrag_bereits_erfuellt`
fehlte. Reflection konnte ihn nicht fertigstellen, weil die
Test-Datei zu groß war. Manuell nachgezogen als deterministischer
Text-Scan-Test: prüft per `find("_is_verify")` → `find("continue")`,
dass der verify-Block `auftrag_bereits_erfuellt` nicht setzt.
Robuster als Mock-basiert, weil er die AK direkt prüft.

**Lehre für Loop-Test 10 (Kandidat für eigenes OP):**
Reflection scheitert bei Test-Tasks mit >3 Assertions, wenn der
Builder die gesamte Test-Datei in einem Task plant. Konsequenz:
Test-Tasks im Planner auf max ~50 Zeilen / ~3 Tests pro Task
begrenzen, oder Test-Datei-Erstellung als `action: create`
atomarer behandeln.


### 2026-11-07 — Stufe 2: Test-Loop-Serie angelegt (OP-188 bis OP-195)

Nach 6+ Stunden Loop-Arbeit (OP-182, 183, 186, 187 geschlossen)
und vollstaendiger IST-Messung des Loops wurde die naechste
Architektur-Stufe als Doku vorbereitet:

- **3 ADRs:**
  - **ADR-0016** (Spec-First Test-Loop) — Tests vor Code,
    Qualification + Freeze, Test-Thaw, Builder test-blind.
  - **ADR-0017** (Mutation-Gate mit pytest-gremlins) — stable
    1.13.2, native pytest-Integration, Score-Schwelle 0.8,
    `hart: false` im ersten Rollout.
  - **ADR-0018** (Debugger als eigene Rolle) — 3-Wege-Check
    (Spec, Code, Test), `systematic-debugging` wandert von
    `builder`/`reflection` zu `debugger`.

- **8 OPs:**
  - **OP-188** Test-Loop-Phase mit Qualification und Freeze.
  - **OP-189** Builder test-blind + verify-Stages
    `test_integrity`/`test_must_fail_initial`.
  - **OP-190** Mutation-Gate als verify-Stage.
  - **OP-191** Debugger-Rolle mit 3-Wege-Check.
  - **OP-192** Test-Thaw-Mechanik.
  - **OP-193** Hypothesis als optionale Dependency.
  - **OP-194** Architektur-Doku aktualisieren.
  - **OP-195** `pyproject.toml` Package-Registrierung +
    test-tools.

- **Reihenfolge:** 195 -> 188 -> 189 -> 190 parallel 193;
  188 -> 191 -> 192; 194 nach 188+191.

**Bewusste Einschraenkungen dieser Session:**
- Kein Code geschrieben ausser den heute geschlossenen
  Bugfixes (OP-182, 183, 186, 187).
- Keine Aenderung an `pyproject.toml`, `requirements.txt`,
  `pytest.ini`, `mypy.ini`.
- OP-092 nicht aktualisiert — der Sammel-OP-Text referenziert
  noch `pipeline_phases.py` (existiert seit OP-139 nicht).
  Das ist eine eigene Aufgabe (siehe unten).

**Naechste Session (Stufe 3):**
- OP-195 bauen (`pyproject.toml`).
- OP-092-Body aktualisieren: `pipeline_phases.py`-Referenzen
  raus, auf `phases/tasks.py` umstellen. Sub-Items 092c/092d
  als ausgelagert markieren (-> OP-188, OP-191).
- Danach OP-188 bauen.

**Benchmark-Ergebnis (2026-11-07):**
- pytest-gremlins 1.13.2 auf Mini-Modul (4 Funktionen, 4
  naive Tests): 18 Mutanten, 15 zapped (83%), 3 survived
  (17%), 6s Laufzeit.
- cosmic-ray 8.7.0: ConfigError in isoliertem venv.
- `hypothesis` 6.170.15 verfuegbar.


### 2026-11-07 — SOLL.md: Ziel-Architektur dokumentiert

Nach Session mit 10 Commits (OP-182, 183, 186, 187 + ADRs 0016-0018
+ OPs 188-195) ist die Ziel-Architektur in `docs/SOLL.md`
festgehalten (708 Zeilen).

**Inhalt SOLL.md:**

- **Vision in einem Satz:** Mensch arbeitet mit Web-UI, Loop ist
  Motor, Chat ist Interface, Erfahrungs-Gehirn ist Gedaechtnis.
- **4 Schichten** (Loop, Chat, Chat-Debugger, Gehirn) mit
  je eigenen Skizzen.
- **7-Phasen-SOLL-Pipeline** (Test-Loop + Mutation-Gate sind neu).
- **3 Kernprinzipien** (Mensch entscheidet, Loop ist Motor,
  Tests sind Spec).
- **6 Stufen** mit 23 OPs (13-23) und expliziten Abhaengigkeiten.
- **Glossar** (25+ Begriffe).
- **Lese-Anleitung** fuer LLMs, Menschen, neue Chats.

**Korrekturen gegenueber frueherer OP-Serie:**

- **OP-191 entfernt.** War doppelt zu OP-128 (Debugger ist
  Chat-Modus, keine eigene Loop-Rolle).
- **OP-192 umformuliert.** Test-Thaw gehoert an OP-188
  (Test-Loop-Phase), nicht an Debugger.
- **OP-188 erweitert** um AK (g) Test-Thaw-Mechanik integriert.

**README neu** (~348 Zeilen): 4 Schichten statt nur Test-Loop,
Verweis auf docs/SOLL.md.

**ARCHITECTURE.md** (184 Zeilen): Blockquote-Verweis auf SOLL.md
als Ziel, mit Widerspruchs-Regel ADR > SOLL.md > ARCHITECTURE.md.

**Keine Code-Aenderung** in dieser Erweiterung — reine Doku.

**Naechster Schritt (Stufe 1):** OP-123 (Gate-Bridge) +
OP-195 (pyproject) bauen — Voraussetzung fuer Loop-headless
und test-tools.


### 2026-11-07 — Doku-Nummern-Mapping auf 2XX

Nach OP-Umnummerierung (`e24e307`) sind alle Referenzen in SOLL.md,
ADR-0010/0016/0017 und README.md auf 2XX-Nummern umgestellt.

- 5 Dateien, konsistente 2XX-Referenzen.
- OP-191 (geloeschte Debugger-Rolle) in README durch OP-240
  (Chat-Debugger-Modus) ersetzt.
- Historische done-OPs (181, 182, 183, 186, 187, 122) bleiben als
  Erwaehnung im Text.

Kein Code geaendert.


### 2026-11-07 — planner_gate: Dotfiles-Whitelist (.gitignore)

Loop-Lauf OP-201 (19:38) brach ab: Task t3 aenderte `.gitignore`,
`TASK_FILE`-Regel lehnte ab (`.gitignore` endet auf kein
`_VALID_SUFFIXES`-Suffix, matcht kein `_DOKU_PATTERNS`). Weil
`TASK_FILE` in `_STRUKTURELLE_REGELN`, kein Reflection-Retry,
Loop sofort tot.

Fix: `_DOTFILES`-Frozenset mit den ueblichen Dotfiles
(`.gitignore`, `.gitattributes`, `.dockerignore`,
`.editorconfig`, `.gitkeep`). In der TASK_FILE-Schleife:
`if f in _DOTFILES: continue` vor dem Suffix-Check.

3 neue Spec-Tests in `test_hooks_planner_gate_suffixe.py`
(`test_gitignore_erlaubt`, `test_gitattributes_erlaubt`,
`test_dockerignore_erlaubt`). Hook-Direktaufruf mit den
6 OP-201-Tasks: `allow: true`.


### 2026-11-07 — OP-201 abgeschlossen: pyproject Paket-Registrierung

Loop-Lauf 19:46-19:56 (erster echter Loop mit 2XX-Nummern):
6/6 Tasks gebaut, dann Phase-Review rejected wegen 3 roter Tests.
Loop per Human-Gate `n` abgebrochen, Arbeit manuell nachgezogen.

**Vom Loop gebaut:** `[project]` in `pyproject.toml`,
`[project.optional-dependencies].test-tools`,
`[tool.setuptools.packages.find]`, `[tool.pytest-gremlins]`,
`docs/ARCHITECTURE.md §1.5 Installation`, 2 Test-Dateien.

**Phase-Review-Bugs (Test-Agent hatte AK zu woertlich genommen):**
- `test_pytest_laeuft_ohne_installiertes_package` wollte
  `testpaths`/`python_files` in `pytest.ini` -> `pytest.ini` ergaenzt.
- `test_requirements_txt_hat_zwei_kommentar_zeilen_fuer_test_tools`
  zaehlte nur 1 Kommentarzeile mit Marker -> beide mit
  `hypothesis`/`pytest-gremlins` benannt.
- `test_pytest_tests_laeuft_mit_installiertem_package` schlug fehl,
  weil `pytest --collect-only` im Subprocess `tools/quality_gate.py`
  importierte und das `sys.exit(0)` beim Modul-Import
  INTERNALERROR warf. **Echter Prod-Bug** in `quality_gate.py`:
  Guard vom Import in `main()` verschoben.

**Manuelle Abnahme:** `pip install -e ".[test-tools]"` gruen,
`pip show werkstatt` -> Version 0.1.0, `hypothesis 6.170.15` +
`pytest-gremlins 1.13.2` aktiv, `pytest` 1384 passed.

**Entblockt:** OP-214 (Mutation-Gate) und OP-215 (Hypothesis).


### 2026-11-07 — OP-217 angelegt + ADR-0016-Nachtrag + kontext-Update

Nach OP-201 (Loop-Lauf 19:46-19:56) wurde das systematische
Problem dokumentiert: der Test-Agent prueft Config-Details
(pytest.ini, requirements.txt), statt Spec-Verhalten.

- **ADR-0016-Nachtrag:** "Test-Agent prueft Verhalten, nicht
  Config-Details". Konkrete Regel: Config-Dateien sind
  Implementierungs-Detail. Test-Spec-Schema erweitert um
  `expected_behavior` + `verification`.
- **OP-217 (Test-Agent-Spec-Qualitaet):** neuer OP, blockiert
  von OP-210 und OP-212. Adressiert das Muster direkt.
- **`tools/werkstatt_kontext.py`:** Identitaets-Abschnitt
  erweitert um SOLL/ZIELBILD-Verweis. Regeln Punkt 7
  aktualisiert auf "Status 2026-11-07": 18 ADRs, 2XX-OPs,
  SOLL-Pipeline, Test-Agent-Regel, produktive Tools inkl.
  state_flow.py (Test-Konsistenz-Anker).

Kein Code geaendert (nur Doku + Kontext-Generator).


### 2026-11-07 — OP-212 (Test-Spec-Validator) — Code + Tests

Code-Baustein fuer Spec-First Test-Loop gebaut, Verdrahtung in
OP-210 (Test-Loop-Phase) bleibt offen.

**Neu:**
- `werkstatt/test_spec.py` — `TestSpec`, `AcceptanceCriterion`
  Dataclasses, `validate_schema()` (Pflichtfelder, Duplikate,
  verification-Enum), `parse_test_spec()` (akzeptiert auch
  unvollstaendige Specs fuer Validator-Reporting).
  `TestSpec.__test__ = False` verhindert pytest-Collection-Warning.
- `werkstatt/test_spec_validator.py` — `validate_test_spec(
  original_requirement, spec, api_key)`. Deterministische
  Smoke-Test-Heuristik (AK mit verification=file_content auf
  Config-Datei, die im OP-Text NICHT genannt ist) plus
  LLM-Validator-Call mit eigenem Prompt. Fail-closed bei
  fehlendem api_key, LLM-Fehler oder unparsebarer Antwort.
  Robuster JSON-Parser (Slice + Klammern-Repair).
- `tests/test_test_spec.py` — 11 Schema-Tests.
- `tests/test_test_spec_validator.py` — 14 Tests (4x Heuristik,
  4x Parser, 6x validate_test_spec inkl. Fail-closed-Faelle).

**OP-212 AK-Status:**
- (a) `validate_test_spec` mit `ValidationResult` — done
- (b) Eigener LLM-Call mit eigenem Prompt — done
- (c) Mehrdeutigkeiten fuehren zu Human-Gate VOR Test-Loop
  — offen, braucht OP-210
- (d) `test_spec`-Struktur erweitert — done
- (e) Tests — done (25 Tests)

**OP-217 AK-Status:**
- (a) `expected_behavior` + `verification` — done (in test_spec.py)
- (b) Test-Agent-Prompt-Regel — offen (Test-Agent existiert
  noch nicht, kommt in OP-210)
- (c) Post-Test-Validation — offen (OP-210)
- (d) Config-Integritaets-Trennung — done (Smoke-Test-Heuristik
  in test_spec_validator.py)
- (e) Tests — teilweise (Validator-Seite done)
## 2026-11-08T01:23:47+00:00 -- add-Funktion in math_utils.py anlegen
- **Status:** done

## 2026-11-08T01:24:32+00:00 -- Tests fuer add in test_math_utils.py anlegen
- **Status:** done


### 2026-11-08 — Web-UI-Stack + Gate-Lifecycle + Audit-Human-Readable

Massive Session. Werkstatt hat jetzt ein vollstaendiges Web-UI mit
Chat, Timeline, Audit-Kalender und Gate-Panel. Gate-Lifecycle
strukturell geloest. ~26 Commits, c0f4542 bis 856f1f0.

**Gate-Bridge (OP-202):** Loop wartet auf HTTP statt stdin.
`gate_bridge.py` mit `wait()`, `signal_open()`, `expire_for_run()`.
`--headless`-Flag im Loop-CLI. Endpoints `POST /api/runs/{id}/gate`,
`GET /api/runs/{id}/gates`.

**Chat-Stack (OP-230/231/232):** Alter Admin-Chat komplett ersetzt.
`ChatSession` (SQLite, pro Projekt, fork-faehig), `chat_tools.py`
(8 read-only Tools), `chat_agent.py` mit Token-Streaming.

**Timeline + Layout (OP-233):** 3-Spalten-Grid (Runs / Timeline /
Chat), Workbench-Drawer (Audit/Terminal/Diff/Verify/Dateien),
Statusleiste mit Token-Anzeige. Timeline gruppiert nach Rolle,
Klick auf Kind oeffnet Rollen-Drawer.

**Quality-Gate (OP-295):** Parser clean-safe, Baseline
ruff/mypy/katalog=0, Regression nur bei delta > 0.

**Informed Gate (OP-298):** Gate-Panel zeigt Plan, Scout-Findings,
Diff, Verify, Reviewer-Verdict, Empfehlung. Draggable.

**Gate-Lifecycle (ADR-0019):** PID/Heartbeat/Timeout verworfen.
try/finally in main() -> loop_ended/loop_failed -> expire_for_run().

**Token-Tracking:** ask_llm in Explorer/Scout/Architect/Reviewer
mit state=state — llm_usage-Events kommen jetzt an.

**Audit-Kalender (OP-311):** Collapsible Kalender mit Tages-Filter.

**Audit Human-Readable (ADR-0020):** _humanSummary() pro Kind.

**Rollen-Detail-Ansicht (ADR-0021):** WerkstattDetail.oeffneRolle().

**Tests:** 1439 passed, 8 skipped. ruff clean, mypy clean.


## 2026-11-08 — OP-300 Semantic Colors System (Commit 320b029)

Farbsystem semantisch. 6 Rollen (`--sem-action`, `--sem-active`,
`--sem-ok`, `--sem-warn`, `--sem-error`, `--sem-history`),
7 Shades, 4 Struct-Variablen im `:root`. 57 Hex-Vorkommen
ausserhalb `:root` ersetzt in `static/layout.css`. chat.css
hatte schon 0 Hex (blieb unangetastet).

**Bewusste Farbwechsel (Design-Entscheidung mit User):**
- Explorer-Cyan `#06b6d4` -> `var(--sem-active)` (blau)
- `.diff-hunk` -> `var(--sem-active)` (Diff im laufenden Build
  ist Ist-Zustand, nicht Vergangenheit)

**Guard:** `grep -cE "#[0-9a-fA-F]{6}"` ausserhalb `:root` == 0.
pytest 1437 passed, ruff/mypy 0, alle 5 Drifts 0.

**Lehre (in MERKPOSTEN aufnehmen):** Erstversuch zerstoerte
`:root`-Block durch fehlerhaftes Reassembly (`s = body` statt
`s = head + neuer_root + tail`). In-Python-Guard `SEM==0` hat
Commit verhindert. Zweiter Versuch mit Guards **vor** `write_text`
erfolgreich. Konsequenz: bei "ausschneiden und wieder einsetzen"
immer Reassembly explizit, nie `s = body`.

**Strukturelle Altlast entdeckt:** zwischen
`## Erledigt (Auto-Log)` und `## Delete-Zone` stehen 16 offene
OPs (OP-263, OP-257, …, OP-241) faelschlich unter Auto-Log.
Eigene OP noetig (Doku-Aufraeumen).

**Nachfolge-OPs entblockt:** OP-301 (Ambient Status Bar),
OP-302 (Command Palette), OP-307 (Chat Tool-Call-Karten),
OP-311 (Audit-Filterleiste), OP-315 (Causal Chain). OP-303 und
OP-306 bleiben an OP-301 gebunden.


## 2026-11-08 — OP-321 JSONL-Trennung stream/semantic (Commit de3be1e)

Zwei JSONL-Streams: semantic (git) + stream (gitignore).
_STREAM_KINDS = {log_line, progress, spinner, heartbeat, task_started,
task_done}. Fail-closed: unbekannter Kind geht in Semantic.
event_id = sha256(run_id|audit_id)[:16] in beiden Funktionen.
_publish in emit.py ruft zusaetzlich audit()/stream(); SQLite-Write
bleibt als Uebergangsphase bis OP-323.

Tests: test_audit_stream_klassifikation.py (5). pytest 1442 passed.


## 2026-11-08 — OP-322 Projector (rebuild/tail/status)

werkstatt/projection.py: JSONL (semantic + stream) -> SQLite.
rebuild() deterministisch (DELETE + replay), tail() idempotent per
event_id UNIQUE + INSERT OR IGNORE, status() liefert jsonl/sqlite/diff.
Checkpoint in projection_state. 6 neue Tests (test_projection.py).
pytest 1448 passed.


## 2026-11-08 — 14 neue OPs (Scriptbank + Loesungsorientierung + Scaffolder + Greenfield)

Vier Komplexe, auf Basis Ist-Zustand:
scaffold.py existiert (CLI), chat_tools.py 8 Tools, Reviewer-Bug
{file, line, description, severity} ohne Loesungsfelder.

**Scriptbank (OP-330..334):** Manifest + 6 Kern-Scripts +
Scaffolder-Vertrag + Chat-Integration + Reflection-Integration.

**Loesungsorientierung (OP-340..342):** Reviewer-Bug-Schema
{warum, wie_loesen, beispiel_ohne_code}. Reflection + Hook +
Gedaechtnis auf gleichen Vertrag. Prompt-Engineering Lichtkegel.

**Scaffolder-UI (OP-350..352):** Greenfield-Modus + UI-Maske
+ Drift-Check.

**Greenfield-Architekt (OP-360..362):** Senior-Architekt-Skill
+ Dialog-Flow + Plan-Artefakte.

Blocker-Ketten:
330 frei; 331<-330; 332<-330; 333<-330,331; 334<-331;
340 frei; 341<-340; 342<-340,341;
350<-332; 351<-350; 352<-350,351;
360<-282,350; 361<-360; 362<-360,361.


## 2026-11-08 — OP-341 AK erweitert (kausale Rekonstruktion statt nur Delta)

User-Klarstellung: Delta allein reicht nicht. Der Reviewer muss
(1) Zeilen-Kontext pro Bug tragen (file, line_start, line_end,
code_ausschnitt), (2) ALLE vorherigen Runden sehen (nicht nur
n-1), (3) pro bestehendem Bug die kausale Kette liefern
("Patch Runde N hat Zeile X geaendert, dadurch brach Zeile Y"),
(4) Delta klassifizieren (bestehend|behoben|neu|verschoben).

Der alte Vorschlag + Grund des Scheiterns sind Teil des Prompts,
nicht nur des Logs. Nur so kann der Builder aus seinen Fehlern
lernen statt neu zu raten. Zirkel-Falle: ohne kausale Rekonstruktion
dreht der Loop im Kreis.

AK (a)-(h), Tests 5 -> 8.


## 2026-11-08 — OP-370 (detect) + OP-350 AK (.env-Schutz)

**OP-370: detect() — Secret-Detection ohne Redaction.**
Nachnutzen statt redact+restore: detect() findet IPv4/6, API-Keys,
E-Mails, credential_urls, private_paths in Payloads. audit()
schreibt secret_detected-Event (Typ, nicht Wert). Statusbar warnt.
Keine Redaction, keine LLM-Aenderung. Begruendung: Werkstatt baut
Code, kein User-Daten-Pipeline. Restore-Risiko > Leak-Risiko.

**OP-350 AK erweitert um .env-Schutz.**
Scaffolder schreibt excluded_from_explorer-Liste in
.werkstatt/script-bank.yaml. .env-Template mit Platzhaltern.
Explorer respektiert die Liste fail-closed.

Industrie-Beleg (Cursor/Claude Code): Zugriffsvermeidung robuster
als Redaction fuer Code-Pipelines.


## 2026-11-08 — OP-304 + OP-305 (Shortcut-Help + Klickwege + Projekt-Anlage)

**OP-304 Shortcut-Help-Overlay (?-Taste):**
`?` oeffnet Overlay mit Kategorien (Navigation, Chat, Palette),
kbd-Boxen, Footer-Hinweis. Ausserhalb von Input-Feldern aktiv.
6 Tests.

**OP-305 Utility-Bar + Klickwege + Projekt-Anlage:**
- `⌘K` und `?`-Buttons in Tab-Leiste (Klickwege parallel zu Shortcuts).
- `Alt+N` fuer Projekt-Anlage (statt `Shift+N` — Chrome-Konflikt).
- `+`-Button funktional: Modal mit Name/Pfad, Auto-Fill `/opt/<name>`,
  Backend `POST /api/projects/create` (scaffold + Validierung).
- Ambient-Bar zeigt aktives Projekt prominent (◆ + fett).
- Multi-Projekt-Sicherheit: `_PROJECTS_BASE`-Konstante (testbar via
  monkeypatch), `/start` validiert docs/STATUS.md (404 sonst), `/ops`
  + Palette projekt-spezifisch.

**Lehren aus der Session:**
- Python-Docstring `"""..."""` in JS = SyntaxError beim Browser.
  Der Fehler war unsichtbar bis Cache-Buster + Hard-Refresh. Konsequenz:
  JS-Files immer mit `node --check` validieren vor Commit.
- `if (false) {  // comment    code` schluckt function-Definition im
  Kommentar. Bracket-Matcher identifizierte 72-Zeilen-Block. Konsequenz:
  tote Bloecke loeschen, nicht auskommentieren.
- Clone-von-tab-neu brach insertBefore-Referenz in tabs.js. Dynamischer
  Lookup (getElementById) statt gespeicherter Referenz.
- `Path("/opt")` hardcoded in Produktion ist untestbar. `_PROJECTS_BASE`-
  Konstante auf Modul-Ebene + monkeypatch in Tests.
- Auth-disable: `auth._AUTH_DISABLED` (nicht `_AUTH_DISABLED_OVERRIDE`).

19 Tests insgesamt (4 Help + 5 Utility + 11 Project-Create/Multi-Projekt).
pytest 1515 passed.

**Bewusst offen (3 neue OPs angelegt):**
- OP-306a Tab-Persistenz (Reload behaelt Tabs)
- OP-306b Projekt-Selector (alle /opt/-Projekte sichtbar)
- OP-306c Multi-Projekt-Datenquellen (SQLite project-Spalte fuer
  /ambient /status /timeline /tokens)

pytest 1515 passed.

## OP-306a: Tab-Persistenz via localStorage (2026-11-08)

**Commit:** f5d333a

**Was:** `static/tabs.js` persistiert offene Tabs in
`localStorage["werkstatt-tabs:v1"]`. Bei Reload werden sie
wiederhergestellt (Shape-Validierung, Debouncing, In-Memory-Fallback
bei localStorage-Fehler, `removeItem` bei 0 Tabs).

**Implementierungs-Details:**
- `_persistiere_tabs()`: 50ms debounce, Shape-Validierung,
  `removeItem` bei 0 Tabs
- `_lade_gespeicherte_tabs()`: JSON.parse + Array- und
  projekt-String-Validierung (defensiv gegen korrupte/manuell
  editierte Daten)
- `_rehydriere_laeuft`-Guard gegen Persist waehrend Rehydration
- Rehydration ersetzt hardcoded `startId = neuerTab("werkstatt")`
- Zaehler waechst beim Rehydrieren mit, keine ID-Kollision

**Tests:** `tests/test_ui_tab_persistenz.py` (14 Tests, Spec-First
nach ADR-0015/0016): `TabSpiegel`-Klasse bildet JS-Verhalten nach.
10 Verhaltens-Tests (leerer Storage -> Default, gespeichert ->
wiederhergestellt, korruptes JSON -> Default, stale -> gefiltert,
Zaehler-Kollision, letzter Tab loescht Key, finale Persistenz,
Aktiv-Persistenz). 4 Drift-Guards (Key-Literal im JS, Funktions-
Existenz, Klammer-Balance als node--check-Ersatz, Cache-Buster-
Synchronitaet).

**AK-Anpassungen (User-bestaetigt 2026-11-08):**
- Key `werkstatt-tabs:v1` statt AK-`werkstatt_tabs` (Versionierung,
  Schema-Migration moeglich)
- Test-Datei `test_ui_tab_persistenz.py` statt `test_tabs_persist.py`,
  14 statt 4 Tests (Spec-First)
- AK-Punkt (f) als Lesart A interpretiert: leerer Storage -> Default-
  Tab `werkstatt`. Overview-Screen als Startansicht wird OP-306b
  (Workspace-Overview-Shell), nicht in OP-306a.

**Geaendert:**
- `static/tabs.js`: +100 Zeilen (Konstanten + Helper + Rehydration)
- `static/layout.html`: Cache-Buster synchron auf 1794171554
- `tests/test_ui_tab_persistenz.py`: neu (14 Tests)

**pytest:** 1521 passed, 5 skipped.

**OP-306b wird aufgewertet** zu "Workspace-Overview-Shell"
(Projekt-Karten + Sparklines + KPI + Home-Navigation) — Startansicht
wird Overview statt Default-Tab. Siehe STATUS.md OP-306b.

## OP-306c: Multi-Projekt-Datenquellen (2026-11-08)

**Commits:** 71cc471 (Etappe 1 Schema), 60a0f92 (Etappe 2 Writer),
0ce6852 (Etappe 3a Reader SQL), 62a6cdd (Etappe 3b Reader ambient+timeline)

**Was:** SQLite `events`-Tabelle bekommt `project`-Spalte. Alle
aggregate_*()-Funktionen filtern nach aktuellem Projekt. Der
test16-Tab zeigt keine Werkstatt-Daten mehr.

**4 Etappen, jede einzeln committet:**

**Etappe 1 (Schema):**
- `Projector._init_schema`: CREATE + ALTER TABLE fuer project TEXT
  NOT NULL DEFAULT 'werkstatt', idempotent per PRAGMA-Check
- Neuer Index idx_events_project_seq fuer schnelle Filter
- Migration auf Live-DB: 410.754 Zeilen bekommen 'werkstatt'
  (alle bisherigen Events stammen aus Werkstatt, kein Backfill
  aus JSONL — der ist ohnehin juenger als SQLite)

**Etappe 2 (Writer):**
- `Projector._insert`: project aus JSONL in Spalte, aus payload
  entfernt (single source of truth)

**Etappe 3a (Reader SQL):**
- `_letzter_run_id(es, projekt='werkstatt')` — zentrale Stelle mit
  WHERE project=?
- `aggregate_status`: 4 Queries + project
- `aggregate_tokens`: llm_usage-Query + project
- `aggregate_ops_run_status`: run_to_op-Ermittlung + project
- `aggregate_ambient`: NUR _letzter_run_id-Aufruf (Queries kamen
  in 3b)

**Etappe 3b (Reader ambient + timeline):**
- `aggregate_ambient`: 7 Queries (heartbeat, loop_erfolg,
  loop_failed, loop_ended, gate_open/answered/expired) + project
- `aggregate_timeline`: JSONL-Events nach project filtern
  (Fallback 'werkstatt' fuer Events vor OP-306c); explizites
  run_id umgeht Filter

**AK-Anpassungen (User-bestaetigt, ehrlich dokumentiert):**
- AK (c): `audit()`/`stream()` schrieben `project` schon vor
  OP-306c ins JSONL (audit.py:141/179). War bereits erfuellt.
- AK (f): Frontend-URLs waren schon `/api/projects/{name}/...`.
  War bereits erfuellt.
- Tests: 10 statt 8 (6 in Etappe 3a: _letzter_run_id-Filter,
  status/tokens/ops_run_status-Filter, leeres Fremdprojekt,
  Default ohne Projekt-Arg. 4 in Etappe 3b: ambient-heartbeat,
  ambient-loop_erfolg, ambient-gates, timeline-JSONL-Filter).

**Live-Verifikation nach Etappe 3b:**
- werkstatt: loop_status=done, gates_open=0
- test16: loop_status=idle, gates_open=0

**Test-Setup-Anpassung:** `_store` in test_ambient_aggregation.py
und test_ops_run_status.py ruft `Projector(db_pfad=db)` VOR
`EventStore(db)` — legt 9-Spalten-Schema an. `_event`-Helper ohne
project-Spalte nutzt DEFAULT 'werkstatt'.

**pytest:** 1533 passed, 5 skipped.

**Bugs unterwegs, alle in MERKPOSTEN:**
- Etappe 1: Verifikation kam NACH Commit statt davor → Live-DB
  war nicht migriert, obwohl Commit-Message es behauptete.
  Nachgeholt mit Etappe 1.5 (Projector() aufrufen).
- Etappe 3a-Versuch-1: `_store`-Patch Anker nicht gematcht
  (Top-Level-Import statt inline), Script brach ab, DB blieb
  7-Spalten → 8 Test-Fails. Erst nach exakter Messung mit
  `sed|cat -A` korrigiert.
- Etappe 3a-Versuch-2: `cmd | tail; $?` misst tail-rc, nicht
  cmd-rc. Diagnose-Block lief trotz roter Tests durch. Merkposten
  bereits 4x dokumentiert.
- Etappe 3b-Versuch-1: Anker-Einrückung falsch abgezählt (16
  statt 12 Space), kein Match. Korrigiert mit cat -A-Ausgabe.
- Etappe 3b-Versuch-2: Test-Design-Fehler — timeline-Test schrieb
  nur loop_phase ohne Kinder. Der Leere-Phasen-Filter (>0 Kinder
  ODER >2s Dauer) warf die Phase raus. Korrigiert mit Kind-Events
  pro Projekt.
- `exit` in Bash-Bloecken killt SSH. Mehrfach reproduziert. Ab
  jetzt nur noch Flag-basiert mit STATUS-Kette und FINAL STATUS.


## Projector-Deadlock behoben (2026-11-08)

**Commit:** a640b19

**Symptom:** SQLite stand seit 2026-11-08 15:14 still, JSONL hatte
31 echte Events nach 15:14. UI zeigte "letzter Run: 01:26", obwohl
der Loop um 17:57 (OP-280) gestartet und um 19:41 mit `loop_failed`
geendet war. Ambient-Bar zeigte "Fertig".

**Ursache (Bug-Kette):**

1. `Projector._jsonl_files()` las auch `*-migrated-*.jsonl` mit ein
   (statische DB-Dumps aus OP-323).
2. `_read_events()` suchte den Checkpoint `MIGRATED-SEM-352017`
   sequenziell in den JSONL-Dateien. Er steht nur in
   `agent-pipeline-migrated-2026-11-08.jsonl` Zeile 33/33 — der
   alphabetisch letzten Datei.
3. Die echten Tagesdateien werden **vor** der migrated-Datei gelesen.
   Sentinel wurde dort nie gefunden, `found_start` blieb `False`,
   alle Events wurden stumm uebersprungen.
4. `tail()`: `eingefuegt == 0` -> `if letzter and eingefuegt > 0`
   greift nicht -> Checkpoint blieb `MIGRATED-SEM-352017`.
5. Deadlock: Jeder weitere Flush las wieder 0 Events.

**Fix (a640b19):**

- `_jsonl_files()` excludet `*-migrated-*.jsonl` (statische Dumps,
  keine fortlaufende Quelle).
- `_read_events()` wirft `ValueError` bei unbekanntem Checkpoint,
  statt still 0 zurueckzugeben. Deadlock wird sichtbar statt
  unsichtbar.

**Daten-Reset:**

- `UPDATE projection_state SET value='PIPE-20261108-151341-a8a36a'
  WHERE key='last_audit_id'` (letzter echter audit_id vor dem Stau).
- `tail()` -> 31 Events eingelesen, 2 wegen `event_id`-Kollision
  uebersprungen (harmlos, `INSERT OR IGNORE`).
- `tail#2` -> 0 eingefuegt (idempotent).
- Checkpoint landet auf `PIPE-20261108-194159-bd35bf`.
- `COUNT` 410754 -> 410785, `MAX(seq)` 788707 -> 788736.

**3 neue Tests** in `tests/test_projection.py`:
`test_jsonl_files_ignoriert_migrated`,
`test_read_events_wirft_bei_unbekanntem_checkpoint`,
`test_tail_nach_reset_liest_alle_neuen_events`.
pytest 1536 passed.

**Live-Effekt nach Reset:** Ambient zeigt jetzt den echten Stand
(letzter Eintrag 19:41). Dass es weiterhin `done` ist statt
`failed`, liegt an einem separaten Bug in `aggregate_ambient` —
siehe neue OP.

**2 neue OPs angelegt:**

- **OP-371:** Ambient-Loop-Status zeigt letzten Erfolg statt
  letzten Zustand. Live-Beleg: `loop_failed` 19:41 wird ignoriert,
  `loop_erfolg` 01:26 gewinnt.
- **OP-372:** Projection-Status-Diff vergleicht JSONL (33k) mit
  SQLite (410k) und zeigt -377.834 an. Semantisch falsch, aber
  kein Datenproblem.


## OP-371: Ambient-Loop-Status zeigt neuestes Terminal-Event (2026-11-08)

**Symptom:** Ambient-Bar zeigte "Fertig", obwohl der letzte Run mit
`loop_failed` endete.

**Live-Beleg 2026-11-08 22:10:**
- SQLite: letzte Terminal-Events = loop_failed (19:41)
- ambient('werkstatt') = "done" (mit last_run = loop_erfolg 01:26)

**Ursache:** aggregate_ambient hatte 3-stufige Kaskade
(loop_erfolg -> loop_failed -> loop_ended). Ein spaeteres loop_failed
wurde ignoriert, weil der aeltere loop_erfolg bereits den Status setzte.

**Fix:** Eine Query mit
`WHERE kind IN ('loop_erfolg','loop_failed','loop_ended') AND project=?`
+ `ORDER BY seq DESC LIMIT 1`. Das kind des neuesten Events entscheidet:
- loop_failed -> failed
- loop_erfolg|loop_ended -> done

last_run zeigt das juengste Terminal-Event, nicht das juengste
Erfolgs-Event.

**Tests:** 2 neue Verhaltens-Tests (Konflikt-Reihenfolge in beide
Richtungen). Bestehende Tests bleiben gruen. pytest 1538 passed.

**Live-Effekt:** ambient('werkstatt') = failed, last_run = 19:41
loop_failed. UI zeigt jetzt die Wahrheit.


## Backfill project-Spalte aus JSONL — Vorbereitung (2026-11-08)

**Symptom:** aggregate_ambient('security-ai') zeigte 'idle', obwohl
security-ai 236 Runs und 23.289 Werkstatt-Laeufe hatte (JSONL 12.10.–
08.11.).

**Ursache:** OP-306c-Migration hat alle 410k Events auf
project='werkstatt' gesetzt (Annahme "alle historischen Events
stammen aus Werkstatt"). Das war falsch — pruefte nie die
project-Verteilung in JSONL.

**Messung:** Alle 23.289 security-ai event_ids sind in SQLite, aber
mit project='werkstatt'. Davon 5.124 mit run_id (236 runs), 18.165
ohne run_id (Pre-run_id-Aera). event_id-Fallback funktioniert
zuverlaessig fuer beide Gruppen.

**Wichtig:** Zwei getrennte audit-Systeme:
- /opt/werkstatt/audit-logs/agent-pipeline-*.jsonl -> Werkstatt-Laeufe
  gegen Projekt security-ai -> GEHOEREN in Werkstatt-SQLite (Backfill-Ziel)
- /opt/security-ai/audit-logs/*.jsonl -> security-ai's EIGENES System
  (Format {agent: security_ai, audit_id: AUD-...}) -> NICHT anfassen

**Fix:** Backfill via event_id-IN-Liste (Sicherheit: event_ids sind
eindeutig aus JSONL mit project=security-ai abgeleitet).


## OP-373 abgeschlossen (2026-11-08)

**Ausgefuehrt:** Manueller SQL-UPDATE mit event_id-IN-Liste.
23.289 Werkstatt-Events von project='werkstatt' auf 'security-ai'
korrigiert.

**Sicherheit:** event_ids eindeutig aus JSONL-Zeilen mit
project=security-ai abgeleitet. `WHERE project='werkstatt'` als
zweite Bedingung. Dry-Run vor Ausfuehrung, DB-Backup in
/tmp/events.db.vor-backfill.

**Verifikation:**
- project-Verteilung: werkstatt=387487, security-ai=23289, default=9
- Idempotent (2. Lauf = 0 Aenderungen)
- ambient('security-ai') nicht mehr 'idle' (zeigt aber leeren
  run_id — siehe OP-374)
- ambient('werkstatt') unveraendert (failed, 19:41)

**Bewusst NICHT gemacht (in OP-374):**
- Kein reproduzierbarer Code (nur manuelles SQL)
- `_letzter_run_id` filtert nicht auf run_id != ''
- 18.165 security-ai Events ohne run_id (Loop-Bug 18.10.-02.11.)
- ops_run_status findet 0 security-ai-OPs (pre-OP-303 op_id-Luecke)

**Wichtig:** /opt/security-ai/audit-logs/ ist security-ai's EIGENES
audit-System (Format {agent: security_ai, audit_id: AUD-...}) und
NICHT Teil des Werkstatt-Backfills. Nur Werkstatt-JSONL und
Werkstatt-SQLite waren Ziel.


## OP-389: WebSocket-Auth-Bypass in /ws/{tab_id} (2026-11-09)

**Ausgefuehrt:** Commit 8880d04. Neuer async-Helper
`require_ws_auth(websocket) -> bool` in `werkstatt/web/auth.py`:
prueft `is_auth_disabled()` oder `is_authed_ws(websocket)` vor
`accept()`; schliesst mit Close-Code 1008 wenn nicht autorisiert.
`ws.py:websocket_kanaele` nutzt den Helper. Damit sind alle 4
existierenden WebSocket-Endpoints gegen Unauth geschuetzt —
`/api/projects/{name}/chat/stream`, `/api/projects/{name}/audit/stream`
und `/ws/terminal/{project}` waren bereits geschuetzt, `/ws/{tab_id}`
war die Luecke.

**Spec-Tests:** `tests/test_ws_auth.py`, 13 Tests.
- 4x unauth → Close 1008 vor accept (parametrisiert ueber alle 4 WS-Pfade)
- 4x mit gueltigem Cookie → akzeptiert
- 4x `_AUTH_DISABLED=True` → akzeptiert (Test-Workflow)
- 1x Meta-Test: Source-Scan aller `@(app|router).websocket`-Routen,
  muss in `WS_ROUTEN_SOURCE` eingetragen sein. Neue WS-Endpoints ohne
  Auth-Test faellt sofort auf.

**Regress-Barriere verifiziert (Revert-Beweis):** Bei Entfernen des
Auth-Checks aus `ws.py` wird genau
`test_unauth_ws_wird_abgelehnt_vor_accept[/ws/abc]` rot; die 3
anderen parametrisierten WS-Pfade bleiben gruen (Bestandsschutz ist
vorhanden, der Test deckt exakt die Luecke). Revert-Beweis ist damit
hart erbracht, nicht "Test ist halt gruen".

**Baseline:** 1550 → 1563 passed, 5 skipped. ruff clean, mypy clean,
alle 5 Drifts (audit/control/import/state/state_inventory) gruen.

**Folge-OP (angelegt):** OP-389b — `app.py`, `audit_panel.py`,
`terminal_proxy.py` auf denselben Helper migrieren (DRY, kein
Verhaltenswechsel, aber Regress-Risiko an 3 funktionierenden
Endpoints → eigene Session mit eigenem Source-Scan-Meta-Test).

**Lehren aus der Session:**
- `Path("werkstatt/web")` nach `monkeypatch.chdir(tmp_path)` ist ein
  leerer Glob. Meta-Test mit `Path(__file__).resolve().parent.parent
  / "werkstatt" / "web"` — relatives Pfad-Handling nach chdir ist
  immer falsch.
- `import pytest` muss **vor** `from fastapi...` stehen (isort-Konvention).
  `str.replace` traf es nicht, `ruff --fix --select I` auf die eine
  Datei schon. `ruff --fix .` bleibt verboten (loescht F401).
- Ein Test, der zweimal hintereinander im selben Block laeuft, nachdem
  Code geaendert wurde, sollte besser als eigener Sub-Block verifiziert
  werden — Test-Fix und Code-Fix nicht in einem Rutsch.


## OP-390: Git-Diff-Argument-Injection (2026-11-09)

**Ausgefuehrt:** Commit f4952ff (Code) + c13a6a9 (Test-Isolation).
Neues zentrales Modul `werkstatt/validierung.py` mit REF_MUSTER
und pruefe_ref(). Muster erlaubt Branch/Tag/SHA/HEAD~N/HEAD^/
origin/main/refs/heads/x; verbietet fuehrendes '-' (Option-
Interpretation: --output=, -p, --ext-diff), Leerzeichen,
Shell-Metazeichen, Laenge > 128. `app.py:/api/projects/{name}/diff`
ruft `_pruefe_ref(ref)` vor git-diff (HTTP-Adapter wandelt
ValueError in HTTPException 400). `chat_tools._git_diff` ruft
`pruefe_ref(ref)` vor subprocess; ValueError -> return
'git_diff: ungueltiger ref ...'.

**Spec-Tests:** `tests/test_diff_ref_validation.py`, 22 Tests
(8x gueltig-param, 7x ungueltig-param, 3x HTTP-Endpoint inkl.
400-Vor-Validierung, 2x chat-tools mit subprocess-Mock, 1x Meta,
1x Endpoint-200).

**Regress-Barriere verifiziert (Revert-Beweis):** bei Revert der
chat_tools-Pruefung werden BEIDE chat-tools-Tests rot
(output-option: prueft mock_run.assert_not_called;
leerer-ref: analog). Staerker als OP-389 (dort nur 1 rot).

**AK-Abweichungen (dokumentiert im Commit):**
- (a) REF_MUSTER zentral in `werkstatt/validierung.py` statt
  `app.py` — `chat_tools.py` (Kern) darf `werkstatt/web/` nicht
  importieren (import_drift-Contract). Ein Helper, zwei Aufrufer.
- (e) '--' steht NACH ref (`git diff {ref} --`), nicht davor. Der
  AK-Text 'git diff -- {ref}' verwechselt Pathspec-Trenner mit
  checkout-Semantik: `git diff -- HEAD` interpretiert HEAD als
  Pfad, liefert leer, haette den Endpoint funktional gebrochen.

**Bewusst NICHT gemacht (nicht im Scope, OP-Kandidaten):** andere
subprocess.run-Aufrufe in app.py/chat_tools.py (Zeilen 63, 77, 125)
auf unvalidierte Argumente pruefen — eigene OPs, nicht Teil von
OP-390.

**Baseline:** 1563 -> 1585 passed, 5 skipped. ruff/mypy clean,
alle 5 Drifts gruen.

**Lehren aus der Session (3):**
- `git status --porcelain` gibt ` M file` (Leerzeichen + M), nicht
  `M file`. Ich habe das Pattern aus dem Kopf geraten, Precondition
  war zwangslaeufig rot. **Shell-Format nie raten — einmal
  `echo "[$VAR]"` und gut.**
- Test-Write VOR Precondition-Check killt den Block. **Precondition
  ist die erste Zeile, jede Schreib-Operation danach.** Zweimal
  hintereinander verletzt; ab jetzt strukturell: Precondition als
  eigener Sub-Block vor allen `cat`-Aufrufen.
- Test der `git diff HEAD` gegen den echten Working Tree macht,
  ist nicht isoliert. `test_chat_tools_git_diff_normaler_ref` war
  in Isolation gruen, in der vollen Suite rot, weil der
  uncommittete STATUS.md-Diff den String 'ungueltiger ref' enthielt.
  **Test-Isolation durch `subprocess.run`-Mock, nicht durch
  Hoffnung auf clean tree.** Betrifft jede Test-Funktion, die
  `subprocess`, `git`, `Path.cwd`, `os.environ` oder HTTP beruehrt.


## OP-391: Files-/Diff-Endpoint respektieren den Projektnamen (2026-11-09)

**Ausgefuehrt:** Commit 0cb8ae0. Zwei hardcoded Stellen in
`werkstatt/web/app.py` ersetzt:
- `/diff` (Zeile 433): `basis = _PROJECTS_BASE / _pruefe_projektname(name)`
  statt `Path("/opt/werkstatt")`. Rueckgabe von `_pruefe_projektname`
  wird jetzt abgefangen und verwendet (vorher verworfen).
- `/files` (Zeile 486): analog. `_pruefe_projektname(name)` wird
  jetzt ueberhaupt aufgerufen — vorher gar nicht, Multi-Projekt war
  halb fertig seit OP-306c.

**Spec-Tests:** `tests/test_files_projekt.py`, 4 Tests.
Isolation: `_PROJECTS_BASE` via monkeypatch auf `tmp_path`,
`subprocess.run` fuer /diff gemockt.

**Regress-Barriere verifiziert:** bei Revert beider basis-Zeilen
werden 3 von 4 Tests rot (files-beruecksichtigt, files-404,
diff-cwd). `pfad_traversal_blockiert` bleibt gruen — richtig, weil
der Root-Check unveraendert bleibt.

**AK-Pruefung:** (a) files: erfuellt. (b) diff: erfuellt.
(c) `_PROJECTS_BASE`: war schon Modul-Konstante. (d) Root-Check:
unveraendert. (e) Live-Test: via Test-Client gegen tmp_path
verifiziert.

**Baseline:** 1585 -> 1589 passed, 5 skipped. ruff/mypy clean,
alle 5 Drifts gruen.

**Lehre (Test-Isolation konsequent):** `_PROJECTS_BASE`-Monkeypatch
und `subprocess.run`-Mock sind jetzt Standard bei jedem Endpoint-
Test, der Pfade oder git anfasst. Kein Test haengt mehr vom
Working Tree ab — das war bei OP-390 noch anders.


## OP-392: loop.py _full_cfg UnboundLocalError + Stash-Verlust (2026-11-09)

**Ausgefuehrt:** Commit 9c29910. Zwei Fehlerpfade in `werkstatt/loop.py`.

**Bug A (_full_cfg, Zeile 493-508):** `_full_cfg = _load_cfg(...)`
steht innerhalb try. Bei gewoehnlicher Exception (ValueError aus
kaputter YAML) greift `except Exception: pass`, `_full_cfg` bleibt
unzugewiesen, Zeile 508 (`if _full_cfg else {}`) wirft
UnboundLocalError. Fix: `_full_cfg: dict = {}` vor try.

**Bug B (Stash-Verlust, Zeile 560):** `run_pipeline_loop` ohne
try/finally. Bei Exception werden `_ps.save()` und `_git_stash_pop`
uebersprungen -> Stash bleibt im Repo, Working Tree leer,
Datenverlust. Fix: `try/except BaseException/finally` um den Aufruf.

**Design:** `except BaseException` faengt KeyboardInterrupt mit
(AK d), `raise` propagiert, `main()` emittiert `loop_failed` via
existierendem `_emit_lifecycle_end` (bereits exception-safe).
`rc=1` als safe-default; `_hat_exception` unterscheidet Fehlerpfad-
Audits (loop_rollback / loop_rollback_skipped / loop_stash_pop) von
Exception (kein Reset, aber pop). Reihenfolge reset->pop bleibt
(Referenz-Tests binden sie).

**Spec-Tests:** 2 neu in `tests/test_loop_main.py`.
- test_main_kaputte_config_kein_unbound_local_error
- test_main_stash_pop_bei_exception

**Regress-Barriere verifiziert (zwei Reverts):**
- Fix A weg -> Test 1 rot mit exakt `UnboundLocalError` Zeile 508.
- Fix B weg (pop im finally raus) -> Test 2 rot (pop_calls leer).

**Baseline:** 1589 -> 1591 passed, 5 skipped. ruff/mypy clean,
alle 5 Drifts gruen.

**Session-Bilanz P1/P2-Serie (4 OPs aus externem Review):**
- OP-389 WebSocket-Auth (f4952ff + c13a6a9 + 7cca2a6 + 6b80e5b)
- OP-390 Git-Diff-Injection (8880d04 + 5 Commits Doku+Test-Isolation)
- OP-391 Files/Diff-Projektname (0cb8ae0 + 00206fb)
- OP-392 loop.py _full_cfg + Stash (9c29910)
Alle mit hartem Revert-Beweis, Baseline 1550 -> 1591.


## Session 2026-11-09 (Abend) — 24 Commits, 1550 -> 1686 Tests

**Ziel der Session:** Loop aus der UI startbar machen und UI auf "Top Notch" bringen (Codex/Claude-Code-Feel, multi-projekt).

**Was gebaut wurde (chronologisch):**

**Sicherheits- und Loop-Härtung (P1/P2, externer Review):**
- OP-389 WebSocket-Auth (f4952ff + c13a6a9 + 7cca2a6 + 6b80e5b): `require_ws_auth`-Helper, alle 4 WS-Endpoints geschützt. `OP-389b` (DRY-Migration) offen.
- OP-390 Git-Diff-Injection (f4952ff + 5 Commits + Doku): `werkstatt/validierung.py` zentral, `pruefe_ref`-Helper, `--`-Trenner nach ref.
- OP-391 Files/Diff-Projektname (0cb8ae0 + 00206fb): `_PROJECTS_BASE / _pruefe_projektname(name)`.
- OP-392 loop.py `_full_cfg` + Stash (9c29910): try/finally um `run_pipeline_loop`, `_full_cfg` vor try.

**Loop-Crash-Ursachen gefunden und behoben:**
- `_OPS_RE` erkennt OP-Suffixe (f90e427): `OP-389b` wurde vom `parse_ops` nicht gefunden -> `POST /start` mit leerer Aufgabe -> `loop_failed` nach 2s.
- Explorer-Fallback-Grep (15ec8b9): Aufgabe mit Backtick-Suchbegriff ohne `.py`-Pfad -> `key_files=[]` -> `loop_explorer_leer`. Fallback grept deterministisch ueber `.py`.
- OP-110 Planner create/update (72a8d4f): `create` bei existierender Datei wird zu `update`.
- OP-381k Resume-Aufgabe-Check (8af1d99): `_resume_erlaubt`-Flag, `phase_state.data['aufgabe']` vs. `aufgabe`.

**Context-Engineering (Token sparen):**
- OP-385a (1ad363f): `scout_auftrag` als einzige Architect-Quelle. Vorher 4 parallele Explorer/Scout-Kanaele -> 100.000 user_len Truncation. Baseline erwartet <60k.

**UI-Modi (ADR-0022):**
- OP-306a (85a29db): Mode-Switch Fundament. 3 Modi via Shift+Space + 1/2/3 + URL `?mode=...` + localStorage + Dropdown. CSS-Grid-Varianten. Tests `test_ui_mode_switch.py` (7). **OP-306 offen fuer Etappe 2-4.**
- Wasserfall ins Cockpit (3671fe9, ADR-0022a): Nachanalyse-Tool. Control bekommt Live-Feed.

**Timeline / Live-Daten:**
- OP-381d (a1caf53): ambient `gates_open` konsistent mit `gate_context`.
- OP-381e (5b05f43): Read-Through (`Projector.tail()` vor UI-Aggregatoren).
- OP-381f (c868fc1): `aggregate_timeline` ignoriert `-migrated-`-Dateien.
- OP-381g (b35502d): `loop_phase:build`-Marker.
- OP-381h (e5a4101 + b44da43): Rollen pro Kind, `aggregate_timeline_aktiv`.
- OP-381i (ca6f0e7..e3a6299): Swimlane-Wasserfall (SVG, Rollen-Lanes, sem-Farben) + Runs-Sidebar togglebar.
- OP-381j (262ed8b..ba78af5): Live-Feed (Backend + Frontend + Codex-Polish: Spinner, Dots, Shimmer, Transition).

**Gate-Modal (OP-381c, 05bc3fc):**
- 900px-Vollbild, Backdrop-Blur, Copy-Button, Markdown-CSS, Sections, Actions sticky, Freitext-Textarea (typ=freitext), Escape, Banner-Dismiss. `_machDraggable` entfernt.

**Was NICHT funktioniert (bekannt, morgen):**
- **Loop scheitert an Verify nach Builder-Patch.** Live-Beleg Run `werkstatt-20261109-222702-a8c4dac4`: Builder baut `inspector.py`, ruff SIM102 bei Zeile 70, Reflection fixt -> mypy `Incompatible types (list vs dict)` bei Zeile 1248, Reflection fixt -> mypy gleicher Fehler bei Zeile 1250, `stagnation_abort`. **Loop-Verhalten korrekt** (nach 2 Stagnationen aufgeben), aber der Builder produziert typ-invaliden Code.
- **`aggregate_ambient.loop_status` haengt bei `running`** wenn Loop tot ist (Gate-Timeout 300s > Loop-Lifetime).
- **`aggregate_live_feed.aktiv = {}`** bei offenem Gate (`_tl_aggregate_aktiv` erkennt `gate_open` nicht als in-progress).
- **`prompt: "Deine Wahl: "`** im Commit-Gate inhaltsleer.

**Baseline:** 1550 -> 1686 passed, 5 skipped. Alle 5 Drifts gruen. ruff/mypy clean.

### 2026-11-09 Abend (Fortsetzung) — 3 Code-Fixes + Handoff-Korrektur

- **mypy-Fix (1869182):** OP-381i-Regress in aggregate_swimlane —
  Variablenname `balken` doppelt belegt (dict vs list[dict]).
  Handoff §1 behauptete "mypy: clean", war aber 1 error in
  inspector.py:1208.
- **Live-Feed (c1dcb4d):** `_tl_aggregate_aktiv` erkennt `gate_open`
  als "in progress". Loop am Gate ist jetzt im Control-Modus
  sichtbar (Rolle `loop`, Aktion "wartet auf Antwort").
- **Ambient (63248c4):** `aggregate_ambient` bevorzugt das
  Terminal-Event nach `gate_open`. Loop tot mit juengem Gate ->
  ambient zeigt `failed`, nicht `running`.
- **Handoff-Korrektur:** Abschnitt 3 [A] teilweise widerlegt —
  `aggregate_fehler_cluster` existiert nicht, Run `a8c4dac4`
  nicht im Repo. Merkposten-Abschnitt "Handoff ist Behauptung"
  dokumentiert das Muster.
- **Stand:** 1689 passed, 5 skipped. Alle 5 Drifts OK. Server
  neu gestartet (PID 3847746).

Commits: 1869182, c1dcb4d, 63248c4

**Nachtrag 2026-11-10 — Handoff-Korrektur nach Messung:**
- [A] Builder-Typ-Bug: widerlegt. `aggregate_fehler_cluster` existiert
  nicht; Run `a8c4dac4` nicht im Repo. Der /tmp-Snapshot zeigt den
  bereits gefixten `balken`-Konflikt aus OP-381i — Builder erbte den
  Fehler, erzeugte ihn nicht.
- [E] Scout-Datei-Validierung: nicht reproduzierbar, Run fehlt.
- [D] Commit-Gate-Prompt explizit gemacht (gates.py:697).

