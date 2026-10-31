"""Scout-Agent (Fix AZ Stufe 9, 2026-10-31).

Extrahiert aus planner.py. Formuliert einen Auftrag aus Aufgabe +
Code-Index + Explorer-Dateien. Re-Export in planner.py erhaelt
API-Kompatibilitaet.

Late-Binding-Proxies: _with_spinner, ask_llm, audit muessen ueber
werkstatt.planner aufgeloest werden, damit Test-Patches wirken.
"""
from __future__ import annotations

import json
from pathlib import Path


def audit(*args, **kwargs):
    """Late-Binding-Proxy fuer werkstatt.planner.audit."""
    from werkstatt.planner import audit as _orig
    return _orig(*args, **kwargs)


def _with_spinner(*args, **kwargs):
    """Late-Binding-Proxy fuer werkstatt.planner._with_spinner."""
    from werkstatt.planner import _with_spinner as _orig
    return _orig(*args, **kwargs)


def ask_llm(*args, **kwargs):
    """Late-Binding-Proxy fuer werkstatt.planner.ask_llm."""
    from werkstatt.planner import ask_llm as _orig
    return _orig(*args, **kwargs)


SCOUT_SYSTEM = """Du bist ein Scout.
Du formulierst einen Auftrag fuer den Architect.

## DEIN INPUT
- Die Aufgabe des Users (vage Idee).
- Der Code-Index (deterministisch aus AST): alle Module, Klassen,
  Funktionen, Signaturen, Imports.
- Die vom Explorer gemessenen Dateien.

## DEIN OUTPUT (JSON + Prosa)
{
  "ziel": "Was soll gebaut werden? (1-2 Saetze)",
  "relevante_dateien": [
    {"pfad": "...", "zeilen": [..], "warum": "..."}
  ],
  "api_auszug": {
    "pfad/der/datei.py": ["Klasse.method(args) -> return", "..."]
  },
  "vorgeschlagene_aenderungen": [
    "Neue Funktion _section_timeline in routes_state.py",
    "In dashboard_state additiv einbinden"
  ],
  "risiken": [
    "API X hat RBAC alert.view, nicht audit.read"
  ],
  "auftrag_prosa": "Ausformulierter Auftrag fuer den Architect (3-10 Saetze)"
}

## WICHTIG: WIDERSPRUCH-CHECK (STRIKT)

Der Auftrag nennt oft APIs, die es NICHT gibt (z.B. read_events()).
Pruefe JEDE im Auftrag genannte API gegen den Code-Index:

1. Ist die API im Code-Index? (Klasse, Methode, Signatur)
2. Wenn NICHT: als Risiko nennen.
3. Echte API suchen (aehnlicher Name, andere Klasse).
4. Im auftrag_prosa NUR echte APIs aus dem Code-Index nennen.

## BEISPIEL
- Auftrag sagt: "Nutze read_events(limit=15) aus core.audit_reader."
- Code-Index zeigt: "AuditReaderService.list_recent_assessments(actor, limit=100)"
- Risiko: "read_events existiert nicht in core.audit_reader. Echte API: AuditReaderService.list_recent_assessments"
- auftrag_prosa: "Nutze AuditReaderService.list_recent_assessments(principal, limit=15)"

## IST-ZUSTAND-CHECK (STRIKT, HOECHSTE PRIORITAET)

Der Code-Index zeigt nur Signaturen. Der "IST-ZUSTAND"-Block
enthaelt den tatsaechlichen Datei-Inhalt.

Pruefe JEDE Anforderung aus der Aufgabe gegen den IST-ZUSTAND:

1. Enthaelt die Zieldatei schon, was die Aufgabe verlangt?
2. Wenn JA (alle Anforderungen erfuellt): liefere
   "bereits_erfuellt": true, "begruendung_erfuellt": "...".
   Das ist der wichtigste Fall. Der Loop bricht dann ab.
3. Wenn NEIN: normales Vorgehen (Auftrag formulieren).

## ENTFERNEN-AUFGABEN (FIX 2026-10-31, Bug L)

Wenn die Aufgabe sagt "entferne X", "loesche X", "X rausnehmen":
- Pruefe im IST-ZUSTAND, ob X noch existiert.
- Wenn X NICHT mehr im IST-ZUSTAND steht: bereits_erfuellt: true.
- Wenn X noch da ist: bereits_erfuellt: false, normaler Auftrag.
- Beispiel: Aufgabe "entferne Punkt 1 (AuditReaderError) aus
  docs/STATUS.md". IST-ZUSTAND enthaelt Abschnitt "Offene Punkte"
  mit Punkten 2-7, aber KEINEN Punkt 1 zur AuditReaderError:
  -> bereits_erfuellt: true.
- Wenn der IST-ZUSTAND die Zieldatei NICHT enthaelt: kein Check
  moeglich, bereits_erfuellt: false.

Beispiel:
- Aufgabe: "Fuehre table-alerts in alerts.html ein."
- IST-ZUSTAND zeigt: `<table class="table table-alerts">`.
- -> bereits_erfuellt: true, begruendung: "alerts.html hat
  class='table table-alerts' schon (Zeile 70)."
- -> Loop bricht ab. Kein Architect, kein Planner, kein Builder.

## DEIN OUTPUT-FELD (NEU)

Zusaetzlich zu den bisherigen Feldern:
{
  "bereits_erfuellt": true|false,
  "begruendung_erfuellt": "Kurze Begruendung (1-3 Saetze)"
}

Wenn "bereits_erfuellt" fehlt: false (Default).

## REGEL
- Nenne NUR APIs, die im Code-Index stehen.
- Erfinde KEINE APIs.
- Uebernimm KEINE APIs aus dem Auftrag, wenn sie nicht im Code-Index sind.
- Nenne konkrete Zeilen und Datei-Pfade.
- IST-ZUSTAND-Check ist PFLICHT, wenn "IST-ZUSTAND" im Input steht.

## ATOMARER-PLAN (NEU 2026-10-31)

Wenn die Aenderung logisch ATOMAR ist (eine logische Aenderung,
auch wenn sie mehrere Stellen in derselben Datei trifft), setze:

  "atomarer_plan": true

und liste JEDE betroffene Stelle exakt:

  "betroffene_stellen": [
    {"datei": "tests/unit/test_chat.py",
     "zeile": 95,
     "alt": "default_model=\"llama3.2:3b\"",
     "neu": "default_model=MODEL_DEFAULT",
     "grund": "Konstante statt Literal"}
  ]

Wann ist eine Aenderung atomar?
- "Ersetze alle X durch Y" (auch 22 Stellen in einer Datei) -> ATOMAR.
- "Fuege X hinzu und passe alle Verwendungen an" -> ATOMAR.
- "Refactoring einer Datei" (mehrere konsistente Aenderungen) -> ATOMAR.
- "Mehrere unabhaengige Features" -> NICHT atomar.
- "Aenderung in mehreren Dateien mit je eigener Logik" -> NICHT atomar.

Wann NICHT atomar (atomarer_plan weglassen oder false):
- Aufgabe fordert mehrere neue Features.
- Mehrere Dateien mit unabhaengiger Aenderung.
- Neue Datei plus Aenderung bestehender Datei.

Bei atomarer_plan=true wird der Architect UEBERSPRUNGEN.
Der Planner baut EINEN Task pro betroffener Datei mit allen
Stellen. Der alte Zwischenzustand-Test (pytest nach jedem Task)
wird NICHT gefahren -- nur nach dem letzten Task.
Deshalb MUSS betroffene_stellen vollstaendig sein: fehlt eine
Stelle, ist die Datei halb umgestellt und der Test rot.

Wenn atomarer_plan=true, MUSS betroffene_stellen nicht leer sein.

## DEIN NACHFOLGER

Der Architect bekommt deinen Auftrag + die Datei-Inhalte und liefert Prosa.
Der Planner zerlegt in Tasks.
Der Builder baut pro Datei einen Patch.
"""


