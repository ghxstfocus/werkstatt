# Mess-Infrastruktur — Recherche und Einordnung (Block M)

Stand: 2026-10-21, HEAD 59fc2a8. Branch umbau/phase-2.

## Zweck

Dieses Dokument haelt fest, wie die Werkstatt ihre Bau-Agenten (Planner,
Builder, Reviewer) mit praezisen, deterministisch gemessenen Daten
versorgt — und was der Markt dafuer schon bietet. Es ist die Vorarbeit
fuer einen eigenen Block **Block M** (Mess-Infrastruktur), der nach
3a-2d und vor 3a-3 (Deadlock) gebaut werden soll.

## Ausgangsproblem

Die Werkstatt hat in der Session 2026-10-21 mehrere Bloecke gebaut
(3a-1c-2a/b, 3a-1c-4, 3a-2a), bei denen **Messfehler** und
**Behauptungen ohne Beleg** zu fast erfolgreichen, aber fehlerhaften
Commits gefuehrt haetten. Beispiele:

- M-57 (Commit-Body-VOR-Werte ohne Vor-Comm-SHA)
- M-58 (Return-Verteilung 3a-2d: 3 statt 2)
- M-59 (state.phase_korrektur_zyklus angeblich geteilt, war es nicht)
- M-60 (VorlaufErgebnis-Namenskonflikt)
- M-61/M-63 (Return-Zaehlung 3a-2c: 6 vs 7, 3a-2b: 4 vs 5)
- M-62 (_phase_vorlauf 6 vs 7 Returns — Erfolgspfad fehlte in Zaehlung)

Jedes Mal half ein read-only-Messblock (ast, git show, grep). Jedes Mal
haette ein **deterministischer Block-Report** den Fehler verhindert.

## Recherche 2026-10-21 — Was der Markt bietet

### 1. Aider — Repository Map
- tree-sitter parst Dateien, baut Symbol-Graph, rankt per PageRank,
  rendert kompakte Karte (Signaturen) innerhalb Token-Budget.
- Fuer uns relevant: **Idee "Struktur statt Code an LLM"**.
- Grenze: keine Block-Semantik (Returns, state.X-Zonen).

### 2. codebase-index
- CLI: refs, path, impact, diff-impact. --compact ist explizit fuer
  Agenten formatiert (path:start-end symbol + nummerierte Zeilen).
- Fast deckungsgleich mit unserem "Anker-Report".
- Grenze: generischer Repo-Index, kein Block-Report.

### 3. CodeWalker (MCP-Server)
- Deterministisch, offline, jedes Signal mit file:line-Evidence,
  keine LLM-Guesses.
- Fuer uns relevant: **Haltung "Evidence, nicht Guess"**.
- Grenze: generisch, kein Block-Begriff.

### 4. CodeCortex
- Persistente Intelligence-Schicht (Repo-Map, Symbol-Graph,
  Git-History, Impact, Architektur). Liefert pro Task das kleinste
  nuetzliche Evidence-Paket. "Every change has a blast radius."
- Fuer uns relevant: **Impact-Denken**.
- Grenze: breites Produkt, nicht unsere Block-Semantik.

### 5. readmenator
- AST + Regex, generiert INDEX.md, API.md, GOTCHAS.md, SECURITY.md
  als agentenfreundliche Markdown-Dateien.
- Fuer uns relevant: **Vorab-Generierung von Warnungen ("GOTCHAS")**.

## Erkenntnis

Alle Profi-Tools bauen **denselben Kern**: AST -> Symbol/Referenz/
Return-Information -> kompaktes, evidenzbasiertes Paket fuer den
Agenten. **Niemand** baut das spezifisch fuer einen Monolithen wie
pipeline.py mit 5000+ Zeilen, 22 Returns und Block-Semantik.

Unsere read-only-Messbloecke sind **prototypisch genau das**, was
CodeCortex/CodeWalker als Produkt bauen — nur ohne Verpackung.

## Vorschlag Block M (Mess-Infrastruktur)

**Position:** Nach 3a-2d, vor 3a-3 (Deadlock).
**Kategorie:** 2 (Werkzeug, kein Runtime-Code).
**Kein Einfluss auf 3a-2x.**

### Bausteine

Drei Skripte unter tools/mess/:

1. `anker.py <funktion>` — Funktions-Report:
   Zeilenbereich, Signatur, Docstring-Zeilen, Return-Liste mit
   If-Kontext, state.X/config.get-Zugriffe, Aufrufer, getsource-Tests,
   Nachbar-Funktionen, `--json`-Flag.

2. `block.py <datei> <start> <ende>` — Block-Report:
   Statements in der Zone, Returns mit If-Kontext, state.X/config.X,
   audit-Kinds, Tests der Zone. **Der eigentliche Hebel fuer Planner
   und Builder.**

3. `baseline.py` — Baseline-Report (JSON):
   pytest, ruff, mypy (isoliert), AST-Test, Katalog.

### Hybrid-Ansatz

- **Symbol-Referenzen, Aufrufer, getsource-Tests:** aus etabliertem
  Tool (codebase-index/CodeWalker) beziehen, wenn praktikabel.
- **Block-Semantik:** eigenes block.py, weil kein Tool das liefert.

### Wirkung

- Planner bekommt pro Block einen Anker-Report statt 5000 Zeilen
  pipeline.py.
- Builder bekommt im Prompt die exakte Zone + Returns + state.X + Tests.
- Reviewer prueft gegen den Report.
- M-58 bis M-63 waeren in einer Runde aufgefallen.


## Explorer-Subagent (W61) — Konsument und Auftraggeber

Der Explorer existiert bereits in pipeline.py (W61, aktiv):
- `EXPLORE_SUBAGENT_PROMPT = "Du bist ein Suchexperte."` (Z. s. grep)
- `rufe_explore_subagent(...)` -> `_subagent_lauf(EXPLORE_SUBAGENT_PROMPT, ...)`
- `_subagent_lauf` erzeugt `sub_state` via `build_subagent_state`
  und ruft `execute_commands` mit `quelle="subagent"`.
- `BASH_SUBAGENT_PROMPT` und `BROWSER_SUBAGENT_PROMPT` sind inaktiv
  ("fuer spaeter").

Der Explorer ist ein LLM-gesteuerter Suchexperte, der Shell-Befehle
absetzt. Kein deterministisches Skript.

## Block M als Aufwertung des Explorers

Block M (tools/mess/) macht den Explorer praeziser:
- Explorer bekommt `tools/mess/block.py` als Werkzeug.
- Statt grep/ast-Suppe selbst zu kochen -> deterministischer
  Block-Report als Input.
- Planner/Builder/Reviewer sehen den Explorer-Output mit exakten
  Zeilen, Returns, state.X-Zonen, Tests.

Damit ist Block M **keine neue Rolle**, sondern die Aufwertung des
bestehenden Explorers: gleicher Aufruf (`rufe_explore_subagent`),
aber mit deterministischem Backend.

## Was der Explorer-Report liefern soll (Zielbild)

Fuer einen Block-Auftrag ("3a-2b, Z. 2242-2430, Loop-Extraktion"):
- Zeilen, Signatur, Docstring-Zeilen der Zone
- vollstaendige Return-Liste mit If-Kontext
- state.X / config.get / audit-Kinds mit Zeilen
- Aufrufer und getsource-Tests
- Nachbar-Funktionen (Zeilen)
- Baseline (pytest/ruff/mypy/AST/Katalog)

Format: strukturiertes JSON + kurze Text-Zusammenfassung. Der
Explorer kann beides an Planner/Builder weitergeben.
