# Bau-Handoff — Werkstatt

Stand: 2026-10-16 (nach Block P2b-5: Budget-Layer-1 + Plan-Korrektur). P2b fertig.
Werkstatt-HEAD: 6e8b791 (P2b-5)
security-ai-HEAD: 220c6be (Doku-Migration)
Letzter echter Probebetrieb: PB-67 (0d0fe2c, 2026-10-15)
Branch: main (beide Repos)
Tests (Werkstatt): 542 passed
ruff --no-cache: 0
mypy pipeline.py: 0
mypy tests/test_pipeline.py: 15 (vorbestehend, tests-mypy)
mypy tests/test_planner.py: 0
mypy tests/test_projekt_schema.py: 0
mypy tests/test_phase.py: 0
Tests (security-ai): 1334 collected

ARCHIV: historische Eintraege in Bau-Handoff-Archiv.md.

================================================================
WICHTIG — PROBEBETRIEB-DEFINITION
================================================================

Ein Probebetrieb ist NUR ein echter Pipeline-
Durchlauf (pipeline_start + pipeline_ende im
Audit-Log, Projekt security-ai).

Manual-Sessions werden NICHT getaggt.
Die Tags probebetrieb-62 bis -83 (alte Vergabe)
wurden am 2026-10-14 entfernt.

Letzter echter Lauf:
  2026-10-15T16:11-16:11  rc=0  PB-67
  Commit 0d0fe2c (Docstring orchestrator.py).
  Erster echter Lauf nach Phase 1 (Projekt-Schema).
  Runden 1, llm_calls 5, kein Solver-Trigger.

Vorheriger echter Lauf:
  2026-10-14T21:00-21:02  rc=0  PB-62
  Commit 3bb5917 (whois).

Naechster echter Probebetrieb: probebetrieb-68.

================================================================
1. WAS DIE WERKSTATT IST
================================================================

Die Werkstatt ist ein Agenten-System. Sie baut
Projekte, ist aber selbst kein Teil eines Projekts.

Verzeichnis: /opt/werkstatt/
Projekt-Konfigurationen: projects/<name>.yaml
Projekt-Schema: schemas/projekt.yaml
Rollen: agents/
Anti-Pattern-Katalog: anti-patterns/katalog.yaml
Tests: tests/
Doku: docs/

Rollen (6):
  - reviewer (LLM, deepseek-reasoner): prueft Patches
    und Commit-Paket, entscheidet GO/NO-GO/ESKALATION.
  - builder (LLM, deepseek-chat): liefert strukturierte
    Code-Patches (PATCH-BEGINN/ENDE) und das Commit-Paket.
  - solver (LLM): unterstuetzt den Builder bei
    wiederholten NO-GOs.
  - test_generator (LLM): liefert Test-Vorschlaege.
  - coverage (No-LLM): misst Coverage.
  - chaos (No-LLM): fuzzt Extremwerte.

================================================================
2. AKTUELLER ZUSTAND
================================================================

Werkstatt-Repo (/opt/werkstatt):
  HEAD 26a9911 (Doku: Handoff — P2a-Smoke-Test).
  P2a-Commit: e700e4b.
  Tests: 542 passed.
  ruff --no-cache: 0.
  mypy pipeline.py: 0.
  git status: clean.
  Remote: github.com/ghxstfocus/werkstatt.git (privat).

Ziel-Projekt security-ai (/opt/security-ai):
  HEAD 0d0fe2c (PB-67).
  Doku-Migration: 220c6be (siehe Abschnitt 3).
  Tests: 1334 collected.
  ruff: 0.
  mypy: 1353 Fehler (Altlast, no-untyped-def).
  git status: sauber.
  Remote: github.com/ghxstfocus/security-ai.git.

