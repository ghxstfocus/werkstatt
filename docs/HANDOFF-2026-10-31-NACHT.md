# HANDOFF — Werkstatt-Session 2026-10-31 (Nacht) -> naechste Session

## Was erledigt ist

Fix AV (action="delete") ist live und belegt. Neun Commits, davon fuenf
in dieser Session (1c9d7e3, 457f248, ce1034e, 40f1c7f, e94bb90).

Live-Beleg 2026-10-31 11:25 RERUN 3 gegen security-ai:
- t5 harness/llm/client.py entfernt (loop_patch_deleted 11:25:20)
- t6 harness/llm/ollama_client.py entfernt (loop_patch_deleted 11:25:22)
- PhaseState 7/7 done
- Werkstatt 884 passed, 5 skipped

## Was tatsaechlich gebaut wurde

- hooks/planner_gate.py: "delete" in _VALID_ACTIONS + Docstring
- werkstatt/builder.py (3 Stellen):
  - Format-Beispiel: {"action":"delete","file":"..."}
  - Regel: GANZE DATEI LOESCHEN vs. Zeile entfernen (Abgrenzung)
  - Validator Z. ~1397: bei Task-action=update, _paction in
    {update, delete}. Ohne diese Aenderung wirft der Builder den
    LLM-Delete-Patch mit builder_patch_invalid expected=update weg.
- werkstatt/loop.py:
  - _delete_ziel_erlaubt(target_rel, task_files, project_dir):
    Whitelist (task_files None = Reflection-Modus), .git,
    data/migrations, "..", absolute Pfade, project_dir.resolve()-
    Bounds.
  - Inline-Delete-Branch in run_pipeline_loop (Z. ~2703):
    task-spezifische Whitelist aus state.tasks[task_id].task_files.
    Audit loop_patch_deleted, applied_count++.
  - Reflection-Delete-Branch in _apply_patches_with_hooks (Z. ~793):
    task_files=None (keine Task-Bindung), harte Checks bleiben.
    Audit modus="reflection".
  - Resume-Fix: PhaseState.data["tasks"] nicht leer -> plan_ok=True,
    _plan_gate + run_planner uebersprungen. Audit loop_resume mit
    quelle=phase_state vs. quelle=gate. Ohne den Fix baute der
    Planner nach jedem Resume einen NEUEN Plan, weil die PhaseState
    keine tests/akz mehr hat.
- werkstatt/audit.py: 4 Kinds im Katalog (loop_patch_deleted,
  _delete_blocked, _delete_skip_missing, _delete_failed)
- tests/test_loop_delete_action.py (10 Tests)
- tests/test_loop_resume_from_phase_state.py (3 Tests, Logik-Zweig)

## Offene Punkte (P2+, nicht heute)

### security-ai Zielprojekt (Commit e94bb90)

1. **deepseek_client.py: API-Paritaet fehlt (4 high Bugs Phase-Review)**
   - `generate_text(prompt, *, system, model, max_tokens, timeout) -> str`
     fehlt (alte OllamaClient-API). Aufrufer brechen mit AttributeError.
   - `is_available(timeout) -> bool` fehlt.
   - `LLMResponse`-Felder: neuer Code nutzt content/prompt_tokens/
     completion_tokens, alter Vertrag war text/done/raw. models.py
     pruefen, dann entweder DeepSeekClient anpassen oder models.py
     erweitern.
   - `HTTPError` wird als LLMUnavailable gemappt, alter Client auf
     LLMError. Aufrufer-Fehlerbehandlung pruefen.

2. **routes_settings.py importiert get_ollama_base_url (Z. 25)**
   - core/config.py hat die Funktion nicht mehr (t2 entfernt).
   - Dashboard-App ist nicht importierbar -> Settings-Seite crasht.
   - Fix: Zeile entfernen oder auf get_deepseek_base_url umstellen.

3. **tests/unit/test_config.py + test_dashboard_settings.py**
   - Beide importieren get_ollama_base_url -> Collection-Error.
   - 1484 Tests sammeln, 1 Datei (test_config) kippt projektweit.
   - Fix: get_ollama_base_url-Importe + Tests entfernen oder
     auf DeepSeek-Aequivalente umstellen.

### Werkstatt (offene Fixes, nicht AV-Scope)

4. **Loop-Footer `tasks_ok` zaehlt nur neu-gebaute Tasks**
   - RERUN 3 zeigte "LOOP FEHLGESCHLAGEN 2/7" obwohl PhaseState
     7/7 done. `tasks_ok` zaehlt nur Tasks, die in DIESEM Lauf
     `task_ok` lieferten. Fuer Resume-Laeufe irrefuehrend.
   - Fix: `tasks_ok` = (neu gebaut) + (PhaseState done beim Start).
     Oder Footer neu formatieren: "2 neu, 5 bereits done".

