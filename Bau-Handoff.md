# Bau-Handoff — Session 2026-10-28 (Ende)

**Vorgänger:** Session 2026-10-28 (Start-Stand) → diese Datei ist neuer Stand.
**Session-Ergebnis:** K17 + K19b abgeschlossen, Suite 1562 passed, origin == HEAD.

---

## WORKFLOW (verbindlich, unverändert)

### Hardrule 1 — Messen, nicht raten
- Erst **lesen** (grep, sed, git log, journalctl), dann **vermuten**.
- Jeder Fix startet mit einem **Messblock**.
- Kein Fix basierend auf „ich glaube, es liegt an X".

### Hardrule 2 — Zusammenhängende Shell-Blöcke, keine Häppchen
- **Ein Messblock** = alle grep/sed/git-Befehle für eine Diagnose in **einem** Block.
- **Ein Patchblock** = Diff anwenden + Test + Suite in **einem** Block.
- Keine „mach erst A, dann B"-Zerstückelung.

### Hardrule 3 — Ein Block, warten auf Paste
- Bau-Chat gibt **einen** Block, wartet auf Ausgabe, **dann** nächster Block.
- Kein „hier sind 3 Blöcke, mach alle".
- Bei Fehler im Block: Ausgabe zurückschicken, **nicht** selbst reparieren.

### Hardrule 4 — Kurz halten
- Keine langen Erklärungen.
- Stichpunkte, keine Prosa.
- Ausgabe des Bau-Chats: max. ~30 Zeilen zwischen Blöcken.

### Zusatzregeln (kumuliert)
- **Kein `set -e`** in Blöcken mit pytest → `set -uo pipefail` + `RC_*`-Variablen.
- **Ruff nur auf geänderte Dateien** — Altlasten ignorieren.
- **Backup vor `cat >`** — auch für `.md`-Dateien.
- **`systemctl stop <timer>`** killt Timer dauerhaft — nie auf Timer, nur auf Service.
- **`python3`, nicht `python`** — `python` schlägt still fehl, Patch wird nicht angewandt.
- **Nach jedem Patch Marker-grep** — Verify, dass der Patch wirklich drin ist.
- **`.env`-Backups nie im Projekt-Root** — nach `/root/backups/`.

---

## STAND 2026-10-28 (Session-Ende)

### Werkstatt (`/opt/werkstatt`)
- **Branch:** `umbau/phase-2` (== origin)
- **HEAD:** `e9d4445`
- **Suite:** **1562 passed** (Start: 1550, +12 neu)
- **Ruff `planner.py`:** 4 = Baseline (kein neuer)
- **Ruff gesamt:** 15 (Baseline 15, unverändert — die „16" im Start-Handoff zählte den „Found"-Header mit)
- **Neue Commits diese Session:**
  - `1075ce2` — K17 Migrationsstand deterministisch
  - `e5b5243` — K19b Block-Größe 2500 konsistent
  - `e9d4445` — K19b-Integration (2 Regression-Tests)

### Zielprojekt (`/opt/security-ai`)
- **HEAD:** `8fda684` (unverändert, 13 unpushed)
- **`.env`-Backups** aus Repo-Root nach `/root/backups/security-ai/` verschoben (4 Stück)
- **`.env`** sauber (`builder:security-ai` mode 640, 1653 B)
- **Untracked:** `core/alerts/` — Owner `root:root`, **M-XXX-Bug**. Nicht angefasst, Messung ausstehend.
- **Services:** alle active
- **PhaseState** (`security-ai.phase.yaml`): korrupt — Task `t1`-Description dreifach wiederholt (AlertFilter × 2, AlertFilterError ohne Körper). **Direkter Vorher-Beleg für K19b.** Frischer RERUN würde das neu bauen.

---

## ERLEDIGT diese Session

