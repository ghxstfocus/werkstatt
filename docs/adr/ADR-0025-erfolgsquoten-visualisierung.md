# ADR-0025: Erfolgsquoten-Visualisierung

Datum: 2026-11-09
Status: Accepted
Grundlage fuer: OP-375

## Kontext

Die Overview-Shell (OP-306b) zeigt Projekt-Karten mit KPI und
Sparkline. Was fehlt: eine aggregierte Sicht auf die Erfolgs-Quote
des Loops. Fehlerklassen (`reviewer_bug`, `loop_verify_failed`,
`loop_failed`) liegen bereits in SQLite (387.487 Werkstatt-Events,
23.289 security-ai-Events), aber werden in der UI nirgends
aufgeschluesselt.

Donut-Charts sind ein etabliertes Muster fuer Erfolgsquoten, ABER:
Recherche (Dribbble, Smashing Magazine, LogRocket, NNG) zeigt, dass
Donuts nur bei 2-4 Segmenten lesbar sind. Ab 5 Segmenten ist eine
Segmentbar besser. Fuer Vergleiche zwischen Projekten sind viele
kleine Donuts nebeneinander unlesbar -- eine horizontale Segmentbar
pro Projekt ist klarer.

Ein weiterer Befund: Die Fehlerklassen-Verteilung ist nicht nur
Statistik, sondern Eingangsgroesse fuer den Selbstverbesserungs-Loop
(ADR-0027). Wenn 38% aller Fehler `reviewer_bug` vom Typ X sind,
ist das der Ansatzpunkt fuer den naechsten OP.

## Entscheidung

Drei-Ebenen-Layout unter der Overview-Sektion:

### 1. Gesamt-Donut (2-4 Segmente, KPI-Wert gross im Zentrum)

    Segmente:   Erfolg | Fehlgeschlagen | Abgebrochen
    Zentrum:    Gesamt-Quote in % (z.B. "83%")
    Farbe:      sem-ok | sem-error | sem-warn

Kein 3D, kein Schatten, keine Animation ausser sanftem Fade-in.

### 2. Projekt-Segmentbar (eine Zeile pro Projekt)

    werkstatt     ████████░░░░  67%   (27 Runs)
    security-ai   ████████████ 100%   (50 Runs, pre-OP-303)

Horizontale Balken, sem-ok fuer Erfolg, Rest sem-history (neutral).

### 3. Fehlerklassen-Tabelle (Top-3 nach Haeufigkeit)

    reviewer_bug                38 %  ████████░░░░
    loop_verify_failed          22 %  █████░░░░░░░
    verify_stage_ohne_hart      15 %  ███░░░░░░░░░

Normalisiert nach Signatur (Datei + Bug-Typ + Kontext). Klick auf
eine Zeile -> Detail-Panel mit den 5 juengsten Events und Verweis
auf OP-376.

## Konsequenzen

Positiv:
- Ehrliche UI: zeigt was da ist, nicht was sein sollte.
- Handlungsansatz: Fehlerklassen sind direkt in OPs uebersetzbar.
- Skaliert: Segmentbar-Projektzeilen beliebig erweiterbar.
- Minimalistisch: ein Donut + Balken, keine Chart-Library noetig.

Negativ:
- 30-Tage-Quote ignoriert aeltere Runs.
- Fehlerklassen-Signatur ist Freitext-Matching. Normalisierung
  muss getestet sein (OP-376).

Risiko-Mitigation:
- Bei genau 2 Segmenten: Halb-Donut.
- Bei nur 1-2 Fehlerklassen: reine Text-Tabelle.
- Baseline-aware: keine Daten -> Hinweis "keine Daten".

## Nicht-Ziele

Kein Drill-down auf Runs. Keine Zeitreihen. Kein Export.

## Referenzen

- NNG: Donut Charts (max 2-4 segments)
- Smashing Magazine: KPI-Dashboard Patterns
- OP-301 (Ambient Bar, sem-Farben)
- OP-306b (Overview-Shell, Etappe 1)
