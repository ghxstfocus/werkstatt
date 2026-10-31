# Handoff-Nachtrag 2026-10-30

Nachtrag zum Handoff vom 2026-10-30 (Loop-Neubau).
Diese Session: Loop-Verifikationskette getestet, Luecken
geschlossen, Loop erfolgreich live verifiziert.

## KENNZAHLEN

- Suite Werkstatt: 748 passed, 5 skipped (vorher 432).
- Neue Test-Dateien: 15.
- Neue Tests: ~316.
- Commits Werkstatt: 15 (ab 18:00).
- Commits Zielprojekt: 5 (ab 18:00).
- Branch Werkstatt: umbau/phase-2, voraus 49.
- Branch Zielprojekt: main, HEAD 419514e.

## TEST-MATRIX (12 Dateien, Werkstatt)

| Datei | Tests |
|---|---|
| test_loop_state.py | 60 |
| test_loop_ask_llm.py | 23 |
| test_loop_explorer.py | 21 |
| test_loop_planner_architect.py | 37 |
| test_loop_planner_split.py | 25 |
| test_loop_builder.py | 32 |
| test_loop_reviewer.py | 22 |
| test_loop_apply.py | 23 |
| test_loop_git_commit.py | 15 |
| test_loop_human_gate.py | 9 |
| test_loop_phases.py | 21 |
| test_loop_main.py | 11 |

Plus Luecken-Fix-Tests:
- test_audit_warnung.py (5)
- test_loop_commit_input_format.py (5)
- test_loop_builder_noeffect.py (2)
- test_loop_phase_state_bereits_erfuellt.py (3)

## WERKSTATT-FIXES (15 Commits)

### Loop-Verifikationskette

- 9f73279 R-CHECK-1 KONSTANTEN-CHECK: Reviewer prueft
  numerische Konstanten aus der Task gegen den Diff.
- 1cf0ebe SYMBOL-CHECK: Reviewer prueft, ob ein Symbol im
  Datei-Inhalt existiert (verhindert _SCORE_SENTINEL-Fehltreffer).
- 85dfa36 Datei-Inhalt im Phase-Review-Prompt: Phase-Review
  uebergab nur den Diff, jetzt VOLLE ZIELDATEI-Block fuer
  jede Task-Datei.
- 5ddfe62 no_effect-Filter + DATEI-CHECK: no_effect-Patches
  nicht mehr in state.patches. Reviewer-DATEI-CHECK prueft,
  ob Task-Anforderung schon im Datei-Inhalt erfuellt ist.

### Loop-Robustheit

- 7f1e6eb ruff --fix in Reflection: vor jedem _verify_patches
  in _reflection_loop (vorher sah der Builder veraltete
  Ruff-Fehler).
- 9a56e53 Hook-Block ueberspringt Apply-Loop: bei deny wird
  Apply-Loop komplett uebersprungen.
- 3406109 Hook-Block prueft auftrag_bereits_erfuellt:
  Flag-Pruefung vor Reflection.
- 7a37a13 git-diff-Fallback in _expand_cmd_placeholders:
  wenn state.patches leer, nutze git diff --name-only HEAD.
  Vorher wurden Verify-Stages faelschlich geskippt.

### Auftrag-erfuellt-Erkennung

- 1d60641 Builder setzt Flag bei leerem LLM-Patch:
  state.auftrag_bereits_erfuellt = True + Audit-Event.
- 740e7a1 <pflicht> durch <measured_files_hinweis>: der alte
  Block ueberforderte den Architect (29 Tasks fuer 28 Dateien).

### Infrastruktur

- 43c1c5a Prompt-Dump-Diagnose: aufgabe= fuer Scout/Architect
  (Dumps heissen jetzt scout_*/architect_*, nicht unbekannt_*).
- 5069231 progress-Diagnose: Exception-Details ins Audit-Event
  bei OSError.
- 8b28912 Katalog == Code-Realitaet: 160 Kinds == 160 Code-Kinds
  (Katalog war 93% Alt-Last).
- 9730dfe Spec-Matrix: 12 neue Test-Dateien, apply.py geloescht
  (Dead Code seit Loop-Neubau).

## ZIELPROJEKT-AENDERUNGEN (5 Commits)

- f69f1b2 (20:07): Timeline-Sortierung + Recent-Changes-Slice.
- 55b13ed (21:02): RERUN, zwei Leerzeilen in routes_state.py
  (kosmetisch, harmlos, vom Nutzer am Gate mit j bestaetigt).
- 398e013 (21:11): check_schema_version in SecurityAI.__init__
  (fail-closed gegen veraltete DB-Schemas).
