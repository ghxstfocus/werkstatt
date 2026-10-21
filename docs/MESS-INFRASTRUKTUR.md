
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
