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
