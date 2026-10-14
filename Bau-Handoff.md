# Bau-Handoff — Werkstatt

Stand: 2026-10-14 (nach Probebetrieb 82)
Werkstatt-HEAD: 9a5a17f (Tag probebetrieb-82)
Letzter Commit in security-ai: 35e5178
Branch: main
Tests: 333 passed
ruff: 0
mypy: 0

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
  HEAD 9a5a17f (probebetrieb-82, 2183 C)
  Tests: 333 passed
  ruff: 0, mypy: 0, git status sauber
  Remote: github.com/ghxstfocus/werkstatt.git (privat)

Ziel-Projekt security-ai:
  HEAD 35e5178 (dns_lookup IPv6-Feld, 2199-Zwischenstand 2)
  Vorgaenger 3ccb883 (Traceroute), dd3048b (PingError)
  git status sauber

Werkstatt-Tags (auf /opt/werkstatt):
  probebetrieb-7, -17, -29 bis -73

Ziel-Projekt-Tags (auf /opt/security-ai):
  probebetrieb-1 bis -28 (historisch, vor dieser Session)
  Der zweite Commit (3ccb883) hat keinen Tag bekommen
  (Werkstatt-Konvention: nur Werkstatt-Repo wird getaggt).

Dateien:
  - pipeline.py (3693 Zeilen, Stand 2183 C)
  - redaction.py (314 Zeilen, Stand 2195)
  - agents/*.md (5 Rollen)
  - projects/security-ai.yaml
  - tests/test_pipeline.py (4156 Zeilen, Stand 2183 C)
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
  PB-62: Feature. run_id im Audit (2200a).
  PB-63: Feature. Audit-Aggregator (2200).
  PB-64: Chore. projects/*.memory.yaml ignorieren.
  PB-65: Doku. Handoff auf PB-64.
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
  2183 C (COMMAND: RUN solver): ERLEDIGT (PB-82).
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

  2183 B (Solver-Code): ERLEDIGT (PB-80).
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


MITTEL (Merkposten):
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
  2185: README 6 Rollen dokumentieren. Mit 2183.
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

3. Reihenfolge:
   a) 2183-AQ Auftragsqualitaet.
      Kategorie 3.
   b) 2200b/c/T Aggregator-Verfeinerung.
   d) 2183-AQ Auftragsqualitaet.
   e) 2200b/c/T Aggregator-Verfeinerung.
   f) 2199a Zustandsmaschine (Kategorie 3).
   g) 2199a Recovery-Zweig.
   h) 2199-R7-P1 (Phase-1-R7-Wirkung).
   i) Werkstatt-Vertrag (nach 2183 B/C,
      siehe MITTEL).

4. Fuer 2199, 2199a, 2183 Kategorie-3-Reviewer-
   Blocks formulieren. Vor Ausfuehrung.

5. Nach Erfolg: git tag probebetrieb-<n>.

6. Bei Problemen: zurueck zu diesem Handoff,
   Faktenlage pruefen, Reviewer-Chat fragen.

================================================================
ENDE DES HANDOFFS
================================================================
