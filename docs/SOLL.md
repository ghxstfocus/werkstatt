# SOLL-Zustand — Werkstatt

**Status:** Zielarchitektur (nicht gebaut)
**Stand:** 2026-11-07
**Zweck:** Diese Datei beschreibt, wohin Werkstatt sich entwickelt.
Jedes LLM, das in diesem Repo arbeitet, soll daraus das Ziel
verstehen — nicht nur den IST-Zustand (siehe `docs/ARCHITECTURE.md`).

---

## 1. Die Vision in einem Satz

Ein Mensch arbeitet mit einer **Web-UI**, um Software zu bauen.
Die UI zeigt den Zustand des Loops, bietet einen Chat für Diagnose
und einen Debugger für Reparatur. Der Loop ist der Motor; der Chat
ist das Interface; das Erfahrungs-Gehirn ist das Gedächtnis.

---

## 2. Das Zielbild

                        MENSCH
                          │
                          │ sieht Timeline, Chat, Memory
                          │ entscheidet an Gates + Repair Ladder
                          ▼
                ┌─────────────────────────┐
                │        WEB-UI           │
                │  Runs │ Timeline │ Chat │
                │  Workbench-Drawer       │
                │  Repair-Ladder-Banner   │
                │  Memory-Panel           │
                └───────────┬─────────────┘
                            │ HTTP / WebSocket
            ┌───────────────┼───────────────┐
            ▼               ▼               ▼
    ┌───────────┐   ┌───────────┐   ┌───────────┐
    │ Chat-     │   │ Chat-     │   │ Loop      │
    │ Agent     │   │ Debugger  │   │ (Motor)   │
    │ (read-only│   │ (Modus)   │   │ (headless)│
    └─────┬─────┘   └─────┬─────┘   └─────┬─────┘
          │               │               │
          └───────────────┼───────────────┘
                          ▼
                 ┌──────────────────┐
                 │  ERFAHRUNGS-     │
                 │  GEHIRN          │
                 │  Episoden+Regeln │
                 │  + Semantic      │
                 │  zweistufig      │
                 └──────────────────┘

**Drei Prinzipien:**

1. **Der Mensch entscheidet.** Chat und Loop schlagen vor,
   der Mensch wählt an Gates und in der Repair Ladder.
2. **Der Loop ist Motor, nicht Interface.** Er läuft headless,
   die UI steuert ihn über HTTP-Gates.
3. **Tests sind Spec.** Code folgt Spec, nicht umgekehrt.
   Der Builder ist test-blind.

---

## 3. Die vier Schichten

| Schicht | Aufgabe | OPs |
|---|---|---|
| **1. Loop** | Motor, baut Code, headless | 123, 188, 189, 190, 193, 195 |
| **2. Chat** | Interface, read-only Diagnose | 124, 125, 126, 127 |
| **3. Chat-Debugger** | Reparatur-Modus, Vorschlag+Fix | 128, 132 |
| **4. Gehirn** | Gedächtnis, zweistufig | 113, 113a, 113i, 129, 130, 131, 160 |

Jede Schicht hat eigene Skizzen und OPs — Details in den
folgenden Abschnitten.

---

## 4. Schicht 1 — Loop (Motor)

### 4.1 Was der Loop tut

Der Loop liest OPs aus `docs/STATUS.md`, plant sie in Tasks,
baut sie, testet sie, committet bei Grün. Er läuft **headless** —
Gates sind HTTP-Endpoints statt stdin.

### 4.2 Der SOLL-Ablauf (7 Phasen)

    Phase 1: Explorer
      deterministisch: ruff, pytest, key_files
                                  │
                                  ▼
    Phase 2: Plan-Gate + Planner
      Architect liefert Prosa + test_spec
      Planner splittet in Tasks (OHNE tests/ in task_files)
                                  │
                                  ▼
    Phase 2b: TEST-LOOP  ★ NEU (OP-210)
      Test-Agent baut Tests aus test_spec
      Qualification: MÜSSEN rot auf unverändertem Repo sein
      Freeze: SHA256 in state.test_manifest
      Bei Test-Bug: Test-Thaw (OP-213)
                                  │
                                  ▼
    Phase 3: CODE-LOOP (test-blind)  ★ OP-211
      Builder sieht tests/ NICHT
      verify-Stage test_integrity prüft SHA256
      pytest_changed läuft auf eingefrorenen Tests
      Bei Fail: Reflection → Debugger-Vorschlag via Chat
                                  │
                                  ▼
    Phase 4: PHASE-REVIEW
      Reviewer prüft gesamten Phase-Diff
      Bei Fail: Phase-End-Reflection (max 2 Runden)
                                  │
                                  ▼
    Phase 4b: MUTATION-GATE  ★ NEU (OP-214)
      pytest-gremlins auf geänderte Files
      Score ≥ 0.8 → OK, sonst Audit (kein Block)
                                  │
                                  ▼
    Phase 5: COMMIT-GATE (HTTP, OP-202)
      Wartet auf POST /api/runs/{id}/gate
      Bei j: commit + push

### 4.3 Die 7 Loop-Rollen

| Rolle | Skills | Aufgabe |
|---|---|---|
| Explorer | `using-werkstatt` | ruff, pytest, key_files |
| Scout | — | Auftrag formulieren, IST-Zustand prüfen |
| Architect | — | Prosa-Plan + `test_spec` (deepseek-reasoner) |
| Planner | `using-werkstatt`, `milestone-planning`, `plan-crafting` | Task-Zerlegung |
| Builder | — | Code-Patches (test-blind, OP-211) |
| Reviewer | `review-work` | Diff-Prüfung gegen Task-Description |
| Reflection | — | Fehlerbehandlung nach Verify-Fail |

**Änderung gegenüber IST:**

- **`systematic-debugging`-Skill** wandert von `reflection`/`builder`
  zum **Chat-Debugger** (OP-240). Nicht in Loop-Rollen.
- **Test-Agent** ist keine Loop-Rolle im klassischen Sinn, sondern
  ein Phase-2b-Agent (OP-210).

### 4.4 Task-Typen (`action`)

| Action | Bedeutung |
|---|---|
| `create` | Neue Datei anlegen |
| `update` | Bestehende Datei ändern |
| `read` | Nur lesen, kein Builder |
| `verify` | Zustand prüfen, kein Builder (seit OP-183) |
| `test` ★ NEU | Vom Test-Agent gebaut (OP-210), kein Builder-Call |

### 4.5 Verify-Kette

**IST (9 Stages, alle hart):**
py_compile_changed, ruff_changed, state_drift, control_drift,
import_drift, mypy_changed, pytest_changed, contract_check,
pytest_regression.

**SOLL — 3 neue Stages:**

| Stage | Phase | Hart | OP |
|---|---|---|---|
| `test_integrity` | post_build | ja | OP-211 |
| `test_must_fail_initial` | pre_build | ja | OP-211 |
| `mutation_gate` | post_build | nein (4 Wochen) | OP-214 |

### 4.6 State-Felder (neu)

    test_spec: list[dict]          # OP-210 (Architect-Output)
    test_manifest: dict[str, str]  # OP-210 (SHA256 pro Test-Datei)
    test_thawed: bool              # OP-213 (Test-Thaw passiert)

---

## 5. Schicht 2 — Chat (Interface)

### 5.1 Was der Chat ist

Ein **read-only Assistent pro Projekt**. Beantwortet Fragen,
liest Audit-Logs, prüft Diffs, liefert Diagnosen. **Kann nichts
schreiben** (außer im `debugger`-Modus, siehe Schicht 3).

### 5.2 Die 3 Chat-Modi (OP-240)

| Modus | Tools | Wann |
|---|---|---|
| `manuell` | read-only | Diagnose ohne Reparatur |
| `debugger` | + pytest_run, write_temp_test | Reparatur mit Fix-Vorschlag |
| `reject` | read-only | Ablehnung mit Begründung an Loop |

**Der Mensch wählt den Modus**, nicht der Chat.

### 5.3 Read-only Tool-Registry (OP-231)

| Tool | Zweck |
|---|---|
| `read_file(path, start, end)` | Datei-Inhalt lesen |
| `grep(pattern, path)` | Text-Suche |
| `git_log(n)` | Letzte Commits |
| `git_diff(ref)` | Diff gegen Ref |
| `audit_query(kind, since)` | Audit-Events filtern |
| `pytest_collect(path)` | Tests sammeln (nicht laufen) |
| `diagnose(state)` | Bekannte Fehlerklassen |
| `read_status()` | STATUS.md / PROGRESS.md |

**Nicht verfügbar:** `write_file`, `apply_patch`, `git_commit`.

### 5.4 Chat-Persistenz (OP-230)

SQLite pro Projekt: `events(seq, session_id, ts, kind, payload)`.

- `ChatSession.append(kind, payload)` — append-only
- `ChatSession.load()` — rekonstruiert Historie
- `derive_messages()` — LLM-Historie aus Events
- `list_sessions(project)` — Sessions auflisten

**Warum Events statt Messages?** Fork-fähig (Branch einer Session),
replaybar, auditierbar.

### 5.5 Chat-UI (OP-232 + OP-233)

    ┌─────────────────────────────────────────────────────┐
    │  Runs-Liste  │   Timeline        │   Chat          │
    │  (200px)     │   (flex)          │   (400px)       │
    │              │                   │                 │
    │  OP-210      │  ● Explorer 0.4s  │  [Nachrichten]  │
    │  ● running   │  ● Scout 2.1s     │  ...            │
    │              │  ● Architect 118s │  [Tool-Call]    │
    │  OP-211      │  ● Planner 3.2s   │  git_diff()     │
    │  ✓ done      │  ● Builder t1     │  → 42 Zeilen    │
    │              │  ✗ Reviewer       │                 │
    │              │                   │  [Eingabe]      │
    ├─────────────────────────────────────────────────────┤
    │  Workbench (collapsible Drawer)                     │
    │  [Dateien] [Diff] [Verify] [Audit] [Terminal]       │
    ├─────────────────────────────────────────────────────┤
    │  Status: 3/5 Tasks │ Verify ✓ │ Drift ✓ │ Phase 3   │
    └─────────────────────────────────────────────────────┘

**3-Spalten-Layout** (OP-233 Variante A):
- Links: Runs-Liste (Status pro OP)
- Mitte: Timeline (Phasen-Knoten aus Event-Store, aufklappbar)
- Rechts: Chat (immer sichtbar)

**Workbench-Drawer** (default geschlossen):
- Dateien-Browser
- Diff-Viewer
- Verify-Ergebnis
- Audit-Log
- Terminal

**Repair-Ladder-Banner** erscheint bei `run_failed` (OP-242).

---

## 6. Schicht 3 — Chat-Debugger (OP-240 + OP-242)

### 6.1 Was der Debugger ist

**Keine eigene Rolle, keine eigene Phase.** Ein **Modus** des Chat-
Agenten. Der Mensch schaltet den Chat in den Debugger-Modus, wenn
der Loop gescheitert ist und er reparieren will.

### 6.2 Der Debugger-Modus (OP-240)

**Zusätzliche Tools im `debugger`-Modus:**

| Tool | Zweck | Pfad-Beschränkung |
|---|---|---|
| `pytest_run(path, test)` | Test ausführen | — |
| `write_temp_test(content)` | Test-Datei schreiben | **nur** `.werkstatt/temp_tests/` |

**Was der Debugger NIE tut:**
- Test-Dateien in `tests/` schreiben (nur nach `.werkstatt/temp_tests/`)
- Fixes automatisch anwenden (immer Diff-Vorschlag, Mensch bestätigt)
- Fixes ins Gehirn schreiben ohne erfolgreichen Re-Run

### 6.3 Der 3-Wege-Check

Der Debugger prüft bei einem roten Test drei Fragen:

    Spec = was die OP fordert (aus AK-Text)
    Code = was der Builder gebaut hat
    Test = was der Test-Agent gebaut hat

    ┌──────────────────────────────────────────────────┐
    │  Code ≠ Spec, Test = Spec  →  FIX CODE           │
    │    Fix als Diff-Vorschlag, Mensch wendet an      │
    │    Loop-Re-Run → Verify grün                     │
    │                                                  │
    │  Code = Spec, Test ≠ Spec  →  TEST-THAW          │
    │    state.test_manifest = {}                      │
    │    Audit "test_thawed" mit Grund                 │
    │    zurück zu Phase 2b (Test-Loop)                │
    │                                                  │
    │  Code ≠ Spec, Test ≠ Spec  →  HUMAN-GATE         │
    │    Fundamentale Misalignment, Loop stoppt        │
    │                                                  │
    │  Alle = Spec, Test rot  →  HUMAN-GATE            │
    │    Infra/flaky/env, Loop stoppt                  │
    └──────────────────────────────────────────────────┘

### 6.4 Strukturierter Fix-Output

Der Debugger liefert einen `DebuggerFix`:

    {
      "signatur": "pytest_changed:test_verify_setzt_nicht",
      "ursache_tag": "code_bug",
      "diff": "...",
      "betroffene_dateien": ["werkstatt/phases/tasks.py"],
      "confidence": "high"
    }

### 6.5 Repair Ladder (OP-242)

Bei `run_failed`-Event erscheint in Timeline und/oder Chat ein
**Banner mit 3 Buttons**:

    ┌────────────────────────────────────────────────────┐
    │  Run #42 fehlgeschlagen (OP-210, 2/5 Tasks)        │
    │                                                    │
    │  [Chat analysiert]  [Debugger starten]  [Loop neu]│
    └────────────────────────────────────────────────────┘

**Die drei Stufen:**

| Button | Modus | Aktion |
|---|---|---|
| Chat analysiert | `manuell` | Chat liest Audit + Diff, liefert Diagnose |
| Debugger starten | `debugger` | Chat + pytest_run, schlägt Fix vor |
| Coding-Loop neu | — | Neuer Loop-Lauf mit gleicher `--aufgabe` |

**Kernprinzip:** Reparatur ist **eskalierend**. Der Mensch
entscheidet, welche Stufe er nimmt.

### 6.6 Der Reparatur-Flow (Kern-Use-Case)

    Loop läuft headless (OP-202)
        │
        ▼
    Fehler → run_failed-Event
        │
        ▼
    UI zeigt Banner mit 3 Buttons (OP-242)
        │
        ├─── [Chat analysiert] ─── manuell-Modus
        │       │
        │       ▼
        │   Chat liest Audit + Diff
        │       │
        │       ▼
        │   Diagnose-Text → Mensch entscheidet
        │
        ├─── [Debugger starten] ─── debugger-Modus
        │       │
        │       ▼
        │   Chat + pytest_run + 3-Wege-Check
        │       │
        │       ▼
        │   Fix als Diff-Vorschlag
        │       │
        │       ▼
        │   Mensch wendet an → Loop-Re-Run
        │       │
        │       ├── Verify grün → debugger_fix_verifiziert
        │       │   → OP-243 → Gehirn-Eintrag
        │       │
        │       └── Verify rot → kein Eintrag, neuer Versuch
        │
        └─── [Loop neu] ─── neuer Loop-Lauf
                │
                ▼
            gleicher Loop, gleiche Aufgabe

---

## 7. Schicht 4 — Erfahrungs-Gehirn

### 7.1 Was das Gehirn ist

Ein **zweistufiges Gedächtnis** für Fehler-Muster und Lösungen.
Nicht Freitext-Sammlung, sondern strukturierte Einträge mit
Vertrauensstufen.

### 7.2 Zweistufig (ADR-0010)

    ┌────────────────────────────────────────┐
    │  Projekt-DB                            │
    │  .werkstatt/erfahrung.db               │
    │  scope='project'                       │
    │  lokal, pro Projekt                    │
    └──────────────┬─────────────────────────┘
                   │  Promotion bei 2+ Projekten
                   │  + Sanitization
                   ▼
    ┌────────────────────────────────────────┐
    │  Global-DB                             │
    │  ~/.werkstatt/gehirn-global.db         │
    │  scope='global'                        │
    │  projektübergreifend                   │
    └────────────────────────────────────────┘

**Sanitization beim Aufstieg:**
- Pfade: `/opt/projekt/...` → `<project>/...`
- IPs maskieren (wie `redaction.py`)
- Projekt-Namen → `<project>`

### 7.3 Datenmodell — 4 Tabellen

| Tabelle | Zweck | Schlüssel-Felder |
|---|---|---|
| `erfahrung` | Episoden (Fehler → Lösung) | `problem_sig`, `loesung`, `erfolg`, `scope`, `quelle`, `ts` |
| `regeln` | Destillierte Muster | `titel`, `trigger`, `anweisung`, `trust`, `scope`, `widerlegt` |
| `semantic_memory` | Projekt-Fakten | `schluessel`, `wert`, `scope`, `confirmed`, `kontext` |
| `memory_ledger` | Append-only Audit | `aktion`, `regel_id`, `payload`, `commit_sha` |

**Trust-Stufen (`regeln`):**
- `candidate` — von LLM destilliert, 3+ Episoden
- `confirmed` — 2-3× erfolgreich angewendet
- `canonical` — 5+ Beobachtungen ohne Widerlegung

### 7.4 Schreiben ins Gehirn — 4 Quellen

| Quelle | Wann | OP |
|---|---|---|
| **Chat-Debugger** | Fix vorgeschlagen + Mensch angewandt + Re-Run grün | OP-243 |
| **Reflection** | Reflection-Erfolg nach Verify-Fail | OP-220 |
| **Log-Backfill** | Einmalig aus 30k Audit-Events | OP-220i |
| **Semantic** | Manuell (DB-Typ, User-Präferenz) | OP-222 |

**Kritisch (OP-243):** Chat-Debugger schreibt **nur** ins Gehirn, wenn
ALLE vier Bedingungen erfüllt sind:
1. Mensch wählt Debugger-Modus
2. Debugger schlägt Fix vor
3. Mensch wendet Fix an
4. Loop-Re-Run deterministisch grün

Ohne alle vier: **kein Eintrag**.

### 7.5 Lesen aus dem Gehirn — 2 Stellen im Loop

| Rolle | Confidence | Warum |
|---|---|---|
| **Reflection-Loop** | ≥ high | Reflection kann Memory nutzen, wenn Vertrauen hoch |
| **Chat-Debugger** | ≥ medium | Debugger kann Memory nutzen, weil Mensch entscheidet |

**Nicht**: Builder Standard-Pfad, Planner, Architect, Scout, Reviewer.
Diese Rollen sollen das aktuelle Problem lösen, nicht raten.

### 7.6 Reife-Modell

| Vorkommen | Status | Aktion |
|---|---|---|
| 1× | nur Audit-Event | kein DB-Eintrag |
| 2× | `erfahrung` mit `confidence=low` | — |
| 3× + erfolgreicher Fix | `confidence=medium` | Injektion in Debugger |
| 5× + erfolgreicher Fix | `confidence=high` | Injektion in Reflection + Debugger |

### 7.7 Destillation (OP-221)

    3+ Episoden mit gleicher problem_klasse
        │
        ▼
    LLM destilliert → candidate-Regel
        │
        ▼
    2-3× erfolgreich → confirmed
        │
        ▼
    5+ Beobachtungen ohne Widerlegung → canonical
        │
        ▼ (wenn in ≥2 Projekten confirmed)
    promote_to_global → global candidate (mit Sanitization)
        │
        ▼
    Mensch bestätigt manuell (tool --scan, kein Auto-Promote)

### 7.8 UI — Memory-Panel (OP-250)

Im Chat-Panel oder als eigener Tab:

    ┌────────────────────────────────────────────┐
    │  Canonical (global)        3 Regeln        │
    │  Confirmed (global)        8 Regeln        │
    │  Projekt-Regeln           12 Regeln        │
    │  Candidates                5 (unbestätigt) │
    │  ─────────────────────────────────────     │
    │  Diese Runde injiziert:    2 Regeln        │
    │                                            │
    │  [Regel für global vorschlagen]            │
    └────────────────────────────────────────────┘

**Klick auf Regel:** Inspector mit Beobachtungs-Historie, Quelle,
Kontext, Widersprüchen.

---

## 8. Die OP-Serien

### 8.1 Stufen-Modell (was zuerst, was hängt an was)

    ┌─────────────────────────────────────────────────────┐
    │  Stufe 1 — Loop headless + Basis                    │
    │                                                     │
    │    OP-202 (Gate-Bridge)                             │
    │    OP-201 (pyproject + test-tools)                  │
    └─────────────────────┬───────────────────────────────┘
                          │
    ┌─────────────────────┴───────────────────────────────┐
    │  Stufe 2 — Loop-Motor testbar                       │
    │                                                     │
    │    OP-210 (Test-Loop + Test-Thaw)                   │
    │    OP-211 (Builder test-blind + verify-Stages)      │
    │    OP-214 (Mutation-Gate)                           │
    │    OP-215 (Hypothesis)                              │
    │    OP-216 (Arch-Doku)                               │
    └─────────────────────┬───────────────────────────────┘
                          │
    ┌─────────────────────┴───────────────────────────────┐
    │  Stufe 3 — Gehirn-Basis                             │
    │                                                     │
    │    OP-220 (erfahrung-Tabelle)                       │
    │    OP-220a (scope-Spalte)                           │
    │    OP-220i (Log-Backfill)                           │
    │    OP-221 (Destillation + Promotion)                │
    └─────────────────────┬───────────────────────────────┘
                          │
    ┌─────────────────────┴───────────────────────────────┐
    │  Stufe 4 — Chat-Infrastruktur                       │
    │                                                     │
    │    OP-230 (Session-Store)                           │
    │    OP-231 (Chat-Agent)                              │
    │    OP-232 (Chat-UI)                                 │
    │    OP-233 (Timeline + Layout)                       │
    └─────────────────────┬───────────────────────────────┘
                          │
    ┌─────────────────────┴───────────────────────────────┐
    │  Stufe 5 — Chat-Debugger + Repair Ladder            │
    │                                                     │
    │    OP-240 (Debugger-Modus)                          │
    │    OP-242 (Repair Ladder Buttons)                   │
    │    OP-243 (Debugger → Gehirn)                       │
    └─────────────────────┬───────────────────────────────┘
                          │
    ┌─────────────────────┴───────────────────────────────┐
    │  Stufe 6 — Semantic + Memory-UI                     │
    │                                                     │
    │    OP-222 (Semantic Memory)                         │
    │    OP-250 (Memory-Panel)                            │
    └─────────────────────────────────────────────────────┘

### 8.2 Kritische Abhängigkeiten (nicht verhandelbar)

| OP | braucht | Warum |
|---|---|---|
| OP-220 | — | Basis erfahrung.db |
| OP-220a | OP-220 | scope-Spalte + Provenance-Spalten |
| OP-220i | OP-220a | Log-Backfill braucht Schema |
| OP-202 | — | Gate-Bridge, unabhaengig |
| OP-231 | OP-230 | Chat-Agent braucht Session-Store |
| OP-230 | — | Session-Store, unabhaengig |
| OP-232 | OP-231, OP-230 | Chat-UI braucht Chat-Agent |
| OP-233 | OP-232 | Timeline braucht Chat-UI-Layout |
| OP-240 | OP-231 | Debugger ist Modus des Chat-Agenten |
| OP-221 | OP-220a | scope + Provenance fuer Promotion |
| OP-222 | OP-220a | scope fuer Semantic Memory |
| OP-250 | OP-221, OP-222 | Regeln + Semantic muessen da sein |
| OP-242 | OP-231, OP-233, OP-240 | Alle drei Stufen verfuegbar |
| OP-243 | OP-240, OP-221 | Debugger-Event + Regeln-Tabelle |
| OP-210 | OP-201 | test-tools als Dependency |
| OP-211 | OP-210 | test_manifest aus Test-Loop |
| OP-214 | OP-211, OP-201 | pytest-gremlins aus test-tools |
| OP-213 | OP-210 | Test-Thaw im Test-Loop |
| OP-215 | OP-201 | hypothesis aus test-tools |
| OP-216 | OP-210, OP-240 | Doku nach Loop + Chat gebaut |
| OP-201 | — | pyproject, unabhaengig |
| OP-212 | OP-210 | Spec-Validator braucht test_spec |
| OP-241 | OP-240 | Debugger-Sandbox braucht Chat-Debugger |

**Status (2026-11-07):** ADR accepted, Code pending.
Alle OPs 113-197 sind als Header in `docs/STATUS.md`,
aber **nicht implementiert**. Ausnahmen:
`action: verify` (OP-183, done), `verify_alternierend` (OP-182, done),
JSON-Repair (OP-186, done), Dependency-Hybrid (OP-187, done).

### 8.3 Was heute bereits gebaut ist (IST-Abgrenzung)

Folgende Punkte aus dieser SOLL-Datei sind **bereits implementiert**:

| Punkt | IST-Stand | Commit |
|---|---|---|
| `action: verify` (Task-Typ) | gebaut | c3e308f |
| `verify_alternierend` (Stagnation) | gebaut | 4de3a65 |
| JSON-Repair im Planner | gebaut | ae2d5a2 |
| Dependency-Hybrid (Architect + Heuristik) | gebaut | e960a40 |
| Dead-Code-Erkennung im Reviewer | gebaut | 9b700e3, fdb01df |

Folgende Punkte sind **nur Doku/ADR, Code pending** (ADR accepted, kein Code):
- Alle OPs 123-132, 160 (Chat/UI/Debugger)
- Alle OPs 113-131 (Gehirn)
- OPs 188-195 (Test-Loop) — nur als OP-Header, kein Code
- OP-212 (Test-Spec-Validator) — neu 2026-11-07, ADR-0016 Nachtrag
- OP-241 (Debugger-Sandbox) — neu 2026-11-07, Punkt 4 aus Review


---

## 9. Die drei Kernprinzipien (nochmal explizit)

### 9.1 Der Mensch entscheidet

Nichts läuft automatisch durch, was die Spec verletzen könnte:
- **4 Human-Gates im Loop**: Plan, Reflection, Phase-Review, Commit
- **Repair Ladder**: 3 Stufen, Mensch wählt
- **Memory-Promotion**: `memory_promote.py --scan` schlägt vor,
  Mensch bestätigt. Kein Auto-Promote.
- **Test-Thaw**: nur über Chat-Debugger + Mensch-Entscheidung

Der Chat und der Loop schlagen vor. Der Mensch wählt.

### 9.2 Loop ist Motor, nicht Interface

- Loop läuft **headless** (OP-202 Gate-Bridge)
- Gates sind **HTTP-Endpoints**, nicht stdin
- UI zeigt Loop-Zustand aus **Event-Store** (OP-122)
- Loop-CLI (`--project`, `--aufgabe`) bleibt für Notfälle
- Standard-Workflow: UI startet Loop, Mensch sieht Timeline, entscheidet

### 9.3 Tests sind Spec

- **Architect liefert `test_spec`** (Block 6)
- **Test-Agent baut Tests** aus test_spec (nicht aus Code)
- **Qualification**: Tests MÜSSEN rot auf unverändertem Repo sein
- **Freeze**: SHA256 in `state.test_manifest`
- **Builder ist test-blind** (sieht `tests/` nicht)
- **Mutation-Gate** prüft Test-Qualität mechanisch
- **Test-Thaw** nur bei bewusster Mensch-Entscheidung

---

## 10. Glossar

| Begriff | Bedeutung |
|---|---|
| **OP-NNN** | Ein offener Auftrag in `docs/STATUS.md` |
| **Loop** | Der Orchestrator (`werkstatt/loop.py`) |
| **Task** | Eine Einheit im Loop (create/update/read/verify/test) |
| **Gate** | Menschliche Entscheidung (j/n/a) |
| **Phase** | Loop-Abschnitt (Explorer, Plan, Task, Review, Finalize) |
| **Reflection** | Loop-interne Fehlerbehandlung nach Verify-Fail |
| **test_spec** | Architect-Output: Test-Namen + Assertion-Prosa |
| **test_manifest** | `{path: sha256}` der eingefrorenen Tests |
| **Test-Thaw** | Bewusste Invalidierung des Manifests |
| **Mutation-Gate** | pytest-gremlins als Test-Quality-Check |
| **Chat-Debugger** | Modus des Chat-Agenten (OP-240) |
| **Repair Ladder** | 3-Stufen-Reparatur im UI (OP-242) |
| **Erfahrungs-Gehirn** | Zweistufige DB (Projekt + Global) |
| **Episoden** | `erfahrung`-Einträge (Fehler → Lösung) |
| **Regeln** | `regeln`-Einträge (destilliert, trust-Stufen) |
| **Promotion** | Projekt-Regel → global candidate (Sanitization) |
| **debugger_fix_verifiziert** | Event nach grünem Re-Run (OP-243) |

---

## 11. Verweise

**Architektur:**
- `docs/ARCHITECTURE.md` — IST-Zustand (was heute läuft)
- `docs/SOLL.md` — dieser Text (wohin es geht)

**Entscheidungen:**
- `docs/adr/ADR-0010` — Memory zweistufig (Projekt + Global)
- `docs/adr/ADR-0016` — Spec-First Test-Loop
- `docs/adr/ADR-0017` — Mutation-Gate
- `docs/adr/ADR-0018` — Debugger als Chat-Modus (nicht Loop-Rolle)

**Konventionen:**
- `docs/MERKPOSTEN.md` — Prozess-Lehren aus Sessions
- `docs/DOC_CONVENTIONS.md` — Golden-Standard für Doku
- `AGENTS.md` — Hinweise für Agenten-Entwicklung

**Status:**
- `docs/STATUS.md` — offene OPs
- `PROGRESS.md` — erledigte OPs

---

## 12. Was diese Datei NICHT ist

- **Keine Spezifikation im engeren Sinn.** Sie beschreibt Absicht,
  nicht Details. Details stehen in den OPs.
- **Keine Implementierung.** Nichts davon ist gebaut, ausser den
  in Abschnitt 8.3 genannten Punkten.
- **Keine Reihenfolge-Empfehlung.** Die Stufen in Abschnitt 8 sind
  logisch geordnet, aber die genaue Session-Reihenfolge hängt von
  Prioritäten ab.
- **Kein Ersatz für ADRs.** Wenn ADR und SOLL.md sich widersprechen,
  gewinnt das ADR (weil es die konkrete Entscheidung dokumentiert).

---

## 13. Wie man diese Datei liest

**Wenn du ein LLM bist, das an einer OP arbeitet:**

1. Lies den OP-Header in `docs/STATUS.md`
2. Lies die zugehörige Sektion in dieser Datei (z.B. OP-210 → §4.2)
3. Lies die relevanten ADRs
4. Lies den IST-Zustand in `docs/ARCHITECTURE.md`
5. Baue

**Wenn du ein Mensch bist, der den Status verstehen will:**

1. §2 (Zielbild) — wo wollen wir hin
2. §8 (Stufen) — was ist der nächste Schritt
3. §4-7 (Schichten) — was ist heute, was kommt
4. `PROGRESS.md` — was ist seit wann gebaut

**Wenn du ein neuer Chat bist:**

1. Diese Datei komplett lesen
2. `docs/MERKPOSTEN.md` lesen (Prozess-Regeln)
3. `docs/STATUS.md` Abschnitt "Offene Punkte" lesen
4. Dem User zuhören — er weiss, was wichtig ist.
