# ADR-0027: Selbstverbesserungs-Loop — Trace-First + Preservation-Gate

Datum: 2026-11-09
Status: Proposed
Grundlage fuer: OP-376, OP-377, OP-378, OP-379

## Kontext

Selbstverbesserung von Agenten ist 2026 kein geloestes Problem mehr,
aber auch kein triviales. Forschungsstand:

    System                  Ergebnis                        Mechanik
    SICA (NeurIPS 2025)     17 % -> 53 % SWE-Bench Verified Meta-Agent,
                                                            volle Editierung
    Darwin Goedel Machine   20 % -> 50 % SWE-Bench,          Archiv, Sampling,
    (ICLR 2026)             14,2 % -> 30,7 % Polyglot       empirische Valid.
    Ouroboros (NeurIPS 2026)86,97 % Terminal-Bench,          Reviewed Commits,
                            90,69 % OSWorld,                Guardrails
                            161-Tage-Live "Hope"            autoritativ
    HarnessPro (Okt 2026)   Pareto Performance<->Kosten     Recursive Self-
                                                            Improvement +
                                                            Kostenbewusstsein

ABER: Zwei Papers zeigen die Schattenseite:

"Beneath the Surface" (05.11.2026): 16 evolvierte Agenten. ALLE
gewinnen neue Tasks und VERLIEREN alte. Ein Fall: Reliability
+5,2 Punkte, aber 10 abgedeckte Tasks verloren. Der hoechst-
bewertete Agent liefert NICHT den groessten mittleren Gewinn.
Forderung: preservation-aware evaluation.

"Trace Evolution Bench" (10.10.2026): Von 9 Text-Update-Verfahren
haben 7 positive Excess-Werte, aber KEIN Verfahren bleibt auf
jedem Seed ueber seinem Rauschband. Ein gepa_llm-Seed faellt um
die Breite seines Bands (-12,5 Punkte).

Konsequenz: Jeder "Self-Improve"-Gewinn muss gegen ein Seed-Band
gemessen werden, nicht gegen einen einzelnen Vorher/Nachher-
Vergleich.

## Entscheidung

Fuenf-Phasen-Loop, trace-first, mit Preservation-Gate.

### Phase 1 — Analyse (deterministisch + LLM)

Input: SQLite events (reviewer_bug, loop_verify_failed,
verify_stage_ohne_hart_flag, loop_failed).
Cluster nach normalisierter Signatur. Ranke nach Haeufigkeit x
Kosten. Output: Top-N Fehler-Cluster mit Evidenz-IDs.

Kein Benchmark. Cluster aus echten Betriebs-Traces (Moat gegenueber
Forschungs-Setups).

### Phase 2 — Hypothese (LLM, read-only)

Fuer jedes Cluster: welcher Code-Pfad ist verantwortlich?
Welche Datei/Zeile? Welcher Patch-Typ?
Output: OP-Entwurf (Titel, AK, Zieldateien).

Der Entwurf landet in docs/STATUS.md als neuer OP. Kein Auto-
Commit.

### Phase 3 — Patch (bestehender Loop)

OP geht durch Explorer -> Architect -> Planner -> Builder ->
Reviewer -> Verify -> Gates. Kein Sonderpfad.

### Phase 4 — Preservation-Gate (neu)

Vor Commit:
- Alle bestehenden Tests gruen
- Fehler-Cluster-Rate nicht gestiegen (AFTER <= BEFORE)
- Keine neuen Datenluecken

Sonst: Rollback.

### Phase 5 — Bewertung (nach N Runs)

Nach 3 unbehandelten Referenz-Runs:
- Hat der Fix die Fehlerrate gesenkt?
- Mit Seed-Band (die 3 Referenz-Runs definieren das Band).
- Ergebnis in erfahrung.db.

Wenn nein: OP wieder oeffnen mit Evidenz.

## Konsequenzen

Positiv:
- Ehrlicher als SICA/DGM: Preservation-Gate verhindert Verlust.
- Trace-first: Cluster aus echten Runs.
- Messbar: Seed-Band.
- Reviewbar: jeder Vorschlag ein OP mit Human-Gate.
- Nutzt bestehende Infrastruktur (Verify, Drift-Checks, OPs).

Negativ:
- Langsamer als SICA/DGM.
- Phase 5 braucht Tage bis Wochen.
- Freitext-Heuristik.
- Preservation-Gate braucht Baseline-Daten.

Risiko-Mitigation:
- OP-376 zuerst bauen. Wenn <10 Cluster in 30 Tagen: Loop noch
  nicht sinnvoll, OP-377 verschieben.
- Preservation-Gate im ersten Zyklus manuell.
- Bei Varianz >30%: mehr Referenz-Runs.

## Nicht-Ziele

Kein Auto-Commit. Keine Selbst-Modifikation von verify.json oder
Gate-Regeln. Keine synthetischen Benchmarks. Kein Multi-Agent-
Archiv. Kein History-Rewrite.

## Wichtig — was wir NICHT machen

Der Loop modifiziert nicht seine eigene Verify-Kette, seine
Gate-Logik, oder die Sicherheitsnetze. Er baut nur Produktivcode
ueber den bestehenden OP-Pfad. Preservation-Gate rot: manueller
Rollback, OP wieder oeffnen.

Das ist Ouroboros' Lektion: Guardrails bleiben autoritativ.

## Referenzen

- SICA (NeurIPS 2025)
- Darwin Goedel Machine (ICLR 2026, arXiv:2505.22954)
- Ouroboros (NeurIPS 2026)
- HarnessPro (Okt 2026)
- Self-HPO (Okt 2026)
- "Beneath the Surface" (05.11.2026)
- Trace Evolution Bench (10.10.2026)
- OP-376, OP-220