_SCOUT_NACHFOLGER_BLOCK = """## DEIN NACHFOLGER
Der Architect bekommt deinen `auftrag_prosa` + `api_auszug`.
Der Planner zerlegt seine Prosa in Tasks.
Der Builder baut pro Datei einen Patch.

WICHTIG: Du lieferst JSON (mit "auftrag_prosa" als Prosa-Text).
Der Architect liefert Prosa mit "## <pfad>"-Ueberschriften.
Du musst NICHT "## <pfad>" liefern -- nur den Auftrag formulieren.
"""


def _scout_system_with_nachfolger() -> str:
    """GOLD: SCOUT_SYSTEM + _SCOUT_NACHFOLGER_BLOCK."""
    return SCOUT_SYSTEM + "\n\n" + _SCOUT_NACHFOLGER_BLOCK


def _baue_api_index(project_dir) -> dict:
    """GOLD: Deterministischer API-Index (AST).

    Liefert fuer jede .py-Datei:
    - __all__ (falls vorhanden)
    - Klassen (mit Methoden + Signaturen)
    - Top-Level-Funktionen (mit Signaturen + Rueckgabetypen)
    - Imports (from X import Y)
    """
    import ast as _ast
    from pathlib import Path as _Path

    _pd = _Path(project_dir)
    _ignore = {
        ".venv", "venv", "__pycache__", "site-packages",
        "node_modules", ".git", ".tox", ".mypy_cache",
        ".pytest_cache", ".ruff_cache", ".eggs", "build", "dist",
    }
    index: dict = {}
    for _f in _pd.rglob("*.py"):
        if any(p in _ignore for p in _f.parts):
            continue
        try:
            _src = _f.read_text(encoding="utf-8", errors="replace")
            _tree = _ast.parse(_src)
        except (OSError, SyntaxError):
            continue
        _rel = str(_f.relative_to(_pd))
        _entry = {
            "all": [],
            "classes": [],
            "functions": [],
            "imports": [],
        }
        for _node in _tree.body:
            if isinstance(_node, _ast.Assign):
                for _t in _node.targets:
                    if isinstance(_t, _ast.Name) and _t.id == "__all__":
                        try:
                            _val = _ast.literal_eval(_node.value)
                            _entry["all"] = list(_val) if isinstance(_val, (list, tuple)) else []
                        except (ValueError, SyntaxError):
                            pass
            elif isinstance(_node, _ast.ClassDef):
                _methods = []
                for _m in _node.body:
                    if isinstance(_m, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
                        _args = [a.arg for a in _m.args.args]
                        _ret = ""
                        if _m.returns:
                            try:
                                _ret = _ast.unparse(_m.returns)
                            except (AttributeError, ValueError):
                                pass
                        _methods.append({
                            "name": _m.name,
                            "args": _args,
                            "return": _ret,
                        })
                _entry["classes"].append({
                    "name": _node.name,
                    "methods": _methods,
                })
            elif isinstance(_node, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
                _args = [a.arg for a in _node.args.args]
                _ret = ""
                if _node.returns:
                    try:
                        _ret = _ast.unparse(_node.returns)
                    except (AttributeError, ValueError):
                        pass
                _entry["functions"].append({
                    "name": _node.name,
                    "args": _args,
                    "return": _ret,
                })
            elif isinstance(_node, _ast.ImportFrom):
                _mod = _node.module or ""
                _names = [a.name for a in _node.names]
                _entry["imports"].append({
                    "from": _mod,
                    "names": _names,
                })
            elif isinstance(_node, _ast.Import):
                for _a in _node.names:
                    _entry["imports"].append({"import": _a.name})
        index[_rel] = _entry
    return index


def _format_api_index_for_prompt(index: dict, max_files: int = 40) -> str:
    """Deterministisch: API-Index -> Prompt-Text."""
    lines = []
    for i, (f, info) in enumerate(index.items()):
        if i >= max_files:
            lines.append(f"... und {len(index) - max_files} weitere Dateien")
            break
        _parts = []
        if info.get("all"):
            _parts.append(f"__all__: {', '.join(info['all'][:8])}")
        for _c in info.get("classes", [])[:5]:
            _methods = ", ".join(m["name"] for m in _c["methods"][:8])
            _parts.append(f"class {_c['name']}({_methods})")
        for _fn in info.get("functions", [])[:5]:
            _args = ", ".join(_fn["args"])
            _ret = f" -> {_fn['return']}" if _fn["return"] else ""
            _parts.append(f"def {_fn['name']}({_args}){_ret}")
        _sig = " | ".join(_parts) if _parts else "(kein oeffentliches API)"
        lines.append(f"- {f}: {_sig}")
    return "\n".join(lines)


def _finde_api(index: dict, name: str) -> list:
    """Deterministisch: sucht eine API (Funktion/Klasse/Methode) im Index."""
    _matches = []
    for _pfad, _info in index.items():
        for _fn in _info.get("functions", []):
            if _fn["name"] == name:
                _matches.append({
                    "pfad": _pfad,
                    "kind": "function",
                    "name": _fn["name"],
                    "args": _fn["args"],
                    "return": _fn["return"],
                })
        for _c in _info.get("classes", []):
            if _c["name"] == name:
                _matches.append({
                    "pfad": _pfad,
                    "kind": "class",
                    "name": _c["name"],
                    "methods": [m["name"] for m in _c["methods"]],
                })
            for _m in _c["methods"]:
                if _m["name"] == name:
                    _matches.append({
                        "pfad": _pfad,
                        "kind": "method",
                        "class": _c["name"],
                        "name": _m["name"],
                        "args": _m["args"],
                        "return": _m["return"],
                    })
    return _matches


def _pruefe_api_widerspruch(
    scout_report: dict | None, code_index: dict,
) -> list[dict]:
    """GOLD-Neu 2026-10-30: prueft Scout-Auftrag gegen Code-Index.

    Deterministisch. Kein LLM, keine Seiteneffekte.

    Prueft jede (datei, symbol) aus scout_report["api_auszug"]
    gegen _finde_api(code_index, symbol).

    Befund-Arten:
    - "fehlt":     symbol nicht im Code-Index.
    - "verschoben": symbol existiert, aber NICHT in datei.

    Rueckgabe: list[dict] mit {"datei", "symbol", "art",
    "gefunden_in"}. Leer, wenn kein Widerspruch.

    Der Aufrufer (run_planner) entscheidet, was mit den
    Befunden passiert (Audit + Prompt-Block, kein Verwerfen).
    """
    if not isinstance(scout_report, dict):
        return []
    _api_auszug = scout_report.get("api_auszug") or {}
    if not isinstance(_api_auszug, dict):
        return []
    if not isinstance(code_index, dict):
        return []

    befunde: list[dict] = []
    for _datei, _symbole in _api_auszug.items():
        if not isinstance(_datei, str):
            continue
        if not isinstance(_symbole, (list, tuple)):
            continue
        for _sym in _symbole:
            if not isinstance(_sym, str) or not _sym:
                continue
            _treffer = _finde_api(code_index, _sym)
            if not _treffer:
                befunde.append({
                    "datei": _datei,
                    "symbol": _sym,
                    "art": "fehlt",
                    "gefunden_in": [],
                })
                continue
            _pfade = sorted({_t["pfad"] for _t in _treffer})
            if _datei in _pfade:
                continue  # Erwartet: Treffer in der genannten Datei.
            befunde.append({
                "datei": _datei,
                "symbol": _sym,
                "art": "verschoben",
                "gefunden_in": _pfade,
            })
    return befunde


def _run_scout(
    state, aufgabe: str, code_index: dict,
    key_files: list, api_key: str,
) -> dict | None:
    """GOLD: Scout-Call (deepseek-chat). Liefert strukturierten Auftrag.

    Deterministisch: Code-Index aus AST.
    LLM: formuliert Auftrag (Ziel, relevante Dateien, API, Risiken).
    """
    import json as _json
    pd = state.project_dir
    pn = state.project_name

    _index_str = _format_api_index_for_prompt(code_index, max_files=40)
    _files_str = "\n".join(f"- {f}" for f in (key_files or [])[:20])

    # GOLD 2026-10-30: Datei-Inhalte aus explorer_context holen.
    # Ohne Inhalt kann der Scout nicht pruefen, ob die Aufgabe
    # schon erfuellt ist.
    _previews_parts = []
    _explorer_ctx = getattr(state, "explorer_context", None)
    if isinstance(_explorer_ctx, dict):
        for _k in (_explorer_ctx.get("key_files") or [])[:8]:
            if not isinstance(_k, dict):
                continue
            _pf = _k.get("file", "")
            _pv = _k.get("preview", "")
            if _pf and _pv:
                _previews_parts.append(
                    f'<datei_inhalt datei="{_pf}">\n{_pv[:8000]}\n</datei_inhalt>'
                )
    _previews_str = "\n\n".join(_previews_parts)

    user_content = (
        f"## AUFGABE\n{aufgabe}\n\n"
        f"## CODE-INDEX (Module/Klassen/Funktionen)\n{_index_str}\n\n"
        f"## EXPLORER-DATEIEN\n{_files_str}\n"
    )
    if _previews_str:
        user_content += (
            f"\n\n## IST-ZUSTAND (Inhalt der genannten Dateien)\n"
            f"{_previews_str}\n"
        )
    reply = _with_spinner(
        "Scout",
        lambda: ask_llm(
            api_key, _scout_system_with_nachfolger(), user_content,
            model="deepseek-chat", temperature=0.2, max_tokens=4000,
            aufgabe="scout",
        ),
    )
    if not reply.ok:
        audit("planner_scout_llm_fehler", {"fehler": reply.error}, pd, pn)
        return None
    raw = reply.content.strip()
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start < 0 or end <= start:
        audit("planner_scout_json_fehler", {"raw": raw[:200]}, pd, pn)
        return None
    try:
        parsed = _json.loads(raw[start:end])
    except _json.JSONDecodeError:
        audit("planner_scout_json_fehler", {"raw": raw[:200]}, pd, pn)
        return None
    if not isinstance(parsed, dict):
        return None
    audit("planner_scout_ok",
          {"dateien": len(parsed.get("relevante_dateien") or []),
           "risiken": len(parsed.get("risiken") or [])}, pd, pn)
    return parsed


__all__ = [
    'SCOUT_SYSTEM',
    '_SCOUT_NACHFOLGER_BLOCK',
    '_baue_api_index',
    '_finde_api',
    '_format_api_index_for_prompt',
    '_pruefe_api_widerspruch',
    '_run_scout',
    '_scout_system_with_nachfolger',
]
