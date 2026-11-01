# WERKSTATT — ÜBERGABE 2026-11-01 (Abend)

Du übernimmst eine Werkstatt-Session. Diese Session hat mehrere
strukturelle Werkstatt-Fixes gemacht UND den ersten echten
security-ai-Loop-Task mit Doku-Anker durchgezogen.

**Lies dieses Dokument ZUERST. Bei Konflikt zwischen Text und Code:
MESSEN, nicht raten.**

---

## 1. STAND (2026-11-01 ~13:00)

| Repo | HEAD | Branch | Tests | Offene OPs |
|---|---|---|---|---|
| Werkstatt | `d19ecdb` | `umbau/phase-2` | 1017 passed, 5 skipped | 5 |
| security-ai | `84ac40b` | `main` | ~1523 passed (11 Min, nicht verifiziert) | 4 |

Beide Trees clean, beide gepusht.

---

## 2. WAS DIESE SESSION (2026-11-01 Abend) GESCHAH

### Werkstatt (5 Commits, `9bdcfc2..d19ecdb`)

| Commit | Inhalt |
|---|---|
| `9bdcfc2` | OP-048-Spec in 3 Ebenen + OP-055/056/057/058 angelegt (war ungestaged aus letzter Session) |
| `73f3156` | **Doku-Selbstpflege-Code + ADR-Mini-Phase.** committer.py + 8 Helper (OP-048 Ebene 1, OP-055 HEAD-Kennzahl, OP-056 CHANGELOG, OP-057 Architecture-Drift), gates.py + ADR-Mini-Phase (OP-058). 27 neue Tests. Env-Gates: `WERKSTATT_DOKU_NACHZUG=1`, `WERKSTATT_ADR_MINI=1`. |
| `8503976` | OP-048/055/056/057/058 nach PROGRESS.md (5 OPs erledigt) |
| `d19ecdb` | **Architect-Prompt: bedingte Test-Scope-Regel.** Bisher: "TESTS SIND OUT-OF-SCOPE" pauschal. Neu: Default out-of-scope, **außer** Auftrag/OP nennt Test-Namen (Pattern `test_*`) → dann MUSS `## tests/...` ein eigener Block sein. |

### security-ai (4 Commits, `2c733fc..84ac40b`)

| Commit | Inhalt |
|---|---|
| `262cb5a` | **Migration 0019** — device_history Spalten feld/alt/neu (Vorbedingung OP-002b2). Manuell gebaut, weil der Architect sie im Loop out-of-scope geplant hatte. |
| `ef413bd` | **OP-002b2 erledigt** — `_insert_device_history` mit Duplikatschutz (NULL-sicher via `IS ?`) + 3 Tests in `test_inventory_op002b2.py`. Loop baute Methode, Test scheiterte an `reflection_ohne_apply`. Methode aus t1-Patch übernommen, Test manuell. |
| `4810d09` | OP-002b2 nach PROGRESS.md + Delete-Zone |
| `84ac40b` | Delete-Zone repariert (2 vorbestehende Bugs: OP-005/OP-054-Zeilen zusammengeklebt + nackte OP-005-Zeile) |

---

## 3. DREI NEUE FIXES IM DETAIL

### OP-048 Ebene 1 (`committer.py`)

`_committe_zielprojekt` ruft nach bestehendem PROGRESS-Append, **vor** `git add -A`:
- `_doku_nachzug_aktiv()` — Env-Check
- `_op_nnn_aus_aufgabe(aufgabe)` — Regex `\bOP-\d{3}[a-z]?\d*\b`
- `_status_md_op_entfernen(status_md, op)` — löscht `### OP-NNN:`-Block
- `_progress_op_done(pd, op, subject, pn)` — PROGRESS-Eintrag
- `_delete_zone_op_append(status_md, op, subject)` — Tabellenzeile (ohne SHA)
- `_update_kennzahlen(status_md, pd)` — HEAD-Zeile (nur HEAD; Tests/ruff/mypy = Follow-up, blockiert OP-039)
- `_update_changelog(pd, entry)` — Zeile unter `## [Unreleased]`
- `_architecture_drift_check(pd)` — Audit-Event bei .py neu/gelöscht ohne ARCHITECTURE.md