5. **Human-Gate wird bei Phase-End-Review-Reject uebersprungen**
   - Kein Bug: Fail-Closed in Z. ~3007: `if not _pe_ok ... return 1`
     vor dem Human-Gate. Korrekt, weil 4 high Bugs offen.
   - Aber: im Renderer sieht es wie ein Skip aus. Eventuell
     `loop_gate_failed`-Panel expliziter machen.

### Endgueltig geschlossen (nicht neu aufmachen)

- Fix AV (delete): live, belegt, getestet.
- Fix AW-Resume (PhaseState vs. _plan_gate): live, belegt.
- Fix AV-3 (Builder-Validator akzeptiert delete): live, belegt.

## HARD-RULES — neu aus Session 2026-10-31 (Nacht)

41. **Builder hat DREI Action-Filter.** Nicht nur den Prompt.
    - Format-Beispiel im BUILDER_SYSTEM-Prompt (~Z. 32-37)
    - Regel-Text (~Z. 57-65)
    - Validator (~Z. 1384-1398): `if _current_action2 == "update"
      and _paction != "update": builder_patch_invalid`
    Wenn ein neuer action-Wert eingefuehrt wird, muessen ALLE DREI
    Stellen angepasst werden. Live-Beleg: Fix AV hat Format+Regel
    gepatcht, Validator uebersehen -> t5/t6 liefen 2 RERUNs
    (builder_failed) bevor der Fehler gefunden war.

42. **PhaseState ist Source of Truth, nicht _plan_gate.**
    - `_plan_gate` prueft Planner-Output-Vollstaendigkeit
      (tasks+tests+akz). Nach Resume fehlen tests/akz oft.
    - Wenn `phase_state.data["tasks"]` nicht leer: plan_ok=True,
      run_planner NICHT aufrufen. Audit quelle=phase_state.
    - Live-Beleg 11:18: Resume lud 7 Tasks, _plan_gate False,
      run_planner baute neuen 1-Task-Plan auf 17 SQL-Migrationen.

43. **`file_whitelist` ist im Loop ungenutzt.** RunState wird mit
    `file_whitelist=[]` initialisiert, nie gefuellt. Fuer
    task-spezifische Autorisierung `state.tasks[task_id].task_files`
    lesen, nicht `state.file_whitelist`.

44. **Delete-Sicherheit ist mehrschichtig.** Auch wenn Whitelist
    greift: `.git/`, `data/migrations/`, `..`, absolute Pfade,
    Symlink-Ausbruch (resolve + relative_to) IMMER zusaetzlich
    pruefen. `_delete_ziel_erlaubt` in loop.py kapselt das.
    Tests: 7 Helper-Faelle + 3 Apply-Faelle in
    tests/test_loop_delete_action.py.

45. **Fail-Closed bei Phase-End-Review-Reject ist korrekt.** Kein
    Human-Gate, kein Commit, `return 1`. Auch wenn der Renderer
    das als "Skip" darstellt — Bug-Fix waere falsch.

46. **`tasks_ok` im Footer zaehlt nur Tasks des aktuellen Laufs.**
    Bei Resume-Laeufen ist "X/Y" irrefuehrend (X = neu gebaut,
    Y = gesamt). Nicht als Bug melden ohne Zaehl-Fix.

## Erste Aktion im naechsten Chat

Ausgangszustand Zielprojekt bestaetigen:

    cd /opt/security-ai
    git log --oneline -3
    git status --short
    .venv/bin/python -m pytest tests/ -q 2>&1 | tail -3

    ls -la harness/llm/client.py harness/llm/ollama_client.py 2>&1
    grep -rn "get_ollama_base_url" --include="*.py" . | grep -v .venv

Erwartet: HEAD e94bb90, Tree clean. Collection-Error in
tests/unit/test_config.py (get_ollama_base_url fehlt). Leichen
client.py/ollama_client.py NICHT mehr vorhanden.

## Reihenfolge naechste Session

1. routes_settings.py + tests/unit/test_config.py +
   tests/unit/test_dashboard_settings.py: get_ollama_base_url-
   Referenzen entfernen (oder auf get_deepseek_base_url umstellen).
   -> pytest gruen, Dashboard wieder importierbar.
2. deepseek_client.py: generate_text + is_available + LLMResponse-
   Vertrag pruefen (models.py lesen, dann entscheiden).
3. Loop-Footer `tasks_ok`: Zaehlung korrigieren (P2).
4. Neue Aufgabe planen (naechster Schritt der DeepSeek-Umstellung
   oder anderes Feature).

## Referenzen

