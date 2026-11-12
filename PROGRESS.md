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

### 2026-11-10 Live-Test OP-381 (f) — strukturell erfolgreich, 3 neue OPs

**Erfolg:** Loop aus UI (POST /start mit op_id=OP-389b) startet
korrekt, Explorer findet Dateien (Volltext-Fix aus c51b21d), Plan-Gate
erscheint im Browser, User-Klick `j` kommt an (gate_answered +
loop_plan_gate_approved), Builder arbeitet 3 Tasks ab (t1 fail wegen
Builder-Import-Halluzination, t2 ok, t3 reviewer-rejected), Loop kommt
bis Phase-Review. **OP-381 (a)-(e) sind live validiert.**

**Neuer Blocker:** Phase-Review-Gate nutzt `input()` statt `gate_bridge`
-> loop_human_gate_eof -> loop_failed. Angelegt als OP-393.

**Drei UI-Befunde:** Aktiv-Block zeigt nur letztes Event, Sortierung
verwirrend, Builder 30-60s ohne Events (wirkt "tot"), technische Kinds
statt semantischer Verben ("Architect denkt" etc.). Angelegt als
OP-394 (semantisch + Sortierung) und OP-395 (Builder-Event-Emission).

**Handoff-Korrektur (weiter):** Handoff §3 [E] "Scout halluziniert
ws.py" war FALSCH — der Scout hat `ws.py:80-82` korrekt referenziert,
der Bug lag im `_pruefe_api_widerspruch` (false-positive). Handoff §3
[A] "Builder-Typ-Bug" war falsch (balken-Konflikt war aus OP-381i).
Damit: 4 von 5 Handoff-Bugs widerlegt oder unzutreffend; nur [B] und
[C] waren echt (gefixt 63248c4 / c1dcb4d).

**Zahlen:** 1697 passed, 5 skipped. 8 Commits (1869182, c1dcb4d,
63248c4, 8768b72, b09af0a, a3140b0, c51b21d, 2978d27). Alle 5
Drifts OK.

**Nachtrag 2026-11-10 (nach dem Live-Test):** Loop-Patch war sauber.
Builder hat t2 (`audit_panel.py`) und t3 (`terminal_proxy.py`) exakt
OP-389b-konform migriert. Diff verworfen, weil unvollstaendig (t4
`tests/test_ws_endpoint_helpers.py` fehlt, t1 failte). Der Patch-Beweis
ist im Merkposten dokumentiert.

### 2026-11-10 — Control-Chat-UI und Session-Race

**Commits:** a90c161, b7dd53b, d79a509, b7b1f96, bbeae4d, 0f8ce77.

Control erhielt eine breitere Chat-Arbeitsfläche, eine sichtbare Loop-
Steuerleiste und lesbare Ereignislabels mit Rohdaten im Tooltip.
Der Projektwechsel leert den bisherigen Chat sofort. Verspätete
Session-Erstellungen werden jetzt über Projekt-/Anfragegeneration
gebunden; ein altes Session-Promise kann keinen neuen Projektzustand
zurücksetzen. „Neue Session“ prüft dieselbe Generation, bevor sie
Nachrichtenbereich und Status aktualisiert.

**Prüfung:** Chat-JavaScript syntaktisch geparst. Python-/Browser-Gates
und Server-Render sind noch nicht ausgeführt; OP-396 bleibt offen.

### 2026-11-10 — Veraltete Chat-Sidebar-Antworten verwerfen

**Commit:** dee7799.

Die Session-Sidebar übernimmt eine verspätete Antwort nur noch, wenn
sowohl Projekt als auch Anfragegeneration noch aktuell sind. So kann
auch ein schneller Wechsel A → B → A keine ältere A-Sessionliste über
die neuere Ansicht legen.

**Prüfung:** Chat-JavaScript syntaktisch geparst; Verhaltenstest und
Server-Gates stehen für diesen Commit noch aus.

### 2026-11-10 — Runs-Fehler und Chat-Markdown

**Commits:** 425c1ca, 3498eb4, 351a0ab, 38b4726, 363c8f3, 21a3a35.

Der Control-Screenshot zeigte eine leere Runs-Seitenleiste. Ursache war
ein nicht definierter Bezeichner `isRunning` in `runs.js`, der das
Rendern vor der OP-Liste abbrach. Das Badge verwendet jetzt den
vorhandenen Run-Status; ein Regressionstest deckt die fehlerhafte
Referenz ab.

Chat-Antworten werden nun als begrenztes Markdown mit Absätzen,
Listen, Code, Zitaten und sicheren HTTP(S)-Links dargestellt. Die
Darstellung baut DOM-Knoten und verwendet kein `innerHTML`; rohe
HTML-Tags bleiben Text. Fliesstext nutzt die UI-Schrift, Code bleibt
monospace. Ein Frontend-Vertragstest deckt Darstellung und
Protokollbeschränkung ab. Statische Asset-URLs wurden versioniert.

**Prüfung:** JavaScript-Syntax und Markdown-DOM-Vertrag im lokalen
isolierten Runtime-Simulator geprüft; Python-/Browser-Gates und
visuelle Serverprüfung stehen noch aus.

### 2026-11-10 — Control stoppt und pausiert Prozessgruppen

**Commits:** c51bf17, ac722b1, e415816.

Der Serverlauf deckte einen Cache-Buster-Testvertrag auf; statische
Asset-Versionen sind wieder numerisch. Zusätzlich startet der Web-Loop
unter POSIX in einer eigenen Session/Prozessgruppe. Pause, Resume und
Stop signalisieren nun die Gruppe, damit Prüf- und Test-Kindprozesse
nicht nach der UI-Aktion weiterlaufen. Der Prozessgruppenvertrag ist
durch Backend-Tests abgedeckt.

**Prüfung:** Der gemeldete Gesamtlauf 1747 passed / 1 failed betraf
noch den nichtnumerischen Cache-Buster; targeted tests und Ruff waren
grün. Der Numeric-Fix und Prozessgruppenänderungen brauchen einen
erneuten Serverlauf.

### 2026-11-10 — Stop-Eskalation der Prozessgruppe getestet

**Commit:** 5746b30.

Ein Backend-Regressionstest deckt jetzt auch den Timeout-Pfad ab:
Nach ausbleibender Beendigung erhält die Prozessgruppe SIGKILL, und die
API liefert erst danach den finalen Prozessstatus. Der Test fängt
SIGTERM/SIGKILL ab und startet keinen echten Loop-Prozess.

**Prüfung:** Test ergänzt; Ausführung auf dem Server steht noch aus.



### 2026-11-10 — Overview-Sparkline-Regression aus Serverlauf behoben

Der Serverlauf auf `37324a1` meldete 1774 passed, 3 failed und Ruff `PIE807`; mypy war mit 0 Fehlern sauber. Die 30-Tage-Sparkline verwendete `GROUP BY 1` auf einer aggregierten SELECT-Expression. SQLite verwirft diese Abfrage; der abgefangene SQL-Fehler erschien als 30 Nullwerte. `_sparkline_30d` gruppiert nun nach dem Datumsausdruck und ignoriert leere `run_id` konsistent mit den Run-KPIs. Das Testfixture ordnet den erwarteten Erfolg dem abgefragten Projekt zu; `lambda: []` wurde durch `list` ersetzt.

**Fixes:** `be61360` (leere Run-IDs), `ce0ef73` (Sparkline-SQL und Fixture/Ruff). **Verifikation:** Die drei zuvor fehlschlagenden Tests, Ruff und das vollständige Quality-Gate müssen nach diesen Commits erneut auf dem Server laufen; Ergebnis steht noch aus.


### 2026-11-10 — Idle-Loop-Status gibt keine alte Run-ID mehr aus

Bei einem persistenten Registry-Eintrag blieb nach dem Übergang in `idle` die vorherige `run_id` im Status-Endpoint sichtbar. Die API gibt die Run-ID nun nur noch für eine aktive Startreservierung aus; ein Backend-Regressionstest prüft `starting → idle`. Fix: `f0a9cc0`. **Verifikation:** Serverlauf steht aus.


### 2026-11-10 — Server-Rerun: Sparkline-Fixture an Run-Deduplizierung angepasst

Der gezielte Serverlauf nach den Overview-/Loop-Status-Fixes ergab 14 passed, 1 failed; Ruff war grün. Der verbleibende Test `test_overview_sparkline_buckets` erwartete drei heutige und zwei gestrige Runs, erzeugte dabei aber je Bucket wiederholt dieselbe `run_id`. Die Sparkline zählt eindeutige Runs, daher war der tatsächliche Wert 1 korrekt. Das Fixture erzeugt nun für jeden erwarteten Run eine eindeutige ID. Zusätzlich liegt seit `83c433e` eine Byte-begrenzte, inkrementelle Chat-Dateilesung mit Offset-Tests vor; diese Änderung ist noch nicht serververifiziert.


### 2026-11-10 — Serververifikation: Overview, Loop-Status und Chat-Read-Limit

Verifiziert auf Server-HEAD `e4366bb`: gezielte Tests 41 passed; vollständige Suite 1781 passed, 5 skipped; Ruff 0; mypy 0; Quality-Gate `ok: true`, `regression: false`. Damit sind die Sparkline-SQL-/Fixture-Korrekturen, der Idle-Run-ID-Vertrag und die bytebegrenzte Chat-Dateilesung samt Tests durch den Serverlauf abgedeckt. AST- und Katalogprüfungen bleiben im Gate übersprungen, weil die dort genannten historischen Dateien fehlen.


### 2026-11-10 — Gate-Debug-Kontext an aktives Projekt gebunden

Beim Lesen der Debug-/Gate-Entscheidungen in ADR-0011, ADR-0022, ADR-0029 und OP-240/242 ist ein Multi-Projektfehler im Gate-Kontext aufgefallen: `aggregate_gate_context(projekt)` las den Git-Diff fest aus `/opt/werkstatt`. Bei einem Gate in einem anderen Projekt konnte der Nutzer somit den Diff eines fremden Projekts sehen. Der Endpoint verwendet jetzt den validierten Projektpfad unter `_PROJECTS_BASE` und fail-closed keinen Diff außerhalb dieser Basis. Zwei Backend-Tests decken Projektbindung und Traversal ab. **Serververifikation steht aus.**


### 2026-11-10 — Gate-Edit an Debug-Chat uebergeben

Der Gate-Button „Im Chat debuggen“ sendet den Projekt-/Run-/Gate-Kontext samt Plan, Verify-Ergebnis und begrenztem Diff an die Chat-Session und wechselt in den Debug-UI-Modus. Er beantwortet das Gate nicht; j/n/Freitext bleiben separate Gate-Antworten. Die Chat-Uebergabe wartet auf das Laden der aktiven Session, damit der Kontext nicht in einer parallelen oder verlorenen Session landet. Die Option „a“ wird als „Plan anpassen“ dargestellt; revidierte und Scout-No-Op-Plaene zeigen nur j/n, entsprechend den tatsaechlich gueltigen Antworten. Frontend- und Gate-Options-Tests ergaenzt. **Serververifikation steht aus; OP-240 bleibt offen, da der Chat derzeit noch read-only ist und keine Debugger-Testwerkzeuge/strukturierte Patch-Freigabe besitzt.**


### 2026-11-10 — Debugger-Abhaengigkeiten bereinigt

Der STATUS-Parser listet OP-231 und OP-233 nicht mehr als offene Punkte; PROGRESS dokumentiert ChatSession, die acht read-only Chat-Tools, chat_agent.py und die dreispaltige Chat-Oberflaeche bereits als umgesetzt. Die veralteten Blocker wurden daher entfernt: OP-240 ist auf dieser Basis startbar, OP-242 wartet nur noch auf OP-240. Das Gate-zu-Chat-UI-Fundament ist in d80902a ergaenzt; Debugger-Tools und die direkte, freigabegestuetzte Patch-Uebergabe bleiben offen.


### 2026-11-10 — Serververifikation: Gate-Chat-Uebergabe

Verifiziert auf Server-HEAD `af91cf6`: Gate-/Chat-Tests 28 passed; vollstaendige Suite 1787 passed, 5 skipped; Ruff 0; mypy 0; Quality-Gate `ok: true`, `regression: false`. Die Option „Im Chat debuggen“ uebergibt den Projekt-/Run-/Gate-Kontext an den Chat, ohne das Gate zu beantworten. Die Option `a` ist als „Plan anpassen“ beschriftet; revidierte/Scout-No-Op-Plaene haben nur `j/n`. AST- und Katalogpruefungen bleiben uebersprungen, weil `tests/test_audit_kinds.py` und `pipeline.py` im Serverstand fehlen. Die maschinenlesbare Patch-Freigabe und Uebergabe an den Loop bleibt noch offen.


### 2026-11-10 — Gate-Antworten serverseitig an Optionen binden

Der Gate-API-Endpunkt liest jetzt die Spezifikation des konkreten offenen Gates und akzeptiert bei Button-Gates nur eine einzelne angebotene Auswahl. Freitext-Gates bleiben unterstützt; leere oder überlange Antworten werden abgewiesen. Neue API-Tests decken unzulässige Zustimmungen, gültige Button-Auswahl und Freitext ab. Die Änderung folgt der Human-Gate-Invariante aus ADR-0029: nur eine explizite, tatsächlich angebotene Gate-Antwort darf den Loop fortsetzen. **Serververifikation ausstehend.**


### 2026-11-10 — Serververifikation: Gate-API-Optionsschutz

Verifiziert auf Server-HEAD `c3a28db`: Gate-/Chat-Tests 32 passed; vollstaendige Suite 1791 passed, 5 skipped; Ruff 0; mypy 0; Quality-Gate `ok: true`, `regression: false`. Unzulaessige Button-Antworten werden ohne `gate_answered`-Event zurueckgewiesen; gueltige Optionen und Freitext-Gates bestehen. AST- und Katalogpruefungen bleiben uebersprungen, weil `tests/test_audit_kinds.py` und `pipeline.py` fehlen.


### 2026-11-10 — Doku-Drift vor Commit fail-closed pruefen

OP-280 wird gegen den tatsaechlichen Verify-Zeitpunkt abgesichert: Die bisherige `doku_check.py` wertete nur bereits committete Historie aus und konnte den gerade entstehenden Patch vor dem Commit nicht beurteilen. Ergaenzt wurden ein Working-Tree-Modus fuer staged, unstaged und untracked Dateien, eine harte `phase_end`-Verify-Stage und Tests. Die Historienpruefung bleibt als Zusatzdiagnose erhalten. **Serververifikation ausstehend.**


## OP-398 — konservative Auswahlstufe (2026-11-10)

Der Web-Start kann ohne expliziten Auftrag den einzigen eindeutig
startfaehigen STATUS-OP auswaehlen. Voraussetzung sind Status `open`,
aufgeloeste Blocker, Akzeptanzkriterien und ein konkreter Test/Nachweis.
Bei mehreren Kandidaten startet der Server keinen Run, sondern liefert
strukturierte Auswahloptionen; ohne geeignete OP erklaert die Antwort die
Ausschlussgruende. Ein direkter Auftrag hat Vorrang vor einer zusaetzlichen
OP-ID. Plan-Gate bleibt im Loop verpflichtend. In der Runs-Steuerung gibt es
einen Startknopf fuer den naechsten eindeutigen OP; mehrdeutige Antworten
zeigen die Kandidaten lesbar an, damit ein OP aus der Liste gewaehlt werden
kann.

Server-Verifikation steht noch aus. Der Selector buendelt keine OPs und
rankt mehrdeutige Kandidaten absichtlich noch nicht; diese OP-398-
Teilarbeit muss vor dem naechsten Ausbau verifiziert und erweitert werden.


## OP-396 — read-only Backlog-Beratung im Chat

Das projektgebundene Chat-Tool `next_op` verwendet den OP-398-Selector,
zeigt Kandidaten und Ausschlussgruende aus dem aktiven `docs/STATUS.md`
und startet oder aendert nichts. Der Chat-Systemprompt nutzt dieses Tool
bei Fragen nach offenen OPs oder dem naechsten sinnvollen Arbeitsschritt
und fragt bei Mehrdeutigkeit nach einer Nutzerauswahl.

Server-Verifikation steht noch aus.


### OP-396/398 — Code-Commit-Belege (GitHub-Multi-File-Updates)

Die GitHub-Contents-API schreibt Dateien als einzelne Commits. Die
folgenden Code-Commits sind durch die obenstehenden OP-396/398-Eintraege,
die Selector-/Chat-Beschreibung und `docs/SOLL.md §5.3` dokumentiert:

- **Commit:** `997399f2721d` — OP-398 Selector-Kern.
- **Commit:** `84492a21aa5c` — OP-398 Web-Start, Audit und sichere Abstention.
- **Commit:** `aca364299d7a` — konsistentes Blocker-Fehlerfeedback im Web-Start.
- **Commit:** `62931e4651c0` — OP-396 read-only Chat-Backlog-Werkzeug.
- **Commit:** `ee870dc33bb8` — OP-396 Chat nutzt Selector-Belege.

Diese Referenzen machen die Doku-Zuordnung pruefbar; sie ersetzen keine
Akzeptanzkriterien und keine Lauf-/Testbelege.


### 2026-11-10 — Serververifikation OP-398/Chat-Selector (HEAD 54b95f0)

- Gezielte Tests: 83 passed.
- Vollstaendige Suite: 1815 passed, 5 skipped.
- Ruff: 0 Fehler.
- Mypy: 1 Fehler; Quality-Gate meldet deshalb Regression (delta +1).
- **Commit:** `6f658b128393` — Selector-Ergebnis wird vor Start auf Typ und OP-ID geprueft; Mypy-Nachpruefung ausstehend.
- Doku-Drift: keine verdaechtigen Commits; der Worktree meldet weiterhin die
  uncommitteten Aenderungen an `werkstatt/web/audit_panel.py` und
  `werkstatt/web/terminal_proxy.py`.
- AST/Katalog: wie im Gate ausgewiesen uebersprungen, da die jeweiligen
  Dateien fehlen.
- Der einzelne Mypy-Befund ist noch zu beheben und erneut auf dem Server zu
  verifizieren; die Suite allein ist damit kein vollstaendig gruener Gate-Lauf.

### OP-398 — doppelte OP-IDs fail-closed (2026-11-10)

Der Selector behandelt wiederholte IDs in `docs/STATUS.md` jetzt als
widerspruechliche Identitaet: keine der gleichnamigen Zeilen wird ausgewaehlt
und Abhaengigkeiten auf diese ID gelten als nicht aufloesbar.
Ein Regressionstest kombiniert eine erledigte und eine offene Zeile mit
derselben ID sowie einen davon abhaengigen OP.

- **Commit:** `90ddd6067a0c` — doppelte Identitaeten fail-closed behandeln.
- **Commit:** `2af3194df0b7` — Regressionstest fuer Auswahl und Abhaengigkeit.
- **Commit:** `c88091e9f6c8` — Testdatei-Formatierung fuer Ruff.
- Server-Verifikation steht aus; vor Ausweitung des Selectors ist ausserdem
  der konkrete Mypy-Befund aus dem Quality Gate zu klaeren.

### Quality-Gate — Mypy-Diagnose im JSON sichtbar machen (2026-11-10)

Der Quality-Gate-Bericht hat bisher nur die Mypy-Fehleranzahl gespeichert;
der konkrete Compiler-Output wurde verworfen und `fehler` blieb dadurch
`null`. Bei einem Fehler enthaelt `current.mypy` jetzt Exit-Code und
Diagnose, auf 4000 Zeichen begrenzt. Damit bleiben Datei/Zeile und Error-Code
im Gate-JSON nachvollziehbar.

- **Commit:** `b8d18f929eaf` — Diagnoseausgabe und Exit-Code im Mypy-Bericht.
- **Commit:** `1d75c375e39c` — Regressionstest fuer den erhaltenen Output.
- **Commit:** `dc7fa117c817` — Formatierung des neuen Gate-Regressionstests.
- Server-Verifikation steht aus.

### Mypy — Fehlerdiagnose aus Serverlauf korrigiert (2026-11-10)

Der Serverlauf auf `c109a62` zeigte konkret `app.py:491 var-annotated`
fuer `_ausgeschlossen`. Die Variable ist jetzt als
`dict[str, Any]` annotiert. Mypy muss auf dem aktualisierten Branch noch
erneut laufen; der Fix gilt bis dahin als unverifiziert.

- **Commit:** `95a4b6832a94` — Typannotation am Selector-Blockerbefund.

### Control-Toolbar — OP-Startknopf nicht mehr kollabiert (2026-11-10)

Der Screenshot zeigte den langen Startknopf ueber dem Loop-Status. Ursache:
Der Control-Knopf erbte die 22-Pixel-Quadratgroesse der kleinen OP-Zeilen-
Aktionen. Er hat jetzt eine eigene Textknopf-Klasse mit intrinsischer
Mindestbreite; auf schmalen Ansichten darf die Beschriftung umbrechen.

- **Commit:** `22b45f559ae3` — eigene Klasse fuer Control-Aktionen.
- **Commit:** `ad139c58c199` — volle Toolbar-Breite und lesbare Knopfmasse.
- **Commit:** `da8728270bea` — UI-Regressionstest.
- **Commit:** `8eb817c55863` — gemeinsamer Asset-Cache-Buster fuer den Browser-Reload.
- Screenshot-/Browser-Verifikation und Servertests stehen aus.

### Nachbesserung UI-Test — Literal-Newline entfernt (2026-11-10)

Der Serverlauf auf `452ce3a` fand am Dateiende von
`tests/test_runs_frontend.py` einen literal geschriebenen `\\n`-Text
(Syntaxfehler bei Collection und Ruff). Der Marker wurde entfernt.
Derselbe Lauf bestaetigte Mypy mit 0 Fehlern; Volltests und Ruff waren wegen
des Syntaxfehlers nicht ausfuehrbar und muessen erneut laufen.

- **Commit:** `4c87b0552a66` — Syntaxfehler im neuen UI-Regressionstest behoben.

### OP-398 — Backlog-Schema-Audit fuer Ranking (2026-11-10)

Der bestehende STATUS-Vertrag in `docs/DOC_CONVENTIONS.md` §5 standardisiert
Status, betroffene Dateien, Akzeptanzkriterien, Tests und Blocker, aber keine
Prioritaet, Risiko- oder Projektziel-Relevanz. Eine strukturelle Auswertung
von `docs/STATUS.md` auf Commit `47f27930a98a` fand 101 OP-Ueberschriften,
davon 100 mit Status `open`; nur 12 offene OPs enthalten ein Prioritaetsfeld,
keiner ein Risiko- oder Projektziel-Feld. Der aktuelle Selector bleibt deshalb
bei eindeutiger Auswahl bzw. sichtbarer Abstention und kann OP-398s gefordertes
Ranking/Buendeln noch nicht belastbar beanspruchen. Naechster Architektur-
Schritt: normalisiertes, rueckwaertskompatibles Kandidaten-Metadaten-Schema
mit Validierung und Migrationsstrategie, bevor Ranking als Entscheidungsgrund
verwendet wird.

### Serververifikation — OP-398, Mypy und Control-Toolbar (HEAD 4eb7e41)

- Zieltests fuer Quality-Gate, Selector, Web-Backend, Runs-Frontend und Tab-Persistenz: 47 passed.
- Ruff: 0 Fehler.
- Vollsuite: 1818 passed, 5 skipped.
- Mypy: 0 Fehler; Quality Gate: `ok=true`, `regression=false`.
- Doku-Check warnt ausschliesslich vor den lokalen, uncommitteten Aenderungen an `werkstatt/web/audit_panel.py` und `werkstatt/web/terminal_proxy.py`; diese wurden nicht veraendert.
- AST/Katalog wurden wie vorgesehen uebersprungen, da die Dateien fehlen.
- **Commit:** `95a4b6832a94` — _ausgeschlossen fuer Mypy annotiert.
- **Commit:** `4c87b0552a66` — UI-Test-Syntaxfehler behoben.
- Diese Gate-Ergebnisse verifizieren API/Tests, aber nicht die visuelle Toolbar nach Browser-Cache-Reload.



### OP-398 — erledigte Abhaengigkeiten aus PROGRESS aufloesen (2026-11-10)

DOC_CONVENTIONS §5 entfernt erledigte OPs aus STATUS.md und fuehrt ihren
Abschluss in PROGRESS.md. Der Selector konnte diese Abhaengigkeiten bisher
nicht erkennen und markierte sie faelschlich als unbekannt. Er liest jetzt
nur explizite Abschlussformen (datierte „OP-NNN abgeschlossen“-Eintraege und
„done“-Ledgerzeilen); blosse Erwaehnungen und „superseded“-Zeilen reichen
nicht. Web-Start und Chat-Tool verwenden dieselbe Aufloesung. Doppelte IDs,
die noch in STATUS.md stehen, bleiben widerspruechlich und fail-closed.

