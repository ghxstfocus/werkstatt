# Aufraeumen und Loop-Umbau — Plan (2026-10-22)

Stand: 2026-10-22 | HEAD 752f1f5 | Branch umbau/phase-2
Baseline: 1245 / 17 / 9 / 6 / 167
Anker: 752f1f5

## Zweck

Vor dem Loop-Umbau (3b-2) raeumen wir die Werkstatt auf.
Grund (Messung T1-T7): 11 tote Audit-Kinds, 30 verstreute
subprocess.run, 12 ungetestete Skills, 404 Z. HARD_RULES-
Dopplung, 3 Builder-Dateien (1143 Z.), Config-Reads ohne
Kapselung, 179 Funktionen in pipeline.py.

Erst aufraeumen, dann Loop bauen. Sonst baut der neue Loop
auf MUELL.

## Profi-Befunde (Recherche, mit Quelle)

1. Multi-Agent ist oft Over-Engineering (Promptise, Respan.ai).
2. State Machine mit verschiedenen Prompts/Tools pro Phase
   ist legitim (Paddo.dev, NeurIPS 2025).
3. "Shorter is better": jede zusaetzliche Instruktion verduennt
   die Aufmerksamkeit auf alle anderen (Paddo.dev).
4. "Was immer gilt ins Prompt, was aufgabenspezifisch ist in
   Skills" (Chinesische Claude-Code-Community, Anthropic-Doku).
5. Dead-Code-Detection ist Standard (slopauditor,
   superclaude-plusplus, GitHub Dead Code Removal Agent).

## Abnahme

Plan abgenommen 2026-10-22 durch Auftraggeber.
Zitat A: "ok vorher halten wir den plan fest und
dann geht es los mit aufraeumen" (Auftraggeber,
Session 2026-10-22).
Zitat B: "ja" auf "Plan so anpassen und committen?"
(Auftraggeber, Session 2026-10-22).



## Reihenfolge

### Block A — Aufraeumen (VOR 3b-2)

A2. subprocess.run kapseln -> werkstatt/exec.py
    Ist: 30 Aufrufe in pipeline.py, verstreut, kein Helper.
    Ziel: run_git(), run_test(), run_lint(), run_shell()
         mit Timeout/Encoding/Exit-Code einheitlich.
    Warum zuerst: keine Verhaltensaenderung, keine Prompt-
         Aenderung, reine technische Schulden.
    Aufwand: 1 Tag.

A1. 11 tote Audit-Kinds streichen
    Ist: _KATALOG_SOLL = 167, 156 aufgerufen, 11 tot.
    Tot: builder_deadlock_anker_nicht_gemessen,
         builder_deadlock_leer, builder_deadlock_rueckfrage,
         builder_readfile_blockiert, llm_timeout_connect,
         planner_new_file_auf_existierend,
         planner_pfad_ausserhalb_projekt,
         planner_phase_zu_gross, review_command,
         review_round, reviewer_frage_antwort.
    Ziel: _KATALOG_SOLL = 156.
    Warum streichen: kein Aufrufer = YAGNI.
    Aufwand: 1h.

