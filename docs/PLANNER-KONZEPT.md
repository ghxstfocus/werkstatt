# Planner-Konzept v4 (final)

Status: final, 2026-10-15.
Kein Bau, nur Design.

Adressat: Auftraggeber, Reviewer-Chat, Bau-Chat.

Umsetzung: Block P1 (Stufe 1) als naechster Schritt.
Siehe Abschnitt 13.

================================================================
1. ZWECK
================================================================

Die Werkstatt soll grosse Arbeitspakete (Phasen mit
10+ Unterkategorien) eigenstaendig abarbeiten. Heute
kann sie das nicht.

Der Planner-Agent schliesst die Luecke:
  - Auftrag aus dem Projektzustand ableiten.
  - Phase in logische Unterbloecke zerlegen.
  - Commit-Pakete sammeln und am Ende gesammelt
    pruefen.

================================================================
2. ROLLE DES PLANNERS
================================================================

## 2.1 Zwei Aufgaben, klar getrennt

Stufe 1 — Auftrags-Uebersetzer (RR-K14):
  Eingabe: roher Auftragstext.
  Ausgabe: praeziser Auftragstext.
  Keine Phasen. Kein Zerlegen.

Stufe 2 — Phasen-Planer:
  Eingabe: Phasentext.
  Ausgabe: Phase mit Unterbloecken.

## 2.2 Rollen-Setup

Bestandteil von Block P1:
  - agents/planner.md.
  - HARD_RULES_PLANNER (in pipeline.py).
  - Eintrag in state.agents.
  - Eintrag in agent_docs (welche Doku der Planner sieht).
  - Modell: deepseek-chat, Temp 0.0 (F1).

## 2.3 Was der Planner lesen darf

  planner:
    modus: manual | auto | off   # Default manual
    max_runden: 3
    docs:
      - status
      - roadmap
      - security_log
      - decisions
      - changelog
    file_whitelist:
      - docs/
      - tools/
      - core/
      - tests/

Reihenfolge (F2): docs, grep, Plan.

================================================================
3. HIERARCHIE
================================================================

  Phase      — zusammenhaengendes Arbeitspaket.
  Unterblock — Bau-Auftrag (run_pipeline-Runde).
  Unterpunkt — Arbeitsschritt im Unterblock.
  Patch      — konkrete Code-Aenderung.

QQ-K2: Unterpunkt : Patch = 0-N (nicht 1:1).

QQ-K1: Kein abhaengigkeiten-Feld. Phase atomar
(siehe Abschnitt 5). Reihenfolge implizit durch
Plan.

================================================================
4. STUFE 1 — PLANNER ALS PIPELINE-SCHRITT
================================================================

  pipeline.py --project security-ai --planner "<roher Text>"

Ablauf:
  1. Planner laeuft, liest planner.docs + grep.
  2. Formuliert praezisen Auftrag.
  3. Pipeline zeigt:
       === PLANNER-VORSCHLAG ===
       <Auftrag>
       [j] uebernehmen / [n] verwerfen / [e] editieren
  4. Bei [j]: normale Kette. [n]: erneut (max 3).
     [e]: Mensch editiert.
  5. Die bestehende Kette laeuft unveraendert.

RR-K9: Kein ASK_HUMAN in Stufe 1.

================================================================
5. STUFE 2 — PHASEN-MODUS
================================================================

Ablauf:
  1. pipeline.py --project security-ai --phase "<Text>"
  2. Planner zerlegt in Unterbloecke.
  3. Pipeline zeigt Phasenplan, Mensch bestaetigt.
  4. Pro Unterblock:
       - run_pipeline.
       - Patches anwenden.
       - Commit-Paket BAUEN, NICHT committen.
       - Sammeln in phase_commit_pakete.
       - Unterblock-NO-GO: weiterer Versuch.
       - Unterblock-Fail-closed: Phase bricht ab,
         Rollback, Bericht.
  5. Gesamt-Review (Reviewer prueft alle Pakete).
  6. PHASE-GO: alle Commits. Approval pro Phase.
  7. PHASE-NO-GO: Rollback. Bericht.

Phase ist ATOMAR.

## 5.1 Fehler-Szenarien (QQ-K7, RR-K12)

  Unterblock-NO-GO: kein Rollback, weiterer Versuch.
  Unterblock-Fail-closed: Phase bricht ab, Rollback.
  Exception mitten in der Phase:
    identisch mit Unterblock-Fail-closed
    (RR-K12).
  Phase-NO-GO: Rollback, Bericht.

## 5.2 Rollback-Strategie (QQ-K9, RR-K1, RR-K2, RR-K3)