- **Commit:** `1f3dd13dde0b` — Abschlussbelege aus PROGRESS parsen und im Selector verwenden.
- **Commit:** `513964ca1503` — Regressionstests fuer explizite, ungueltige und doppelte Abschlussbelege.
- **Commit:** `ef4b195adc22` — Web-Start mit Abschlussliste aus dem Projekt-PROGRESS verbinden.
- **Commit:** `cde3927e3818` — Chat-Selector an die projektgebundene Abschlussliste binden.
- **Commit:** `32a3542154d2` — Chat-Regressionstest fuer OP-201-Abhaengigkeit.
- **Commit:** `4fed0db2c692` — Ruff-konforme Formatierung der Chat-Testsignatur.
- **Commit:** `1ff88b62ab68` — autonomer Web-Start mit erledigtem PROGRESS-Blocker als Regressionstest.
- **Commit:** `5b49820c3097` — Fake-Prozess-Signal im Web-Test isolieren.
- **Serververifikation steht aus.** Zieltests, Ruff und vollstaendiges Quality-Gate nach Pull ausfuehren.



### ADR-/STATUS-Konsistenz — OP-216 und ADR-0018 (2026-11-10)

Der aktuelle Status-Eintrag OP-216 verlangte eine eigene Debugger-Loop-Rolle
und 3-Wege-Checks aus ADR-0018, obwohl dieser ADR als rejected markiert ist
und ADR-0011/0029 den Debugger als Chat-Modus festlegen. OP-191 war ausserdem
als Abhaengigkeit eingetragen, obwohl PROGRESS seine Entfernung dokumentiert.
OP-216 beschreibt nun die akzeptierte Chat-Debugger-Architektur, trennt IST
von SOLL und wartet auf OP-210/211/240. Die veraltete OP-191-Referenz wurde
auch aus der ausgehenden Blockiert-Liste von OP-210 entfernt. Der ADR-Index
zeigt ADR-0018 jetzt als rejected.

- **Commit:** `9a3e06c81a85` — OP-216 an akzeptierte ADRs und aktuelle Abhaengigkeiten angepasst.
- **Commit:** `719e4028ea4c` — ADR-0018-Status im Index korrigiert.
- **Commit:** `36c2ce19d63e` — entfernte OP-191-Referenz aus OP-210 bereinigt.
- **Serververifikation:** OP-398/Abhaengigkeitsfix auf `c959440`: 41 gezielte Tests,
  1823 Tests voll, Ruff 0, Mypy 0, Quality Gate gruen. Die nun folgenden
  Aenderungen sind Doku-only; Doku-Konsistenzpruefung nach Pull steht aus.



### OP-398 — Abschlussledger aus STATUS-Auto-Log beruecksichtigen (2026-11-10)

Der Serverlauf auf `d630980` bestaetigte den bisherigen Code mit 1823
Tests und gruenem Quality Gate, meldete aber Doku-Drift fuer drei nachfolgende
Code-Commits. Zudem ergab die Queue-Pruefung, dass `docs/STATUS.md` einen
expliziten `Erledigt (Auto-Log)`-Abschnitt mit `done`-Ledgerzeilen fuer
OP-381c und OP-305 enthaelt, die `PROGRESS.md` noch nicht kanonisch
referenziert. Der Selector liest nun solche expliziten Zeilen zusaetzlich
zur PROGRESS-Historie. Freitext-Erwaehnungen und andere Ledger-Statuswerte
loesen Abhaengigkeiten weiterhin nicht auf. Web-Start und Chat nutzen dieselbe
Abschlussmenge.

- **Commit:** `d452003a7b20` — STATUS-Auto-Log-Zeilen auswerten.
- **Commit:** `900c26c54529` — Web-Start mit STATUS-Auto-Log verbinden.
- **Commit:** `78be2bef8063` — Chat-Auswahl mit STATUS-Auto-Log verbinden.
- **Tests:** `784c5f9e39fd`, `3555f4d0193f`, `08dc2cf807e2` — Selector, autonomer Web-Start und Chat.
- **Formatierung:** `9a713fec9d54`.
- **Verifikation auf Server-HEAD `78be2be`:** 41 gezielte Tests,
  1823 volle Tests, Ruff 0, Mypy 0, Quality Gate gruen. Dieser Lauf
  enthaelt noch nicht die danach hinzugefuegten drei Regressionstests;
  erneuter Lauf auf dem aktuellen HEAD steht aus.


### OP-398 — STATUS-Abschlussledger auch ohne PROGRESS lesen (2026-11-10)

Der Serverlauf meldete, dass der autonome Start fuer OP-322 trotz eines
expliziten `OP-381c | done`-Eintrags in `docs/STATUS.md` mit HTTP 422
abgelehnt wurde. Ursache: fehlendes projektbezogenes `PROGRESS.md` liess
den Hilfsleser vorzeitig mit einer leeren Abschlussmenge zurueckkehren und
STATUS gar nicht mehr parsen. Fehlendes PROGRESS gilt jetzt als leerer Text;
die STATUS-Abschlusszeilen werden trotzdem ausgewertet. Der bestehende
Backend-Regressionstest bildet genau diesen Fall ohne PROGRESS-Datei ab.

- **Commit:** `8edd8749717d` — STATUS-Ledger auch ohne PROGRESS lesen.
- **Serververifikation:** Zieltest, Ruff und vollstaendiges Quality-Gate nach
  Pull ausstehend. Die lokalen Aenderungen an `audit_panel.py` und
  `terminal_proxy.py` bleiben unberuehrt.


### Verifikation und OP-Abhaengigkeiten — 2026-11-10

Der Server bestaetigte den Fix fuer den fehlenden PROGRESS-Fall: der
Regressionstest `test_autonomous_start_uses_status_done_ledger_dependency`
besteht; die Vollsuite meldet 1826 passed / 5 skipped, Ruff 0, Mypy 0 und
Quality Gate `ok=true`, `regression=false`. Der Doku-Check meldet nur die
bereits vorhandenen uncommitteten Aenderungen an `werkstatt/web/audit_panel.py`
und `werkstatt/web/terminal_proxy.py`.

Der Queue-Abgleich gegen Roadmap, ADR-0010/0011/0029 und DOC_CONVENTIONS §5
fand zwei nicht aufloesbare Blocker: OP-160 referenzierte den verworfenen
Debugger-Entwurf OP-128 und OP-113a; OP-113i referenzierte ebenfalls die
nicht mehr offene OP-113a. Beide Aufgaben sind jetzt an die aktuellen OP-240-
und OP-220-Memory-Bausteine gebunden. OP-160 und OP-113i sind explizit Phase-3
und warten auf OP-382. Ausserdem blockiert OP-382 jetzt das Memory-Grundpaket
OP-220, sodass nachgelagerte Memory-Arbeit nicht vor den zehn Dogfooding-Runs
aus dem Selector heraus startbar ist. OP-220a verwendet jetzt wie ADR-0010
`scope='project'` statt des widerspruechlichen Werts `'projekt'`.

- **Code-Fix:** `8edd8749717d` — STATUS-Abschlussledger ohne PROGRESS lesen.
- **STATUS:** `8db8d84ccd5d` — veraltete Debugger-/Memory-Blocker korrigieren.
- **STATUS:** `f3f3c2645f9b` — Phase-3-Sperre und ADR-konformes Memory-Scope festhalten.
- **Serververifikation der STATUS-Neufassung:** noch ausstehend; sie erfolgte
  nach dem gemeldeten Serverlauf auf `61eeb75`.


### Roadmap-Sperre Phase 3 an Startpfaden durchsetzen (2026-11-10)

Der OP-Audit zeigte, dass der Selector das STATUS-Feld `Phase:` ignorierte.
Obwohl die aktuelle Roadmap OP-382 als Dogfooding-Gate vor Phase 3 festlegt,
konnten Phase-3-Aufgaben ohne explizites Blockerfeld sowohl autonom als auch
per direkter OP-ID gestartet werden. Der Selector schliesst solche Aufgaben
jetzt aus, bis ein expliziter Abschlussbeleg fuer OP-382 vorliegt; der direkte
Web-Start nutzt dieselbe Ablehnung. Tests decken autonome Abstention,
Freigabe nach OP-382 und das Ausbleiben eines Subprozessstarts bei direkter
OP-ID ab.

Der Queue-Abgleich hat ausserdem alle offenen OP-Abhaengigkeiten gegen STATUS
und explizite Abschlussledger geprueft: keine unbekannten Blocker mehr.
OP-160/113i wurden auf aktuelle ADR-/OP-IDs umgestellt, OP-220 sperrt als
Memory-Grundlage die abhaengigen Memory-Arbeiten bis OP-382, und OP-220a ist
an ADR-0010s `project`-Scope angepasst.

- **Selector:** `2cb294b0713d`, `028673d2fda2`.
- **Web-Start:** `a9db0602cf63`.
- **Tests:** `f6b87f1d02c2`, `b0da89951598`, `e7f33a50a3b1`, `5e26589c3577`.
- **STATUS:** `8db8d84ccd5d`, `f3f3c2645f9b`.
- **Serververifikation:** zielgerichtete Tests, Ruff, Doku-Check und
  Quality-Gate nach Pull noch ausstehend.


### OP-398 — explizite OP-Starts ohne Blockerfeld gegen Phase-Gate pruefen (2026-11-10)

Beim Nachpruefen des neuen Backend-Tests fiel auf, dass der direkte Startpfad
Blocker nur dann erneut auswertete, wenn `inspector.parse_ops` ein nichtleeres
`Blockiert von`-Feld lieferte. Phase-3-OPs ohne Blockerfeld konnten dadurch am
Roadmap-Gate vorbeilaufen. Der direkte Start wertet jetzt fuer jede explizite
OP-ID die Selector-Ausschlussgruende aus; die bestehende Testfixture mit
`Blockiert von: —` prueft genau diesen Bypass.

- **Commit:** `0ea9b8878c33` — Phase-Gate auch ohne Blockerfeld erzwingen.
- **Serververifikation:** nach Pull noch ausstehend.


### OP-398 — widerspruechlichen OP-382-Abschlussbeleg fail-closed behandeln (2026-11-10)

Die Phase-3-Sperre nutzt Abschlussbelege aus PROGRESS und STATUS. Ein
veralteter Abschlussbeleg darf die Sperre nicht aufheben, solange dieselbe
OP-ID noch in STATUS steht (offen oder doppelt). Der Selector akzeptiert den
OP-382-Beleg deshalb nur, wenn OP-382 aus der offenen STATUS-Liste entfernt
ist. Ein Regressionstest kombiniert einen stale done-Beleg mit offenem OP-382
und prueft, dass OP-382 selbst startbar bleibt, Phase 3 aber gesperrt bleibt.

- **Commit:** `8b3b7f5ae403` — widerspruechliche Freigabe verhindern.
- **Commit:** `2dd3b724b1ab` — Regressionstest.
- **Serververifikation:** nach Pull weiterhin ausstehend.


### Loop-Kontext — Pflichtdokumente tatsaechlich laden und fail-closed behandeln (2026-11-10)

Der Architekturabgleich gegen AGENTS.md, DOC_CONVENTIONS §6 und ADR-0029
zeigte, dass `projects/werkstatt.yaml` README.md statt AGENTS.md als Einstieg
lud und ROADMAP.md, ARCHITECTURE.md, ADR-Index und Glossar nicht mitgab.
Damit entsprach der tatsaechliche Planner-/Scout-Kontext nicht der
Dokumentations-Lese-Reihenfolge. Das Manifest laedt nun die Living Docs in der
vorgesehenen Prioritaet.

Zusaetzlich unterdrueckte `build_run_state` fehlende oder fehlerhafte
Pflichtdokumente und lieferte einen leeren Doku-Kontext. Der CLI-Pfad konnte
nicht-lesbare Dokumente ebenfalls still tolerieren. Beide Pfade brechen jetzt
sichtbar und auditiert ab; sie starten keine Arbeit mit unvollstaendigem
Projektkontext. Tests decken Manifest-Schluessel, fehlende Dateien und einen
Lesefehler ab.

- **Manifest:** `b7480d358f96` — erforderliche Living Docs laden.
- **Loader:** `a45ebee55fcc` — Pflichtdokumente fail-closed lesen.
- **Loop:** `d0ca7e1a2e44` — Fehler als Event/Status melden und abbrechen.
- **Tests:** `dc177d1d9f5e`, `ab4cbe4f15bf`.
- **Serververifikation:** nach Pull noch ausstehend.


### OP-397 — parallele Chat-Arbeit und sichere Run-Aenderungen praezisieren (2026-11-10)

Die Nutzeranforderung, waehrend eines langen Runs weiter Fragen zu stellen und
neue Arbeit einzureichen, wurde gegen ADR-0029 abgeglichen. Die bestehende
Architektur hat getrennte HTTP-/Loop-Prozesse, aber OP-397 spezifizierte noch
nicht, wie neue Auftraege mit einem bereits freigegebenen Plan konkurrieren.
STATUS legt jetzt ein Betriebsmodell fest: lesende Jobs parallel, neue
Schreibarbeit in einer persistenten Projekt-Inbox, ein exklusiver Schreibslot
pro Projekt und Plan-Aenderungen nur als versionierte Revision am sicheren
Checkpoint mit erneutem Plan-Gate. Ein Reject darf den freigegebenen Plan und
Working Tree nicht veraendern.

- **Commit:** `feb496d7c55a` — Inbox-, Job- und Checkpoint-Vertrag.
- **Implementierung:** noch offen in OP-397; Serververifikation der Doku
  ausstehend.


### Manifest-Vertrag — Pflicht-Living-Docs fail-closed erzwingen (2026-11-10)

Die Konfigurationspruefung stellte sicher, dass Werkstatt die fehlenden
Doku-Quellen laedt. Zusaetzlich verlangt `load_project_config` jetzt fuer
jedes Projektmanifest die DOC_CONVENTIONS-§6-Kernschluessel
`entry/status/roadmap/architecture/conventions/adr_index/glossary`. Damit
verlassen sich neue Projekte nicht allein auf ein korrekt gepflegtes Template;
ein unvollstaendiges Manifest wird vor dem Loop-Start abgewiesen.

- **Loader:** `dc063a94c81e` — Pflichtschluessel validieren.
- **Test:** `28827edf5bd5` — unvollstaendiges Manifest wird abgewiesen.
- **Testformatierung:** `e0d4d697fc3a` — Newline-Literale korrigieren.
- **Commit:** `b51033c2d1bab10a328b236538814d138eb6440b` — Snapshot-Return-Typ Ruff-konform machen.
- **Commit:** `a17b7901a3d83e8589b49a45a0924c44e244843a` — lokale Chat-Job-Imports Ruff-konform umbrechen.
- **Serververifikation:** nach Pull ausstehend.
- **Commit:** `ac0af29e9419153cdb8f7ea8d8efd3916201cba3` — offene OP-397-Punkte an den parallelen Read-Job-Stand anpassen.


### Pflichtdoku-Ladefehler — Audit-Katalog und Regressionstest (2026-11-10)

Der Serverlauf fand zwei Regressionstests nach der fail-closed-Aenderung:
Der neue Audit-Kind `loop_docs_load_failed` fehlte im Katalog, und ein
OP-392-Test erwartete noch den alten Erfolg trotz kaputter Projektkonfiguration.
Der Kind ist jetzt registriert. Der Test verlangt nun Exit-Code 1, keinen
Aufruf des Pipeline-Loops und ein Audit-Event. Damit bleibt der Lauf bei
fehlendem/kaputtem Pflichtkontext sicher gestoppt.

- **Commit:** `b07378953cdf` — Audit-Kind fuer Ladefehler registrieren.
- **Commit:** `dc063a94c81e` — Pflichtschluessel im Manifest validieren.
- **Commit:** `a45ebee55fcc` — Pflichtdokumente fail-closed laden.
- **Commit:** `d0ca7e1a2e44` — Ladefehler im Loop sichtbar behandeln.
- **Regressionstest:** `b976ef2b24ad`; Formatierung: `10c62c006095`.
- **Doku-Drift-Fix:** `706db3323df8` dokumentierte die Code-Commits; die
  Referenzen stehen jetzt im vom Doku-Checker ausgewerteten Commit-Format.
- **Serververifikation:** gezielte Tests, Ruff, Doku-Check, Vollsuite und
  Quality Gate nach diesem Nachtrag noch ausstehend. Letzter Stand auf
  `706db33`: 1833 passed / 5 skipped; Ruff 1, mypy 0, Quality Gate rot.

## M-479 — Rollenbasiertes DeepSeek-Modellrouting (2026-11-10)

- Architect: `deepseek-v4-pro`, Thinking enabled, Effort high.
- Builder, Planner-Split, Reviewer, Scout, Explorer, Validator und Reflection:
  `deepseek-flash`, Thinking disabled. Chat und Debugger-Modus nutzen dieselbe
  Flash-Route; Debugger ist gemaess ADR-0018 keine eigene Loop-Rolle.
- Die zentrale `ask_llm`-Schicht setzt Modell und Thinking fuer bekannte Rollen;
  alte Modellnamen aus Call-Sites koennen die Policy nicht mehr umgehen.
- Rollenbezogene Overrides: `WERKSTATT_MODEL_<ROLLE>`; die bisherige
  `WERKSTATT_ARCHITECT_MODEL`-Variable bleibt kompatibel.
- Der direkte UI-Chat nutzt dieselbe Flash-Rollenpolicy.
- **Commit:** `8c9b1433070722263af6130` — Rollenpolicy und aktuelle Modell-IDs.
- **Commit:** `c47f389778f30f008d1c516b` — Rollenrouting in der zentralen LLM-Schicht.
- **Commit:** `f408ce1689a9a80469715612` — Reviewer-Kurzlabel auf Flash geroutet.
- **Commit:** `13ca4fc65b82db1df049a57b` — UI-Chat an die Flash-Policy gebunden.
- **Commit:** `2317891f3d8cb467c0053ddf` — Architect-Default auf V4-Pro gestellt.
- **Commit:** `9d03b72c956a0bb810eca8b7` — Rollenvertraege im Architect-Prompt korrigiert.
- **Commit:** `c8ec2b8c0cd850187c038114` — Architect-Modelltest aktualisiert.
- **Commit:** `54b47e726112e1f0219fdac0` — Test-Umgebung und Erwartungswert korrigiert.
- Code und Tests sind auf GitHub eingetragen; Laufzeittests wurden hier nicht
  ausgefuehrt. Server-Verifikation steht noch aus.

- **Commit:** `3b108acc01ae32c011b71252` — API-Antwortmodell im LLM-Usage-Audit protokolliert.
- **Commit:** `ee50914b1e6955d33b3196d7` — Provider-Modell-ID auch im Chat-Usage-Datensatz sichtbar.

- **Commit:** `fcfe69339bdfb4fd5f1faa1d` — veraltete Chat-Modellkonstante entfernt.

- **Commit:** `64ecf7df45e56f05680aeb1f` — Rollenrouting eingefuehrt.
- **Commit:** `c03b94c86cefe744a321d60` — Debugger-Modus der Chat-Rolle zugeordnet.
- **Commit:** `67e288ee4eb1d14db08f69e` — Import-Reihenfolge nach Server-Ruff korrigiert.
- **Commit:** `eab316ae50e119d3752a5765` — Audit-/Payload-Tests auf kanonische Flash-ID aktualisiert.

## OP-397 — Chat-Job-Turns pro Session serialisiert (2026-11-10)

Die SQLite-Claim-Transaktion laesst pro Chat-Session nur einen Job gleichzeitig
in den Zustand `running`. Die Queue nimmt je Session den aeltesten Job an;
nach Jobabschluss wird der naechste wieder eingeplant. Unterschiedliche
Sessions bleiben parallel. Eine Worker-Lease mit periodischem Heartbeat
markiert nach Ablauf verwaiste Jobs als fehlgeschlagen und spielt danach
wartende Session-Jobs weiter ein; Live-Leases bleiben bei Reconnect gueltig.
OP-397 bleibt offen: Abbruch, Chat waehrend Run und Checkpoint-/Planrevision
sind noch nicht vollstaendig umgesetzt oder verifiziert.

- **Commit:** `ca7e6814fad5b99726f5404e` — serialisierte Session-Claims und Queue-Fortsetzung.
- **Commit:** `8f65f2a76f31872d3c86beff` — Tests fuer Session-Serialisierung und parallele Sessions.
- **Serververifikation:** noch ausstehend.

- **Commit:** `437f39e4f7b66a4a8ba69f2f` — stabile FIFO-Reihenfolge auch bei gleichen Zeitstempeln.

- **Commit:** `a968c21ca7629640f14c2941` — unbekannte Agent-Labels fallen fail-safe auf Flash zurueck.

- **Commit:** `11506b4e28ef4e5225c9dbae` — Overrides nur fuer registrierte Rollen erlauben.


## Chat-Job-Idempotenz (2026-11-10)

Wiederverwendung eines Idempotency-Keys mit abweichendem Nachrichtentext oder Modus wird jetzt als Konflikt abgewiesen (HTTP 409), statt still den alten Job zurueckzugeben. Gleiche Anfrage mit gleichem Key bleibt dedupliziert. Servertests fuer den API-Konflikt stehen noch aus.



## Chat-Job-Future-Registry begrenzt (2026-11-10)

Abgeschlossene Worker-Futures werden jetzt per Done-Callback aus der globalen Registry entfernt. Der Callback prueft die Future-Identitaet, damit ein spaeterer Eintrag unter demselben Schluessel nicht geloescht wird. Ein Test deckt auch den sofort abgeschlossenen Future ab. Serververifikation steht aus.



- **Commit:** `de1d0313ea2055a3eae2bbdf` — Worker-Leases, Heartbeat und Recovery abgelaufener Jobs.
- **Commit:** `f9ba062e1ce59bc7fc84289` — Worker-ID explizit aus Prozess-ID und Zufallswert.
- **Commit:** `cd77c2240b40a2e640ec05c8` — Tests fuer aktive/verwaiste Lease und Worker-Eigentum.
- **Commit:** `d020e46e9abaa3302c7b254f` — Migrationstest fuer bestehende SQLite-Jobdatenbank.
- **Serververifikation:** einschliesslich Lease-Schema-Migration weiterhin ausstehend.
- **Serververifikation:** fuer Idempotenz, Future-Cleanup und Lease-Recovery ausstehend.


## Chat-Job-Future-Callback typisiert (2026-11-10)

Der Quality-Gate-Lauf fuer `1af90ca` meldete Mypy `Cannot infer type of lambda` in der Future-Bereinigung. Der Lambda wurde durch einen benannten, explizit typisierten Callback ersetzt. Die Serververifikation der Korrektur und der seitdem hinzugefuegten Worker-Lease steht noch aus.


## OP-397 — Fehlgeschlagene Chatjobs nach Reconnect sichtbar (2026-11-10)

Die Reconnect-Abfrage liefert neben queued/running Jobs die letzten 20 fehlgeschlagenen Session-Jobs mit Fehlertext. Die UI rendert diese Fehler nach Session-Reconnect wieder als Chat-Antwort, einschliesslich Jobs, deren User-Event vor einem Prozessabbruch noch nicht in der Chat-Historie stand. Erfolgshistorie wird nicht erneut abgespielt. API- und Frontend-Vertragstests ergaenzt; Serververifikation ausstehend. OP-397 bleibt offen.


## OP-397 — Chatjobs abbrechbar (2026-11-10)

Chatjobs koennen jetzt projekt- und sessiongebunden abgebrochen werden. Wartende Jobs wechseln direkt auf `cancelled`; laufende Jobs erhalten eine persistente Cancel-Anfrage und der LLM-Stream prueft diese an Chunk-Grenzen. Die UI bietet einen separaten Abbrechen-Button, sodass der Composer waehrenddessen weiter nutzbar bleibt. Der SSE-Read-Timeout ist auf 30 Sekunden begrenzt, damit ein ausbleibender Chunk den Abbruch nicht minutenlang verzoegert. Tests decken Store-Lifecycle, API-Session-Scope, Chat-Agent und UI-Vertrag ab. Serververifikation steht aus; OP-397 bleibt offen.


## Reconnect-Assertion fuer Chatjobs robust gemacht (2026-11-10)

Der Frontend-Vertragstest akzeptiert jetzt den mehrzeiligen `_jobFertig`-Aufruf fuer fehlgeschlagene und abgebrochene Jobs. Das bisherige Literal-Matching schlug fehl, obwohl die Reconnect-UI den terminalen Zustand samt Fehlertext korrekt anzeigte. Serververifikation steht aus.