A3. 12 Skills testen (skills/*)
    Ist: 12 Skills, 0 Code-Referenzen, 0 Tests.
    Ziel: test_skills_ladbar: jeder Skill laedbar,
         valides Format (Frontmatter, Sektionen).
    Aufwand: 1 Tag.

A4. Config kapseln -> werkstatt/config.py
    Ist: 15+ config.get(...) Aufrufe direkt verstreut.
    Ziel: Config-Klasse mit Defaults, typsicher.
    Aufwand: 1 Tag.

A5. Builder-Dateien KONTROLLIERT KUERZEN (nicht zusammenfuehren)
    Ist: builder.md (552) + builder_patch.md (486)
         + builder_commit.md (105) = 1143 Z.
    Befund: Die Aufteilung ist State Machine (legitim).
         Aber 1143 Z. Prompt = "Shorter is better"-Verstoss.
    Ziel: je Datei auf ~150-200 Z. kuerzen. Gemeinsame
         Regeln in HARD_RULES_BASE (19 Z., bleibt).
         Aufgabenspezifisches in Skills auslagern.
    Warum NICHT zusammenfuehren: State Machine ist richtig,
         das Problem ist die Groesse, nicht die Trennung.
    Aufwand: 2 Tage (Kuerzen + Tests).

A6. HARD_RULES entdoppeln (Phase 3.0) — Prompt vs. Skill trennen
    Ist: HARD_RULES_REVIEWER 191 Z., HARD_RULES_PLANNER_
         STUFE2 213 Z. Body-Dopplung (6 identische Saetze).
    Befund: 404 Z. sind zu viel fuer den Prompt. Enthalten
         beides: echte rote Linien (HARD_RULES) + aufgaben-
         spezifische Prozeduren (gehoeren in Skills).
    Ziel: HARD_RULES nur rote Linien (kurz, immer gueltig).
         Aufgabenspezifisches in skills/* auslagern.
         Gate 14 mit 5 Auflagen.
    Scope: Voller Gate-14-Scope (planner, builder, judge).
    Aufwand: 2-3 Tage.

### Block B — Loop-Umbau (3b-2)

B1. Plan-Gate (deterministisch)
    Neue Funktion _plan_gate(state) -> bool.
    Prueft: tasks + tests + akzeptanzkriterien.
    Kein LLM.

B2. Verifier (deterministisch)
    Neue Funktion _verify_patches(state) -> int.
    Ruft tools/quality_gate.py + Tests.
    Kein LLM.

B3. Judge-Loop extrahieren
    run_pipeline body[51] (170 Z., 16 Returns)
    -> _build_verify_judge_loop(...) -> int.
    2 Commits (tot + Body), wie 3a-3.

B4. Reihenfolge umstellen
    Plan -> Plan-Gate -> Build -> Verify -> Judge -> Human.

B5. Chef-Wrapper
    _approval_und_human_gate: Prompt-Sprache "Chef (Agent)"
    statt "Mensch". input() bleibt.
    Nutzt bestehende Subagenten-Infrastruktur (_subagent_lauf).

### Block C — Rollen-Reduktion (3b-3)

C1. Solver entfernen -> deterministischer Deadlock-Checker.
C2. TestGen entfernen -> deterministischer Coverage-Check.
C3. Reviewer (verdict) in Judge konsolidieren.

### Block D — Cross-Vendor + UI (3c, spaeter)

D1. Judge von anderem Vendor als Builder.
D2. UI-Tests (Playwright) als Verifier-Erweiterung.

## Abgrenzung — was NICHT in Block A

- Kein Loop-Umbau (das ist Block B).
- Kein Rollen-Schnitt (das ist Block C).
- Kein Zusammenfuehren der Builder-Dateien (State Machine bleibt).
- Baseline 1245/17/9/6/167 muss nach jedem Block-A-Commit
  gruen bleiben (Delta 0).

## Risiken

- A2 (subprocess) beruehrt 30 Stellen. Jede kann Test-Verhalten
  aendern. Rollback-Anker pro Sub-Block.
- A5 (Builder kuerzen) beruehrt 3 agents/-Dateien.
  Prompt-Verhalten kann sich aendern (kuerzer = weniger
  Kontext, aber weniger Rauschen).
- A6 (HARD_RULES) beruehrt das Gate-14-Design. Braucht
  eigene Mess-Infrastruktur (Test pro Rolle: keine doppelten
  Aussagen).

## Aufwand-Schaetzung

Block A: ~1 Woche (A2 1d, A1 1h, A3 1d, A4 1d, A5 2d, A6 2-3d)
Block B: ~3-4 Tage (B1 0.5d, B2 0.5d, B3 1-2d, B4 0.5d, B5 0.5d)
Block C: ~2 Tage
Block D: spaeter

## Mess-Referenzen (T1-T7)

- T1: 179 Funktionen in pipeline.py, 5 tote (rufe_bash_subagent,
  rufe_browser_subagent, _builder_user_prompt,
  _bauer_no_go_prompt, _bauer_auflagen_prompt).
  werkstatt/: get_run_id (audit.py), _zeilen (commit_input.py).
- T2: 167 Katalog-Kinds, 156 aufgerufen, 11 tot (Liste in A1).
- T3: 30 subprocess.run in pipeline.py.
- T4: 12 Skills, 0 Referenzen im Code.
- T5: 404 Z. HARD_RULES fuer 2 Rollen (reviewer, planner_stufe2).
     6 identische Saetze zwischen agents/*.md und HARD_RULES.
- T6: 15 config.get()-Keys, 5 getenv-Keys.
- T7: 30 _phase*-Funktionen, 4 _commit*, 5 _parse*.