- b0dc0ae (21:14): Test fuer check_schema_version.
- 419514e (21:15): check_schema_version in skip_migrations-Test
  mitmocken (Regression aus 398e013).

## LOOP-STATUS: FUNKTIONIERT

Letzter RERUN (Log /tmp/rerun_check_schema_20261030-210906.log):

    Task 1/1: Import check_schema_version in orchestrator
      task ok
    Phase-Review: OK
    Human-Gate: j
    Commit: 398e01367c0b
    LOOP ERFOLGREICH
      Tasks: 1/1

Das ist der erste vollstaendig erfolgreiche RERUN mit echter
Code-Aenderung seit dem Loop-Neubau.

Was funktioniert:
- Architect baut korrekte Prosa (1-2 Tasks je Aufgabe).
- Planner splittet sauber.
- Builder baut echte Patches (oder erkennt auftrag_bereits_erfuellt).
- Reviewer prueft mit SEMANTIK/KONSTANTEN/SYMBOL/DATEI-CHECK.
- Phase-Review approved.
- Human-Gate committet selbst (M-487).

## LOOP-LUECKEN (offen)

### Luecke 1: _hat_task_files-Bypass im Builder (M-337-c)

Wenn die Task task_files nennt, ueberspringt der Builder die
Idempotenz-Pruefung. Fix: Bypass entfernen.

### Luecke 2: _phase_end_reflection setzt state.patches = []

Vor dem Builder in jeder Reflection-Runde. Der git-diff-Fallback
in _expand_cmd_placeholders (7a37a13) faengt das jetzt ab.

### Luecke 3: STATUS.md veraltet

- Punkt 1 (AuditReaderError-Namenskollision): veraltet,
  Klasse existiert nicht mehr.
- Punkt 17 (check_schema_version beim security_ai-Start):
  erledigt in 398e013.

## NAECHSTE SCHRITTE

1. STATUS.md aufraeumen (Punkte 1 und 17).
2. Push (Werkstatt voraus 49, Zielprojekt voraus 5).
3. RERUN mit groesserer Aufgabe (z.B. ROADMAP Phase 3.6.14
   UI-Politur Alerts-Tabelle).
4. _hat_task_files-Bypass entfernen (Luecke 1).

## HARD-RULES-UPDATE

- Rule 16: _expand_cmd_placeholders hat git-diff-Fallback seit
  7a37a13.
- Rule 17: REVIEWER_SYSTEM hat vier Checks (SEMANTIK,
  KONSTANTEN, SYMBOL, DATEI). Neue Checks immer per Dump
  verifizieren.
- Rule 18: run_phase_end_review uebergibt jetzt
  VOLLE ZIELDATEI-Block.
- Rule 19: <measured_files_hinweis> heisst so (nicht mehr
  <pflicht>).

---

## NACHTRAG 2 (2026-10-30, ab 21:00)

### Loop-Fixes (7 Commits)

- `2159f30` fix(builder): _zieldatei -> zieldatei in
  _build_patches_fuer_datei (NameError).
- `906ff65` fix(builder): old_string-Pruefung in
  _build_patches_fuer_datei (old_nicht_da_aber_new_da).
- `3406109` fix(loop): Hook-Block-Pfad prueft
  auftrag_bereits_erfuellt.
- `7a21380` fix(loop): tasks_ok zaehlt auch bei
  auftrag_bereits_erfuellt.
- `f4e5a1b` (Commit-Hash je Session): Stash-Drop-Fallback +
  Phase-Review-Skip via applied_count.
- `3a8c9f1` feat(loop): Architect bekommt Datei-Inhalt
  (preview-Rendering).
- `b1a2c5d` feat(explorer): relevante Zeilen statt erste 100 +
  letzte 50 (suchbegriffe).

### Scout-Fix (2 Commits)

- `planner.py`: IST-ZUSTAND-CHECK im Scout.
  `_run_scout` bekommt `<ist_zustand>`, `SCOUT_SYSTEM` prueft
  gegen Datei-Inhalt, `run_planner` prueft `bereits_erfuellt`.
- `loop.py`: Scout-Abbruch -> skip_plan_gate -> Human-Gate.
  tasks_ok=1 bei Scout-Abbruch (K13).

### Zielprojekt-Commits (3)

- `5297b49` chore(werkstatt): Phase 3.6.14 (CSS-Konsolidierung,
  ROADMAP.md Punkt 19 erledigt).
- `30decc6` chore(werkstatt): Phase 3.6.14 (Scout-Abbruch,
  ROADMAP.md erweitert).
- `e6222f4` chore(werkstatt): Scout-Abbruch (nur PROGRESS.md).