- Vorgaenger-Handoff: /opt/werkstatt/docs/HANDOFF-2026-10-31-ABEND.md
- Fix-AV-Commits: 1c9d7e3, 457f248, ce1034e, 40f1c7f
- Zielprojekt-Commit: e94bb90
- Audit-Log: /opt/werkstatt/audit-logs/agent-pipeline-2026-10-31.jsonl
- RERUN-Logs: /tmp/rerun_delete{,2,3}.log

## Nachtrag 2026-10-31 (nach AV): DeepSeek-Reste

Zielprojekt-Commits: 10b1635 (get_ollama_base_url-Reste +
generate_text-Bug), 1faa184 (routes_chat 500->502 + Chat-Tests).

Geschlossen:
- apps/dashboard/routes_settings.py + templates/settings.html:
  ollama_base_url -> deepseek_base_url
- harness/llm/deepseek_client.py: generate_text reichte model=None/
  max_tokens=None an LLMRequest durch -> ValueError. Fix: nur
  nicht-None uebergeben.
- tests/unit/test_llm_client.py (OllamaClient, 17 Tests) ersetzt
  durch tests/unit/test_deepseek_client.py (25 Tests).
- apps/dashboard/routes_chat.py: _build_chat_service() war
  AUSSERHALB des try-Blocks -> 500 statt 502 bei fehlendem Key.
  Fix + Spec-Test test_chat_api_ohne_key_liefert_502.
- tests/unit/test_dashboard_chat.py: Autouse-Fixture DEEPSEEK_API_KEY.
- tests/unit/test_chat.py: 4 Tests auf deepseek-reasoner umgestellt
  (qwen2.5:7b war hart kodiert).

Befund zu Phase-Review-Bugs t1 aus RERUN 3:
- Bug 1 (LLMResponse-Felder content/prompt_tokens/completion_tokens):
  HALLUZINATION. deepseek_client.py nutzt text=, korrekt.
- Bug 2 (generate_text fehlt): HALLUZINATION. Existiert, aber war
  intern kaputt (None-Durchreichung) — zufaellig gefunden.
- Bug 3 (is_available fehlt): HALLUZINATION. Existiert.

Weiter offen (P2):
- _MODEL_TIMEOUTS in apps/security_ai/chat.py kennt noch
  llama3.2:3b/qwen2.5:7b. Fallback 60 s greift, aber Kandidat
  fuer eigene Session.
- Loop-Footer tasks_ok zaehlt nur Tasks des aktuellen Laufs
  (siehe HARD-RULE 46).

## Fix AX (2026-10-31): deterministischer Reviewer-Bug-Verifier

Commit: 6dc67b0 (werkstatt, umbau/phase-2)

Problem: REVIEWER_SYSTEM enthaelt vier Prompt-Checks (SEMANTIK,
KONSTANTEN, SYMBOL, DATEI), aber keine Python-Funktion prueft die
LLM-Behauptungen gegen den Code. Drei Halluzinationen aus RERUN 3
(generate_text fehle, is_available fehle, LLMResponse-Felder falsch)
liefen ungeprueft in _phase_end_reflection, die einen Reparatur-
Versuch auf einen nicht-existenten Mangel startete.

Fix: _verifiziere_reviewer_bugs(bugs, project_dir, project_name) in
reviewer.py Z. 264. Aufruf in run_phase_end_review Z. 500 zwischen
LLM-JSON-Parsing und high/medium-Zaehlung -- _pe_ok basiert damit
auf verifizierten Bugs, nicht nur die Reflection.

Heuristiken (konservativ):
- "X(...) fehlt/nicht vorhanden/existiert nicht" -> ast.parse(file),
  Symbol als FunctionDef/AsyncFunctionDef/ClassDef/AnnAssign gesucht.
- "Datei <path> fehlt/existiert nicht" -> Path(project_dir/path).exists().
- Sonst: Bug bleibt.

Audit: reviewer_bug_widerlegt mit grund=symbol_existiert oder
datei_existiert. Katalog in audit.py erweitert.

Bewusste Grenze: semantische Behauptungen (HTTPError-Mapping,
API-Paritaets-Listen, Feld-Semantik) sind nicht per AST pruefbar
und werden durchgelassen. Diese Grenze ist der Preis dafuer, dass
der Filter keinen echten Bug unterdrueckt.

Tests: tests/test_reviewer_bug_verifier.py, 8 Faelle.
Werkstatt: 892 passed, 5 skipped.

## HARD-RULE 47

47. Phase-Review-Behauptungen gegen den Code pruefen, bevor sie
    an die Reflection gehen. Der Verifier (_verifiziere_reviewer_bugs)
    faengt Symbol- und Datei-Halluzinationen. Bei neuen Bug-
    Kategorien (Feld-Semantik, Timeout-Mapping) pruefen, ob eine
    Heuristik erganzt werden muss -- sonst bleibt die Kategorie
    ungefiltert (siehe 6dc67b0).
