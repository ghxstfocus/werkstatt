# ADR-0013: Layer-Architektur + Submodul-Split-Reihenfolge

- **Datum:** 2026-11-04
- **Status:** accepted
- **Kontext:** ADR-0012 identifiziert vier Strukturmuster als Ursache
  fuer Multi-File-Failures. Die Werkstatt ist aktuell funktionsfaehig,
  aber jede Aenderung an einer Stelle strahlt auf 2-3 andere aus
  (Re-Exports, Gott-Objekte, implizite Vertraege, Layer-Verletzungen).

**Fragestellung:** Wie sieht die Zielstruktur aus, und in welcher
Reihenfolge wird sie erreicht?

**Zielstruktur (Layer):**

    cli/       kennt: phases
    phases/    kennt: roles, domain, infra
    roles/     kennt: domain, infra
    domain/    kennt: nichts
    infra/     kennt: nichts
    web/       kennt: infra, phases (nicht roles!)

Regeln:
- Rollen kennen keine anderen Rollen. Nur domain + infra.
- phases/ kennt Rollen, aber keine Rolle kennt phases/.
- web/ liest infra (Event-Store, Audit), triggert phases (Loop-Start),
  aber importiert keine Rollen direkt.
- domain/ und infra/ importieren keine Werkstatt-Module ausser paths.

**Aktuell (Ist):**

    cli(loop.py) -> phases(pipeline_phases.py) -> rollen
                                              -> render(loop_renderer.py)
                                              -> audit -> paths
                                              -> web(app.py) -> web/*

Mit Zirkularitaeten via Re-Export-Proxies. `web/` und `cli/` sind
nicht getrennt, `loop_renderer` ist Mix aus infra (Tee, Emit) und
domain (Plan-Rendering).

**Zielstruktur (Soll):**

    cli/
        __init__.py     (leer oder Re-Exports fuer Tests)
        main.py         (argparse, main)
    pipeline.py         (run_pipeline_loop — phasenunabhaengige Steuerung)
    phases/
        __init__.py     (Komposition, ~50 Zeilen)
        explorer.py     (_phase_explorer_and_setup)
        plan.py         (_phase_plan_and_preflight)
        tasks.py        (_phase_tasks_loop)
        finalize.py     (_phase_finalize)
    roles/
        builder/
            __init__.py (_build_patches_fuer_datei)
            ast.py      (_ast_block_fuer_zieldatei, _finde_modul_pfad,
                         _hat_symbol) — isoliert, damit Architect es
                         importieren kann ohne ganzen Builder zu ziehen
            patch.py    (_normalisiere_aider_patches, Apply)
            validate.py (_validate_imports_in_patch)
            prompt.py   (_builder_system, Prompt-Bau)
        architect/  (run_architect + Prompt-Bau)
        scout/
        reviewer/
        explorer/
        planner/
        reflection/
        verify/
        gates/
    domain/
        state/      (RunState aufgeteilt pro Rolle)
        contracts/  (State-Contract-Registry)
    infra/
        render/     (loop_renderer aufgeteilt)
            __init__.py
            emit.py     (_emit, _emit_raw, _publish)
            progress.py (_emit_progress, step, heartbeat, spinner_*)
            tasks.py    (task, task_ok, task_failed)
            tee.py      (_TeeWriter, _tee, set_tee_stream)
            rich.py     (_use_rich, _console)
            plan.py     (plan, header, summary)
        audit.py
        event_store.py
        paths.py
        git_ops.py
        hooks.py
    web/
        __init__.py
        app.py          (Komposition, ~50 Zeilen)
        routes/
            projekte.py
            runs.py
            events.py
            gates.py
            chat.py
        auth.py
        terminal.py     (aus shell.py + terminal_proxy.py konsolidiert)
        chat.py
        ws.py

**Split-Reihenfolge (nicht alle gleichzeitig!):**

1. **OP-134..137** (State-Contracts) — Voraussetzung fuer OP-141
2. **OP-138** (`render/` split) — groesster Einzelgewinn Lesbarkeit,
   wenig Risiko (nur Render-APIs)
3. **OP-139** (`phases/` split) — nach OP-138, weil phases
   render-APIs nutzt
4. **OP-140** (`builder/` split) — AST-Helpers isolieren, oeffnet
   den Architect-AST-Fix (OP-137)
5. **OP-142** (`web/routes/` split) — parallel zu OP-139/140,
   unabhaengig
6. **OP-141** (`state/` split) — nach OP-135/136, invasivster Schritt
7. **OP-143** (`cli/` + Re-Export-Bereinigung) — nach OP-139,
   weil phases-Re-Exports dann entfallen
8. **OP-144** (`import-linter` als Post-Build-Stage) — frueh
   parallel, mit Whitelist fuer bestehende Verletzungen

## Entscheidung

**Reihenfolge nach Risiko und Nutzen:**
- **Risiko-arm zuerst:** `render/` (OP-138) — reine API-Splits,
  keine Aufrufer-Aenderungen.
- **Voraussetzung zuerst:** OP-134..137 — ohne Contracts kein
  `state/`-Split.
- **Parallel:** OP-142 (web) und OP-144 (import-linter) blockieren
  nichts.
- **Invasiv zuletzt:** OP-141 (state) und OP-143 (Re-Exports).

**Nicht in einer Session:** Jeder Split ist ein eigener Commit,
mit Tests + Drift-Gruen. Wenn ein Split den Loop bricht, Rollback
via `git revert`.

**Erzwingung der Layer-Regeln via import-linter:**
Neue Verify-Stage in `.werkstatt/verify.json` (neben `audit_drift`
und `control_drift`). Initial mit Whitelist (bestehende Verletzungen
ignoriert), dann schrittweise schaerfer. Ziel: 0 Verletzungen.

## Konsequenzen

Positiv:
- Klare Modulgrenzen, einzeln testbar.
- Neue Rollen (z.B. `roles/debugger/`) haben einen klaren Platz.
- Architect kann AST importieren, ohne den Builder zu ziehen
  (loest das heutige AST-Asymmetrie-Problem).
- import-linter verhindert Rueckfall in alte Muster.

Negativ:
- Multi-Session-Arbeit (8-12 Sessions insgesamt).
- Jeder Split muss einzeln verifiziert werden — kein "einmal gross
  umbauen".
- Re-Export-Aufraeumen bricht 20+ Tests. Bewusste Entscheidung:
  Tests patchen den echten Modul-Pfad (`werkstatt.audit.audit`
  statt `werkstatt.loop.audit`).
- `web/routes/`-Split braucht Router-Integration-Tests (heute:
  keine).

Neutral:
- Der Loop bleibt waehrend der Splits funktionsfaehig.
- Bestehende OPs (OP-098 "pipeline_phases reduzieren") werden
  durch OP-139 implizit erledigt.
