# ADR-0028: Scout-Report als einzige Architect-Kontextquelle

- **Datum:** 2026-11-10
- **Status:** accepted
- **Grundlage fuer:** OP-385

## Kontext

Der Explorer sammelt breite Mess- und Dateidaten. Der Scout soll daraus
einen auftragsbezogenen Kontext fuer den Architect bilden. In der Praxis
wurden Explorer-Findings, AST/API-Index, Scout-API-Auszug und gemessene
Dateien parallel injiziert. Das vervielfachte Informationen und konnte
den Architect-Prompt bis zur Abschneidung aufblasen. Ein leerer oder
unvollstaendiger Scout-Report durfte ausserdem nicht stillschweigend den
breiten Fallback-Kontext aktivieren.

## Entscheidung

Wenn der Scout einen strukturierten, nichtleeren `auftrag_prosa`-Wert
liefert, ist der Scout-Report die einzige fachliche Quelle fuer den
Architect-Kontext. Rohdaten aus Explorer und API-Index werden nicht
parallel wiederholt. Der Planner speichert den Report im RunState; der
Architect injiziert ihn an genau einer Stelle.

Fehlt der Report, ist er kein Dictionary oder fehlt `auftrag_prosa`,
bricht der Planner vor dem Architect-Aufruf mit Audit-Befund ab. Der
Architect hat denselben fail-closed Vertrag, damit direkte Aufrufe den
Planner-Guard nicht umgehen.

Ein eng begrenzter Legacy-Fallback bleibt nur fuer bereits gespeicherte
Runs ohne Scout-Report verfuegbar. Er darf keinen fehlerhaften Report
ueberschreiben.

## Konsequenzen

- Weniger doppelte Tokens und weniger konkurrierende Kontextquellen.
- Fehlerhafte Scout-Ausgaben werden sichtbar statt mit zufaelligem
  Explorer-Kontext kaschiert.
- Tests muessen den Scout-Vertrag ausdruecklich abbilden.
- Live-Messungen muessen Prompt-Groesse und Ergebnisqualitaet pruefen;
  Kontextverengung allein beweist keine bessere Planung.

## Verifikation

- Planner-Tests fuer fehlenden und unvollstaendigen Report.
- Architect-Tests: genau ein Scout-Block, kein paralleler Explorer-Block.
- Live-Dogfooding vergleicht Prompt-Tokens, Plan-Qualitaet und
  Fehlerrate vor und nach der Aenderung.
