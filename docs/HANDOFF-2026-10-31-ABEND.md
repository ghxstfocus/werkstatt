# Werkstatt - Handoff 2026-10-31 (Abend)

## Session-Ergebnis

Erster echter Multi-File-Feature-Commit durch den Loop: `4f0ac63`
(security-ai) - Chat ist auf DeepSeek umgestellt.

Werkstatt: 871 passed, 5 skipped. ~35 Fixes in 22 Commits seit
`4d58da1` (Session-Start 22:40).

## Zielprojekt-Stand (security-ai, main)

- `4f0ac63` Chat auf DeepSeek umgestellt (5 Dateien, +273/-40)
- `2b38bab` STATUS.md Punkt 3 entfernt
- `8ea5503` docs/PLAN_CHAT_ACTIONS.md angelegt
- `53db3b0` STATUS.md Punkt 1 entfernt

Verifiziert funktional: DeepSeekClient importiert und konstruierbar,
get_deepseek_base_url() liefert api.deepseek.com, chat_cli --help
zeigt --base-url/--model/--timeout, routes_chat.py nutzt
DeepSeekClient, py_compile aller 5 Dateien OK.

## Werkstatt-Fixes (chronologisch)

### Runde 1 - Root-Cause
- Fix 1: redaction IPv6-Regex trennt Code-Kontext von Adressen
  (python::AuditError wurde zu python[IPV6]uditError - Ursache
  aller Fake-Commits 669a7de, e6222f4, 30decc6, 5297b49)

### Runde 2 - Fail-Closed-Gates
- Fix 2: Reviewer fail-closed bei update-Task ohne Diff
- Fix 3: Committer prueft task_files im Working Tree
- Fix 4: verify.json doku_diff_check-Stage
- Fix A v3.1: planner._doku_post_check reduziert Doku-Tasks,
  schuetzt legitime Code-Tasks (create oder in Aufgabe erwaehnt)

### Runde 3 - Prompt-Treue
- Fix B: REVIEWER_SYSTEM Auftrag-Treue-Check
- Fix C: builder._extrahiere_verbote isoliert Verbote-Block
- Fix E: docs_ctx fuer Doku max 5 KB (statt 100 KB)
- Fix F: Explorer ueberspringt Ziel-.md als Code-Pfad-Quelle
- Fix G: PLANNER_SYSTEM entfernt (deprecated)
- Fix J: builder._pruefe_doku_patch_breite filtert zu breite
  Loesch-Patches

### Runde 4 - Commit + Progress + Planner-Gate
- Fix K: PROGRESS.md-Eintrag VOR git add -A
- Fix L: SCOUT_SYSTEM ENTFERNEN-AUFGABEN-Regel
- Fix S: _deterministic_entfernen_precheck laeuft vor dem Scout
- Fix Y: planner_gate erlaubt .example/.template/.sample/.dist
- Fix Z: Loop-Meldung 'Plan verworfen' statt 'kein Plan'

### Runde 5 - Create-Pfad + Status
- Fix M: create-Task laeuft durch (fehlende Datei blockte LLM)
- Fix N: write_text-Fehler fail-closed (kein Traceback)
- Fix O: Human-Gate zeigt untracked via git add -N .
- Fix P: Builder create-Prompt fordert ALLE Abschnitte
- Fix Q v2: Reviewer prueft Konzept-Schlagworte
- Fix R: Deterministischer Reviewer-Fail fail-closed
- Fix V: _expand_cmd_placeholders nutzt status --porcelain -uall
- Fix W: Doppel-Schreiben in run_builder entfernt
- Fix X: .strip() auf Gesamt-Output vor splitlines() entfernt