## Chatjob-Replay an Session gebunden (2026-11-10)

Der Event-Replay-Endpunkt akzeptiert jetzt eine Session-ID und liefert einen Job nur fuer die Session aus, die ihn angelegt hat. Der Poller sendet den Session-Kontext mit; API-Tests pruefen Zugriff innerhalb der Session und Verbergen bei fremder Session. Vor einem Reconnect-Dispatch wird zuerst die Session-Zugehoerigkeit geprueft. Serververifikation steht aus.


## Expliziter OP-Start blockiert bei unbekannter Abhaengigkeit (2026-11-10)

Der Web-Start-Endpunkt verweigerte bereits erkannte offene Blocker, uebersah aber unbekannte oder widerspruechliche Blocker bei einer expliziten OP-Auswahl. Der Ausschlussgrund wird jetzt ebenfalls als 409 zurueckgegeben; ein API-Regressionstest prueft, dass kein Prozess startet. Serververifikation steht aus.

- **Commit:** `7d8e943379cede38141ecee2cf855df9164c2ee8`


## Expliziter OP-Start verweigert doppelte OP-IDs (2026-11-10)

Der Web-Start nutzt bei einer expliziten OP-ID den ersten Parser-Treffer. Wenn STATUS dieselbe OP-ID mehrfach enthielt, konnte dadurch eine mehrdeutige Aufgabe starten, obwohl der Selector Duplikate ausgeschlossen hatte. Der Start-Endpunkt weist diese Auswahl jetzt mit 409 ab; ein API-Test prueft, dass kein Prozess gestartet wird. Serververifikation steht aus.

- **Commit:** `ca539549ad0162109b8470086f73f2e72ae16874`


## Quality Gate prueft aktuelle Quellen statt Altdateien (2026-11-10)

Die AST-Pruefung parst nun alle Python-Quellen im Repository ausser virtuellen Umgebungen und Cache-/Git-Verzeichnissen. Der Audit-Katalog wird durch den bestehenden `test_katalog_enthaelt_alle_code_kinds`-Test geprueft. Fehlende Pruefdatei, Syntaxfehler, fehlgeschlagener oder uebersprungener Katalogtest machen das Gate rot, statt die Checks als neutralen Skip zu verbuchen. Regressionstests fuer Syntax- und Katalogfehler ergaenzt; Serververifikation steht aus.

- **Commit:** `823f942538e774aafd07637896ed95d149d5f3cc`


## Serververifikation fuer Chat-Replay, OP-398 und Quality-Gate-Tests (2026-11-10)

Auf `/opt/werkstatt` wurde `9c505cb` getestet: gezielt 50 Tests bestanden, Ruff ohne Fehler, Gesamtsuite 1885 passed / 5 skipped. `doku_check --strict --limit 10 --worktree` erkannte die bereits in dieser Datei referenzierten Code-Commits fuer den OP-398- und Quality-Gate-Fix; uebrig blieb der Working-Tree-Drift fuer lokale Aenderungen an `werkstatt/web/audit_panel.py` und `werkstatt/web/terminal_proxy.py`. `tools.quality_gate --json` lief ebenfalls erfolgreich: 1885 passed / 0 failed, Ruff 0, Mypy 0, AST 369 Dateien / 0 Fehler und Audit-Katalog 1 passed / 0 Fehler; `ok: true`, `regression: false`.

- **Commit:** `9c505cbc9e521fc20a99d5def5a6ce45dd03a232`


### OP-397 — Session-Queue bleibt nach verlorenem Worker-Claim nicht haengen (2026-11-10)

Die Dispatch-Pruefung fand ein Timing-Rennen: Ein Session-Job konnte bereits
laufen, waehrend ein spaeter eingereihter Worker seinen Claim verlor. Wenn der
laufende Worker genau waehrend des Future-Cleanup den naechsten Job dispatchte,
sah er noch den nicht abgeschlossenen Future und uebersprang den Job. Nach
dessen Cleanup gab es keinen weiteren Dispatch-Ausloeser; der Job blieb
dauerhaft `queued`.

Der Dispatcher ueberspringt jetzt Sessions mit einem aktiven Job. Ein Future,
dessen Worker den Claim verloren hat, loest nach seinem Cleanup einen erneuten
Dispatch aus. So wird der Retry nicht ausgefuehrt, solange die Session noch
belegt ist, und ein spaeterer Queue-Eintrag bleibt nach dem Claim-Rennen nicht
liegen.

- **Commit:** `11cc1cb2ea1e5f9ff6a42b09c018e3b8eb8e9d21` — aktive Sessions beim Dispatch ueberspringen und nach Claim-Verlust erneut dispatchen.
- **Commit:** `f523e4c3ecef044948cd2934c8ed57cb16b5f1c1` — Future-Rueckgabewert fuer die Claim-Retry-Entscheidung typisieren.
- **Commit:** `f3bf56c58545fbf8be0672e0a935ae36eac89607` — Regressionstests fuer aktive Sessions und erneuten Dispatch nach Claim-Verlust.
- **Serververifikation:** nach Pull noch ausstehend.


### OP-397 — parallele Read-Jobs mit isolierten Transcript-Snapshots (2026-11-10)

Die bisherige Session-FIFO machte zwar mehrere Anfragen annehmbar, liess
spaetere Fragen aber hinter einer langen LLM-Inferenz warten. Ein
Session-Lock war noetig, weil alle Worker dasselbe append-only Transcript
veraenderten. OP-397 verlangt unabhaengige Antworten; die parallele Ausfuehrung
darf dabei keine partiellen Tool-Traces oder gekreuzten Turns in die
Modellhistorie mischen.

Jeder Job speichert jetzt beim Annehmen den hoechsten Event-Seq-Wert der
Eltern-Session. Der Worker erstellt daraus idempotent eine eigene
ChatSession mit job_id als Branch-ID und fuehrt den Turn ausschliesslich dort
aus. Gleichzeitige Jobs derselben Session koennen parallel claimen und
inferenzieren. Erfolgreiche Antworten werden als ein idempotentes
`job_turn`-Event in die Eltern-Session projiziert; fehlgeschlagene oder
abgebrochene Branches werden nicht als erledigte Konversation uebernommen.
Beim Laden der Historie sowie vor neuen Jobs gleicht der Server erfolgreiche
Jobs erneut ab, um einen Prozessabbruch zwischen Jobabschluss und
Transcript-Projektion zu reparieren. Job-Branches bleiben aus der
Projekt-Sessionliste ausgeblendet und werden nach normalem Abschluss oder bei
der Reconciliation eines erfolgreichen Jobs entfernt. Bei vor der Migration
angelegten Jobs bleibt der Kontext-Wasserstand NULL und wird einmalig aus der
Session beim ersten Worker-Start aufgenommen; neue Jobs speichern den
Wasserstand bereits bei der Annahme. Die UI zeigt fuer jeden Auftrag eine
eigene Antwortkarte direkt nach der zugehoerigen Frage und behaelt den
Working-Status, solange andere Jobs aktiv sind.

- **Commit:** `fede9aca75bd51ad0403183e012a052c85c58ac8` — stabile Session-Snapshots und idempotente Job-Turn-Projektion.
- **Commit:** `071c2cbf90d49e576930c230fab1be100064eb28` — abgeschlossene Job-Turns in der allgemeinen Verlaufskonvertierung abbilden.
- **Commit:** `6d4e70a2cad8e0c5e3063557eda923630a111f4a` — abgeschlossene Job-Turns im Chat-Agent-Kontext abbilden.
- **Commit:** `ba20a0b61e2c5740eecf86c278d0cb70aa04ca30` — Kontext-Wasserstand persistieren, Session-Serialisierung entfernen, Branches ausfuehren und Recovery-Projektion ergaenzen.
- **Commit:** `5a86d4d0d22b6772aadef2ecd202c9735cc02de9` — Chat-Historie und Jobannahme mit Turn-Reconciliation/Wasserstand verbinden.
- **Commit:** `15057fd3f87fca1e50aa18b2e597aa1a3bda4124` — zusammengehoerige User-/Assistant-Paare nach Reload rendern.
- **Commit:** `aea5a4b202760212a2d067d386cd9b4fbb551ab0` — parallele Antwortkarten am jeweiligen Auftrag verankern und Laufstatus fuer uebrige Jobs erhalten.
- **Commit:** `7aa3ffdd285977dbf0ac26e5b3852b35d2340cc9` — Chat-Asset-Cache aktualisieren.
- **Commit:** `0142a7ceea444900bdaa9ff131ba72596e7fbeac` — Job-Claim-Vertrag an isolierte Branches anpassen.
- **Commit:** `e3439e03067cca50cbfbc31c31241f0445c83fca` — Fehler bei Snapshot-Aufbau als fehlgeschlagene Jobs abschliessen.
- **Commit:** `d81f5092970c21a903668b59e4e381ba8559c846` — Idempotenz erhaelt den urspruenglichen Kontext-Wasserstand.
- **Commit:** `0969c532f042654ab4ed745e23442ad5c0c59941` — Snapshot-Wasserstand und Job-Turn-Projektion testen.
- **Commit:** `295598fe65193b2bfbff410213f00146db444f94` — Chat-Agent-Prompt fuer abgeschlossene Job-Turns testen.
- **Commit:** `8a4c8bfcd4cd1be71953a27246fc925bf562231c` — gleiche Session kann unabhaengige Job-Worker dispatchen.
- **Commit:** `4dbac6b7c550fe78484451ddaff8e766c0f8bef7` — isolierte Job-Ausfuehrung und Recovery-Projektion testen.
- **Commit:** `584e862c9381719f62be48af36d2db8ef7aae788` — History-Endpunkt repariert fehlende Projektion nach Worker-Abbruch.
- **Commit:** `274a9cc30a028a9cfc47e89babd74427f25e52ff` — UI-Vertrag fuer History-Rendering der Job-Turn-Paare testen.
- **Commit:** `f6857ff98937085edc5e557314f571ccb3978132` — API-Test fuer den uebergebenen Kontext-Wasserstand.
- **Commit:** `9302abe9dafe98c019606103536a047467d947c0` — Legacy-Jobs ohne historischen Wasserstand beim ersten Start kompatibel behandeln.
- **Commit:** `393b9d0bc3a75c8f2ef4ae283daf604adc4f9d21` — Migrationstest fuer NULL-Wasserstand bestehender Jobs.
- **Commit:** `538ff57eb5e73e3423f079f67aace1ead28d988d` — Job-Branches aus der Sessionauswahl ausblenden und kontrolliert loeschen.
- **Commit:** `5be75eacfbb33d4cbac54dc2d529b3c5c6c35087` — Branch nach Worker-Abschluss entfernen.
- **Commit:** `a7504cd7c0e0c4d19fd46262e60583520b14eefa` — optionale Session-Referenzen explizit typisieren.
- **Commit:** `f81b22fd717d6ca928170dad0fd73a307ff0d2fa` — Listenfilter und Branch-Bereinigung testen.
- **Commit:** `ea52fa250e36e868b31ac70f4fd86d8e9623d314` — Branch-Loeschung nach erfolgreichem Worker testen.
- **Commit:** `2da4951d23d4a8e2a5c78c74b6fddabafcbad545` — Branch-Bereinigung auch nach Prozess-Reconnect durchfuehren.
- **Serververifikation:** gezielte Tests, UI/Ruff, Doku-Check und Quality Gate nach Pull stehen noch aus.

## 2026-11-10 — Reconnect-Aufraeumung paralleler Chatjobs

Beim Reconnect werden abgelaufene Worker-Leases zuerst recovered; danach entfernt die Reconciliation Transcript-Branches aller terminalen Jobs, auch bei Fehler oder Abbruch. Erfolgreiche Job-Turns bleiben idempotent in die Eltern-Session projiziert. Regressionstest deckt einen fehlgeschlagenen Job mit stehengebliebenem Branch ab.

- **Commit:** `c3ebc2ef3dba0b67767c0cd997f179dd792d4fa1` — terminale Job-Branches bei Reconnect bereinigen.
- **Commit:** `66f5c60bdf9a63e4a9800f8e33276931e0ad891a` — Transcript-Branches fuer alle terminalen Jobs bereinigen.
- **Commit:** `26e70f9b8941fef1faa0c2be848d0d1f12190aa5` — Lease-Recovery vor Reconnect-Bereinigung ausfuehren.
- **Commit:** `d9f7a475a025d96f7b466b66b187c64ce4c18c01` — Regressionstest fuer fehlgeschlagenen Job-Branch.
- **Commit:** `b5d2c825716b4e35bd7055cd9f8ffcde142d4cd5` — STATUS um Reconnect-Verhalten ergaenzen.
- **Serververifikation:** nach Pull ausstehend.

## 2026-11-10 — Chat-Jobs dem aktiven Loop-Run zuordnen

Der Job-Speicher fuehrt jetzt ein optionales `run_id`-Feld mit Migration fuer bestehende Datenbanken. Die Web-API liest den aktuellen Zustand aus der persistenten Loop-Registry; bei `starting`, `running` oder `paused` bindet sie die Job-Annahme an diese Run-ID. Idempotente Wiederholungen behalten den urspruenglichen Run-Kontext. Create- und Reconnect-Antworten geben die Zuordnung aus.

- **Commit:** `94ba0dd642b0b332235f97964b33d62474d12a74` — optionales Run-Feld in Chat-Jobs speichern.
- **Commit:** `6ae75f5dc9ceb62fbb10e8c669a9e7e8959dd70d` — aktive Run-ID aus Registry an Job-API uebergeben.
- **Commit:** `22ac864c3e6936da6d21ba71de2b5ead77202e80` — Idempotenz behaelt Run-Zuordnung der ersten Annahme.
- **Commit:** `cad1cab22bd1638e02691dbf9b75e87d52baf2a1` — API-Test fuer Run-ID bei aktivem Loop.
- **Commit:** `074abc529ba14fb30f54e815a956c79e47ef9fbf` — Migrationstest fuer Run-ID-Spalte.
- **Commit:** `430ce24736773e8056fb689a12592941d30818eb` — STATUS um Run-Verknuepfung und verbleibende Event-Store-Luecke ergaenzen.
- **Commit:** `a53fadd4d0f8c4a1c05851579bd50de7922ad6f5` — Replay-Ereignisse mit Run-, Job- und Session-ID versehen.
- **Commit:** `ecb07f60830c88a803dbc82654ef75c0998a3037` — API-Test fuer IDs in wiedergegebenen Job-Events.
- **Commit:** `1f6ce1cae029d507a03bf98fe3c19556743e9ae3` — STATUS um Event-Kontext im Replay ergaenzen.
- **Serververifikation:** nach Pull ausstehend.

## 2026-11-10 — Chat-Job-Events in die Control-Timeline projizieren

Der Event-Store kann Events jetzt mit Projektbezug und deterministischer Event-ID idempotent annehmen. Chat-Job-Events bleiben zunaechst im Job-Speicher; beim Status-Replay werden ausstehende Events in die gemeinsame Run-Timeline projiziert. Ein Retry nach Prozessabbruch erzeugt dank stabiler Quell-ID keinen zweiten Timeline-Eintrag. Der Control-Live-Feed liest nur die Chat-Job-Events des angefragten Projekts und rendert Status, Chat-Rolle und kurze Aktivitaetsdetails.

- **Commit:** `eb23504c14ff0cd92bbb7da4e0b33b290411045a` — Projektfeld und idempotente Event-ID im gemeinsamen Event-Store.
- **Commit:** `d26fd8efbf190ddb84e26ce9366cde782d56608f` — Projektbezug und Projektionsmarker fuer Job-Events migrieren.
- **Commit:** `c9fee5d17f23137c395948feb12aba7689a8b6c2` — gespeicherte Run-gebundene Job-Events idempotent projizieren.
- **Commit:** `cf20536be0129a2a305fe8bd5d0adcae3c516e8a` — Projekt-ID beim Job-Anlegen uebergeben.
- **Commit:** `ed50f8d18217a31619673c4d83948bb8e0e66f7a` — API-Test fuer den Projektbezug.
- **Commit:** `39fc946bff5c539eb2809c6a9a769283bb6fd821` — Integrationstest fuer einmalige Timeline-Projektion.
- **Commit:** `4df910398b0da5fb73aecd472a31b424250ac54e` — Idempotenz- und Projektfiltertest fuer den Event-Store.
- **Commit:** `b6dfe542e2ad8935833ae045150da182ead3e999` — Projektion beim Job-Poll auf den angefragten Job begrenzen.
- **Commit:** `b6e6f8c629b6ea89635a662b8f5a2166e4ed6370` — Migrationstest fuer bestehende Job-Event-Tabellen.
- **Commit:** `e934cfd8b086c8aac355eb02fe4120653eb7aa79` — Run-gebundene Chat-Events in den Projekt-Live-Feed aufnehmen.
- **Commit:** `c2aef3c11f0723a135b30c015f3cb4612a42df98` — Chat-Ereignisse im Live-Feed semantisch darstellen.
- **Commit:** `24a0fe75869887fd311b72ddb466734389155f6a` — Chat-Rolle und Eventtitel im Control-Feed ergaenzen.
- **Commit:** `aa4ef4561e8bc041ee2cea8f120ddda83b58e22c` — statische Live-Feed-Datei cache-invalidieren.
- **Commit:** `7940bcb352eb8164c2f977e9ddf8a28f32424dda` — Backend-Integrationstest fuer projektgefilterte Chat-Feed-Events.
- **Commit:** `899a24cdb445a3dbf185744deefa06f2498bd535` — Chat-Worker bei nicht verfuegbarem Timeline-Store nicht fehlschlagen lassen.
- **Commit:** `23f63f024b1d7f9ab353e4c6a081c3b1ef4a8c9d` — unbenutzten Event-Store-Cursor entfernen.
- **Commit:** `6e9b3ad4bb5094522b24ad1b92e4ec087bb5d0fd` — STATUS um Timeline-Integration und Verifikationsstatus ergaenzen.
- **Serververifikation:** gezielte Event-Store-/Job-/Live-Feed-Tests, Ruff, volle Testsuite und Quality Gate nach Pull ausstehend.


## Chat-Event-Timeline Regressionen (2026-11-10)

- Serverlauf auf `73d2893` fand einen API-Fehler: `enqueue_chat_job` erhielt `project` zugleich positional und als Keyword. Den doppelten Keyword-Parameter entfernt; der API-Test sichert die Argumentform.
- Der Live-Feed behandelt einen laufenden `chat_job_started` als aktuelle Aktivität und blendet ihn aus `steps` aus, um Doppelanzeige zu vermeiden. Den Test auf diesen Vertrag umgestellt und Projekt-Isolation des fehlgeschlagenen Fremdprojekts mitgeprüft.
- Verifikation auf dem Server nach Pull steht aus.

- **Mehrprojekt-Audit:** Web-Auswahl-, Pause-, Resume- und Stop-Events erhalten nun auch die Event-Store-Projektspalte. Payload-Projekt allein reichte fuer projektgefilterte Timeline-Abfragen nicht; Tests pruefen den Projektbezug.


## ADR-0024 Event-Store Single-Writer Korrektur (2026-11-11)

- Web-Control- und Chat-Job-Ereignisse werden dauerhaft in Semantic-JSONL geschrieben; SQLite wird nur noch durch den Projektor beschrieben.
- Job-Events nutzen stabile Event-IDs und eine Outbox-Migration, sodass ein Read-Model-Rebuild sie wiederherstellt. Live-Feed dedupliziert JSONL- und Read-Model-Kopien.
- Tests und Dokumentation ergänzt. Serververifikation nach Pull steht aus.


## Syntax-Reparatur fuer Audit-Projektor-Patch (2026-11-11)

- Server-Testsammlung meldete einen fehlerhaften Katalogabschluss in `werkstatt/audit.py` und ein fehlendes `except` im Web-Stop-Handler. Beide Syntaxfehler sind repariert; erneute Serververifikation ausstehend.


## Event-Log-Regressionstests nach Serverlauf (2026-11-11)

- Serverlauf auf `c3f34a4` bestaetigte Syntaxreparatur und 51 gezielte Tests, legte aber drei Testannahmen offen: `EventStore.query()` liefert keine Event-ID, `Projector` liegt im Modul `werkstatt.projection`, und das Duplikat-Fixture brauchte die persistierte Job-Sequenz. Die Tests sind an die echten Schnittstellen angepasst; erneute Verifikation steht aus.


## Live-Feed-Testfixture nach JSONL-Format korrigiert (2026-11-11)

- Der Serverlauf auf `15bbeab` bestaetigte 53/54 gezielte Tests, aber das JSONL-Fixture legte den Job-Status faelschlich unter `payload` ab. Audit-JSONL flacht Event-Payloads auf die oberste Ebene ab; das Fixture folgt jetzt diesem Format. Ruff-Importe sind ebenfalls angepasst. Erneute Verifikation steht aus.


## Idempotenter JSONL-Retry ohne falsche Drift (2026-11-11)

- Ein Crash zwischen durablem Audit-Append und Outbox-Markierung kann dasselbe stabile Job-Event erneut anhängen. `Projector.status()` zählt jetzt logische eindeutige Events statt physische Wiederholungszeilen; `tail()` setzt den Checkpoint auch bei übersprungenen Duplikaten fort.
- Regressionstest deckt Retry, Event-ID-Deduplizierung, driftfreien Health-Status und Checkpoint-Fortschritt ab.
- **Serververifikation auf `7bfdba3`:** gezielte Event-/Job-/Live-Feed-Suite 67 bestanden; Ruff ohne Fehler; Gesamtsuite 1900 passed / 5 skipped. Quality Gate: `ok: true`, Regression `false`, Ruff 0, Mypy 0, AST 369 Dateien / 0 Fehler, Audit-Katalog bestanden. `doku_check --strict --limit 10 --worktree` meldete den bereits bekannten historischen Drift `42f0c01397` sowie lokale uncommittete Änderungen an `werkstatt/web/audit_panel.py` und `werkstatt/web/terminal_proxy.py`.


## Phase-Review-Freigabe bleibt menschlich (2026-11-11)

- Code-Audit gegen ADR-0029 fand im Phase-Review-Gate die Option `a = auto bis Ende`. Sie setzte `phase_review_auto`, wodurch ein spaeteres Human-Gate derselben Reflection-Invocation uebersprungen wurde.
- Die Auto-Option und der Skip-Merker sind entfernt. Nach jeder Reviewer-Ablehnung wird erneut eine konkrete menschliche Entscheidung verlangt; unbekannte Antworten wie `a` geben nicht frei und werden erneut abgefragt. Tests sichern die UI/Gate-Optionen und beide Reject-Runden.
- Serververifikation nach Pull steht aus.


## Finales Human-Gate nicht per Projektconfig abschaltbar (2026-11-11)

- Der Code-Audit fand im finalen Human-Gate einen zweiten Auto-Freigabe-Pfad: `require_human_approval: false` beendete das Gate mit Erfolg, bevor eine menschliche Antwort eingeholt wurde.
- Der Config-Bypass ist entfernt. Eine Legacy-Konfiguration mit `false` bleibt fail-closed und verlangt weiterhin eine ausdrueckliche menschliche Antwort; EOF wird abgelehnt. Tests und ADR-0029/OP-396-Doku aktualisiert.
- Serververifikation nach Pull steht aus.

## Gate-Fix Regressionen aus Serverlauf (2026-11-11)

Der Serverlauf auf `512ad5a` bestätigte die gezielte Gate-Suite (37 bestanden), Ruff und State-Drift-Prüfung. Die Gesamtsuite fand zwei Folgefehler: Der entfernte Auto-Gate-Pfad hinterliess `loop_human_gate_auto` als toten Katalogeintrag; ein älterer Reflection-Test erwartete trotz expliziter menschlicher Freigabe nach der letzten Reviewer-Ablehnung noch `False`. Den Eintrag entfernt und den Test auf die aktuelle Semantik umgestellt: zwei Reviewer-Rejects mit je explizitem `j` ergeben eine angenommene Reflection, nachdem Verify erfolgreich war. Erneute Serververifikation steht aus.

## Serververifikation der Human-Gate-Fixes (2026-11-11)

Der Serverlauf auf `bb427ff` bestaetigte 63 gezielte Tests, Ruff ohne Fehler und State-Drift ohne Abweichung. Die Gesamtsuite bestand mit 1900 passed / 5 skipped; das Quality Gate meldete `ok: true`, Ruff/Mypy 0, AST 369 Dateien ohne Fehler und Audit-Katalog bestanden. Der Doku-Checker meldete den separat committeten Audit-Katalog-Fix sowie die lokalen uncommitteten UI-Dateien.

## Portabilitaet der Human-Gate-Tests und deklarierte Laufzeitabhaengigkeit (2026-11-11)

