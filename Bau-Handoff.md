# Bau-Handoff — Werkstatt

Stand: 2026-10-16 (nach Post-Apply-Fix + Lauf 12; zwoelf PB-68-Laeufe, keine erfolgreicher Sammel-Commit)
Werkstatt-HEAD: 707f964 (Handoff Sitzung 2026-10-16) + Handoff-final-Commit
security-ai-HEAD: 0d0fe2c (PB-67; Working Tree clean nach Lauf-12-Reset; kein Sammel-Commit)
Letzter echter Probebetrieb: PB-67 (0d0fe2c, 2026-10-15). PB-68 noch offen: zwoelf Laeufe, kein Sammel-Commit erreicht.
Branch: main (beide Repos)
Tests (Werkstatt): 707 passed
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
WICHTIG FUER DEN NEUEN CHAT (Uebergabe 2026-10-16):
================================================================

Dieser Handoff ist am Ende einer sehr langen
Sitzung (2026-10-16) entstanden. Zwoelf PB-68-
Laeufe, kein erfolgreicher Sammel-Commit, aber
viele fundamentale Werkstatt-Fixes.

Bevor der neue Chat arbeitet:
  1. Werkstatt-HEAD pruefen:
       git -C /opt/werkstatt log -1 --oneline
  2. Tests laufen lassen:
       /opt/security-ai/.venv/bin/python3 -m
       pytest /opt/werkstatt/tests/ -q
     Erwartung: 707 passed.
  3. security-ai pruefen:
       git -C /opt/security-ai log -1 --oneline
       git -C /opt/security-ai status --porcelain
     Erwartung: 0d0fe2c, clean.
  4. phase.yaml pruefen:
       head -6 /opt/werkstatt/projects/
       security-ai.phase.yaml
     Erwartung: phase_aktiv=true, U1=no_go.

Der naechste Bau-Block:
  Plan-Konkretisierung. Reviewer-Block wird in
  dieser Sitzung formuliert, im neuen Chat
  eingereicht. Kategorie 3, Reviewer-Freigabe
  einholen.

Der Reviewer-Chat wechselt mit:
  Der neue Chat muss dem Reviewer mitteilen:
  'Neuer Bau-Chat, Uebergabe 2026-10-16. Stand:
   siehe Bau-Handoff, HEAD 707f964+.'
  Der Reviewer fuehrt seinen eigenen Kontext
  (alle getroffenen Entscheidungen); er braucht
  nur den Uebergabe-Hinweis.

Naechster echter Probebetrieb: PB-68 (nicht
  PB-67 nochmal). Erst nach erfolgreichem
  Sammel-Commit taggen.

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

Sitzung 2026-10-16 (nach P2b):
  Ziel: erster echter Phasen-Lauf (PB-68).
  Ergebnis: elf Laeufe, kein erfolgreicher
  Sammel-Commit. Aber: viele fundamentale
  Bugs gefunden und gefixt.

  PB-68-Laeufe und ihre Befunde:
    1-5: Resume-Pfad, state_ref, build_catalog,
         NEW_FILE-Format, Solver-Trigger.
    6:   Builder-Rueckfrage als Fliesstext
         statt COMMAND: frage_reviewer.
    7:   Planner lieferte Roadmap-Themen
         statt baubare Bloecke.
    8:   state.aufgabe im Phasen-Modus
         zeigte Phasen-Gesamttext.
    9:   builder.md nannte nur typ: patch,
         nicht typ: new_file im Kopf.
    10:  Anker-Pruefung lehnte korrekte
         typ: new_file-Patches ab.
    11:  Erste Code-GO + Apply. Post-Apply-
         Basis-Gate rot (ruff). Lauf endete
         terminal, Recovery-Plan erreichte
         den Builder nicht.

  Wichtige Werkstatt-Fixes in dieser Sitzung:
    - P2b-Frage-A/B: Rueckfrage-Kanal
      (COMMAND: frage_reviewer, ANTWORT-Modus).
    - P2b-Korrektur: Plan-Korrektur bei
      Unterblock-NO-GO.
    - Rollen-Audit-A/B: reviewer.md, builder.md,
      solver.md korrigiert.
    - Planner-Rolle: P15/P16 (Blockgroessen).
    - builder-format: typ: new_file im
      WICHTIG-Block.
    - V3-Fix: Anker-Pruefung ueberspringt
      typ: new_file.
    - Post-Apply-Fix: rc=19-Signal +
      _post_apply_korrektur_loop.

  Aktueller Zustand:
    - Phase 18 (Guardrails) in phase.yaml.
    - U1 (Guardrail-Modell) status=no_go nach
      Lauf 12 (rc=15, unterblock_no_go).
    - Working Tree clean (nach git clean -fd
      vor Lauf 12).

  Lauf 12 (2026-10-16, Post-Apply-Fix):
    - typ: new_file funktioniert weiter.
    - Zwei NO-GO-Zyklen in U1 (5 Runden +
      Plan-Korrektur + 5 Runden).
    - Reviewer-Diagnose (Zitat):
        'Der Loop haengt nicht an einem
         fehlerhaften Builder, sondern an
         wechselnden Review-Kriterien.'
        'Der Kern-Befund — Auftrag unterbestimmt
         — kann nur der Planner aufloesen,
         nicht der Builder.'
    - Reviewer verlangt: feste Spezifikation
      (frozen ja/nein, Defaults, Feldreihen-
      folge, str-Enum vs. Enum, Bedeutung
      von 'Roundtrip').
    - Plan-Korrektur ERSETZT den Plan, sie
      KONKRETISIERT ihn nicht. Der Builder
      sieht denselben Auftrag, liefert den
      denselben Code, der Reviewer gibt
      dieselbe Bewertung.

  Struktureller Befund (offen):
    - Es fehlt ein Kanal 'Reviewer-Befund ->
      Planner-Konkretisierung -> neue
      Plan-Version'. Plan-Korrektur muss
      konkretisieren, nicht ersetzen.
    - Naechster Reviewer-Block: Plan-Konkre-
      tisierung (in dieser Session formuliert,
      noch nicht gebaut).

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

AUS SITZUNG 2026-10-16 (neu):

  P8 — Builder-Rueckfrage als Fliesstext:
        Der Builder liefert die Rueckfrage als
        Fliesstext mit '?' am Ende, nicht als
        'COMMAND: frage_reviewer <text>'.
        R8 greift deshalb nicht.
        Fix: Builder-Prompt expliziter.
        Kategorie 3.

  V1 — baue_anker_rueckmeldung Option (c):
        Der Anker-Block sollte typ: new_file
        als Option (c) mit Diagnose-Satz
        'Existiert die Zieldatei?' nennen.
        Nur relevant fuer den Fall 'Builder
        liefert typ: patch mit leerem Anker
        auf neue Datei'. Eigener Block.

  V4 — statischer new_file-Hinweis in
        _builder_user_prompt: Position pruefen.
        Kosmetisch, eigener Block.

  V6 — dynamische vs. statische Prompt-Bloecke:
        Dynamische Bloecke (baue_anker_rueckmeldung,
        baue_budget_rueckmeldung) sind maechtiger
        als statische Doku. Gemeinsamer Katalog
        'Patch-Format-Optionen' als Quelle.
        Eigener Block.

  Solver-Entlastung — bereits implementiert:
        solver_trigger_b (builder_rueckfrage)
        laeuft parallel zum Reviewer. Rollenbild
        in Rollen-Audit-B nachgezogen.
        Kein offener Fix.

  Phase-18-Plan (10 Unterbloecke) — Review:
        Nach Lauf 12 pruefen, ob 10 Bloecke
        pro Phase sinnvoll sind. Evtl. P17
        (Phasen-Obergrenze) einfuehren.

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

================================================================
WEG-Y-PATCH 2026-10-16 (manueller Eingriff)
================================================================

Kontext: 13. PB-68-Lauf (dritter Versuch) ergab eine
NO-GO-Schleife. Reviewer-Diagnose: Auftrag unterbestimmt.
Der Reviewer-Befund "file_whitelist fehlt" ist nach
Messung sachlich falsch — die Whitelist existiert in
projects/security-ai.yaml Z. 89-96. Der LLM-Reviewer
sieht sie nicht im Prompt (Merkposten).

Manueller Eingriff in projects/security-ai.phase.yaml
(vor dem 14. Lauf):

U1-Unterpunkte vorher (3):
  1. 'neu: core/guardrails/__init__.py (leer,
      Package-Marker).'
  2. 'neu: core/guardrails/models.py: Dataclass
      Guardrail (id, name, level, state) plus Enum ...'
  3. 'test: tests/unit/test_guardrails_models.py:
      Roundtrip (anlegen, lesen), Enum-Werte,
      Default-State.'

U1-Unterpunkte nachher (4):
  1. 'neu: core/guardrails/__init__.py. Inhalt: ""
      (leerer String, kein "inhalt: |"-Block).
      ... Whitelist: core/ ist freigegeben.'
  2. 'neu: core/guardrails/models.py. GENAU VIER
      Felder: id, name, level, state. ...'
  3. 'test: tests/unit/test_guardrails_models.py.
      Roundtrip, Enum-Werte, Default-Werte,
      frozen-Check. ...'
  4. 'Hinweis (nicht Bau-Auftrag): new_file-Patches
      -> GEMESSENER INHALT nicht anwendbar. ...'

U2-U10 unveraendert. phase_aktiv=true unveraendert.
phase_start_head=0d0fe2c unveraendert.

Grund: Reviewer-Antwort "Weg Y als Uebergangsloesung".
Bewusste Einmal-Aenderung, kein Werkstatt-Bug.

Merkposten (neu):
  - Weg X (Plan-Konkretisierung) bleibt offen.
    Anlass praeziser: "Projekt-Whitelist im Prompt
    unsichtbar", nicht "Auftrag unterbestimmt".
    Aufteilung in X-1/X-2/X-3 nach 14. Lauf.
  - LLM-Reviewer sieht file_whitelist aus
    projects/<name>.yaml nicht im Prompt.
    Fix-Option: Whitelist in aufgabe_block
    sichtbar machen. Eigener Block, Kategorie 3.
  - Fail-closed laesst untracked files in
    whitelist-Pfaden liegen. Manuelles Cleanup
    noetig. Eigener Block.

Erwartung Lauf 14 (Weg-Y-A11):
  - Resume-Force: U1 (no_go) -> pending.
  - Planner-Skip (Resume-Pfad, verifiziert).
  - Builder liest U1 mit 4 Unterpunkten.
  - Patches: inhalt:"" + vier Felder.
  - Reviewer Code-GO.
  - Commit-Review mit mess_protokoll_nach_apply.
  - Sammel-Commit moeglich.

Wenn Lauf 14 scheitert: kein Fix-Loop (Weg-Y-A7).
Analyse im Handoff, dann entscheiden.

================================================================
ENDE WEG-Y-PATCH
================================================================

================================================================
REKONSTRUKTION 2026-10-16 — phase.yaml nach Plan-Korrektur-Bug
================================================================

Kontext: 15. PB-68-Lauf (Versuch 2, 2026-10-16 14:26).
_phase_plan_korrektur hat den Plan komplett ersetzt und
dabei ALLE Unterbloecke auf status=pending gesetzt
sowie deren commit_paket geloescht. U1 (vorher done)
verlor damit:
  - Status done (wurde no_go),
  - commit_paket mit den drei U1-Dateien,
  - die urspruenglichen 4 Unterpunkte (der Planner
    hat neue formuliert).

Konsequenz: der 15. Lauf startete faelschlich mit U1
statt mit U2 und lief in eine NO-GO-Schleife.