Dateien (Werkstatt):
  - pipeline.py (~6162 Zeilen)
  - redaction.py
  - werkstatt_aggregate.py
  - schemas/projekt.yaml
  - projects/security-ai.yaml
  - agents/*.md (7 Rollen: reviewer, builder, solver,
    test_generator, coverage, chaos, planner)
  - anti-patterns/katalog.yaml (26 Eintraege)
  - tests/test_pipeline.py
  - tests/test_projekt_schema.py
  - tests/test_anti_patterns.py
  - tests/test_aggregate.py
  - tests/test_redaction.py
  - tests/test_planner.py (27 Tests)
  - tests/test_phase.py (17 Tests)
  - docs/WORKFLOW.md (~583 Zeilen)
  - docs/ROADMAP.md
  - docs/PROTOKOLL-29-40.md
  - docs/PLANNER-KONZEPT.md (v4 final)

Ziel-Projekt-Doku (nach Doku-Migration):
  Top-Level: README.md, CHANGELOG.md,
             PROJECT_VISION.md, LICENSE
  docs/: STATUS.md, ROADMAP.md, DECISIONS.md,
         SECURITY_LOG.md, CONVENTIONS.md,
         WORKFLOW (entfernt), ARCHITECTURE.md,
         SECURITY.md, PERMISSIONS.md, PROTOCOL.md,
         DEPLOYMENT.md, WEB_SECURITY_CHECKLIST.md,
         ADMIN_AI_SCOPE.md, INCONSISTENCIES_FOUND.md,
         WERKZEUGE.md, ICONS.md, NTFY.md, README.md

Struktur-Konvention (gilt fuer alle Projekte):
  - README.md (Top-Level) — 30-Sekunden-Ueberblick.
  - CHANGELOG.md (Top-Level) — chronologisch.
  - PROJECT_VISION.md (Top-Level) — Vision.
  - docs/STATUS.md — aktueller Stand.
  - docs/ROADMAP.md — Phasen und Ausblick.
  - docs/DECISIONS.md — Design-Entscheidungen.
  - docs/SECURITY_LOG.md — Sicherheits-Entscheidungen.
  - docs/CONVENTIONS.md — projektspezifische Konventionen.

Status-Icons:
  ✅ abgeschlossen, 🔨 in Arbeit, 💡 geplant,
  ❌ abgebrochen, ⏸ pausiert.

================================================================
3. LETZTE SESSION (2026-10-15)
================================================================

Phase 1 Projekt-Schema (Commit 406e3cc):
  schemas/projekt.yaml (K/O/P/W+O, Defaults,
  Alias-Mechanik), projects/_template.yaml,
  tests/test_projekt_schema.py.
  pipeline.py: pruefe_projekt_yaml (Warn-Modus,
  Fail-Modus via WERKSTATT_SCHEMA_MODUS),
  _lade_und_pruefe_projekt.

Phase 3a-1 Anti-Pattern-Bibliothek (Commit 1ed875a):
  anti-patterns/katalog.yaml (7 Eintraege),
  anti-patterns/README.md, pipeline.lade_anti_patterns
  + anti_patterns_fuer, _AUDIT_KINDS_BEKANNT.

Phase 3a-2 Anti-Pattern-Katalog (Commit 8ed6cd0):
  Katalog auf 26 Eintraege erweitert.

Phase 3b Builder-Injektion (Commit 04012f6):
  _anti_pattern_block, _ap_trigger_grund_aus_state,
  Zwei-Stufen-Sortierung (spezifisch vor Fallback).

Phase 3c-1/2/3 Reviewer + Solver Injektion
(Commits 4916b01, 045556e, b84ee8e, d0a9bad):
  - 3c-1: Solver-Rolle zu 6 Anti-Patterns.
  - 3c-2: Reviewer-Injektion in build_system_prompt.
  - 3c-3: Solver-Injektion in rufe_solver
    (trigger_grund, aufrufer).

Erster echter Pipeline-Lauf PB-67:
  Commit 0d0fe2c in security-ai, Tag probebetrieb-67.
  Commit-Message: "docs: Docstring in
  _build_default_registry entkoppelt".
  Inhalt: Docstring orchestrator.py korrigiert
  (Punkt 94).
  Runden 1, llm_calls 5, kein Solver-Trigger.
  Tag probebetrieb-67 gesetzt.
  Damit ist die Bedingung fuer Phase 1b erfuellt.

Block P1 (Planner-Rolle + _planner_lauf):
  ERLEDIGT 2026-10-15. Commit 9544c7e.
  agents/planner.md (73 Zeilen).
  HARD_RULES_PLANNER (P1-P9),
  PLANNER_BLOCK_PRAEFIXE,
  HARD_RULES_BY_ROLE["planner"].
  RunState: planner_model, planner_vorschlag,
  planner_modus, planner_runden.
  parse_planner_reply, _planner_lauf,
  _planner_main_pfad.
  main() --planner-Pfad.
  Minimales Basis-Gate (Projekt + git clean).
  Rueckfrage-Loop, Bestaetigung [j]/[n]/[e].
  projects/security-ai.yaml: agent_docs.planner
  + planner-Block.
  schemas/projekt.yaml: planner-Schema.
  tests/test_planner.py (19 Tests).
  514 passed.

Planner-Konzept v4 (final):
  Commit da80b1f. docs/PLANNER-KONZEPT.md.
  Alle 40 Praezisierungen aus 3 Reviewer-
  Durchlaeufen eingearbeitet.

P1-Live-Test (2026-10-15, nach Commit 9544c7e):
  Erster echter --planner-Lauf.
  Rohauftrag: "Schau dir den aktuellen
  Projektstand an und plane den naechsten
  sinnvollen Bau-Auftrag."

  Ergebnis:
    - Planner-Runde 1: Auftrag formuliert
      (Punkt 26 aus SECURITY_LOG: security_ai-
      Startpfad, __main__.py + systemd-Unit).
    - Bestaetigung [j]: Lauf startet.
    - Basis-Gate: gruen.
    - Builder-Runde 1-3: kein Patch, nur
      COMMAND-Zeilen (Rueckfragen zur Messung).
    - Deadlock: builder_command_deadlock.
    - Recovery: Reviewer diagnostiziert
      "Zuschnitt-Fehler".
    - Kein Commit in security-ai.
    - security-ai unveraendert 0d0fe2c.

  Erkenntnis:
    - P1 funktioniert im Live-Betrieb.
    - Der Planner hat den Ist-Zustand korrekt
      gelesen und einen sinnvollen Auftrag
      formuliert.
    - ABER: Der Auftrag war zu gross (6 Schritte,
      7-9 Dateien, Betriebsakt in einem Block).
    - Der Builder misst korrekt und endlos,
      kommt aber nie zum Bauen.
    - Das ist genau der Zuschnitt-Fehler, den
      P2 (Phasen-Modus) loesen soll.
    - Bestaetigt: P2 ist dringender als gedacht.

  Reviewer-Recovery-Vorschlag (im Audit):
    Vier Bloecke:
      1. Bestandsaufnahme (Kategorie 1, nur lesen).
      2. __main__.py + Tests (Kategorie 3).
      3. systemd-Unit + Doku (Kategorie 1/2).
      4. Betriebsakt systemctl (Kategorie 3,
         eigener GO, eigener Rollback).
    Faustregel: hoechstens EIN neuer Code-Pfad
    pro Block; systemd-Start nie im selben Block
    wie der Code; Erkundung nie im selben Block
    wie Bau.

Doku-Migration (Werkstatt 254b3fb,
security-ai 220c6be):
  - Profi-Konvention: PHASES -> ROADMAP,
    DESIGN_DECISIONS -> DECISIONS,
    SECURITY_REVIEW_LOG -> SECURITY_LOG,
    WORKFLOW -> CONVENTIONS.
  - Neue Dateien: docs/STATUS.md, CHANGELOG.md.
  - Entfernt: docs/CONTEXT_PROMPT.md,
    docs/REVIEWER_HANDOFF.md.
  - Werkstatt-WORKFLOW um 9 Abschnitte erweitert.
  - Alias-Mechanik datengetrieben (Schema als
    einzige Quelle).

Block P2a (Phasen-Modus Fundament):
  ERLEDIGT 2026-10-15. Sieben Teilschritte.
  Basis: HEAD e8a01a4 (P1-Live-Test-Doku).
  Commit: e700e4b ("P2a: Phasen-Modus Fundament —
  Datenmodell, Parser, Persistenz, CLI").
  Folge-Commits: 7186363 (Werkstatt-Regel projects/-
  Owner), 26a9911 (Handoff P2a-Smoke-Test).

Block P2b-1 (run_phase-Geruest + Status-Helfer):
  ERLEDIGT 2026-10-16. Commit 770fbea.
  Reviewer: GO-mit-Auflagen (P2b-Zuschnitt).
  Reihenfolge (Reviewer F3): Rollback VOR
  Phasen-Modus. Daher P2b-2 = Rollback.

  Aenderungen:
    - _AUDIT_KINDS_BEKANNT +8 (phase_abgebrochen,
      phase_commit_paket_gesammelt,
      phase_gesamt_review, phase_rollback,
      phase_unterblock_ende, phase_unterblock_start,
      run_phase_ende, run_phase_start).
    - _phase_yaml_status_update neu (liest via
      _phase_plan_laden, patcht status, ruft
      _phase_plan_speichern; Fail-closed ValueError).
    - run_phase neu (Loop ueber phase_unterbloecke,
      pending->running->done, phase_aktueller_index,
      Audit-Kette, Idempotenz-Schutz, Stub statt
      run_pipeline mit TODO(P2b-3)).
    - _phase_main_pfad: Andock an run_phase
      (Z. ~5821).
  Tests: 542 -> 555. test_phase.py +13.
  Kein Probebetrieb-Tag (F7: PB-68 erst nach P2b-4).

Block P2b-2 (Rollback + phase_start_head):
  ERLEDIGT 2026-10-16. Commit 95b2671.
  Reviewer: GO-mit-Auflagen (P2b-2-Zuschnitt).

  Aenderungen:
    - _AUDIT_KINDS_BEKANNT +1
      (phase_start_head_gesetzt).
    - _git_rev_parse_head (neu): git rev-parse HEAD,
      "" bei Fehler.
    - _git_status_porcelain (neu): git status
      --porcelain, "!FEHLER!" bei Fehler.
    - _phase_rollback (neu): RR-K1/K2/K3.
      Best-Effort (F6): faengt Exception, gibt False.
      Rueckgabe bool (F4), kein rc.
      state.phase_commit_pakete wird geleert (F5).
    - run_phase: phase_start_head-Synchronisation
      vor run_phase_start (YAML gewinnt, wenn != "").
  Tests: 555 -> 570. test_phase.py 30 -> 45.
  Kein Probebetrieb-Tag.
  Rollback-Aufruf folgt P2b-3 (Exception-Pfad) und
  P2b-4 (Phase-NO-GO).

Block P2b-2-A7 (Fail-closed phase_start_head):
  ERLEDIGT 2026-10-16. Commit fd34f5d.
  Reviewer-Nachtrag zu P2b-2 (K2 aus P2b-3).
  run_phase prueft jetzt vor dem phase_start_head-
  Setzen: yaml_head == "" UND state != "" ->
  ValueError. Plus mypy-Fix (_state-Rueckgabetyp
  in test_phase.py).
  Tests: 570 -> 571.

Block P2b-3 (run_pipeline-Phasen-Modus):
  ERLEDIGT 2026-10-16. Commit 85e0572.
  Reviewer: GO-mit-Auflagen (P2b-3-Zuschnitt).

  Aenderungen:
    - _AUDIT_KINDS_BEKANNT +1
      (phase_commit_paket_leer).
    - run_pipeline-Signatur: *, phasen_state=None
      (keyword-only).
    - Docstring fuer phasen_state.
    - phasen_state-Guard beim RunState-Bau:
      state_ref muss leer sein, sonst ValueError.
    - Phasen-Modus vor Schritt 6:
      state.phase_aktiv True -> Paket sammeln
      (Audit phase_commit_paket_gesammelt) +
      return 0.
      Leeres Paket -> rc=21 (Audit
      phase_commit_paket_leer).
    - apply_commit_and_doku unveraendert.
  Tests: 571 -> 575. test_phase.py 46 -> 50.
  Loop-Aufruf folgt in P2b-3b.

Block P2b-3b (Loop-Aufruf in run_phase):
  ERLEDIGT 2026-10-16. Commit af45157.
  Reviewer: GO-mit-Auflagen (P2b-3b-Zuschnitt).

  Aenderungen:
    - run_phase-Signatur:
      (project_name, state, state_ref) -> int.
    - state_ref-Guard (ValueError wenn nicht leer).
    - Loop-Koerper: Stub ersetzt durch
      run_pipeline(phasen_state=state),
      lokaler sr_intern pro Aufruf,
      Vertragspruefung sr_intern[0] is state.
    - Vier rc-Klassen (L3):
        Klasse 1: rc=0 + Paket -> done, weiter.
        Klasse 2: rc=0 ohne Paket -> B2,
                  done, weiter.
        Klasse 3: rc=15 -> no_go, Loop-Abbruch,
                  KEIN Rollback.
        Klasse 4: sonst -> failed + Rollback,
                  rc zurueck.
    - Exception im Loop -> Rollback, rc=22.
    - state_ref.append(state) am Ende
      (nur im Erfolgspfad).
    - _phase_main_pfad-Aufruf angepasst.
  Tests: 575 -> 583. test_phase.py +8.
  Merkposten NA3: run_pipeline B2-Signal im
  state (siehe Abschnitt 4).

Block P2b-4 (Phasen-Gesamt-Review + Sammel-Commit):
  ERLEDIGT 2026-10-16. Commit 16eec88.
  Reviewer: GO-mit-Auflagen (P2b-4-Zuschnitt).

  Aenderungen:
    - _phase_gesamt_review (deterministisch).
    - _phase_sammel_message (Commit-Message-Format).
    - _phase_sammel_paket (Union aller Pakete).
    - _print_phase_approval_dokument.
    - run_phase: Gesamt-Review + Approval [j]/[n]
      + Sammel-Commit via apply_commit_and_doku.
    - _phase_main_pfad: phase_aktiv=False nach
      erfolgreichem run_phase.
  Tests: 583 -> 592.
  Kein Probebetrieb-Tag (F7: PB-68 erst nach
  P2b-5).

Block P2b-5 (Budget-Layer-1 + Plan-Korrektur):
  ERLEDIGT 2026-10-16. Commit 6e8b791.
  Reviewer: GO-mit-Auflagen (P2b-5-Zuschnitt).

  Aenderungen:
    - _AUDIT_KINDS_BEKANNT +3 (phase_budget_ende,
      phase_plan_korrektur_failed,
      phase_plan_korrektur_start).
    - _planner_user_content + korrektur_kontext.
    - _planner_lauf + korrektur_kontext.
    - _phase_rr_k8 (neu): RR-K8-Menue [1]/[2]/[3].
    - _phase_plan_korrektur (neu): Planner-Korrektur.
    - run_phase: korrektur_zyklus (keyword-only),
      Budget-Check vor jedem Unterblock (rc=13),
      Plan-Korrektur im [n]-Zweig (max 1 Zyklus).
    - conftest.py: autouse DEEPSEEK_API_KEY-Fixture.
  Tests: 592 -> 602.
  P2b ist damit FERTIG.

  Teilschritte:
    1. RunState + 7 phase_*-Felder.
    2. _parse_phase_plan (P10-P14-Format).
    3. _phase_plan_laden/_speichern (atomar, 0600).
       .gitignore: projects/*.phase.yaml +
       projects/.*.tmp.*
    4. HARD_RULES_PLANNER_STUFE1/STUFE2.
       P1-P9 wortgleich in STUFE1. STUFE2:
       P1', P2, P3', P4', P5, P6, P8, P9',
       P10-P14. Alias HARD_RULES_PLANNER auf
       STUFE1.
    5a. _parse_phase_kopf + build_system_prompt
        stufe-Parameter (keyword-only) +
        _planner_lauf stufe-Parameter +
        _planner_user_content.
    5b. _phase_main_pfad + main() --phase +
        Audit-Kinds phase_plan_erstellt,
        phase_plan_parse_failed,
        phase_plan_verworfen.
    5c. Konflikt-Check --phase/--planner (rc=65)
        + _phase_plan_als_text (Roundtrip)
        + _phase_edit_modus (nur Titel/Runden)
        + Audit-Kind phase_plan_editiert
        + letzter_vorschlag-Mechanik.
    6. agents/planner.md: Stufe-1/Stufe-2-Sektionen.
    7. projects/security-ai.yaml +
       schemas/projekt.yaml: planner.phasen_modus,
       budget.max_llm_calls_phase (Deklaration).

  Tests: 514 -> 542 (+28).
  Reviewer-Auflagen: P2a-A1..A14, P2a-S1..P2a-S6-7
  (alle eingearbeitet).
  Kein Probebetrieb-Tag (kein echter Pipeline-
  Durchlauf; der Phasen-Loop ist erst in P2b
  funktional).

  Smoke-Test (2026-10-15, kein Tag):
    Aufruf: pipeline.py --project security-ai
            --phase "Baue eine kleine Testphase ..."
    Ergebnis: erfolgreich.
      - Planner Stufe 2 liefert korrektes P10-P14-
        Format.
      - Anzeige korrekt (Phase-Titel, U1 mit 5
        Unterpunkten, U2 mit 4 Unterpunkten,
        (Runde 1/3)).
      - [j] schreibt projects/security-ai.phase.yaml
        atomar, mode 0600, owner builder:builder.
      - Audit-Kette vollstaendig: pipeline_start
        -> planner_start (stufe=2) ->
        planner_vorschlag -> phase_plan_erstellt
        -> pipeline_ende (rc=0).
      - .gitignore-Schutz greift (git status leer).
      - Kein tmp-Zombie.
    Deployment-Regression entdeckt:
      projects/ war faelschlich root:root (Phase-1-
      Commit 406e3cc hatte den Owner versehentlich
      ueberschrieben). Reparatur: chown
      builder:builder + chmod 750. Werkstatt-Regel
      im Handoff ergaenzt.
    Qualitaets-Beobachtung (wichtig fuer P2b):
      Der Planner liefert praezise Unterpunkte mit
      Datei, Testpfad, Verifikationskommandos und
      Doku-Nachzug. Der Loop in P2b kann sich auf
      'unterpunkte' als Bau-Auftrag verlassen.

================================================================
4. OFFENE MERKPOSTEN
================================================================

KRITISCH: keine.

WICHTIG:

  Block P2a (Phasen-Modus Fundament):
        ERLEDIGT 2026-10-15. Siehe Abschnitt 3.
        Commit: "P2a: Phasen-Modus Fundament".

  Block P2b-1 (run_phase-Geruest): ERLEDIGT.
        Commit 770fbea. Siehe Abschnitt 3.

  Block P2b-2 (Rollback + phase_start_head):
        ERLEDIGT. Commit 95b2671. Siehe Abschnitt 3.

  Block P2b-3 (run_pipeline-Phasen-Modus):
        ERLEDIGT. Commit 85e0572. Siehe Abschnitt 3.

  Block P2b-3b (Loop-Aufruf in run_phase):
        ERLEDIGT. Commit af45157. Siehe Abschnitt 3.

  Merkposten (P2b-3b-A4-NA3): run_pipeline B2-Fall
        B2 ist heute nur per Audit
        (auftrag_bereits_erfuellt) und rc=0
        erkennbar. run_phase nutzt die strukturelle
        Heuristik rc=0 ohne Paket = B2
        (P2b-3b-A4). Wenn run_pipeline weitere
        rc=0-Pfade ohne Paket bekommt, MUSS die
        Heuristik durch ein state-Feld (z.B.
        state.b2_erreicht: bool) ersetzt werden.
        Eigener Block, nicht in P2b.

  Block P2b-4: ERLEDIGT. Commit 16eec88.

  Block P2b-5: ERLEDIGT. Commit 6e8b791.

  P2b ist FERTIG. Naechster Meilenstein:
        PB-68 (erster echter Phasen-Lauf).
        Kategorie 3 (echter Lauf, Commit in
        security-ai).
        Bedingung F7 erfuellt.
        Vorsicht: der Lauf committet in
        security-ai. Auftrag klein halten.

  Planner-Portionierung (Zwischenloesung):
        OFFEN. Falls P2 zu gross ist, reicht
        evtl. eine Zwischenloesung: der Planner
        liefert bei grossen Auftraegen eine Liste
        von Unterauftraegen, und der main-Pfad
        ruft run_pipeline mehrfach auf. Das waere
        eine vereinfachte Form des Phasen-Modus
        ohne Persistenz, Gesamt-Review, atomaren
        Rollback. Diskussion in naechster Session.

  Block P3 (ASK_HUMAN + Persistenz):
        OFFEN. Nach P2. Kategorie 3.
        Datei-basiert (ask-human/<run_id>).
        Timeout 60 min.

  Rollen-Modell aus Frontmatter lesen:
        OFFEN. Bestehende Inkonsistenz:
        agents/*.md Frontmatter liefert
        model/temperature, wird aber nicht
        vom Code gelesen. Alle *_model-Felder
        in pipeline.py sind hartcodiert.
        Eigener Block, Kategorie 2.
        Anlass: P1, SS7-(C).

  Phase 1b (Validator Fail-closed): BEREIT.
        WERKSTATT_SCHEMA_MODUS Default ist warn
        (pipeline.py:478). PB-67 (2026-10-15) ist
        der erste echte Lauf nach Phase 1, Warn-
        Modus ohne Warnung durchgelaufen. Bedingung
        erfuellt.
        Naechster Schritt: Kategorie-3-Reviewer-Block,
        dann Default auf fail umstellen. Kategorie 3
        (bestaetigt vom Reviewer-Chat 2026-10-15).

  Solver-Kurskorrektur Block 6 (Smoke-Test): OFFEN.
        Echter Solver-Lauf im Deadlock- und
        Phase-1-Trigger-Pfad. Nach PB-67 oder
        spaeter. Kategorie 3.

  2183-AQ (Auftragsqualitaet vor Werkstatt-Lauf):
        Auftraege gegen Zielcode pruefen, bevor
        ein Lauf startet. Auftraege, die Verhalten
        annehmen, das im Zielcode nicht existiert,
        enden in Livelock oder Deadlock.
        Kategorie 3.

  2199a (Recovery-Pfad post-apply-Basis-Gate):
        Zustandsmaschine klaeren:
          - Recovery-Lauf vs. normaler Builder-Lauf.
          - Zaehlung in state.review_runden?
          - Reviewer sieht Recovery als neue Runde?
          - max_llm_calls-Zaehlung.
        Dann Recovery-Zweig bauen. Max 1 Zyklus.
        Kategorie 3.

  Werkstatt-Vertrag (2183). Kategorie 3.
        Fuenf Vertraege zusammenfuehren:
          1. Anker-Vertrag.
          2. Auftrags-Vertrag.
          3. Patch-Vertrag.
          4. Fail-Vertrag.
          5. Rollen-Vertrag.
        Format: docs/WERKSTATT-VERTRAG.md + .yaml.
        Offene Design-Fragen W1-W4 im Archiv.

  B2 — Builder-Kanal fuer Solver-Befund.
        praezisierter_auftrag landet heute nur in
        state.solver_befunde und im Reviewer-Prompt.
        Der Builder sieht ihn nicht. Kategorie 3.

  _WERKSTATT_PROJECTS_DIR (aus P2a-S3-A8):
        Path("/opt/werkstatt/projects") inline in
        memory.yaml-Pfad + _PHASE_YAML_DIR in P2a
        sind zwei Stellen. Zusammenfuehren in eine
        Konstante. Kategorie 2.

  ruff TRY004 vs. Auflage ValueError (P2a-S3-NA-A5):
        In _phase_plan_laden bewusst # noqa: TRY004,
        weil P2a-A7 explizit ValueError fordert.
        Bei haeufigerem TRY004 in spaeteren Bloecken:
        Werkstatt-Konvention statt 4x # noqa.

  Resume/Schutz alter phase.yaml (aus P2a-S5b-3):
        5b/5c pruefen NICHT, ob eine alte phase.yaml
        existiert, und loeschen nichts. Resume
        gehoert in einen eigenen Block (Konzept 9.2).

  Gemeinsame Basis _planner_main_pfad +
  _phase_main_pfad (aus P2a-S5b-F4):
        Bewusste Duplikation in P2a. Spaeter pruefen,
        wenn weitere Pfade dazukommen (P3,
        Scaffolder). Kategorie 2.

MITTEL:

  _AUDIT_KINDS_BEKANNT: manuell pflegen.
        Neue kind-Werte im Audit-Log muessen in
        pipeline.py ergaenzt werden, sonst
        schlaegt die Katalog-Validierung fehl.
        Merkposten: automatische Ableitung pruefen.

  ap-string-literal-statt-konstante:
        Bau-Chat-Befund. Bei der naechsten
        Katalog-Durchsicht pruefen, ob weitere
        Bau-Chat-Befunde in Eintraege umgewandelt
        werden.

  tests-mypy: 15 Fehler (nicht mehr 151).
        In tests/test_pipeline.py, Zeilen
        3583-3608 (code_entwurf_historie) und
        4147 (append return value). Vorbestehend.
        Eigener Block. Kategorie 2.

  II2b (Substring-Kollision): Ersatz-Pruefung
        nutzt Substring-Match. Bei erster realer
        Kollision: Wortgrenzen oder exakter Match.

  II5b (Audit-Fuss-Kuerzung): _audit_builder_
        reply kuerzt Fuss auf 200 Zeichen.
        Vorschlag: auf redigiert[-1000:] erweitern.

  II6b (Inhaltswort-Kalibrierung): Liste
        INHALTSWOERTER_TRIGGER_B nach 5-10
        PB-Laeufen kalibrieren.

  F2 (Fail-closed bei rufe_solver-Fehler):
        max_rufe_solver_fehler = 2 nach
        5-10 PB-Laeufen mit Solver kalibrieren.

  F3 (Fail-closed bei unvollstaendigem Befund):
        Bleibt (a): leerer Block + Audit.
        Fail-closed nur bei Quote >20%.

  F4 (_bauer_auflagen_prompt): DD5 bleibt.
        Ueberdenken, wenn Auflagen-Pfad haeufiger
        failt.

  B5-M1 (Historie-Block Umfang): Solver-Prompt
        zeigt nur DIAGNOSE, nicht Volltext.
        Nach ersten PB-Laeufen pruefen.

  B5-M2 (Trigger-Pfad-Test): voller Test
        ausstehend.

  Solver-Kurskorrektur Merkposten:
        W10 (Befund-Historie), W12 (Rollen-Vertrag),
        P4-nach-Solver (max_llm_calls neu messen),
        max_solver_runden-Kalibrierung (3 ist
        Setzung), solver_befunde-Eingrenzung,
        Audit-Kanal Solver-UNKLAR.

  U4-Kalibrierung (P1): Schwellwert 0.5 und
        min_tokens 10 sind Setzungen. Nach ersten
        PB-Laeufen labeln und neu setzen.

  P4-nach-P1-B (llm_calls): P1 reduziert den
        Trigger. Wirkung nicht gemessen. Nach
        Solver-Nutzung neu messen.

  docs-Migration Rollen-Prompt-Generator
        (Phase 3.5): mittelfristig docs/*.md
        durch generierte Rollen-Prompts ersetzen.

NIEDRIG:

  2187b: read_file Zeilenbereich.
  2188a: agents/*.md konsolidieren.
  2188c, 2189c, 2190b-M, 2191-M2, 2192-M2,
  2198-M, 2198-M2: Feature + Prompt + Aktualisierung
        konsolidieren.
  2190-M: Reviewer-Auswahl-Logik pruefen.
  2192-M1: execute_commands prueft, ob Pfad schon
        vollstaendig gemessen.
  2195-M2: MAC-Redaction rechtfertigen oder entfernen.
  2195-M3: Anker mit gemischten privaten/oeffentlichen IPs.
  2191-R2b-T: Test fuer commit_review_ohne_messung.
        Test-Harness bauen. Kategorie 2.
  2191-R4: Builder-Prompt vs. Reviewer-Prompt
        (GEMESSENER INHALT Position). Kategorie 2.
  Phase-2-COMMAND-Schleichpfad: classify_verdict
        erkennt COMMAND in Phase 2, Loop bricht
        ab. Kein Fail, kein Log. Merkposten.
  Audit-Log-Ausbau dauerhaft.
  Tag-Verwirrung vereinheitlichen.

================================================================
5. ERLEDIGTE MERKPOSTEN (KURZREFERENZ)
================================================================

Detaillierte Beschreibungen in Bau-Handoff-Archiv.md,
Abschnitt B.

  2183 A1a, A1b, A1c, A2, A3, A4/A5, B, C
       (Solver-Kurskorrektur, alle erledigt).
  2183-B3, 2183-B5 (Solver-Wissensbasis, -Loop).
  2183-P4-Log2 (pipeline_ende-Wrapper).
  2184 (max_llm_calls 30).
  2185 (README komplett).
  2186-2198 (Auflagen 2026-10-12 bis -13).
  2199, 2199-R7-P2 (ABGESCHLOSSEN).
  2200, 2200a, 2200c, 2200-T.
  Agent-Memory Ebene 1 (Commits 4e23aba, 52cd658).
  Stufe 0 (Commits b5f3073 bis 737afe9).
  Auftrag bereits erfuellt (Commits a0d436b bis 3cf7404).
  Phase 1 Projekt-Schema (Commit 406e3cc).
  Phase 3a-1 (1ed875a), 3a-2 (8ed6cd0), 3b (04012f6).
  Phase 3c-1 (4916b01), 3c-1b (045556e),
    3c-2 (b84ee8e), 3c-3 (d0a9bad).
  Doku-Migration (Werkstatt 254b3fb,
    security-ai 220c6be).
  Block P1 (Planner-Rolle + _planner_lauf,
    Commit 9544c7e).
  Block P2a (Phasen-Modus Fundament,
    Commit "P2a: Phasen-Modus Fundament").
  Block P2b-1 (run_phase-Geruest + Status-Helfer,
    Commit 770fbea).
  Block P2b-2 (Rollback + phase_start_head,
    Commit 95b2671).
  Block P2b-2-A7 (Fail-closed phase_start_head,
    Commit fd34f5d).
  Block P2b-3 (run_pipeline-Phasen-Modus,
    Commit 85e0572).
  Block P2b-3b (Loop-Aufruf in run_phase,
    Commit af45157).
  Block P2b-4 (Phasen-Gesamt-Review + Sammel-
    Commit, Commit 16eec88).
  Block P2b-5 (Budget-Layer-1 + Plan-Korrektur,
    Commit 6e8b791).

================================================================
6. ZIELE
================================================================

Ziel 1 — Autonomie bis Approval.
        Die Werkstatt soll grosse Arbeitspakete
        eigenstaendig abarbeiten. Mensch nur am
        Approval-Gate.

Ziel 2 — Deterministisch vor LLM.
        Regel entscheidet, wo moeglich.

Ziel 3 — Ordner-/Doku-Schema + Scaffolder.
        Vorlage fuer neue Projekte, Migration
        bestehender. Struktur-Konvention jetzt
        dokumentiert.

Ziel 4 — Dashboard (spaeter).
        Web-Ansicht des Prozesses, Live-Log,
        Konversation zwischen LLMs, ASK_HUMAN-Kanal.

Ziel 5 — Anti-Pattern-Bibliothek.
        ERLEDIGT fuer 3 Rollen (Builder, Reviewer,
        Solver). Aggregator-Vorschlaege noch offen.

Ziel 6 — Planner-Agent (spaeter).
        Liest Roadmap des Ziel-Projekts, formuliert
        Auftraege, Uebergabe an Reviewer.
        Voraussetzung: Ziel 3 + Roadmap-Format.

================================================================
7. WIE MAN WEITERARBEITET
================================================================

Regeln fuer jeden Bau-Block:

1. Faktenlage vor Meinung. Kein Inhalt annehmen.
2. Patch per Python-Skript mit assert count == 1.
   Kein sed auf Python-Code.
   Heredoc nur bis ~40 Zeilen. Laenger: Skript in
   /tmp anlegen, dann per write_text schreiben.
3. Nach jedem Patch: wc -l, py_compile, ruff,
   mypy, pytest.
4. Vor jedem Commit: git status --porcelain.
5. Commit-Autor: ghxstfocus <ghxst.focus@gmail.com>.
6. Bei Kategorie 3: Reviewer-Block vor Commit.
6a. Probebetrieb-Tag NUR bei echtem Pipeline-
    Durchlauf (pipeline_start + pipeline_ende).
7. Nach jedem Meilenstein: Handoff aktualisieren.
8. Reviewer-Blocks in Codeblock.
9. Kein Scope-Creep. Jede Auflage eigener Block.
10. Am Ende: git status sauber, Handoff aktuell.

Werkstatt-Regel: ruff --no-cache messen.
Werkstatt-Regel: mypy rekursiv pruefen.
Werkstatt-Regel: bei Import-Sortierung ruff --fix.
Werkstatt-Regel: /opt/werkstatt/projects/ gehoert
                 builder:builder 750 (Pipeline-User
                 schreibt dort Laufzeit-State). Nach
                 root-Eingriffen pruefen.

================================================================
8. WERKZEUGE UND BEFEHLE
================================================================

ruff:   /opt/security-ai/.venv/bin/python3 -m ruff check ... --no-cache
mypy:   /opt/security-ai/.venv/bin/python3 -m mypy ...
pytest (aus /opt/werkstatt):
        /opt/security-ai/.venv/bin/python3 -m pytest tests/ -q

Werkstatt-Lauf (aus /opt/security-ai als builder):
  set -a
  . /opt/security-ai/.env
  set +a
  cd /opt/security-ai && \
  runuser -u builder -- env DEEPSEEK_API_KEY="$DEEPSEEK_API_KEY" \
    /opt/security-ai/.venv/bin/python3 \
    /opt/werkstatt/pipeline.py \
    --project security-ai \
    "<Block-Auftrag>"
  unset DEEPSEEK_API_KEY

Git-Commit mit Autor:
  git -c user.name="ghxstfocus" \
      -c user.email="ghxst.focus@gmail.com" \
      commit -F /tmp/msg.txt

================================================================
9. GIT-STATUS
================================================================

Werkstatt-Repo: /opt/werkstatt/.git
  Branch: main
  Remote: git@github.com:ghxstfocus/werkstatt.git
  .gitignore: Cache, .venv, audit-logs/,
              approvals/*.db, *.env,
              projects/*.memory.yaml, *.alt.

Ziel-Projekt (security-ai): /opt/security-ai/.git
  Branch: main
  Remote: git@github.com:ghxstfocus/security-ai.git

Hinweis: Werkstatt-Lauf braucht Schreibrechte des
builder-Users im Ziel-Projekt. Nach manuellen
git-Eingriffen als root: chown builder:builder pruefen.

================================================================
10. HARD RULES
================================================================

Rollenspezifisch getrennt (Auflage 2182):
  - HARD_RULES_BASE (universell).
  - HARD_RULES_REVIEWER (R1-R7).
  - HARD_RULES_BUILDER (B1-B10).
  - HARD_RULES_TEST_GENERATOR (T1-T4).
  - HARD_RULES_SOLVER (S1-S7).
build_system_prompt waehlt anhand des Agent-Namens.
Quelle: pipeline.py.

Die Chat-Regeln (HR-R1..R10) und Antwortformate
sind Zwei-Webchat-Artefakte. Sie sind im Archiv.
Die Werkstatt hat sie durch HARD_RULES_REVIEWER
und classify_verdict abgeloest.

================================================================
11. NAECHSTE SCHRITTE (konkret)
================================================================

Der neue Bau-Chat soll:

1. Diesen Handoff lesen. HEAD pruefen:
     git -C /opt/werkstatt log -1 --oneline
     git -C /opt/werkstatt status --porcelain
     /opt/security-ai/.venv/bin/python3 -m pytest \
       /opt/werkstatt/tests/ -q

2. Reihenfolge:
   a) Block P2: --phase + run_phase + Gesamt-Review.
      Naechster Block. Stufe 2 des Planner-Konzepts.
      Kategorie 3.
   b) Block P3: ASK_HUMAN + Persistenz.
      Kategorie 3.
   c) Phase 1b: Validator Fail-closed.
      Nach P2/P3. Kategorie 3.
   d) Solver-Kurskorrektur Block 6 (Smoke-Test).
      Echter Solver-Lauf.
   e) Phase 2: Scaffolder.
   f) Rollen-Modell aus Frontmatter lesen.
      Kategorie 2.
   d) Rollen-Prompt-Generator (Phase 3.5).
   e) Agent-Memory Ebene 2.
   f) Ziel 2: Phasen-Modus.
   g) Ziel 4: Dashboard.
   h) 2183-AQ, 2199a, Werkstatt-Vertrag, B2.

3. Fuer Kategorie-3-Bloecke: Reviewer-Block
   formulieren, vor Ausfuehrung.

4. Nach Erfolg (NUR echter Pipeline-Durchlauf):
   git tag probebetrieb-<n>. Naechste Nummer: 68.

5. Bei Problemen: zurueck zu diesem Handoff,
   Faktenlage pruefen, Reviewer-Chat fragen.

================================================================
ENDE DES HANDOFFS
================================================================