Skip-Bedingungen → Audit `doku_nachzug_skip` mit Grund.

### OP-058 ADR-Mini-Phase (`gates.py`)

**Spec-Abweichung:** Spec sagt "in pipeline_phases.py, vor Human-Gate". Realität: `_committe_zielprojekt` wird **in** `_human_gate` aufgerufen (gates.py:315). Deshalb lebt `_adr_mini_phase` in `gates.py`, **nach** `input()=="j"`, **vor** `_committe_zielprojekt`. Nur so landet die ADR im selben Commit.

Deterministisches Template statt LLM-Call (kein LLM-Client in Werkstatt gefunden). `WERKSTATT_ADR_MINI=1`. Template enthält `<!-- Vom Menschen zu fuellen -->`-Marker.

### Architect-Prompt (`architect.py`)

`ARCHITECT_SYSTEM` wird immer mitgeschickt (auch bei `WERKSTATT_ARCHITECT_PROMPT=v2`). Alter Block "TESTS SIND OUT-OF-SCOPE" ersetzt durch bedingte Regel. Kein Test hängt am alten String (gemessen via grep).

---

## 4. WAS DER ERSTE ECHTE LOOP-LAUF MIT DOKU-ANKER ZEIGTE

**Aufgabe:** "Lies docs/STATUS.md, nimm den ersten offenen OP, bearbeite ihn."

**Erkenntnis 1 — Doku-Anker funktioniert.** Explorer/Scout/Architect ziehen den ersten OP (`OP-003`) autonom aus STATUS.md. Kein manuelles OP-Nennen nötig.

**Erkenntnis 2 — OP-003 ist nicht atomar.** Architect plante 4 Tasks für `pyproject.toml` + `docs/STATUS.md`. Muster wie OP-002b im Handoff §11. Empfehlung: OP-003 splitten (Kategorie 3, "eigener Block mit Bestandsaufnahme pro Regel-Gruppe" — nicht Loop-geeignet).

**Erkenntnis 3 — Doku-Anker ≠ Datei-Namen.** Architect erfand `tests/unit/test_inventory_repository.py`, weil OP-Text den Test-Namen nannte, aber nicht die Datei. Reale Datei: `test_inventory_op002a.py` (wurde `test_inventory_op002b2.py`). **Loop-Aufgaben sollten Datei-Pfade explizit nennen.**

**Erkenntnis 4 — OPs mit Vorbedingungen.** OP-002b2 forderte SELECT auf fehlende Spalten. Architect erkannte das, plante eigenmächtig Migration (out-of-scope, technisch richtig). Migration 0019 manuell vorgebaut, dann Loop erfolgreich.

**Erkenntnis 5 — `reflection_ohne_apply`.** Test-Builder scheiterte an t2 mit diesem internen Loop-Fehler. **Nicht behoben.** Werkstatt-Bug, nicht code-spezifisch.

---

## 5. OFFENE OPs

**security-ai (4):** OP-002b3 (upsert_seen ruft _insert_device_history nach Diff, ~30 Min), OP-003 (ruff-Regelschaerfung, **nicht Loop-tauglich, splitten**), OP-004 (A900 mypy), OP-006 (Planner-Split out-of-scope).

**Werkstatt (5):** OP-035 (Doku-Task-Datum), OP-039 (Suite 11 Min), OP-041 (quality_gate rot), OP-045 (WORKFLOW.md entstauben), OP-046 (PLANNER-KONZEPT+ROLLEN-AUDIT+MERKPOSTEN entstauben).

---

## 6. NAECHSTE SCHRITTE

**P1** Loop-Retry OP-002b3. Wenn reflection_ohne_apply wieder auftritt -> Werkstatt-Bug isolieren + fixen.

**P2** reflection_ohne_apply untersuchen. Logs: .werkstatt/abbrueche.jsonl, /tmp/werkstatt-prompts/, /tmp/loop-*.log.