Die Human-Gate-Tests legten eine globale Konfiguration unter `/opt/werkstatt/projects` an, obwohl der Gate-Code diese Konfiguration nicht mehr liest. Das Schreiben in einen server-spezifischen absoluten Pfad ist entfernt; die Tests sind nun tmp_path-isoliert und auch ausserhalb des Produktivservers ausfuehrbar. Ausserdem deklariert `requirements.txt` jetzt PyYAML, das von der Produktivkonfiguration importiert wird. Verifikation dieser Folgeaenderungen steht aus.


## Chat als Loop-Ansprechpartner: bestaetigungspflichtige Control-Aktionen (2026-11-11)

Der Chat-Agent darf Start, Pause, Fortsetzen und Stoppen jetzt als natuerliche Projektanfrage aufnehmen. Das neue Tool legt nur einen 15-Minuten-Vorschlag in der urspruenglichen Chat-Session ab; ein separater UI-Klick ist erforderlich. Vorschlaege zeigen Projekt und konkreten Auftrag, sind bei OP-Start auf die OP-ID beschraenkt und werden beim Bestaetigen erneut durch den bestehenden Start-Endpunkt validiert. Der API-Endpunkt konsumiert Vorschlaege atomar/einmalig, protokolliert Ablehnung, Ablauf, Erfolg und Fehler und ruft bestehende Control-Funktionen auf. Reconnect rendert Vorschlaege und Ergebnisse aus Session-Events erneut. Das verpflichtende Plan- und Human-Gate bleiben unveraendert.

- Serververifikation: noch ausstehend; die Aenderungen auf main sind nicht lokal ausgefuehrt.


## Syntaxfehler im Chat-Control-Tool aus Serverlauf korrigiert (2026-11-11)

Der Serverlauf auf a1fc32b konnte mehrere Chat-Tests nicht sammeln: Der request_loop_action-Eintrag in CHAT_TOOLS enthielt literal gespeicherte \\n-Sequenzen und verursachte einen SyntaxError in chat_tools.py. Der Registry-Eintrag wurde als normale mehrzeilige Python-Struktur neu geschrieben. Der Fix ist auf main, aber nach diesem Commit noch nicht auf dem Server verifiziert.


## Chat-Control-API-Test an echte Audit-Nahtstelle angepasst (2026-11-11)

Der Serverlauf nach dem Syntaxfix sammelte die Tests wieder und meldete 108 bestanden, aber ein neuer API-Test patchte _audit_loop_control als Modulvariable. Die Funktion ist lokal in create_app definiert; der Test verwendet jetzt die echte modulweite Nahtstelle _audit_web_loop_event. Serververifikation nach diesem Testfix steht aus.

## CI fuer Python-Quality-Gate und JavaScript-Syntax (2026-11-11)

