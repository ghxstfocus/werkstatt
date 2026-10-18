#!/usr/bin/env python3
"""Werkstatt-Audit: statische Analyse von pipeline.py und Umgebung.

Read-only. Aendert nichts. Liefert Markdown-Berichte
nach /opt/werkstatt/audit/.

Kein LLM, keine API. Reines ast + grep.
"""
from __future__ import annotations

import ast
import re
import sys
from collections import defaultdict
from pathlib import Path

WERKSTATT = Path("/opt/werkstatt")
PIPELINE = WERKSTATT / "pipeline.py"
OUT = WERKSTATT / "audit"


def _lies(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except OSError:
        return ""


def _schreibe(name: str, inhalt: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(inhalt, encoding="utf-8")
    print(f"[+] {name}: {len(inhalt)} Zeichen")


def _funktionen(tree: ast.Module) -> dict[str, ast.AST]:
    """Alle Top-Level- und Klassen-Funktionen."""
    fns: dict[str, ast.AST] = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            fns[node.name] = node
    return fns


def _aufrufe_in(fn: ast.AST) -> set[str]:
    """Alle Funktionsnamen, die in fn referenziert werden.

    A-B1-1 (2026-10-18): Erkennt auch ast.Name in
    Argument-Position (Funktion als Callback-Wert) und
    ast.Name im RHS einer Zuweisung (Handler-Dict).

    Grenzen: erkennt NICHT getattr(), functools.partial,
    dynamische Dispatch-Dicts mit spaeterem Aufruf,
    Dekorator-Registrierung, dynamische Imports.
    """
    aufrufe: set[str] = set()
    for node in ast.walk(fn):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                aufrufe.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                aufrufe.add(node.func.attr)
            # A-B1-1: Argumente, die ast.Name sind
            for arg in node.args:
                if isinstance(arg, ast.Name):
                    aufrufe.add(arg.id)
            # A-B1-1: kwargs-Werte, die ast.Name sind
            for kw in node.keywords:
                if isinstance(kw.value, ast.Name):
                    aufrufe.add(kw.value.id)
        # A-B1-1: RHS einer Zuweisung (Handler-Dict, Tabelle)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Subscript):
                    if isinstance(node.value, ast.Name):
                        aufrufe.add(node.value.id)
    return aufrufe


def _state_zugriffe(tree: ast.Module) -> tuple[
        dict[str, list[int]], dict[str, list[int]]]:
    """state.FELD: schreiben (Store) und lesen (Load)."""
    schreibt: dict[str, list[int]] = defaultdict(list)
    liest: dict[str, list[int]] = defaultdict(list)
    for node in ast.walk(tree):
        # state.FELD = ...  oder  state.FELD += ...
        if isinstance(node, ast.Attribute):
            if (isinstance(node.value, ast.Name)
                    and node.value.id in ("state", "s", "self")):
                # A-B1-1: state., s. und self. als Praefix.
                feld = node.attr
                ctx = type(node.ctx).__name__
                if "Store" in ctx or "Del" in ctx:
                    schreibt[feld].append(node.lineno)
                elif "Load" in ctx:
                    liest[feld].append(node.lineno)
    return dict(schreibt), dict(liest)


def _ask_llm_aufrufe(tree: ast.Module) -> list[dict]:
    """Jeder ask_llm()-Aufruf mit umgebender Funktion und Argumenten."""
    treffer: list[dict] = []
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for node in ast.walk(fn):
            if not isinstance(node, ast.Call):
                continue
            if not (isinstance(node.func, ast.Name)
                    and node.func.id == "ask_llm"):
                continue
            # Argumente: api_key, system_prompt, user_content,
            # model, temp, timeout, ...
            def _arg(i: int) -> str:
                if i < len(node.args):
                    a = node.args[i]
                    try:
                        return ast.unparse(a)
                    except Exception:
                        return "?"
                return "?"
            treffer.append({
                "funktion": fn.name,
                "zeile": node.lineno,
                "system_prompt": _arg(1),
                "user_content": _arg(2),
                "model": _arg(3),
                "max_tokens": _kwarg(node, "max_tokens"),
            })
    return treffer


def _kwarg(call: ast.Call, name: str) -> str:
    for kw in call.keywords:
        if kw.arg == name:
            try:
                return ast.unparse(kw.value)
            except Exception:
                return "?"
    return ""


def _audit_kinds_aufrufe(tree: ast.Module) -> dict[str, list[int]]:
    """Jedes audit("kind", ...): kind -> Zeilen."""
    kinds: dict[str, list[int]] = defaultdict(list)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not (isinstance(node.func, ast.Name)
                and node.func.id == "audit"):
            continue
        if node.args and isinstance(node.args[0], ast.Constant):
            k = node.args[0].value
            if isinstance(k, str):
                kinds[k].append(node.lineno)
    return dict(kinds)


def _returns(tree: ast.Module) -> list[dict]:
    """Jeder return mit Zahl/None/String: Funktion, Zeile, Wert."""
    treffer: list[dict] = []
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for node in ast.walk(fn):
            if not isinstance(node, ast.Return):
                continue
            if node.value is None:
                wert = "None"
            else:
                try:
                    wert = ast.unparse(node.value)[:60]
                except Exception:
                    wert = "?"
            treffer.append({
                "funktion": fn.name,
                "zeile": node.lineno,
                "wert": wert,
            })
    return treffer


def _tote_funktionen(tree: ast.Module) -> list[str]:
    """Top-Level-Funktionen, die nirgends referenziert werden.

    A-B1-1b (2026-10-18): Nutzt _aufrufe_in, damit
    Callback-Argumente mitgezaehlt werden. Vorher
    eigener, unvollstaendiger Walk.

    Grenzen: siehe 00-audit-grenzen.md.
    """
    definiert = set(_funktionen(tree).keys())
    fns = _funktionen(tree)
    aufgerufen: set[str] = set()
    for fn in fns.values():
        aufgerufen |= _aufrufe_in(fn)
    eingaenge = {"main", "run_pipeline", "run_phase", "__main__"}
    return sorted(definiert - aufgerufen - eingaenge)


def _commands(tree: ast.Module) -> dict[str, list[int]]:
    """COMMAND-IDs: jede Zuweisung einer Konstanten mit 'run' etc."""
    # Heuristik: Konstante COMMAND_*-IDs, dict-Literale, Strings
    return {}


def _datei_infos() -> list[dict]:
    """Groesse, Zeilen, Owner der wichtigen Dateien."""
    dateien = [
        PIPELINE,
        WERKSTATT / "werkstatt" / "state.py",
        WERKSTATT / "werkstatt" / "parser.py",
    ]
    for p in sorted((WERKSTATT / "agents").glob("*.md")):
        dateien.append(p)
    for p in sorted((WERKSTATT / "docs").glob("*.md")):
        dateien.append(p)
    infos: list[dict] = []
    for p in dateien:
        if not p.exists():
            continue
        st = p.stat()
        infos.append({
            "pfad": str(p.relative_to(WERKSTATT)),
            "zeilen": len(_lies(p).splitlines()),
            "bytes": st.st_size,
            "owner": f"{st.st_uid}:{st.st_gid}",
        })
    return infos


def _doku_widersprueche() -> list[str]:
    """Halb-automatisch: Doku-Claims, die gegen Code-Fakten
    geprueft werden koennen."""
    w: list[str] = []
    # Rollen-Anzahl
    readme = _lies(WERKSTATT / "README.md")
    arch = _lies(WERKSTATT / "docs" / "ARCHITEKTUR.md")
    agents = list((WERKSTATT / "agents").glob("*.md"))
    w.append(
        f"- agents/-Dateien: {len(agents)} "
        f"({', '.join(a.name for a in agents)})")
    if "sechs Rollen" in arch:
        w.append("- ARCHITEKTUR.md sagt 'sechs Rollen'")
    if "sieben Rollen" in readme:
        w.append("- README.md sagt 'sieben Rollen'")
    return w


def main() -> int:
    if not PIPELINE.exists():
        print(f"[FAIL] {PIPELINE} fehlt")
        return 1
    text = _lies(PIPELINE)
    tree = ast.parse(text, filename=str(PIPELINE))

    # 01 Funktionen
    fns = _funktionen(tree)
    lines = [f"# Funktionen ({len(fns)})\n",
             "| Funktion | Zeile |",
             "|---|---|"]
    for name, node in sorted(fns.items(),
                              key=lambda kv: kv[1].lineno):
        lines.append(f"| `{name}` | {node.lineno} |")
    _schreibe("01-funktionen.md", "\n".join(lines))

    # 02 Call-Graph
    lines = ["# Call-Graph\n", "Jede Funktion: direkte Aufrufe.\n"]
    for name, node in sorted(fns.items(),
                              key=lambda kv: kv[1].lineno):
        aufrufe = sorted(_aufrufe_in(node))
        if aufrufe:
            lines.append(f"## `{name}` (Z. {node.lineno})\n")
            for a in aufrufe:
                lines.append(f"  - `{a}`")
            lines.append("")
    _schreibe("02-call-graph.md", "\n".join(lines))

    # 03 State-Zugriffe
    schreibt, liest = _state_zugriffe(tree)
    alle = sorted(set(schreibt) | set(liest))
    lines = ["# RunState-Felder\n",
             "| Feld | schreibt | liest | Anzahl liest |",
             "|---|---|---|---|"]
    for feld in alle:
        s = schreibt.get(feld, [])
        l = liest.get(feld, [])
        lines.append(
            f"| `{feld}` | {len(s)} | {len(l)} | "
            f"{', '.join(map(str, l[:5]))}"
            f"{' ...' if len(l) > 5 else ''} |")
    _schreibe("03-state-zugriffe.md", "\n".join(lines))

    # 04 LLM-Aufrufe
    calls = _ask_llm_aufrufe(tree)
    lines = [f"# ask_llm-Aufrufe ({len(calls)})\n",
             "| Funktion | Zeile | Modell | System | User | max_tokens |",
             "|---|---|---|---|---|---|"]
    for c in sorted(calls, key=lambda x: x["zeile"]):
        lines.append(
            f"| `{c['funktion']}` | {c['zeile']} | "
            f"`{c['model']}` | `{c['system_prompt']}` | "
            f"`{c['user_content']}` | {c['max_tokens']} |")
    _schreibe("04-llm-aufrufe.md", "\n".join(lines))

    # 05 Audit-Kinds
    kinds = _audit_kinds_aufrufe(tree)
    lines = [f"# audit()-Kinds ({len(kinds)})\n",
             "| Kind | Aufrufe | Zeilen |",
             "|---|---|---|"]
    for k in sorted(kinds):
        lines.append(
            f"| `{k}` | {len(kinds[k])} | "
            f"{', '.join(map(str, kinds[k][:5]))}"
            f"{' ...' if len(kinds[k]) > 5 else ''} |")
    _schreibe("05-audit-kinds.md", "\n".join(lines))

    # 06 Returns
    rets = _returns(tree)
    lines = [f"# return-Werte ({len(rets)})\n",
             "| Funktion | Zeile | Wert |",
             "|---|---|---|"]
    for r in sorted(rets, key=lambda x: x["zeile"]):
        lines.append(
            f"| `{r['funktion']}` | {r['zeile']} | `{r['wert']}` |")
    _schreibe("06-returns.md", "\n".join(lines))

    # 07 Tote Funktionen
    tot = _tote_funktionen(tree)
    lines = [f"# Tote Funktionen ({len(tot)})\n",
             "Definiert, aber nirgends aufgerufen:\n"]
    for t in tot:
        node = fns[t]
        lines.append(f"- `{t}` (Z. {node.lineno})")
    _schreibe("07-tote-funktionen.md", "\n".join(lines))

    # 08 Datei-Infos
    infos = _datei_infos()
    lines = ["# Datei-Groessen und Owner\n",
             "| Datei | Zeilen | Bytes | Owner |",
             "|---|---|---|---|"]
    for i in infos:
        lines.append(
            f"| `{i['pfad']}` | {i['zeilen']} | "
            f"{i['bytes']} | {i['owner']} |")
    _schreibe("08-datei-infos.md", "\n".join(lines))

    # 09a Audit-Grenzen
    grenzen = [
        "# Audit-Grenzen (A-B1-1)\n",
        "Erkennt:",
        "- ast.Call-Namen (direkte Aufrufe)",
        "- ast.Attribute mit state./s./self.-Praefix",
        "- ast.Name in Argument-Position (Callbacks)",
        "- ast.Name im RHS von Handler-Dicts",
        "",
        "Erkennt NICHT:",
        "- getattr(obj, \"name\")-Dispatch",
        "- functools.partial",
        "- dynamische Dispatch-Dicts mit spaeterem Aufruf",
        "- Dekorator-basierte Registrierung",
        "- dynamische Imports",
        "",
        "Konsequenz: Der Audit ist 'besser als vorher',",
        "nicht 'vollstaendig'. Vor Loeschen: manuelle",
        "Sichtpruefung jeder 'toten' Funktion.",
    ]
    _schreibe("00-audit-grenzen.md", "\n".join(grenzen))

    # 09 Doku-Widersprueche
    w = _doku_widersprueche()
    lines = ["# Doku-Widersprueche (halb-automatisch)\n"] + w
    _schreibe("09-doku-widersprueche.md", "\n".join(lines))

    # 10 Skills
    skill_dir = WERKSTATT / "skills"
    lines = ["# Skills\n"]
    for p in sorted(skill_dir.glob("*/SKILL.md")):
        lines.append(f"- `{p.parent.name}` "
                     f"({len(_lies(p).splitlines())} Zeilen)")
    # Wo wird load_skill im Code angeboten?
    lines.append("\n## load_skill-Angebote im Code\n")
    for m in re.finditer(
            r"^(\d+):.*(load_skill|available_skills)",
            text, re.MULTILINE):
        lines.append(f"- Z. {m.group(1)}: `{m.group(2)}`")
    # In agents/*.md?
    lines.append("\n## load_skill in agents/*.md\n")
    for p in sorted((WERKSTATT / "agents").glob("*.md")):
        if "load_skill" in _lies(p):
            lines.append(f"- `{p.name}` erwaehnt load_skill")
        else:
            lines.append(f"- `{p.name}` erwaehnt load_skill NICHT")
    _schreibe("10-skills.md", "\n".join(lines))

    # 11 Prompt-Groessen
    lines = ["# Prompt-Groessen (statisch)\n",
             "| Funktion | Zeile | Prompt-Bausteine |",
             "|---|---|---|"]
    for fn_name in (
            "_builder_user_prompt", "_build_commit_input",
            "_build_judge_input", "_planner_user_content",
            "_solver_prompt_bauen", "_build_judge_prompt"):
        if fn_name not in fns:
            lines.append(f"| `{fn_name}` | — | (fehlt) |")
            continue
        node = fns[fn_name]
        bausteine = []
        for sub in ast.walk(node):
            if isinstance(sub, ast.Call):
                if isinstance(sub.func, ast.Name):
                    bausteine.append(sub.func.id)
                elif isinstance(sub.func, ast.Attribute):
                    bausteine.append(sub.func.attr)
        # doppelte raus
        uniq = sorted(set(bausteine))
        lines.append(
            f"| `{fn_name}` | {node.lineno} | "
            f"{', '.join(f'`{b}`' for b in uniq[:15])}"
            f"{' ...' if len(uniq) > 15 else ''} |")
    _schreibe("11-prompt-bausteine.md", "\n".join(lines))

    print(f"\n[+] Audit fertig. Berichte in {OUT}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