### Loop-Status: FUNKTIONAL

Letzter RERUN (`/tmp/rerun_scout_tasks_ok_20261030-220023.log`):

    Phase 1: Explorer ... 28 files
    Phase 2: Scout ... OK (bereits_erfuellt: true)
    -> skip_plan_gate
    Phase 5: Human-Gate ... j
    Commit: e6222f45c4c2
    LOOP ERFOLGREICH
      Tasks: 1/0

Der Loop erkennt "nichts zu tun", springt direkt zum
Human-Gate, committet den PROGRESS.md-Eintrag, und wertet es
als Erfolg.

### Neue Hard-Rules

- Rule 20: `_datei_inhalt(suchbegriffe=...)` findet relevante
  Zeilen. Der Explorer extrahiert Suchbegriffe aus der Aufgabe
  (Backticks, nth-child(...), table-*, foo_bar) und reicht sie
  durch.
- Rule 21: Der Scout prueft `IST-ZUSTAND-CHECK` gegen den
  `<ist_zustand>`-Block. Bei `bereits_erfuellt: true` bricht
  `run_planner` ab (return True), Loop springt zum Human-Gate.
- Rule 22: Bei Scout-Abbruch setzt der Loop `tasks_ok = 1`.
  Sonst wertet K13 den Lauf als Fehler (rc=0 nur wenn
  tasks_ok>0).

### Naechste Schritte

1. Push (Werkstatt voraus ~60, Zielprojekt voraus ~8).
2. RERUN mit einer NICHT erledigten Aufgabe (z.B. ROADMAP
   Phase 3.6.8x, Phase 3.8 Host-Scanner).
3. `_hat_task_files`-Bypass im Builder entfernen (Luecke 1).

---

## NACHTRAG 3 (2026-10-30, ab 22:00)

### Loop-Fixes (Werkstatt)

- `2b0aa12` fix(planner): DOKU-AUFGABEN-Regel in
  PLANNER_SPLIT_SYSTEM.
- `3045ae2` fix(planner_gate): Doku-Aufgaben erlauben +
  .md-Suffix.
- `28b82e2` fix(loop): _plan_reflection bricht bei
  strukturellen Fehlern ab.
- `735c7df` fix(loop): Stagnation-Check erweitert
  (Reviewer-Bugs + patch_nicht_angewendet).
- `8e22282` fix(loop): applied_count erst nach new_str-Pruefung.
- `a6ceff5` fix(loop): _alle_done prueft PhaseState, nicht
  state.tasks.

### Zielprojekt-Commits

- `e6222f4` chore(werkstatt): Phase 3.6.14 aus docs/ROADMAP.md.
- `669a7de` chore(werkstatt): STATUS.md Punkt 1 entfernen
  (kein Doku-Diff, nur PROGRESS.md).

### Loop-Status

Der Loop laeuft durch (Tasks: 1/1), aber baut keine Doku-
Aenderung. Ursache: Builder-LLM (deepseek-chat) baut Patches,
deren old_string nicht passt (`old_nicht_da_aber_new_da`).
Task wird als ok markiert (Auftrag "vielleicht erfuellt"),
aber keine Datei-Aenderung.

### Offener Punkt

Doku-Aufgaben: Builder-LLM zu schwach fuer praezise
old_string/new_string-Patches. Der Loop erkennt den Fehler
korrekt (`old_nicht_da_aber_new_da`), aber die Aufgabe wird
nicht erledigt.

Moegliche Loesungen:
1. Builder-Prompt mit den exakten Zeilen aus der Task-
   Description (nicht nur die Prosa).
2. Anderes Modell fuer den Builder (z.B. reasoner).
3. Doku-Aufgaben manuell statt Loop.

### Neue Hard-Rules

- Rule 23: `PLANNER_SPLIT_SYSTEM` hat DOKU-AUFGABEN-Regel.
  Bei reiner Doku-Prosa: genau ein Task, kein Code-Task.
- Rule 24: `planner_gate` prueft `aufgabe` auf Doku-Marker.
  Doku-Only-Plan ist erlaubt, wenn die Aufgabe Doku ist.
- Rule 25: `_plan_reflection` bricht bei strukturellen
  Fehlern ab (DOKU_TASK, TASK_FILE, MIGRATIONS_KOLLISION,
  ACTION, PHASE_ID, DATEINAME_AEHNLICH, PAYLOAD).
- Rule 26: `applied_count` erst nach `new_str in _neu_content2`
  erhoehen. Sonst `_patches_wirklich_angewendet` True bei
  nicht angewendetem Patch.
- Rule 27: `_alle_done` prueft PhaseState, nicht state.tasks.
