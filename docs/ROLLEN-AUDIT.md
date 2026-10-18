# Rollen-Audit — Werkstatt

Stand: 2026-10-18 (nach W61-Label-Fix)
Anlass: Planner liefert P17-konforme Listen, aber keine Aufträge. Builder und Reviewer zeigen Symptome von Prompt-Überflutung. Vor P20+P21 (Planner-Auftrags-Kontext + Selbst-Kritik) muss das Gesamtbild der Rollen geklärt werden.

## 1. Ist-Zustand (gemessen 2026-10-17)

### Rollen-Dateien (agents/*.md)

| Datei | Zeilen | Zeichen | Zweck |
|---|---|---|---|
| builder.md | 534 | 13.748 | Builder-Rolle (Patch-Format, Anker, Commit-Message) |
| reviewer.md | 410 | 11.623 | Reviewer-Rolle (Code/Commit-Review, Verdict) |
| planner.md | 236 | 6.177 | Planner-Rolle (Stufe 1/2, Phasenplan) |
| solver.md | 182 | 4.676 | Solver-Rolle (Deadlock-Diagnose) |
| test_generator.md | 18 | 490 | Test-Generator (schmal) |
| chaos.md | 10 | 244 | Chaos (schmal) |
| coverage.md | 10 | 246 | Coverage (schmal) |

### HARD_RULES (pipeline.py)

| Konstante | Zeilen | Zeichen | Zuordnung |
|---|---|---|---|
| HARD_RULES_BASE | 18 | 584 | Alle Rollen |
| HARD_RULES_BUILDER | 113 | 3.713 | Builder (B1-B15) |
| HARD_RULES_REVIEWER | 186 | 6.854 | Reviewer (R1-R17) |
| HARD_RULES_SOLVER | 49 | 1.939 | Solver (S1-S10) |
| HARD_RULES_TEST_GENERATOR | 11 | 249 | Test-Generator (T1-T4) |
| HARD_RULES_PLANNER_STUFE1 | 29 | 1.007 | Planner Stufe 1 (P1-P9) |
| HARD_RULES_PLANNER_STUFE2 | 212 | 7.993 | Planner Stufe 2 (P10-P19) |

### Prompt-Größe pro Aufruf (Basis, ohne Doku)

| Rolle | Roll-Body + HARD_RULES | Basis |
|---|---|---|
| Builder | 534 + 18 + 113 | **665 Zeilen** |
| Reviewer | 410 + 18 + 186 | **614 Zeilen** |
| Planner Stufe 2 | 236 + 18 + 212 | **466 Zeilen** |
| Solver | 182 + 18 + 49 | 249 Zeilen |

**Mit Projekt-Doku (`doc_keys`), Anti-Pattern-Block, Aufgabe, GEMESSENER INHALT, Messprotokoll:**
- Builder: 800-1.500 Zeilen.
- Reviewer: 700-1.000 Zeilen.
- Planner: 600-900 Zeilen.

## 2. Redundanz-Analyse

### Builder

| agents/builder.md | HARD_RULES_BUILDER | Redundanz |
|---|---|---|
| ## ANKER UND ERSATZ | B4, B7, B10 | Ja (Anker-Regeln) |
| ## NEUE DATEIEN | B12, B15 | Ja (new_file) |
| ## SPEC-TREUE | B13 | Ja |
| ## SOLVER-BEFUND | B14 | Ja |
| ## MESSWERTE ALS MESSUNG | B1, B2, B3 | Ja |
| ## MESSWERTE IM PROMPT | B1, B2, B3 | Ja |
| ## COMMAND: RUN | B5 | Ja |

**Geschätzte Redundanz: 228 Zeilen von 534 (~43 %).**

### Reviewer

| agents/reviewer.md | HARD_RULES_REVIEWER | Redundanz |
|---|---|---|
| ## GEMESSENER INHALT | R7 | Ja |
| ## PHASE 1 | R13 | Ja |
| ## ERSETZUNG UND EINFUEGUNG | R7 | Ja |
| ## COMMAND vs. VERDICT | R6 | Ja |
| ## SACHFADEN | R11 | Ja |
| ## VERDICT-KONSISTENZ | R14 | Ja |

**Geschätzte Redundanz: 170 Zeilen von 410 (~41 %).**

### Planner

| agents/planner.md | HARD_RULES_PLANNER_STUFE2 | Redundanz |
|---|---|---|
| ## Stufe 2: Phasenplan | P10-P14 | Ja |
| ## Korrektur-Kompetenz (P18) | P18 | Ja |

**Geschätzte Redundanz: 47 Zeilen von 236 (~20 %).**

## 3. Rollen-übergreifende Überschneidungen

| Regel | Builder | Reviewer | Solver | Planner |
|---|---|---|---|---|
| Messen (`COMMAND: RUN`) | B5 | R6 | – | P19 |
| Anker-Prüfung | B7, B10 | R7 | – | – |
| new_file-Marker | B12, B15 | R10, R12, R15 | – | – |
| Sachfaden | – | R11 | – | – |
| Verdict-Konsistenz | – | R14 | – | – |
| Phasen-Trennung | – | R13 | – | – |