**P3** OP-003 in 3-4 Sub-OPs splitten (je eine ruff-Regelgruppe).

**P4** Doku-Stale sammeln (OP-035, OP-039, OP-041, OP-045, OP-046).

---

## 7. LOOP-AUFRUF

Kanonischer Aufruf: siehe handoff-2026-11-01.md. Zusaetzliche Env-Vars heute: **WERKSTATT_DOKU_NACHZUG=1** (Doku-Selbstpflege aktiv), **WERKSTATT_ADR_MINI=1** (ADR-Mini-Phase aktiv).

**Wichtig:** einfache Quotes im Aufgabentext kollidieren mit dem su -c Wrapper. Keine einfachen Quotes in --aufgabe.

Nach dem Lauf immer: git status --short in security-ai; grep -E "^(status|phase_id):" /opt/security-ai/.werkstatt/security-ai.phase.yaml; Audit-Log letzte 30 Zeilen.

---

## 8. WAS HEUTE SCHIEFGING (ehrlich)

1. **Erster Loop-Aufruf mit einfachen Quotes** scheiterte am su -c Wrapper (Dateiende beim Suchen nach Quote). Fix: keine einfachen Quotes in Aufgabentext.

2. **Architect hat Datei erfunden.** tests/unit/test_inventory_repository.py existierte nicht. FileNotFoundError erkannt, Test manuell in test_inventory_op002b2.py geschrieben.

3. **Migration fehlte im OP-Text.** OP-002b2 forderte Spalten, die nicht existierten. Migration 0019 manuell vorgebaut.

4. **Zwei versteckte Doku-Bugs in security-ai/STATUS.md** (Delete-Zone): OP-005/OP-054-Zeilen zusammengeklebt + nackte OP-005-Zeile. Vorbestehend, jetzt behoben.

5. **reflection_ohne_apply nicht behoben.** Loop-Bug, dokumentiert, vertagt.

6. **Paste-Escaping bei langen Bash-Heredocs.** >30 Zeilen = fragil. Regel: >30 Zeilen = Python-Heredoc mit write_text, ohne Backslash-Escapes.

---

## 9. WAS DU NICHT TUN SOLLTEST

- git reset --hard als root macht Dateien root:root (HARD-RULE 22: chown danach). Heute nicht passiert, weil t1-Patch brauchbar war.
- n am Human-Gate ohne git diff zu lesen - naechstes Mal unbekannt.
- OP-Text ohne Datei-Pfade (Architect raet).
- OP-Text ohne Vorbedingungen (Migrationen, externe APIs).
- Einfache Quotes in --aufgabe (su -c Wrapper frisst sie).
- Bash-Heredoc >30 Zeilen (Python-Heredoc nutzen).

---

## 10. STARTBEFEHLE FUER NAECHSTE SESSION

    cd /opt/werkstatt && git status --short && git log --oneline -5
    cd /opt/security-ai && git status --short && git log --oneline -5
    cat /opt/werkstatt/docs/STATUS.md | head -60
    cat /opt/security-ai/docs/STATUS.md | head -60

Dann P1 (OP-002b3 via Loop) oder P2 (reflection_ohne_apply).

---

## 11. DAS PRINZIP

Der Loop liest die Doku autonom. Er **raet** Datei-Namen, wenn sie nicht explizit im OP stehen. Er **plant out-of-scope**, wenn Vorbedingungen fehlen. Er **scheitert leise** an internen Bugs (reflection_ohne_apply).

Deterministische Doku-Selbstpflege (OP-048, OP-055, OP-056) ist gebaut, aber **noch nicht im Live-Loop getestet** - weil der einzige getestete Lauf mit rc=1 endete. Naechster Test: Loop-Lauf mit WERKSTATT_DOKU_NACHZUG=1, der mit rc=0 endet, sollte OP-002b3 automatisch aus STATUS.md entfernen.

Wenn das klappt, ist der Loop erstmals **selbst-dokumentierend**.

Viel Erfolg. Bei Zweifel: MESSEN, nicht raten.