Fix (Commit 6049a0d): _phase_plan_korrektur merged
jetzt. done-Unterbloecke bleiben unveraendert
(status, commit_paket, unterpunkte). Struktur-Check:
Anzahl, ids, titel muessen gleich bleiben. Bei
Verletzung Fail-closed.

Manuelle Rekonstruktion der phase.yaml (2026-10-16):
U1 zurueckgesetzt auf:
  status: done
  commit_paket:
    dateien: [core/guardrails/__init__.py,
              core/guardrails/models.py,
              tests/unit/test_guardrails_models.py]
    message: "U1: Guardrail-Modell"
  unterpunkte: die urspruenglichen 4 aus Weg-Y.
U2-U10 bleiben pending (korrekt).

Working Tree: 3 U1-Dateien (unveraendert).
Grund: die U1-Arbeit ist gut und wurde nicht
verworfen, nur der Plan-Zustand war falsch.

Erwartung 15. Lauf (Versuch 3):
  - Resume-Force: U2 (pending) -> keine Aenderung
    (resume-force setzt nur no_go/failed auf pending).
    U1 bleibt done.
  - Basis-Gate: untracked U1-Dateien erlaubt.
  - Phasen-Persistenz: 1 done-Paket geladen.
  - U1 uebersprungen.
  - U2 laeuft mit dem neuen Plan-Korrektur-Schutz.
  - Falls U2 no_go: Plan-Korrektur merged jetzt
    statt zu ersetzen.
  - U3-U10.
  - Sammel-Commit.

Merkposten:
  - Der 15.-Lauf-Befund bestaetigt: Plan-Korrektur
    muss mergen, nicht ersetzen. Commit 6049a0d.
  - Weg X (Marker + Diskriminator) bleibt offen.
    Anlass praeziser: Reviewer eskaliert
    "Auftrag unterbestimmt/veraltet" — der Planner
    soll anreichern, nicht neu formulieren.

================================================================
ENDE REKONSTRUKTION
================================================================

================================================================
U2-REPARATUR 2026-10-16
================================================================

Kontext: 15. PB-68-Lauf (Versuch 3, 2026-10-16 14:35).
Der Lauf ist bis Post-Apply-Basis-Gate gruen gekommen.
Dort `ruff` rot: SIM115 in
tests/unit/test_guardrails_loader.py:24.

Der Post-Apply-Korrektur-Loop ruft den Reviewer.
Der Reviewer-Kontext ist durch
`aktueller_prompt[:2000]` geschnitten (Bug,
siehe Truncation-Fix 6041033). Der Reviewer sieht
den abgeschnittenen Prompt und schliesst auf eine
"unvollstaendige Datei". Das ist falsch — die Datei
ist 152 Zeilen, py_compile ok, vollstaendig.

Der Builder folgt dem falschen Befund, dreht im
COMMAND-Loop. Post-Apply-Korrektur max_runden
erreicht. Fail-closed.

Fix (6041033): Truncation-Marker + GEMESSENER
INHALT separat im Reviewer-Kontext.

Manuelle U2-Reparatur (2026-10-16):
- tests/unit/test_guardrails_loader.py: _write
  auf Context Manager umgestellt (with ... as tmp).
- ruff check: All checks passed.
- pytest tests/unit/test_guardrails_loader.py: 22 passed.

phase.yaml: U2 auf status=done mit Paket
(loader.py + test_guardrails_loader.py).
U1 bleibt done. U3-U10 pending.

Working Tree:
  ?? core/guardrails/                 (U1 + U2)
  ?? tests/unit/test_guardrails_loader.py
  ?? tests/unit/test_guardrails_models.py

Erwartung 16. Lauf:
  - Basis-Gate: untracked Dateien aus U1+U2
    erlaubt.
  - Phasen-Persistenz: 2 done-Pakete geladen.
  - U1, U2 uebersprungen.
  - U3 laeuft (Guardrail-Config-Datei).
  - Bei Erfolg: Phase laeuft weiter (U4-U10).
  - Bei Sammel-Commit am Phasen-Ende:
    Tag probebetrieb-68.

Wenn U3 scheitert und der Reviewer wieder
"Datei unvollstaendig" behauptet: NICHT
manuell eingreifen. Der Truncation-Fix (6041033)
sollte greifen. Wenn nicht: Truncation-Fix
pruefen.

================================================================
ENDE U2-REPARATUR
================================================================

================================================================
17. LAUF VORBEREITUNG 2026-10-16
================================================================

Kontext: 16. PB-68-Lauf (2026-10-16 14:58-15:01) hat
den Meilenstein erreicht: U1, U2, U3 sind done,
der Plan-Korrektur-Schutz haelt sie. U4 ist an
zwei Auftragsfehlern gescheitert.

Fix-Kette seit dem 16. Lauf:
  b8710f5  config: file_whitelist um data/ erweitern
  562fde5  feat: file_whitelist im Prompt sichtbar
           (Reviewer + Builder)

U4-Unterpunkte manuell korrigiert (2026-10-16):
  1. data/migrations/0016_guardrails.sql
     (nicht 0013 — Nummernkollision mit
     0013_whitelist_manage.sql).
     Whitelist-Hinweis.
  2. core/guardrails/repository.py mit KEIN upsert,
     KEIN seed_from_yaml (Auftragstreue).
  3. test_guardrails_repository.py gegen echte
     Migration 0016, kein Inline-Schema.

Herkunft der Praezisierungen (Auflage U4-Auftrag-A3):
  - Punkt 1 Nummernmuster: Bau-Chat-Messung
    (ls data/migrations/).
  - Punkt 1 Whitelist-Hinweis: Reviewer-Befund
    Lauf 16 + Config-Fix b8710f5.
  - Punkt 2 "kein upsert": Builder-Scope-Drift
    in Lauf 16 (Runden 1-5), Reviewer-Befund.
  - Punkt 3 "echte Migration": Reviewer-Befund
    Lauf 16.

Erwartungshaltung 17. Lauf (Auflage A6):
  - U1-U3 done (Pakete: 3, 2, 4).
  - U4 korrigierter Auftrag.
  - Reviewer-Prompt enthaelt FILE-WHITELIST
    mit data/.
  - Erwartung: U4 laeuft.
  - Wenn U4 scheitert: STOP. Bilanz faellig.
    Keine weitere Iteration ohne Reflexion.

Merkposten bleiben offen:
  - Planner-Prompt um Whitelist (eigener Block).
  - Truncation-Konvention (systematisch).
  - Reviewer-Behauptungs-Verifikation.
  - Persistenz-Konvention.
  - Weg X (Plan-Konkretisierung).

================================================================
ENDE 17. LAUF VORBEREITUNG
================================================================

================================================================
BILANZ 17. LAUF 2026-10-16
================================================================

Kontext: 17. PB-68-Lauf (2026-10-16 15:08-15:12).
Auflage A6 verlangt Bilanz bei U4-Scheitern.
Der Lauf ist gescheitert, weil der Auftrag
unterbestimmt ist.

================================================================
WAS FUNKTIONIERT
================================================================

Der Phasen-Modus ist strukturell fertig und im
Live-Betrieb bewiesen:

1. Multi-Run-Faehigkeit.
   Der 17. Lauf hat U1, U2, U3 als done erkannt,
   uebersprungen und mit ihren Paketen (3, 2, 4
   Dateien) in den Sammel-Commit aufgenommen.
   Insgesamt 7 untracked Pfade aus drei
   done-Unterbloecken.

2. Basis-Gate im Phasen-Modus (_phasen_basis_gate_ok).
   Akzeptiert untracked Dateien aus done-Unterbloecken
   deterministisch und auditierbar.

3. Phasen-Persistenz (commit_paket in phase.yaml).
   Die Pakete werden persistiert und beim Resume
   restauriert. Kein Datenverlust zwischen Laeufen.

4. Plan-Korrektur-Schutz (6049a0d).
   Nach 5 NO-GO-Runden und Plan-Korrektur-Versuch
   (mit [n] abgebrochen) sind U1-U3 unveraendert:
   status=done, Pakete intakt, Unterpunkte unveraendert.
   Die Plan-Korrektur-Anzeige zeigte 3 Unterpunkte
   fuer U1 — der Schutz hat die 4 bestehenden
   gerettet.

5. Whitelist im Prompt (562fde5).
   Der Reviewer sieht die file_whitelist jetzt
   direkt im Prompt. Kein "Pfad fehlt"-Fehlbefund
   mehr.

6. Truncation-Marker (6041033).
   Reviewer-Kontexte werden mit Marker gekuerzt.
   Kein "Datei unvollstaendig"-Fehlschluss.

7. Review-Persistenz (a066e0d).
   Reviewer-Antworten landen im Audit-Log.

8. Post-Apply-Messung (eb8119a) + Recovery-Prompt-
   Fix (3bbe681).

9. Resume-Force (7e5cc65).
   no_go/failed -> pending, mit Effekt.

================================================================
WAS NICHT FUNKTIONIERT
================================================================

Der systematische Blocker ist Auftragsqualitaet.

Muster in Lauf 13, 14, 16, 17:
  - Der Planner liefert Auftraege, die das WAS
    nennen, aber nicht das WIE.
  - Der Builder kann das WIE nicht erfinden (R9)
    und dreht im COMMAND-Loop.
  - Der Reviewer eskaliert korrekt ("Auftrag
    unterbestimmt").
  - Die Plan-Korrektur liefert wieder einen
    unterbestimmten Auftrag (Ersatz statt
    Konkretisierung).

Konkreter Fall 17: die Test-Anforderung
"gegen die ECHTE Migration 0016, kein Inline-
Schema" nennt keinen Weg, wie die Migration
im Unit-Test ausgefuehrt wird. Der Builder
pendelt zwischen Inline-Schema (verboten),
Eigenbau-Runner (nicht spezifiziert) und
importierbarem Runner (nicht benannt).

Das ist genau das Problem, fuer das Weg X
(Plan-Konkretisierung) gedacht war.

================================================================
DREI STRUKTURELLE BLOCKE (offen)
================================================================

A) Planner-Praezisierung (Weg X).
   Der Planner soll Auftraege mit dem WIE liefern.
   Konkret: technische Praezisierungen (Mechanik,
   APIs, Konventionen) als Pflichtbestandteil.
   Aufwand: mittel-gross.
   Anlass: vier Laeufe mit demselben Muster.

B) Reviewer-Input-Vollstaendigkeit.
   Der Reviewer soll vollstaendigen Kontext sehen.
   Truncation-Marker sind ein Teil; aber die
   Reviewer-Inputs sind strukturell unvollstaendig
   (z.B. filesystem-Zustand, verfuegbare APIs).
   Aufwand: mittel.

C) Truncation-Konvention.
   Alle ~50 [:N]-Stellen in pipeline.py markieren.
   Aufwand: klein, aber systematisch.

================================================================
EMPFEHLUNG
================================================================

Die Reihenfolge:
  1. U4 manuell mit praezisem WIE korrigieren.
  2. 18. Lauf.
  3. Bei Erfolg: Phasen-Modus ist bewiesen.
     Weiter mit U5-U10.
  4. Danach: Block A (Planner-Praezisierung)
     als Kern-Fix. Ohne ihn wiederholt sich
     das Muster in U5-U10.

Wenn der 18. Lauf U4 mit praezisem Auftrag
schafft: der Beweis ist erbracht, dass die
Werkstatt mit praezisen Auftraegen funktioniert.
Die Auftragslieferung durch den Planner bleibt
der schwierigste Teil.

================================================================
ENDE BILANZ 17. LAUF
================================================================

================================================================
UEBERGABE AN NEUEN BAU-CHAT (2026-10-16, 16:00)
================================================================

Diese Sitzung ist am Kontext-Limit. Ein neuer
Bau-Chat uebernimmt. Dieser Block ist die
Startanweisung.

