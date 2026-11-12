"""Gates: Plan- und Human-Gate (Fix AZ Stufe 5b, 2026-10-31).

Extrahiert aus loop.py. Re-Export in loop.py erhaelt API-
Kompatibilitaet (Tests patchen werkstatt.loop._human_gate_plan).
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from werkstatt.state import RunState


def audit(*args, **kwargs):
    """Late-Binding-Proxy fuer werkstatt.loop.audit."""
    from werkstatt.loop import audit as _orig
    return _orig(*args, **kwargs)


def _call_hook(*args, **kwargs):
    """Late-Binding-Proxy fuer werkstatt.loop._call_hook."""
    from werkstatt.loop import _call_hook as _orig
    return _orig(*args, **kwargs)


def _committe_zielprojekt(*args, **kwargs):
    """Late-Binding-Proxy fuer werkstatt.loop._committe_zielprojekt."""
    from werkstatt.loop import _committe_zielprojekt as _orig
    return _orig(*args, **kwargs)


def _verify_patches(*args, **kwargs):
    """Late-Binding-Proxy fuer werkstatt.loop._verify_patches."""
    from werkstatt.loop import _verify_patches as _orig
    return _orig(*args, **kwargs)


def _verify_patches_soft(*args, **kwargs):
    """Late-Binding-Proxy fuer werkstatt.loop._verify_patches_soft."""
    from werkstatt.loop import _verify_patches_soft as _orig
    return _orig(*args, **kwargs)


_HEADLESS: bool = False


def set_headless(flag: bool) -> None:
    """Aktiviert den headless-Modus (OP-202, ADR-0007)."""
    global _HEADLESS
    _HEADLESS = flag


def _frage_gate(
    kind: str,
    prompt: str,
    optionen: str = "jna",
    timeout: float | None = None,
) -> str:
    """Fragt interaktiv (input) oder per Event-Store (gate_bridge).

    OP-381c: typ wird aus ``kind`` abgeleitet — ``plan_reason`` bekommt
    typ="freitext" (Reflection-Reject-Grund ist ein Textfeld, keine
    j/n/a-Buttons). Alle anderen kinds bleiben "jna".
    """
    if not _HEADLESS:
        return input(prompt)
    from werkstatt import gate_bridge
    from werkstatt.audit import get_run_id

    run_id = get_run_id()
    if not run_id:
        raise RuntimeError(
            "headless-Modus ohne set_run_id() -- Gate kann nicht "
            "adressiert werden"
        )
    gate_id = gate_bridge.make_gate_id(kind)
    _typ = "freitext" if kind == "plan_reason" else "jna"
    gate_bridge.signal_open(run_id, gate_id, prompt, optionen, typ=_typ)
    try:
        _kw = {} if timeout is None else {"timeout": timeout}
        return gate_bridge.wait(run_id, gate_id, **_kw)
    except gate_bridge.GateTimeout as exc:
        # Fail-closed: Loop-Antwort 'n' (= reject), Reflection kann greifen.
        # _frage_gate hat keinen RunState -> EventStore direkt.
        try:
            from werkstatt.event_store import EventStore as _ES
            _ES().append(
                run_id=run_id,
                kind="loop_gate_timeout",
                payload={"gate_id": gate_id, "kind": kind,
                         "error": str(exc)[:200]},
            )
        except Exception:  # noqa: BLE001
            pass
        return "n"


def _task_graph_error(tasks: list) -> str | None:
    """Liefert einen konkreten Fehler fuer einen ungueltigen Task-DAG."""
    by_id: dict[str, dict] = {}
    for index, task in enumerate(tasks, 1):
        if not isinstance(task, dict):
            return f"Task {index} ist kein Objekt"
        task_id = task.get("id")
        if not isinstance(task_id, str) or not task_id.strip():
            return f"Task {index} hat keine nichtleere ID"
        if task_id in by_id:
            return f"Task-ID {task_id!r} ist mehrfach vergeben"
        by_id[task_id] = task

    dependencies_by_id: dict[str, list[str]] = {}
    for task_id, task in by_id.items():
        dependencies = task.get("dependencies")
        if dependencies is None:
            dependencies = []
        if not isinstance(dependencies, list) or any(
            not isinstance(dependency, str) or not dependency.strip()
            for dependency in dependencies
        ):
            return f"Task {task_id!r} hat ungueltige dependencies"
        if len(set(dependencies)) != len(dependencies):
            return f"Task {task_id!r} wiederholt eine dependency"
        for dependency in dependencies:
            if dependency not in by_id:
                return (
                    f"Task {task_id!r} referenziert unbekannte "
                    f"dependency {dependency!r}"
                )
            if dependency == task_id:
                return f"Task {task_id!r} haengt von sich selbst ab"
        dependencies_by_id[task_id] = dependencies

    dependents: dict[str, list[str]] = {task_id: [] for task_id in by_id}
    indegree = {task_id: len(dependencies) for task_id, dependencies in dependencies_by_id.items()}
    for task_id, dependencies in dependencies_by_id.items():
        for dependency in dependencies:
            dependents[dependency].append(task_id)

    ready = [task_id for task_id, degree in indegree.items() if degree == 0]
    visited = 0
    while ready:
        task_id = ready.pop()
        visited += 1
        for dependent in dependents[task_id]:
            indegree[dependent] -= 1
            if indegree[dependent] == 0:
                ready.append(dependent)
    if visited != len(by_id):
        cyclic = sorted(task_id for task_id, degree in indegree.items() if degree)
        return f"zyklische Task-Abhaengigkeiten: {', '.join(cyclic)}"
    return None


def _plan_gate(state: RunState) -> bool:
    """B1: Plan-Gate (deterministisch).

    M-323c: Validiert Phasen-Struktur, wenn phasen existiert:
      - jeder Task mit phase_id hat eine gueltige phase_id
      - jede phase_id existiert in phasen
      - jede Phase hat mindestens 1 Task
    Flacher Plan (phasen leer) bleibt gueltig.
    """
    # M-408c: Architect-Modus braucht keine tests/akzeptanzkriterien
    _tasks_check = state.tasks or []
    graph_error = _task_graph_error(_tasks_check)
    if graph_error:
        state.last_planner_info = {
            "regel": "TASK_GRAPH",
            "fakt": graph_error,
            "erklaerung": (
                "Tasks muessen eindeutige IDs und einen vollstaendigen, "
                "azyklischen Abhaengigkeitsgraphen haben."
            ),
        }
        return False
    _is_architect = any(
        isinstance(_t, dict) and _t.get("action") == "architect"
        for _t in _tasks_check
    )
    if _is_architect:
        # Architect-Modus: 1 Task mit action=architect -> Plan ok
        return bool(_tasks_check)

    # M-457: Planner-Split (Architect+Split) braucht keine
    # tests/akzeptanzkriterien. Tests sind out-of-scope (M-449).
    _is_split = bool(state.architect_prosa)
    if _is_split:
        if not state.tasks:
            return False
    elif not all((
        state.tasks,
        state.tests,
        state.akzeptanzkriterien
    )):
        return False

    _phasen = state.phasen or []
    _tasks = state.tasks or []

    # K5: Phasen-Validierung nur wenn phasen existieren. Der
    # Doku-Filter-Hook unten laeuft IMMER — auch bei flachem Plan.
    if _phasen:
        _phasen_ids = {p.get("id") for p in _phasen if isinstance(p, dict)}

        # Jede Phase hat mindestens 1 Task
        for _phase in _phasen:
            _pid = _phase.get("id")
            _ptasks = [t for t in _tasks if isinstance(t, dict) and t.get("phase_id") == _pid]
            if not _ptasks:
                return False

        # Jeder Task mit phase_id hat eine gueltige phase_id
        for _t in _tasks:
            if not isinstance(_t, dict):
                continue
            _tid = _t.get("phase_id")
            if _tid is not None and _tid not in _phasen_ids:
                return False

    # M-349b: Doku-Tasks via Hook ablehnen (deterministisch).
    _hook_res = _call_hook("planner_gate.py", {
        "tasks": _tasks,
        "phasen": _phasen,
        "project_dir": str(getattr(state, "project_dir", "")),
        # K17c: Architect-Prosa fuer Migrations-Kollisions-Check.
        "architect_prosa": state.architect_prosa or "",
        # GOLD 2026-10-30: Original-Aufgabe, damit der Hook
        # Doku-Aufgaben erkennen kann.
        "aufgabe": state.aufgabe or "",
    })
    if not _hook_res.get("allow", True):
        # Info fuer Planner-Reflection
        state.last_planner_info = _hook_res.get("info", {})
        return False

    return True


def _human_gate_plan(state, kontext=""):
    """Verlangt immer menschliche Planfreigabe vor dem Builder.

    Weder CLI-Option noch Projektkonfiguration duerfen das verpflichtende
    Plan-Gate umgehen.
    """
    pd = getattr(state, "project_dir", None)
    pn = getattr(state, "project_name", "?")
    if pd is None:
        return 1

    import os as _os
    if _os.environ.get("WERKSTATT_IN_TEST") == "1":
        audit("loop_plan_gate_test", {"reason": "WERKSTATT_IN_TEST=1"}, pd, pn)
        return 0

    from werkstatt import render as _r
    _r.plan(
        state.phasen or [],
        state.tasks or [],
        state.tests or [],
        state.akzeptanzkriterien or [],
    )

    # OP-299: Plan-Text auditieren, damit er in der UI nachlesbar bleibt.
    # Der Architect-Prosa-Text ist die eigentliche Planung — kein UI-Weg
    # sonst, weil _r.plan() nur ins Terminal rendert.
    _is_noop_scout = bool(
        getattr(state, "scout_bereits_erfuellt", False)
    )
    _plan_text = getattr(state, "architect_prosa", "") or ""
    if _is_noop_scout:
        _plan_text = (
            "NO-OP-PLAN: Der Scout meldet den Auftrag bereits als erfuellt. "
            "Es sind keine Datei-Aenderungen geplant; die Freigabe erlaubt "
            "nur den Uebergang zur Ergebnispruefung."
        )
    if not _plan_text:
        # Fallback: strukturierter Plan als Text
        _parts: list[str] = []
        if state.phasen:
            _parts.append("Phasen:")
            for _ph in state.phasen:
                if isinstance(_ph, dict):
                    _parts.append(f"  - {_ph.get('id', '?')}: {_ph.get('titel', '')}")
        if state.tasks:
            _parts.append("")
            _parts.append("Tasks:")
            for _t in state.tasks:
                if isinstance(_t, dict):
                    _parts.append(f"  - {_t.get('id', '?')}: {_t.get('name', '')}")
        if state.akzeptanzkriterien:
            _parts.append("")
            _parts.append("Akzeptanzkriterien:")
            for _ak in state.akzeptanzkriterien:
                if isinstance(_ak, dict):
                    _parts.append(f"  - {_ak.get('id', '?')}: {_ak.get('text', '')}")
        _plan_text = "\n".join(_parts)

    if _plan_text:
        audit("loop_plan_shown",
              {
                  "plan_text": _plan_text[:80_000],
                  "plan_laenge": len(_plan_text),
                  "phasen_anzahl": len(state.phasen or []),
                  "tasks_anzahl": len(state.tasks or []),
              },
              pd, pn)

    # K20c: Leere-Antworten-Zaehler (EOF-aehnlicher Zustand via script-Wrapper).
    # OP-093: auch ungueltige-Antworten-Zaehler (Fail-closed nach 3 Versuchen).
    _leer_count = 0
    _ungueltig_count = 0
    # Nachbesserung OP-089: nach Reflection klar sagen dass es ein
    # revidierter Plan ist. Kein "a" (Plan anpassen) — sonst
    # Endlos-Zyklus moeglich.
    _ist_revidierter = kontext == "revidierter_plan"
    if _is_noop_scout:
        _prompt = (
            "\n== NO-OP-PLAN (Scout-Befund) ==\n"
            "Der Scout meldet, dass der Auftrag bereits erfuellt ist.\n"
            "Es sind keine Code-Aenderungen geplant. Die Freigabe setzt\n"
            "den Lauf nur zur Ergebnispruefung fort.\n"
            "\nDiesen Befund zur Ergebnispruefung freigeben? [j/n]\n"
            "  j = Ergebnispruefung fortsetzen\n"
            "  n = ablehnen und Lauf beenden\n"
            "Deine Wahl: "
        )
    elif _ist_revidierter:
        _prompt = (
            "\n== REVIDIERTER PLAN (nach Reflection) ==\n"
            "Du hattest den vorherigen Plan abgelehnt. Die Reflection hat\n"
            "einen neuen Plan gebaut. Bitte pruefen.\n"
            "\nRevidierter Plan OK? [j/n]\n"
            "  j = bauen\n"
            "  n = abbrechen (keine weitere Reflection)\n"
            "Deine Wahl: "
        )
    else:
        _prompt = (
            "\nPlan ausfuehren? [j/n/a]\n"
            "  j = bauen\n"
            "  n = ablehnen (Reflection mit Grund, max 1 Runde)\n"
            "      - Reject-Grund eingeben -> Planner baut revidierten Plan\n"
            "      - Grund leer lassen    -> hart abbrechen (kein Reflection)\n"
            "  a = Plan anpassen\n"
            "Deine Wahl: "
        )
    while True:
        try:
            _antwort = _frage_gate(
                "plan", _prompt,
                optionen=("jn" if _ist_revidierter or _is_noop_scout else "jna"),
            ).strip().lower()
        except (EOFError, KeyboardInterrupt):
            audit("loop_plan_gate_eof", {}, pd, pn)
            return 1

        # K20c: Leere Antwort -- script/su-Wrapper liefert '' statt EOFError.
        # Nach 3 leeren Versuchen abbrechen, sonst endlos-Schleife.
        if not _antwort:
            _leer_count += 1
            if _leer_count >= 3:
                audit("loop_plan_gate_leer",
                      {"anzahl": _leer_count}, pd, pn)
                return 1
            continue
        _leer_count = 0

        if _antwort == "j":
            audit("loop_plan_gate_approved", {}, pd, pn)
            return 0
        if _antwort == "n":
            # Welle H (2026-11-02): Reject-Grund erfassen fuer Reflection
            try:
                _reason = _frage_gate("plan_reason", 
                    "Reject-Grund (optional, Enter=leer): "
                ).strip()
            except (EOFError, KeyboardInterrupt):
                _reason = ""
            try:
                state.last_reject_kind = "plan"
                state.last_reject_reason = _reason
            except (AttributeError, TypeError):
                pass
            audit("loop_plan_reject_grund",
                  {"grund": _reason[:200]}, pd, pn)
            audit("loop_plan_gate_rejected", {"grund": _reason}, pd, pn)
            return 1
        if _antwort == "a":
            if _ist_revidierter or _is_noop_scout:
                # Kein Plan-Anpassen im revidierten Modus (Zyklus-Schutz)
                _ungueltig_count += 1
                if _ungueltig_count >= 3:
                    audit("loop_plan_gate_ungueltig",
                          {"anzahl": _ungueltig_count, "letzte_antwort": "a"}, pd, pn)
                    return 1
                _hinweis = (
                    "Kein 'a' in diesem No-Op-Gate."
                    if _is_noop_scout
                    else "Kein 'a' nach Reflection."
                )
                print(f"{_hinweis} Versuch {_ungueltig_count}/3.")
                continue
            _plan_file = Path(pd) / ".werkstatt" / f"{pn}.phase.yaml"
            print(f"\nPlan-Datei: {_plan_file}")
            try:
                _weiter = _frage_gate(
                    "plan_edit_continue",
                    "Plan-Datei bearbeiten, dann fortfahren? [j]: ",
                    "j",
                ).strip().lower()
            except (EOFError, KeyboardInterrupt):
                audit(
                    "loop_plan_gate_eof",
                    {"reason": "plan_edit_continue"},
                    pd,
                    pn,
                )
                return 1
            if _HEADLESS and _weiter != "j":
                audit(
                    "loop_plan_gate_rejected",
                    {"reason": "plan_edit_continue"},
                    pd,
                    pn,
                )
                return 1
            if _plan_file.exists():
                try:
                    import yaml
                    with _plan_file.open() as fh:
                        _d = yaml.safe_load(fh) or {}
                    if _d.get("tasks"):
                        state.tasks = _d["tasks"]
                    if _d.get("phasen"):
                        state.phasen = _d["phasen"]
                    if _d.get("tests"):
                        state.tests = _d["tests"]
                    if _d.get("akzeptanzkriterien"):
                        state.akzeptanzkriterien = _d["akzeptanzkriterien"]
                except Exception:
                    pass
            _r.plan(
                state.phasen or [],
                state.tasks or [],
                state.tests or [],
                state.akzeptanzkriterien or [],
            )
            continue
        # OP-093: Fail-closed nach 3 ungueltigen Antworten.
        _ungueltig_count += 1
        if _ungueltig_count >= 3:
            audit("loop_plan_gate_ungueltig",
                  {"anzahl": _ungueltig_count,
                   "letzte_antwort": _antwort[:20]},
                  pd, pn)
            return 1
        print(f"Antworte mit j, n oder a. "
              f"(Versuch {_ungueltig_count}/3)")
        continue

    return 1


def _adr_mini_aktiv() -> bool:
    """OP-058: Opt-in via WERKSTATT_ADR_MINI=1."""
    import os as _os_adr
    return _os_adr.environ.get("WERKSTATT_ADR_MINI") == "1"


def _naechste_adr_nummer(adr_dir: Path) -> int:
    """OP-058: Hoechste existierende ADR-Nummer +1. Fallback 1."""
    import re as _re_adr
    if not adr_dir.exists():
        return 1
    max_n = 0
    for f in adr_dir.iterdir():
        if f.is_file() and f.name.startswith("ADR-"):
            m = _re_adr.match(r"ADR-(\d+)", f.name)
            if m:
                max_n = max(max_n, int(m.group(1)))
    return max_n + 1


def _adr_template(nummer: int, slug: str, aufgabe: str, pd: Path) -> str:
    """OP-058: Deterministisches ADR-Template (kein LLM, Mensch fuellt)."""
    from datetime import date as _date_adr
    datum = _date_adr.today().isoformat()
    return (
        f"# ADR-{nummer:04d}: {slug}\n\n"
        f"- **Datum:** {datum}\n"
        f"- **Status:** proposed\n"
        f"- **Kontext:** Loop-Aufgabe in {pd.name}: {aufgabe[:200]}\n\n"
        f"## Entscheidung\n\n"
        f"<!-- Vom Menschen zu fuellen: Welche Entscheidung wurde getroffen? -->\n\n"
        f"## Konsequenzen\n\n"
        f"<!-- Vom Menschen zu fuellen: Was folgt daraus? -->\n\n"
        f"## Alternativen\n\n"
        f"<!-- Vom Menschen zu fuellen: Was wurde verworfen und warum? -->\n"
    )


def _adr_index_append(adr_dir: Path, nummer: int, slug: str, filename: str) -> bool:
    """OP-058: Ergaenzt Zeile in docs/adr/README.md."""
    readme = adr_dir / "README.md"
    if not readme.exists():
        return False
    txt = readme.read_text(encoding="utf-8")
    lines = txt.split("\n")
    last_row = -1
    for i, ln in enumerate(lines):
        if ln.strip().startswith("|") and "ADR-" in ln:
            last_row = i
    if last_row < 0:
        return False
    new_row = f"| {nummer:04d} | {slug} | [{filename}]({filename}) |"
    lines.insert(last_row + 1, new_row)
    readme.write_text("\n".join(lines), encoding="utf-8")
    return True


def _adr_mini_phase(state: RunState) -> bool:
    """OP-058: Fragt nach ADR, legt ADR an bei 'j'. True = weitermachen."""
    import os as _os_adr_run
    if not _adr_mini_aktiv():
        return True
    if _os_adr_run.environ.get("WERKSTATT_IN_TEST") == "1":
        return True
    pd = getattr(state, "project_dir", None)
    pn = getattr(state, "project_name", "?")
    if pd is None:
        return True
    adr_dir = Path(pd) / "docs" / "adr"
    if not adr_dir.exists():
        audit("adr_mini_skip", {"reason": "no_adr_dir"}, pd, pn)
        return True
    try:
        antwort = _frage_gate(
            "adr_mini", "ADR dokumentieren? [j/n]: ", "jn",
        ).strip().lower()
    except (EOFError, KeyboardInterrupt):
        return True
    if antwort not in ("j", "ja", "y", "yes"):
        audit("adr_mini_skip", {"reason": "user_no"}, pd, pn)
        return True
    nummer = _naechste_adr_nummer(adr_dir)
    aufgabe = (state.aufgabe or "").strip()
    slug = "-".join(aufgabe.lower().split()[:5])[:50] or "loop-entscheidung"
    filename = f"ADR-{nummer:04d}-{slug}.md"
    try:
        (adr_dir / filename).write_text(
            _adr_template(nummer, slug, aufgabe, Path(pd)),
            encoding="utf-8",
        )
        _adr_index_append(adr_dir, nummer, slug, filename)
        audit("adr_mini_created", {"file": filename, "nr": nummer}, pd, pn)
        print(f"  ADR angelegt: docs/adr/{filename}")
    except Exception as _e:
        audit("adr_mini_fehler", {"error": str(_e)[:200]}, pd, pn)
    return True


def _diff_hunk_summary(diff: str, max_hunks_per_file: int = 5) -> str:
    """OP-062c: Kompakte Hunk-Summary statt Roh-Diff.

    Pro Datei: Datei + Hunk-Header (@@ ... @@ funcname). Keine '+'-Zeilen,
    keine '-'-Zeilen, keine Kontext-Zeilen. Nur die Struktur, damit der
    Mensch sieht 'wo wurde was geaendert' ohne den vollen Diff zu lesen.
    """
    _out: list[str] = []
    _cur: str | None = None
    _hunks: list[str] = []

    def _flush() -> None:
        nonlocal _cur, _hunks
        if _cur is None:
            return
        _out.append(_cur)
        for _h in _hunks[:max_hunks_per_file]:
            _out.append(f"  {_h}")
        if len(_hunks) > max_hunks_per_file:
            _out.append(
                f"  ... ({len(_hunks) - max_hunks_per_file} weitere Hunks)"
            )
        _cur, _hunks = None, []

    for line in diff.splitlines():
        if line.startswith("diff --git "):
            _flush()
            # b/pfad extrahieren
            _parts = line.split(" b/", 1)
            _file = _parts[1] if len(_parts) == 2 else line[11:]
            _cur = _file
        elif line.startswith("@@") and _cur is not None:
            _hunks.append(line)
    _flush()
    return "\n".join(_out) if _out else "(keine Hunk-Header)"


def _human_gate_body(state) -> str:
    """OP-062b: Kontext-Block fuer das Human-Gate.

    Zeigt dem Menschen am Gate, was der Loop im Hintergrund entschieden
    hat: Architect-Plan, letzte Reviewer-Bugs, Reflexions-Runden.
    Ohne diese Anzeige sah der Mensch 15:16 nur Task-Status + Diff-Stat
    und musste den Audit-Log manuell lesen.

    Reine Funktion, kein Seiteneffekt. Leerer String wenn nichts da ist.
    """
    _parts: list[str] = []

    # OP-090: Reflection-Erschoepfungs-Hinweis
    if state.reflection_erschoepft:
        _parts.append(
            "## Reflection erschoepft\n"
            "Der Loop konnte keinen gruenen Test erreichen.\n"
            "j = Patches behalten + committen (Task ok)\n"
            "n = Patches verwerfen (Task fail, Loop laeuft weiter)\n"
            "e = Datei manuell editieren"
        )

    # 0. OP-062e + OP-062g: Nullfall-Anzeige.
    if state.scout_bereits_erfuellt:
        _parts.append(
            "## Erfuellt ohne Aenderung (Scout)\n"
            "Der Scout hat erkannt, dass die Zieldatei bereits "
            "den geforderten Zustand hat. Kein Builder, kein Diff."
        )
    if state.auftrag_bereits_erfuellt:
        _parts.append(
            "## Erfuellt ohne Aenderung\n"
            "Der Builder hat 'auftrag_bereits_erfuellt' gesetzt — "
            "die Zieldatei war bereits im Zielzustand. Es gab nichts "
            "zu aendern."
        )
    _pe_skip = getattr(state, "phase_review_uebersprungen", None)
    if _pe_skip:
        _parts.append(
            f"## Phase-End-Review (uebersprungen: {_pe_skip})\n"
            "Kein Diff in der Phase — die Review wurde uebersprungen."
        )

    # 1. Architect-Plan / Scout-Marker
    _prosa = (state.architect_prosa or "").strip()
    if _prosa:
        if _prosa == "[atomarer Plan vom Scout]":
            _parts.append("## Plan (vom Scout, atomar zerlegt)")
        else:
            # Auf 2000 Zeichen kappen, damit der Panel nicht explodiert.
            _snippet = _prosa[:2000]
            if len(_prosa) > 2000:
                _snippet += "\n... (gekuerzt)"
            _parts.append("## Architect-Plan\n" + _snippet)

    # 2. Letzte Reviewer-Bugs (aus History, letzte Runde)
    # OP-062c: Bug-Sync. Wenn state.reviewer_bugs leer ist, war der
    # letzte Reviewer-Call gruen -> History-Bugs sind behoben.
    _cur_bugs = state.reviewer_bugs or []
    _current_open = bool(_cur_bugs)
    _hist = state.reviewer_bugs_history or []
    _last_bugs: list = []
    if _hist:
        _last_bugs = [b for b in (_hist[-1] or [])
                      if isinstance(b, dict)]
    if not _last_bugs and _current_open:
        _last_bugs = [b for b in _cur_bugs if isinstance(b, dict)]
    if _last_bugs:
        _status = "offen" if _current_open else "vermutlich behoben"
        _lines = [
            f"## Reviewer-Bugs (letzte Runde, {len(_last_bugs)}, {_status})"
        ]
        for _b in _last_bugs[:5]:
            _sev = _b.get("severity", "?")
            _file = _b.get("file", "?")
            _desc = (_b.get("description") or "")[:200]
            _mark = "" if _current_open else " (vermutlich behoben)"
            _lines.append(f"  - [{_sev}] {_file}: {_desc}{_mark}")
        if len(_last_bugs) > 5:
            _lines.append(f"  ... ({len(_last_bugs) - 5} weitere)")
        _parts.append("\n".join(_lines))

    # 3. Reflexions-Runden
    # OP-062c: task_id-Prefix, damit bei mehreren Tasks die Runden
    # nicht als 'Runde 1, Runde 1' verwechselt werden.
    _refl = state.reflection_history or []
    if _refl:
        _lines = [f"## Reflexion ({len(_refl)} Runde(n))"]
        for _r in _refl[-5:]:
            if not isinstance(_r, dict):
                continue
            _nr = _r.get("runde", "?")
            _tid = _r.get("task_id")
            _n = _r.get("patches_applied", 0)
            _v = len(_r.get("verify_errors") or [])
            _b = len(_r.get("reviewer_bugs") or [])
            _label = f"{_tid} Runde {_nr}" if _tid else f"Runde {_nr}"
            _lines.append(
                f"  - {_label}: {_n} Patches angewendet, "
                f"{_v} verify-Fehler offen, {_b} reviewer-Bugs offen"
            )
        _parts.append("\n".join(_lines))

    return "\n\n".join(_parts)


def _human_gate(state: RunState, *, defer_commit: bool = False) -> int:
    """Eigenes Human-Gate im Loop (fail-closed).

    Projektkonfiguration kann dieses Human-Gate nicht deaktivieren.
    Bei EOF/Abbruch wird fail-closed abgelehnt (rc=1).
    - defer_commit=True: explizites j gibt rc=2 zurueck; der Aufrufer
      muss erst nach erfolgreichem Verify committen.
    """
    pd = getattr(state, "project_dir", None)
    pn = getattr(state, "project_name", "?")
    if pd is None:
        return 1

    # Im Test-Kontext: automatisch approven (kein input())
    import os as _os
    if _os.environ.get("WERKSTATT_IN_TEST") == "1":
        audit("loop_human_gate_test", {"reason": "WERKSTATT_IN_TEST=1"}, pd, pn)
        return 0

    # Interaktiv: fail-closed bei EOFError
    # M-303: Impact-Preview vor dem Gate (Agent-Polis/pi-show-diffs-Muster).
    # M-372: panel_diff statt Plain-Text (rich im pretty/live-Modus).
    from werkstatt import render as _rh
    _stat_txt = ""
    _diff_txt = ""
    try:
        # FIX O 2026-10-31: Untracked sichtbar machen via intent-to-add.
        # Sonst zeigt Human-Gate nur PROGRESS.md, nicht die neue Datei.
        subprocess.run(
            ["git", "-C", str(pd), "add", "-N", "."],
            capture_output=True, text=True, check=False, timeout=10,
        )
        _stat = subprocess.run(
            ["git", "-C", str(pd), "diff", "--stat"],
            capture_output=True, text=True, check=False, timeout=10,
        ).stdout
        _stat_txt = _stat.strip() if _stat.strip() else "  (keine Aenderungen)"

        # OP-062d: Voller Diff bei <=2000 Zeichen, sonst Hunk-Summary.
        _full = subprocess.run(
            ["git", "-C", str(pd), "diff"],
            capture_output=True, text=True, check=False, timeout=10,
        ).stdout
        if _full.strip() and len(_full) <= 2000:
            _diff_txt = _full
        elif _full.strip():
            _summary = _diff_hunk_summary(_full)
            _diff_txt = (
                f"  (Diff {len(_full)} Zeichen, Struktur:)\n"
                f"{_summary}"
            )
    except Exception:
        _stat_txt = "  (Diff nicht verfuegbar)"

    # FIX AD 2026-10-31: Task-Fortschritt VOR dem Diff anzeigen.
    _fortschritt = _task_fortschritt_block(Path(pd), pn)
    _gate_body = ""
    if _fortschritt:
        _gate_body = _fortschritt + "\n"
    # OP-062b: Architect-Plan, Reviewer-Bugs, Reflexionen.
    _detail = _human_gate_body(state)
    if _detail:
        _gate_body += "\n" + _detail + "\n"
    _gate_body += f"Aenderungen im Zielprojekt:\n{_stat_txt}"
    if _diff_txt:
        _gate_body += f"\n\n{_diff_txt}"
    try:
        _rh.panel_diff(_gate_body, title="HUMAN GATE")
    except Exception:
        # Fallback: Plain
        print("\n=== HUMAN GATE ===")
        print(_gate_body)

    print()
    print("Approve? [j/n/e]")
    print("  j = approve")
    print("  n = reject (Loop bricht ab)")
    print("  e = Datei manuell bearbeiten (dann erneut fragen)")
    try:
        antwort = _frage_gate(
            "commit",
            "\nPhase committed werden? [j/n/e]\n"
            "  j = ja (committen)\n"
            "  n = nein (Abbruch, kein Commit)\n"
            "  e = edit (Aenderungen pruefen, dann neu fragen)\n"
            "Deine Wahl: ",
            "jne",
        ).strip().lower()
    except (EOFError, KeyboardInterrupt):
        audit("loop_human_gate_eof", {"reason": "EOFError/KeyboardInterrupt"}, pd, pn)
        return 1

    if antwort in ("j", "ja", "y", "yes"):
        audit("loop_human_gate_approved", {}, pd, pn)
        # OP-058: ADR-Mini-Phase (opt-in WERKSTATT_ADR_MINI=1).
        _adr_mini_phase(state)
        # In Phase 5 muss das harte Phase-End-Verify erst ueber
        # denselben, gegebenenfalls manuell geaenderten Diff laufen.
        # Rueckgabewert 2 signalisiert: explizit freigegeben, Commit offen.
        if defer_commit:
            return 2
        # M-487: Human-Gate committet selbst (nur bei explizitem j).
        _ok, _info = _committe_zielprojekt(state)
        if not _ok:
            audit("loop_human_gate_commit_abort", {"info": _info}, pd, pn)
            print(f"  FEHLER beim Commit: {_info}")
            return 1
        if _info:
            print(f"  Commit: {_info}")
        return 0
    if antwort == "e":
        # Manueller Edit-Modus: Nutzer oeffnet Editor, dann erneut fragen
        print("  Bitte Datei(en) manuell bearbeiten.")
        try:
            _weiter = _frage_gate(
                "commit_edit_continue",
                "Aenderungen geprueft? Fortfahren? [j]: ",
                "j",
            ).strip().lower()
        except (EOFError, KeyboardInterrupt):
            audit(
                "loop_human_gate_eof",
                {"reason": "commit_edit_continue"},
                pd,
                pn,
            )
            return 1
        if _HEADLESS and _weiter != "j":
            audit(
                "loop_human_gate_rejected",
                {"reason": "commit_edit_continue"},
                pd,
                pn,
            )
            return 1
        # Rekursiv erneut fragen (Diff neu anzeigen)
        return _human_gate(state, defer_commit=defer_commit)
    audit("loop_human_gate_rejected", {"antwort": antwort}, pd, pn)
    return 1



def _task_fortschritt_block(*args, **kwargs):
    """Late-Binding-Proxy fuer werkstatt.loop._task_fortschritt_block."""
    from werkstatt.loop import _task_fortschritt_block as _orig
    return _orig(*args, **kwargs)


__all__ = ['_diff_hunk_summary', '_frage_gate', '_human_gate', '_human_gate_body', '_human_gate_plan', '_plan_gate', 'set_headless']