**Überschneidungen:**
- **Messen:** 3 Rollen (Builder, Reviewer, Planner). Konzept: „Wer darf messen, wann, wie oft?" → In Builder und Planner produktiv, in Reviewer nur als Prüfauftrag.
- **Anker:** 2 Rollen (Builder, Reviewer). Builder führt, Reviewer prüft. Redundanz-Risiko: zwei Definitionen von „Anker".
- **new_file-Marker:** 2 Rollen (Builder, Reviewer). Dito.

## 4. Widerspruchs-Verdacht (nicht abschließend geprüft)

1. **B4 vs. B13b:** „Du bist kein Messender" vs. „Prüfe Behauptungen". Aufgelöst durch B4-Aufteilung (Systemwerte vs. Auftrags-Behauptungen), aber Wortlaut B4 wirkt noch absolut.
2. **R9 vs. B13:** „Eskalation an den Menschen" vs. „Der Auftrag ist verbindlich". Kontextuell verschieden, aber nicht explizit getrennt.
3. **P15-Neu max 7** vs. Planner-Output U1 mit 4 Unterpunkten: Planner hält die Grenze ein, aber inhaltlich unterbestimmt (4 Punkte, aber Widerspruch „Grundgerüst" vs. „config_change anwenden").
4. **P17-4-Pflichtfelder** vs. Planner-Output „signatur/anker": Planner hat die Semantik verstanden (WEG-X-P19c), aber nicht die Konsistenz-Anforderung.
5. **R7-Anker-Prüfung** vs. `_plan_ist_messungsbasiert`: zwei verschiedene Prüf-Konzepte (Reviewer prüft, ob Anker existiert; Pipeline prüft, ob Plan Anker enthält).

## 5. Empfehlungen

### Sofort (P20+P21, Kategorie 3)

- **P21 (Planner-Auftrags-Kontext):** Jeder Unterblock MUSS enthalten:
  - Kontext (2-4 Sätze: Warum diese Runde? Ausgangspunkt? Bezug Doku?).
  - Fail-closed-Semantik (falls relevant).
  - Grenzen (Was gehört NICHT dazu?).
  - Akzeptanz (3-5 konkrete Prüfpunkte).
  - Abhängigkeiten (Braucht U_n etwas von U_m?).
- **P20 (Planner-Selbst-Kritik):** Vor Abgabe prüft der Planner seinen Plan auf:
  - Widerspruchsfreiheit (Titel vs. Unterpunkte).
  - Konsistenz mit Doku (DECISIONS, ROADMAP, STATUS).
  - Machbarkeit (kann der Builder das ohne Rückfrage bauen?).
  - Abhängigkeiten (sind Vorbedingungen erfüllt?).

### Mittelfristig (Rollen-Sanierung, Kategorie 3)

- **Redundanz auflösen:** Ein Konzept, eine Quelle.
  - Anker-Regeln: nur in HARD_RULES_BUILDER B7/B10, Roll-Body verweist.
  - new_file-Regeln: nur in HARD_RULES_BUILDER B12/B15, Roll-Body verweist.
  - Spec-Treue: nur in HARD_RULES_BUILDER B13.
  - Messwerte: nur in HARD_RULES_BUILDER B1-B3.
  - Command: nur in HARD_RULES_BUILDER B5.
  - Dito für Reviewer: GEMESSENER INHALT, PHASE 1/2, ERSETZUNG, COMMAND, SACHFADEN, VERDICT-KONSISTENZ → nur in HARD_RULES_REVIEWER, Roll-Body verweist.
- **Prompt-Größe reduzieren:** Ziel:
  - Builder-Roll-Body < 300 Zeilen.
  - Reviewer-Roll-Body < 250 Zeilen.
  - Planner-Roll-Body < 150 Zeilen.
- **Klare Quellen-Hierarchie:**
  1. HARD_RULES (deterministisch, fail-closed).
  2. Roll-Body (Verhalten, Beispiele, Kontext).
  3. Projekt-Doku (projektspezifisch).
  4. Anti-Pattern-Katalog (situativ).

### Langfristig (Kategorie 3)

- **Prompt-Größen-Limit:** Neue Regeln prüfen gegen eine Obergrenze (z.B. Builder-Prompt < 800 Zeilen Basis).
- **Determinismus-Vorrang:** Wo möglich, Prompt-Regel durch deterministischen Check ersetzen (Muster WEG-X-P19).
- **Regel-Audit-Routine:** Nach jeder Session prüfen: Neue Regeln? Redundanz entstanden?

## 6. Nächster Schritt

**Option A (empfohlen):** WEG-X-P20+P21 bauen (Planner-Auftrags-Kontext + Selbst-Kritik), Kategorie 3.

**Option B:** Rollen-Sanierung zuerst (Redundanz auflösen), dann P20+P21.

**Option C:** Beides in einem Block (großer Umbau).

**Entscheidung:** Option A, weil der Planner das sichtbarste Problem ist. Rollen-Sanierung folgt als eigener Block.

## 7. Nicht in diesem Audit

