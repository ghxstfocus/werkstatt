# Ist-Zustand des Werkstatt-Loops — 2026-11-12

Diese Bestandsaufnahme trennt den im Checkout belegten Ist-Zustand vom
Zielbild. Sie ist keine Behauptung ueber den laufenden Server: Der Checkout
steht auf `40251ac`; Deployments koennen davon abweichen.

## Kurzbefund

Die Werkstatt besitzt bereits wertvolle Grundlagen: projektgebundene Runs,
Rollen, Verify-Stufen, Human Gates, Event Store, Chatjobs und eine
Run-Registry. Der zentrale Coding-Lauf ist jedoch weiterhin eine lineare
Funktionskette mit einem begrenzten Task-Unterloop. Chat und Lauf haben
getrennte Zustandsquellen; am finalen Verify fehlt der adaptive
Diagnose-und-Reparaturpfad. Das erklaert, warum lokale Reflexionen moeglich
sind, ein Fehler am falschen Ort aber den gesamten Run beendet.

## Belegte Implementierung

| Bereich | Ist-Zustand im Checkout | Fundstelle |
|---|---|---|
| Run-Steuerung | `run_pipeline_loop` ruft Setup/Explorer, Plan/Preflight, Task-Loop und Finalizer nacheinander auf. | `werkstatt/loop.py:299,369-392` |
| Tasks | Der Task-Loop nimmt Tasks aus `PhaseState` und fuehrt Builder, Verify, Reviewer und begrenzte Reflection aus. | `werkstatt/phases/tasks.py:74-99,156-181,320-354` |
| Recovery | Recovery ist in Teilpfaden vorhanden; sie ist kein einheitlicher Laufzustand und wird nicht von jedem Fehlerpfad verwendet. | `werkstatt/phases/tasks.py`; `werkstatt/reflection.py` |
| Final Verify | `phase_end`-Verify schlaegt fehl und setzt den Rueckgabecode auf Fehler. Danach folgt kein erneuter Diagnose-/Reparaturversuch vor Run-Ende. | `werkstatt/phases/finalize.py:128-156` |
| Doku-Gate | `.werkstatt/verify.json` fuehrt `doku_drift` als harte `phase_end`-Stufe. Die Doku-Pruefung laeuft damit vor dem spaeteren Commit-Abschluss. | `.werkstatt/verify.json`; `werkstatt/verify.py:635` |
| Doku-Reihenfolge | Der Finalizer verifiziert vor dem Commit; `PROGRESS.md` wird im Commit-Pfad bzw. anschliessend ergaenzt. Der Lauf kann daher an Doku-Drift scheitern, bevor genau dieser Lauf seinen Abschluss dokumentiert. | `werkstatt/phases/finalize.py:141-156,211-220`; `werkstatt/committer.py` |
| Chatstatus | `read_status` liest STATUS/PROGRESS, nicht den lebenden Prozess. Die Web-API hat einen separaten Live-Endpunkt fuer Loop-Zustand. | `werkstatt/chat_tools.py:272`; `werkstatt/web/app.py:808` |
| Events | Agenten-LLM-Aufrufe koennen Start/Ende protokollieren, wenn `RunState` mitgegeben wird. Der Builder-Aufruf in `roles/builder/run.py` uebergibt in diesem Pfad keinen State an `ask_llm`; sein Spinner/Eventbild ist dadurch lueckenhaft. | `werkstatt/agent.py:711-731`; `werkstatt/roles/builder/run.py:363` |
| Planung | Scout ist teilweise bedarfsabhaengig; Architect kann Prosa liefern, die ein separater Planner-Split nochmals in Tasks zerlegt. Das kann doppelte Planung erzeugen. | `werkstatt/planner.py:76-...` |
| Chat-Runden | Die aktuelle Chat-API setzt `_DEFAULT_MAX_ROUNDS = None`; ein sichtbarer alter `[chatloop: maxrounds=5...]`-Eintrag belegt deshalb keinen aktuellen globalen Fuenf-Runden-Deckel. | `werkstatt/chat_agent.py:23,536,575` |
| Gates/UI | Gate-Banner/Modal und Chat sind getrennte UI-Bestandteile. Der akzeptierte ADR-0029 verlangt Plan-Gates als Chat-Karten; dieser Vertrag ist nicht durchgaengig umgesetzt. | `static/layout.html`; `static/gate_panel.js`; ADR-0029 |
| Persistenz | Chatjobs und Loop-Registry persistieren Teile der Arbeit und erlauben Replay/Prozessbezug. Ein vollstaendiger, gemeinsamer Run-Koordinatorzustand fuer Ziel, Inbox, Checkpoints, Evidence Ledger und Recovery ist daraus noch nicht ersichtlich. | `werkstatt/chat_jobs.py`; `werkstatt/web/loop_registry.py`; `werkstatt/phases/state.py` |

## Konkreter Fehlermechanismus

Der im Screenshot sichtbare `phase_end`-Fehler passt zu einem strukturellen
Problem: Ein harter Doku-Verify laeuft im Finalizer. Bei Rot wird der Lauf
als fehlgeschlagen markiert; derselbe Run bekommt dort keinen Diagnose- und
Repair-Zyklus. Zusaetzlich ist die Reihenfolge empfindlich, wenn der
PROGRESS-Eintrag erst nach dem Verify bzw. Commit geschrieben wird. Diese
Bestandsaufnahme belegt die Architektur-Luecke, aber nicht den vollstaendigen
stdout/stderr eines konkreten Server-Runs. Fuer dessen exakte Ursache muessen
Run-ID, Verify-Artefakt und Event-Store zusammen ausgewertet werden.

Die richtige Reparatur ist nicht, `doku_drift` pauschal weich zu machen.
Das Gate muss semantisch und zeitlich korrekt eingeordnet werden: erst
Run-Dokumentation vorbereiten, dann den finalen Dokumentations- und
Codezustand pruefen; ein rotes Ergebnis wird als strukturiertes Failure
zurueck an denselben Koordinator gegeben. Human Gates bleiben bestehen.

## Was beibehalten wird

- Deterministische, projektgebundene Tools und Verify-Kommandos.
- Human Gates fuer Plan, Ergebnis und echte Risiko-/Scope-Aenderungen.
- Event Store, Replay, Run-Registry und getrennte Chatjobs als Bausteine.
- Builder als kontrollierter Schreibpfad; Verifikation unabhaengig vom Modell.
- Scout/Explorer fuer breite oder unklare Recherche, Architect fuer echte
  Architekturentscheidungen und Reviewer fuer risikoreiche Aenderungen.
- STATUS als Queue genehmigter Arbeit und PROGRESS als Verlauf.

## Was ersetzt werden soll

Die starre Runtime-Kette aus Phasen wird durch einen dauerhaften,
zielorientierten Run-Koordinator ersetzt. Eine Phase ist dann kein
Zwangsschritt, sondern hoechstens ein UI-/Audit-Label fuer eine Aktion.
OP-Run und Chat-Auftrag erzeugen denselben Run-Datensatz. Der Koordinator
waehlt je nach Befund die naechste erlaubte Faehigkeit und setzt am
Checkpoint fort, bis Ziel belegt erreicht, menschliche Entscheidung
noetig, Auftrag gestoppt oder ein echtes Budget ausgeschoepft ist.

Das Zielbild und der begruendete Migrationspfad stehen in
[`ADR-0032`](adr/ADR-0032-adaptiver-zielorientierter-run-kern.md).

