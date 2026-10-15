# Bau-Handoff — Werkstatt

Stand: 2026-10-15 (nach 2183 + Stufe 0 + Auftrag-erfuellt + PB-65 + Agent-Memory-E1)
Werkstatt-HEAD: 52cd658 (Agent-Memory Ebene 1)
Letzter echter Probebetrieb: PB-65 (2aa2b0b, 2026-10-15)
Letzter Commit in security-ai: 2aa2b0b
Branch: main
Tests: 346 passed
ruff: 0
mypy: 0

================================================================
WICHTIG (2026-10-14)
================================================================

Ein Probebetrieb ist NUR ein echter Pipeline-
Durchlauf (pipeline_start + pipeline_ende im
Audit-Log, Projekt security-ai).

Die Tags probebetrieb-62 bis probebetrieb-83
wurden fuer manuelle Bau-Sessions vergeben. Das
war falsch. Sie wurden am 2026-10-14 entfernt.
Die Commits selbst bleiben (die Arbeit ist real),
nur die Tags waren semantisch falsch.

Letzter echter security-ai-Durchlauf:
  2026-10-14T21:00-21:02  rc=0  PB-62
  Commit 3bb5917 (whois ToolArgumentValueError).
  Erster erfolgreicher Lauf nach der
  Probebetrieb-Neudefinition.

Naechster echter Probebetrieb: probebetrieb-63.

================================================================

Dieses Dokument ist der Einstiegspunkt fuer einen neuen
Bau-Chat. Es enthaelt alles zum Weiterbauen. Es ist ein
Arbeitsdokument und wird bei jedem Meilenstein aktualisiert.

================================================================
1. WAS DIE WERKSTATT IST
================================================================

Die Werkstatt ist ein Agenten-System. Sie baut Projekte, ist
aber selbst kein Teil eines Projekts. Aktuell baut sie
Homelab Security AI, kann aber jedes Projekt bauen.

Verzeichnis: /opt/werkstatt/
Projekt-Konfigurationen: /opt/werkstatt/projects/
Rollen: /opt/werkstatt/agents/
Tests: /opt/werkstatt/tests/
Doku: /opt/werkstatt/docs/
  - WORKFLOW.md (Regeln, Anti-Patterns, Merkposten)
  - ROADMAP.md (offene Architektur-Ideen)
  - PROTOKOLL-29-40.md (Beobachtungs-Protokoll der
    Probebetriebe 29 bis 40)

Rollen (5):
  - reviewer (LLM, deepseek-reasoner): prueft Patches
    und Commit-Paket, entscheidet GO/NO-GO/ESKALATION.
  - builder (LLM, deepseek-chat): liefert strukturierte
    Code-Patches (PATCH-BEGINN/ENDE) und das Commit-Paket.
  - test_generator (LLM): liefert Test-Vorschlaege.
  - coverage (No-LLM): misst Coverage.
  - chaos (No-LLM): fuzzt Extremwerte.

================================================================
2. AKTUELLER ZUSTAND
================================================================

Werkstatt-Repo:
  HEAD 1cb266c (kein Tag, Solver-Kurskorrektur Block 2a+4)
  Tests: 346 passed
  ruff: 0, mypy: 0, git status sauber
  Remote: github.com/ghxstfocus/werkstatt.git (privat)

Ziel-Projekt security-ai:
  HEAD 3bb5917 (whois ToolArgumentValueError, PB-62)
  Vorgaenger 35e5178 (dns_lookup IPv6-Feld)
  git status sauber

Werkstatt-Tags (auf /opt/werkstatt):
  probebetrieb-7, -17, -29 bis -61
  (Nur echte Pipeline-Durchlaeufe.)

Ziel-Projekt-Tags (auf /opt/security-ai):
  probebetrieb-1 bis -28 (historisch)
  probebetrieb-62 (3bb5917, erster echter Lauf
  nach der Neudefinition)
  Konvention: Ziel-Repo-Tag fuer echte
  Pipeline-Durchlaeufe.