- Inhalts-Detailanalyse jeder Regel (nur Überschriften-Ebene).
- Widerspruchs-Auflösung (nur Verdacht benannt).
- Code-Analyse der prompt-bauenden Funktionen (`build_system_prompt`, `_anti_pattern_block`, `baue_anker_rueckmeldung`, `baue_budget_rueckmeldung`).
- `agent_docs`-Zuordnung pro Rolle (welche Doku bekommt welche Rolle?).
- Anti-Pattern-Katalog (26 Einträge) — werden an welche Rollen angehängt?

Diese Punkte gehören in eine Folge-Session (Rollen-Sanierung).

## 8. Update 2026-10-18 (nach W48-W54h)

Der Audit ist vom 2026-10-17. Seitdem wurde teilweise saniert,
teilweise gegen die Empfehlung gebaut.

### 8.1 Gemessener Stand 2026-10-18

| Datei | Audit 2026-10-17 | Stand 2026-10-18 | Delta | Ursache |
|---|---|---|---|---|
| builder.md | 534 | 647 | +113 | W54-a (+12), W54-h (+17), W37-Nachzug (?) |
| planner.md | 236 | 297 | +61 | W51a, c, d, f, g |
| reviewer.md | 410 | 56 | -354 | W40-Sanierung |
| judge.md | (nicht vorhanden) | 90 | neu | W28b |
| solver.md | 182 | 182 | 0 | - |
| chaos.md | 10 | 10 | 0 | - |
| coverage.md | 10 | 10 | 0 | - |
| test_generator.md | 18 | 18 | 0 | - |

### 8.2 Was saniert wurde

- **reviewer.md: W40 hat die Redundanz aufgelöst.**
  410 -> 56 Zeilen. Die Regeln sind jetzt in
  HARD_RULES_REVIEWER (pipeline.py), der Roll-Body
  verweist nur noch.

- **judge.md: neue Rolle (W28b).**
  Der Judge (Phasen-Gesamt-Review) ist im Audit
  nicht erwähnt, weil er damals noch nicht existierte.
  90 Zeilen, Aufgabe: Contract-Treue und Sicherheit.

### 8.3 Was gegen die Empfehlung lief

- **builder.md: 534 -> 647 (+113).**
  Audit-Ziel war < 300 Zeilen (Roll-Body).
  W54-a (+12, doppelte Imports/Klassen) und
  W54-h (+17, Ziel-Klasse aus ZIELDATEI) sind
  Symptom-Behandlung: sie fuegen Regeln hinzu,
  statt Redundanz aufzuloesen.
  Der Builder liest die Anker-Regeln nicht mehr
  (Phase-20b-Laeufe: "Anker nicht im GEMESSENER
  INHALT", Builder wiederholt 3x).

- **planner.md: 236 -> 297 (+61).**
  Audit-Ziel war < 150 Zeilen (Roll-Body).
  W51a-h haben sechs neue Abschnitte hinzugefuegt:
  MESS-PFLICHT, MESSUNGEN, Phasen-Groesse,
  DEIN LETZTER PLAN WURDE ABGELEHNT.
  Der Planner-Loop ist durch die W51-Kette
  stabilisiert, aber der Roll-Body ist gewachsen.

### 8.4 Was offen bleibt

- **W61 (Rollen-Sanierung, Kategorie 3):**
  Redundanz aufloesen (builder.md 43% geschaetzt),
  Roll-Body < 300/250/150.
  Wurde durch die W51/W54-Serie dringlicher,
  nicht weniger dringlich.

- **W54-f (builder.md 647 Zeilen):**
  Aufraeumen bei W36-2b..6 oder W61.

- **W57 (Prompt-Audit):**
  Nach Phase 20b alle Rollen-Dateien pruefen:
  was liest das LLM tatsaechlich? Was wird ignoriert?

### 8.5 Fazit

Der Audit war richtig. Die W51/W54-Serie hat ihn
ignoriert. Die Symptome (Deadlock in Phase 20b,
Builder wiederholt Anker) sind die Folge.

W61 (Rollen-Sanierung) ist der strukturelle Fix.
W59 (Deadlock-Mechanismus) ist der mechanische Fix.
Beide sind noetig, in dieser Reihenfolge.

## Update 2026-10-18 — W61

- **Judge-Labels**: Der Judge-Loop spricht jetzt Judge
  (vorher Reviewer). Siehe ARCHITEKTUR.md.
- **solver_model**: eigene Rolle (deepseek-reasoner),
  nicht mehr reviewer_verdict_model. W61c.
- **Subagenten**: explore (aktiv), bash/browser
  (inaktiv). Siehe ARCHITEKTUR.md.
- **W61a (Reviewer 3->1)**: offen. Reviewer macht
  heute noch Mess-Wahl (Schritt 1), Commit-Review,
  Recovery. Ziel: nur Commit-Review.
- **W61b (Judge 2->1)**: offen. Judge macht heute
  Patch-Review + Repair (`_phase_judge_repair_runde`).
  Ziel: nur Patch-Review.
- **W61d (Prompt-Groessen)**: offen. builder.md 647,
  planner.md 299. Ziel: <300 / <150.

