# ADR-Index — Werkstatt

Architecture Decision Records. Dateiname: `ADR-NNNN-<slug>.md`.

| Nummer | Titel | Status |
|---|---|---|
| [ADR-0001](ADR-0001-sops-age.md) | Key-Architektur mit SOPS + age | accepted |
| [ADR-0002](ADR-0002-loop-neubau.md) | Loop-Neubau aus pipeline.py-Monolith | accepted |
| [ADR-0003](ADR-0003-kontroll-zentralisierung.md) | Kontroll-Zentralisierung in werkstatt/control/ | accepted |
| [ADR-0004](ADR-0004-deterministische-drift-checks.md) | Deterministische Drift-Checks | accepted |
| [ADR-0005](ADR-0005-verify-json-hart-asymmetrie.md) | verify.json hart-Feld — asymmetrische Semantik | accepted |
| [ADR-0006](ADR-0006-event-store-ssot.md) | Event-Store als SSOT fuer Loop-Events | accepted |
| [ADR-0007](ADR-0007-gate-bridge.md) | Gate-Bridge — Loop headless, Gates ueber HTTP | accepted |
| [ADR-0008](ADR-0008-chat-eigener-agent.md) | Chat als eigener Agent | accepted |
| [ADR-0009](ADR-0009-timeline-primaer-layout-a.md) | Timeline primaer, Chat rechts (Layout A) | accepted |
| [ADR-0010](ADR-0010-memory-zweistufig.md) | Memory zweistufig — project + global | accepted |
| [ADR-0011](ADR-0011-debugger-chat-modus.md) | Debugger als Chat-Modus (evidence-first) | accepted |
| [ADR-0012](ADR-0012-vier-strukturmuster.md) | Vier Strukturmuster als Ursache fuer Multi-File-Failure | accepted |
| [ADR-0013](ADR-0013-layer-architektur.md) | Layer-Architektur + Submodul-Split-Reihenfolge | accepted |
| [ADR-0014](ADR-0014-rollen-registry.md) | Rollen-Registry als Single Source of Truth | accepted |
| [ADR-0015](ADR-0015-tests-sind-specs.md) | Tests sind Specs, keine Attrappen | accepted |
| [ADR-0016](ADR-0016-spec-first-test-loop.md) | Spec-First Test-Loop — Tests vor Code | proposed |
| [ADR-0017](ADR-0017-mutation-gate.md) | Mutation-Gate mit pytest-gremlins | proposed |
| [ADR-0018](ADR-0018-debugger-rolle.md) | Debugger als eigene Rolle | rejected |
| [ADR-0019](ADR-0019-gate-lifecycle.md) | Gate-Lifecycle-Vertrag statt PID/Heartbeat/Timeout | accepted |
| [ADR-0020](ADR-0020-human-readable-audit.md) | Human-Readable Audit-Trail im Frontend | accepted |
| [ADR-0021](ADR-0021-rollen-detail-ansicht.md) | Rollen-spezifische Detail-Ansicht im Chat-Drawer | accepted |
| [ADR-0022](ADR-0022-hybrid-ui-modi.md) | Hybrid-UI-Modi (Cockpit / Control / Debug) | accepted |
| [ADR-0023](ADR-0023-multi-projekt-kontext.md) | Multi-Projekt-Kontext | accepted |
| [ADR-0024](ADR-0024-tiered-event-log.md) | Tiered Event Log + Projector (CQRS-light) | accepted |
| [ADR-0025](ADR-0025-erfolgsquoten-visualisierung.md) | Erfolgsquoten-Visualisierung | accepted |
| [ADR-0026](ADR-0026-memory-graph-visualisierung.md) | Memory-Graph-Visualisierung | accepted |
| [ADR-0027](ADR-0027-selbstverbesserungs-loop.md) | Selbstverbesserungs-Loop (Trace-First + Preservation-Gate) | proposed |
| [ADR-0028](ADR-0028-scout-report-als-architect-kontext.md) | Scout-Report als einzige Architect-Kontextquelle | accepted |
| [ADR-0029](ADR-0029-chat-zentrierte-projektsteuerung.md) | Chat-zentrierter Control-Plane und autonome Arbeit | accepted |
