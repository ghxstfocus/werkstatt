# Umbau-Fahrplan — Werkstatt → Profi-Architektur

Stand: 2026-10-19
Status: EMPFEHLUNG (noch nicht beschlossen — braucht Abnahme
durch Bau-Chat und Reviewer-Chat)

## 0. Warum

Die Werkstatt funktioniert (Phase 20b durch, Phase 21 U1
gruen). Aber der Preis ist ein 12.800-Zeilen-Monolith mit
166 Audit-Kinds, 6+ Rollen und einer Kultur der Symptom-
Fixes (21 W-Bloecke in zwei Sitzungen).

Die Profis bauen das Gegenteil: kleinere Dateien, weniger
Rollen, haertere Guards, mehr Messung. Dieser Fahrplan
ist die Architektur-Korrektur.

## 1. Profi-Referenzen (recherchiert, mit Beleg)

- **Claude Code:** Subagenten sind Isolation, nicht Rollen.
  Eigener Kontext, eigener Prompt, eigener Tool-Zugriff.
  Parent sieht nur das Ergebnis.
- **Aider:** Repo-Map mit tree-sitter + PageRank, 1024
  Tokens Default. 4,3–6,5% Context-Nutzung vs. 54–70%
  bei iterativer Suche.
- **Cursor:** Dynamic Context Discovery, 46,9% Token-
  Reduktion. Offload in Dateien, `tail` + selektives
  Lesen statt Truncation.
- **OpenHands:** Critic mit Quality-Threshold 90/100,
  max 3–5 Iterationen. Fortschritts-Check.
- **12-Factor Agents:** Factor 3 (Own context), Factor 4
  (Tools sind structured outputs), Factor 5 (Unify
  state), Factor 10 (Small focused agents, 3–10 Steps).
- **AgentSeed:** verify_code als hartes MCP-Gate, nicht
  Prompt-Bitte. "Done means observed fact".
- **Keystone:** "Grep before invoking". Type-check-Sensor
  faengt falsche Signaturen.
- **Stanford CooperBench:** Multi-Agent ist oft
  schlechter als Single-Agent. "Curse of coordination".
- **Hermes God-File:** Facade + Siblings, 2000-Zeilen-
  Gate pro Datei, 300 Zeilen pro Funktion.
- **Chroma Context Rot:** Alle 18 Frontier-Modelle
  degradieren ab 50K Tokens, auch bei 200K-Fenster.

## 2. Ist vs. Soll (harte Zahlen)

| Dimension | Ist | Soll |
|---|---|---|
| pipeline.py | ~12.800 Z. | < 100 (Facade) |
| Groesste Datei | 12.800 Z. | < 500 Z. |
| Rollen | 6+ | 3 (Plan, Act, Verify) |
| Audit-Kinds | 166 | 20 |
| Pipeline-Tests | 1189 | 50 |
| Produkt-Tests | 11 | 50 |
| builder_patch.md | 486 Z. | < 300 Z. |
| planner.md | 299 Z. | < 150 Z. |
| Loop max Iterationen | endlos | 3 |
| Fortschritts-Check | nein | ja |
| mypy tests/ | nein | ja (always_run) |
| Repo-Map im Prompt | nein | ja (1024 Tokens) |
| phase.yaml | YAML | state.json |

## 3. Die 7 Phasen

### Phase 0 — Baseline messen (1 Tag)

Nur messen, nicht bauen.

