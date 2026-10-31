"""Planner-Agent (Phase 5, 2026-10-23).

Eigenstaendiger Planner. Liest Aufgabe + Kontext,
ruft ask_llm (JSON-Modus) auf, schreibt Plan in
state.tasks / state.tests / state.akzeptanzkriterien.

Kein Schreiben von Code. Kein Executor.
Reiner Denker (Codex Plan Mode).
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from werkstatt.agent import ask_llm
from werkstatt.loop_renderer import _with_spinner


# M-442: Architect-Modell konfigurierbar (Default: deepseek-chat).
# Fuer Messungen: WERKSTATT_ARCHITECT_MODEL=deepseek-reasoner
def _is_reasoning_model(model: str) -> bool:
    """M-445: Reasoning-Modelle unterstuetzen temperature/top_p nicht."""
    return "reasoner" in model.lower() or "r1" in model.lower()


_ARCHITECT_MODEL = os.environ.get("WERKSTATT_ARCHITECT_MODEL", "deepseek-chat")

from werkstatt.audit import audit
# Fix AZ Stufe 9+10: Re-Exports fuer API-Kompatibilitaet.
from werkstatt.scout import (  # noqa: F401
    SCOUT_SYSTEM,
    _SCOUT_NACHFOLGER_BLOCK,
    _baue_api_index,
    _finde_api,
    _format_api_index_for_prompt,
    _pruefe_api_widerspruch,
    _run_scout,
    _scout_system_with_nachfolger,
)
from werkstatt.architect import (  # noqa: F401
    ARCHITECT_SYSTEM,
    _BUILDER_SCHNITTSTELLE,
    _architect_system_with_builder,
    _planner_system,
    run_architect,
)
from werkstatt.state import RunState


def _klassifiziere_fehler(stage_id: str, fehlertext: str) -> str:
    """M-299a: Klassifiziert einen Verify-Fehler nach Klasse.

    Klassen:
      env     — Umgebungsproblem (ModuleNotFoundError, ImportError)
      lint    — mechanisch (ruff --fix)
      type    — Typfehler (mypy)
      test    — Testfehler (pytest)
      syntax  — Syntaxfehler (py_compile)
      unknown — Sonstiges
    """
    # K9: Prefix-Match statt Gleichheit — verify.json liefert
    # py_compile_changed/py_compile_core, ruff_changed, pytest_changed.
    if stage_id.startswith("py_compile") or "SyntaxError" in fehlertext:
        return "syntax"
    if "ModuleNotFoundError" in fehlertext or "ImportError" in fehlertext:
        return "env"
    if stage_id.startswith("ruff"):
        return "lint"
    if stage_id.startswith("mypy"):
        return "type"
    if stage_id.startswith("pytest"):
        return "test"
    return "unknown"


def _preflight_scan(state: RunState) -> list[dict]:
    """M-299a: Liest verify.json, fuehrt Stages aus, klassifiziert Fehler.

    Liefert strukturierte Fehlerliste:
      [{klasse, stage_id, datei, text}, ...]

    Wird in state.preflight_fehler persistiert (vom Aufrufer).
    """
    import json
    import subprocess
    from pathlib import Path as _P

    pd = getattr(state, "project_dir", None)
    if pd is None:
        return []
    project_dir = _P(pd)

    contract = project_dir / ".werkstatt" / "verify.json"
    if not contract.exists():
        return []

    try:
        stages = json.loads(contract.read_text(encoding="utf-8")).get("stages", [])
    except (json.JSONDecodeError, OSError):
        return []

    fehler: list[dict] = []
    for stage in stages:
        cmd = stage.get("command")
        if not cmd:
            continue
        stage_id = stage.get("id", "?")
        try:
            res = subprocess.run(
                cmd, cwd=str(project_dir),
                capture_output=True, text=True, timeout=300, check=False,
            )
            if res.returncode == 0:
                continue
            stderr = (res.stderr or "") + (res.stdout or "")
            klasse = _klassifiziere_fehler(stage_id, stderr)
            # M-299i: Datei-Pfad aus Fehlertext extrahieren (deterministisch).
            # mypy/ruff: "path/to/file.py:ZEILE: ..." oder
            #            "path/to/file.py:ZEILE:SPALTE: CODE ..."
            _file_pattern = re.compile(r'([a-zA-Z0-9_./-]+\.(?:py|md|yaml|yml|json|txt|toml))')
            _dateien = _file_pattern.findall(stderr)
            _datei = _dateien[0] if _dateien else None
            fehler.append({
                "klasse": klasse,
                "stage_id": stage_id,
                "datei": _datei,
                "text": stderr[:500],
            })
        except Exception as exc:  # noqa: BLE001
            fehler.append({
                "klasse": "unknown",
                "stage_id": stage_id,
                "datei": None,
                "text": f"Exception: {exc}",
            })
    return fehler



_TOOL_CALL_TAGS = (
    "shell_command", "read_file", "write_file", "tool_call", "tool_result",
    "tool", "function", "function_calls", "invoke", "parameter",
    "antml:invoke", "antml:parameter",
)

_DSML_TOKEN = "\uff5c\uff5cDSML\uff5c\uff5c"


def _strip_xml_tags(text: str) -> str:
    """K7/K51/K52: Entfernt XML- und DSML-Tool-Call-Marker aus Prosa.

    K52: generischer Ansatz. Statt eine feste Tag-Liste zu pflegen
    (jedes LLM nutzt neue Marker: <tool_call>, <invoke>, <function_calls>,
    <read_file>, DSML-Special-Tokens), entfernen wir:
    - Bekannte Tag-Namen (Block + Einzel).
    - DSML-Special-Tokens (Unicode-Fullwidth-Pipes).
    - Verbleibende Bloecke <X>...</X> mit identischem Namen (rekursiv).
    """
    import re as _re
    # 1) K52: bekannte Tag-Namen als Block.
    _names = "|".join(_TOOL_CALL_TAGS)
    text = _re.sub(
        rf"<({_names})(?:[^>]*>|\s[^>]*>).*?</\1>",
        "",
        text,
        flags=_re.DOTALL,
    )
    # 2) K52: bekannte Tag-Namen als Einzel-Tag.
    text = _re.sub(
        rf"<({_names})[^>]*/?>",
        "",
        text,
        flags=_re.DOTALL,
    )
    # 3) K51: DSML-Special-Tokens.
    text = _re.sub(
        "<" + _DSML_TOKEN + r"[^>]*>.*?</" + _DSML_TOKEN + r"[^>]*>",
        "",
        text,
        flags=_re.DOTALL,
    )
    text = _re.sub(
        "<" + _DSML_TOKEN + r"[^>]*/?>",
        "",
        text,
        flags=_re.DOTALL,
    )
    # 4) K52: verbleibende <X>...</X>-Bloecke mit gleichem Namen
    #    (generisch, unabhaengig vom Tag-Namen).
    text = _re.sub(
        r"<([a-zA-Z_:][\w:.-]*)(?:\s[^>]*)?>.*?</\1>",
        "",
        text,
        flags=_re.DOTALL,
    )
    # 5) K52: verbleibende Einzel-Tags mit Attributen (kein
    #    Vergleichstext, z.B. <br>, <img>).
    text = _re.sub(
        r"<[a-zA-Z_:][\w:.-]*(?:\s[^>]*)?/?>",
        "",
        text,
    )
    return text.strip()


def _erledigte_punkte(pd) -> str:
    """K6: Sammelt erledigte Punkte aus git log + ROADMAP.md.

    Verhindert, dass der Architect bereits abgeschlossene
    Punkte erneut plant.
    """
    import re as _re
    import subprocess as _sp
    from pathlib import Path as _Path

    _teile: list[str] = []
    _pd = _Path(pd) if pd else _Path(".")
    try:
        res = _sp.run(
            ["git", "-C", str(_pd), "log", "--grep=✅", "--oneline", "-20"],
            capture_output=True, text=True, timeout=10, check=False,
        )
        if res.stdout.strip():
            _teile.append("Commits mit ✅:\n" + res.stdout.strip())
    except Exception:  # noqa: BLE001
        pass

    # K6.1: ROADMAP.md UND STATUS.md als Signal.
    for _name, _rel in (
        ("ROADMAP", ("docs/ROADMAP.md", "ROADMAP.md")),
        ("STATUS", ("docs/STATUS.md", "STATUS.md")),
    ):
        _file = None
        for _cand in _rel:
            _cand_p = _pd / _cand
            if _cand_p.is_file():
                _file = _cand_p
                break
        if _file is None:
            continue
        try:
            _txt = _file.read_text(encoding="utf-8")
        except OSError:
            continue
        _matches = _re.findall(r"^.*✅.*$", _txt, flags=_re.MULTILINE)
        if _matches:
            _teile.append(
                f"{_name} ✅-Zeilen:\n" + "\n".join(_matches[:30])
            )

    return "\n\n".join(_teile)




PLANNER_SPLIT_SYSTEM = """Du bist ein Task-Zerleger.
Du bekommst eine Architect-Prosa und eine Liste von Dateien.
Zerlege die Prosa in so viele Sub-Tasks wie noetig (typisch 3-10).
Nicht mehr, nicht weniger als die Aufgabe braucht.

