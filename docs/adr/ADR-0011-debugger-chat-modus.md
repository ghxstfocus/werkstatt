# ADR-0011: Debugger als Chat-Modus (evidence-first)

- **Datum:** 2026-11-04
- **Status:** accepted
- **Kontext:** Bei fehlgeschlagenem Run hat der Nutzer heute drei
  Optionen: Chat fragen (read-only, schnell, aber ohne Laufzeit-
  Evidenz), Coding-Loop neu starten (langsam, riskant), oder
  manuell fixen. Es fehlt eine mittlere Stufe, die **reproduziert**
  statt **raet** — professionelle Debugging-Agenten (pi-debug-mode,
  VS-Debugger-Agent) arbeiten evidence-first: reproduce →
  investigate → fix → verify. Der Coding-Loop ist dafuer zu
  schwergewichtig; der Chat hat zu wenige Tools.

**Fragestellung:** Wie kommt Reproduktions-Faehigkeit (Tests
ausfuehren, temporaere Tests schreiben) in den Chat, ohne dass der
Chat Produktionscode schreiben kann?

**Optionen:**

A) Debugger als eigener Agent (dritter Loop).
B) Debugger als Modus des Chats (`modus="debugger"`), mit
   zusaetzlichen Tools, aber **keinem** Schreibrecht auf
   Produktionscode.

## Entscheidung

**Option B — Chat-Modus mit erweiterten Tools.**

- `chat_loop(session, msg, tools, modus="chat"|"debugger")`.
- Im Debugger-Modus zusaetzlich verfuegbar:
  - `pytest_run(path, test)` — einzelne Tests, mit Timeout.
  - `read_file(path, start, end)` — Zeilenbereich (fuer Stacktraces).
  - `write_temp_test(content)` — schreibt **nur** nach
    `.werkstatt/temp_tests/`, nie nach `tests/`/`werkstatt/`.
- **Kein** Produktionscode-Schreibrecht. Der Fix bleibt ein
  Diff-Vorschlag (Text), den der Mensch annimmt oder an den
  Coding-Loop weitergibt.
- Session-Events markieren `modus` je Turn, damit der Verlauf
  nachvollziehbar bleibt.

**Begruendung:** Reproduktion ist der entscheidende Schritt zwischen
"ich rate" und "ich weiss". Ein eigener Debugger-Agent (A) waere
Overkill: gleicher LLM, gleiches Session-Modell, gleiche Projekt-
Kontext — nur ein anderer System-Prompt und 3 zusaetzliche Tools.
Der Chat ist der richtige Traeger.

Die Restriktion "nur temp_tests" ist die Sicherheitsgrenze:
Reproduktion braucht einen Test, aber der Test darf nicht mit dem
Produktionscode verwechselt werden. Der Nutzer entscheidet ueber
jeden Fix explizit.

## Konsequenzen

Positiv:
- Sekundenschnelle Diagnose wird möglich, ohne Risiko.
- Reproduzierbare Fehler (Test schlaegt zuverlaessig fehl) sind
  sofort diagnostizierbar.
- Fix bleibt Diff-Vorschlag → menschliche Kontrolle.

Negativ:
- `.werkstatt/temp_tests/` muss aufgeraeumt werden (Cleanup nach
  Session-Ende, sonst sammelt sich Muell).
- Debugger-Modus ist maechtiger als Chat-Modus → mehr Risiko bei
  Prompt-Injection (Test-Inhalt koennte Shell-Code enthalten).

Neutral:
- Der Coding-Loop bleibt unveraendert — Debugger ist keine
  Konkurrenz, sondern Vorstufe.