- wc -l pipeline.py, agents/*.md
- grep -c "audit(" pipeline.py
- git rev-list --count seit W1
- pytest --collect-only pro Datei
- Ein echter Phase-21-Lauf mit Zeitmessung

### Phase 1 — Loeschen (2–3 Tage)

Ziel: 40% Komplexitaet entfernen, ohne Funktion.

- 146 Audit-Kinds loeschen, auf 20 reduzieren.
- Rollen test_generator, coverage/chaos, Solver entfernen
  (sind Measurements, keine Rollen).
- verify_code (AST) loeschen, durch mypy tests/ ersetzen.
- 1000+ Pipeline-Tests loeschen, auf 50 Integration + 50
  Produkt.
- _sim_mtime, --allow-empty, D2-Sonderfaelle entfernen
  (Symptom-Fixes, durch Phase 3–4 obsolet).

Kriterium: pytest gruen. Rote Tests sind Symptom-Tests
und gehoeren geloescht.

### Phase 2 — Modularisieren (3–5 Tage)

pipeline.py → 6 Module, jede < 500 Zeilen.

- werkstatt/orchestrator.py: run_phase, run_pipeline (< 400)
- werkstatt/apply.py: apply_code_patches (< 300)
- werkstatt/verify.py: verify_values, mypy-Runner (< 200)
- werkstatt/prompts.py: _build_commit_input, _build_judge_input (< 300)
- werkstatt/audit.py: audit(), JSONL-Writer, 20 Kinds (< 100)
- werkstatt/phase.py: phase.yaml → state.json (< 300)
- pipeline.py: Facade, main() (< 100)

Pattern: Hermes Facade + Siblings. Jede Datei eine
Verantwortung. Gate: keine Datei > 500 Z., keine
Funktion > 100 Z.

### Phase 3 — Loop neu bauen (3–5 Tage)

Plan-Act-Verify statt 7-gliedriger Kette.

PLAN (Planner): Auftrag + Repo-Map → Contract mit
Ankern, Pfaden, Tests.
ACT (Builder): Contract + Repo-Map + Zieldatei-Snippets
→ Patch. Guard: mypy tests/ + verify_values.
VERIFY (Judge): Patch + voller Datei-Inhalt + ruff/mypy
Exit-Codes → GO / NO-GO / ESKALATION. Threshold 90/100.

Kern-Aenderungen:
1. Kein failed → pending endlos. Nach 3 Iterationen ohne
   Fortschritt: Eskalation an Mensch.
2. Kein Planner-Resume bei failed. Nur bei no_go.
3. Kein Solver, kein Reviewer-Recovery.
4. Fortschritts-Check: letzter_test_fehler-Laenge oder
   failed_test_ids-Anzahl muss sinken. Sonst Eskalation.

### Phase 4 — State-Persistence (2 Tage)

phase.yaml → state.json + JSONL-Audit.

- phase.yaml (YAML, Regex, fragil) → state.json
  (JSON, schema-validiert).
- audit-logs/*.jsonl (166 Kinds) → audit.jsonl (20 Kinds).
- letzter_test_fehler (String, 2000 Z.) →
  state.json: {letzter_fehler: {...}}.
- mess_protokoll (String) → state.json:
  {messungen: [{pfad, sha, datei}]}.

Format: JSON + JSON-Schema. Kein YAML, kein Regex.

### Phase 5 — Grounding (2–3 Tage)

Keine erfundenen APIs mehr, ohne 166-Kind-Apparat.

- mypy tests/ in always_run (Keystone: type-check sensor).
- Repo-Map (tree-sitter + PageRank, 1024 Tokens) im
  Planner- und Builder-Prompt (Aider: 4,3–6,5% Context).
- grep-Pflicht im Builder-Prompt: "Bevor du eine Funktion
  aufrufst, grep sie" (Keystone GOLDEN RULE).
- verify_values behalten (Enum-Checks, einzigartig).

Wegfall: verify_code (AST), verify_code_kwargs
(inspect.signature). mypy + grep ersetzen beides.

### Phase 6 — Prompts kuerzen (2 Tage)

- builder_patch.md 486 → < 300 (EINRUECKUNG 123 → 28,
  NEUE DATEIEN 54 → 20, COMMAND: RUN 44 → 20).
- planner.md 299 → < 150 (3 Beispiele raus,
  MESS-PFLICHT 23 → 10).
- builder_commit.md 105 → 105 (bleibt).
- judge.md 90 → 90 (bleibt).

Regel: Jede Zeile muss die >=80%-Frage beantworten.
Was nicht >=80% gebraucht wird, fliegt raus und wird
durch Repo-Map + grep ersetzt.

### Phase 7 — Tests umdrehen (2 Tage)

50 Integration + 50 Produkt statt 1189 Pipeline.

- Integration: run_phase mit echtem State,
  apply_code_patches mit echten Patches,
  verify_values mit echten Enums.
- Produkt (security-ai): Audit-Pfade (APPLIED, FAILED,
  ROLLED_BACK), ChangeApplier, Repo-Map.

Loesch-Kriterium: Jeder Pipeline-Test, der eine private
Funktion testet, fliegt. Jeder Test, der ein Verhalten
testet, bleibt.

## 4. Loeschen / Behalten / Neu denken

### Loeschen
- 146 Audit-Kinds (Factor 4: structured outputs).
- Rollen test_generator, coverage/chaos, Solver.
- verify_code (AST) — mypy + grep ersetzen es.
- _sim_mtime, --allow-empty, D2-Sonderfaelle.
- 1000+ Pipeline-Tests.
- phase.yaml (YAML).
- 7-gliedrige Deadlock-Kette.

### Behalten
- Audit-Prinzip (aber 20 Kinds, JSONL).
- Human-Gate.
- Phasen-Idee (Unterbloecke, Contracts).
- Feedback-Loop (letzter_test_fehler im Prompt).
- verify_values (Enum-Checks).
- Subagenten (nur fuer Isolation, nicht fuer Rollen).
- max_tokens_judge 32768.
- builder_commit.md (105 Z., schon schlank).

### Neu denken
- pipeline.py → 6 Module (Facade + Siblings).
- Loop → Plan-Act-Verify mit Fortschritts-Check.
- State → state.json + JSON-Schema.
- Prompts → Repo-Map (1024 Tokens) + grep-Pflicht.
- Tests → 50 Integration + 50 Produkt.
- Audit → 20 Kinds, JSONL, schema-validiert.

## 5. Reihenfolge

Phase 0 (Messen)
  → Phase 1 (Loeschen)
  → Phase 2 (Modularisieren)
  → Phase 3 (Loop neu)
  → Phase 4 (State)
  → Phase 5 (Grounding)
  → Phase 6 (Prompts)
  → Phase 7 (Tests)

Kritischer Pfad: 1 → 2 → 3. Ohne Loeschen kein
Modularisieren, ohne Modularisieren kein neuer Loop.

Parallel moeglich: Phase 5 (Grounding) ab Phase 2,
Phase 6 (Prompts) ab Phase 5.

## 6. Erfolgs-Kriterien (messbar)

| Metrik | Ist | Ziel | Messung |
|---|---|---|---|
| pipeline.py Zeilen | 12.800 | < 100 | wc -l |
| Groesste Datei | 12.800 | < 500 | wc -l |
| Rollen | 6+ | 3 | ls agents/ |
| Audit-Kinds | 166 | 20 | _KATALOG_SOLL |
| Pipeline-Tests | 1189 | 50 | pytest --collect-only |
| Produkt-Tests | 11 | 50 | pytest tests/unit/ |
| builder_patch.md | 486 | < 300 | wc -l |
| planner.md | 299 | < 150 | wc -l |
| Loop-Iterationen max | endlos | 3 | Code |
| Fortschritts-Check | nein | ja | Code |
| mypy tests/ | nein | ja | always_run |
| Repo-Map im Prompt | nein | ja (1024 Tokens) | Prompt-Laenge |
| phase.yaml | YAML | state.json | Datei-Endung |

## 7. Die eine Regel

"Is this needed on >=80% of turns?
 Yes -> pre-load. No -> identifier plus a tool to fetch it."

Jede Datei, jede Funktion, jeder Prompt-Block, jeder
Test, jeder Audit-Kind muss diese Frage beantworten.
Was nicht >=80% ist, fliegt raus und wird durch grep +
Repo-Map + mypy ersetzt.

Das ist der Unterschied zwischen der Werkstatt
(Symptom-Kultur, 12.800 Zeilen) und den Profis
(Ursachen-Kultur, 6 Module).

## 8. Naechster Schritt

Dieser Fahrplan braucht Abnahme durch:
1. Bau-Chat (macht die Umsetzung).
2. Reviewer-Chat (prueft die Architektur).

Vor Phase 0: Ein Beschluss, ob der Fahrplan in dieser
Form umgesetzt wird. Wenn ja: Phase 0 (Messen) startet
im naechsten Bau-Chat.