Jeder Sub-Task:
- id: "t1", "t2", ... (aufsteigend)
- name: kurzer Titel (< 50 Zeichen)
- action: "update" (Datei existiert) oder "create" (neue Datei)
- task_files: Liste der Dateien, die dieser Sub-Task aendert
  (max 1 Datei pro Task, wenn moeglich)
- architect_start: ERSTE Zeile des Architect-Abschnitts,
  der zu diesem Task gehoert (woertliches Zitat, z.B. "5. Backup").
  FUER __init__.py-Tasks: verwende den exakten Schritt, z.B.
  "15. In __init__.py: __all__ alphabetisch sortieren".
- architect_ende: LETZTE Zeile des Architect-Abschnitts
  (woertliches Zitat, z.B. "6. Anwenden").
  WICHTIG: architect_start und architect_ende muessen BENACHBARTE
  nummerierte Schritte sein (max 3 Schritte dazwischen).
  Wenn ein Task nur 1 Schritt umfasst, setze start = ende.
- dependencies: Liste von Task-IDs, die vorher fertig sein muessen.

Regeln:
  - INTERFACE-GRENZE: Jede Task liefert EIN vollstaendiges,
    reviewbares Interface — nicht einen Schritt einer Funktion.
    Beispiel GUT: eine Funktion/Methode komplett (Eingabepruefung,
    Kernlogik, Fehlerbehandlung, Rueckgabe) als EINE Task.
    Beispiel SCHLECHT: Eingabepruefung / Kernlogik / Fehler-
    behandlung als getrennte Tasks fuer dieselbe Funktion.
  - Groesse: 50-150 Zeilen Code pro Task. Zu klein (< 30 Zeilen):
    Reviewer sieht kein Feature. Zu gross (> 200 Zeilen):
    Semantik geht verloren.
  - Eine Datei mit N unabhaengigen Funktionen/Klassen:
    EINE Task pro Einheit, nicht pro Schritt.
  - Eine Datei mit EINER Funktion/Klasse: EINE Task fuer die
    ganze Einheit — nicht in Schritte aufteilen.
  - Keine Test-Dateien (tests/*).
  - DOKU-AUFGABEN: Wenn die Prosa AUSSCHLIESSLICH
    Markdown-Dateien (docs/*.md, README.md) aendert und
    KEINEN Python-Code nennt: Erzeuge GENAU EINEN Task fuer
    die genannte Markdown-Datei. Keine Code-Tasks aus
    Symbolen, die in der Prosa nur als "schon erledigt" oder
    "bereits vorhanden" erwaehnt werden. Beispiel: Prosa sagt
    "in docs/DECISIONS.md Abschnitt 2 praezisieren, kein
    Python-Code" -> Task t1 mit task_files=["docs/DECISIONS.md"],
    action="update", architect_start/ende aus der Prosa.
  - architect_start und architect_ende MUESSEN woertlich in
    der Architect-Prosa vorkommen. Der Loop extrahiert dann
    den Text dazwischen.

Antworte NUR mit JSON:
{
  "tasks": [
    {"id": "t1", "name": "...", "action": "update",
     "task_files": ["..."], "architect_start": "...",
     "architect_ende": "...", "dependencies": []},
    ...
  ]
}
Keine Erklaerung, nur JSON."""

PLANNER_SPLIT_SINGLE_SYSTEM = """Du bist ein Task-Zerleger.
Du bekommst EINEN zu grossen Sub-Task (Description > 2000 Zeichen
oder vom Builder als zu gross gemeldet).
Zerlege ihn in 2-3 kleinere Sub-Tasks.

Jeder Sub-Task:
- id: "tN_a", "tN_b", ... (abgeleitet von der Original-ID)
- name: kurzer Titel (< 50 Zeichen)
- action: "update" oder "create"
- task_files: Liste der Dateien (max 1)
- architect_start: ERSTE Zeile des Architect-Abschnitts (woertlich)
- architect_ende: LETZTE Zeile (woertlich, benachbart zu start)
- dependencies: Liste von Task-IDs

Regeln:
  - Jede Sub-Task liefert ein vollstaendiges, reviewbares
    Interface (nicht einen Schritt). Max 3 Sub-Tasks.
  - Groesse: 50-150 Zeilen Code pro Sub-Task.
  - architect_start und architect_ende MUESSEN woertlich
    in der Architect-Prosa vorkommen.

Antworte NUR mit JSON:
{
  "tasks": [
    {"id": "...", "name": "...", "action": "update",
     "task_files": ["..."], "architect_start": "...",
     "architect_ende": "...", "dependencies": []},
    ...
  ]
}
Keine Erklaerung, nur JSON."""




def _migrations_stand(pd) -> str:
    """K17: Deterministischer Migrationsstand fuer Architect-Kontext.

    Liest data/migrations/ und liefert eine kurze, sortierte Liste
    der vorhandenen Nummern + die hoechste Nummer explizit. Wird
    NUR eingefuegt, wenn Dateien vorhanden sind. Kein Fehlerfall
    propagiert (fail-soft, Kontext ist Zusatzinfo).
    """
    try:
        from pathlib import Path as _P
        mdir = _P(str(pd)) / "data" / "migrations"
        if not mdir.is_dir():
            return ""
        files = sorted(f.name for f in mdir.glob("*.sql") if f.is_file())
        if not files:
            return ""
        nums = []
        for name in files:
            head = name.split("_", 1)[0]
            if head.isdigit():
                nums.append(head)
        if not nums:
            return ""
        hoechste = max(nums)
        naechste = f"{int(hoechste) + 1:04d}"
        # K17b: Kompakter pflicht-Block (Lost-in-the-Middle-Schutz).
        # Nur Fakten: hoechste Nr., naechste freie Nr., Sperrliste.
        gesperrt = ", ".join(f"{n}_*" for n in sorted(set(nums))[-5:])
        lines = [
            "<migrationsstand pflicht=\"true\">",
            f"Hoechste vorhandene Nummer: {hoechste}",
            f"Naechste freie Nummer: {naechste}",
            f"VERBOTEN (bereits belegt): {gesperrt}",
            "Waehle fuer neue Migrationen NUR die naechste freie Nummer.",
            "Eine andere Nummer fuehrt zu einem Review-Fail und Loop-Abbruch.",
            "</migrationsstand>",
        ]
        return "\n".join(lines)
    except Exception:  # noqa: BLE001
        return ""


def _pruefe_migrations_kollision(
    prosa: str, pd,
) -> list[dict]:
    """K17b: Deterministische Migrations-Kollision pruefen.

    Sucht in der Architect-Prosa nach 'data/migrations/NNNN_*.sql'
    und prueft, ob NNNN als Datei bereits existiert. Gibt Liste
    von Kollisionen zurueck (leer = OK).

    Fail-soft: bei IO-Fehler (Ordner fehlt) -> leere Liste.
    """
    try:
        import re
        from pathlib import Path as _P
        mdir = _P(str(pd)) / "data" / "migrations"
        if not mdir.is_dir():
            return []
        existierend = set()
        for f in mdir.glob("*.sql"):
            head = f.name.split("_", 1)[0]
            if head.isdigit():
                existierend.add(head)
        geplant = re.findall(r"data/migrations/(\d+)_", prosa)
        kollisionen: list[dict] = []
        for n in sorted(set(geplant)):
            if n in existierend:
                kollisionen.append({"nummer": n, "existiert": True})
        return kollisionen
    except Exception:  # noqa: BLE001
        return []


# =====================================================
# GOLD: Agent-Schnittstellen (kompakt, deterministisch)
# =====================================================












def _normalisiere(text: str) -> str:
    """M-463: Entfernt Backticks, mehrfache Leerzeichen.

    Damit Marker wie "1. In `applier.py`" und "1. In applier.py"
    matchen.
    """
    import re as _re
    text = text.replace("`", "")
    text = _re.sub(r"\s+", " ", text)
    return text.strip()


def _segmentiere_nach_pfad(prosa: str) -> list[dict]:
    """Deterministisch: zerlegt Prosa an "## <pfad>"-Ueberschriften.

    Liefert Liste von {"datei": str, "prosa": str}.
    Reine Textverarbeitung, kein LLM.
    """
    import re as _re
    segs: list[dict] = []
    pat = _re.compile(r"^##\s+(\S+\.py)\s*$", _re.MULTILINE)
    ms = list(pat.finditer(prosa))
    for i, m in enumerate(ms):
        start = m.start()
        ende = ms[i + 1].start() if i + 1 < len(ms) else len(prosa)
        segs.append({
            "datei": m.group(1),
            "prosa": prosa[start:ende].strip(),
        })
    return segs


def _extrahiere_prosa_abschnitt(
    prosa: str, start: str, ende: str,
) -> str:
    """M-461/M-463: Extrahiert woertlichen Prosa-Abschnitt zwischen Markern.

    Sucht erst woertlich, dann normalisiert (ohne Backticks).
    Fallback: leerer String (NICHT ganze Prosa).
    """
    if not start:
        return ""
    # 1. Woertliche Suche.
    i_start = prosa.find(start)
    if i_start < 0:
        # 2. Normalisierte Suche.
        _p_norm = _normalisiere(prosa)
        _s_norm = _normalisiere(start)
        i_start_norm = _p_norm.find(_s_norm)
        if i_start_norm < 0:
            return ""
        # Position im Original: erstes Wort des Markers.
        _erstes_wort = start.split()[0] if start.split() else start
        i_start = prosa.find(_erstes_wort)
        if i_start < 0:
            return ""
    if not ende or ende == start:
        return prosa[i_start:]
    i_ende = prosa.find(ende, i_start + len(start))
    if i_ende < 0:
        _ende_wort = ende.split()[0] if ende.split() else ende
        i_ende = prosa.find(_ende_wort, i_start + len(start))
        if i_ende < 0:
            return prosa[i_start:]
    _result = prosa[i_start:i_ende + len(ende)]
    # K15c: Laengen-Begrenzung an Block-Format angepasst.
    # M-466 hatte 800 Zeichen (Mini-Task-Zeitalter). K15/K15b
    # produzieren ganze Funktions-Bloecke; 800 schnitt den
    # Konstruktor ab. 2500 = ~150-200 Zeilen Code.
    if len(_result) > 2500:
        _cut = _result.rfind(".", 0, 2500)
        if _cut > 0:
            _result = _result[:_cut + 1]
        else:
            _result = _result[:2500]
    return _result


def _llm_split_einzel_task(
    prosa: str, task: dict, api_key: str, pd, pn,
) -> list[dict]:
    """M-469: Zerlegt EINEN zu grossen Task in 2-3 Sub-Tasks (LLM)."""
    import json as _json
    _user = (
        f"## ZU GROSSER TASK:\n"
        f"id: {task.get('id')}\n"
        f"name: {task.get('name')}\n"
        f"description (Laenge {len(task.get('description', ''))}):\n"
        f"{task.get('description', '')[:3000]}\n\n"
        f"## ARCHITECT-PROSA (Kontext):\n{prosa[:4000]}"
    )
    reply = _with_spinner(
        f"Split-{task.get('id', '?')}",
        lambda: ask_llm(
            api_key, PLANNER_SPLIT_SINGLE_SYSTEM, _user,
            model="deepseek-chat", temperature=0.2, max_tokens=4000,
        ),
    )
    if not reply.ok:
        return []
    raw = reply.content.strip()
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start < 0 or end <= start:
        return []
    try:
        parsed = _json.loads(raw[start:end])
    except _json.JSONDecodeError:
        return []
    tasks_raw = parsed.get("tasks", [])
    if not isinstance(tasks_raw, list):
        return []
    out: list[dict] = []
    for i, t in enumerate(tasks_raw, 1):
        if not isinstance(t, dict):
            continue
        _start = t.get("architect_start") or ""
        _ende = t.get("architect_ende") or ""
        _abschnitt = _extrahiere_prosa_abschnitt(prosa, _start, _ende)
        if not _abschnitt and not _start:
            _tf = t.get("task_files") or task.get("task_files") or []
            _ziel = _tf[0] if _tf else ""
            if _ziel:
                for _seg in _segmentiere_nach_pfad(prosa):
                    if _seg["datei"] == _ziel or _seg["datei"].endswith("/" + _ziel) or _ziel.endswith(_seg["datei"]):
                        _abschnitt = _seg["prosa"]
                        break
        if not _abschnitt:
            _name = t.get("name") or ""
            _desc = t.get("description") or ""
            _abschnitt = f"## TASK: {_name}\n{_desc}" if _desc else _name
        # K19b: 2500 statt 800 -- konsistent mit K15c-Extraktor.
        if len(_abschnitt) > 2500:
            _cut = _abschnitt.rfind(".", 0, 2500)
            _abschnitt = _abschnitt[:_cut + 1] if _cut > 0 else _abschnitt[:2500]
        out.append({
            "id": t.get("id") or f"{task.get('id', 't')}_{i}",
            "name": t.get("name") or f"Sub {i}",
            "action": t.get("action", "update"),
            "task_files": t.get("task_files") or task.get("task_files") or [],
            "dependencies": t.get("dependencies") or [],
            "description": _abschnitt,
        })
    return out


def _korrigiere_aktion(task: dict, pd, pn: str) -> None:
    """K20: Korrigiert action anhand Datei-Existenz (deterministisch).

    - action='update' + Datei fehlt -> action='create'
    - action='create' + Datei existiert -> action='update'

    Mehrere task_files: pruefe JEDE. Bei gemischtem Zustand
    (manche existieren, manche nicht) -> keine Aenderung
    (unsicher, Architect oder Gate soll entscheiden).
    Audit-Eintrag pro Korrektur.
    """
    try:
        act = task.get("action", "update")
        if act not in ("update", "create"):
            return
        files = task.get("task_files") or []
        if not files or not isinstance(files, list):
            return
        from pathlib import Path as _P
        pd_path = _P(str(pd))
        zustaende = []
        for f in files:
            if not isinstance(f, str) or not f:
                return  # ungueltig, nicht anfassen
            zustaende.append((pd_path / f).is_file())
        if len(set(zustaende)) != 1:
            # Gemischt -- unsicher, nicht anfassen.
            return
        exists = zustaende[0]
        if act == "update" and not exists:
            task["action"] = "create"
            audit("planner_action_korrigiert", {
                "dateien": files, "von": "update", "nach": "create",
                "grund": "datei_fehlt",
            }, pd_path, pn)
        elif act == "create" and exists:
            task["action"] = "update"
            audit("planner_action_korrigiert", {
                "dateien": files, "von": "create", "nach": "update",
                "grund": "datei_existiert",
            }, pd_path, pn)
    except Exception:  # noqa: BLE001
        return


def _korrigiere_aktion_sequenziell(tasks: list[dict], pd, pn: str) -> None:
    """K20b: Beruecksichtigt Task-Reihenfolge.

    Problem: Architect plant t1=create + t2=create auf selber Datei.
    Sequentiell korrekt, aber K20 isoliert sieht beide als create
    (Datei fehlt beim Plan-Zeitpunkt).

    Fix: nach _korrigiere_aktion, iteriere in Reihenfolge.
    Merke 'wird angelegt bis Position'. Wenn Task an Position i
    auf Datei X create und X bereits (durch frueheren Task)
    angelegt wird -> update.
    """
    try:
        # Set: Datei wird bis jetzt angelegt.
        angelegt_bis: set[str] = set()
        for t in tasks:
            if not isinstance(t, dict):
                continue
            act = t.get("action", "update")
            files = t.get("task_files") or []
            if not isinstance(files, list):
                continue
            _alle_existieren = all(
                isinstance(f, str) and f in angelegt_bis
                for f in files
            )
            if act == "create" and _alle_existieren and files:
                t["action"] = "update"
                audit("planner_action_korrigiert", {
                    "dateien": files, "von": "create", "nach": "update",
                    "grund": "frueherer_task_legt_an",
                }, pd, pn)
            elif act == "create":
                for f in files:
                    if isinstance(f, str):
                        angelegt_bis.add(f)
    except Exception:  # noqa: BLE001
        return


def _merge_mini_tasks(tasks: list[dict], max_merged_len: int = 1800) -> list[dict]:
    """K15a: Merged benachbarte Tasks mit gleicher Zieldatei.

    Der LLM-Split zerlegt eine Funktion oft in 3-4 Mini-Tasks
    (Validierung / Kernlogik / Fehler / Rueckgabe). Keine ist
    allein reviewbar. Diese deterministische Nachbearbeitung merged
    aufeinanderfolgende Tasks mit gleicher task_files[0], solange
    die kombinierte desc_len <= max_merged_len bleibt.

    Andere Dateien und action-Wechsel (create <-> update) blocken
    den Merge.
    """
    if not tasks:
        return tasks

    # K41: zaehlt Merges pro Datei -- max 2 kombinierte Mini-Tasks
    # pro Zieldatei. Sonst entsteht ein Mega-Task (>200 Zeilen Code),
    # den der Builder nicht sauber baut.
    _merge_count: dict[str, int] = {}
    merged: list[dict] = []
    for t in tasks:
        if not merged:
            merged.append(dict(t))
            continue

        prev = merged[-1]
        prev_file = (prev.get("task_files") or [None])[0]
        cur_file = (t.get("task_files") or [None])[0]
        prev_act = prev.get("action", "update")
        cur_act = t.get("action", "update")

        same_file = prev_file is not None and prev_file == cur_file
        same_act = prev_act == cur_act
        combined_len = (
            len(prev.get("description", "")) + len(t.get("description", ""))
        )

        # K41: pro Datei max 2 Merges (d.h. max 2 Mini-Tasks zusammengefasst).
        _file_key = prev_file if isinstance(prev_file, str) else "_none_"
        _at_limit = _merge_count.get(_file_key, 0) >= 2

        if same_file and same_act and combined_len <= max_merged_len and not _at_limit:
            _merge_count[_file_key] = _merge_count.get(_file_key, 0) + 1
            # K36: Merge-Audit -- sichtbar machen, welche Tasks gemergt werden.
            _merge_audit = {
                "prev_id": prev.get("id"),
                "prev_file": prev_file,
                "prev_action": prev_act,
                "cur_id": t.get("id"),
                "cur_file": cur_file,
                "cur_action": cur_act,
                "combined_len": combined_len,
                "max_len": max_merged_len,
            }
            import sys
            print(f"[K36-MERGE] {_merge_audit}", file=sys.stderr)
            # Merge: Description anhaengen, architect_start behalten,
            # architect_ende auf den spaeteren Task setzen.
            prev["description"] = (
                prev.get("description", "").rstrip()
                + "\n\n"
                + t.get("description", "").lstrip()
            )
            if t.get("architect_ende"):
                prev["architect_ende"] = t["architect_ende"]
            _deps = set(prev.get("dependencies") or [])
            _deps.update(t.get("dependencies") or [])
            _deps.discard(prev.get("id"))
            prev["dependencies"] = sorted(_deps)
        else:
            # K36: Nicht-gemergt -- auch loggen.
            import sys
            print(
                f"[K36-KEEP] prev={prev.get('id')}({prev_file}) "
                f"cur={t.get('id')}({cur_file}) "
                f"same_file={same_file} same_act={same_act} "
                f"combined={combined_len}/{max_merged_len}",
                file=sys.stderr,
            )
            merged.append(dict(t))

    # IDs neu vergeben (t1..tN).
    for i, t in enumerate(merged, 1):
        t["id"] = f"t{i}"

    return merged


def _normalisiere_task_files(tasks, explorer_ctx, pd, pn) -> list:
    """K61a: Korrigiert task_files ohne Pfad-Praefix anhand key_files.

    Problem (Live 2026-10-29 14:16): Architect plante t5 mit
    task_files=["routes_state.py"], Builder fand die Datei nicht
    (sie liegt unter apps/dashboard/routes_state.py).

    Fail-closed bei Mehrdeutigkeit: mehrere Dateien mit gleichem
    Basisnamen -> unveraendert + audit, damit Builder meldet.
    """
    if not tasks:
        return tasks or []
    _basen: dict = {}
    for kf in (explorer_ctx or {}).get("key_files") or []:
        if isinstance(kf, dict):
            f = kf.get("file")
        elif isinstance(kf, str):
            f = kf
        else:
            continue
        if not f or "/" not in f:
            continue
        _basen.setdefault(f.rsplit("/", 1)[-1], []).append(f)
    for t in tasks:
        if not isinstance(t, dict):
            continue
        files = t.get("task_files") or []
        neu = []
        for f in files:
            if not isinstance(f, str) or not f:
                neu.append(f)
                continue
            if "/" in f:
                neu.append(f)
                continue
            treffer = _basen.get(f, [])
            if len(treffer) == 1:
                neu.append(treffer[0])
                audit("planner_task_files_korrigiert",
                      {"alt": f, "neu": treffer[0]}, pd, pn)
            elif len(treffer) > 1:
                neu.append(f)
                audit("planner_task_files_mehrdeutig",
                      {"name": f, "kandidaten": treffer}, pd, pn)
            else:
                neu.append(f)
        t["task_files"] = neu
    return tasks


def _zerlege_in_sub_tasks(
    prosa: str, key_files: list[str], api_key: str, pd, pn,
    aufgabe: str = "",
) -> list[dict]:
    """M-453: Zerlegt Architect-Prosa in 3-5 Sub-Tasks."""
    import json as _json
    _user = (
        f"## ARCHITECT-PROSA:\n{prosa}\n\n"
        f"## DATEIEN:\n" + "\n".join(f"- {f}" for f in key_files)
    )
    reply = _with_spinner(
        "Planner-Split",
        lambda: ask_llm(
            api_key, PLANNER_SPLIT_SYSTEM, _user,
            model="deepseek-chat", temperature=0.2, max_tokens=8000,
        ),
    )
    if not reply.ok:
        audit("planner_split_llm_fehler", {"fehler": reply.error}, pd, pn)
        return []
    raw = reply.content.strip()
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start < 0 or end <= start:
        audit("planner_split_json_fehler", {"raw": raw[:200]}, pd, pn)
        return []
    try:
        parsed = _json.loads(raw[start:end])
    except _json.JSONDecodeError:
        audit("planner_split_json_fehler", {"raw": raw[:200]}, pd, pn)
        return []
    tasks_raw = parsed.get("tasks", [])
    if not isinstance(tasks_raw, list):
        return []
    tasks: list[dict] = []
    for i, t in enumerate(tasks_raw, 1):
        if not isinstance(t, dict):
            continue
        _start = t.get("architect_start") or ""
        _ende = t.get("architect_ende") or ""
        # M-461: Woertlichen Prosa-Abschnitt extrahieren.
        _abschnitt = _extrahiere_prosa_abschnitt(prosa, _start, _ende)
        # GOLD: Wenn architect_start fehlt (Gold-Architect liefert
        # "## <pfad>"-Ueberschriften), deterministisch segmentieren.
        if not _abschnitt and not _start:
            _tf = t.get("task_files") or []
            _ziel = _tf[0] if _tf else ""
            if _ziel:
                for _seg in _segmentiere_nach_pfad(prosa):
                    if _seg["datei"] == _ziel or _seg["datei"].endswith("/" + _ziel) or _ziel.endswith(_seg["datei"]):
                        _abschnitt = _seg["prosa"]
                        break
        if not _abschnitt:
            # M-463: Fallback: Task-Name + Description, NICHT ganze Prosa.
            _name = t.get("name") or ""
            _desc = t.get("description") or ""
            _abschnitt = f"## TASK: {_name}\n{_desc}" if _desc else _name
        # K19b: Fallback 2500 statt 800 -- K15c-Konsistenz.
        if len(_abschnitt) > 2500:
            _cut = _abschnitt.rfind(".", 0, 2500)
            if _cut > 0:
                _abschnitt = _abschnitt[:_cut + 1]
            else:
                _abschnitt = _abschnitt[:2500]
        tasks.append({
            "id": t.get("id") or f"t{i}",
            "name": t.get("name") or f"Sub-Task {i}",
            "action": t.get("action", "update"),
            "task_files": t.get("task_files") or [],
            "dependencies": t.get("dependencies") or [],
            "description": _abschnitt,
        })
    # M-469: Rekursive Zerlegung (ADaPT). Tasks > 2500 Zeichen (K19b).
    # werden neu zerlegt (max 2 Ebenen tief).
    _final: list[dict] = []
    import re as _re_470
    for t in tasks:
        _desc = t.get("description", "")
        # K11: Tiefe und Komplexitaetsmetriken fuer den Haupt-Task.
        # Vorher waren die Tiefe, Schritte und Bullets
        # '_komplexitaet' undefiniert -> NameError >2000 Zeichen.
        _tiefe = int(t.get("split_tiefe", 0) or 0)
        _schritte = len(_re_470.findall(
            r"^\s*\d+\.", _desc, _re_470.MULTILINE
        ))
        _bullets = len(_re_470.findall(
            r"^\s+-\s", _desc, _re_470.MULTILINE
        ))
        _komplexitaet = _schritte + _bullets
        # M-472: On-Demand-Zerlegung (ADaPT). Keine praeventive
        # Komplexitaetspruefung mehr. Nur Sicherheitsnetz: > 2000 Zeichen.
        _zu_gross = len(_desc) > 2500
        if not _zu_gross or _tiefe >= 2:
            _final.append(t)
        else:
            audit("planner_task_zu_gross",
                  {"id": t.get("id"),
                   "desc_len": len(_desc),
                   "schritte": _schritte,
                   "bullets": _bullets,
                   "komplexitaet": _komplexitaet,
                   "tiefe": _tiefe}, pd, pn)
            _sub = _llm_split_einzel_task(prosa, t, api_key, pd, pn)
            if _sub:
                for _st in _sub:
                    _st_desc = _st.get("description", "")
                    _st_schritte = len(_re_470.findall(
                        r"^\s*\d+\.", _st_desc, _re_470.MULTILINE
                    ))
                    _st_bullets = len(_re_470.findall(
                        r"^\s+-\s", _st_desc, _re_470.MULTILINE
                    ))
                    _st_komplex = _st_schritte + _st_bullets
                    # K19b: 2500 statt 800 -- konsistent mit K15c.
                    _st_gross = len(_st_desc) > 2500 or _st_komplex > 4
                    if not _st_gross or _tiefe + 1 >= 2:
                        _final.append(_st)
                    else:
                        _sub2 = _llm_split_einzel_task(prosa, _st, api_key, pd, pn)
                        _final.extend(_sub2 or [_st])
            else:
                _final.append(t)

    # K61a: task_files normalisieren (Dateiname -> voller Pfad).
    # Vor K20, damit _korrigiere_aktion auf korrekten Pfaden arbeitet.
    _final = _normalisiere_task_files(
        _final, {"key_files": key_files}, pd, pn,
    )
    # K20: Action anhand Datei-Existenz korrigieren (vor Merge).
    for _t_korr in _final:
        if isinstance(_t_korr, dict):
            _korrigiere_aktion(_t_korr, pd, pn)
    # K20b: Sequentiell -- create auf Datei, die ein frueherer
    # Task bereits anlegt -> update.
    _korrigiere_aktion_sequenziell(_final, pd, pn)

    # K36: Vor-Merge-State loggen.
    audit("planner_split_vor_merge", {
        "anzahl": len(_final),
        "tasks": [
            {"id": t.get("id"), "name": t.get("name"),
             "files": t.get("task_files"), "action": t.get("action"),
             "desc_len": len(t.get("description", ""))}
            for t in _final if isinstance(t, dict)
        ],
    }, pd, pn)

    # K15a: deterministischer Merge benachbarter Mini-Tasks.
    _vor_merge = len(_final)
    _final = _merge_mini_tasks(_final)
    if len(_final) != _vor_merge:
        audit("planner_split_merged",
              {"vorher": _vor_merge, "nachher": len(_final)},
              pd, pn)

    audit("planner_split", {"anzahl": len(_final), "tasks": [
        {"id": t["id"], "files": t["task_files"],
         "desc_len": len(t.get("description", ""))} for t in _final
    ]}, pd, pn)
    return _doku_post_check(_final, prosa, pd, pn, aufgabe)




def _doku_post_check(
    tasks: list[dict], prosa: str, pd, pn,
    aufgabe: str = "",
) -> list[dict]:
    """FIX 2026-10-31 v2: Doku-Aufgaben deterministisch auf 1 Task reduzieren.

    Trigger: User-Auftrag enthaelt "nur"/"ausschliesslich"/"keine python"/
    "kein code" UND nennt .md oder docs/. Dann darf der Loop NICHT
    alle Explorer-Dateien als Tasks bauen.

    Live-Beleg 2026-10-30 23:03: 19 task_files fuer 1 Datei-Aufgabe
    (docs/STATUS.md), weil der Explorer Code-Pfade aus .md-Bodies
    extrahiert und der Split-LLM daraus Tasks macht.
    """
    if not tasks:
        return tasks
    _MD_SUFFIX = (".md", ".rst", ".txt")
    _aufgabe_lower = (aufgabe or "").lower()
    _prosa_lower = (prosa or "").lower()
    _both = _aufgabe_lower + " " + _prosa_lower
    _trigger_marker = ("nur", "ausschliesslich", "keine python",
                       "kein code", "nur doku", "keine code")
    _has_trigger = any(m in _both for m in _trigger_marker)
    _has_doku_ziel = (".md" in _aufgabe_lower or "docs/" in _aufgabe_lower
                      or "doku" in _aufgabe_lower)
    if not (_has_trigger and _has_doku_ziel):
        return tasks
    # FIX A v3 2026-10-31: Code-Tasks schuetzen. Wenn der Planner-Split
    # schon eine Code-Task gebaut hat, war das Absicht. Live-Beleg
    # 2026-10-30 23:48: t1=scripts/preflight_check.py wurde weggeworfen,
    # weil die Prosa das Wort "nur" enthielt.
    _CODE_SUFFIX_V3 = (
        ".py", ".sql", ".js", ".ts", ".html", ".css",
        ".yaml", ".yml", ".toml", ".json",
    )
    # Code-Task schuetzen NUR wenn:
    #   - action=create (Architect will neue Datei), ODER
    #   - Datei in der Aufgabe explizit genannt.
    # Sonst: Explorer-Muell (update-Task auf fremder .py-Datei).
    _aufgabe_v3 = aufgabe or ""
    def _ist_geschuetzter_code_task(_t: dict) -> bool:
        if not isinstance(_t, dict):
            return False
        _files = _t.get("task_files") or []
        _code = [f for f in _files
                 if isinstance(f, str) and f.endswith(_CODE_SUFFIX_V3)]
        if not _code:
            return False
        if _t.get("action") == "create":
            return True
        return any(f in _aufgabe_v3 for f in _code)
    _hat_code_task = any(_ist_geschuetzter_code_task(t) for t in tasks)
    if _hat_code_task:
        return tasks
    _md_tasks = [
        t for t in tasks
        if isinstance(t, dict)
        and any(
            isinstance(f, str) and f.endswith(_MD_SUFFIX)
            for f in (t.get("task_files") or [])
        )
    ]
    if not _md_tasks:
        audit("planner_doku_post_check_leer", {
            "original_task_count": len(tasks),
            "aufgabe_len": len(aufgabe or ""),
        }, pd, pn)
        return []
    if len(tasks) > 1:
        audit("planner_doku_post_check_reduziert", {
            "original_task_count": len(tasks),
            "md_task_count": len(_md_tasks),
            "behalten": _md_tasks[0].get("task_files"),
        }, pd, pn)
    return _md_tasks[:1]


def _deterministic_entfernen_precheck(state) -> bool:
    """FIX S 2026-10-31: 'entferne X aus Y' wenn X fehlt -> Skip.

    Scout erkennt per LLM nicht zuverlaessig, dass eine
    Entfernen-Aufgabe bereits erfuellt ist. Dieser Check
    laeuft deterministisch VOR dem Scout und spart den
    Architect+Planner-Lauf.

    Beispiele:
      'In docs/STATUS.md den Punkt 1 entfernen' +
      Datei hat Punkt 1 nicht -> Skip.
      'Entferne AuditReaderError aus docs/STATUS.md' +
      Datei enthaelt 'AuditReaderError' nicht -> Skip.
    """
    import re as _re_s
    _aufgabe = (getattr(state, "aufgabe", "") or "").strip()
    if not _aufgabe:
        return False
    _auf = _aufgabe.lower()
    # Trigger: Entfernen-Wort UND Punkt ODER Marker
    if not any(w in _auf for w in (
        "entfern", "loesch", "lösch", "raum ab", "räum ab",
        "rausnehmen", "raus nehmen",
    )):
        return False
    _pd = getattr(state, "project_dir", None)
    if _pd is None:
        return False
    _md_paths = _re_s.findall(r"[a-zA-Z_][\w/.-]*\.md", _aufgabe)
    if not _md_paths:
        return False
    _m_punkt = _re_s.search(r"punkt\s+(\d+)", _aufgabe, _re_s.IGNORECASE)
    _m_marker = _re_s.search(r"\(([A-Za-z][A-Za-z0-9_-]{3,})\)", _aufgabe)
    if not _m_punkt and not _m_marker:
        return False
    _pn = getattr(state, "project_name", "?")
    for _p_str in _md_paths:
        _target = Path(_pd) / _p_str
        if not _target.is_file():
            continue
        try:
            _content = _target.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if _m_punkt:
            _n = _m_punkt.group(1)
            if _re_s.search(rf"^\s*{_n}\.\s", _content, _re_s.MULTILINE):
                return False  # Punkt existiert noch
        if _m_marker:
            if _m_marker.group(1) in _content:
                return False  # Marker existiert noch
        try:
            state.auftrag_bereits_erfuellt = True  # type: ignore[attr-defined]
        except (AttributeError, TypeError):
            return False
        audit("planner_precheck_bereits_erfuellt", {
            "datei": _p_str,
            "punkt": _m_punkt.group(1) if _m_punkt else None,
            "marker": _m_marker.group(1) if _m_marker else None,
        }, _pd, _pn)
        return True
    return False


def _tasks_aus_betroffenen_stellen(
    scout_report: dict, aufgabe: str,
) -> list[dict]:
    """Fix AY (2026-10-31): Atomarer Plan -- 1 Task pro Datei.

    Aus scout_report["betroffene_stellen"] (Liste von Dicts mit
    datei/zeile/alt/neu/grund). Alle Stellen derselben Datei werden
    in EINEN Task zusammengefasst, damit der Builder sie in einem
    Rutsch patcht und der Verify-Pfad nur einmal nach dem letzten
    Patch testet.

    Kein Architect, kein Split. Der Scout hat die Stellen bereits
    exakt benannt.
    """
    _stellen = scout_report.get("betroffene_stellen") or []
    if not isinstance(_stellen, list) or not _stellen:
        return []

    # Gruppieren nach Datei
    _per_file: dict[str, list[dict]] = {}
    for _s in _stellen:
        if not isinstance(_s, dict):
            continue
        _f = _s.get("datei")
        if not isinstance(_f, str) or not _f:
            continue
        _per_file.setdefault(_f, []).append(_s)

    tasks: list[dict] = []
    for _idx, (_datei, _stellen_f) in enumerate(_per_file.items(), 1):
        _zeilen_text: list[str] = []
        for _s in _stellen_f:
            _zeile = _s.get("zeile")
            _alt = _s.get("alt", "")
            _neu = _s.get("neu", "")
            _grund = _s.get("grund", "")
            _z = f"Z. {_zeile}: " if _zeile else ""
            _zeilen_text.append(
                f"- {_z}ersetze `{_alt}` durch `{_neu}` ({_grund})"
            )
        _desc = (
            f"## {_datei}\n\n"
            f"Atomare Aenderung (Scout-Plan, kein Architect).\n"
            f"Alle Stellen in EINEM Rutsch ersetzen.\n"
            f"Kein Zwischenzustand testen -- erst nach dem letzten"
            f" Patch.\n\n"
            f"### Stellen ({len(_stellen_f)}):\n"
            + "\n".join(_zeilen_text)
        )
        tasks.append({
            "id": f"t{_idx}",
            "name": f"{_datei} atomar umstellen",
            "action": "update",
            "task_files": [_datei],
            "description": _desc,
        })

    # Wenn der Scout mehrere Dateien nennt: atomarer Plan ist
    # dann NICHT atomar -- warnen und leeren Plan liefern, der
    # Aufrufer faellt auf den Architect-Pfad zurueck.
    if len(tasks) > 1:
        return []

    return tasks


def run_planner(state: RunState) -> bool:
    """Erstellt den Plan. Schreibt in state.tasks/tests/akzeptanzkriterien."""
    pd = state.project_dir
    pn = state.project_name
    api_key = getattr(state, "api_key", "")
    
    if not api_key:
        audit("planner_kein_key", {}, pd, pn)
        return False

    # FIX S 2026-10-31: Deterministischer Pre-Check VOR dem Scout.
    # Wenn Aufgabe "entferne X" ist und X fehlt, Loop sauber beenden.
    if _deterministic_entfernen_precheck(state):
        return True

    aufgabe = getattr(state, "aufgabe", "")
    docs_ctx = ""
    if getattr(state, "docs", None):
        # FIX 2026-10-31 (Fix E): Bei Doku-Aufgaben ("nur X.md") nur
        # die betroffene .md + max 5 KB. Sonst: 3 Dateien, je 20 KB.
        _aufgabe_lower = (aufgabe or "").lower()
        # Phase 5e — vage Aufgaben: STATUS.md ist primaere Quelle.
        _VAGUE_KW = (
            "aufraeumen", "aufräumen", "naechster", "nächster",
            "was ist zu tun", "offene punkte", "todo", "to-do",
        )
        _ist_vage_task = any(kw in _aufgabe_lower for kw in _VAGUE_KW)
        _ist_doku_task = (
            ("nur" in _aufgabe_lower or "ausschliesslich" in _aufgabe_lower
             or "keine python" in _aufgabe_lower
             or "kein code" in _aufgabe_lower)
            and (".md" in _aufgabe_lower or "docs/" in _aufgabe_lower)
        )
        if _ist_doku_task:
            import re as _re_e
            _md_paths = _re_e.findall(
                r"[a-zA-Z_][\w/.-]*\.md", aufgabe or "",
            )
            _md_ziel = _md_paths[0] if _md_paths else ""
            _found = ""
            for _k, _v in state.docs.items():
                if _md_ziel and (_md_ziel in _v[:2000] or _md_ziel in _k):
                    _found = f"--- {_k} ---\n{_v[:5000]}"
                    break
            docs_ctx = _found
        elif _ist_vage_task and "status" in state.docs:
            # Phase 5e — bei vagen Aufgaben STATUS.md zuerst.
            docs_ctx = (
                f"--- status (PRIMAERE AUFGABENQUELLE) ---\n"
                f"{state.docs['status'][:20000]}\n\n"
            )
            _rest = [(k, v) for k, v in state.docs.items() if k != "status"][:2]
            if _rest:
                docs_ctx += "\n".join(
                    f"--- {k} ---\n{v[:5000]}" for k, v in _rest
                )
        else:
            docs_ctx = "\n".join(
                f"--- {k} ---\n{v[:20000]}"
                for k, v in list(state.docs.items())[:3]
            )

    user_content = f"Aufgabe: {aufgabe}\n\nKontext:\n{docs_ctx}"

    # K6: Abgeschlossene Punkte als Signal — verhindert Neu-Planen.
    _erledigt = _erledigte_punkte(getattr(state, "project_dir", None))
    if _erledigt:
        user_content += (
            "\n\n## BEREITS ERLEDIGT (NICHT neu planen):\n"
            + _erledigt[:3000]
        )

    # FIX AF 2026-10-31: Fehlschlaege aus vorherigem Lauf zeigen.
    # Bei --resume soll der Planner wissen, was schon gescheitert
    # ist, statt blind den gleichen Plan zu bauen.
    try:
        from werkstatt.phase_state import PhaseState as _PS_af
        _ps_af = _PS_af(pn, base_dir=Path(pd) / ".werkstatt")
        if _ps_af.exists() and _ps_af.load():
            _fails_af = [
                t for t in (_ps_af.data.get("tasks") or [])
                if isinstance(t, dict) and t.get("status") == "failed"
            ]
            if _fails_af:
                user_content += "\n\n## VORHERIGE FEHLSCHLAEGE:\n"
                for _f_af in _fails_af[:10]:
                    _fid = _f_af.get("id", "?")
                    _fname = (_f_af.get("name") or "")[:60]
                    _fg = _f_af.get("failure") or "unbekannt"
                    user_content += f"- {_fid} {_fname}: {_fg}\n"
                user_content += (
                    "\nBeruecksichtige diese Fehlschlaege im neuen Plan. "
                    "Wenn ein Fehlschlag auf eine fehlende Voraussetzung "
                    "hindeutet (z.B. Import fehlt, Datei fehlt), sorge "
                    "dafuer, dass die Voraussetzung zuerst gebaut wird.\n"
                )
    except Exception:  # noqa: BLE001, S110
        pass

    # M-375/M-376: Explorer-Kontext lesen (key_files + findings).
    _explorer_ctx = getattr(state, "explorer_context", None)
    if isinstance(_explorer_ctx, dict):
        _key = _explorer_ctx.get("key_files") or []
        _findings = _explorer_ctx.get("findings") or ""
        if _key or _findings:
            _key_names = [
                k.get("file") for k in _key
                if isinstance(k, dict) and k.get("file")
            ]
            user_content += "\n\nExplorer-Kontext:"
            if _findings:
                user_content += f"\nBefund: {_findings[:2000]}"
            if _key_names:
                user_content += f"\nRelevante Dateien: {_key_names}"
                user_content += (
                    "\nNutze diese Dateien als task_files. "
                    "Erfinde KEINE anderen Dateien."
                )

    # M-395: key_files-Inhalt lesen (max 3 Dateien, je max 2000 Zeichen).
    _key_files_content = ""
    if isinstance(_explorer_ctx, dict):
        _key = _explorer_ctx.get("key_files") or []
        _file_paths = [
            k.get("file") for k in _key[:3]
            if isinstance(k, dict) and k.get("file")
        ]
        for _fp in _file_paths:
            if not isinstance(_fp, str):
                continue
            _target = Path(pd) / _fp
            if not _target.is_file():
                continue
            try:
                _content = _target.read_text(encoding="utf-8")[:2000]
                _key_files_content += (
                    f"\n--- {_fp} ---\n{_content}\n"
                )
            except (OSError, UnicodeDecodeError):
                continue
        if _key_files_content:
            user_content += (
                "\n\nDatei-Inhalt (relevant, gekuerzt):"
                + _key_files_content
            )

    # M-307b: letzte 10 PROGRESS.md-Eintraege als Kontext.
    try:
        from werkstatt import progress as _progress
        progress_text = _progress.read_recent(pd, n=10)
        if progress_text:
            user_content += f"\n\nProjekt-Fortschritt (letzte 10):\n{progress_text}"
    except Exception:  # noqa: BLE001, S110
        pass  # PROGRESS.md nicht kritisch

    # M-310b: strukturierter Phase-State (wo bin ich jetzt).
    try:
        from werkstatt.phase_state import PhaseState
        _ps = PhaseState(pn, base_dir=pd / ".werkstatt")
        if _ps.exists() and _ps.load():
            _tasks_status = [
                {"id": t.get("id"), "name": t.get("name", ""),
                 "status": t.get("status"), "failure": t.get("failure")}
                for t in _ps.data.get("tasks", [])
            ]
            if _tasks_status:
                user_content += (
                    "\n\nPhase-State (aktueller Stand):\n"
                    + json.dumps(_tasks_status, ensure_ascii=False)
                )
    except Exception:  # noqa: BLE001, S110
        pass  # PhaseState nicht kritisch fuer Prompt

    # M-299e: Preflight-Fehler + Follow_up aus vorheriger Phase.
    preflight = getattr(state, "preflight_fehler", []) or []
    follow_up_prev = getattr(state, "follow_up_fehler", []) or []
    if preflight:
        user_content += (
            "\n\nPreflight-Fehler (aktuell):\n"
            + json.dumps(preflight[:10], ensure_ascii=False)
        )
    if follow_up_prev:
        user_content += (
            "\n\nFollow_up (vorherige Phase, neu bewerten):\n"
            + json.dumps(follow_up_prev[:10], ensure_ascii=False)
        )

    # M-349d: Planner-Info aus vorherigem _plan_gate-Fail.
    # Der Hook hat den Plan abgelehnt. Der Planner MUSS die Info
    # sehen, sonst plant er blind neu.
    # K17: Migrationsstand deterministisch in den Kontext.
    _mig_stand = _migrations_stand(pd)
    if _mig_stand:
        user_content += "\n\n" + _mig_stand

    _planner_info = getattr(state, "last_planner_info", None)
    if _planner_info:
        user_content += (
            "\n\n=== ABGELEHNT ===\n"
            f"Regel: {_planner_info.get('regel', '?')}\n"
            f"Fakt: {_planner_info.get('fakt', '?')}\n"
            f"Erklaerung: {_planner_info.get('erklaerung', '?')}\n"
            f"Details: {_planner_info.get('details', '?')}\n"
            "\n"
            "Der vorherige Plan wurde nicht gebaut.\n"
            "Antworte mit gueltigem JSON. "
        "GOLD: KEINE TOOL-CALLS. KEIN {\"tool\": ...}. "
        "Beginne deine Antwort mit '{' und ende mit '}'. "
        "Erst Dateien lesen, DANN planen -- in einer Antwort."
        )

    # M-398: Tool-Use-Loop (max 3 Runden).
    # GOLD: Tool-Use nur 1 Runde. Architect soll PLANEN, nicht
    # staendig Dateien lesen. Bei 3 Runden liefert er oft nur
    # Tool-Calls (DSML) statt Plan-JSON (Live 14:52).
    # === GOLD: Architect (Prosa) + Planner (JSON) ===
    # Der Architect liefert strukturierte Prosa. Der Planner
    # (_zerlege_in_sub_tasks) macht daraus Tasks. Zwei Calls,
    # zwei Agents -- kein Tool-Use, kein JSON/Prosa-Raetsel.

    # === GOLD: CALL 0 -- Scout (Code-Index + Auftrag) ===
    _code_index = _baue_api_index(pd)
    _key_files_scan: list[str] = []
    if isinstance(_explorer_ctx, dict):
        for _k in (_explorer_ctx.get("key_files") or []):
            if isinstance(_k, dict) and _k.get("file"):
                _kf = _k["file"]
                if _kf not in _key_files_scan:
                    _key_files_scan.append(_kf)
    _scout_report = _run_scout(
        state, aufgabe, _code_index, _key_files_scan, api_key,
    )

    # GOLD 2026-10-30: Scout kann "bereits_erfuellt" melden.
    # Dann brechen wir ab: kein Architect, kein Planner, kein Builder.
    if _scout_report and _scout_report.get("bereits_erfuellt") is True:
        _begr = _scout_report.get("begruendung_erfuellt", "")
        audit("auftrag_bereits_erfuellt",
              {"quelle": "scout",
               "begruendung": _begr[:300]}, pd, pn)
        # Flag fuer den Loop setzen
        state.auftrag_bereits_erfuellt = True  # type: ignore[attr-defined]
        return True

    if _scout_report:
        _scout_auftrag = _scout_report.get("auftrag_prosa") or ""
        _scout_apis = _scout_report.get("api_auszug") or {}
        _scout_risiken = _scout_report.get("risiken") or []
        if _scout_auftrag:
            user_content += (
                "\n\n## SCOUT-AUFTRAG (vorformuliert):\n"
                + _scout_auftrag[:3000]
            )
        if _scout_apis:
            _api_lines = []
            for _af, _asyms in list(_scout_apis.items())[:10]:
                _api_lines.append(f"-- {_af}")
                for _asym in (_asyms or [])[:20]:
                    _api_lines.append(f"   {_asym}")
            user_content += (
                "\n\n## VERFUEGBARE APIS (aus Code-Index):\n"
                + "\n".join(_api_lines)[:4000]
            )
        if _scout_risiken:
            user_content += (
                "\n\n## SCOUT-RISIKEN:\n"
                + "\n".join(f"- {r}" for r in _scout_risiken[:10])
            )

        # GOLD-Neu 2026-10-30: Widerspruchs-Check Auftrag vs Code-Index.
        _widersprueche = _pruefe_api_widerspruch(_scout_report, _code_index)
        if _widersprueche:
            audit("planner_scout_api_widerspruch",
                  {"anzahl": len(_widersprueche),
                   "widersprueche": _widersprueche[:10]}, pd, pn)
            _w_block = "\n".join(
                f"- {w['symbol']} ({w['art']}) -> "
                + (", ".join(w["gefunden_in"]) if w["gefunden_in"]
                   else "nicht im Code-Index")
                for w in _widersprueche[:10]
            )
            user_content += (
                "\n\n## API-WIDERSPRUCH (Auftrag nennt APIs,"
                " die so nicht existieren)\n"
                "Der Scout-Auftrag nennt folgende APIs. Der Code-Index"
                " kennt sie nicht oder nur in anderer Datei. Richte"
                " dich nach dem CODE-INDEX, nicht nach dem Auftrag:\n"
                + _w_block
            )

    # Fix AY (2026-10-31): Atomarer Plan -- Architect ueberspringen.
    # Der Scout hat betroffene_stellen exakt benannt und atomarer_plan
    # auf true gesetzt. Der Planner baut direkt EINEN Task pro Datei.
    if _scout_report and _scout_report.get("atomarer_plan") is True:
        _atom_tasks = _tasks_aus_betroffenen_stellen(_scout_report, aufgabe)
        if _atom_tasks:
            audit("planner_atomarer_plan",
                  {"tasks": len(_atom_tasks),
                   "dateien": [t["task_files"][0] for t in _atom_tasks]},
                  pd, pn)
            state.tasks = _atom_tasks  # type: ignore[attr-defined]
            # Marker, damit _plan_gate den Plan als gueltig sieht.
            state.architect_prosa = "[atomarer Plan vom Scout]"
            state.akzeptanzkriterien = list(
                getattr(state, "akzeptanzkriterien", []) or []
            )
            return True
        else:
            audit("planner_atomarer_plan_verworfen",
                  {"grund": "betroffene_stellen leer oder multi-file"},
                  pd, pn)

    # CALL 1: Architect (Fix AZ Stufe 10: ausgelagert nach architect.py)
    if not run_architect(state, aufgabe, user_content, api_key, _explorer_ctx):
        return False
    _arch_prosa = state.architect_prosa

    # CALL 2: Planner (JSON aus Prosa)
    _key_files: list[str] = []
    if isinstance(_explorer_ctx, dict):
        for k in (_explorer_ctx.get("key_files") or []):
            if isinstance(k, dict) and k.get("file"):
                _f = k["file"]
                if _f not in _key_files:
                    _key_files.append(_f)

    _sub_tasks = _zerlege_in_sub_tasks(
        _arch_prosa, _key_files, api_key, pd, pn,
        aufgabe=aufgabe,
    )

    if _sub_tasks:
        _sub_tasks = _normalisiere_task_files(
            _sub_tasks, _explorer_ctx, pd, pn,
        )
        state.tasks = _sub_tasks  # type: ignore[attr-defined]
    else:
        state.tasks = [{  # type: ignore[attr-defined]
            "id": "t1", "name": "Architect-Loesung umsetzen",
            "action": "update", "description": _arch_prosa,
            "task_files": _key_files,
        }]

    state.phasen = []  # type: ignore[attr-defined]
    state.tests = []  # type: ignore[attr-defined]
    state.akzeptanzkriterien = []  # type: ignore[attr-defined]

    audit("planner_plan_erstellt",
          {"tasks": len(state.tasks),
           "prosa_len": len(_arch_prosa)}, pd, pn)

    return bool(state.tasks)  # type: ignore[attr-defined]