RR-K3 — phase_start_head setzen:
  Vor dem ersten Unterblock.
  Nicht neu gesetzt bei Plan-Aenderung (Plan ist
  Werkstatt-Zustand, nicht Ziel-Repo).

RR-K1 — Rollback-Bedingung:
  git reset --hard nur, wenn:
    - HEAD == phase_start_head UND
    - git status ist clean.
  Sonst: kein Reset, Bericht.

RR-K2 — reset + clean:
  git reset --hard phase_start_head
  + git clean -fd fuer untracked Dateien, aber
    nur in file_whitelist-Pfaden.
  Sonst loeschen wir Dateien ausserhalb des
  Phase-Scopes.

## 5.3 Unterbrochene Pakete (QQ-K15)

  Verworfen. Im Bericht an den Menschen kompakt.

## 5.4 Unterblock ohne Patches (RR-F16)

  Wenn B2 (Auftrag bereits erfuellt) greift:
    Unterblock als "done", kein Fail.
  Sonst:
    Fail-closed.

## 5.5 Gesamt-Review-Ergebnis (F15)

  Drei Ablageorte:
    - Audit-Log "phase_gesamt_review".
    - phase.yaml: Status pro Unterblock.
    - Approval-Dokument am Ende (Konsolen-Output).

## 5.6 Plan-Korrektur durch Planner (RR-K6, RR-K7)

  Bei Phase-NO-GO:
    - Planner wird gerufen.
    - Bekommt: NO-GO-Begruendung + alten Plan +
      Pakete (kompakt).
    - Liefert korrigierten Plan.
    - ALTE phase_commit_pakete werden verworfen.

  Bei Konflikt Planner vs. Reviewer ohne Loesung
  (RR-K8): Mensch entscheidet.
  Drei Optionen:
    - Plan manuell editieren.
    - Phase abbrechen.
    - Phase mit geaendertem Auftrag neu starten.

================================================================
6. INTERAKTIONSMODI
================================================================

  Modus 1 — CLI (Stufe 1 + 2).
  Modus 2 — Dashboard-Button (Ziel 4, spaeter).
  Modus 3 — Chat (Ziel 4, spaeter).

## 6.1 ASK_HUMAN-Kanal (QQ-K12, QQ-K13)

Datei-basiert.

  Pipeline schreibt:
    /opt/werkstatt/ask-human/<run_id>.frage.json
    {
      "frage": "...",
      "kontext": "...",
      "optionen": ["j", "n", "e"],
      "timestamp": "..."
    }

  Pipeline pollt:
    /opt/werkstatt/ask-human/<run_id>.antwort.json
    {
      "wahl": "j",
      "text": "...",
      "timestamp": "..."
    }

Timeout (QQ-K13): 60 min Default.
  planner.ask_human_timeout_min: 60
  Nach Timeout: Fail-closed (rc=12).

================================================================
7. ROLLENTRENNUNG
================================================================

## 7.1 Rollen morgen

  reviewer      — prueft Code + Commit-Paket
  builder       — baut Code-Patches
  solver        — diagnostiziert bei wiederholtem NO-GO
  test_generator — Test-Vorschlaege
  coverage      — Coverage messen
  chaos         — Chaos-Probe
  planner       — formuliert Auftraege / Phasenplaene (NEU)

## 7.2 Konflikt-Staffelung (QQ-K3)

  Konflikt A: Planner vs. Reviewer.
    1. Reviewer lehnt Unterblock ab: kein Planner,
       normaler Loop.
    2. Reviewer lehnt Phase ab: Planner korrigiert.
    3. Beide keine Loesung: Mensch.

  Konflikt B: Planner vs. Mensch: Mensch gewinnt.
  Konflikt C: Planner vs. Builder: Fail-closed.

Regel: Planner kann Reviewer nicht uebergehen.

================================================================
8. NEUE RUNSTATE-FELDER
================================================================

Stufe 1:
  planner_vorschlag: str = ""
  planner_modus: str = "manual"
  planner_runden: int = 0

Stufe 2 (zusaetzlich):
  phase_id: str | None = None
  phase_titel: str = ""
  phase_unterbloecke: list[dict] = []
  phase_aktueller_index: int = 0
  phase_commit_pakete: list[dict] = []
  phase_start_head: str = ""
  phase_aktiv: bool = False

Struktur phase_unterbloecke:
  [
    {
      "id": "U1",
      "titel": "...",
      "unterpunkte": ["a", "b", "c"],
      "geschaetzte_runden": 2
    },
    ...
  ]