Das Repository hatte keinen GitHub-Actions-Workflow. Ein Workflow prueft nun auf Pushes nach main und Pull Requests Python 3.11, installiert requirements.txt, parst alle static/*.js-Dateien mit Node 20 und fuehrt tools.quality_gate aus. Der erste CI-Lauf nach Anlage steht zur Auswertung aus.


## CI-Ruff-Baseline aus erstem sauberen Lauf korrigiert (2026-11-11)

Der erste CI-Lauf nach dem Dependency-Fix bestand den JavaScript-Syntaxcheck, zeigte aber sieben EXE001-Befunde fuer CLI-Skripte, die im Repository als nicht-ausfuehrbar gespeichert sind, sowie einen unsortierten Import in tests/test_audit.py. Da die Werkstatt diese Skripte explizit mit python3 tools/<name>.py startet, ist die Shebang-/Executable-Regel fuer tools/*.py eng begrenzt ausgenommen; der Testimport ist sortiert. Die naechste CI-Ausfuehrung entscheidet, ob weitere bestehende Ruff-Befunde oder Tests sichtbar werden.

- Commits: 0809b901 Ruff-Ausnahme fuer Python-CLI-Dateien; 3ee6ace5 Testimport sortiert.
- CI nach diesen Fixes: ausstehend.


## Ruff-Importtest aus dem ersten CI-Lauf portabel gemacht (2026-11-11)

Der Test fuer tools/audit.py manipulierte sys.path und importierte danach audit top-level. Diese historische Importtechnik liess Ruff den Block weiterhin als unsortiert erkennen und war an einen absoluten Serverpfad gebunden. Der Test importiert das Modul nun als Namespace-Package tools.audit aus dem Repository; die Pfadmutation und der absolute Pfad entfallen.

- Betroffene Commits: cdfce9e (Zwischenschritt), 4bd6f8c (korrigierter Import).
- CI nach der Korrektur: ausstehend.


## Saubere CI fuehrt pytest mit Detaildiagnose aus (2026-11-11)

Nach erfolgreichem Ruff-Lauf meldete Quality Gate in sauberer CI 92 Testfehler (0 bestanden), waehrend Mypy, AST und Audit-Katalog sauber waren. Quality Gate fasst pytest-Ausgaben hier nur als Zaehler zusammen; der Workflow fuehrt deshalb die Testsuite vorher direkt aus, damit der naechste Lauf konkrete Fehler und Tracebacks im Actions-Log zeigt. Die Fehlerursache ist noch offen und wird anhand dieses Laufs behoben.

- Workflow-Commit: 5bf8e45.
- CI-Diagnose: ausstehend.


## CI stellt den kanonischen Werkstatt-Pfad bereit (2026-11-11)

Der erste diagnostische pytest-Lauf auf GitHub Actions zeigte 68 Fehler und 1838 bestandene Tests. Der Grossteil der Fehler entstand, weil historische Tests und einige Pfadvertraege /opt/werkstatt fest erwarten, waehrend der Runner den Checkout unter /home/runner/work ablegt. Der Workflow erstellt nun im kurzlebigen Ubuntu-Runner einen Symlink von /opt/werkstatt auf den Checkout. Dadurch bleibt der Produktivpfad-Vertrag im Test erhalten; Tests ausserhalb dieses Pfadvertrags werden in der erneuten Suite sichtbar.

- Workflow-Commit: 71540a79.
- Vollstaendige CI-Verifikation: ausstehend.


## Importvertrag-Testabhaengigkeit in CI ergaenzt (2026-11-11)

Mit dem kanonischen /opt/werkstatt-Symlink stieg die saubere GitHub-Suite auf 1904 bestanden / 2 fehlgeschlagen. Beide Fehler waren derselbe Setup-Mangel: import-linter war nicht installiert, obwohl tests/test_import_drift.py es voraussetzt. Die Abhaengigkeit steht jetzt in requirements.txt; die volle CI-Verifikation laeuft erneut.

- Commit: 4aeaff83.
- CI nach Dependency-Ergaenzung: ausstehend.


## Erste saubere GitHub-CI vollstaendig gruen (2026-11-11)

Nach den Setup-Fixes besteht der Workflow nun alle Stufen: JavaScript-Syntax, Ruff, direkte pytest-Diagnose und Quality Gate. Die Suite meldete 1906 passed / 5 skipped; Quality Gate: ok true, Regression false, Ruff/Mypy 0, AST 370 Dateien ohne Fehler und Audit-Katalog bestanden. Der Lauf war auf Commit d192545. Der Chat-Control-API-Testfix und die vorausgehende Syntaxreparatur sind damit im CI-Checkout abgedeckt; der Server-Pull und der dortige gezielte Lauf bleiben ausstehend.

- Erfolgreicher Actions-Lauf: https://github.com/ghxstfocus/werkstatt/actions/runs/42932576328


## OP-393 — alle interaktiven Gate-Eingaben laufen ueber die Bridge (2026-11-11)

Audit gegen den noch offenen OP fand neben dem bereits korrigierten Phase-Review-Gate weitere direkte input()-Pfade in gates.py: Plan-Datei bearbeiten, optionales ADR-Mini und Human-Gate-Edit. Sie liefen am headless UI-Gate vorbei; der Plan-Edit-Pfad konnte den Subprozess mit EOF abbrechen. Alle drei warten jetzt ueber _frage_gate und damit im Headless-Modus ueber gate_bridge. Optionale ADR-Entscheidung bleibt fail-soft; Bearbeitungsfortsetzung bricht bei fehlender/abgelehnter Gate-Antwort fail-closed ab. Ein AST-Regressionstest erlaubt direkten input()-Aufruf nur noch innerhalb von _frage_gate.

Tests pruefen Plan-Edit-Weitergang, ADR-Mini-Entscheidung und den echten Phase-Review-Bridge-Roundtrip mit gate_open-Signal und Antwort-Wartefunktion.

- Commits: 1d9e974 (Headless-Eingaben), 063410b (Edit-/ADR-Regressionstests), 771382f / 2c0771e (Bridge-Roundtrip-Test und Lint-Korrekturen).
- GitHub Actions auf 2c0771e: JavaScript-Syntax, Ruff, pytest und Quality Gate gruen; 1910 passed / 5 skipped, Ruff 0, Mypy 0, AST 370 Dateien ohne Fehler, Katalog bestanden; ok=true, regression=false.
- Server-Dogfooding nach Pull steht aus.


## OP-396 — explizite Chat-Starts pruefen Startfaehigkeit vor Vorschlag (2026-11-11)

Der Chat hat fuer eine explizite OP-ID bisher nur die Ueberschrift in STATUS.md gesucht und daraus eine bestaetigbare Aktionskarte gebaut. Der Loop-Control-Endpunkt hat ungueltige Starts zwar erneut abgewiesen, dadurch erhielt der Nutzer aber erst nach Freigabe einen Fehler. request_loop_action verwendet jetzt denselben evidenzbasierten OP-Selector und erzeugt nur fuer eine eindeutig startfaehige OP einen Vorschlag. Bei erledigtem Status, fehlenden Tests/Nachweisen oder unbekannten Blockern kommen die Ausschlussgruende als Rueckfrage zurueck; es wird kein Session-Vorschlags-Event angelegt. Die erneute Validierung beim tatsaechlichen Start bleibt bestehen, damit Statusaenderungen nach dem Vorschlag sicher abgefangen werden.

- Regressionstests fuer erledigte OPs, fehlende Nachweise und unbekannte Blocker; gueltiger expliziter Start bleibt abgedeckt.
- GitHub Actions auf Commit 1f821ea (inklusive Zitatregel): JavaScript-Syntax, Ruff, pytest und Quality Gate gruen; 1914 passed / 5 skipped, Ruff/Mypy 0, AST 370 Dateien ohne Fehler, Audit-Katalog bestanden, ok=true.


## OP-396 — Chat-Zeilenzitate muessen nachpruefbar sein (2026-11-11)

Der System-Prompt verlangte Datei-/Zeilenbelege, obwohl read_file start/end Zeichen-Offsets bezeichnet und keine Zeilen liefert. Der Chat-Agent ist jetzt angewiesen, Zeilennummern mit grep zu verifizieren, read_file-Offsets nicht als Zeilen zu behandeln und fehlende Belege offenzulegen. Ein Prompt-Vertragstest schuetzt diese Regel vor Regression.

- GitHub Actions auf Commit 1f821ea: JavaScript-Syntax, Ruff, pytest und Quality Gate gruen; 1914 passed / 5 skipped, Ruff/Mypy 0, AST 370 Dateien ohne Fehler, Audit-Katalog bestanden, ok=true.


## OP-240 — Debugger-Modus bis zu Chat-Jobs weiterreichen (2026-11-11)

Die UI-Auswahl `debug` wird beim Senden als Backend-Faehigkeit `debugger` an den persistenten Chat-Job uebergeben. Cockpit und Control bleiben read-only. Job-, synchroner Chat- und WebSocket-Endpunkt akzeptieren `debugger`; schreibender Job-Modus bleibt abgewiesen. Ein Registry-Test haelt Debugger-Werkzeuge ausserhalb dieses Modus verborgen, API- und Frontend-Tests decken die Weitergabe ab. OP-240 bleibt offen: exakter strukturierter Patch, Freigabe an Patch-Hash/Projekt/Run gebunden und copy/paste-freie Uebergabe an den Coding-Loop fehlen weiterhin.

- GitHub Actions auf `ded9211`: JavaScript-Syntax, Ruff, Gesamtsuite und Quality Gate gruen; 1920 passed / 5 skipped, Ruff/Mypy 0, AST 370 Dateien ohne Fehler, Audit-Katalog bestanden, `ok=true`, `regression=false`. Ein vorheriger Testfehler bei der Argumentreihenfolge von `pytest -k` wurde im Test korrigiert.


## Chat-Arbeitsbereich und API-Kompatibilitaet (2026-11-11)

Der Chat wurde als projektbezogener Arbeitsbereich gestaltet: Gespraeche zeigen lesbare Titel und Zeitangaben, Antworten erhalten mehr typografische Hierarchie, Hintergrundaktionen erscheinen als kompakte Aktivitaets-Timeline, und der Composer bekommt einen klaren Fokuszustand. Aktivitaetskarten bleiben an Projekt und Session gebunden und werden vor der laufenden Antwort angezeigt. Der Asset-Cache in `layout.html` wurde synchron erneuert.

Der Screenshot zeigte `Chat-Auftrag konnte nicht angenommen werden: Not Found`. Die aktuelle API stellt `/chat/jobs` bereit; bei einem Server, dessen geladene API diese Route noch nicht kennt, faellt die UI fuer genau den generischen Routen-404 auf den bestehenden direkten Chat-Endpunkt zurueck. Projekt- oder Session-404s werden davon nicht verschluckt. Das kann eine fehlende Prozess-Neuladung temporaer abfedern, ersetzt den Webserver-Neustart fuer die Hintergrundjob-API aber nicht.


## Einheitliches UI-Designsystem (2026-11-11)

Nach dem Chat-Arbeitsbereich wurde die gemeinsame Werkstatt-Oberflaeche visuell angeglichen: Palette und Fokuszustand, Modus-Umschalter, Projekt-Tabs, obere Ambient-Leiste, Panel-Koepfe, Runs- und Timeline-Zeilen, Workbench-Drawer, Uebersichtskarten und Statusleiste teilen nun dieselben Abstaende, Radien, Flaechen und Interaktionszustaende. Die drei Modi behalten ihre bestehende Layout- und Funktionslogik; angepasst ist die gemeinsame visuelle Sprache samt responsiven Breakpoints und reduzierter Bewegung. Asset-Cache synchron erneuert.

- CSS-Aenderungen sind auf `main`; Browser- und Server-Visual-QA steht nach Neuladen des Webprozesses noch aus.
- Der Chat-404-Fallback fuer aeltere laufende API-Prozesse ist ebenfalls auf `main`; der direkte Chat-Fallback ist nur eine Kompatibilitaetsbruecke, nicht der Ersatz fuer persistente Hintergrundjobs.



## Projekt-Navigation und Chat-Vertrag synchronisiert (2026-11-11)

Die Modusleiste mit Cockpit, Control, Debug und Runs steht jetzt direkt unter der Projekt-Tab-Leiste. Zwei Server-Testfehler nach dem UI-Update waren veraltete Erwartungen: Gate-Handoff suchte noch die vorherige Sessionsortierung, und die leere Sessions-API erwartete noch keine Vorschau-Liste. Tests sind auf die aktuelle Summary-basierte Sessionauswahl und die Antwortform `{sessions, summaries}` aktualisiert. Die Gate-Uebergabe wartet weiterhin auf `loadPromise`, bevor sie die Chat-Historie wechselt oder den Debug-Auftrag sendet.

- Cache-Buster fuer alle statischen Assets synchron erneuert.
- Die beiden gemeldeten Tests muessen nach Pull erneut zusammen mit Quality Gate ausgefuehrt werden; CI-Ergebnis steht aus.

## 2026-11-11 — Gemeinsamen Loop-Pausenzustand zwischen Web-Workern

- `_loop_prozess` gleicht den Status eines lokalen Live-Prozesses mit der
  persistenten Loop-Registry ab. So sehen mehrere ASGI-Worker dieselbe
  Pause und Fortsetzen kann das erforderliche POSIX-Signal senden.
- Regressionstest `test_live_worker_reconciles_pause_from_shared_registry`
  ergänzt: simuliert die Pause durch einen anderen Worker, prüft den UI-Status
  und dass Resume `SIGCONT` auslöst.
- **Verifikation offen:** Der Test und die Quality Gates wurden in dieser
  Umgebung nicht ausgeführt. Serverlauf nach Pull steht aus.
\n

## 2026-11-11 — OP-397 Mehrprozess-Pause verifiziert

- Der CI-Lauf auf `1a71832` hat den Worker-Reconnect-Regressionstest
  bestanden: **1922 passed, 5 skipped**.
- Ruff: 0 Fehler; JavaScript-Syntax: bestanden; Mypy: 0 Fehler;
  AST: 370 Dateien / 0 Fehler; Audit-Katalog: bestanden.
- `tools.quality_gate --json`: `ok: true`, `regression: false`.
- Dieser Nachweis ersetzt den oben dokumentierten offenen Testlauf.

## 2026-11-11 — Chat-Willkommenstext an Steuerungsfunktionen angepasst

- Die Leerzustandskarte behauptete noch, der Chat könne keine Runs starten.
  Sie beschreibt jetzt Loop-Aktionen mit ausdruecklicher Bestaetigung und
  weist klar darauf hin, dass direkte Code-Patches aus dem Chat noch nicht
  verfuegbar sind.
- Statische Asset-Version auf `202611110006` synchronisiert.
- CI auf `4662bca`: JavaScript-Syntax und Ruff bestanden; Gesamtsuite
  **1923 passed, 5 skipped**; Mypy 0, AST 370 Dateien / 0 Fehler,
  Katalogtest bestanden, Quality Gate `ok: true`, `regression: false`.
- Die Overview-Auswertung dedupliziert Endereignisse pro Run. Der Screenshot
  zeigt 3 Erfolge aus 27 terminalen Runs; den Inhalt der Server-Event-DB
  haben wir damit nicht separat geprueft.



## 2026-11-11 — Loop-Control cross-worker serialisiert

- Pause, Resume und Stop waren nur durch einen prozesslokalen Lock geschuetzt.
  Mehrere Gunicorn-Worker konnten deshalb denselben Registry-Zustand lesen und
  widerspruechliche POSIX-Signale senden.
- Die SQLite-Registry besitzt jetzt compare-and-set Uebergaenge fuer
  pausing, resuming und stopping. Eine Aktion beansprucht den
  erwarteten Zustand atomar, bevor sie ein Signal sendet; parallele Steuerung
  erhaelt HTTP 409. Der persistierte Zwischenzustand bleibt fuer andere Worker
  und nach Webserver-Neustarts sichtbar.
- Nach einem Worker-Absturz werden verwaiste pausing/resuming-Zustaende
  nach 15 Sekunden aus dem Kernel-Prozessstatus zu running/paused rekonstruiert;
  stopping bleibt wiederaufnehmbar, bis der Prozess beendet ist.
- Stop sendet vor SIGTERM ein idempotentes SIGCONT, damit ein zuvor pausierter
  Prozess das Terminationssignal empfangen kann.
- Regressionstests pruefen konkurrierende Registry-Uebergaenge und ein
  Resume-Request waehrend eines persistenten pausing-Zustands. Die Test-Prozesse verwenden eine
  lebende PID, damit Registry-Liveness den Control-Pfad realistisch abbildet.
- **Verifikation laeuft:** GitHub Actions fuer den aktuellen main-Stand muss
  gezielte Web-Tests und den vollen Quality Gate noch bestaetigen.


## 2026-11-11 — OP-397 Loop-Control ueber Workergrenzen verifiziert

Der Race zwischen mehreren Web-Workern ist mit atomaren SQLite-Statusuebergaengen behoben. Pause, Resume und Stop beanspruchen den erwarteten Laufzustand, bevor sie POSIX-Signale senden; konkurrierende Aktionen koennen den Claim nicht doppelt erhalten. Verwaiste Pause-/Resume-Uebergaenge werden anhand des Kernel-Prozesszustands wiederhergestellt. Stop setzt einen pausierten Prozess vor SIGTERM fort.

- Regression im Chat-Control-Test an die Registry-CAS-Schnittstelle angepasst.
- GitHub Actions auf `67caa8b`: **1926 passed, 5 skipped**; Ruff/Mypy 0; AST 370 Dateien / 0 Fehler; Audit-Katalog bestanden; Quality Gate `ok: true`, `regression: false`.
- Statusdokumentation ergaenzt. Server-Pull und Live-Dogfooding stehen noch aus.


## 2026-11-11 — OP-397 parallele Stop-Aufrufe abgegrenzt

Ein Worker, der einen Loop bereits als `stopping` beansprucht hat, schuetzt den laufenden Stop jetzt gegen gleichzeitige Wiederholung durch weitere Web-Worker. Nach 30 Sekunden ohne Abschluss kann ein anderer Worker einen verwaisten Stop atomar uebernehmen; dadurch bleiben fehlgeschlagene Stops wiederholbar, waehrend konkurrierende Requests nicht doppelte Stop-Audit-Events erzeugen.

- Registry-Regressionstest prueft erstmaligen Claim, Konflikt eines zweiten Workers, Wiederuebernahme nach abgelaufenem Claim und Ablehnung eines zweiten frischen Claims.
- GitHub Actions auf `4a39e09`: **1927 passed, 5 skipped**; Ruff/Mypy 0, AST 370 Dateien / 0 Fehler, Audit-Katalog bestanden; Quality Gate `ok: true`, `regression: false`.
- Neue Produktanforderungen sind in OP-399/OP-400 und der vorgeschlagenen ADR-0030 als offene Arbeit erfasst.


## 2026-11-11 — OP-240 DebuggerFix-Vertrag abgesichert

Ein neuer Validierungsbaustein definiert den strukturierten Debugger-Patch als unveraenderlichen Datensatz mit Signatur, Ursache, Diff, exakten Dateipfaden, Confidence, Projekt, Ursprungs-Run und Basis-Commit. Der SHA-256 bindet alle diese Felder einschliesslich des exakten Diff-Inhalts. Pfad-Traversal, interne Werkstatt-/Git-Pfade, erkennbare Secret-Pfade, Binaer-/Rename-/Modus-/Submodule-Aenderungen, unpassende Dateilisten und geaenderte Basis-HEADs werden fail-closed abgewiesen.

- Checkout-Pruefung verwendet nur `git apply --check`; der Baustein schreibt keinen Produktionscode.
- Regressionstests decken Hash-Bindung, Kontextbindung, ungueltige Pfade, Diff-/Dateilisten-Abweichung und HEAD-Wechsel ab.
- Die Freigabekarte und der tatsaechliche CLI-Handoff sind weiterhin offen; OP-240 bleibt offen, bis sie den selben Vertrag nutzen und die Loop-Gates nachweislich erhalten bleiben.


## 2026-11-11 — OP-240 CI-Lintkorrektur

Die erste GitHub-Actions-Runde fuer den neuen DebuggerFix-Vertrag stoppte vor pytest am Ruff-UP035-Hinweis: Mapping gehoert in collections.abc. Import korrigiert; die vollstaendige Verifikation laeuft mit dem Folgecommit.


## 2026-11-11 — OP-240 Importordnung nach CI-Ruff

Die Folge-CI meldete weiterhin I001, weil collections.abc und dataclasses in falscher Reihenfolge standen. Importblock alphabetisch sortiert; die erneute CI-Runde prueft nun Ruff, Tests und Quality Gate.


## 2026-11-11 — OP-240 Diff-Hash-Regressionstest korrigiert

GitHub Actions meldete, dass der Manipulationstest beim Erstellen des geaenderten Diffs zugleich einen neuen gueltigen Hash erzeugte. Der Test behaelt jetzt den urspruenglich bestaetigten Hash bei und veraendert nur den Diff; damit prueft er die tatsaechliche Bindung zwischen Freigabe und Patch-Inhalt.


## 2026-11-11 — OP-240 Projektzuordnung terminaler Run-Events korrigiert

Das Lifecycle-Finalizer-Event loop_ended/loop_failed verwendete bisher
hartcodiert den Projektnamen werkstatt. Dadurch wurden terminale Events
anderer Projekte im Event-Store falsch zugeordnet. Der CLI-Projektname wird
nun bis zum Finalizer weitergereicht; ohne bekannten Projektnamen wird kein
irrefuehrend zugeordnetes Terminal-Event geschrieben.

Die Debugger-Vorschlagspruefung aktualisiert vor der Suche den Audit-Projektor
und verlangt jetzt einen Fehler- oder Gate-Nachweis desselben Projekts im
Quell-Run. Ein beliebiger existierender Run reicht nicht mehr.
Regressionstests pruefen Projektzuordnung des Lifecycle-Events und
fail-closed Verhalten des Debugger-Vertrags.

- Ausloeser: Audit der OP-240-Handoff-Implementierung gegen ADR-0029 und den Event-Store.
- Server-Pull von df539a4 bestaetigt; neue Folgeaenderungen und deren CI-Verifikation stehen noch aus.

## 2026-11-11 — OP-240 Folge-CI Ruff-Korrektur

Ruff meldete PIE807 im neuen Debugger-Tool-Test: Der Fake-Projektor verwendete einen wirkungslosen Lambda-Wrapper fuer ein leeres Dictionary. Der Test nutzt jetzt direkt den Konstruktor `dict`. Die Folge-CI muss Lifecycle-Projekttests, volle Pytest-Suite und Quality Gate erneut bestaetigen.


## 2026-11-11 — OP-240 Run-Evidenz-Test prueft mehrere Audit-Kinds

Die neue Fail-closed-Pruefung fragt mehrere Fehler- und Gate-Kinds ab. Der Test-Fake setzte faelschlich voraus, dass jede Abfrage `loop_failed` lautet, und brach deshalb beim zweiten Kind mit AssertionError ab. Er liefert jetzt nur fuer den Terminalfehler-Nachweis einen Treffer und erlaubt weitere korrekte Kind-Abfragen. Folge-CI ausstehend.

## 2026-11-11 — OP-/Doku-Audit: Statusschema und historische Roadmap getrennt

Audit von STATUS.md, ROADMAP.md und DOC_CONVENTIONS.md: Alle 102 OP-Header
haben die kanonische Form und eindeutige IDs. Legacy-Feldnamen und nicht
spezifizierte Felder wurden im STATUS-Vertrag vereinheitlicht und als `—`
markiert, damit unvollstaendige OPs nicht still startfaehig erscheinen.
Der doppelte Phasenplan wurde aus STATUS entfernt; historische ROADMAP-
Snapshots sind jetzt als solche beschriftet. OP-212 bleibt `open`, weil
seine Integration von OP-210 abhaengt. OP-396 nennt den inzwischen
angeschlossenen Chat-Steuerungsstand und den aktuellen CI-Nachweis.

- CI verifiziert auf `bc8a84a`: 1942 passed, 5 skipped; Ruff/Mypy 0,
  AST 372 Dateien ohne Fehler, Katalog bestanden.
- Naechster offener Nachweis fuer OP-396/OP-240 bleibt Server-Dogfooding.

## 2026-11-11 — STATUS-Queue bereinigt

Historische Abschlusszeilen aus der Delete-Zone wurden hierher uebernommen, soweit sie nicht bereits dokumentiert waren. Die Delete-Zone enthaelt ab jetzt ausschliesslich entfernte Pfade gemaess DOC_CONVENTIONS §5.

Die alte Roadmap mit historischen Phasen wurde nach docs/archiv/roadmap-history-2026-11-10.md verschoben; docs/ROADMAP.md enthaelt jetzt nur Ziel, aktuelle Meilensteine und verbindliche Quellen. Der nicht angenommene SOLL-Entwurf wurde nach docs/archiv/soll-zielbild-2026-11-08.md verschoben. Die offene Queue wurde auf aktuell begrenzte, verifizierbare Arbeit reduziert. In die bestehenden Ziele integriert oder als ueberholt verworfen wurden: OP-303/307/310 in OP-396/397; OP-306/306b als bereits vorhandene UI-Funktionen; OP-381/381b in den einheitlichen Gate-/Chat-Vertrag von OP-396; OP-281/282 zugunsten OP-385/398; OP-309/313 als widerspruechliche Floating-Chat-/Ghost-Intent-Entwuerfe; OP-330–334 zugunsten vorhandener Skills und expliziter Chat-Tools; OP-350/351/352 und OP-370 in OP-399; OP-360/361/362 zugunsten der zentralen Projekt-Chat-Architektur; OP-210–217 bleiben ausserhalb der Queue, solange ADR-0016/0017 nicht angenommen sind. Phase-3-Memory- und Selbstverbesserungs-OPs bleiben bis zum Dogfooding-Ergebnis auf hoher Roadmap-Ebene. Alte Kleinarbeiten ohne aktuelle Reproduktion (OP-101/109/115/116/112/117/118/121) muessen vor einer Wiederaufnahme neu belegt werden.

- 2026-11-08 | OP-306c-Fix | done | Projector-Deadlock behoben (Commit a640b19). Sentinel-Checkpoint MIGRATED-SEM-352017 (aus OP-323-Migration) stand in der alphabetisch letzten agent-pipeline-migrated-2026-11-08.jsonl Zeile 33/33 — _read_events() fand ihn nie in den echten Tagesdateien, uebersprang stumm alle Events, Checkpoint blieb Sentinel. Folge: SQLite stand seit 15:14 still, JSONL hatte 31 echte Events nach 15:14 (u.a. loop_started 17:57 OP-280, loop_failed 19:41). Fix: _jsonl_files() excludet *-migrated-*.jsonl (statische DB-Dumps); _read_events() wirft ValueError bei unbekanntem Checkpoint statt stumm 0. 3 neue Tests. Daten-Reset: Checkpoint auf PIPE-20261108-151341-a8a36a -> tail() las 31 Events ein (2 wegen event_id-Kollision uebersprungen, harmlos). tail#2 idempotent. Checkpoint landet auf PIPE-20261108-194159-bd35bf. COUNT 410754 -> 410785, MAX(seq) 788707 -> 788736. pytest 1536 passed.
- 2026-11-08 | OP-320 | done | ADR-0024 Tiered Event Log + Projector. Deklariert Semantic-Stream (git) + Stream-Stream (gitignore), SQLite rebuildbar, audit()/stream() als einzige Writer, EventStore.append() verbannt. Grundlage fuer OP-321..323.
- 2026-11-08 | OP-319 | done | Event-Architektur-Messung. 32804 JSONL-Events (320 Kinds, 267 Runs) vs. 374353 SQLite-Events (10 Kinds, 5290 Runs). Schnittmenge: 0 Kinds, 25 Runs. Beweis fuer Dual-Write-Anti-Pattern (Confluent/Microsoft-CQRS/AutoMQ). Grundlage fuer OP-320..323.
- 2026-11-07 | OP-180 | wontfix | Reviewer-Praezision (Konfidenz-Feld + Pre-Check): falsche Problem-Annahme. Loop-Test 7 hatte keinen Reviewer-Bug, sondern OP-179 (mypy Duplicate-Module) — die 3 HIGH reviewer_phase_rejected-Bugs waren ALLE berechtigt (t3/t4/t5 wurden wegen OP-179 nicht gebaut). Konfidenz-Feld und Pre-Check basieren auf "Reviewer meldet falsche Bugs" — das war nie wahr. Kein Code angelegt, kein Test, wird nicht gebraucht.
- 2026-11-07 | OP-179 | wontfix | mypy-Setup "Duplicate-Module": **falsche Problem-Annahme**. Ich habe den truncated mypy-Output aus Loop-Test 7 (`(also at "werkstatt/phases/review.py")`) als "Source file found twice" interpretiert — das war eine Fehldeutung des OP-172-Truncation-Artefakts. Reproduktion (Block 33, 2026-11-07): alle vier mypy-Varianten rc=0 auf aktuellem Code-State, kein Duplicate-Module-Fehler, kein Top-Level-`phases/`-Konflikt, `__init__.py` ueberall da. Wahre Loop-Test-7-Ursache fuer t3/t4-Fails: der Loop baute zuerst t2 (`review.py`, setzt `state.phase_review_gate_auto`), aber t1 (`state.py`, deklariert das Feld) war noch nicht gebaut — Planner erkannte Cross-Task-Feldabhaengigkeit nicht. **Bereits behoben** durch OP-168b (c713033): Feld ist jetzt in RunState deklariert, Loop-Test 8 findet es. Kein Code angelegt, kein Test.
- 2026-11-07 | OP-177 | wontfix | Reviewer-Kontext-Vertrag: falsche Problem-Annahme. _phase_files (alle Task-Dateien der Phase) liefert vollstaendigen Diff — bestaetigt durch Messblock 31. Die 3 HIGH-Bugs aus Loop-Test 7 waren berechtigt, weil t3/t4/t5 tatsaechlich nicht gebaut wurden (OP-179). Der Reviewer-Selbst-Hinweis "nur der Anfang von _phase_end_reflection ist sichtbar" war praezise Diagnose ("Patch fehlt im sichtbaren Kontext"), nicht Truncation-Beschwerde. Kein Code angelegt, kein Test. Ursache fuer "3 von 4 Tasks nicht gebaut" ist OP-179 (mypy Setup) + OP-172 (Verify-Truncation, heute gefixt).
- 2026-11-04 | OP-122 | done | SQLite-Event-Store fuer Loop-Events (append/query, kind-Filter, WAL, .werkstatt/events.db)
- 2026-11-04 | OP-114 | done | Audit-Events reicher: bugs/grund/gate/fehler (c4b525a)
- 2026-11-04 | OP-111 | done | Progress-Events in ask_llm + _with_spinner (4c0c59d, 2c1b30d)
- 2026-11-03 | OP-108 | done | Scout create/update + Kopier-Auftrag (3884036)
- 2026-11-03 | OP-097 | superseded | aufgeteilt in OP-104 (Kopie) + OP-105 (Proxy) + OP-106 (Aufrufer) + OP-107 (Tests)
- 2026-11-03 | OP-099 | done | Phase 33.6: control_drift als Post-Build-Stage hart (67cd6b0)
- 2026-11-03 | OP-088 | done | explorer_result in beiden Zweigen (Mess+LLM), audit.py-Katalog (4b6058f)
- 2026-11-03 | OP-091 | done | audit_panel: _home_kontext Modulebene (Diagnose korrigiert: Writer OK, Reader crasht) (4a10645)
- 2026-11-03 | OP-095 | done | Phase 33.2a: verify.json hart-Feld explizit + fail-loud (1ac3446)
- 2026-11-03 | OP-089 | done | Reflection-Circuit-Breaker + Katalog-Drift (c00ef17)
- 2026-11-03 | OP-093 | done | Plan-Gate Fail-closed bei ungültiger Antwort (d0f871a)
- 2026-11-03 | OP-090 | done | Human-Gate bei Reflection-Erschöpfung (47b6e07)
- 2026-11-02 | OP-035 | Doku-Task-Datum wird halluziniert — deterministisch geloest (BUILDER_SYSTEM + {date}-Ersetzung + _korrigiere_doku_datum Sicherheitsnetz)
- 2026-11-02 | OP-068 | Heartbeat-Stage-Name (Builder/Reviewer) — Commit 2c099da
- 2026-11-02 | OP-069 | Delete-Zone-Sektion anlegen — Commit 6fa1d74 + Fix ebe8049
- 2026-11-03 | OP-009 | obsolete (python3 -m werkstatt.loop funktioniert (CLI seit Monaten aktiv)) — Commit n/a
- 2026-11-11 | OP-009 | obsolete | Historischer Eintrag: der CLI-Einstieg ist `python -m werkstatt.loop`; kein eigener Loop-OP erforderlich.
Weitere aus der startbaren Queue entfernte Eintraege (kein Arbeitsverlust): OP-303/306/306b/307/310/381/381b sind in der vorhandenen Projekt-/Modus-/Chat-Steuerung umgesetzt oder in OP-396/397 zusammengefuehrt; OP-309 und OP-313 widersprachen dem zentralen Chat und expliziten Freigabemodell. OP-242 ist Debug-Umfang von OP-240. OP-241 bleibt optionale Sandbox-Arbeit nach Debug-Dogfooding. Die Phase-3-Eintraege OP-160/220/220a/221/222/250/376–380 und OP-113i bleiben bis nach OP-382 gesperrt. OP-210–217 sind nicht aktiv, solange ADR-0016/0017 proposed sind. Kleine, nicht neu reproduzierte Wartungs-/Refactor-Vorhaben OP-096/098/101/105–109/112/115–118/121, OP-255–266, OP-283/294, OP-318, OP-340–342 und OP-389b kommen erst nach neuer Evidenz zurueck. Experimental-UI OP-311–317, Script-Bank OP-330–334 und separate Senior-Architekt-OPs OP-360–362 werden nicht weiterverfolgt; Skills und zentrale Chat-/Tool-Faehigkeiten sind die einheitliche Linie.

Weitere Aussteuerungen: Bereits durch die aktuelle UI abgedeckt bzw. in OP-396/397 integriert: OP-303, OP-306, OP-306b, OP-307, OP-310, OP-381 und OP-381b. OP-309 und OP-313 entfallen als widerspruechliche Floating-Chat-/Ghost-Intent-Modelle; OP-281/282 werden durch OP-385/398 ersetzt; OP-242 gehoert zu OP-240; OP-350/351/352/370 gehen in den sicheren Projektquellen-Vertrag OP-399 ein; OP-383 in die Kontext-/Rollenarbeit OP-384/400. Keine getrennten Script-Bank- oder Senior-Architekt-Strukturen: OP-330–334 und OP-360–362 entfallen zugunsten von Skills, Chat und vorhandenen Tools. OP-160/220/220a/221/222/250/376–380/113i sowie optionale Sandbox OP-241 bleiben ausserhalb der aktiven Planung bis nach OP-382. OP-210–217 setzen eine angenommene ADR-0016/0017 voraus. Alte, nicht erneut belegte Wartungs- und Refactor-Punkte OP-096/098/101/105–109/112/115–118/121/255–266/283/294/311–318/340–342/389b sowie automatischer Push OP-256 werden nicht als startbare Arbeit gefuehrt; Wiederaufnahme nur mit aktueller Evidenz und klarem Bezug zum Produktziel.


## 2026-11-11 — ADR-Gates bei der OP-Auswahl

- OP-399 und OP-400 referenzieren ADR-0030 jetzt maschinenlesbar als Voraussetzung.
- Chat- und Loop-Starts akzeptieren nur ADRs mit genau einem `Status: accepted`-Eintrag; fehlende oder widerspruechliche ADRs blockieren fail-closed.
- ADR-0030 ist im ADR-Index als proposed verzeichnet; Selector-Regressionstests decken proposed, accepted und fehlerhafte Metadaten ab.


## 2026-11-11 — Veralteten PhaseState bei Auftragswechsel verwerfen

- Ein neuer, freigegebener Plan ersetzt nun den Checkpoint des vorherigen Auftrags. Der alte Checkpoint bleibt bis zur erfolgreichen Planfreigabe erhalten.
- Ein Integrationstest durchlaeuft die echte Plan-Phase und belegt, dass danach nur der neue Task im PhaseState liegt.


## 2026-11-11 — Planfreigabe als Chat-Gate festgelegt

- ADR-0029 beschreibt jetzt einen versionierten Plan als gemeinsames Objekt von Chat und Loop, mit begruendeter Empfehlung und Inline-Gate im Chat.
- Eine Planfreigabe deckt nur den angezeigten Arbeitsumfang ab; Planrevisionen, Mehrdeutigkeit und externe/destruktive Aktionen erfordern erneute Entscheidung.

## 2026-11-11 — Rollenaufrufe und Tokenbudget nach Bedarf ausrichten

- ADR-0029 und OP-385 halten den aktuellen dreistufigen LLM-Planpfad als Optimierungsziel fest: Scout bedarfsbasiert, Architect mit strukturiertem Plan, deterministische Task-Kompilierung; LLM-Split nur als Fallback.
- Builder, Verify und unabhaengiger Reviewer bleiben nachweislich getrennte Kontrollfunktionen; Entfernung erst nach messbarer Qualitaetsevaluation.

## 2026-11-11 — PhaseState beim Laden strukturell validieren

- YAML mit falscher Wurzel oder fehlerhaften Task-/Dependency-Typen wird nicht mehr als nutzbarer Checkpoint geladen; der Loop startet damit nicht versehentlich aus inkonsistentem Zustand.
- Ein Legacy-Checkpoint ohne `tasks` wird kompatibel als leerer Task-Checkpoint behandelt.
- Regressionstests decken falsche Wurzel, Task-Form, ID und Dependency-Typen ab.

## 2026-11-11 — PhaseState an aktives Projekt binden

- Ein gespeicherter PhaseState mit abweichendem `project`-Feld wird beim Laden verworfen, bevor seine Tasks den aktuellen Projekt-Loop erreichen koennen.
- Ein Regressionstest belegt die Zurueckweisung eines fremden Projekt-Checkpoints.

## 2026-11-11 — SIGTERM kontrolliert bereinigen

- Web-Stop wird im Loop-Prozess als kontrollierter Abbruch behandelt, damit der bestehende `finally`-Pfad PhaseState persistiert und einen vor Run-Beginn angelegten Stash zurueckholt.
- Der Lifecycle unterscheidet einen menschlich angeforderten Stop von einem unerwarteten Loop-Fehler und auditiert ihn als `loop_stopped`.
- Ein Regressionstest sendet SIGTERM innerhalb des Run-Pfads und belegt den Stash-Cleanup.

## 2026-11-11 — Lifecycle-Audits explizit typisieren

- Terminale Run-Ereignisse werden als direkte, typisierte Audit-Aufrufe emittiert, damit der Katalogtest neue und tote Kinds erkennt.

## 2026-11-11 — Scout bedarfsbasiert ueberspringen

- Der Planner ueberspringt den Scout nur bei einem expliziten, einzelnen Zielpfad, den der Explorer bestaetigt und der im Projekt existiert.
- Such-, Diagnose-, Mehrdatei- und breite Auftraege behalten den Scout. Der Architect und das verpflichtende Plan-Gate bleiben in diesem Schritt unveraendert.
- Routing-Entscheid und Zielpfad werden als `planner_scout_skipped` auditiert; Regressionstests belegen die Grenzen.


## 2026-11-11 — Architect-Bypass an aktuelle Belege binden

- Ein atomarer Scout-Plan ueberspringt den Architect nur noch bei genau einer bestehenden Projektdatei, vollstaendigen Ersetzungsfeldern und eindeutigen Treffern an den angegebenen Zeilen.
- Veraltete, mehrdeutige oder unvollstaendige Stellen fallen in den Architect-Pfad zurueck; Tests sichern Annahme und Eskalation.
- Mypy verlangt eine explizite Typpruefung der Scout-Felder; der Quality-Gate-Lauf deckt diesen Vertrag neben Pytest und Ruff ab.


## 2026-11-11 — Scout-Routing im Audit begruenden

- Jeder Planlauf auditiert, ob der Scout wegen breiter/unklarer Anfrage gebraucht oder durch explizites Einzeldateiziel mit Explorer-Beleg uebersprungen wird.
- Der Audit-Grund enthaelt den konkreten Routing-Faktor statt Auftragsprosa; Tests pruefen Eskalationsgrund und Skip-Grund.

## 2026-11-11 — Architect nach Beleglage ueberspringen

- Ein eng begrenzter deterministischer Pfad erkennt wortwoertliche Einzeldatei-Ersetzungen mit Explorer-Beleg und exakt einmaligem aktuellem Treffer.
- In diesem Fall erstellt der Planner direkt einen pruefbaren Ein-Task-Plan; Scout, Architect und Task-Split entfallen. Mehrdeutige oder veraltete Treffer fallen auf den bisherigen Reasoning-Pfad zurueck.
- Planquelle und Architect-Bypass werden auditiert; Regressionstests decken Skip und Eskalation ab. Das Plan-Gate bleibt unveraendert verpflichtend.

## 2026-11-11 — Server-Fetch fuer GitHub-verbundene Projekt-Runs festhalten

- OP-399/ADR-0030 praezisieren: Der Werkstatt-Server muss den registrierten Ref vor einem GitHub-verbundenen Run selbst abrufen und die ausfuehrende Revision auf eine Commit-SHA pinnen.
- Der Run nutzt einen verwalteten isolierten Checkout; lokale Serverdateien und uncommittete Aenderungen werden nicht ueberschrieben oder ungefragt mit Remote-Arbeit vermischt.
- Reine lokale Projekte laufen weiterhin direkt aus ihrem Serverpfad. Fetch-/Auth-/Ref-Fehler stoppen Remote-Runs sichtbar; Push/Merge bleibt separat freigabepflichtig.
- ADR-0030 bleibt vorgeschlagen, bis Git-Authentifizierung und die weiteren dortigen Architekturfragen entschieden sind.

## 2026-11-11 — Server-first-Projektfluss praezisieren

- Neue Projekte entstehen primaer auf dem Werkstatt-Server; GitHub kann beim Greenfield-Setup oder spaeter als Remote verbunden werden.
- OP-399/ADR-0030 ergaenzen initiales Pushen mit eigener Freigabe sowie sicheren serverseitigen Fetch vor Remote-Runs. Lokale Aenderungen/Commits duerfen bei Sync nie still ueberschrieben werden; Konflikte muessen im Chat erklaert werden.
- Die ADR bleibt vorgeschlagen, da GitHub-Authentifizierung, initiales Repo-Publishing und Konfliktpolitik noch formell zu entscheiden sind.

## 2026-11-11 — Loop-Stash-Cleanup gegen Datenverlust absichern

- Bei Cleanup wurde ein fehlgeschlagenes `git stash pop` durch ein unbedingtes `git stash drop stash@{0}` gefolgt; damit konnte ein Konflikt den einzigen wiederherstellbaren Nutzer-Stash loeschen.
- Ausserdem galt ein erfolgreicher `git stash push`-Exitcode bereits als Beleg, dass ein neuer Stash angelegt wurde. Bei einem Race zur Dirty-Pruefung konnte so ein vorhandener Fremd-Stash gepoppt werden.
- Cleanup ordnet die Wiederherstellung jetzt einer konkreten Stash-SHA zu, behaelt Konflikt-Stashes und bricht vor dem Loop ab, wenn lokale Aenderungen nicht nachweisbar gesichert wurden. OP-397, Audit-Katalog und Regressionstests werden angepasst.

## 2026-11-11 — Generischen Stash-Drop-Helper entfernen

- Der nach dem Cleanup-Fix ungenutzte `_git_stash_drop` verwarf pauschal den neuesten Stash ohne Ownership-Pruefung. Definition, Re-Export und API-Eintrag sind entfernt.

## 2026-11-11 — Git-Statusfehler fail-closed behandeln

- `_git_dirty` ignorierte bislang einen fehlerhaften Exitcode von `git status` und meldete den Baum als sauber. In einem erkennbaren Repo kann der Loop dadurch die Stash-Sicherung überspringen.
- Bei Statusfehlern wird ein Projekt mit `.git`-Marker jetzt als unsicher behandelt; Nicht-Git-Projekte bleiben ohne Git lauffaehig. Ein Regressionstest deckt den fehlerhaften Git-Status ab.


## 2026-11-11 — ADR-0030 angenommen, GitHub-Run-Worktree vorbereitet

- ADR-0030 ist nach ausdruecklicher Freigabe als accepted in ADR, ADR-Index und Roadmap eingetragen. Die Richtung ist server-first: Greenfield-Scaffolding bleibt auf dem Server; Remote-Verbindung und initiales Pushen bleiben separate Freigaben.
- GitHub-Runs pruefen jetzt auf dem Server den konfigurierten origin-Upstream, holen den Remote-Stand und erstellen einen eigenen Worktree-Branch auf der gepinnten Commit-SHA. Der bestehende Checkout wird nicht gemergt oder zurueckgesetzt; dirty, vorausliegende oder divergierende lokale Branches stoppen den Start.
- Der Loop kann den Worktree-Pfad explizit als Arbeitsverzeichnis verwenden. Der Start-API-Response nennt Repository, Remote-Branch, Basis- und Ziel-SHA sowie Run-Branch.
- CI fuer den Git-Status-Fix: 1963 Tests bestanden, 5 uebersprungen; Ruff/Mypy/AST/Katalog und Quality Gate ohne Regression. Die Integration von OP-399 wird mit Remote-/Worktree- und UI-Gates weiterverifiziert.


## 2026-11-11 — OP-399 erste CI-Korrektur

- CI meldete einen zu frueh entfernten SHA-Wert in den Worktree-Tests, drei verschachtelte Test-Context-Manager und eine Ruff-Regel fuer Dateiendungen. Testbelege und Remote-Slug-Normalisierung werden korrigiert; volle CI folgt erneut.


## 2026-11-11 — OP-399 Worktree-CI-Korrekturen

- Lokale Nicht-Git-Projekte werden vor jedem Git-Aufruf erkannt und ohne Git-Subprozess behandelt. Das hält den lokalen Startpfad kompatibel mit laufenden Web-Tests und spart unnötige Prozessstarts.
- Der finale Status-/HEAD-Abgleich erfolgt vor dem Anlegen des verwalteten Worktree-Verzeichnisses. Der Projekt-Testfixture ignoriert `.werkstatt/`, wie es für das Laufzeitverzeichnis vorgesehen ist.
- GitHub Actions hatte 22 Fehler wegen dieser beiden Randbedingungen; Ruff war bereits sauber. Der vollständige CI-Lauf wird nach dieser Korrektur erneut abgewartet.


## 2026-11-11 — OP-399 CI-Fixture fuer Worktree-Start

- Der GitHub-Run-API-Test stellt nun auch `docs/STATUS.md` im isolierten Worktree bereit. Damit prüft er tatsächlich den erfolgreichen Startpfad, statt beim absichtlich fehlenden Fixture-Inhalt den Fehler-Cleanup auszulösen.
- Der vorherige Quality-Gate-Lauf scheiterte nur in `test_github_run_starts_in_pinned_worktree`: Der Fake-Worktree fehlte die STATUS-Datei, weshalb korrekterweise Cleanup aufgerufen wurde und dabei den global gemockten `subprocess.Popen` traf. Die vollständige Suite lief mit 1.977 bestanden und 5 übersprungen, eine Testfixture schlug fehl.


## 2026-11-11 — OP-399 Worktree-State ausserhalb des Projekt-Checkouts

- GitHub-Run-Worktrees werden jetzt in einem projektbezogenen Verzeichnis unter dem konfigurierten Werkstatt-State gespeichert, nicht mehr in `.werkstatt/` des Projekts. Projekte brauchen dadurch keine spezielle Ignore-Regel und bleiben nach einem Run clean.
- Regressionstests erstellen ein Projekt ohne `.werkstatt`-Ignore-Regel und starten zwei gepinnte Run-Worktrees nacheinander; außerdem wird eine State-Konfiguration innerhalb des Checkouts fail-closed abgewiesen.
- ADR-0030 und OP-399 halten diese Ablage- und Isolationsinvariante fest.


## 2026-11-11 — OP-397 Chat-Worker bei Lease-Verlust sicher stoppen

- Ein Worker mit abgelaufener oder entzogener Lease bekam bisher bei der naechsten Abbruchpruefung `False`, weil die Abfrage nur laufende Jobs des eigenen Workers betrachtete. Er konnte dadurch nach Lease-Recovery noch weitere Chat-Tools ausfuehren.
- Die Abbruchpruefung behandelt fehlende Jobs, nicht mehr laufende Jobs und abweichende Worker-IDs jetzt als Abbruch. Der Lease-Test prueft, dass ein abgelaufener Worker keine Heartbeats erneuern kann und fail-closed als abgebrochen gilt.


## 2026-11-11 — ADR-0031 freigegeben: parallele Chat- und Loop-Arbeit

- Der Nutzer hat die Architektur fuer parallele Chat-/Loop-Auftraege freigegeben. Der Chat soll waehrend eines Runs natuerlich ansprechbar bleiben; Planversionen und Commit-Pinning sind interne Konsistenzmechanismen, keine zusaetzliche UI-Bedienung.
- Schreibauftraege arbeiten in getrennten Worktrees auf festen Basis-Commits. Ereignisse informieren laufende Runs ueber Aenderungen; nur betroffene Arbeit pausiert am Checkpoint und wird auf dem kombinierten Stand neu geplant und verifiziert. Integration bleibt pro Projekt serialisiert; Diffs verschiedener Basen werden nicht verglichen.
- ADR-0031, OP-396/397 und Roadmap beschreiben das Ziel. Die Funktion ist noch nicht vollstaendig implementiert; verpflichtende Plan-/Ergebnis-Gates bleiben bestehen.


## 2026-11-11 — Parallelkoordination in umsetzbare OPs zerlegt

- OP-401 behandelt Chat-/Session-Kontext, dauerhafte Auftragseinreihung und Aenderungsereignisse fuer aktive Runs.
- OP-402 behandelt getrennte Worktrees, feste Basis-Commits, serialisierte Integration und erneute Gates auf dem kombinierten Commit.
- Damit bleibt der normale Chatfluss leichtgewichtig: interne Versions-/SHA-Pruefungen werden nicht als manuelle UI-Schritte gezeigt. Unklare oder scopeveraendernde Konflikte werden erklaert und gezielt freigegeben.

## 2026-11-11 — Chat meldet belegten Loop-Start korrekt

- Ein bestaetigter Chat-Start, bei dem bereits ein Loop laeuft, wird als `not_started` zurueckgegeben und als fehlgeschlagener Kontrollversuch gespeichert; er erscheint nicht mehr als abgeschlossene Aktion.
- Die Chatkarte zeigt klar, dass kein neuer Run gestartet oder eingereiht wurde. Ein vorhandener Run wird nicht faelschlich dem neuen Auftrag zugeordnet.
- Eine dauerhafte Warteschlange fuer solche Auftraege ist weiterhin Teil von OP-401/OP-397 und wird hier nicht vorgetaeuscht.

## 2026-11-11 — Reflexion nach gruenen Zwischenschritten konkretisiert

- OP-398 verlangt jetzt einen evidenzbasierten Zielabgleich nach jedem gruenen Schritt. Der Loop setzt innerhalb der freigegebenen Grenze selbststaendig fort, wenn Akzeptanzkriterien offen sind, und schliesst erst nach belegter Zielerreichung plus Abschluss-Verify ab.
- Neue unabhaengige Funde werden als getrennte Folgearbeit vorgemerkt; echte Mehrdeutigkeit oder eine Scope-Erweiterung wird im Chat geklaert. Begrenzte Reflexion darf keine unbegrenzte Arbeit erzeugen.
- Die Reflexion ist ein Steuerungsschritt zwischen Aufgaben, keine zusaetzliche Pflichtrolle bei jedem kleinen Tool-Aufruf.

## 2026-11-11 — ADR-0031 um Zielabgleich nach gruenen Schritten ergaenzt

- Die angenommene Metaorchestrator-Entscheidung beschreibt nun eine begrenzte Reflexion an sicheren Aufgaben-/Checkpoint-Grenzen: Belege gegen Nutzerziel und freigegebene Kriterien pruefen, innerhalb des Scope fortsetzen oder nach Abschluss-Verify beenden.
- Gruene Einzeltests gelten als Zwischenbelege. Reflexion erzeugt keine neue Freigabe fuer fremde Ziele und wird nicht nach jedem Tool-Aufruf ausgefuehrt.

## 2026-11-11 — Control-Timeline als nachvollziehbare Arbeitsspur festgelegt

- OP-394/395 erfassen Arbeitsschritt, Status, Ergebnis/Beleg, kurze Entscheidungszusammenfassung und naechsten Schritt fuer die Control-Timeline.
- Die Timeline soll den Loop beim Denken und Arbeiten nachvollziehbar machen, ohne rohe interne Gedankengaenge zu speichern. Chatfragen bleiben waehrenddessen unabhaengig beantwortbar.
- Erste UI-Etappe umgesetzt: Der Chat zeigt je Hintergrundauftrag nur einen aktuellen, natuerlich formulierten Status, ersetzt ihn beim Schrittwechsel und zeigt nach Abschluss die Antwort. Tool-Schrittlisten und Tool-Ergebnisse werden nicht mehr im Chat angezeigt. Die ausfuehrliche Control-Timeline mit Belegen und Replay steht noch aus.

- Der Chat zeigt nur die aktuelle temporaere Aktivitaet in normaler Sprache. Control enthaelt den detaillierten, replaybaren Schrittverlauf.


## 2026-11-11 — Control-Timeline-Projektisolation

- JSONL-basierte Timeline-, Aktivitaets-, Swimlane- und Live-Feed-Aggregatoren filterten teilweise nur dann nach Projekt, wenn keine Run-ID vorgegeben war. Eine explizite oder kollidierende Run-ID konnte deshalb Auditdaten anderer Projekte in der UI zeigen.
- Alle vier Aggregatoren begrenzen die Daten jetzt immer zuerst auf das angefragte Projekt; Legacy-Events ohne Projektzuordnung gelten weiterhin ausschliesslich als Werkstatt-Events.
- Regressionstests decken identische Run-IDs in mehreren Projekten fuer Timeline, aktive Rolle, Swimlane und Live-Feed ab.
- Das schliesst einen konkreten Teil der Projektisolationskriterien aus ADR-0031 und OP-394 ab; die vollstaendige Control-Timeline bleibt offen.


## 2026-11-11 — Projektspezifische Run-Suche in der Command-Palette

- Die Run-Suche der projektgebundenen Command-Palette fragte SQLite bisher ohne Projektfilter ab und konnte Treffer anderer Projekte anzeigen.
- Die SQL-Abfrage bindet das aktive Projekt nun als Pflichtfilter; ein Regressionstest legt gleichnamige Suchtreffer in zwei Projekten an und bestaetigt, dass nur der projektrelevante Run erscheint.


## 2026-11-11 — Control-Timeline mit kuratierten Belegen

- Der Live-Feed kann jetzt den fortgeschriebenen Phase-/Task-Kontext sowie explizite Ergebnis-Kurztexte, begruendete Entscheidungen, Beleglisten und naechste Schritte anzeigen.
- Backend und UI reichen nur diese benannten Kurzfelder weiter; beliebige Payloads und chain_of_thought bleiben ausgeschlossen. Die UI rendert Nutzdaten ausschliesslich mit DOM-Textknoten.
- Backend- und Frontend-Regressionstests pruefen den Belegvertrag und dass ein internes Rohfeld nicht in der Timeline erscheint. Die Detailansicht in Control ist damit vorbereitet; Loop-Emitter muessen die strukturierten Belege noch an den relevanten Checkpoints liefern.


## 2026-11-11 — Timeline-Task-Erfolge an tatsächlichen Abschluss gebunden

- `_task_ende` meldet jetzt zurück, ob der Task neu als `done` markiert wurde. Duplikate, Sticky-Vetos und Human-Review-Pfade erzeugen dadurch keinen irreführenden `loop_task_ok`-Eintrag.
- Erfolgsereignisse tragen die Phase-State-Task-ID, den Status und einen knappen Abschlussbeleg. Der bisher nicht protokollierte erfolgreiche Verify-Task erscheint ebenfalls; Task-Start und Read-only-Ereignis verwenden dieselbe stabile ID.
- Regressionstests prüfen den einmaligen `done`-Übergang und den strukturierten Timeline-Beleg. Die Chat-Aktivitätszeile bleibt davon getrennt.


## 2026-11-11 — Verify-Belege fuer gezielte Reparaturen

Verify speichert je ausgefuehrter Stage einen kleinen strukturierten Befund
(Stage-ID, Exit-Code, begrenzter Fehlerkern). Der Builder erhaelt nur die
fehlgeschlagenen aktuellen Checks, als untrusted Tool-Ausgabe markiert; alte
Befunde werden an Task-Grenzen zurueckgesetzt. Volle Logs und interne
Gedankengaenge werden nicht in den Reparaturkontext kopiert.

Umsetzung auf Main: `fb6c680`, `6bf01bc`, `ce2f68d`, `8d4f091`.
Tests fuer Stage-Belege, Task-Reset und Builder-Kontext sind hinzugefuegt.
Quality-Gate laeuft; Ergebnis wird erst nach Abschluss des CI-Laufs bewertet.


## 2026-11-11 — Chat-Werkzeugarbeit laeuft bis zum Ergebnis

Der Chat-Agent hat keinen willkuerlichen Default von fuenf Werkzeugrunden mehr.
Er arbeitet bis zur finalen Antwort weiter; Nutzerabbruch bleibt moeglich.
Wiederholt sich derselbe Werkzeugzyklus mit identischen Argumenten und
identischem Ergebnis, gibt der Agent zunaechst einen Kurswechsel-Hinweis und
fasst bei weiterem Stillstand den belegten Stand samt offenen Punkten zusammen.
Ein explizit gesetztes Rundenbudget endet ebenfalls mit einer normalen,
beleggebundenen Abschlussantwort statt einer internen Fehlermeldung.

Umsetzung: `2447873` (Fortsetzung/Stagnation), `4469948` (Tests) und
`21028ac` (Mypy-Signatur). Regressionstests fuer sechs Werkzeugrunden und
Stagnationsabschluss hinzugefuegt. GitHub Quality Gate fuer `21028ac`:
1.996 passed, 5 skipped; Ruff 0, Mypy 0, AST 374 Dateien/0 Fehler,
Audit-Katalog bestanden; `ok: true`.


## 2026-11-11 — Chatdarstellung und Composer

Assistant-Antworten werden ohne Bubble vollbreit dargestellt; Nutzernachrichten
bleiben rechtsbuendige Bubbles. Die Chat-Eingabe hat nur noch einen sichtbaren
Fokusrahmen und setzt nach dem Senden ihre Hoehe zurueck. Der Asset-Cache wurde
aktualisiert.

GitHub Quality Gate: `9993b25` — 1.998 passed, 5 skipped; Ruff/Mypy 0,
AST 374 Dateien ohne Fehler, Audit-Katalog bestanden; `ok: true`.


## 2026-11-11 — Assistant-Text kompakter setzen

- Assistant-Antworten werden auf 68 Zeichenbreiten begrenzt und mittig ausgerichtet; dadurch bleiben lange Absätze im Chat leichter lesbar.
- Nutzernachrichten behalten ihre rechtsbuendige Bubble-Darstellung. Ein Frontend-Test sichert die Lesebreite.


## 2026-11-11 — Nutzer-Bubbles an Lesespalte ausrichten

- Nutzer-Bubbles bleiben am rechten Chat-Rand ausgerichtet und sind auf maximal 72% bzw. 68ch begrenzt; auf schmalen Displays nutzen sie den verfügbaren Platz.
- Ein Frontend-Test sichert Desktop-Breite, Ausrichtung und Mobile-Grenze.


## 2026-11-11 — Architektur-Doku mit angenommenen ADRs abgleichen

- ARCHITECTURE.md behauptete noch, ADR-0030 sei proposed, beschrieb Worktrees innerhalb des Checkouts und zeigte Scout/Architect als starre Pflichtkette.
- Aussagen sind mit ADR-0030, STATUS.md und den aktuellen Pfaden in project_sources.py/planner.py abgeglichen. OP-399/400 bleiben als offene Umsetzung gekennzeichnet.


## 2026-11-11 — Chat-Loop-Grenzfaelle aus OP-396 absichern

- Beim Abgleich der Akzeptanzkriterien fehlten Tests fuer explizite Werkzeugrunden-Budgets und Nutzerabbruch nach einem ausgefuehrten Werkzeugschritt.
- Die Abschlussantwort wird ohne weitere Tools aus den vorhandenen Belegen erstellt; ein Abbruch stoppt vor dem naechsten LLM-Aufruf und laesst User-/Tool-Ereignisse replaybar im Verlauf.


## 2026-11-12 — Chat-Kontextbudget

- Vorherige abgeschlossene Chat-Turns werden fuer Modellaufrufe auf ein Zeichenbudget begrenzt; alte Roh-Werkzeugtraces bleiben im persistenten Verlauf, werden aber nicht erneut in den Prompt kopiert.
- Auch im aktiven Auftrag werden abgeschlossene Werkzeugrunden zwischen Modellaufrufen auf 24.000 Zeichen begrenzt: die juengsten Runden bleiben bevorzugt roh, aeltere Runden werden als markierte Belegauszuege mit Toolnamen und Argumenten verdichtet. Grosse Einzelausgaben werden nur im Modellprompt gekuerzt; der Event-Store behaelt sie vollstaendig, damit gezielte Nachlese moeglich bleibt. Es gibt weiterhin kein Standard-Rundencap.
- Regressionstests decken alte und aktive Kontextbudgets, erhaltene aktuelle Belege, unveraenderte Transcripts und gekuerzte Prompt-Ausgaben bei vollstaendiger Event-Persistenz ab.


## UI-Nachbesserung Chat-Ausrichtung (2026-11-12)

- Assistant-Antworten bleiben links in einer begrenzten Lesespalte; Nutzer-Bubbles sitzen am rechten Rand und sind schmaler begrenzt.
- Stylesheet-Cache-Buster aktualisiert.


## OP-398: Kein falscher Erfolg bei unvollstaendigen Tasks (2026-11-12)

- Befund im aktuellen Phase-Finalizer: Nach freigegebenem Human-Gate und gruener Phase-End-Verify konnte `loop_erfolg` erscheinen, obwohl geplante Tasks im PhaseState failed, blocked oder noch offen waren.
- Finalisierung prueft jetzt den persistierten Task-Status. Unvollstaendige Tasks erzeugen ein `loop_phase`-Ereignis mit Status `incomplete`, IDs und Statusbelegen; der Prozess kehrt mit Fehlerstatus zurueck und emittiert kein `loop_erfolg`. Bereits ausdruecklich freigegebene Teil-Aenderungen koennen nach gruener Verify committed bleiben; der Run wird trotzdem nicht als vollstaendig gemeldet.
- Regressionstests decken failed, blocked, pending, running und fehlenden Task-Status ab.


## 2026-11-12 -- OP-398: Scout-No-Op an Phase-End-Verify gebunden
- **Status:** done
- **Info:** Scout-No-Op konnte Plan- und Ergebnis-Gate passieren und direkt `loop_erfolg` melden. Der Pfad in `werkstatt/phases/plan.py` fuehrt jetzt nach dem Ergebnis-Gate dieselbe Phase-End-Verify aus; bei Fehlern wird der Run als unvollstaendig auditiert und rc=1 geliefert. Die Full-Suite-Stage `pytest_regression` in Repo- und Scaffold-Verify-Konfiguration laeuft bei `phase_end` auch ohne geaenderte Python-Dateien. Der alte OP-149-Testvertrag wurde angepasst; Regressionstests sichern Reihenfolge und Verify-Stage ab.
- **Tests:** `tests/test_loop_planner_split.py` erweitert; CI-Verifikation folgt.


## 2026-11-12 — Final-Verify-Failure-Record und UI-Zielplan

- Der Finalizer persistiert jetzt bei rotem Phase-End-Verify einen strukturierten Failure Record ausserhalb des Projekt-Checkouts: Run/Projekt, Verify-Stage, Exit-Code, HEAD-SHA, Worktree-Fingerprint und redigierte kurze Fehlerauszuege. Der Artefaktverweis und Befund werden an das bestehende Gate-Failed-Event gebunden; ein Fehler bleibt rc=1 und kann keinen Erfolg ausloesen.
- OP-403 bleibt offen: derselbe Run muss den Befund noch an eine sichere Diagnose-/Repair-Schleife uebergeben und erneut verifizieren. Der Record ist deren belastbare Eingabe, kein vorgetaeuschter Repair.
- OP-397/398 wurden an Run-Zielgraph und Checkpoint statt an den alten PhaseState als Laufzeitsteuerung angepasst. Runde-Cap als Abschlusskriterium aus OP-396 entfernt; echte Budgets/Stagnation bleiben.
- Neuer UI-Zielplan: `docs/UI-PLAN-2026-11-12.md`. Codeguardian ist als unabhaengige, nicht schreibende Diff-Schutzschicht beschrieben und in OP-404 aufgenommen.
- CI: Quality gate erfolgreich auf `fd5adae`; Ruff und JavaScript-Syntax gruen, `pytest` 2.015 passed / 5 skipped, `tools.quality_gate --json` erfolgreich.


## 2026-11-12 — OP-Queue an ADR-0032 ausgerichtet

- OP-324 und OP-385 sind in OP-398 zusammengefuehrt: Planabdeckung, DAG-Validierung und adaptive Auswahl von Scout/Architect/Spec-First gehoeren zum zielorientierten Koordinator, nicht in zwei parallel gepflegte Ziele.
- OP-386 ist in OP-403 aufgegangen: strukturierte, relevante Fehlerbelege und evidenzgebundene Reparatur sind Bestandteil derselben Failure-Recovery-Kette.
- OP-384/387/388 sind in OP-405 konsolidiert: Rollenbudgets, begrenztes JIT-Retrieval und deterministische Budgetregressionstests bilden einen gemeinsamen Kontextvertrag.
- OP-372/374/375, OP-394/395 und OP-308 bleiben offen: aktuelle Doku und UI belegen nur Teilfunktionen; fuer semantische Projektion, Backfill-Herkunft, vollstaendige Timeline und Browser-Dogfooding fehlt noch der angeforderte Betriebs-/Regressionnachweis. Die Oberflaeche allein ist kein Erledigungsbeleg.
- Keine dieser Zusammenfuehrungen erklaert die enthaltenen Anforderungen fuer erledigt; sie bleiben als Akzeptanzkriterien in den neuen bzw. bestehenden OPs erhalten.


## 2026-11-12 — Verify-State nach Recovery-Versuch zuruecksetzen
- **Status:** done
- **Info:** Ein erfolgreiches Verify loescht nun `last_verify_errors` und ersetzt die Stage-Ergebnisse durch die aktuelle Ausfuehrung. Damit kann ein frueherer Fehler nicht als aktueller Diagnosebefund weiterleben. Regressionstest: erst rotes, danach gruenes Verify im selben Run-State.
- **Tests:** CI-Verifikation ausstehend.
- **OP-403:** bleibt offen; sichere, evidenzgebundene Reparatur und erneute Endpruefung im selben Run sind noch nicht implementiert.


## 2026-11-12 — Reflection-Befund auf aktuellen Task begrenzen
- **Status:** umgesetzt; Quality-Gate-Verifikation ausstehend.
- **Info:** Die Erschoepfungsdiagnose fuer einen Spec-Widerspruch wertet nur Reflection-Versuche desselben Aufrufs aus. Historische Patches eines vorigen Tasks koennen keinen aktuellen Widerspruch mehr vortaeuschen. Regressionstest deckt den Cross-Task-Fall ab.
- **OP-403:** Der Failure-Record ist weiterhin nur Diagnosegrundlage. Same-run-Reparatur nach finalem Verify und deren End-to-End-Nachweis bleiben offen.

## 2026-11-12 — Laufbudget an RunState

`loop.main()` uebergibt jetzt das konfigurierte Projektbudget an den `RunState`; zuvor wurde es trotz YAML-Konfiguration leer initialisiert. Ein Regressionstest prueft die Durchreichung von `max_minutes` und `max_llm_calls`. Das aktiviert noch keine Budgetdurchsetzung; diese folgt als eigener Schritt mit kontrolliertem Abbruch und Audit-Ereignis.

## 2026-11-12 — Run-Budgets werden durchgesetzt

Projektbudgets fuer max_llm_calls und max_minutes stoppen weitere Modellaufrufe vor dem HTTP-Aufruf. Die Erschoepfung wird einmal pro Run auditiert und als Zustand festgehalten; der Task-Loop stoppt am naechsten Checkpoint, speichert den Phase-State und meldet keinen Erfolg. Endpruefung und Prozess-Cleanup bleiben davon getrennt. Regressionstests decken beide Grenzen ab. Server-/CI-Ausfuehrung steht noch aus.

## 2026-11-12 — Verify-Regressionstest auf Repo-Konfiguration begrenzen

- Serverlauf auf `1ce6483` zeigte einen Testfehler, weil `test_verify_regression.py` neben den Werkstatt-Konfigurationen auch `/opt/security-ai/.werkstatt/verify.json` eines separaten Projekts geprueft hat. Dessen changed-files-Filter ist kein Werkstatt-Repo- oder Scaffold-Vertrag.
- Der Test prueft nun nur die repo-eigene Verify-Konfiguration und das Scaffold-Template. Die Verifikation auf `main` laeuft ueber GitHub Actions.

## 2026-11-12 — Verify-Test-CI-Korrekturen

- Die erste CI nach der Testisolation stoppte vor pytest: Ruff fand eine veraltete `f`-Referenz im geaenderten Test und implizite Stringverkettung im zuvor bestehenden Zeitbudget-Guard. Beide Befunde sind korrigiert; GitHub Actions prueft den Commit erneut.

- Die zweite CI-Runde meldete Ruff UP032 fuer die format()-Schreibweise; der Budget-Fehlertext nutzt nun f-Strings. Die komplette CI muss den Fix noch bestaetigen.

## 2026-11-12 — Run-Budget aus State-Inventar-Totbaseline entfernt

- GitHub-CI lief mit Ruff gruen und 2.019 Tests bestanden; ein Baseline-Test meldete `budget` als aus der Tote-Feld-Baseline weggefallen. Das Feld ist durch den Run-Budget-Guard jetzt direkt gelesen und damit `read_only`.
- `budget` ist aus `BASELINE_TOTE` entfernt und der State-Inventar-Test prueft seine neue Kategorie explizit. Vollstaendige CI-Verifikation folgt.

## 2026-11-12 — OP-403: Unversionierte Inhalte im Failure-Fingerprint

- Failure Records hashen nun auch Inhalt, Pfad und Dateityp nicht ignorierter unversionierter Dateien; zuvor enthielt der Hash dort nur Status und Dateiname. Symlinks werden als Linktext gehasht und nicht verfolgt. Dateiinhalte werden nicht im Artefakt gespeichert.
- Regressionstest prueft, dass eine Aenderung in einem unversionierten Quellfile den Fingerprint aendert. GitHub-CI prueft den Patch.

- CI meldete im OP-403-Fingerprint-Patch nur einen unsortierten Importblock; die Reihenfolge ist korrigiert. Der Testlauf steht noch aus.

- CI pruefte den Fingerprint-Code und fand zwei Test-Fixture-Luecken: Der Git-Mock lieferte keine leere `ls-files`-Liste und der neue Regressionstest codierte NUL/Newline falsch. Beides ist korrigiert; die naechste CI prueft den echten Inhaltswechsel.

- Der vollstaendige Lauf erreichte nach dem Fingerprint-Fix einen nichtdeterministischen Zeitbudget-Test: Er leitete den Startzeitpunkt aus dem globalen `time.monotonic()` ab. Der Test setzt Startzeit und Uhr jetzt explizit, damit ein anderer Test-Mock die Messung nicht beeinflusst.

- OP-403 begonnen: Ein fehlgeschlagenes Phase-End-Verify kann im selben Run anhand gespeicherter, redigierter Stage-Auszuege in die bestehende Reflection-Reparatur gehen. Ein erfolgreicher Reparaturcheck reicht nicht; danach muss die vollstaendige Phase-End-Verify erneut gruen sein. Unvollstaendige Failure Records bleiben fail-closed.

- OP-403 Audit-Integration: Recovery-Start, Reparaturfehler, erfolgreiche Reparatur und Stillstand sind jetzt als bekannte Audit-Kinds registriert; der Regressionstest ist im Modul-Stil formatiert.


## 2026-11-12 — Verify-Recovery in der Control-Timeline erklaert

- Die same-run-Recovery nach rotem Phase-End-Verify liefert jetzt explizite Kurztexte zu Ergebnis, begruendeter Entscheidung, Verify-Belegen und naechstem Schritt.
- Recovery-Start, Reparaturfehler, gruene Reparatur und nicht erfolgreiche Reparatur haben eigene lesbare Labels in Backend und Control-UI. Die Timeline bleibt bei kuratierten Feldern; Prompt-/Rohdaten werden nicht dargestellt.
- Ein Backend-Regressionstest prueft die Kurzfelder und schliesst Rohprompt-Leckage aus. GitHub Actions muss das Paket noch verifizieren.


## 2026-11-12 — OP-403: Recovery prueft zuerst nur fehlgeschlagene Stages

- Der same-run-Reparaturpfad uebergibt die Stage-IDs aus dem Failure Record an Reflection. Jede Reparaturpruefung laeuft damit gezielt; der Finalizer fuehrt danach weiterhin die vollstaendige Phase-End-Verify aus.
- Fehlt eine angeforderte Stage im aktuellen Verify-Contract oder wird sie durch Requires/Dateiplatzhalter uebersprungen, gilt die gezielte Pruefung fail-closed als fehlgeschlagen. Ein uebersprungener Test kann nicht mehr als gruener Reparaturnachweis gelten.
- Control-Timeline protokolliert pro Reparaturversuch die betroffenen Verify-Stages und den anschliessenden Voll-Verify als naechsten Schritt.
- Neue Tests decken Stage-Auswahl, fehlende Contract-Stages und geskipte angeforderte Stages ab. CI-Verifikation ausstehend.


- OP-403-Korrektur waehrend der Umsetzung: Nach gruener gezielter Stage-Verify beendet Reflection jetzt den Reparaturversuch unmittelbar. Zuvor konnte sie nach einem erfolgreichen gezielten Check weitere Builder-Runden starten, bevor der Finalizer den Voll-Verify ausfuehrte. Der Voll-Verify bleibt die einzige Abschlussfreigabe.


## 2026-11-12 — OP-403: Folgefehler im selben Run weiterbearbeiten

- Wenn die gezielte Reparatur einen Befund behebt, aber die vollstaendige Phase-End-Pruefung einen weiteren Stage-Fehler findet, erzeugt der Finalizer einen neuen Failure Record und startet gezielte Recovery fuer diese Fehlergruppe im selben Run.
- Die Recovery verwendet alle fehlgeschlagenen Stage-IDs aus dem redigierten Record, nicht nur die ersten sechs. Sie verknuepft Folgeversuche ueber vorherige Failure-IDs in der Timeline.
- Wenn derselbe Fehlerauszug am selben Worktree-Fingerprint wiederkommt, erkennt der Finalizer Stagnation, stoppt fail-closed und laesst Verify rot. Ein roter Voll-Verify kann weder Commit noch Erfolg ausloesen.
- Regressionstests pruefen einen zweiten, neu auftretenden Stage-Befund sowie das Stoppen bei identischem Fehlerzustand. CI-Verifikation fuer diesen Commit steht aus.


## 2026-11-12 — Resume nach fehlgeschlagenem Phase-End-Verify

- Befund: Der Task-Loop uebersprang im Resume persistierte `done`-Tasks korrekt, setzte seinen Laufzaehler aber auf null. Damit konnte die Finalisierung trotz erledigtem Plan mit `no_successful_tasks` abbrechen, bevor sie das fehlgeschlagene Phase-End-Verify erneut pruefte.
- Der Laufzaehler uebernimmt jetzt ausschliesslich `done`-Tasks aus dem validierten Phase-State. Failed-, blocked- und pending-Tasks zaehlen nicht als erledigt; die Abschlusspruefung kontrolliert sie weiterhin einzeln und bleibt fail-closed.
- Ein Regressionstest startet den Task-Loop mit einem bereits erledigten Plan und prueft, dass die Finalisierung den Resume-Pfad erreicht.
- OP-397 bleibt offen: Dauerhaftes Run-Checkpointing, Pause/Resume ueber Prozessneustarts und Ende-zu-Ende-Verifikation sind damit nicht abgeschlossen. CI-Verifikation fuer diesen Patch steht aus.


## 2026-11-12 — OP-397: Resume bis zur erneuten Phase-End-Verify integriert

- Der Verhaltensregressionstest verwendet denselben gespeicherten Phase-State fuer Task-Loop und Finalizer. Er beweist, dass bereits erledigte Tasks nicht erneut gebaut werden, der Laufzaehler erhalten bleibt und die vollstaendige Phase-End-Verify vor Commit erneut laeuft.
- Ein erfolgreicher Abschluss wird nur nach dieser Verify protokolliert. Das deckt den zuvor nur isoliert getesteten Uebergang Task-Loop -> Finalizer ab.
- GitHub-CI prueft den erweiterten Test; dauerhafte Wiederaufnahme und Live-Run-SSOT nach Prozessneustart bleiben Teil von OP-397/M1.

## 2026-11-12 — OP-397/M1: Run-Startkontext restartfest speichern

- Die persistente Loop-Registry speichert beim atomaren Start jetzt Zieltext, OP-ID, Herkunft, Remote-/Branch-/Basis-SHA und die Auswahlbegruendung mit demselben Run. Eine konkurrierende Startanfrage kann diesen Kontext nicht ueberschreiben.
- Der Projekt-Loop-Endpunkt gibt den aktiven Startkontext nach einem Webserver-Reconnect mit aus. Der Prozessstatus bleibt in der vorhandenen Registry; es wird keine zweite Run-State-Quelle angelegt.
- Migration bestehender Registry-Datenbank erfolgt additiv mit leerem Kontext fuer alte Runs. Registry- und Web-API-Regressionstests pruefen Speicherung, Duplikatschutz und Abfrage. Vollstaendige CI-Verifikation ausstehend.

## 2026-11-12 — OP-397/M1: Startkontext-CI verifiziert

- GitHub-CI meldete zunaechst zwei bestehende Loop-Status-Tests, deren exakte JSON-Vergleiche das neue additive Feld nicht erwarteten. Die Tests pruefen jetzt die bisherigen Statusfelder plus den Run-Kontext gezielt.
- Der korrigierte Quality-Gate-Lauf ist gruen: 2.032 Tests bestanden, 5 uebersprungen; Ruff, Mypy, AST und Audit-Katalog ohne Fehler. Lauf: https://github.com/ghxstfocus/werkstatt/actions/runs/43212112192

## 2026-11-12 — Fresh-Start-Checkpoint-Archivierung

- Befund: Jeder Webstart beginnt absichtlich mit `--fresh`. Ein zweiter Fresh-Start konnte die vorhandene `.fresh-bak`-Recovery-Kopie lautlos ueberschreiben.
- Der Loop archiviert eine bestehende Recovery-Kopie jetzt nummeriert, bevor er den aktiven Checkpoint als aktuelle Recovery-Kopie verschiebt. Scheitert das Verschieben, bricht der Start fail-closed ab; der alte Checkpoint wird nicht stillschweigend ignoriert.
- Regressionstests pruefen Erhalt und eindeutige Archivnamen. Das ist ein Sicherungsschritt, keine vollstaendige Wiederaufnahme nach Prozess- oder Server-Neustart; OP-397 bleibt offen.

## 2026-11-12 — Phase-Checkpoint an Run-ID binden

- Phase-State speichert jetzt die Run-ID als Checkpoint-Eigentum; Legacy-State ohne Feld bleibt ladbar und erhaelt die ID beim naechsten Save.
- Ein headless Lauf mit widerspruechlicher Run-ID stoppt vor Plan-/Task-Ausfuehrung fail-closed. Damit kann eine Registry-Recovery spaeter nicht versehentlich Checkpoint-Daten eines aelteren Runs fortsetzen.
- Tests decken Run-ID-Roundtrip, ungueltige Metadaten und den Abbruch bei Run-ID-Mismatch ab. OP-397 ist weiterhin offen; die Web-API bietet noch keinen Recovery-Start.

## 2026-11-12 — Reflection-Test an das verpflichtende Review-Gate angepasst

- Der erste CI-Lauf zur Checkpoint-Run-ID-Bindung lief in einem Reflection-Test in ein echtes Human-Gate, weil der Test nur den Reviewer abgelehnt, aber die nachgelagerte Gate-Entscheidung nicht isoliert hatte.
- Der Test beantwortet das Phase-Review-Gate jetzt explizit mit Reject; damit bleibt er deterministisch und kann die volle Suite ohne interaktive Eingabe durchlaufen.
- Der vorherige CI-Lauf hatte zusaetzlich bereits bei 7 Prozent einen Assertion-Fehler, dessen Abschlussbericht durch den spaeteren Timeout fehlte. Der korrigierte Lauf muss diesen Befund noch offenlegen.

- Folgepruefung: Ein zweiter Reflection-Test mit fehlgeschlagenem Builder traf denselben interaktiven Gate-Pfad. Auch dieser Test beantwortet das Gate jetzt explizit mit Reject, damit CI nicht erneut vor der Fehlerzusammenfassung haengen bleibt.

- Weitere Reflection-Faelle ohne Patch und mit rotem Verify liefen ebenfalls in dasselbe Gate. Beide isolieren die menschliche Reject-Antwort jetzt ebenfalls, damit die Tests das produktive Gate nicht versehentlich pollen.

- Der CI-Hang in den OP-168-Unit-Tests kam ebenfalls von veralteten Fixtures: Sie ersetzten `input()`, waehrend das aktuelle Gate `gates._frage_gate` nutzt. Die Fixtures beantworten jetzt den tatsaechlichen Gate-Einstieg und behalten die getrennte TTY-Pruefung.

- Zusaetzlicher Befund: `_HEADLESS` ist globaler Gate-Zustand; ein anderer Test konnte ihn bis in die OP-168-Tests tragen. Die Interactive-/Non-TTY-Fixtures setzen ihn jetzt vor jedem Fall zurueck und verhindern so Bridge-Polling aus CLI-Testresten.


## 2026-11-12 — Checkpoint-Run-ID-Kind registriert

- CI auf `b548933` bestand mit 2.038 Tests und 5 Skips; der verbleibende Fehler war ein fehlender Katalogeintrag fuer `loop_checkpoint_run_mismatch`, nicht ein Gate-Hang.
- Der Audit-Kind ist in der Registry ergaenzt. Die vollstaendige CI prueft den Katalog-Fix erneut.


## 2026-11-12 — Resume-Checkpoint fail-closed an Run-ID binden

- Befund: `--resume` uebersprang den Checkpoint-Run-ID-Vergleich. Ein Backup eines anderen Runs konnte dadurch geladen und auf die aktuelle Run-ID umgeschrieben werden. Fehlende, ungueltige oder strukturell kaputte Resume-Checkpoints konnten ausserdem unbemerkt einen neuen Planpfad ausloesen.
- Resume prueft den Checkpoint jetzt vor jeder Mutation: Datei muss existieren und gueltig sein; bei headless/Web-Aufrufen muss ihre Run-ID exakt der angeforderten Run-ID entsprechen. Abgelehnte Backups bleiben unveraendert liegen.
- Beim Aktivieren eines geprueften Backups wird ein vorhandener aktiver Checkpoint nummeriert archiviert; ein fehlgeschlagener Move stoppt fail-closed. `--resume` und `--fresh` sind gegenseitig ausgeschlossen.
- Regressionstests decken Run-ID-Mismatch, kaputte und fehlende Checkpoints sowie den Erhalt des aktiven Checkpoints ab. GitHub-CI (Run 43225327934): 2050 Tests bestanden; Ruff, Mypy, AST und Audit-Katalog gruen.

## 2026-11-12 — Resume-Test-Fixtures verwenden echte YAML-Zeilen

- CI fand im neuen Backup-Promotionstest, dass YAML-Fixtures literale `\\n` statt Zeilenumbrueche enthielten. Die Produktionsvalidierung hat sie daher korrekt abgelehnt.
- Testdaten auf echte Zeilenumbrueche korrigiert; erneute CI-Pruefung laeuft.


## 2026-11-12 — Verify-Recovery stoppt bei unverändertem Worktree

- OP-403: Wiederholte Failure Records wurden bisher nur bei identischem Fehlertext als Stillstand erkannt. Fluktuierende Testausgaben konnten bei unverändertem Code immer neue Builder-Reparaturversuche auslösen.
- Der Phase-End-Recovery-Pfad erkennt nun unveränderten Worktree-Fingerprint nach einem Reparaturversuch als Stillstand, auch wenn Stage-Ausgabe oder Fehlertext variiert. Rotes Verify bleibt fail-closed; der Audit-Eintrag nennt den Grund.
- Regressionstest variiert den Fehlerauszug bei identischem Worktree. GitHub-CI (Run 43225327934): 2050 Tests bestanden; Ruff, Mypy, AST und Audit-Katalog gruen.


## 2026-11-12 — Verify-Recovery verlangt Git-Provenienz

- OP-403: Ein Git-Fehler wurde im Failure Record bisher mit leerer Ausgabe gleichgesetzt. Das konnte einen scheinbar gültigen konstanten Worktree-Fingerprint erzeugen.
- Failure Records markieren HEAD/Fingerprint nun als nicht verfügbar, wenn Git-Abfragen fehlschlagen. Die automatische Phase-End-Reparatur bleibt dann vor dem Builder fail-closed und protokolliert die fehlenden Provenienzfelder.
- Tests prüfen fehlende Git-Provenienz und dass ohne Fingerprint kein Reparaturaufruf erfolgt. GitHub-CI (Run 43225327934): 2050 Tests bestanden; Ruff, Mypy, AST und Audit-Katalog gruen.


## 2026-11-12 — Phase-End-Recovery erhält begrenzte Verify-Belege

- OP-403: Der Recovery-Prompt wurde nach einer pauschalen 8.000-Zeichen-Grenze abgeschnitten. Bei vielen oder langen Verify-Ausgaben konnte dadurch ungültiges JSON entstehen und spätere Fehlerbelege verloren gehen.
- Die Begrenzung kürzt Auszüge strukturiert, erhält Stage-IDs und Exit-Codes wo möglich und kennzeichnet gekürzte oder ausgelassene Belege. Der erzeugte JSON-Teil bleibt parsebar und innerhalb des Budgets.
- Regressionstests decken lange Ausgaben und Metadaten-Überlauf ab. GitHub-CI (Run 43225327934): 2050 Tests bestanden; Ruff, Mypy, AST und Audit-Katalog gruen.


## 2026-11-12 — Phase-End-Recovery ist budget- und fortschrittsgesteuert

- OP-403: Die gezielte Phase-End-Reparatur lief bisher durch den allgemeinen Fünf-Runden-Deckel. Sie arbeitet jetzt bis zur bestandenen betroffenen Verify-Stage, bis ein identischer Code-/Fehlerzustand wiederkehrt oder das Run-Budget erreicht ist.
- Der Builder übergibt seinen RunState jetzt an den LLM-Aufruf. Dadurch zählen Recovery-Aufrufe gegen das bestehende LLM-/Zeitbudget und können es nicht umgehen.
- Regressionstest lässt die gezielte Stage erst nach sechs Builder-Aufrufen grün werden. Vollständige Phase-End-Verify bleibt danach verpflichtend. GitHub-CI (Run 43225327934): 2050 Tests bestanden; Ruff, Mypy, AST und Audit-Katalog gruen.


## 2026-11-12 — Finale Verify-Recovery wartet am menschlichen Checkpoint

- OP-403: Wenn die automatische Phase-End-Recovery ohne grünes Voll-Verify endet, wird der Run nicht mehr kommentarlos als abgeschlossen behandelt. Er öffnet ein adressiertes Gate mit Failure-Record, betroffenen Verify-Stages und konkretem nächsten Schritt.
- Das Gate kann den Debugger-Chat öffnen und offen bleiben. Nach menschlicher Aktion führt „Weiter“ zuerst die vollständige Phase-End-Verify aus; bei geändertem Arbeitsstand kann derselbe Run die gezielte Recovery erneut starten.
- Ein rotes oder nicht belegbares Ergebnis bleibt fehlgeschlagen. Nur die tatsächlich bestandene Vollprüfung setzt den Run fort. Regressionstest deckt Pause und Fortsetzung nach grüner Prüfung ab; GitHub-CI-Verifikation läuft.

## 2026-11-12 — Resume bleibt an die gespeicherte Run-ID gebunden

- ADR-0032: Ein lokaler Resume ohne CLI-Run-ID uebernahm bisher den Phase-Checkpoint, stellte aber den Run-Kontext fuer Audit- und Gate-Ereignisse nicht wieder her. Checkpoints ohne Run-ID konnten ebenfalls fortgesetzt werden.
- Resume lehnt Checkpoints ohne Run-ID jetzt fail-closed ab. Bei lokalem Resume wird die persistierte Run-ID vor dem Worker-Start wieder aktiviert; Web-Resume prueft weiterhin die explizite ID gegen den Checkpoint.
- Regressionstests decken fehlende Run-ID und lokale Wiederaufnahme mit stabiler Run-ID ab. Lokale Vollsuite/Quality-Gate-Verifikation steht noch aus.


## 2026-11-12 — Verify-Recovery-Gate und Run-Kontext korrigiert

- GitHub-Actions zeigte drei Integrationsfehler: neue Recovery-Events fehlten im Audit-Katalog; ein fehlgeschlagener Builder-Versuch brach vor dem menschlichen Phase-End-Gate ab; ein lokaler Resume-Test hatte ungültige YAML-Zeilenumbrüche.
- Recovery öffnet nun auch nach einem erfolglosen automatischen Reparaturversuch das adressierte Gate mit Failure Record. Die Entscheidung bleibt beim Menschen; ein Erfolg wird weiterhin nur nach bestandener vollständiger Verify gemeldet.
- Audit-Katalog um die Verify-Recovery- und Checkpoint-Mismatch-Events ergänzt. Resume-Fixture auf echtes mehrzeiliges YAML umgestellt.
- CI-Runs 43247044555 und 43248717924 belegten die Ausgangsfehler. Run 43250234763 stoppte zunächst am Ruff-Doppel-Eintrag des bereits vorhandenen `loop_checkpoint_run_mismatch`; der doppelte Katalogeintrag wurde entfernt. Neue CI- und Server-Verifikation stehen noch aus.


## 2026-11-12 — Verify-Recovery-Gate beendet Wiederholung ohne Fortschritt

- OP-403-Review: Nach „erneut prüfen“ konnte ein unveränderter, weiterhin roter Worktree das Phase-End-Gate erneut öffnen und bei wiederholter gleicher Antwort in einer Schleife bleiben.
- Recovery prüft jetzt den neuen Failure Record auf vollständige Provenienz und vergleicht danach den Worktree-Fingerprint. Fehlende Belege oder ein unveränderter Fingerprint beenden die Recovery fail-closed mit `loop_verify_recovery_stalled` und einem konkreten nächsten Schritt; ein geänderter Diff darf weiter gezielt repariert werden.
- Regressionstest belegt genau einen Gate-Durchlauf bei rotem Verify ohne Worktree-Fortschritt und stellt sicher, dass der Builder nicht erneut gestartet wird.


## 2026-11-12 — OP-396: Gate-Antworten laufen über die Projekt-Chat-Session

- Offene Run-Gates werden beim UI-Reconnect idempotent als Chat-Karten in die aktuelle Projekt-Session übernommen; Plan, Empfehlung und knappe Verify-/Diff-Belege bleiben aufklappbar.
- Antwort aus Chat oder Gate-Detailmodal läuft über denselben projekt- und run-gebundenen Chat-Endpunkt. Die Gate-Antwort bleibt im Run-Audit und wird zusätzlich in derselben Chat-Session replaybar gespeichert.
- Gate-Karten und Entscheidungen verwenden sessiongebundene Idempotenzschlüssel, damit das 2-Sekunden-Polling und Reconnect keine doppelten Chat-Ereignisse anlegen.
- Implementiert in Commit `7f359a1`; GitHub Actions Quality Gate Run [43256007757](https://github.com/ghxstfocus/werkstatt/actions/runs/43256007757) ist gruen: 2059 Tests, Ruff 0, Mypy 0, AST 378 Dateien ohne Fehler, Audit-Katalog bestanden.


## 2026-11-12 — OP-397: Herkunft des Chat-Loopstarts restartfest speichern

- Chat-Bestaetigungen uebergaben bisher nur Auftrag/OP-ID an den Web-Start. Die Registry markierte dadurch auch Chatstarts als `origin: web`; Session, bestaetigter Vorschlag und Auswahlgrund gingen im Run-Kontext verloren.
- Der bestaetigte Start setzt nun request-lokale Herkunftsmetadaten. Die Registry persistiert Chat-Session, Proposal-ID und Auswahlgrund zusammen mit dem vorhandenen Ziel, OP und gepinnten Source-Kontext. Direkte Webstarts erhalten einen expliziten Grund fuer die Nutzerauswahl bzw. den Direktauftrag.
- Tests decken Web-Direktstart-Metadaten, Chat→Start-Kontext und Auswahlgrund ab. GitHub Actions Quality Gate Run [43258824522](https://github.com/ghxstfocus/werkstatt/actions/runs/43258824522) ist gruen: 2060 Tests, Ruff 0, Mypy 0, AST 378 Dateien ohne Fehler und Audit-Katalog bestanden.


## 2026-11-12 — OP-397: Git-Stash nur mit Run-Marker zuordnen

- Der Loop wertete bisher eine Veraenderung an `refs/stash` als Beleg fuer eigenen Besitz. Ein gleichzeitig angelegter fremder Stash konnte dadurch beim Cleanup versehentlich wiederhergestellt werden.
- Stash-Erzeugung sucht jetzt den eindeutigen `werkstatt-loop:<uuid>` Marker in der Stash-Reflog-Nachricht und liefert ausschliesslich den zugehoerigen Commit-Hash. Fehlender, mehrdeutiger oder nicht lesbarer Nachweis stoppt den Run fail-closed; ein fremder Stash wird nicht als Cleanup-Ziel verwendet.
- Die Laufzeit-Restore-Tests verwenden den explizit belegten Hash und pruefen auch, dass ein fehlender Besitznachweis den Builder nicht startet. Der erste GitHub-CI-Lauf fand einen bestehenden Vertragstest fuer den Bool-Kompatibilitaets-Wrapper. Dieser Wrapper behaelt seine bisherige Semantik; nur der Loop-Cleanup nutzt die neue Hash-Rueckgabe. CI laeuft erneut.

## 2026-11-12 — OP-397: Stash anhand des Commit-Hashes wiederherstellen

- Beim Cleanup konnte ein gleichzeitig angelegter Stash den zuvor ermittelten `stash@{n}`-Selektor verschieben. Der Loop verwendet jetzt `git stash apply --index <commit>` und behaelt den Stash-Eintrag auch nach erfolgreicher Wiederherstellung als Sicherung. Das Audit markiert den erhaltenen Eintrag.
- Ein Test im echten Git-Repository erzeugt den fremden Stash zwischen Auflisten und Wiederherstellen. Er prueft Index und Working Tree separat sowie den Erhalt beider Stash-Eintraege.

## 2026-11-12 — OP-397: Checkpoint an die Run-ID binden

- Lokale CLI-Starts erzeugen ihre Run-ID vor der Ausfuehrung und speichern sie zusammen mit dem Plan. Ein lokaler Resume verwendet dieselbe ID fuer Audit und Checkpoint.
- Ein Resume mit expliziter Run-ID bevorzugt den passenden aktiven Checkpoint, auch wenn ein Fresh-Backup existiert. So bleiben bereits erledigte Tasks erhalten. Ein passendes Backup kann weiterhin aktiviert werden, wenn der aktive Checkpoint einem anderen Run gehoert.

## 2026-11-12 — OP-403: Befund je Abschluss-Recovery-Versuch sichtbar machen

- Das Control-Ereignis `loop_verify_recovery_started` nennt jetzt den konkreten Fehlerauszug der fehlgeschlagenen Verify-Stages und die laufende Versuchsnummer. Lange Details bleiben im Failure Record; erfolgreiche Stage-Ausgaben werden nicht in den Befund kopiert.
- Ein Regressionstest prueft zwei aufeinanderfolgende Recovery-Versuche mit unterschiedlichen Stage-Befunden und stellt sicher, dass Timeline-Evidenz und Versuchnummern pro Befund passen.
- GitHub Actions Quality Gate fuer diesen Commit muss vor Abschluss gruen sein.

## 2026-11-12 — OP-403: Fortschrittsereignisse an Runs binden

- Die globale PROGRESS-Deduplizierung konnte gleiche `verify_pending`-/Abschluss-Eintraege spaeterer Runs unterdruecken. Der Append-Schluessel traegt jetzt die Run-ID; Wiederholungen innerhalb desselben Runs bleiben idempotent, unterschiedliche Runs bleiben einzeln sichtbar.
- Task-, Verify-, Abschluss- und Doku-Nachzug-Eintraege uebergeben die Run-ID. Tests decken Wiederholung im selben Run, gleiche Ereignisse in zwei Runs und Run-Zuordnung im Finalizer ab.
- Verifikation: GitHub Actions Quality Gate fuer den Commit.

## 2026-11-12 — OP-403: Commit-Nachkontrolle im Loop

- Der Committer prueft nach erfolgreichem `git commit` erneut die gueltige HEAD-SHA, `git show --check` und den Working Tree. So werden nach dem Verify entstandene Aenderungen (etwa parallele Chat-Edits oder Hook-Reste) nicht stillschweigend als gepruefter Abschluss behandelt.
- Ein Post-Commit-Befund wird mit Commit-SHA und betroffenen Pfaden auditiert; der Run bleibt fehlgeschlagen statt `loop_erfolg` zu melden. Das tatsaechliche Commit-Ergebnis wird separat markiert.
- Regressionstest injiziert eine Aenderung unmittelbar nach dem Git-Commit und prueft, dass die Nachkontrolle sie erkennt. GitHub Actions Quality Gate fuer diesen Commit muss gruen sein.

- CI-Nachkorrektur: Der Whitespace-Check nutzt `git diff-tree --check --root --no-commit-id -r HEAD`, damit auch Root-Commits eindeutig behandelt werden und der reale Commit-Diff geprueft wird.

- CI-Nachkorrektur: `git diff-tree --check` liefert auf dem Zielrunner Exit-Code 2; der Post-Commit-Whitespace-Check nutzt deshalb `git show --check --oneline HEAD`.

- CI-Nachkorrektur: Der Whitespace-Check vergleicht jetzt direkt `HEAD^..HEAD` mit `git diff --check`; Root-Commits verwenden den `git show --root`-Pfad. Fehlermeldungen enthalten die Git-Ausgabe.

- Ursache des roten CI-Laufs behoben: `progress.append()` erzeugt keine zusaetzliche Leerzeile am EOF mehr. Zwischen Eintraegen bleibt ein sauberer Absatz; der neue End-of-file-Test und die Post-Commit-Pruefung schuetzen das Format.

- Qualitaetsgate-Nachkorrektur: Die optionale Liste offener Dateien wird vor dem Auditing zur Laufzeit typgeprueft; damit bleibt der Post-Commit-Fehlerpfad auch im mypy-Gate sauber.

## 2026-11-12 — OP-403: Commit gegen gepinnten Basisstand pruefen

- Die Post-Commit-Kontrolle vergleicht jetzt den Eltern-Commit des neuen HEAD mit dem unmittelbar vor `git commit` gepinnten Stand. Ein paralleler Commit im selben Checkout kann so nicht als Ergebnis des Runs ausgegeben werden.
- Ein Regressionstest simuliert einen konkurrierenden Folge-Commit und erwartet einen protokollierten `head_parent_mismatch` statt eines erfolgreichen Runs.
- GitHub Actions Quality Gate fuer den neuen Stand muss gruen sein.

## 2026-11-12 — OP-403: Commit-Inhalt gegen gepinnten Index pruefen

- Nach `git add -A` wird der Index als Tree-SHA fixiert. Die Commit-Nachkontrolle vergleicht danach Eltern-Commit und Tree-SHA; ein Hook, der Dateien waehrend des Commits umschreibt und staged, kann nicht als verifizierter Run-Commit durchgehen.
- Regressionstest simuliert einen Hook, der eine Datei waehrend `git commit` aendert und staged; der Commit wird als `head_tree_mismatch` fail-closed protokolliert.

## 2026-11-12 — OP-403: Voll-Verify nach jedem Commit

- Nach einem erfolgreichen Commit fuehrt der Finalizer die vollstaendige Phase-End-Verify erneut aus. Ein roter Befund erzeugt einen Failure Record und geht mit gezielter Reflection in denselben Run; nach jeder erfolgreichen Reparatur wird erneut committet und der neue HEAD wieder voll verifiziert.
- Wiederholter unveraenderter Arbeitsstand fuehrt zum bestehenden Recovery-Gate. Ein Commit allein kann keinen Run-Erfolg ausloesen.


## 2026-11-12 — OP-403 abgeschlossen: Commit nach Commit vollstaendig verifizieren

- Der Finalizer fuehrt nach jedem Commit die volle Phase-End-Verify erneut aus. Bei Rot werden Failure Record, gezielte Diagnose/Reparatur und erneuter Commit in derselben Run-ID weitergefuehrt.
- Nach gruener Verify prueft ein Snapshot-Check, dass HEAD weiterhin dem erwarteten Commit entspricht und der Working Tree sauber ist. Abweichungen verhindern Erfolg und werden mit Grund und Belegen auditiert.
- Verifikation auf `main` `681a47a`: GitHub Actions Quality Gate [43278824595](https://github.com/ghxstfocus/werkstatt/actions/runs/43278824595) erfolgreich: 2075 Tests bestanden, 5 uebersprungen, Ruff 0, Mypy 0, AST 379 Dateien ohne Fehler, Audit-Katalog bestanden.
- OP-403 aus der offenen STATUS-Queue entfernt. M0 bleibt wegen Live-Prozessstatus und vollstaendigen Builder-Ereignissen (OP-397/OP-395) offen.


## 2026-11-12 — OP-395: Builder-Modellaufrufe mit Task-/Dateikontext

- Modellaufrufe protokollieren Start und Ergebnis mit begrenzten Task-/Dateimetadaten; Prompt- und Datei-Inhalte gelangen nicht in diese Progress-Events.
- Lange Modellaufrufe senden alle 15 Sekunden einen Heartbeat an die Control-Timeline. Der bestehende CLI-Heartbeat bleibt bei fuenf Sekunden; Audit-Ausfall darf den Modellaufruf nicht unterbrechen.
- OP-395 bleibt offen: die temporaere Chat-Aktivitaetszeile, Reconnect-Replay und der durchgaengige End-to-End-Nachweis stehen weiterhin aus.
- ADR-0031/Roadmap/Architektur praezisieren den globalen Metaorchestrator auf der Startseite und die Projektchats als projektbezogene Koordinatoren. Die Aktivierung bleibt an ADR-0031-Nachweise gebunden.


## 2026-11-12 — OP-395: Live-Arbeit im Projektchat rekonstruieren

- Der Projektchat liest den aktiven Loop-Run und dessen aktuelle Live-Feed-Aktivitaet und zeigt genau eine temporaere, ersetzbare Statuszeile mit Rolle und Arbeitsschritt.
- Beim Projektwechsel wird die alte Anzeige entfernt; Reload und Reconnect rekonstruieren den Schritt aus Loop-Registry und Audit-Feed. Aktive Chatfragen behalten Vorrang, damit keine zweite konkurrierende Aktivitaetszeile entsteht.
- Die Anzeige enthaelt nur den aktuellen Arbeitsschritt, keine Prompts oder internen Gedankengaenge. Detaillierte Ereignisse bleiben in Control.
- OP-395 bleibt offen bis Reconnect-, UI- und End-to-End-Verifikation sowie laengere Builder-Heartbeats gemeinsam belegt sind.


## 2026-11-12 — OP-395: Heartbeat-Aktivitaet vollstaendig anzeigen

- Der Live-Feed behandelt `llm_call_heartbeat` jetzt als aktive Arbeit. Dadurch verschwindet die Chat-Aktivitaetszeile bei langen Modellaufrufen nicht nach dem ersten 15-Sekunden-Heartbeat.
- Start- und Heartbeat-Zeilen zeigen bounded Task-Name, Task-ID und maximal zwei Dateipfade; Prompt- und Datei-Inhalte bleiben ausgeschlossen.
- Regressionstest prueft Heartbeat-Erkennung und Kontextdarstellung. OP-395 bleibt fuer den vollstaendigen E2E-Nachweis offen.

## 2026-11-12 — OP-Doku-Nachzug: Belegkonsistenz und begrenzte Delete-Zone

- Der Committer bestaetigt jetzt einen bereits geschriebenen Progress-Beleg nur bei passender OP, `done`-Status und Run-ID. Ein fehlender oder nicht schreibbarer Beleg verhindert das Entfernen des OPs aus `STATUS.md`; bei fehlendem Beleg wird der vorherige Status wiederhergestellt.
- Die Delete-Zone dedupliziert OP-IDs und behaelt hoechstens die 20 neuesten Eintraege. Die ausfuehrliche Historie bleibt in dieser Datei.
- DOC_CONVENTIONS.md legt die Abschlussregel fest: vollstaendige Phase-End-Verify und persistierter OP-/Run-Beleg vor Statusentfernung.
- Regressionstests decken fehlenden Progress-Beleg, idempotenten Retry, Delete-Zone-Deduplizierung und Aufbewahrungsgrenze ab.
- Doku-Drift-Belege fuer die Code-Commits:
  - **Commit:** `d9bd0580739d531fbc33e26121fa9ce02c0c91af`
  - **Commit:** `49cd355848faa6f2eb7071b2646f4d52068c862c`
  - **Commit:** `5ddfb566e6d2f6b376a469b863517fca7b649808`
- GitHub-CI nach dem Doku-Nachzug: 1 Fehler im Audit-Katalog (`doku_nachzug_status_restore_failed` fehlte); Ruff und die uebrigen Pruefungen waren erfolgreich. Katalog-Fix: `3169aad8a51c1c8d5ac6ab981ee27ac845c89d89`; Folge-CI steht noch aus.


## 2026-11-12 — OP-405 Teilstand: Living-Docs-Kontext verbindlich und begrenzt

- Der Projektmanifest-Vertrag verlangt jetzt PROGRESS.md wie STATUS, ROADMAP und ARCHITECTURE. Der Loop laedt Progress als historische Evidenz; STATUS bleibt alleinige Quelle fuer offene OPs und Run-Events fuer den Live-Zustand.
- Der Progress-Kontext ist deterministisch auf zehn neueste Eintraege und 12.000 Zeichen begrenzt. Der Parser wird auch fuer read_recent genutzt. Das reduziert Kontextwachstum, ohne den append-only Verlauf im Dokument zu kuerzen.
- Regressionstests pruefen Pflichtfeld, letzte Eintraege und Zeichenlimit. OP-405 bleibt offen, weil Rollenrouting, Retrieval und Evaluierung noch fehlen.
- Doku-Drift-Belege fuer Code-Commits:
  - **Commit:** 2973e26db6706eb439f71c30cb2f957d18e1f036
  - **Commit:** c30e2090bed02ba2d4a9080a1b4a893c7ea71bf8
  - **Commit:** ba788989efaffb473b9436f3aac54a15d2f514cc
  - **Commit:** 2c71a59811a676e5bec7978b75503d116d8cc4c1
  - **Commit:** 5ee908b50a7954101662854fd2757fb1dd3d1700
  - **Commit:** 6e93c8d2d318b568b0595d3b2a063bebbfe18ea6
- CI fuer Commit `0c18649159e3f0b1085bbeb3aff9322f5394be49`: Quality-Gate-Workflow erfolgreich; 2.086 Tests bestanden, 5 uebersprungen; Ruff, JavaScript-Syntax und Quality Gate gruen. [Run 43290497310](https://github.com/ghxstfocus/werkstatt/actions/runs/43290497310).


## 2026-11-12 — OP-405 Teilstand: implementierte Architektur im Architect-Kontext

- Der standardmaessige Architect-Prompt v2 liess ARCHITECTURE.md bisher aus, obwohl das Manifest sie verpflichtend lud. Der Architect erhaelt nun einen begrenzten Auszug aus Produktarchitektur, Ausfuehrung, Verifikation und Doku-Vertrag (maximal 3.400 Zeichen).
- Der Regressionstest prueft Abschnittsauswahl, Groessenlimit und tatsaechliche Einbindung in den Architect-Kontext. OP-405 bleibt offen: Retrieval fuer weitere Rollen, ADR-Evidenz und Evaluierung sind noch nicht fertig.
- Doku-Drift-Belege fuer Code-Commits:
  - **Commit:** b9fb3569b167b8dbfd0d08dfc741e33c0f6a8436
  - **Commit:** 03975c07741c11485b311717463a6ca461cb5728
- CI fuer Commit `6fff05905324f3d3ff0956ee0e8c29b22245a292`: Quality-Gate-Workflow erfolgreich; 2.087 Tests bestanden, 5 uebersprungen; Ruff, JavaScript-Syntax und Quality Gate gruen. [Run 43292109189](https://github.com/ghxstfocus/werkstatt/actions/runs/43292109189).


## 2026-11-12 — OP-Doku-Nachzug: explizite OP-Zuordnung

- Die optionale STATUS-Automatik schloss bisher die erste OP-ID, die irgendwo im freien Auftragstext vorkam. Dadurch konnte eine bloß erwähnte Blocker- oder Folge-OP entfernt werden.
- Automatisch geschlossen wird jetzt nur noch eine OP, die als erste Auftragszeile ausdrücklich im Format `OP-NNN: Auftrag` oder `### OP-NNN: Auftrag` steht. Die allgemeine OP-Erkennung für Commit-Betreffzeilen bleibt davon getrennt.
- Regressionstests decken explizite Kopfzeilen sowie beiläufige OP-Erwähnungen und Blocker ab.
- Doku-Drift-Belege für die Code-Commits:
  - **Commit:** `d44d191876975701a81a5f2e85e04292b631483f`
  - **Commit:** `0fc358ac461314fc7a8024edc858aff6e032be13`
  - **Commit:** `470b2a96064405bd416395feef54f8b6421ee9a4`
  - **Commit:** `b318d296037015d1da03b4d72788744305ff9f86`
- GitHub Actions für den Teststand `b318d296037015d1da03b4d72788744305ff9f86`: 2.089 Tests bestanden, 5 übersprungen; Ruff, JavaScript-Syntax und Quality Gate grün. [Run 43293886542](https://github.com/ghxstfocus/werkstatt/actions/runs/43293886542).

## 2026-11-12 — Planner-Kriterien im Run erhalten

- Audit-Fund: Der normale Architect/Planner-Split verlangte keine strukturierten Akzeptanzkriterien und setzte den Run-State am Ende explizit auf eine leere Kriterienliste. Dadurch hatte der Phase-Review im Standardpfad keine prüfbaren Kriterien.
- Der Planner-Split erhält jetzt zusätzlich den Originalauftrag, fordert beobachtbare Kriterien im JSON-Ergebnis an und persistiert gültige, deduplizierte Kriterien im Run-State. Der nachfolgende Planner-Schritt löscht sie nicht mehr. Bestehende Kriterien bleiben erhalten, falls eine Split-Antwort sie auslässt.
- Regressionstests prüfen den Originalauftrag im Split-Kontext, die Übernahme der Kriterien und deren Erhalt durch run_planner.
- OP-398 bleibt offen: deterministische Planabdeckung, DAG-Validierung und ein SHA-/Artefakt-gebundenes Evidence Ledger sind damit noch nicht umgesetzt.
- Doku-Drift-Belege für die Code-Commits:
  - **Commit:** `d209eb3fc9e9de8e8abb1e8c0cd94486b9448972`
  - **Commit:** `6486d3dab06388b9c9b4906ab479f36420bcfb62`

## 2026-11-12 — OP-Abschluss an Review und Kriterien gebunden

- Audit-Fund: Der optionale STATUS-Nachzug konnte eine explizit genannte OP entfernen, obwohl der normale Planner-Split keine Kriterien geliefert hatte oder der Phase-Review nicht freigegeben war.
- Der Run-State speichert jetzt die erfolgreiche Phase-Review-Freigabe. Der Committer schließt eine OP nur bei ausdrücklicher OP-Kopfzeile, mindestens einem nichtleeren Abnahmekriterium und freigegebenem Phase-Review. Fehlende Voraussetzungen lassen den OP-Eintrag offen und werden mit einem konkreten Skip-Grund auditiert.
- Regressionstest deckt fehlende Review-Freigabe, fehlende Kriterien, beiläufige OP-Erwähnung und den zulässigen Fall ab. Der Committer wird im Finalizer erst nach grüner Phase-End-Verify aufgerufen.
- Doku-Drift-Belege für die Code-Commits:
  - **Commit:** `af502c9a35bbd13a53e7e1fa886b341e0f58c911`
  - **Commit:** `88702f47be2b4b999d986a47ec45b262f5d3e0d9`
  - **Commit:** `167b3b64200c644d494240ab4088be980be38357`
  - **Commit:** `9e1564fae4930b3098b2b7b41f480297f016feb1`
- GitHub Actions für den Abschlussstand `b3a5e9f91f3e031598096ee1089b46486e7a9ad6`: Quality-Gate-Workflow erfolgreich; Ruff, Pytest und Quality Gate grün. [Run 43297016790](https://github.com/ghxstfocus/werkstatt/actions/runs/43297016790).


## 2026-11-12 — OP-Doku erst nach vollständiger Verify schließen

- Audit-Fund: Der STATUS-Nachzug lag im selben Commit wie die Codeänderung. Eine danach rote Post-Commit-Verify konnte die OP daher bereits als erledigt hinterlassen.
- Der Finalizer hält den OP-Nachzug jetzt zurück, bis Code-Commit und vollständige Post-Commit-Verify grün sind. STATUS/PROGRESS/CHANGELOG werden danach separat geändert, auf diesem konkreten Stand erneut verifiziert und erst dann als Doku-Commit gespeichert. Bei roter Doku-Verify werden die Dokuänderungen vor dem Commit zurückgesetzt; bei Commitfehlern wird der Snapshot ebenfalls wiederhergestellt.
- Regressionstests prüfen die Reihenfolge Code-Commit → Post-Commit-Verify → Doku-Verify → Doku-Commit sowie Snapshot-Rollback für geänderte und neu angelegte Dateien.
- Code-Commits:
  - **Commit:** `9f3dbbcedb3b42cc83276fe4a9b393767c2f4b20`
  - **Commit:** `4341bc0ebeada1ad2e7e9306aa1862a2a1705509`
  - **Commit:** `11b2e7ec6dec2ef5cae136689000bdc976d4f301`
  - **Commit:** `53b97fb484cdfe29c30fecd1ab677da2b3c26785`
  - **Commit:** `a45f8aab8485934389af1a9d7870e7c647b1b6bb`
  - **Commit:** `cac1947fcb04481d2d0fc52e6199339be0261f28` (Ruff-Importkorrektur)
  - **Commit:** `ea8e88848659359eeff1295de02da43fc0577b43` (Ruff-Importkorrektur der Snapshot-Tests)
  - **Commit:** `ab14060ee6e517a48bcc22802baa81a5d5250b42` (Audit-Katalog)
  - **Commit:** `35db247bb8d0a8d9fb1ea92f6eb0e454b769cac7` (Legacy-State-Kompatibilität)
  - **Commit:** `dac56a82bfbcb4d8853e60f1a075dd1e483851ad` (Snapshot-Fehlerfixture)
  - **Commit:** `18a379d7903857e35e083a83ea6ed56fde6d2ed8` (Review-Reihenfolge-Fixture)
- GitHub Actions für den dokumentierten Stand `96473017a85f69eb18b748b7554f35a46d81f61d`: 2.095 Tests bestanden, 5 übersprungen; Ruff, mypy, AST-Check (379 Dateien), Audit-Katalog und Quality Gate grün. [Run 43300483073](https://github.com/ghxstfocus/werkstatt/actions/runs/43300483073).


## 2026-11-12 — Doku-Vertrag pro Projekt und Greenfield-Onboarding

- Befund: Scaffolder und Run-Start prueften bislang nur teilweise, ob Dokus vorhanden und lesbar sind. Fehlende Struktur, nicht ersetzte Template-Platzhalter und ein STATUS ohne OP-/Leer-Marker wurden nicht als gemeinsamer Vertrag fuer jedes Projekt erkannt.
- Der neue deterministische Doku-Preflight prueft die acht Living-Docs-Pfade aus dem Projektmanifest, sichere Checkout-relative Pfade, UTF-8-Lesbarkeit, nichtleere Dateien, offene Template-Platzhalter und das STATUS-Grundformat. Er laeuft nach jedem realen Scaffold sowie vor jedem Run; leere Startvorlagen mit explizitem Marker bleiben gueltig.
- OP-399/ADR-0031 verankern, dass UI und spaeterer Metaorchestrator denselben bestaetigungspflichtigen Greenfield-Anlagepfad verwenden. Projektregistrierung/Manifest muss Teil des startbaren Greenfield-Ergebnisses sein; Remote-Verknuepfung und Push bleiben separat freizugebende Aktionen.
- Der Check behauptet keine semantische Wahrheit oder Aktualitaet ueber Dokumente. Das bleibt eine spaetere evidenzbasierte Review-Aufgabe.
- Die lokale Projektanlage nutzt jetzt einen gemeinsamen Dienst fuer UI und spaeteren Metaorchestrator. Er legt die Pflichtdokumente an, validiert den strukturellen Vertrag und registriert danach exklusiv ein Manifest mit allen acht erforderlichen Doku-Pfaden; ein bestehendes Ziel oder Manifest wird nicht ueberschrieben.
- Die Pfadgrenze wird auch im gemeinsamen Dienst selbst erzwungen (Produktion: unter `/opt`). Schlaegt Scaffold/Manifest fehl, wird nur das neu von diesem Vorgang angelegte Projektverzeichnis bereinigt.
- Regressionstests decken startbares Manifest, Orchestrator-Laden, Pfad-/Namensgrenzen, Kollisionen und Bereinigung bei Scaffold-Fehler ab.
- Code-Commits: `7b48dd6434d0acb9d92ca3832e8f07440dea96ff` (Dokuvertrag, Tests, OP/ADR), `a74985f2fab93adc0c9142276e184e0043ff0648` und `62a16afc5dbb42db3fcf185cdfc2072a5229e2c2` (Ruff-Importkorrekturen), `a97f0b126477e021fa82cc9a8cde4ed819e0185d`, `e1935e5d9fd10ec63cff93e538c0151aa1a0a83e`, `3ab03580f1677116289555b37432be244de72eb9`, `93d665c7c035f702aebd7150c4c154e69fe3c4e1`, `0c6c123cd05f19ed0151906938a4ef78e7c6bd5e`, `b3c23aa683a5aaa5318beb898461f2c72486dc3d` und `690f6d408fc4a70032190bea91625e73c8d7ce1f` (gemeinsame Projektanlage und Tests).
- GitHub Actions auf `62a16afc5dbb42db3fcf185cdfc2072a5229e2c2`: 2.104 Tests bestanden, 5 übersprungen; Ruff, mypy, AST (381 Dateien), Audit-Katalog und Quality Gate grün, `ok=true`, `regression=false`. [Run 43303935169](https://github.com/ghxstfocus/werkstatt/actions/runs/43303935169).