Dateien:
  - pipeline.py (3772 Zeilen, Stand Block 2a+4)
  - redaction.py (314 Zeilen, Stand 2195)
  - agents/*.md (5 Rollen)
  - projects/security-ai.yaml
  - tests/test_pipeline.py (4345 Zeilen, Stand Block 2a+4)
  - agents/solver.md (42 Zeilen, Stand 2183 B)
  - tests/test_redaction.py
  - docs/WORKFLOW.md
  - docs/ROADMAP.md
  - docs/PROTOKOLL-29-40.md
  - README.md

================================================================
3. WAS SEIT DEM LETZTEN HANDOFF PASSIERT IST
================================================================

Das Handoff vom 2026-10-12 (gesichert als
Bau-Handoff-2026-10-12.md.alt) ist veraltet. Es
beschreibt einen Stand vor den Auflagen 2027-2094
und vor UMB-1.

Seitdem:
  A) Auflagen 2027-2094 (16 kritische + 21 Befunde).
  B) UMB-1 (Architektur-Umbau, 4 Teile).
  C) Probebetriebe 1-28 (vor dieser Session).
  D) Auflagen 2186-2198 (diese Session).
  E) Zwei erfolgreiche Werkstatt-Commits in security-ai:
     dd3048b (PingError) und 3ccb883 (Traceroute).

================================================================
4. DIE 12 PROBEBETRIEBE DIESER SESSION (29-40)
================================================================

Ausfuehrliches Protokoll: siehe docs/PROTOKOLL-29-40.md.

Kurzfassung:
  PB-29: Fail (Anker 0x). Ausschnitt-Bug entdeckt.
  PB-30: Fail (Livelock, 5x NO-GO). COMMAND-Loop fehlt.
  PB-31: Fail (Anker 0x). Prompt einmal gebaut.
  PB-32: Fail (builder_command_deadlock).
  PB-33: Fail (Anker 0x). read_file ignoriert.
  PB-34: Fail (Anker 0x). GEMESSENER INHALT fehlt.
  PB-35: Fail (Anker 0x). GEMESSENER INHALT ignoriert.
  PB-36: Fail (Anker 0x). Automatik + GEMESSENER INHALT
         greifen nicht.
  PB-37: Fail (Anker 0x). Audit-Debug zeigt: IP-Redaction
         zerstoert Anker. WURZEL GEFUNDEN.
  PB-38: Fail (Commit-NO-GO). Anker trifft! Testzahl fehlt.
  PB-39: Fail (Commit-NO-GO). Rechte-Problem + Testzahl.
  PB-40: ERFOLG. Commit 3ccb883 in security-ai.
  PB-41: Doku. Handoff + Protokoll 29-40 neu.
  PB-42: Chore. .gitignore um *.alt ergaenzt.
  PB-43: ERFOLG. Auflage 2191-R. HEAD 87092f8.
  PB-44: Doku. Handoff auf PB-43-Stand.
  PB-45: Style. ruff I001 in tests/ behoben.
         KORREKTUR (PB-75): War unvollstaendig.
         Bei PB-75 gemessen: 2 Stellen weiterhin
         offen (tests/test_pipeline.py:16,
         tests/test_redaction.py:15). Eigener
         Block offen.
  PB-46: Doku. Handoff Abschluss-Update PB-45.
  PB-47: Fix. reviewer.md Verweis HR4 -> B5.
  PB-48: Refactor. Audit-Debug-Felder reduziert (2194-M).
  PB-49: Feature. GEMESSENER INHALT + CODE-PATCHES
         in commit_input (2191-R2).
  PB-50: Feature. Fail-closed bei leerem mess_protokoll
         in Phase 2 (2191-R2b).
  PB-51: Doku. Handoff auf PB-50.
  PB-52: Fix. reviewer.md Body an R7 angeglichen
         (2191-R3).
  PB-53: Doku. Handoff-Update 2199-Zwischenstand.
  PB-54: Doku. Handoff-Update 2199a als Auflage.
  PB-55: Doku. Handoff 2199 abgeschlossen, 2183 vor.
  PB-56: Feature. pipeline_ende mit llm_calls
         (2183-P4-Log).
  PB-57: Feature. pipeline_ende im Deadlock-Pfad
         (Nachtrag).
  PB-58: Doku. Handoff 2199 R7 bestaetigt.
  PB-59: Feature. pipeline_ende im basis_gate_
         nach_apply-Pfad (2183-P4-Log2).
  PB-60: Doku. Handoff P4-Log2 + Worst-Case.
  PB-61: Refactor. Zentraler pipeline_ende-Wrapper
         (2183-P4-Log2, endgueltig).
  (Hinweis: PB-62 bis PB-73 in der alten
   Liste waren manual, Tags entfernt. Siehe
   WICHTIG-Block oben. Der echte PB-62 ist
   jetzt der whois-Lauf vom 2026-10-14.)
  M-62: Feature. run_id im Audit (2200a).
  M-63: Feature. Audit-Aggregator (2200).
  PB-64: Chore. projects/*.memory.yaml ignorieren.
  (Hinweis: die Nummer PB-65 wurde 2026-10-15 neu
   vergeben: echter notify_ntfy-Test-Lauf. Siehe
   Session-Liste unten.)
  PB-66: Fix. R7-Phase-2-Toleranz + Aggregator
         mypy/ruff (2199-R7-P2).
  PB-67: Doku. Handoff auf PB-66.
  PB-68: Feature. Recovery-Zustand + Prompt-Block
         (2183 A1a).
  PB-69: Doku. Handoff auf PB-68.
  PB-70: Feature. code_entwurf_historie (2183 A1b).
  PB-71: Feature. rollback_vor_recovery +
         max_llm_calls 30 (2183 A1c).
  PB-72: Doku. Handoff auf PB-71.
  PB-73: Feature. SolverBefund-Klasse + run_id
         (2183 A2).
  PB-74: Doku. Handoff auf PB-73.
  PB-75: Feature. Trigger-Erkennung (2183 A3).
         zaehle_no_go_in_folge, recovery-Marker
         ab 2. NO-GO, recovery_hinweis_block
         neutral. +8 Tests, 301 passed.
  PB-76: Doku. Handoff auf PB-75.
  PB-77: Doku. Handoff-Korrektur nach PB-75.
         Doppelung b/e aufgeloest, P1 als
         Punkt a). Werkstatt-Vertrag-Merkposten.
  PB-78: Feature. P1 Gegenstandsvergleich
         (2183 A4/A5). jaccard_aehnlichkeit,
         gegenstand_gleich, _p1_schon_getriggert,
         _tokenisiere. zaehle_no_go_in_folge U8-
         angepasst. Audit solver_trigger mit
         jaccard/schwellwert/min_tokens/grund.
         solver_config im YAML. +10 Tests,
         311 passed.
  PB-79: Doku. Handoff auf PB-78 (2183 A4/A5).
  PB-80: Feature. Solver-Code (2183 B).
         agents/solver.md, HARD_RULES_SOLVER,
         parse_solver_diagnose, baue_solver_befund,
         rufe_solver, _letzte_zwei_entwuerfe,
         _solver_prompt_bauen. recovery_hinweis_
         block um befund-Parameter erweitert
         (Option C). Solver-Call im Trigger,
         nur bei P1_GRUND_GETRIGGERT, eigenes
         Budget-Gate. X7: kein Builder-Kanal
         (B2 separater Block). +14 Tests,
         325 passed.
  PB-81: Doku. Handoff auf PB-80 (2183 B).
  PB-82: Feature. COMMAND: RUN solver (2183 C).
         ERLAUBTE_QUELLEN um reviewer_command.
         SOLVER_ARG_MAX_LEN=200. RunState.
         solver_trigger_quellen. _handle_
         solver_command (Duplikat, Budget,
         Fail-closed, Marker). Phase-1-Loop
         in Reihenfolge. Phase-2-Audit bei
         solver-Versuch. P1-Audit mit quelle.
         +8 Tests, 333 passed.

Auflagen dieser Session:
  2186: KUERZUNGS-MARKER
  2187: Builder-COMMAND-Loop
  2188: builder.md KUERZUNGS-MARKER respektieren
  2189: Pfad-Woertlichkeit + Fehler-Marker
  2190: GEMESSENER INHALT als primaere Quelle
  2191: Prompt pro Runde frisch
  2192: Werkstatt messt automatisch
  2193: zurueckgezogen (Modellwechsel)
  2194: Audit-Debug (Diagnose)
  2195: Private IPs nicht mehr redigieren (WURZEL)
  2196: collect_messwerte bevorzugt nach-apply
  2197: Fail-closed-Rollback
  2198: collect_messwerte-Regex an Kuerzung
  2185: README komplett, 6 Rollen inkl. Solver
        (nachgezogen 2026-10-15, Commit da50145)
  2183-B3: Solver-Wissensbasis (Solver sieht
        Projekt-Doku wie Reviewer). Kategorie 3,
        Reviewer-Block GO mit FF1-FF8. Commit
        d706e66. +4 Tests, 350 passed.
  2183-B5: Solver-Loop + Fail-Pfade. Variante X
        mit GG1-GG5. max_solver_runden=3, Zaehler
        solver_aufrufe, Historie im Solver-Prompt.
        Commit 0b19bcb. +5 Tests, 355 passed.
  PB-63 (2026-10-15): notify_ntfy auf Konvention
        umgestellt. Erster echter Lauf nach Neudefinition
        mit sauberem Werkstatt-Stand. Commit 8db36f7,
        Tag probebetrieb-63. Runden 2, llm_calls 7, rc 0.
  Feldtest PB-64 (Feld, 2026-10-15): Auftrag bereits
        erfuellt. Drei Laeufe:
        - Lauf 1 (11:04): Deadlock, kein Solver-Trigger
          im Deadlock-Pfad. rc=19.
        - Lauf 2 (11:21): Solver gerufen, aber UNKLAR
          (Solver-Prompt ohne Auftrag). rc=19.
        - Lauf 3 (11:26): Solver gerufen, ANDERER_FEHLER
          (Auftrag bereits erfuellt). B2 greift, rc=0,
          kein Commit. Ziel-Repo unveraendert 8db36f7.
        Loesung: Block Auftrag-erfuellt (B1-B5) +
        Solver-Prompt-Auftrag (Commit 3cf7404).
  Block Auftrag-erfuellt: ERLEDIGT 2026-10-15.
        B1 (wirkungslos), B3 (Signal), B4 (Trigger C),
        B2 (Pipeline-Pfad), B5 (Deadlock-Solver),
        A2 (solver.md-Hinweis), AUFTRAG-Block.
        Commits a0d436b, 183f560, 0f6442d, 7fdaffa,
        3cf7404. +24 Tests, 407 passed.
  PB-65 (2026-10-15): notify_ntfy — acht Tests fuer
        ToolArgumentValueError. Erster Lauf im normalen
        Erfolgspfad nach Auftrag-erfuellt. Code-GO Runde 1,
        Commit-GO, kein Solver-Trigger. Commit 2aa2b0b,
        Tag probebetrieb-64. 13 passed in test_notify_ntfy.
  Agent-Memory Ebene 1: ERLEDIGT 2026-10-15.
        Aggregator sammelt projekt_stand aus git log
        (letzte 5 Commits, Quelle werkstatt/mensch).
        Prompt-Bau zeigt ## PROJEKT-STAND in Builder,
        Reviewer, Solver (nach AUFTRAG).
        main laedt memory.yaml (UU6 fail-closed korrupt).
        Aggregator-Aufruf nach pipeline_ende (TT2).
        Commits 4e23aba, 52cd658. +16 Tests, 423 passed.
  Stufe 0 (Selbstheilung): ERLEDIGT 2026-10-15.
        A1+1b: pruefe_anker_gegen_messung + pruefe_
        ersatz_gegen_messung (deterministisch).
        A2: Builder-Rueckmeldung mit Mess-Chance.
        A4: Deadlock-Differenzierung (3 Faelle).
        A3: Solver-Trigger A+B. Commits b5f3073,
        5bafc02, f4a8378, 737afe9. +28 Tests.
        383 passed.

================================================================
5. OFFENE AUFLAGEN UND MERKPOSTEN
================================================================

KRITISCH: keine.

WICHTIG (naechste Session):
  2183: Solver-Agent (vorgezogen, siehe MITTEL).
        Nachster Bau-Block. Siehe MITTEL-Eintrag
        fuer Design P1-P9.
        Vorbedingung P4 erfuellt (2183-P4-Log,
        PB-56 + PB-57 + PB-59): pipeline_ende mit
        llm_calls an 10 Pfaden.
        Messung 17:31: mittlerer Fail-Lauf
        (commit_no_go_max): rc=7, llm_calls=11.
        Lauf 17:48 (basis_gate_nach_apply): ohne
        Endlog (Pfad fehlte, PB-59 nachgezogen).
        Lauf 17:57 (eskalation): ohne Endlog
        (Pfad fehlt noch, siehe 2183-P4-Log2).

  2199-L: Livelock-Fall (neu aus 2199-Lauf 3).
        Drei 2199-Laeufe, R7 in keinem getriggert.
        Lauf 3 (dns_lookup_reverse): 5x NO-GO,
        Fail-closed. Reviewer-Diagnose: Struktur-
        Fehler (Patch 1 ersatz == anker) und
        Auftrags-Ambiguitaet, in derselben Runde
        bewertet, kein Fortschritt. Ohne Solver
        laeuft der Loop 5x ins Leere.
        Loesung: 2183. Kategorie 3.

  2199: ABGESCHLOSSEN (R7 wirkt).
        Drei Laeufe ohne R7-Trigger. Vierter Lauf
        (leerer hostname, 17:31): R7 hat in Phase 2
        (Commit-Review, Stufe 3) getriggert. Der
        Commit-Reviewer erkannte, dass das Commit-
        Paket Aenderungen behauptet, die nicht im
        GEMESSENER INHALT stehen. COMMIT-NO-GO 2x,
        Fail-closed mit Rollback. -> 2191-R2 wirkt.
        Restfall 2199-R7-P1: Phase-1-R7-Wirkung
        weiter unbetaetigt.

  2183-P4-Log2: Zentraler pipeline_ende-Wrapper.
        ERLEDIGT (PB-61). run_pipeline nimmt
        state_ref: list[RunState]. main ruft
        _pipeline_ende im finally. 10 verstreute
        Aufrufe entfernt. Verifikation:
        _pipeline_ende genau 2 Fundstellen.

  2183-P4-Wert: 30 als max_llm_calls.
        Datenlage (2200-Aggregator, PB-63):
        llm_calls min=3 max=11 median=7
        (samples=3). Worst Case mit Solver +
        Recovery: 18-20. 30 konservativ.
        Umsetzung mit 2184.

  2183 A1a (Recovery-Zustand): ERLEDIGT (PB-68).
        Marker recovery an review_runden.
        formatiere_runden(), recovery_hinweis_block().
  2183 A1b (code_entwurf_historie): ERLEDIGT (PB-70).
        Feld + record_code_entwurf().
        Kuerzung auf 10 Eintraege.
  2183 A1c (rollback_vor_recovery + 2184):
        ERLEDIGT (PB-71). Neue Funktion
        rollback_vor_recovery (ungenutzt bis A3).
        max_llm_calls-Defaults 20 -> 30.
  Solver-Kurskorrektur 2026-10-14:
        Der Solver-Agent unterstuetzt den
        Builder-Agenten (nicht den Reviewer,
        nicht den Menschen).
        Block 1 (Konzept): ERLEDIGT.
        Block 2 (solver.md + HARD_RULES_SOLVER):
        ERLEDIGT (Commit d415e9e).
        Block 2a+4 (Befund-Kanal):
        ERLEDIGT (Commit 1cb266c).
          - recovery_hinweis_block: hat_befund
            statt befund. Reviewer sieht nur
            neutralen Hinweis (W6, BB1).
          - _solver_befund_block: Befund im
            Builder-Prompt (NO-GO-Pfad),
            Audit bei verworfenem Befund
            (DD9, EE1).
          - _bauer_auflagen_prompt unveraendert
            (DD5).
        Block 3 (Wissensbasis): ERLEDIGT
        (Commit d706e66). Solver sieht dieselbe
        Projekt-Doku wie der Reviewer (S9).
        agent_docs.solver = reviewer-Set.
        Block 5 (Solver-Loop + Fail-Pfade):
        ERLEDIGT (Commit 0b19bcb, Variante X mit
        GG1). max_solver_runden=3 (YAML),
        RunState.solver_aufrufe zaehlt Versuche,
        Audit solver_max_runden_erreicht,
        Solver-Prompt zeigt FRUEHERE SOLVER-BEFUNDE
        (nur Diagnose-Zeile, B5-M1).
        F1-F4 als Merkposten (MITTEL).
        Block 6 (Smoke-Test): OFFEN.
        Zwischenzustand CC10 aufgeloest:
        echte Laeufe wieder erlaubt.

  2183 C (COMMAND: RUN solver): ERLEDIGT (manual,
        Commit 9a5a17f; PB-82 war manual, Tag entfernt).
        ERLAUBTE_QUELLEN um reviewer_command.
        SOLVER_ARG_MAX_LEN=200 (F6, kuerzen
        statt reject). RunState.solver_trigger_
        quellen. _solver_prompt_bauen(grund)
        + rufe_solver(grund_text) (Y6). _handle_
        solver_command (Duplikat Y4, Budget X5,
        Fail-closed F3, Marker Y3). Phase-1-
        Loop in Reihenfolge (Y1). Phase-2-Audit
        reviewer_run_solver_phase2_ignoriert
        (Y2). P1-Audit mit quelle=p1_trigger.
        +8 Tests, 333 passed.

  2183 B (Solver-Code): ERLEDIGT (manual,
        Commit 47a9a8b; PB-80 war manual, Tag entfernt).
        agents/solver.md (Rolle, HARD_RULES_
        SOLVER S1-S7). Parser parse_solver_
        diagnose (Fallback UNKLAR). baue_
        solver_befund, rufe_solver, _letzte_
        zwei_entwuerfe (X8), _solver_prompt_
        bauen. recovery_hinweis_block um
        befund-Parameter erweitert (Option C,
        X1/X2). Solver-Call nur bei GETRIGGERT
        (X6), eigenes Budget-Gate (X5). Bei
        Fail: Marker zurueck (X3), audit
        solver_failed. X4: Parser-Fehler ist
        UNKLAR, kein Fail. V6: ANDERER_FEHLER
        ist legitim. X7: B baut keinen Builder-
        Kanal, praezisierter_auftrag landet in
        state.solver_befunde. Builder-Kanal B2
        separater Block. +14 Tests, 325 passed.

  2183 A4/A5 (P1 Gegenstandsvergleich):
        ERLEDIGT (PB-78). jaccard_aehnlichkeit,
        gegenstand_gleich, _p1_schon_getriggert,
        _tokenisiere. zaehle_no_go_in_folge
        zaehlt Recovery-Runden nicht (U8).
        Audit solver_trigger immer, mit
        jaccard/schwellwert/min_tokens/grund
        (U6/U7/V3). solver_config im YAML (U3):
        p1_schwellwert=0.5, p1_min_tokens=10.
        U1: Annaeherung im Docstring dokumentiert.
        Fehler 3 (U8 still wirkungslos) durch
        Test aufgedeckt, behoben. V4: Stopwort-
        Liste um 3-Zeichen-Woerter ergaenzt.
        +10 Tests, 311 passed.

  2183 A3 (Trigger-Erkennung): ERLEDIGT (PB-75).
        zaehle_no_go_in_folge(), recovery-Marker
        ab 2. NO-GO in Folge, audit("solver_trigger").
        recovery_hinweis_block() neutral (kein
        Solver-Befund). ACHTUNG (T1): Ohne P1
        triggert der Marker auch bei ANDERER_FEHLER;
        Solver-Pfad (B) muss tolerant sein (P6).

  Bug-Fix 2026-10-14 (GEMESSENER INHALT nach Apply):
        ERLEDIGT (Werkstatt-HEAD dd0e111).
        mess_protokoll_veraltet-Flag. Phase 1:
        Header + Nach-Apply-Block. Commit-Review:
        nur Nach-Apply-Block. Erster echter Lauf
        mit dem Fix: PB-62, COMMIT-GO in Runde 1.

  2183 A2 (SolverBefund-Klasse): ERLEDIGT (PB-73).
        Enum SolverDiagnose, @dataclass
        SolverBefund, format_solver_befund.
        RunState.run_id und RunState.solver_befunde.
        10 neue Tests, 293 passed.

  2200 (Audit-Aggregator): ERLEDIGT (PB-63).
        werkstatt_aggregate.py liest JSONL,
        schreibt projects/<name>.memory.yaml.

  2200a (run_id im Audit): ERLEDIGT (PB-62).
        _AKTUELLE_RUN_ID modul-global.
        audit() schreibt run_id, wenn gesetzt.
        Format YYYYMMDD-HHMMSS-<pid>.
        Alte Events ohne run_id, Aggregator
        matcht dann per Zeitachse.

  2200b: --heute-Flag fuer Aggregator
        (Kalendertag statt 24h). Merkposten.

  2200c: Pipeline ruft Aggregator nach
        pipeline_ende automatisch. Merkposten.

  2200-T: Test fuer Aggregator.
        Synthetisches Audit-Log, Aggregation
        pruefen. Merkposten.

  2199-R7-P2: ERLEDIGT (PB-66).
        reviewer.md PHASE 2 Punkt 6:
        vier Stufen. Stufe 2a/2b -> COMMIT-GO
        mit Bemerkung. Nur Stufe 3 -> NO-GO.
        Kein COMMAND in Phase 2.

  Owner-Regel: Nach jedem manuellen
        git checkout/reset im Zielprojekt:
        chown -R builder:builder /opt/security-ai/.
        Sonst Permission denied beim naechsten
        Werkstatt-Lauf. Als Werkstatt-Regel
        dokumentieren.

  P6-Regel: mypy ab jetzt rekursiv pruefen
        (mypy /opt/werkstatt/), nicht nur
        pipeline.py. PB-63 hatte 2 Fehler
        in werkstatt_aggregate.py, die durch
        die enge Pruefung nicht auffielen.
        Als Werkstatt-Regel dokumentieren.

  tests-mypy: tests/test_pipeline.py hat
        139 mypy-Fehler (fehlende
        Annotationen in Test-Methoden).
        KORREKTUR (PB-75): Bei PB-75 gemessen:
        151 Fehler (nicht 139). Differenz 12.
        Alle vor Zeile 3739 (vor A3-Tests).
        A3-Tests selbst: mypy-sauber.
        Altes Problem, eigener Block.
        Kategorie 2. Siehe tests-mypy-151.

  tests-mypy-151: 151 Fehler in
        tests/test_pipeline.py (nicht 139
        laut Handoff-Kopf). Differenz 12:
        entweder neu seit PB-45 oder
        Zaehlfehler. Alle vor Zeile 3739.
        Eigener Block. Kategorie 2.

  Phase-2-COMMAND-Schleichpfad:
        classify_verdict erkennt COMMAND in
        Phase 2, aber der Loop bricht bei
        "!= COMMIT-NO-GO" ab. Kein Fail,
        kein Log. Merkposten.

  2183-AQ: Auftragsqualitaet vor Werkstatt-Lauf.
        Neue Auflage (aus 2199-Lauf 3 + Lauf
        network_interfaces/Deadlock). Auftraege,
        die Verhalten annehmen, das im Zielcode
        nicht existiert, enden in Livelock oder
        Deadlock. Loesung: vor jedem Lauf pruefen,
        ob der Auftrag gegen den Zielcode passt.
        Messung: grep -n 'def .*_run' tools/*.py
        und grep -rn 'ToolArgumentValueError' tools/.
        Kategorie 3.

  2199a: Recovery-Pfad post-apply-Basis-Gate.
        AUFLAGE (hochgestuft aus Merkposten).
        Zwei 2199-Laeufe in Folge mit demselben
        Muster: post-apply-Basis-Gate rot,
        Reviewer-Vorschlag liegt vor, Loop wendet
        nicht an, Mensch muss manuell abschliessen.
        Reviewer-Entscheidung: Option 3, aber erst
        Zustandsmaschine.
        Schritt A (Zustandsmaschine): Klaeren
          - Recovery-Lauf vs. normaler Builder-Lauf.
          - Zaehlung in state.review_runden?
          - Reviewer sieht Recovery als neue Runde?
          - max_llm_calls-Zaehlung.
          - Strukturierter Ort fuer Reviewer-
            Vorschlag in state (heute Freitext?).
        Schritt B (Recovery-Zweig):
          Trigger: Basis-Gate rot UND Reviewer-
            Verdict mit strukturiertem Vorschlag.
          Nicht bei rot ohne Vorschlag (Fail-closed).
          Max 1 Recovery-Zyklus, dann Fail-closed.
        Verworfen: Option 1 (Lint-Auto-Repair,
          Verantwortungsfrage offen), Option 2
          (mypy hat kein --fix).
        Kategorie 3.

  2191-R2b-T: Test fuer commit_review_ohne_messung.
           main() ist nicht isoliert testbar. Test-
           Harness muss erst gebaut werden. Eigener
           Block. Kategorie 2.

  2191-R4: Builder-Prompt (Zeile 2344) hat GEMESSENER
           INHALT nach ZIELDATEIEN. Reviewer-Prompt
           (Zeile 2424) hat ihn jetzt davor. Inkonsistenz
           bewusst? Kategorie 2.


ZIELE (2026-10-15, laengerfristig)
---------------------------------

Ziel 1 — Autonomie bis Approval.
        Die Werkstatt soll grosse Arbeitspakete
        (Phasen mit 10+ Unterkategorien)
        eigenstaendig abarbeiten. Der Mensch
        greift nur am Approval-Gate ein.

Ziel 2 — Deterministisch vor LLM.
        Wo eine Regel entscheiden kann, ent-
        scheidet Code. LLM nur wo Urteils-
        vermoegen noetig ist.

Ziel 3 — Ordner-/Doku-Schema + Scaffolder.
        security-ai ist historisch gewachsen.
        Fuer Scaffolder (anlegen, migrieren,
        konsolidieren) braucht es eine Vorlage.
        Konsolidierung: Dopplungen finden
        (deterministisch), aehnliche Dokumente
        zusammenfuehren (LLM), Mensch bestaetigt.

Ziel 4 — Dashboard (spaeter).
        Web-Ansicht, die den Werkstatt-Prozess
        live zeigt: Builder, Reviewer, Solver,
        Test-Generator, Patches, Verdicts.
        Funktionen:
        - Live-Ansicht (WebSocket/SSE aus dem
          Audit-Log).
        - Konversations-Fenster zwischen allen
          LLMs in Echtzeit.
        - Grafische Prozess-Darstellung
          (State-Diagramm).
        - Lauf starten (Eingabefeld + Button).
        - ASK_HUMAN-Kanal: Agent stellt Frage,
          Lauf pausiert, Mensch antwortet.
        Voraussetzungen:
        - Audit-Log um vollstaendige Prompts/
          Replies erweitern (mit Redaction).
        - Event-Katalog standardisieren.
        - Web-Layer (kleiner HTTP-Server).
        Reihenfolge: nach Agent-Memory (Ebene
        1+2) und Audit-Erweiterung.

STUFE 0 (Selbstheilung) — ERLEDIGT 2026-10-15.
        Deterministische Anker-/Ersatz-Pruefung,
        Builder-Rueckmeldung mit Mess-Chance,
        Solver-Trigger A+B, Deadlock-
        Differenzierung. Commits b5f3073 bis
        737afe9.

MITTEL (Merkposten):

  Auftrag bereits erfuellt (Feldtest PB-64, 2026-10-15):
        STATUS: ERLEDIGT in Commits a0d436b bis 3cf7404.
        Die folgende Beschreibung dokumentiert den
        urspruenglichen Befund:
        Die Werkstatt hat keinen Pfad fuer "Auftrag ist
        bereits erfuellt". Beobachtet:
        1. Der Builder hat korrekt erkannt: "Die Datei
           entspricht bereits der Konvention, kein Patch
           noetig." (reply_fuss, run 20261015-104113).
        2. Der Builder lieferte einen Patch mit anker ==
           ersatz (wirkungslos).
        3. Der Reviewer gab GO, obwohl HR5 (ersatz !=
           anker) verletzt ist und der Fuss explizit
           "kein Patch noetig" sagte.
        4. Stufe-0-Trigger greift nicht: der Anker steht
           wortwoertlich im mess_protokoll, nur der Ersatz
           ist identisch.
        5. Kein Solver-Trigger. Commit-Paket leer ->
           Commit-NO-GO 2x -> rollback_fail_closed rc=7.
        Loesung (eigener Block, Kategorie 3):
          - pruefe_anker_gegen_messung um anker == ersatz
            erweitern (Grund "wirkungslos").
          - Reviewer-Prompt: HR5-Pruefung explizit.
          - Pipeline-Pfad "Auftrag bereits erfuellt":
            rc=0, Audit auftrag_bereits_erfuellt, kein
            Commit, kein Tag.
          - Solver-Trigger erweitern (wirkungslos / kein
            Patch noetig).

  II2b (Substring-Kollision): Ersatz-Pruefung
        nutzt Substring-Match (modul in mess_
        protokoll). Kollisionen bei Modulnamen,
        die Praefix eines laengeren Modulnamens
        sind, werden nicht erkannt. Bei erster
        realer Kollision: Wortgrenzen oder
        exakter Match.

  II5b (Audit-Fuss-Kuerzung): _audit_builder_
        reply kuerzt den Fuss auf 200 Zeichen.
        Rueckfragen im Fuss sind dadurch nur
        teilweise sichtbar. Vorschlag: auf
        redigiert[-1000:] erweitern, damit
        Rueckfragen messbar sind.

  II6b (Inhaltswort-Kalibrierung): Die Liste
        INHALTSWOERTER_TRIGGER_B ist eine
        Setzung. Nach 5-10 PB-Laeufen:
        echte Rueckfragen klassifizieren,
        Liste anpassen. >20% False Positives
        -> verschaerfen. >20% echte Rueckfragen
        nicht getriggert -> lockern.

  F1 (Solver-Frequenz): ERLEDIGT in Block 5
        als (c) max_solver_runden=3 ohne
        bool-Blockade. COMMAND-Pfad bleibt
        _solver_schon_gelaufen (einmal pro Lauf).
        Asymmetrie bewusst: P1-Trigger automatisch
        mehrfach (bis max_runden), COMMAND manuell
        einmal.

  F2 (Fail-closed bei rufe_solver-Fehler):
        Merkposten. Vorschlag max_rufe_solver_
        fehler = 2. Nach 5-10 PB-Laeufen mit Solver
        kalibrieren. Heute X3-Marker zurueck.

  F3 (Fail-closed bei unvollstaendigem Befund):
        Merkposten. Bleibt (a): leerer Block +
        Audit solver_befund_verworfen. Fail-closed
        nur erwaegen, wenn Quote >20%.

  F4 (_bauer_auflagen_prompt): Merkposten.
        DD5 bleibt. Solver-Befund nur im NO-GO-
        Prompt. Ueberdenken, wenn Auflagen-Pfad
        haeufiger failt.

  B5-M1 (Historie-Block Umfang): Der Solver-
        Prompt zeigt in FRUEHERE SOLVER-BEFUNDE
        nur DIAGNOSE: <art.name>, nicht den
        Volltext. Grund: format_solver_befund
        kann ValueError werfen bei unvollstaen-
        digem Befund, das wuerde den Prompt-Bau
        abbrechen. Nach ersten PB-Laeufen pruefen,
        ob Volltext gebraucht wird.

  B5-M2 (Trigger-Pfad-Test): test_max_solver_
        runden_blockt_nach_3 prueft nur die
        Zaehl-Logik, nicht den vollen Trigger-Pfad.
        Voller Test steht aus, braucht RunState
        mit Review-Runden bis zum Trigger.

  Solver-Kurskorrektur Merkposten:
        W10 (Befund-Historie): Builder-Prompt
             nur letzter Befund. Solver-Prompt
             (bei Runde > 1) Historie.
             Reviewer-Prompt nichts. Umgesetzt
             fuer Builder + Reviewer. Solver-
             Historie kommt mit Block 5.
        W12 (Rollen-Vertrag): sechste Rolle
             "solver" mit Auftraggeber-
             Beschreibung. Nach Block 5.
        P4-nach-Solver: max_llm_calls nach 5-10
             PB-Laeufen mit Solver neu messen.
             Nicht auf Verdacht erhoehen (F6).
        max_solver_runden-Kalibrierung:
             3 ist Setzung (F5). Nach 5-10
             PB-Laeufen kalibrieren.
        solver_befunde-Eingrenzung: haengt an
             RunState-Lebensdauer (BB3). Bei
             persistentem State auf run_id
             filtern.
        Audit-Kanal Solver-UNKLAR: heute nur
             Audit-Log (Frage 5, CC). Am
             Approval-Gate anzeigen? Block 5.

  B2 — Builder-Kanal fuer Solver-Befund.
        Kategorie 3. Aus 2183 B (X7).
        Der praezisierte_auftrag (Diagnose
        ANDERER_FEHLER) landet heute nur in
        state.solver_befunde und im Reviewer-
        Prompt. Der Builder sieht ihn nicht.
        Offene Fragen: wo im Builder-Prompt,
        mit welchem Gewicht (verbindlich vs.
        Hinweis), was bei Widerspruch zum
        Auftrag. Nach 2183 C.

  U4-Kalibrierung (P1): Schwellwert 0.5
        und min_tokens 10 sind Setzungen,
        nicht Messungen. Nach ersten PB-
        Laeufen mit P1: echte NO-GO-Paare
        labeln (gleicher/anderer Gegenstand),
        Jaccard-Verteilung messen, Schwell-
        wert neu setzen. Kategorie 3.

  P4-nach-P1-B (llm_calls): P1 reduziert
        den Trigger. Wirkung nicht gemessen.
        Sobald B (Solver) gebaut ist und
        Calls verbraucht: llm_calls neu
        messen. Wenn median/max deutlich
        unter den heutigen 7/11 liegen,
        kann max_llm_calls in 2184 nach
        unten korrigiert werden.

  Werkstatt-Vertrag (2183). Kategorie 3.
        Fuenf Vertraege zusammenfuehren:
        1. Anker-Vertrag (woertlich |
           Kuerzungs-Marker | +2-Shift;
           drei Konsumenten).
        2. Auftrags-Vertrag (Auftrag
           gegen Zielcode geprueft).
        3. Patch-Vertrag (PATCH-BEGINN/
           ENDE, whitelist, count == 1,
           ersatz != anker).
        4. Fail-Vertrag (rc-Semantik,
           Audit-Events, Endlog, Rollback).
        5. Rollen-Vertrag (wer darf was,
           inkl. solver, scaffolder).
        Plus docs/KONVENTIONEN.md.
        Format: docs/WERKSTATT-VERTRAG.md
        + .yaml (maschinenlesbar).
        Zeitpunkt: NACH 2183 B und C.
        Offene Design-Fragen W1-W4:
          W1 Eigentuemer (Auftraggeber
             inhaltlich, Bau-Chat Konsistenz,
             Reviewer prueft).
          W2 Sanktion bei Verletzung:
             Fail-closed, im Vertrag.
          W3 Versionierung: Version im YAML,
             im Audit-Log jedes Laufs.
          W4 Bezug zu Auflagen: bei Wider-
             spruch gewinnt die Auflage, bis
             sie zurueckgezogen wird.
        Migration in 6 Schritten (Vertrag-
        Doc, Patch+Anker, Auftrag, Fail,
        Rollen, Konventionen), je Kategorie 3.
  2183: Solver-Agent. VORGEZOGEN nach WICHTIG
        (siehe oben). Design P1-P9:
        - P1: Schwellwerte Levenshtein/Token-Overlap.
        - P2: Dosierung Befund.
        - P3: COMMAND: RUN solver erst nach Stabilisierung.
        - P4: max_llm_calls erst messen.
        - P5: Trigger-Vorbedingung (gleicher Gegenstand).
        - P6: Solver darf 'kein Handlungsbedarf' melden.
        - P7: Fail-closed + Rollback (Lehre 4).
        - P8: Historisierung code_entwurf messen.
        - P9: Format SOLVER-BEFUND definieren.
        Trigger: NO-GO 2, wenn NO-GO 1 und NO-GO 2
        denselben Gegenstand betreffen (P5).
        Befund an Reviewer (voll) und Bau-Chat
        (nur praezisierter Auftrag).
        Kategorie 3. Groesserer Umbau.
  2184: max_llm_calls 20 -> 30.
        Begruendung aus P4-Messung:
        - Einfacher Lauf: ~5 Calls.
        - Mittlerer Fail-Lauf: 11 Calls (gemessen).
        - Livelock: ~13 Calls.
        - Mit Solver: +1-2. Mit 2199a-Recovery:
          +2-4. Reserve Faktor 2.
        30 ist aus Messung abgeleitet, nicht geraten.
        Umsetzung mit 2183.
  2187b: read_file Zeilenbereich (fuer sehr grosse Dateien).
  2188a: agents/*.md konsolidieren (Widersprueche durch
         anhaengende Auflagen).
  2188c, 2189c, 2190b-M, 2191-M2, 2192-M2, 2198-M,
  2198-M2: Merkposten zum "Feature + Prompt +
         Aktualisierung"-Muster. Konsolidieren in eine
         Werkstatt-Regel.
  2190-M: Reviewer-Auswahl-Logik (Schritt 1) pruefen.
  2192-M1: execute_commands prueft, ob Pfad schon
         vollstaendig gemessen.
  2195-M2: MAC-Redaction rechtfertigen oder entfernen.
  2195-M3: Anker mit gemischten privaten/oeffentlichen IPs.

NIEDRIG:
  Audit-Log-Ausbau dauerhaft (statt Debug-Felder).
  Tag-Verwirrung: Ziel-Repo-Tags 1-24 auf f913eac,
  25-28 auf dd3048b. Werkstatt-Tags 7, 17, 29-53.
  Vereinheitlichen.

================================================================
6. WIE MAN WEITERARBEITET
================================================================

Regeln fuer jeden Bau-Block:

1. Faktenlage vor Meinung. Keine Datei-Inhalte
   annehmen. Immer cat/sed/grep zum Messen.

2. Patch per Python-Skript mit assert count == 1.
   Kein sed auf Python-Code. Kein Heredoc >3 KB.

3. Nach jedem Patch: wc -l, py_compile, ruff,
   mypy, pytest.

4. Vor jedem Commit: git status --porcelain
   pruefen.

5. Commit-Autor immer ghxstfocus
   <ghxst.focus@gmail.com>.

6. Bei Kategorie 3: Reviewer-Block vor Commit.

6a. Probebetrieb-Tag NUR bei echtem Pipeline-
    Durchlauf. Beleg: pipeline_start UND
    pipeline_ende im Audit-Log (Projekt
    security-ai). Manual-Sessions werden
    NICHT getaggt. Neue Regel seit 2026-10-14.

7. Nach jedem Meilenstein: dieses Handoff
   aktualisieren.

8. Reviewer-Blocks in Codeblock.

9. Kein Scope-Creep. Jede Auflage als eigener
   Block.

10. Am Ende jeder Session: git status sauber,
    dieses Handoff aktuell.

Reviewer-Chat:
  - Der Reviewer-Chat ist ein separater
    Web-Chat (nicht der Bau-Chat).
  - Kategorie 3: Code VOR Ausfuehrung an
    den Reviewer.
  - Kein Improvisieren nach NO-GO.

================================================================
7. WERKZEUGE UND BEFEHLE
================================================================

ruff:   /opt/security-ai/.venv/bin/python3 -m ruff check ...
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

Reviewer-Block nach Kategorie 3:
  Datei in /tmp/ schreiben, mit cat anzeigen,
  in Reviewer-Chat kopieren.

================================================================
8. GIT-STATUS
================================================================

Werkstatt-Repo: /opt/werkstatt/.git
  Branch: main
  Remote: git@github.com:ghxstfocus/werkstatt.git
  .gitignore: Cache, .venv, audit-logs/,
              approvals/*.db, *.env.

Ziel-Projekt (security-ai):
  Repo: /opt/security-ai/.git
  Erster Werkstatt-Commit: dd3048b
  Zweiter Werkstatt-Commit: 3ccb883

Hinweis: Der Werkstatt-Lauf benoetigt Schreibrechte
des builder-Users im Ziel-Projekt. Nach manuellen
git-Eingriffen als root: chown builder:builder pruefen.

================================================================
9. HARD RULES (HR1-HR10)
================================================================

Seit Auflage 2182 sind die HARD_RULES rollenspezifisch
getrennt:
  - HARD_RULES_BASE (universell: HR1, HR7, HR8, HR9, HR10).
  - HARD_RULES_REVIEWER (R1-R6).
  - HARD_RULES_BUILDER (B1-B10).
  - HARD_RULES_TEST_GENERATOR (T1-T4).
build_system_prompt waehlt anhand des Agent-Namens.

HR2-HR6 sind entfallen. Ihre Inhalte stehen in B6-B9.

B4 (wichtig): "Du bist kein Messender. Die Werkstatt
ist der Messende." Wird seit Auflage 2192 durch
ensure_ziel_gemessen automatisch durchgesetzt.

================================================================
10. HARD RULES FUER DEN REVIEWER-CHAT (HR-R1 bis HR-R10)
================================================================

Unveraendert. Siehe vorherige Handoff-Version
(Bau-Handoff-2026-10-12.md.alt, Abschnitt 10).

HR-R1. Faktenlage vor Meinung.
HR-R2. Bestandsaufnahme vor Reviewer-Block.
HR-R3. Auflagen-Nummern global fortlaufend.
HR-R4. Reviewer-Blocks immer in einen Codeblock.
HR-R5. Kategorie 3 nur mit vorherigem Reviewer-Block.
HR-R6. Wenn unsicher: ESKALATION.
HR-R7. Fehler anerkennen, korrigieren, dokumentieren.
HR-R8. Kein Scope-Creep.
HR-R9. Fail-closed.
HR-R10. Kein "das haben wir schon immer so gemacht".

================================================================
11. ANTWORTFORMATE DES REVIEWERS
================================================================

GO:
    GO
    Grund: <kurz>
    Bemerkung: <optional>

NO-GO:
    NO-GO
    Grund: <konkreter Punkt>
    Empfehlung: <wie richtig>
    Verweis: <Design-Entscheidung / Doc>

ESKALATION:
    ESKALATION
    Frage: <was>
    Warum: <warum unsicher>
    Vorschlag: <was du empfiehlst>

================================================================
12. NAEECHSTE SCHRITTE (konkret)
================================================================

Der neue Bau-Chat soll:

1. Diesen Handoff lesen. HEAD pruefen:
     git -C /opt/werkstatt log -1 --oneline
     git -C /opt/werkstatt status --porcelain
     /opt/security-ai/.venv/bin/python3 -m pytest \
       /opt/werkstatt/tests/ -q

2. docs/PROTOKOLL-29-40.md lesen.

3. Reihenfolge (Stufe 0 + Auftrag-erfuellt + PB-65
   + Memory-E1 erledigt 2026-10-15):
   a) PB-66 mit echtem Auftrag. Test des PROJEKT-
      STAND-Blocks im Feld.
   b) Block "Anti-Pattern-Bibliothek" (Teil B,
      Kategorie 3, Ziel 5).
   c) Block "Migration WORKFLOW.md -> katalog.yaml"
      (Teil C).
   d) Block "Agent-Memory Ebene 2" (Run-Memory,
      Phasen-Fortschritt).
   e) Ziel 3: Ordner-/Doku-Schema + Scaffolder.
   f) Ziel 2: Phasen-Modus.
   g) Ziel 4: Dashboard.
   h) Solver-Kurskorrektur Block 6, 2183-AQ,
      2200b/c/T, 2199a, 2199-R7-P1, Werkstatt-Vertrag.

4. Fuer 2199, 2199a, 2183 Kategorie-3-Reviewer-
   Blocks formulieren. Vor Ausfuehrung.

5. Nach Erfolg (NUR echter Pipeline-Durchlauf):
   git tag probebetrieb-<n>. Naechste Nummer:
   63 (Stand 2026-10-15). PB-62 = 3bb5917.

6. Bei Problemen: zurueck zu diesem Handoff,
   Faktenlage pruefen, Reviewer-Chat fragen.

================================================================
ENDE DES HANDOFFS
================================================================