### Runde 6 - Resume + Failure-Persistenz
- Fix AA: git reset --hard nur bei --rollback
- Fix AB: --resume laedt aus .phase.yaml.fresh-bak
- Fix AC: resume_failed() laeuft immer
- Fix AD: _task_fortschritt_block zeigt Status im Human-Gate
- Fix AE: .werkstatt/abbrueche.jsonl persistiert Task-Failures
- Fix AF: Planner + Builder lesen Failures aus PhaseState
- Fix AH: Loop-Ende schreibt PROGRESS.md korrekt
- Fix AI: applied_count++ nach Post-Verify
- Fix AJ: _hat_gleiche_bugs mit bool() (frozenset-Crash)
- Fix AK: audit() serialisiert mit default=str
- Fix AL: Reflection-OK nur bei applied_count-Anstieg
- Fix AM: pre_tool_use nutzt sys.stdlib_module_names
- Fix AN: run_pipeline_loop prueft Schreibrechte vor Task 1
- Fix AP: _pruefe_prior_failed_dependency prueft Vor-Task-Fails
- Fix AQ: Builder-Prompt listet Module im Zielverzeichnis
- Fix AR: Task-Fail -> continue statt return 1 (9 Stellen)
- Fix AS: loop_task_partial_ok im Loop-Ende
- Fix AT: _stage_ist_hart klassifiziert Verify-Stages
- Fix AU: _verify_patches_soft trennt hart/weich

## Was der Loop jetzt kann

- Doku-Aufgaben (STATUS.md bereinigen)
- Mehrdatei-Code-Aufgaben (DeepSeek: 5 Dateien in einem Lauf)
- Task-Fail ueberlebt (Fix AR) - partielle Erfolge
- Failure-Persistenz (.werkstatt/abbrueche.jsonl + PhaseState)
- Resume nach Abbruch (--resume laedt aus .fresh-bak)
- Human-Gate zeigt partielle Bilanz (Fix AD)
- Style-Fehler blockieren Commit nicht (Fix AT/AU)
- Pre-Flight-Rechte-Check (Fix AN)
- Modul-Hint im Builder-Prompt (Fix AQ)

## Was noch offen ist

1. Delete-Action fehlt. Loop kennt keine action="delete".
   Live-Beleg 4f0ac63: t5/t6 konnten client.py / ollama_client.py
   nicht loeschen.

2. Projektweiter Symbol-Hint fehlt. Fix AQ zeigt nur das
   Zielverzeichnis, nicht projektweite Klassen (LLMClientProtocol
   aus apps/security_ai/chat.py). Live-Beleg v6 t2 failte daran.

3. Scout erkennt "entferne X wenn X fehlt" nicht deterministisch.
   Fix L + Fix S greifen nur bei "entferne"+"Punkt"/"Marker".

4. Echter Chat-Test fehlt. DEEPSEEK_API_KEY in .env notwendig.

5. Volltest-Suite (11 Min) nicht gelaufen seit 4f0ac63.

## Naechste Session

### P0 - sofort
1. Volltest: `cd /opt/security-ai && time .venv/bin/python3 -m pytest -q`
2. Chat manuell testen (mit DEEPSEEK_API_KEY in .env):
   - `scripts/chat_cli.py --principal cli-admin --whoami`
   - `scripts/chat_cli.py --principal cli-admin --question "Status?"`

### P1 - Delete-Action (Fix AV)
- Neue Action "delete" in _VALID_ACTIONS (planner_gate.py)
- Builder-Prompt: {"action": "delete", "file": "path"}
- Apply-Logik: Path.unlink() bei delete
- Safety: nur in file_whitelist, nicht .git/migrations/

### P2 - Projektweiter Symbol-Index (Fix AW)
- _projekt_symbol_index() im Builder-Prompt
- Format: "## VERFUEGBARE SYMBOLE IM PROJEKT" mit max 40 Symbolen

### P3 - Naechste Zielprojekt-Aufgabe
Preflight-Verifikation (Loop-Vorschlag aus v7-Lauf),
Endpoint-Watcher, Chat als Aktions-Schnittstelle (Plan in
docs/PLAN_CHAT_ACTIONS.md).

## Repo-Stand
- Werkstatt umbau/phase-2: cb2ffb0 als HEAD, gepusht
- Zielprojekt main: 4f0ac63 als HEAD, clean tree

## Wichtige Erkenntnisse
1. Root-Ownership nach `git restore .` als root: danach
   `chown -R security-ai:security-ai .` in /opt/security-ai.
2. LLM halluziniert Modulnamen - Fix AQ hilft, ist nicht perfekt.
3. Deterministische Gates > LLM-Gates (AT/AU, AP, AR, AL).
4. Audit-Payloads sind Debugging-Gold.
5. Bei Multi-Task-Laeufen: Human-Gate zeigt partielle Bilanz.