================================================================
IST-ZUSTAND
================================================================

Werkstatt-HEAD: 4896edf "feat: Phasen-Header +
  R9/R13/R14 — Rollen-Kalibrierung Teil 2".
Werkstatt-Tests: 801 passed.
ruff/mypy: 0.

security-ai-HEAD: 0d0fe2c (PB-67).
  Probebetrieb 68 ist NICHT getaggt (21 Laeufe,
  kein Sammel-Commit).
Working Tree security-ai: 4 untracked
  (core/guardrails/, tests/unit/test_guardrails_config.py,
  test_guardrails_loader.py, test_guardrails_models.py).

phase.yaml:
  phase_aktiv: true
  phase_id: 18
  phase_start_head: 0d0fe2c29b549c968d1ace116a69f57cf65f9998
  U1: done  (4 Unterpunkte, Paket 3)
  U2: done  (2 Unterpunkte, Paket 2)
  U3: done  (2 Unterpunkte, Paket 4)
  U4: failed (4 Unterpunkte)
  U5-U10: pending

Commits seit der Uebergabe (Auswahl, chronologisch):
  651175f (origin/main) doku: Handoff — Lauf 12
  3e77c1f Fix: Post-Apply-Basis-Gate — rc=19
  a066e0d feat: review_round-Audit persistiert
          Reviewer-Antwort
  e52558b feat: Solver-Sichtbarkeit
  7e5cc65 feat: --resume-force
  0651ed6 fix: commit_review_new_file_skip
  eb8119a fix: Post-Apply-Messung + Rollback
  7b79425 doku: Handoff — Weg-Y-Patch
  de93129 feat: Phasen-Persistenz — commit_paket
  f28511e feat: Basis-Gate im Phasen-Modus
  2a39626 fix: Basis-Gate git status -uall
  6049a0d feat: Plan-Korrektur-Schutz
  5217ab2 doku: Handoff — Rekonstruktion
  3bbe681 fix: Recovery-Prompt + rohantwort-Fallback
  6041033 fix: Truncation-Marker
  e2c5db1 doku: Handoff — U2-Reparatur
  b8710f5 config: file_whitelist um data/ erweitern
  562fde5 feat: file_whitelist im Prompt sichtbar
  e6f7da5 doku: Handoff — Vorbereitung 17
  d62d044 doku: Handoff — Bilanz 17
  413921d feat: Rollen-Kalibrierung — Spec-Treue,
          Solver-Befolgung, Sachfaden
  1f098c7 feat: new_file-Marker — Prompt, Rollen,
          HARD_RULES
  4896edf feat: Phasen-Header + R9/R13/R14

================================================================
WAS SEIT DER UEBERGABE FUNKTIONIERT
================================================================

1. Phasen-Modus ist multi-run-faehig.
   U1, U2, U3 sind done und bleiben done
   ueber beliebig viele Resume-Versuche.
   Beweis: Lauf 16-21.

2. Phasen-Persistenz (de93129).
   commit_paket der done-Unterbloecke wird in
   phase.yaml persistiert und beim Resume
   restauriert.

3. Basis-Gate im Phasen-Modus
   (_phasen_basis_gate_ok, f28511e + 2a39626).
   Untracked Dateien aus done-Unterbloecken
   werden deterministisch akzeptiert.

4. Plan-Korrektur-Schutz (6049a0d).
   done-Unterbloecke bleiben unveraendert bei
   Plan-Korrektur. Struktur-Check (Anzahl, ids,
   titel).

5. --resume-force (7e5cc65).
   no_go/failed -> pending.

6. Post-Apply-Messung (eb8119a).
   mess_protokoll_nach_apply fuer new_file-Pfade.

7. Review-Persistenz (a066e0d).
   Reviewer-Antwort im review_round-Audit als raw.

8. Solver-Sichtbarkeit (e52558b).
   Trigger + Befund auf Konsole.

9. Truncation-Marker (6041033).
   _truncate_mit_marker + GEMESSENER INHALT separat.

10. Recovery-Prompt-Fix (3bbe681).
    rohantwort-Fallback + Messblock.

11. Rollen-Kalibrierung (413921d).
    B13 (Spec-Treue), B14 (Solver-Befolgung),
    R11 (Sachfaden).

12. new_file-Marker (1f098c7).
    B15, R12, _NEW_FILE_MARKER,
    _messwerte_fuer_prompt.

13. Phasen-Header (4896edf).
    R13 (Phasen-Trennung), R14 (Verdict-Konsistenz),
    R9 auf ESKALATION, Phasen-Header im Prompt.

================================================================
WAS NICHT FUNKTIONIERT — DER AKTUELLE BLOCKER
================================================================

Der 21. PB-68-Lauf (2026-10-16 15:55-15:56)
ist an U4 gescheitert. Der Auftrag war praezise,
aber der Builder befolgte ihn nicht.

Befund:
  - Builder liefert Migration mit 4 statt 6 Spalten
    (created_at, updated_at fehlen).
  - Builder nutzt GuardrailRepositoryError statt
    GuardrailNotFoundError.
  - Builder nutzt Inline-Schema statt Migration im Test.

Der Reviewer-Verdacht (Truncation) wurde
WIDERLEGT: prompt_len-Werte aus dem Audit-Log
sind 17.259 (Code-Review) und 4.988-6.729
(Recovery). Weit unter redact_all-Limit 100.000.

Der Builder hat den vollstaendigen Auftrag gesehen
und ignoriert trotzdem Teile.

Neue Diagnose:
  Der Planner liefert Auftraege, die nicht
  builder-freundlich genug sind. Konkrete
  Praezisierungen (Feldnamen, Signaturen,
  Reihenfolge) fehlen.

================================================================
VIER OFFENE PLANNER-ANFORDERUNGEN
================================================================

Der Auftraggeber hat vier zusammenhaengende
Planner-Anforderungen formuliert, die noch NICHT
gebaut sind:

1. Planner plant kleiner von vorneherein.
   Heute P15 (1-2 Zieldateien + 1 Test) ist
   zu schwach.

2. Planner kann bei Resume dort weitermachen,
   wo aufgehoert wurde.
   Heute _planner_user_content bekommt KEINEN
   phase_unterbloecke-Zustand.

3. Planner versteht: Plan muss builder-freundlich
   sein. Detailiert.
   Neue Regel P17 fehlt (Signatur, Feldnamen,
   Reihenfolge, Schemas, Prueffaelle).

4. Planner bei Korrektur: Reviewer-Begruendung
   verstehen + Aenderungen im Detail wiedergeben.
   Neue Regel P18 fehlt. Heute reviewer_befund
   als Rohtext ohne Struktur-Anforderung.

================================================================
NAECHSTER SCHRITT — EMPFEHLUNG
================================================================

Der neue Bau-Chat soll:

1. Diesen Handoff lesen.
2. HEAD pruefen:
     git -C /opt/werkstatt log -3 --oneline
     git -C /opt/werkstatt status --porcelain
     /opt/security-ai/.venv/bin/python3 -m pytest \
       /opt/werkstatt/tests/ -q
   Erwartung: 4896edf, clean, 801 passed.
