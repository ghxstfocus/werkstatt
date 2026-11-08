# ADR-0026: Memory-Graph-Visualisierung

Datum: 2026-11-09
Status: Accepted
Grundlage fuer: OP-380

## Kontext

Nach OP-220 (Erfahrungs-Gehirn) und OP-221 (Memory-Destillation)
entstehen Erfahrungs-Eintraege in `.werkstatt/erfahrung.db`. Diese
Eintraege sind Textzeilen -- ohne Visualisierung bleibt dem User
verborgen, welche Loesungen gegriffen haben, welche Fehler
miteinander zusammenhaengen, und wo die Evidenz liegt.

Recherche etablierter Memory-Visualisierungen:

    System                Ansatz                          Skalierung
    total-agent-memory    3D WebGL, Click-to-Focus        3.500+ Nodes
    memorygraph           typisierte Kanten (kausal,       mittel
                          hierarchisch, temporal)
    heym                  2D-Canvas, Ring-Layout um         klein-mittel
                          Zentrum, stabile Positionen
    Cognee                Graph Explorer + Reasoning-      mittel
                          Subgraph + Evidence
    AgentFlow/Langfuse    Graph + Timeline + Evidence-     mittel
                          Panel bei Klick

Kernbefund: 3D lohnt erst ab ~1.000 Nodes. Bei kleineren Graphen
ist 2D mit stabilem Layout lesbarer. Evidence-Panel bei Klick ist
der Unterschied zwischen "schoener Graph" und "analysierbares
Werkzeug".

## Entscheidung

2D-Canvas mit Ring-Layout als Start. Kein 3D.

### Node-Typen

    Typ         Farbe           Bedeutung
    fehler      --sem-error     Problem-Klasse
    loesung     --sem-ok        Patch-Typ / gelungener Fix
    evidenz     --sem-history   Run-ID + Commit-SHA
    projekt     --sem-active    Projekt-Knoten
    op          --sem-action    OP

### Kanten

    loeste      Loesung -> Fehler
    trat_auf    Fehler -> Evidenz
    verwandt    Fehler <-> Fehler (Embedding > 0.8)
    blockierte  Fehler -> Fehler

### Layout

Ring-Layout um Canvas-Zentrum (heym-Vorbild). Stabile Positionen
per Hash(node_id). Kein Force-Layout, kein Jitter. Kanten
opacity 0.3, bei Hover 1.0.

### Klick-Detail (Evidence-Panel)

Klick auf Node -> Seiten-Panel mit: Node-Info, Nachbarn, Evidenz-
Liste (letzte 10 SQLite-Events), verwandte OPs. Einklappbar.

### Technologie

SVG bei <200 Nodes. Canvas ab 200. Keine externe Chart-Library.

## Konsequenzen

Positiv:
- Lesbar bei kleinen Graphen.
- Stabile Positionen.
- Evidence-Panel macht Analysen moeglich.
- Erweiterbar auf 3D.
- Keine Dependency.

Negativ:
- Ring-Layout zeigt nur 1-2 Ebenen sinnvoll.
- Verwandtschaft via Embedding ist heuristisch.
- Evidence-Panel bei vielen Nachbarn ueberladen.

Risiko-Mitigation:
- Bei >200 Nodes: Canvas.
- Bei >20 Nachbarn: gruppieren.
- Verwandtschaft opt-in (Default: nur loeste + trat_auf).

## Nicht-Ziele

Keine Echtzeit. Keine fliessenden Kanten. Kein 3D. Kein Graph-
Editor (nur Lesen).

## Referenzen

- total-agent-memory, memorygraph, heym, Cognee, AgentFlow, Langfuse
- OP-220, OP-221, OP-222