================================================================
9. NEUE DATEIEN UND ERWEITERUNGEN
================================================================

  agents/planner.md              (P1)
  docs/PLANNER-KONZEPT.md        (dieses Dokument)

  pipeline.py (P1):
    + _planner_lauf (Stufe 1)
    + main() --planner (Stufe 1)
    + HARD_RULES_PLANNER

  pipeline.py (P2):
    + run_phase, _phase_gesamt_review, _phase_rollback
    + _phase_plan_laden / _phase_plan_speichern
    + main() --phase

  pipeline.py (P3):
    + _ask_human (datei-basiert)

  projects/<name>.yaml:
    + planner.modus, planner.max_runden
    + planner.docs, planner.file_whitelist
    + planner.ask_human_timeout_min
    + budget.max_llm_calls_phase (200)

  schemas/projekt.yaml:
    + planner-Schema

## 9.1 Persistenz (QQ-K10, QQ-K11, RR-K13)

Ort: projects/<name>.phase.yaml.

RR-K13: wird SOFORT nach Planner-Lauf
geschrieben, nicht am Phasenende.
Sonst geht der Plan bei einem Crash verloren.

Format:
  phase_aktiv: true
  phase_id: "dashboard-fundament-1"
  phase_titel: "Dashboard-Fundament"
  phase_start_head: "abc123"
  phase_erstellt_am: "2026-10-15T18:00:00+00:00"
  phase_unterbloecke:
    - id: U1
      titel: "..."
      status: done
      commit_paket: {...}
    - id: U2
      titel: "..."
      status: in_progress
    - id: U3
      titel: "..."
      status: pending

## 9.2 Resume (QQ-K8)

Eigener Block spaeter. Heute: bei Fail-closed
phase_aktiv: false. Naechster Aufruf mit
--phase resume liest phase.yaml.

================================================================
10. BUDGET (QQ-K5, QQ-K6, RR-K4, RR-K5, RR-K11)
================================================================

Layer 1 — Gesamtbudget pro Phase:
  max_llm_calls_phase: 200
  Bei Ueberschreitung: Phase-Fail-closed.

Layer 2 — Teilbudget pro Unterblock:
  max_llm_calls: 30 (bestehend)
  Bei Ueberschreitung: Unterblock-Fail-closed,
  Phase bricht ab.

RR-K4: kein Uebertrag von Restbudget.

RR-K11: max_llm_calls_phase zaehlt pro PHASE,
  nicht pro Session. Auch wenn die Phase ueber
  mehrere Sessions laeuft.

RR-K5: Kalibrierung nach 5-10 echten Laeufen.

================================================================
11. OFFENE FRAGEN (alle beantwortet)
================================================================

F1-F7 (Durchlauf 1): eingearbeitet.
QQ-K1..QQ-K15 (Durchlauf 2): eingearbeitet.
RR-K1..RR-K14 (Durchlauf 3): eingearbeitet.

F15 (Gesamt-Review-Ort): siehe 5.5.
F16 (Unterblock ohne Patches): siehe 5.4.

## 11.1 KONZEPT-FINAL — keine neuen offenen Fragen

Alle offenen Punkte aus den drei
Reviewer-Durchlaeufen sind eingearbeitet.
Weitere Punkte werden im Code (P1, P2, P3)
geloest, nicht mehr im Konzept.

================================================================
12. ZUSAMMENFASSUNG
================================================================

Alle Praezisierungen sind eingearbeitet:
  PP-K1 bis PP-K11 (Durchlauf 1).
  QQ-K1 bis QQ-K15 (Durchlauf 2).
  RR-K1 bis RR-K14 (Durchlauf 3).

Alle Auftraggeber-Klaerungen:
  Phasenplan in projects/.
  Rollback mit HEAD + status-Check.
  Budget 200 + 30.

Konzept v4 ist FINAL. Kein weiterer
Reviewer-Durchlauf fuer das Konzept.

================================================================
13. UMSETZUNG (Reihenfolge)
================================================================

  Block P1: Planner-Rolle + _planner_lauf.
            Stufe 1. Kategorie 3.
            Eigener Block.

  Block P2: --phase + run_phase + Gesamt-Review.
            Stufe 2. Kategorie 3.
            Eigener Block.
            RR-K10: vorlaeufig Konsolen-Approval,
            bis P3 fertig ist.

  Block P3: ASK_HUMAN + Persistenz.
            Kategorie 3. Eigener Block.

  Block P4: Dashboard-Button (Ziel 4).
  Block P5: Chat-Modus (Ziel 4).

Naechster Schritt: Reviewer-Block fuer P1.
Der Reviewer prueft dann den CODE von P1,
nicht mehr das Konzept.

================================================================
ENDE DES KONZEPTS
================================================================