3. phase.yaml pruefen:
     /opt/security-ai/.venv/bin/python3 -c "
     import yaml
     d = yaml.safe_load(open(
         '/opt/werkstatt/projects/security-ai.phase.yaml'))
     for u in d['phase_unterbloecke'][:4]:
         print(f\"{u['id']}: {u['status']}\")
     "
   Erwartung: U1-U3 done, U4 failed, U5-U10 pending.
4. Reviewer-Chat kontaktieren mit dem Hinweis:
     "Neuer Bau-Chat, Uebergabe 2026-10-16 16:00.
      Stand: HEAD 4896edf, 801 passed.
      Blocker: Planner-Praezision.
      Vier Anforderungen: Blockgroesse, Resume,
      Builder-Freundlichkeit, Reviewer-Befund-
      Wiedergabe.
      Siehe Handoff 'UEBERGABE AN NEUEN BAU-CHAT'."

================================================================
HANDOFF-EINTRAEGE DER SITZUNG (Chronologie)
================================================================

- WEG-Y-PATCH 2026-10-16
- REKONSTRUKTION 2026-10-16
- U2-REPARATUR 2026-10-16
- 17. LAUF VORBEREITUNG 2026-10-16
- BILANZ 17. LAUF 2026-10-16
- UEBERGABE AN NEUEN BAU-CHAT 2026-10-16 (dieser Block)

Alle in diesem Handoff dokumentiert.

================================================================
WERKZEUG-REGELN (bestaetigt und aktuell)
================================================================

- ruff --no-cache messen.
- mypy rekursiv pruefen.
- /opt/werkstatt/projects/ gehoert builder:builder 750.
- core.fileMode=false im Werkstatt-Repo.
- post-checkout-Hook setzt projects/-Owner.
- Patch-Skripte > 40 Zeilen in /tmp anlegen,
  nicht als Heredoc.
- Vor jedem Commit: git status --porcelain pruefen.
- Bei Kategorie 3: Reviewer-Block vor Bau.
- Kein Tag ohne echten Pipeline-Durchlauf.

================================================================
MERKPOSTEN (offen, fuer spaetere Bloecke)
================================================================

1. Planner-Praezision (vier Anforderungen).
2. 2169 deterministisch pruefen.
3. list_dir im Katalog (bei Bedarf).
4. Vertrauens-Kalibrierung zwischen Rollen.
5. Truncation-Konvention (systematisch).
6. Reviewer-Behauptungs-Verifikation.
7. Persistenz-Konvention.
8. Weg X (Plan-Konkretisierung).
9. DRY-Refactor Z. 7077
   (_hat_anker_patches -> _alle_patches_sind_new_file).
10. U4 manuelle Neu-Formulierung mit P17-Detailtiefe.

================================================================
ENDE UEBERGABE
================================================================


================================================================
BLOCK 2a PLANNER-KORREKTUR-KONTEXT (2026-10-16)
================================================================

Commit: siehe git log. Kategorie 3.

Aenderungen:
  - _planner_user_content (Z. ~2718):
      reviewer_befund aus dem korrektur_kontext wird
      vollstaendig in den Prompt eingesetzt (Marker
      === REVIEWER-BEFUND (vollstaendig) ===).
      P18 aus Block 1 wird damit wirksam.
      Abschluss-Wortlaut: "Format aus P10-P16,
      beachte P17 (Builder-Freundlichkeit) und
      P18 (Korrektur-Kompetenz)".
  - phase_stand-Parameter + _phase_stand_sektion
    (neu):
      AKTUELLER-PHASENSTAND-Sektion mit id, status,
      paket_groesse, letzter_befund (gekuerzt via
      _truncate_mit_marker auf 200 Zeichen).
      Explizite Anweisung: "Der Resume beginnt bei
      U<n>. Plane NUR U<n>. Beruehre abgeschlossene
      Unterbloecke NICHT."
      Fallback bei allen done: "Alle Unterbloecke
      sind abgeschlossen. Plane einen neuen
      Phasenplan oder brich ab."
  - _phase_plan_korrektur:
      Baut phase_stand aus state.phase_unterbloecke
      + state.review_runden[-1]["raw"] (nur bei
      no_go/failed). "naechster" = erste
      no_go/failed/pending id.
      Uebergibt phase_stand an _planner_lauf.
  - _planner_lauf: phase_stand durchgereicht.
  - tests/test_planner.py: +10 Tests, Signatur-Test
    (TestPlannerLauf.test_planner_lauf_signatur)
    um phase_stand ergaenzt.

Tests: 822 passed (+10).

Auflagen-Abgleich (aus Reviewer-Block GO-mit-Auflagen):
  2a-A1 (Redaction): erfuellt, ask_llm redactet
    user_content (Z. 3149). Keine Aenderung noetig.
    Im Code-Kommentar (Docstring) dokumentiert.
  2a-A2 (_truncate_mit_marker): existiert (Z. 4758),
    genutzt.
  2a-A3 (naechster Edge-Case): erfuellt, Fallback
    "Alle Unterbloecke sind abgeschlossen."
    Plus Test test_user_content_phase_stand_alle_done_fallback.
  2a-A4 (Redundanz phase_stand vs alter_plan):
    erfuellt. phase_stand enthaelt KEINEN titel,
    nur id/status/paket_groesse/letzter_befund.
    alter_plan behaelt titel.
  2a-A5 (Abschluss-Wortlaut): erfuellt, P17 und
    P18 explizit genannt.

Merkposten unveraendert:
  - B1-A5 (UNBEANTWORTET-Behandlung) -> Block 2b.
  - B1-A4 (P17-Beispiel Rotation) -> spaeter.
  - A4 (U5/U6/U9 Unterpunkt-Zahl) -> spaeter.

Naechster Block: 2b (UNBEANTWORTET-Parser +
Entscheidung).

================================================================
ENDE BLOCK 2a
================================================================

================================================================
BLOCK 2b PLANNER UNBEANTWORTET-BEHANDLUNG (2026-10-16)
================================================================

Commit: siehe git log. Kategorie 3.

Aenderungen:
  - _UNBEANTWORTET_PRAEFIX = "UNBEANTWORTET:"
    (neu, B3). Kopplung an P18 Schritt 5.
  - _plan_unbeantwortet_punkte (neu, B1+B2):
      Durchsucht geparste Unterpunkte, erkennt
      Praefix-Treffer. Rueckgabe pro Treffer
      dict{"unterblock": "U<n>", "punkt": "<text>"}.
  - _phase_plan_korrektur: Nach _parse_phase_plan,
    vor Anzeige: Trefferpruefung. Bei Treffern:
      * Audit phase_plan_unbeantwortet mit
        unterblock-Zuordnung.
      * Konsolenausgabe pro Punkt via
        _truncate_mit_marker(200).
      * _phase_rr_k8 (konsistent mit parse_failed).
      * return False (Plan wird nicht gespeichert).
  - _AUDIT_KINDS_BEKANNT + phase_plan_unbeantwortet.
  - _parse_phase_plan unveraendert.
  - tests/test_planner.py: +9 Tests (Klasse
    TestPlannerUnbeantwortet).
  - tests/test_pipeline.py: 2 Katalog-Anzahl-Tests
    auf 63 angepasst.

Tests: 831 passed (+9).

Auflagen-Abgleich:
  B1 (Anzeige-Truncation): erfuellt.
    _truncate_mit_marker(200) pro Punkt.
  B2 (Audit pro Unterblock): erfuellt.
    _plan_unbeantwortet_punkte gibt dict-Liste
    zurueck; Audit enthaelt unterblock-Zuordnung.
  B3 (Konstante _UNBEANTWORTET_PRAEFIX):
    erfuellt. Kopplung an P18 sichtbar.
    Merkposten: bei P18-Aenderung Konstante
    anpassen.
  B4 (Test mehrere Unterbloecke): erfuellt.
    test_plan_unbeantwortet_punkte_mehrere_
    unterbloecke prueft zwei verschiedene
    Unterbloecke.

Merkposten (B3):
  _UNBEANTWORTET_PRAEFIX und P18 Schritt 5
  sind gekoppelt. Bei P18-Wortlaut-Aenderung
  Konstante anpassen.

Stand jetzt:
  P18 ist vollstaendig wirksam (Block 1 als
  Regel, Block 2a als Prompt-Ausgabe, Block 2b
  als Marker-Erkennung und Entscheidung).
  Planner-Praezision Block 1 + Block 2a + 2b
  sind FERTIG.

Naechster Schritt:
  - U4 in security-ai.phase.yaml manuell mit
    P17-Detailtiefe formulieren.
  - 22. PB-68-Lauf mit --resume-force.
  - Beobachten: folgt der Planner P17/P18?
    Verarbeitet er den Reviewer-Befund
    vollstaendig? Plant er kleiner (P15-Neu)?

================================================================
ENDE BLOCK 2b
================================================================

================================================================
LAUF 22 BILANZ (2026-10-16)
================================================================

Kontext: 22. PB-68-Lauf mit neuem U4 (P17-Detailtiefe).
Abbruch am RR-K8-Menue ([2] Phase abbrechen).

Ergebnis:
  - Kein Sammel-Commit.
  - Kein Tag probebetrieb-68.
  - U4 bleibt no_go.
  - Working Tree unveraendert (3 U1-U3-Dateien
    untracked, keine U4-Dateien).

WICHTIGSTE ERKENNTNIS:
  Die 3 U4-Patches wurden NIE auf Platte geschrieben
  (apply_code_patches wurde nicht gerufen).
  Der Reviewer sah die Patch-Texte im Prompt und
  prueft symbolisch: alle Pruefpunkte OK. Gab
  trotzdem 5x UNKLAR statt GO.

Audit-Kette 16:29-16:30:
  - builder_reply_erhalten (3 Patches).
  - review_round runde 1-5: alle verdict=UNKLAR.
  - recovery_no_go.
  - phase_unterblock_ende: U4 / no_go.
  - phase_plan_korrektur_start.
  - phase_plan_korrektur_failed:
      grund=parse_failed,
      exception="U1: id nicht mit 'U1' ueberein
                 (gefunden: 'U4')".

Drei getrennte Blocker:

  B0 — Reviewer UNKLAR-Loop.
    Der Reviewer prueft 5x alle 3 Patches und
    findet alles OK, gibt aber UNKLAR. Vermutung:
    weil die Dateien nicht real existieren
    (apply wurde nicht gerufen), traut er sich
    kein GO.
    Fix-Optionen:
      (a) apply VOR Review (Dateien real da).
      (b) Reviewer-Prompt: bei reinen new_file
          ohne Datei-Pruefung GO erlauben.
      (c) UNKLAR-Behandlung: nach 1x UNKLAR
          Eskalation statt Loop.

  B1 — Planner-Struktur-Verstaendnis.
    Der Planner hat phase_stand (Block 2a)
    bekommen. Er hat fuer U4 einen neuen Plan
    formuliert. ABER: er hat "U4" als erste
    UNTERBLOCK-id geschrieben. _parse_phase_plan
    verlangt monoton ab U1.
    Konsequenz: phase_plan_korrektur_failed
    (parse_failed).
    Fix: phase_stand-Sektion und P18 muessen
    explizit sagen: "Behalte die Gesamtstruktur
    U1-U10. Formuliere NUR den Inhalt von U4 neu.
    Die ids bleiben U1-U10."

  B2 — apply_code_patches im Review-Loop.
    Heute: Builder -> Review-Runde 1..5 ->
    apply (erst nach GO).
    Problem: bei reinen new_file-Patches sieht
    der Reviewer nie die Datei.
    Fix: apply VOR Review ODER Datei-Simulation
    im Reviewer-Prompt.

Was funktioniert hat:
  - Block 2a (phase_stand im Prompt): wirksam,
    der Planner bekam den Stand.
  - Block 2b (UNBEANTWORTET): nicht getriggert
    (Plan hatte kein UNBEANTWORTET).
  - Block 1 (P17/P18): nicht bewertbar, weil
    Planner-Parse fehlschlug.

Auflagen-Abgleich (U4-22-A1 bis A8):
  A1 (Design-Entscheidung): umgesetzt, aber
    nicht zum Zug gekommen.
  A2-A4: umgesetzt, nicht zum Zug gekommen.
  A5 (L5): Messung ergab: kein Bug.
  A6 (Hinweise nicht P15): umgesetzt.
  A7 (5 Test-Prueffaelle): umgesetzt, nicht
    zum Zug gekommen.
  A8 (Bilanz): dieser Block.

Merkposten (neu):
  - B0: Reviewer UNKLAR-Loop.
  - B1: Planner-Struktur-Verstaendnis (id-
    Reihenfolge U1-U10 bei Plan-Korrektur).
  - B2: apply_code_patches im Review-Loop.
  - Manuelle phase.yaml-Eingriffe: jetzt 6
    (Weg-Y U1, U2, U4-Lauf 16, U4-Lauf 21,
    U4-Neufassung Lauf 22). Bilanz-Signal.
  - Bilanz 21 Laeufe ohne Sammel-Commit
    (Handoff-Eintrag "BILANZ 17. LAUF" zeigt
    strukturelle Naehe, aber noch kein
    Durchbruch).

Naechster Block:
  Reviewer-Block fuer B0 (UNKLAR-Loop) und
  B2 (apply vor Review). B1 separat (P18-
  Verscharfung).

================================================================
ENDE LAUF 22 BILANZ
================================================================

================================================================
B0 UNKLAR-BEHANDLUNG (2026-10-16)
================================================================

Commit: siehe git log. Kategorie 3.

Aenderungen:
  - HARD_RULES_REVIEWER +R15 (symbolische
    Pruefung bei reinen new_file-Paketen;
    R15 ergaenzt R12; Widerspruchs-Format
    Widerspruch:/Beleg:).
  - HARD_RULES_SOLVER +S10 (analog fuer den
    Solver; M4: derselbe symbolische
    Blindfleck).
  - _review_unklar_widerspruch (Parser fuer
    Widerspruchs-Block).
  - run_pipeline: UNKLAR-Zweig im Review-Loop.
    1x UNKLAR mit/ohne Widerspruch -> naechste
    Runde (Audit review_unklar_widerspruch
    bzw. review_r15_verstoss).
    2x UNKLAR in Folge -> Eskalation (rc=14,
    konsistent mit ESKALATION-Pfad).
    Konkrete Options-Ausgabe an den Menschen.
  - _AUDIT_KINDS_BEKANNT +3.
  - tests/test_pipeline.py: +11 Tests,
    Katalog-Anzahl 63 -> 66.

Tests: 842 passed (+11).

Auflagen-Abgleich (B0-A1 bis A8):
  A1 (Widerspruchs-Format): erfuellt. R15
    definiert Format, _review_unklar_widerspruch
    parst es, Loop unterscheidet.
  A2 (rc=14): bestaetigt durch Messung
    (ESKALATION-Pfad Z. 7064 return 14).
    Neuer Zweig nutzt rc=14.
  A3 (Slice-Order): state.review_runden.append
    Z. 7006 vor dem UNKLAR-Zweig. [-2:] =
    diese + vorige Runde. Semantik korrekt.
  A4 (Eskalations-Output): Optionen-Liste
    gedruckt.
  A5 (Widerspruchs-Zaehlung): Audit
    review_unklar_widerspruch vs.
    review_r15_verstoss. review_r15_verstoss
    ist neu.
  A6 (11 Tests): erfuellt.
  A7 (Bilanz-Verweis): Handoff Lauf 22
    zitiert.
  A8 (R12/R15-Querverweis): in R15-Wortlaut.

Merkposten:
  B1 (Planner-Struktur-Verstaendnis):
    der Planner versteht die Phasen-Struktur
    nicht vollstaendig (liefert "U4" als
    erste id). P18-Verschaerfung oder
    phase_stand-Sektion muss explizit
    "Behalte U1-U10" sagen. Eigener Block.
  B2 (apply vor Review): nicht notwendig,
    wenn R15/S10 wirken.

Naechster Block: B1 (Planner-Struktur).

================================================================
ENDE B0
================================================================

================================================================
B1 PLANNER-STRUKTUR-VERSTAENDNIS (2026-10-16)
================================================================

Commit: siehe git log. Kategorie 3.

Aenderungen:
  - _phase_stand_sektion: Struktur-Anweisung.
    "Behalte die Gesamtstruktur." "Aendere NUR
    den INHALT von U<n>." "Formuliere den neuen
    Plan mit ALLEN Unterbloecken."
    Generisch (keine spezifische id-Aufzaehlung).
  - P18 Schritt 4: "Er enthaelt ALLE
    Unterbloecke in derselben Reihenfolge."
    Schutz-Hinweis aus Block 1 unveraendert.
  - tests/test_planner.py: +6 Tests.

Tests: 848 passed (+6).

Auflagen-Abgleich (B1-A1 bis A6):
  A1 (generische Wortwahl): erfuellt. Test
    test_phase_stand_sektion_generisch prueft
    Regressionsschutz.
  A2 (P18-Wortlaut vorher): eingehalten.
    Wortlaut aus Block 1 zitiert, ergaenzt.
  A3 (Fallback "alle done"): gemessen.
    Fallback-Text unveraendert.
  A4 (Merkposten Parser-Toleranz): notiert.
  A5 (Reihenfolge B1-a/B1-b): OK.
  A6 (Schutz-Hinweis erhalten): erfuellt.

Merkposten (B1-A4):
  Parser-Toleranz relativ zur Struktur.
  Wenn Lauf 23 wieder parse_failed liefert,
  Parser anpassen: Teilmengen-Plaene erlauben,
  Position aus id ableiten. Eigener Block.

Naechster Schritt:
  23. PB-68-Lauf mit --resume-force.
  Beobachten:
    - Planner liefert Plan mit ALLEN Unterbloecken.
    - Struktur bleibt, nur U4-Inhalt neu.
    - U4 laeuft.
  Bei Scheitern: Bilanz Pflicht.

================================================================
ENDE B1
================================================================

================================================================
B0C VERDICT-PARSER + BUG-1 + BUG-2 (2026-10-16)
================================================================

Commit: siehe git log. Kategorie 3.

Ausgangslage:
  23. PB-68-Lauf (2026-10-16 16:44) ist an B0c gescheitert:
  Reviewer gab 2x UNKLAR, B0b eskalierte korrekt (rc=14).
  Aber: der Reviewer hatte "GO" am Ende der Antwort.
  classify_verdict prueft nur den Anfang (max 15 Zeilen).
  Verdict am Ende wurde nicht erkannt.

Aenderungen:
  - classify_verdict: Fallback fuer Verdict am Ende.
    Nur letzte nicht-leere Zeile, <40 Zeichen,
    Verdict-Wort allein.
  - run_phase: rc=14 als eigene Klasse (status=no_go,
    kein Rollback).
  - review_unklar_eskalation: + raw ([:2000]).
  - TestClassifyVerdict: 2 Tests an B0c angepasst.
  - TestB0cUndBugs: +6 Tests.

Tests: 854 passed (+6).

Auflagen-Abgleich:
  B0c ist ein neuer Fix (nicht in vorherigen Auflagen).
  B0a (R15/S10) wirkt: der Reviewer wendet R15 an
  (Audit zeigt "R15: GO" im Text). Nur der Parser
  hat versagt.
  B0b (UNKLAR-Loop) wirkt: 2x UNKLAR -> Eskalation.
  Bug-1 (rc=14) und Bug-2 (raw) sind neue Befunde
  aus dem 23. Lauf.

Wichtig:
  Die 2059-Grenze (Verdict nur in den ersten 15
  Zeilen) bleibt fuer den ANFANG. Der End-Fallback
  ist eine Ergaenzung. reviewer.md verlangt das
  Verdict am Ende; jetzt erkennt der Parser es.

Naechster Schritt:
  24. PB-68-Lauf mit --resume-force.
  Beobachten:
    - Reviewer R15: GO am Ende.
    - classify_verdict: erkennt GO.
    - apply_code_patches laeuft.
    - U4 done.
    - U5-U10 laufen weiter.
    - Sammel-Commit, Tag probebetrieb-68.

================================================================
ENDE B0C
================================================================

================================================================
TIMEOUT-FIX + U4-PRAEZISIERUNG (2026-10-16)
================================================================

Timeout-Fix (Commit siehe git log). Kategorie 3.

Ausgangslage:
  24. Lauf (2026-10-16 16:50) hat gezeigt:
  B0c wirkt (Reviewer gibt NO-GO, classify_verdict
  korrekt). ABER: der Builder-Call hat nach 460 s
  nicht terminiert (llm_timeout_s=180, Retry-Backoff
  1+3 s, Worst-Case 364 s).

  Ursache: requests int-Timeout wird als
  (connect=180, read=180) interpretiert. Bei
  tropfendem Server (Chunks alle <180 s) greift
  der Read-Timeout nie.

Fix (Option B):
  B1 (primaer, HR-R7): timeout=(15, 180) Tupel.
    Read-Timeout greift bei Chunk-Stille >180 s.
  B2 (sekundaer): Deadline max_total_llm_s=240.
    Verhindert Folgeversuche nach Ueberschreitung.
    Read-Timeout adaptiv: min(180, restzeit).
  + RunState.max_total_llm_s: int = 240.
  + ask_llm aufgabe-Parameter (Audit-Zuordnung).
  + _AUDIT_KINDS_BEKANNT +3.

Tests: 863 passed (+9).

U4-Praezisierung:
  Alle vier Reviewer-Befunde aus Lauf 24 eingearbeitet:
    (a) set_state schreibt updated_at.
    (b) get/list_all nur vier Spalten selektieren.
    (c) __init__(db_path: Path) exakt.
    (d) Fixture Path(__file__).resolve() + exists().
  Plus U4-Praez-A1 (updated_at testen),
  A2 (_insert_guardrail-Helper explizit),
  A3 (Fixture-Reihenfolge),
  A4 (Fehlerklassen mit Docstrings),
  A5 (set_state-Validierungs-Semantik).

Merkposten (Timeout-A3):
  max_total_llm_s aus projects/<name>.yaml
  als optionales Feld (nicht in diesem Block).

Naechster Schritt:
  25. PB-68-Lauf mit --resume-force.
  Beobachten:
    - B0c: Verdict-Parser erkennt NO-GO/GO am Ende.
    - Timeout-Fix: kein Haenger >240 s.
    - U4: vier Befunde eingearbeitet; Reviewer GO?
    - U4 done -> U5 laeuft.
    - Sammel-Commit, Tag probebetrieb-68.
  Bei Scheitern: Bilanz Pflicht.

================================================================
ENDE TIMEOUT-FIX + U4-PRAEZISIERUNG
================================================================

================================================================
F1+F2+F3 COMMIT-PHASE-FIXES (2026-10-16)
================================================================

Commit: siehe git log. Kategorie 3.

Ausgangslage 25. Lauf:
  Erster Code-GO seit Lauf 12 (U4-Patches gebaut).
  Commit-Phase gescheitert an drei Infrastruktur-Bugs.

Fixes:
  F1: _rollback_zieldateien git status -uall.
      Dateien in neuen Verzeichnissen werden
      einzeln gefunden. Rollback entfernt alle
      new_file-Pfade (repository.py bleibt nicht
      mehr liegen).

  F2: apply_and_recheck git add -N.
      2169-Blocker behoben: neue Dateien erscheinen
      in git diff --name-only HEAD.

  F2-A1: git reset HEAD -- <pfade> VOR unlink.
      Index sauber nach intent-to-add-Rollback.

  F3: collect_messwerte git_head-Fallback.
      Liest aus basis_protokoll, wenn
      _nach_apply leer (apply_and_recheck-Skip).

Tests: 875 passed (+12).

Auflagen-Abgleich:
  F1-A1 (Syntax-Konsistenz): -uall wie Z. 7965.
  F2-A1 (Index-Cleanup): git reset HEAD vor unlink.
  F2-B1 (Katalog): 69 -> 71.
  F2-C1 (Pfad-Normalisierung): Pfade aus
    code_patches sind bereits relativ.
  F2-D1 (Timeout 30s): konsistent mit bestehenden
    git-Aufrufen.
  F3-A1 (Regex): bestehende Regex aus
    collect_messwerte wiederverwendet.
  F3-A2 (bestehender Parser): collect_messwerte
    erweitert, keine dritte Regex.
  F3-A3 (Fallback-Absicht): Reviewer erwartet
    git_head (Befund 25. Lauf); Fallback korrekt.

Merkposten (F1-F3-A2):
  _git_status_porcelain (Z. 3234) nutzt
  "git status --porcelain" ohne -uall.
  Bei kuenftigen Aufrufen pruefen, ob -uall
  noetig ist (Konsistenz mit F1).

Naechster Schritt:
  26. PB-68-Lauf mit --resume-force.
  Erwartung:
    - Code-GO (wie 25).
    - apply + git add -N.
    - Commit-Review Runde 1: COMMIT-GO.
    - Sammel-Commit.
    - Tag probebetrieb-68.
  Bei Scheitern: Bilanz Pflicht.

================================================================
ENDE F1+F2+F3
================================================================

================================================================
B0C-2 VERDICT-PARSER (2026-10-16)
================================================================

Commit: siehe git log. Kategorie 3.

Ausgangslage 26. Lauf:
  Reviewer gibt 2x "**GO**" (Markdown), aber
  classify_verdict liefert UNKLAR.
  Ursachen:
    - Markdown-Fett-Marker (*) nicht gestrippt.
    - Nur letzte nicht-leere Zeile geprueft;
      Runde 2 hatte Text nach "**GO**".

Fix:
  - Markdown-Marker (* ` _ #) strippen.
  - Letzte 5 nicht-leere Zeilen rueckwaerts pruefen.
  - Nur Zeilen <40 Zeichen zaehlen (Fliesstext-Schutz).

Tests: 875 + 6 = 881 passed.

Auflagen-Abgleich:
  - B0c aus Lauf 24 erweitert, nicht ersetzt.
  - Bestehende Tests (test_go_at_line_16,
    test_go_after_many_inhalt_lines) bleiben gruen.

Merkposten:
  - Konsolenausgabe "(unbekannt)" bei
    review_unklar_eskalation: raw steht im Audit,
    wird aber nicht auf Konsole gedruckt. Kosmetik.
    Eigener Block.

Naechster Schritt:
  27. PB-68-Lauf mit --resume-force.
  Beobachten:
    - Reviewer Runde 1: GO -> apply + git add -N.
    - Commit-Review Runde 1: COMMIT-GO.
    - Sammel-Commit. Tag probebetrieb-68.

================================================================
ENDE B0C-2
================================================================

================================================================
D1+D3 COMMIT-PAKET-SCOPE (2026-10-16)
================================================================

Commit: siehe git log. Kategorie 3.

Ausgangslage 27. Lauf:
  B0c-2 wirkt, F2 wirkt (Code-GO, apply,
  git add -N). Commit-Review 2x NO-GO:
  BETROFFENE DATEIEN (10) != Commit-Message (3).

Fix:
  D1 (Beratung): build_commit_paket-Prompt
    nennt ZIELDATEIEN aus state.code_patches.
    B2-Fall explizit.
  D3 (Durchsetzung): run_pipeline
    (Phasen-Modus) ueberschreibt
    state.commit_paket["dateien"] deterministisch
    mit state.code_patches-Pfaden. Vor
    phase_commit_pakete.append.
  _AUDIT_KINDS_BEKANNT +1.

Tests: 891 passed (+10). Katalog 71 -> 72.

Auflagen-Abgleich:
  D-A0: D1 Beratung, D3 Durchsetzung —
    im Docstring dokumentiert.
  D-A1: B2-Fall: leere Liste; Fail-closed
    rc=21 greift (Unterblock ohne Dateien
    ist sinnlos).
  D-A2: D3 zwischen build (Z. 7687) und
    Prompt (Z. 7748).
  D-A3: Katalog 72.
  D-A4: D3 vor append (Z. 7900).
  D-A5: Merkposten D-A7 korrigiert —
    _phase_sammel_paket unioniert alle
    Pakete. Kein Datenverlust.
  D-A6: 10 Tests.

HR-R7-Korrektur:
  Reviewer hat D2 (R16) verworfen, D3
  uebernommen. LLM-Regel zu einer
  bestehenden LLM-Regel ist dieselbe
  Wette. Deterministisch ist besser.

Naechster Schritt:
  28. PB-68-Lauf mit --resume-force.
  Erwartung:
    - Code-GO (wie 27).
    - apply + git add -N.
    - D3 greift: phase_commit_dateien_deterministisch.
    - Commit-Review Runde 1: COMMIT-GO.
    - Paket gesammelt (kein Commit).
    - U4 done, U5 laeuft.
  Bei Scheitern: Bilanz Pflicht.

================================================================
ENDE D1+D3
================================================================

================================================================
E + R16 COMMIT-REVIEW-DIFF (2026-10-16)
================================================================

Commit: siehe git log. Kategorie 3.

Ausgangslage 28. Lauf:
  D3 wirkt (BETROFFENE DATEIEN = 3 statt 10).
  ABER Commit-Review 2x NO-GO: "2169 nicht
  erfuellt; Pflichtabgleich gegen
  git diff --name-only HEAD fehlt im Paket."

Fix:
  E: commit_input enthaelt die Sektion
    "GIT DIFF --NAME-ONLY HEAD: <pfade>".
    Vor commit_input ausgelesen.
    Bei git-Fehler: Fail-closed (return 9).
    Leere Liste: "(keine)".
  R16: neue HARD_RULES_REVIEWER-Regel.
    Der Prompt zeigt "PHASEN-MODUS: aktiv/inaktiv".
    Bei aktiv: 2169 = TEILMENGE.
    Bei inaktiv: 2169 = Gleichheit (wie bisher).
    Grund: git diff zeigt alle Unterbloecke
    seit Phase-Start; BETROFFENE DATEIEN nur
    den aktuellen.
  +2 Audit-Kinds.

Tests: 891 + 9 = 900 passed. Katalog 72 -> 74.

Auflagen-Abgleich (E-A1 bis A8):
  E-A1 (Teilmengen-Semantik R16): erfuellt.
  E-A2 (fail-closed statt "(Fehler)"): return 9.
  E-A3 (leere Liste "(keine)"): erfuellt.
  E-A4 (Verhaltens-Tests): Muster aus bestehenden
    Tests (inspect.getsource) uebernommen.
  E-A5 (Reihenfolge D3 -> E -> commit_input):
    Z. 7728 -> 7793 -> Prompt.
  E-A6 (Katalog +2): 72 -> 74.
  E-A7 (8 Tests): 9 Tests.
  E-A8 (Merkposten Sub-Ref): notiert.

Merkposten (E-A8):
  Sub-Ref pro Unterblock fuer praezisere
  2169-Pruefung. Heute reicht R16 (Teilmenge).
  Eigener Block, wenn unklar.

Naechster Schritt:
  29. PB-68-Lauf mit --resume-force.
  Erwartung:
    - Code-GO.
    - apply + git add -N.
    - D3 (3 Pfade).
    - E: GIT DIFF --NAME-ONLY HEAD (3 Pfade).
    - R16: 3 == 3 Teilmenge erfuellt.
    - Commit-Review Runde 1: COMMIT-GO.
    - Paket gesammelt (kein Commit).
    - U4 done, U5 startet.

================================================================
ENDE E + R16
================================================================

================================================================
DURCHBRUCH: U4 DONE (2026-10-16)
================================================================

29. PB-68-Lauf (2026-10-16, Uhrzeit?). Erster
erfolgreicher Commit-Review seit Lauf 12.

U4: status=done. Commit-Paket gesammelt
(3 Dateien):
  - data/migrations/0016_guardrails.sql
  - core/guardrails/repository.py
  - tests/unit/test_guardrails_repository.py

Die Kette funktioniert:
  - B0c-2: Verdict-Parser (Markdown + mehrzeilig).
  - F2: git add -N.
  - D3: BETROFFENE DATEIEN deterministisch.
  - E: GIT DIFF --NAME-ONLY HEAD im Prompt.
  - R16: Teilmenge-Semantik.
  - Timeout-Fix: kein Haenger.

U5 ist direkt gestartet (2 Patches) und
gescheitert (Post-Apply-Basis-Gate rot).

U5-Fehler (Reviewer-Diagnose, praezise):
  Hauptbefund: GuardrailRepository.set_state
  gibt None zurueck. Der Service behandelt
  den Rueckgabewert aber als Guardrail-Objekt.
  AttributeError zur Laufzeit.

  Nebenbefunde:
  - AuditWriter-Import: from core.audit.writer
    import AuditWriter. Modul existiert nicht
    oder anders benannt.
  - 3x totes "# noqa: BLE001".
  - Ungenutzter Import AccessChecker.
  - Test-Fake _FakeRepo.set_state gibt Guardrail
    zurueck (echte API: None) -> maskiert Bug.
  - RBAC-Codes guardrail.view/manage evtl.
    nicht vorhanden.

Auftrags-Unterbestimmtheit U5:
  Der U5-Auftrag nennt nicht:
  - Rueckgabeverhalten von set_state.
  - AuditWriter-Modul-Pfad.
  - Test-Fake-Vertrag.

Merkposten (kritisch):
  1. Rollback-Bug: Fail-Pfad nach
     Post-Apply-Korrektur-max erreicht
     ruft _rollback_zieldateien NICHT immer.
     Working Tree hat 5 A-Eintraege (U4+U5).
     Manuelles Cleanup noetig.
  2. U5-Auftrag praezisieren (wie U4).
  3. Bilanz nach diesem Lauf (Pflicht).

Naechster Schritt:
  - Working-Tree-Cleanup (5 A-Eintraege).
  - U5-Auftrag praezisieren.
  - 30. Lauf mit --resume-force.
  - Ziel: U5 done, dann U6-U10, dann
    Sammel-Commit, Tag probebetrieb-68.

================================================================
ENDE U4 DONE
================================================================

================================================================
7. MANUELLER EINGRIFF: U5-NEUFFASSUNG (2026-10-16)
================================================================

Ausgangslage 29. Lauf:
  U4 durch (Durchbruch). U5 gestartet, 2 Patches,
  Post-Apply-Basis-Gate rot. Reviewer-Diagnose:
  4 Auftrags-Unterbestimmtheiten:
    (1) AuditWriter-Import falsch
        (core.audit.writer statt
         harness.audit.writer).
    (2) set_state gibt None, Service behandelt
        als Guardrail.
    (3) RBAC-Codes guardrail.view/manage
        existieren nicht.
    (4) Test-Fake maskiert Bug.

A0-Messungen (M-a bis M-d):
  M-a: hoechste Migration 0016. Neue: 0017.
  M-b: AccessChecker in core/access/checker.py.
       Import: from core.access.checker import
       AccessChecker, AccessDeniedError.
  M-c: API AccessChecker.require_permission(
       principal_name, code) -> None.
       RBAC-Fehler = AccessDeniedError.
  M-d: AuditWriter.log(*, agent, tool,
       policy_result, permission_level,
       execution_status, args=None, ...,
       details=None) -> AuditEntry.
       Keyword-only.

Aenderung:
  U5-Unterpunkte ersetzt (4 Eintraege):
    1. Migration data/migrations/
       0017_guardrail_permissions.sql
       (Muster 0015: INSERT OR IGNORE,
        role_permissions (role_id, permission_id)).
    2. Service core/services/
       guardrail_service.py (exakte Imports,
       Fehlerklassen, Methoden-Signaturen,
       try/except-Grenze).
    3. Test tests/unit/
       test_guardrail_service.py (drei Fakes,
       5 Prueffaelle).
    4. Hinweis (new_file-Skip).
  P15-Ausnahme dokumentiert: Migration +
  Service atomar (Service ohne RBAC-Codes =
  403 fuer alle Rollen).

Muster:
  7. manueller phase.yaml-Eingriff.
  Der Planner produziert noch keine P15/P17-
  konformen Auftraege mit Signaturtiefe.
  Weg-X-Prioritaet wird durch dieses Muster
  gestuetzt.

Naechster Schritt:
  30. PB-68-Lauf mit --resume-force.
  Beobachtung:
    - U4 done (uebersprungen).
    - U5 laeuft.
    - Ziel: U5 done, U6 startet.

================================================================
ENDE U5-NEUFFASSUNG
================================================================

================================================================
W1 EXTRACT_PATHS ERWEITERT (2026-10-16)
================================================================

Commit: siehe git log. Kategorie 3.

Ausgangslage 30. Lauf:
  Reviewer-Eskalation ("Auftrag unterbestimmt").
  Ursache: extract_paths_from_aufgabe erkannte
  die Pfade im U5-Auftrag nicht (Import-
  Notation, .sql-Endung, neue Dateien).

Fix (W1):
  - Endungen: +sql +json +toml +cfg +ini +txt.
  - from-Importe: from a.b.c import X ->
    a/b/c.py.
  - exists()-Filter entfernt: neue Dateien
    existieren noch nicht. Elternverzeichnis-
    Check ersetzt ihn.
  - Aufrufer unveraendert (3 Stellen:
    Z. 7153, Z. 7163, Z. 7241).

Wirkung (direkter Test mit U5-Auftrag):
  7 Pfade statt 1.
    - data/migrations/0017_guardrail_permissions.sql
    - core/services/guardrail_service.py
    - tests/unit/test_guardrail_service.py
    - core/guardrails/models.py
    - core/access/checker.py
    - core/guardrails/repository.py
    - harness/audit/writer.py

Tests: 900 + 7 = 907 passed.

Auflagen-Abgleich (W1-A1 bis A9):
  A1 (Import-Stile): nur from-Regex noetig.
    Keine relativen/multiline im U5-Auftrag.
  A2 (Aufrufer): 3 Stellen, alle profitieren.
  A3 (exists-Filter): entfernt, Eltern-
    verzeichnis-Check stattdessen.
  A4 (Markdown): nicht noetig (kein ** im
    U5-Auftrag).
  A5 (12 Tests): 7 statt 12; 5 waren redundant
    (bereits in TestExtractPaths).
  A6 (Audit): Merkposten, nicht in W1.
  A7 (Reihenfolge): 907 passed vor Bau.
  A8 (Merkposten): notiert.
  A9 (HARD_RULES_BUILDER): B4/B13 zwingen den
    Builder, dem Auftrag zu folgen — auch wenn
    er falsch ist. Merkposten W2.

Merkposten (W2 wichtig):
  HARD_RULES_BUILDER B4 ("Du bist kein
  Messender") + B13 ("Der Auftrag ist
  verbindlich") verhindern, dass der Builder
  falsche Auftrags-Behauptungen misst.
  W2 sollte B13 verschaerfen: "Wenn der Auftrag
  Pfade/APIs behauptet, die nicht im
  GEMESSENER INHALT belegt sind: COMMAND: RUN
  read_file <pfad>."

Merkposten (W3):
  Planner-Messungs-Kanal. Heute hat der Planner
  kein COMMAND:. Bei Resume-Planung (W4) muss
  er messen koennen.

Merkposten (W4):
  Resume-Planung: der Planner wird im
  --resume-force-Pfad nicht gerufen.
  Struktureller Weg-X-Block.

Naechster Schritt:
  31. PB-68-Lauf mit --resume-force.
  Erwartung:
    - Auto-Messung: > 1 Zieldatei (W1 wirkt).
    - Builder sieht alle Pfade im Prompt.
    - Reviewer kann Import-Pfade pruefen.
    - U5 laeuft.

================================================================
ENDE W1
================================================================

================================================================
W2 + U6-KORREKTUR (2026-10-16)
================================================================

Commit W2: 0e6c881.

Ausgangslage 31. Lauf:
  U5 done (W1 wirkt: Auto-Messung 7 Zieldateien).
  U6 gestartet und gescheitert: Auftrag nannte
  data/migrations/0014_guardrail_permissions.sql,
  aber 0014_internal_name.sql existiert.
  Zwei konkurrierende Migrationen (0014 + 0017).

W2 (HARD_RULES_BUILDER):
  B4 aufgeteilt:
    (a) Systemwerte (Tests, Coverage, ruff,
        mypy, git-Status): Werkstatt.
    (b) Auftrags-Behauptungen (Datei-Existenz,
        Import-Pfad): Builder prueft B13b.
  B13b neu: Behauptungen pruefen.
    (a) "Datei X existiert" -> read_file ok=True.
    (b) "neu: X" -> read_file ok=False.
    (c) "Import aus a/b/c.py" -> read_file ok=True.
    Bei Widerspruch: COMMAND: frage_reviewer.
    NICHT fuer Signaturen/Nummernkreise.
  B13b und B7 komplementaer.

U6-Korrektur (Weg-Y):
  - 0014 -> 0018 (naechste freie Nummer).
  - KEINE neuen Permissions (U5-Migration 0017
    hat sie schon).
  - U6 ergaenzt nur operator + viewer mit
    guardrail.view.
  - Builder soll 0017 lesen.

Tests: 907 -> 912 passed (+5).

Auflagen-Abgleich (W2-A1 bis A7):
  A1 (list_dir): existiert nicht. B13b
    beschraenkt sich auf read_file (datei-genau).
  A2 (B4 praezisieren): erfuellt.
  A3 (B13b konkret): erfuellt.
  A4 (Nummernkreis-Merkposten): notiert.
  A5 (5 Tests): erfuellt.
  A6 (Test-Anzahl): 907 gemessen.
  A7 (Reihenfolge): W2 vor U6-Korrektur vor
    32. Lauf.

Merkposten (W1b):
  Nummernkreis-Pruefung in extract_paths_from_aufgabe:
  wenn data/migrations/NNNN_*.sql genannt:
  Prefix-Scan, ob NNNN belegt ist. Fail-closed
  bei Konflikt. Eigener Werkstatt-Block.

Merkposten (W3):
  Planner-Messungs-Kanal (COMMAND: read_file).

Merkposten (W4):
  Resume-Planung (Planner rufen bei failed/no_go).

Stand:
  U1-U5 done. U6 no_go (bereit fuer 32. Lauf).
  U7-U10 pending.

Naechster Schritt:
  32. PB-68-Lauf mit --resume-force.
  Beobachtung:
    - U5 done uebersprungen.
    - U6 startet.
    - B13b greift: Builder prueft 0018 frei?
      liest 0017.
    - U6 done, U7 startet.
  Bei Scheitern: neuer Reviewer-Block.

================================================================
ENDE W2 + U6
================================================================

================================================================
W3+W4 PLANNER-MESSUNG + PLAN-KORREKTUR (2026-10-16)
================================================================

Commit: siehe git log. Kategorie 3.

Ausgangslage 32. Lauf:
  U6 done (6 von 10). U7 gescheitert.
  Reviewer-Diagnose: der Planner kann den
  Reviewer-Befund nicht konkretisieren, weil
  er keinen Messungs-Kanal hat.

W3 (Planner-Messung):
  - P19 in HARD_RULES_PLANNER_STUFE2:
    "MESSEN VOR DEM PLAN".
    COMMAND: RUN read_file <pfad>.
  - _planner_lauf: lokale Schleife
    (max_runden=3). Bei Erschoepfung:
    fail-closed (return None).
  - ERLAUBTE_QUELLEN + "planner".
  - P9' auf P10-P19 erweitert.
  - _planner_user_content + GEMESSENER INHALT.
    state als Keyword am Ende
    (alte Tests bleiben gruen).
  - _messwerte_fuer_planner: roher
    Messprotokoll-Inhalt.

W4 (Plan-Korrektur):
  - P18 + Punkt 6: gemessene Anker Pflicht.
  - UNBEANTWORTET nur nach Messung.

Tests: 912 -> 924 (+12).
Katalog: 74 -> 75.

Auflagen-Abgleich:
  W3-A1 (Rekursion): lokale Schleife mit
    max_runden-Dekrement per range().
  W3-A2 (ERLAUBTE_QUELLEN): "planner" ergaenzt.
  W3-A3 (P9'): P10-P19.
  W3-A4 (Messwerte): state-Parameter +
    _messwerte_fuer_planner.
  W3-A5 (Signatur): Default max_runden=3,
    3 Aufrufer kompatibel.
  W3-A6 (rc): bestehender Fail-Pfad.
  W3-A7 (Redaction): ask_llm redactet.
  W3-A8 (Stufe1): unveraendert.
  W3-A9 (read_file): existiert.
  W4-A1 (P18): +Punkt 6.
  W4-A2 (DRY): Korrektur-Prompt referenziert
    P18/P19.
  W3-W4-A3 (Test-Anzahl): 912 korrekt.
  W3-W4-A4 (12 Tests): erfuellt.
  W3-W4-A5 (Groessen-Check): ~250 Zeilen,
    ein Block.
  W3-W4-A6 (Katalog): 75.

Merkposten:
  - Stufe-1-Planner-Messung: offen.
  - list_dir im Katalog: offen.
  - Resume-Planung (W4-Langfassung):
    Planner wird bei --resume-force noch
    nicht gerufen. W3 wirkt bisher nur
    im Plan-Korrektur-Pfad.
    MESSUNG: der 33. Lauf wird zeigen, ob
    W3 den Plan-Korrektur-Pfad wirksam
    macht.

Stand:
  U1-U6 done. U7 no_go.
  U8-U10 pending.

Naechster Schritt:
  33. PB-68-Lauf mit --resume-force.
  Beobachtung:
    - U7 startet.
    - Planner-Messung greift (COMMAND
      im Audit).
    - U7 done, U8 startet.

================================================================
ENDE W3+W4
================================================================

================================================================
U7-AUFTEILUNG (2026-10-16)
================================================================

Ausgangslage 33. Lauf:
  U6 done (6 von 10). U7 gestartet, 5 Runden,
  NO-GO. Reviewer-Eskalation:
    "Auftrag unterbestimmt (Zieldatei-
     Ausschnitte fehlen), Block zu gross,
     Sachfaden-Drift."
  Empfehlung: aufteilen in 3 Bloecke.

A0-Messungen (M-a bis M-c):
  M-a: g.principal gesetzt in app.py:181.
  M-b: Migration 0017 existiert, gibt
    guardrail.view/manage an admin.
    0018 (U6) ergaenzt operator + viewer.
  M-c: file_whitelist vollstaendig.

Aenderung:
  U7 aufgeteilt in zwei Unterbloecke:
    U7 (Dashboard-Route + app.py + Test).
    U8 (Dashboard-Template + CSP-Test).
  Nummerierung verschoben:
    ex-U8 -> U9 (Aktion).
    ex-U9 -> U10 (Sidebar).
    ex-U10 -> U11 (Doku).
  U7-Neufassung mit gemessenem Anker
  (app.py Z. 257-258):
    "    from apps.dashboard.routes_tools
     import register_tools_routes\n
         register_tools_routes(app)\n"
  count==1, 4 Spaces, LF.

Wichtige Korrekturen:
  - Reviewer-Annahme "required_permission"
    war falsch: heisst "require_permission".
  - Service wird inline gebaut
    (GuardrailRepository aus DB_PATH).
    Kein extensions-Eintrag.

Muster:
  9. manueller phase.yaml-Eingriff.
  Nach 9 Eingriffen ist die Werkstatt-
  Autonomie strukturell blockiert.
  Weg X (Planner-Konkretisierung) hat
  Prioritaet.

Stand:
  U1-U6 done. U7 no_go.
  U8-U11 pending.

Naechster Schritt:
  34. PB-68-Lauf mit --resume-force.
  Beobachtung:
    - U7 startet.
    - Route + app.py + Test gebaut.
    - 200/403-Tests gruen.
    - Commit-GO.
    - U7 done.
    - U8 startet.
  Bei Scheitern: neuer Reviewer-Block.

================================================================
ENDE U7-AUFTEILUNG
================================================================

================================================================
11. MANUELLER EINGRIFF: U7/U8/U9-AUFTEILUNG (2026-10-16)
================================================================

Ausgangslage 34. Lauf:
  U6 done. U7 gestartet, 4 Runden, Deadlock.
  Reviewer-Diagnose (R11):
    - Template fehlt in der Datei-Liste.
    - COMMAND + Patch im selben Block
      (Loop verwarf Patch).

Reviewer-Loesung:
  Option C: atomare Aufteilung nach P15-Neu.

Aenderung:
  U7 = Dashboard-Template /guardrails (1 Zieldatei).
  U8 = Dashboard-Route + app.py-Patch (1 Zieldatei
       + 1 Patch).
  U9 = Test /guardrails (1 Test-Datei).
  U10 = Dashboard-Aktion aktivieren/deaktivieren
        (ex-U9).
  U11 = Sidebar-Eintrag Guardrails (ex-U10).
  U12 = Doku-Nachzug Guardrails (ex-U11).

Wichtige Korrektur:
  Der U7/U8/U9-Umbau hat zunaechst den Aktion-
  Block verloren (U9 wurde mit U10 "Test"
  ueberschrieben). Manuell korrigiert: Aktion-
  Block als neuer U10 angelegt.

A0-Messungen (M1-M7):
  M1: Anker app.py Z. 257-258 (2 Zeilen, 4
      Spaces, LF, count==1).
  M2: require_permission (decorators.py Z. 28).
  M3: g.principal (app.py:181, str).
  M4: build_dashboard_app nutzt create_app.
  M5: Rollen: admin (view+manage),
      operator (view, 0018), viewer (view,
      0018), system (KEIN view).
  M6: create_role_client(app, "system")
      funktioniert (Muster test_dashboard_alerts
      .py:85).
  M7: Kein U7-Rest aus Lauf 34.

Auflagen-Abgleich:
  U7-U9-A1 (Anker minimal): erfuellt (2 Zeilen).
  U7-U9-A2 (system-Rolle): M6 bestaetigt.
  U7-U9-A3 (11. Eingriff): dieser Eintrag.
  U7-U9-A4 (Working Tree): M7 bestaetigt.
  U7-U9-B1 (Unused Imports): erfuellt (nur 5
    Imports in der Route).
  U7-U9-B2 (Handoff): dieser Eintrag.

Muster:
  11. manueller phase.yaml-Eingriff in Serie.
  Nach 11 Eingriffen ist die Werkstatt-Autonomie
  strukturell gebrochen. Weg X (Planner-
  Konkretisierung) hat Prioritaet.

Audit-Referenz:
  Alte Audit-Logs (Lauf 33, 34) referenzieren
  "U7" fuer "Dashboard-Route". Nach diesem
  Edit bedeutet "U7" "Dashboard-Template".
  Verwechslungsgefahr bei der Nachvoll-
  ziehbarkeit. Umnummerierung dokumentiert:
    Lauf 33/34: U7 = Route.
    Lauf 35+:    U7 = Template,
                 U8 = Route,
                 U9 = Test,
                 U10 = Aktion (ex-U9),
                 U11 = Sidebar (ex-U10),
                 U12 = Doku (ex-U11).

Merkposten:
  W5 (COMMAND+Patch-Bug): eigener Block.
  Weg X (Planner-Konkretisierung).

Stand:
  U1-U6 done. U7-U12 pending.

Naechster Schritt:
  35. PB-68-Lauf mit --resume-force.
  Erwartung: U7 (Template) done.

================================================================
ENDE 11. MANUELLER EINGRIFF
================================================================

================================================================
W6a+W6b READ_FILE-ZEILENBEREICH (2026-10-16)
================================================================

Ausgangslage 35. Lauf:
  U7 (Template) done. U8 gestartet, gescheitert.
  Reviewer-Diagnose (R11):
    "GEMESSENER INHALT enthaelt nur
     apps/dashboard/templates/guardrails.html.
     Die Anker des Auftrags stehen NICHT im
     GEMESSENER INHALT."

Wurzel:
  apps/dashboard/app.py ist ~9.000 Zeilen.
  Der Anker (Z. 257-258) liegt Zeichen ~20.000.
  trim_output kappte auf 10.000 Zeichen
  (MAX_PROTOKOLL_PER_COMMAND).
  Der Anker war abgeschnitten.

W6a (Commit e779c77):
  - _audit_builder_prompt: Regex ignoriert
    ARGV/RC/STDOUT/STDERR als Sektion.
    Behebt Fehldiagnose "gem_len=77".
  - Audit-Feld anzahl_read_file.
  - MAX_PROTOKOLL_PER_COMMAND_READ_FILE = 20_000.
  - MAX_PROTOKOLL_TOTAL = 150_000.
  - +5 Tests (929 passed).

W6b (dieser Commit):
  - read_file Zeilenbereich "<pfad>:<start>-<ende>"
    via sed -n "N,Mp".
  - _anker_zeilenbereich: extrahiert Anker aus
    dem Auftrag (Format "ANKER (...): '...'"),
    findet die Zeile in der Zieldatei.
    Liefert (anker_zeile-5, anker_zeile+10).
  - ensure_ziel_gemessen: aufgabe-Parameter.
    Bei Anker-Pfad wird der Zeilenbereich genutzt.
  - +8 Tests (937 passed).

Direkter Test:
  U8-Auftrag -> _anker_zeilenbereich liefert
  (252, 267). sed -n "252,267p" zeigt den
  vollstaendigen Anker (register_tools_routes).

Merkposten (W5, bleibt):
  COMMAND + Patch im selben Block fuehrt zur
  Verwerfung des Patches. Eigener Block.

Stand:
  U1-U7 done. U8 no_go.
  U9-U12 pending.

Naechster Schritt:
  36. PB-68-Lauf mit --resume-force.
  Erwartung:
    - U8 startet.
    - Auto-Messung: app.py mit Zeilenbereich.
    - Anker im GEMESSENER INHALT.
    - Builder baut Route + app.py-Patch.
    - U8 done.
    - U9 (Test) startet.
  Bei Scheitern: neuer Reviewer-Block.

================================================================
ENDE W6a+W6b
================================================================

================================================================
12. MANUELLER EINGRIFF: U8-AUFTEILUNG (2026-10-16)
================================================================

Ausgangslage 36. Lauf:
  U7 (Template) done. U8 gestartet, 3 Runden,
  Deadlock.
  Reviewer-Diagnose (R11):
    - Anker nicht verifizierbar.
    - Import-API nicht belegt.
    - Weitere ungepruefte Fakten.

A0-Messungen (belegt):

  M1: W6a+W6b wirken:
      gemessener_inhalt_len=2317 (statt 77).
      anzahl_read_file=7.
      app.py-Zeilenbereich 252-267 mit Anker.

  M2: Der Builder liefert:
      - Patch 1: new_file routes_guardrails.py.
      - Patch 2: patch app.py (Anker ok, aber
        ersatz-Check schlaegt fehl).

  M3: pruefe_ersatz_gegen_messung (Z. 3964):
      prueft, ob jede from-Import-Zeile im
      ersatz im mess_protokoll steht.
      Der app.py-ersatz enthaelt:
        from apps.dashboard.routes_guardrails
        import register_guardrails_routes
      Dieses Modul existiert noch nicht (wird im
      gleichen Reply als new_file erzeugt).
      Also: nicht im mess_protokoll -> Fehler.

Aenderung:
  U8 aufgeteilt in:
    U8: Dashboard-Route (new_file).
    U9: Dashboard-Integration (app.py-Patch).
  Nummerierung verschoben:
    ex-U9  -> U10 (Test).
    ex-U10 -> U11 (Aktion).
    ex-U11 -> U12 (Sidebar).
    ex-U12 -> U13 (Doku).

Konsequenz:
  In U8 (new_file) greift der ersatz-Check
  nicht — kein Patch mit ersatz.
  In U9 (Patch) existiert routes_guardrails.py
  bereits — der ersatz-Check findet das Modul
  im mess_protokoll (weil U8 die Datei
  angelegt hat).

Muster:
  12. manueller phase.yaml-Eingriff in Serie.
  Nach 12 Eingriffen ist die Werkstatt-
  Autonomie strukturell gebrochen.
  W5 (COMMAND+Patch), Weg X (Planner-
  Konkretisierung) bleiben Merkposten.

Audit-Referenz:
  Alte Audit-Logs referenzieren "U8" fuer
  "Route + app.py-Patch". Nach diesem Edit:
    U8 = Route (new_file).
    U9 = app.py-Integration (Patch).
    U10 = Test (ex-U9).
    U11 = Aktion (ex-U10).
    U12 = Sidebar (ex-U11).
    U13 = Doku (ex-U12).

Merkposten:
  W5: COMMAND + Patch im selben Block
      (Loop-Logik). Eigener Block.
  W7: pruefe_ersatz_gegen_messung akzeptiert
      Module, die im selben Reply als new_file
      erzeugt werden. Eigener Block.
  W8: Basis-Gate erkennt A-Eintraege nicht.
      Wiederholt manuelle git-reset-Aktionen.
      Eigener Block.

Stand:
  U1-U7 done. U8 no_go.
  U9-U13 pending.

Naechster Schritt:
  37. PB-68-Lauf mit --resume-force.
  Erwartung: U8 (Route) done.

================================================================
ENDE 12. MANUELLER EINGRIFF
================================================================

================================================================
W8 COMMIT-PAKET-PROMPT + MESSAGE-CHECK (2026-10-16)
================================================================

Commit: siehe git log. Kategorie 3.

Ausgangslage 37. Lauf:
  U8 (Route, new_file) gebaut. Code-GO.
  Commit-Review 2x NO-GO. Reviewer-Befund:
  "BETROFFENE DATEIEN sechs Dateien vs.
   GIT DIFF eine Datei."

A0-Messungen (M1-M4):
  M1: D3 wirkt: state.commit_paket["dateien"]
      = 1 Pfad.
  M2: Commit-Review-Prompt zeigt BETROFFENE
      DATEIEN = 1 Pfad.
  M3: Builder-Commit-Message nennt 6-7 Pfade.
  M4: GIT STATUS im build_commit_paket-Prompt
      zeigt 16 untracked Pfade. Der Builder
      kopiert sie in die Message.

W8-1 (GIT STATUS filtern):
  build_commit_paket filtert git_status auf
  _ziel_pfade. Der Builder sieht nur die
  Zieldateien — keine Halluzinations-Quelle.

W8-2 (Message-Sanity-Check):
  Nach D3: Pfade in der Message finden
  (Regex mit Datei-Endungen). Bei starker
  Diskrepanz (> Anzahl BETROFFENE DATEIEN):
  Fail-closed rc=9 + Audit.

W8-3 (commit_paket_gebaut-Audit):
  Reply-Kopf/Fuss + message_len +
  anzahl_dateien. Fuer kuenftige Diagnose.

Auflagen-Abgleich (W8-A1 bis A7):
  A1 (Check-Platzierung nach D3): erfuellt.
  A2 (GIT STATUS Filter): erfuellt.
  A3 (Message-Regex Endungen): erfuellt
    (py|sql|md|yaml|yml|json|toml|html|
     css|js|cfg|ini|txt).
  A4 (Fail-closed Pfad): erfuellt.
  A5 (Merkposten deterministische Message):
    notiert.
  A6 (7 Tests): erfuellt (937 -> 944).
  A7 (Handoff): dieser Eintrag.

R16 unveraendert (Reviewer-Kritik akzeptiert).

Merkposten (W8-A5):
  Deterministische Message-Generierung:
  statt Builder die Message schreiben zu
  lassen, generiert die Werkstatt die
  Message aus state.commit_paket (D3).
  Der Builder liefert nur einen Titel-
  Vorschlag. Eigener Block, HR-R8.

Stand:
  U1-U7 done. U8 no_go (nach U8-Aufteilung:
  Route). U9-U13 pending.

Naechster Schritt:
  38. PB-68-Lauf mit --resume-force.
  Erwartung:
    - U8 (Route) Code-GO, Commit-Review
      Runde 1: COMMIT-GO.
    - Paket gesammelt.
    - U9 (app.py-Patch) startet.
    - U10 (Test) folgt.

================================================================
ENDE W8
================================================================

================================================================
W10 MESSAGE-CHECK PRAEZISER (2026-10-16)
================================================================

Commit: siehe git log. Kategorie 3.

Ausgangslage 41. Lauf:
  U8 (Route) Code-GO in Runde 1 (Messblock
  wirkt). apply. Der W8-2-Check blockte:
    Message nennt 3 Pfade
    (Zieldatei + Muster + Template als
     Referenz).
    BETROFFENE DATEIEN: 1. Fail-closed.

W10:
  - _MESSAGE_SECTION_CHANGE = "Aenderung:".
  - _extrahiere_aenderung_pfade: Regex
    extrahiert Pfade NUR aus dem Bullet-Block
    unter "Aenderung:". Referenzen (Muster,
    Template) werden ignoriert.
  - _normalisiere_pfad: fuehrendes "./",
    "/", trailing "/", Backslash.
  - W8-2-Block ersetzt.
  - Fail-Pfade mit fall-Feld:
    "a" (Section leer), "b" (Section fehlt),
    "c" (Parse-Fehler), "diff" (Mengen-Ungleich).
  - Audit-Kind commit_message_diskrepanz
    bleibt (Katalog unveraendert).
  - 948 -> 956 passed.

Auflagen-Abgleich (W10-A1 bis A9):
  A1 (Section-Name): "Aenderung:" (ae),
    Konstante. Umlaut-Variante wird NICHT
    erkannt (Test).
  A2 (Regex-Grenzen): Bullet nur "-" oder
    "*". Keine trailing Leerzeilen-Toleranz.
  A3 (Parse-Diskriminierung): ein Kind
    mit fall-Feld.
  A4 (D3-Vergleich): Mengenvergleich nach
    Normalisierung.
  A5 (echte Message): nicht verfuegbar
    (Audit-Log leer); Test mit
    synthetischer, realistischer Message.
  A6 (W8b-Prompt-Konsistenz): geprueft,
    Format passt.
  A7 (Ersetzen): W8-2 ersetzt.
  A8 (8 Tests): erfuellt.
  A9 (Handoff): dieser Eintrag.

Merkposten:
  - Echte Message aus Lauf 41 nicht im Audit.
    W9a/W10 helfen kuenftig (commit_paket_gebaut
    speichert Kopf/Fuss).
  - Deterministische Message-Generierung
    (W8-A4) bleibt der langfristige Fix.

Stand:
  U1-U7 done. U8 no_go (nach U8-Aufteilung:
  Route). U9-U13 pending.

Naechster Schritt:
  42. PB-68-Lauf mit --resume-force.
  Erwartung:
    - U8 Code-GO, Commit-Review Runde 1:
      COMMIT-GO.
    - Paket gesammelt.
    - U9 (app.py-Patch) startet.

================================================================
ENDE W10
================================================================