### K17 — Architect-Migrationsnummern ✅
- **Fix:**
  - `ARCHITECT_SYSTEM` um Block `MIGRATIONS-NUMMERN` erweitert (hoechste Nr. +1, Kollision = Review-Fail, nie belegte Nummer).
  - Neuer Helper `_migrations_stand(pd)` in `planner.py`: liest `data/migrations/`, hoechste Nummer + Empfehlung nächste.
  - `user_content` in `_run_phase_and_plan`: `<migrationsstand>`-Block eingefügt (nur wenn Dateien vorhanden).
- **Test:** `tests/test_k17_migrations_nummern.py` (6 Tests).
- **Erkenntnis:** security-ai hat `0017_guardrail_permissions.sql` **und** `0018_guardrail_permissions.sql` — beide echt, kein Duplikat. Der 0018-Kommentar dokumentiert, dass der Mensch am 16.10. die Nummernkollision manuell korrigiert hat — **exakt der K17-Bug real eingetreten**.

### K19b — Blockgröße 2500 konsistent ✅
- **Root Cause:** **Drei 800-Zeichen-Hard-Cuts** unterliefen den K15c-Fix (`_extrahiere_prosa_abschnitt` war 2500, aber die Split-/Fallback-Pfade schnitten bei 800):
  - `_llm_split_einzel_task` (Sub-Split, rekursiv)
  - `_zerlege_in_sub_tasks` Fallback (wenn `architect_start/ende` nicht gefunden)
  - `_st_gross`-Schwelle (Cascade-Splits)
