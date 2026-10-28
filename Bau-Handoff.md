# Bau-Handoff — Session 2026-10-28 (Ende)

**Session-Ergebnis:** 25 K-Fixes gepusht (K17-K47). Suite 1550 -> 1616.
Loop baut+prueft mit 70-80% Erfolgsquote.

---

## STAND

**Werkstatt** (`/opt/werkstatt`):
- Branch `umbau/phase-2` (== origin)
- HEAD: `83f371f` (K45+K46+K47)
- Suite: **1616 passed**
- Ruff Baseline: loop.py 7, planner.py 4, builder.py 2, reviewer.py 0

**Zielprojekt** (`/opt/security-ai`):
- Services active, `.env` vollstaendig
- `core/alerts/` untracked, security-ai-owner (M-XXX-Altlast)
- `.phase.yaml` oft leer nach Rollback

---

## WAS FUNKTIONIERT (verifiziert)

- **Explorer:** 20-22 Files, Migrationsstand prominent (K31/K32)
- **Planner:** `<migrationsstand pflicht>`, keine erfundenen Nummern (K17/K17c)
- **Planner-Split:** Merge-Limit 1800, max 2/Datei (K41)
- **planner_gate:** 7 Checks (K17c MIGRATIONS_KOLLISION, K27 DATEINAME_AEHNLICH)
- **Builder:** baut Tasks, Reflection mit old_string-Praezision (K46), History (K47)
- **Reviewer:** fail-closed (K23a), Historie (K40), Severity-Def (K42)
- **Phase-End-Review:** vor Human-Gate (K23c)
- **Reflection:** iteriert Verify+Reviewer (K39), History (K47)
- **ADaPT:** Schwelle 2500 (K44a)

**Live-Beleg (18:33):** 3/10 Tasks done mit Reviewer-Approved.

---

## OFFEN (Prioritaet)

### K48 — old_string-Patch-Ansatz fragil (P1, GROSS)
- Symptom: `loop_patch_old_string_not_found` trotz K46-Prompt
- Fix-Optionen: A) Aider-Style Kontext-Zeilen, B) ganze Datei neu schreiben, C) Fuzzy-Match
- Goldstandard: B (ganze Datei) + Diff-Check nach Apply

### `_reflection_loop` returned zu frueh False (P1)
- Symptom: Nach Runde 1 (patch_nicht_angewendet) returned False statt 5 Runden
- Diagnose: `_had_error_context`-Logik in `_reflection_loop`

### M-XXX Owner-Permissions (P2)
- Setup-Skript `setup_project.sh` (`.werkstatt` 2775, `.ruff_cache` chown, git safe.directory)

### `core/alerts/` (P3)
- `git rm -r core/alerts/` manuell im Zielprojekt

### `_k13_rc` praezisieren (P3)
- `tasks_ok == tasks_total` pruefen, nicht `> 0`

### Doku-Ueberarbeitung (P4)
- AGENTS.md (Loop-Phasen, fail-closed, Gates)
- docs/ARCHITEKTUR.md (Layer, PhaseState, Reflection)
- docs/RUNBOOK.md (RERUN, Debug, safe.directory, --fresh)

### K14 / K18 (P5, gross)
- `run_pipeline_loop` 601 Zeilen -> 7 Phasen-Funktionen
- `pipeline.py` 11k Zeilen zerlegen

---

## NAECHSTE SESSION — START

**Vorbereitung:**
1. `git status --short --branch` sauber?
2. `git log --oneline -1` == `83f371f`?
3. `pytest -q` — 1616 erwartet.
4. `systemctl is-active` — alle active?

**Erste Aktion: K48** — old_string-Patch-Ansatz ueberdenken.
- Messung: `grep -c "old_string" werkstatt/apply.py werkstatt/builder.py`
- Entscheidung Aider-Style vs. ganze Datei.

**Danach:** `_reflection_loop`-Bug diagnostizieren. Danach Doku.

---

## WICHTIGE PFADE

- Code: `/opt/werkstatt/werkstatt/*.py`
- Tests: `/opt/werkstatt/tests/`
- Hooks: `/opt/werkstatt/hooks/*.py`
- PhaseState: `/opt/security-ai/.werkstatt/security-ai.phase.yaml`
- Audit: `/opt/werkstatt/audit-logs/agent-pipeline-YYYY-MM-DD.jsonl`
- Zielprojekt: `/opt/security-ai/`
- Logs: `/tmp/rerun_*.log`
- Backups: `/root/backups/{security-ai,werkstatt}/`

---

## BEWAEHRTE RERUN-INVOCATION

Am Prompt `j` waehlen (Plan-Gate + Human-Gate). Kein grep/tee in der Pipe.
`--fresh` loescht `.phase.yaml` vor Start (K24).

```bash
set -uo pipefail
cd /opt/security-ai || exit 1
for f in core/services/sofortmassnahme_service.py; do
  [ -f "$f" ] && mv -v "$f" "/root/backups/security-ai/$(basename $f).alt-$(date +%s)"
done

cd /opt/werkstatt || exit 1
LOG="/tmp/rerun_$(date +%Y%m%d-%H%M%S).log"
script -q -e -c "su -s /bin/bash security-ai -c 'cd /opt/werkstatt && PYTHONUNBUFFERED=1 WERKSTATT_RENDER=live WERKSTATT_ARCHITECT_MODEL=deepseek-reasoner exec timeout 2400 python3 -m werkstatt.loop --fresh --project security-ai --aufgabe \"Architect: Lies docs/STATUS.md. Plane den naechsten offenen Code-Punkt.\"'" "$LOG"
```

---

## REGELN

- Messen, nicht raten.
- Ein Block, warten auf Paste.
- Backup vor `cat >`.
- `python3`, nicht `python`.
- Kein `systemctl stop <timer>`.
- Kein `grep`/`tee` um interaktive Prozesse (TTY-Problem).
- `git status --short` vor Commit.
- Heredoc in Bash: nur fuer <30 Zeilen. Sonst Python-Heredoc oder stuetzweise.

---

*Ende Bau-Handoff 2026-10-28 (Session-Ende).*