- **Beweis:** `PhaseState t1` (26.10.) — Description dreifach wiederholt. Genau der 800-Cut-Effekt bei rerun84 Punkt 9/12 („leerer Filter NICHT abkürzen").
- **Fix:** alle drei auf 2500.
- **Test:**
  - `tests/test_k19b_split_blockgroesse.py` (4 Tests, Quelltext-Assertions)
  - `tests/test_k19b_integration.py` (2 Tests, `_zerlege_in_sub_tasks` mit gemocktem `ask_llm` + 15-Punkte-Prosa)
- **K15c-Regression:** `tests/test_k15a/b/c`, `test_k15_split_prompt` — alle grün.

---

## OFFEN (Priorität)

### M-XXX — Owner-Trennung Werkstatt vs. security-ai (P1)
- **Bug:** RERUN legt Dateien als `root`/`builder` in `/opt/security-ai`. Audit-Owner-Check bricht Dashboard-Start.
- **Beleg:** `core/alerts/` (26.10. 17:47) = `root:root`.
- **Fix-Optionen:**
  - (a) Post-Run-Hook: `chown -R security-ai:security-ai audit-logs/ data/` + `chmod 640`
  - (b) Loop auf `security-ai`-User umstellen (`User=security-ai` in `.service`)
- **Eintragen in:** `docs/OFFENE-BLOECKE.md`.
- **Wichtig vor nächstem RERUN.**

### Live-RERUN-Verifikation K17+K19b (P2)
- **Nicht diese Session gemacht** — bewusst, um M-XXX nicht zu triggern.
- **Erst nach M-XXX-Fix.**
- **Messung:** `.phase.yaml`-Description `t1` sollte **nicht mehr dreifach** auftreten; Task-Beschreibungen > 800 Zeichen sollten vollständig sein.

### K14 — `run_pipeline_loop` zerlegen (P3, groß)
- Datei: `werkstatt/loop.py`, Funktion `run_pipeline_loop` (601 Zeilen).
- Ziel: 7 `_phase_*`-Funktionen.
- Strategie: ein Block pro Commit, pytest nach jedem.
- Kein Test im Handoff — Suite (1562) ist Schutz.

### K18 — `pipeline.py` zerlegen (P3, groß)
- 11.118 Zeilen, 25 Test-Imports.
- Abgedeckt durch M-345/M-346.

### K19a — Builder-Prompt-Regel (P4, klein)
- „Gehe JEDEN nummerierten Punkt im Architect-Text durch." — **nicht** umgesetzt (K19b deckt Root Cause, K19a wäre weich).
- Nur sinnvoll wenn K19b allein nicht reicht.

---

## LESSONS LEARNED (Session 2026-10-28)

### Handoff-Zahlen können veralten
- Start-Handoff sagte „Ruff 11 Altlasten". Real: **15**. Kein neuer durch K-Serie. **Vor Fix immer nachmessen.**

### `python` vs. `python3`
- Block mit `python - <<'PY'` schlägt **still** fehl (kein `python`-Binary). Patch wird nicht angewandt, `set -uo pipefail` fängt es nicht.
- **Regel:** immer `python3`. Nach Patch: `grep` auf Marker als Verify.

### `AskReply` existiert nicht
- Es heißt `LLMReply` (aus `werkstatt.agent`).
- `_with_spinner(label, fn)` → `fn()` aufrufen. Für Mock: `side_effect = lambda label, fn: fn()`.

### Ruff-Header zählt als „Fehler"
- `ruff check --output-format=concise | awk -F: '{print $1}'` zählt `"Found N errors"` als eigene Zeile in der File-Spalte.
- **Regel:** für echte Zählung `grep -cE '^\S+:[0-9]+:[0-9]+:'` oder `ruff check --quiet | wc -l`.

### `.env`-Backup im Repo-Root
- Nach `.env`-Unfall lagen 4 Backups als untracked Files in `/opt/security-ai`.
- **Regel:** Backups nach `/root/backups/security-ai/` (außerhalb Repo).

### `_merge_mini_tasks` (K15a) kann Text duplizieren
- Beleg: `PhaseState t1` dreifach. K19b adressiert 800-Cut, aber nicht explizit Merge-Duplikation.
- **Noch nicht gefixt** — potenzielle nächste Baustelle. Live-RERUN wird zeigen, ob K19b allein reicht.

---

## NÄCHSTE SESSION — START

### Vorbereitung
1. `cd /opt/werkstatt && git status --short --branch` — sauber?
2. `git log --oneline -3` — HEAD `e9d4445`?
3. `pytest -q` — **1562** erwartet.
4. `systemctl is-active security-ai-dashboard.service security-ai-event-reader.timer security-ai-fritzbox-watcher.timer` — alle active?

### Erste Aktion
- **M-XXX angehen** (Owner-Fix), weil:
  - verhindert nächsten RERUN-Schaden
  - Voraussetzung für Live-RERUN K17/K19b
- Messung: `stat -c '%U:%G %a %n' /opt/security-ai/{audit-logs,data,core}/` — Soll vs. Ist.
- Fix: Post-Run-Hook in `werkstatt/loop.py` (nach Phase-Erfolg).

### Danach
- **Live-RERUN** mit K17+K19b live, danach `.phase.yaml`-Description prüfen (nicht mehr dreifach).
- Wenn grün: **K14** starten (loop.py zerlegen, groß).

---

## WAS DER BAU-CHAT NICHT MACHT

- Keine neuen Features.
- Kein Rollback auf `efe4ffc` (nur bei reproduzierbarem Suite-Bruch).
- Kein Fix ohne Messung.
- Keine M-XXX-Blöcke aus alter Liste (nur P0/P1).
- Kein `cat > .env` (nur `>>` oder nano).
- Kein `systemctl stop <timer>` (nur Service).
- Kein `python - <<PY` (immer `python3`).
- Kein `cat > Bau-Handoff.md` ohne Backup davor.

---

## KONTAKT / KONTEXT

- **User:** ghxstfocus (ghxst.focus@gmail.com)
- **Repo:** github.com:ghxstfocus/werkstatt.git
- **Zielprojekt-Repo:** `/opt/security-ai` (eigenes Git, `main` + 13 unpushed).
- **Sprache:** deutsch, technisch, direkt.

---

*Ende Bau-Handoff 2026-10-28 (Ende).*
