"""Explorer-Subagent. Read-only. Deterministische Messung VOR dem LLM.

M-338-Fix: Der Explorer MESS'T zuerst (ruff, pytest), extrahiert
die Dateien, und liefert sie als key_files. Das LLM formuliert
nur noch findings. Kein Raten.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

from werkstatt.agent import ask_llm
from werkstatt.audit import audit
from werkstatt.skills import load_all_skills, load_skill_by_name
from werkstatt.state import RunState
from werkstatt.tools import run_readonly

EXPLORER_SYSTEM = """Du bist ein read-only Codebase-Explorer.

WICHTIG (M-338-Fix):
  - Wenn die Aufgabe eine Messung verlangt (ruff-Fehler,
    Test-Fehler, Bug), hast du die Messung BEREITS erhalten
    (siehe "Messungen" im Kontext). Nutze sie.
  - Rate NICHT. Die Dateien aus der Messung sind deine
    key_files.
  - Wenn keine Messung moeglich war und keine Datei explizit
    in der Aufgabe genannt ist: key_files = [].

Antworte NUR mit validem JSON:
{
  "findings": "Kurze Zusammenfassung",
  "key_files": [{"file": "pfad/datei.py", "why": "warum", "symbols": "symbole", "confidence": "high|medium|low"}],
  "next_reads": ["pfad/datei.py"]
}
Keine Erklaerung, nur JSON."""


def _list_py_files(project_dir: Path, max_files: int = 200) -> list[str]:
    try:
        res = subprocess.run(
            ["find", str(project_dir), "-name", "*.py", "-type", "f",
             "-not", "-path", "*/.venv/*", "-not", "-path", "*/__pycache__/*"],
            capture_output=True, text=True, timeout=30, check=False,
        )
        return [f for f in res.stdout.split("\n") if f.strip()][:max_files]
    except Exception:  # noqa: BLE001
        return []


def _extract_dateien(stdout: str) -> list[str]:
    """Extrahiert Dateipfade aus ruff-concise-Output.

    Format: 'pfad/datei.py:zeile:spalte: CODE message'
    """
    dateien: list[str] = []
    for line in stdout.splitlines():
        m = re.match(r"^([^:\s]+\.py):", line)
        if m:
            d = m.group(1)
            if d not in dateien:
                dateien.append(d)
    return dateien



def _verwandte_dateien(project_dir: Path, dateien: list[str]) -> list[str]:
    """M-396-Fix: Findet verwandte Dateien zu explizit genannten.

    Nachbarn = gleicher Ordner (*.py), __init__.py, models.py,
    sowie Test-Dateien, die den Modul-Stamm enthalten.
    """
    verwandt: list[str] = []
    gesehen: set[str] = set(dateien)
    for rel in dateien:
        p = project_dir / rel
        if not p.exists():
            continue
        # 1. Gleicher Ordner: alle *.py.
        for nachbar in sorted(p.parent.glob("*.py")):
            nrel = str(nachbar.relative_to(project_dir))
            if nrel not in gesehen:
                gesehen.add(nrel)
                verwandt.append(nrel)
        # 2. Tests, die den Modul-Stamm nennen.
        stamm = p.stem
        tests_dir = project_dir / "tests"
        if tests_dir.exists():
            for t in tests_dir.rglob(f"*{stamm}*.py"):
                trel = str(t.relative_to(project_dir))
                if trel not in gesehen:
                    gesehen.add(trel)
                    verwandt.append(trel)
    return verwandt[:10]


def _messen(frage: str, project_dir: Path) -> dict[str, Any]:
    """M-373: Deterministische Messung VOR dem LLM.

    Fuehrt basierend auf der Aufgabe die passenden Befehle aus.
    """
    results: dict[str, Any] = {}
    frage_lower = frage.lower()

    if "ruff" in frage_lower:
        r = run_readonly("ruff check . --output-format=concise", project_dir)
        results["ruff"] = {
            "ok": r.get("ok", False),
            "stdout": r.get("stdout", "")[:5000],
            "stderr": r.get("stderr", "")[:1000],
            "dateien": _extract_dateien(r.get("stdout", "")),
        }

    # M-393: pytest nur bei explizitem Test-Fehler-Trigger.
    # 'offene Tests' oder 'Test-Suite' soll NICHT die Vollsuite starten.
    _pytest_trigger = (
        "pytest", "testfehler", "roter test",
        "test schlaegt fehl", "test fail", "failing test",
    )
    if any(w in frage_lower for w in _pytest_trigger):
        r = run_readonly("pytest -q", project_dir)
        results["pytest"] = {
            "ok": r.get("ok", False),
            "stdout": r.get("stdout", "")[:3000],
            "stderr": r.get("stderr", "")[:1000],
        }

    # M-392: Doku-Exploration — offene Punkte, Roadmap, Status
    _doku_trigger = (
        "offene", "todo", "naechste", "roadmap", "status",
        "was fehlt", "was ist offen", "unvollstaendig",
        "finde", "durchsuche",
    )
    if any(w in frage_lower for w in _doku_trigger):
        r = run_readonly(
            "grep -rn Offen docs/ --include=*.md",
            project_dir,
        )
        results["docs_offen"] = {
            "ok": r.get("ok", False),
            "stdout": r.get("stdout", "")[:5000],
            "stderr": r.get("stderr", "")[:500],
            "dateien": _extract_dateien(r.get("stdout", "")),
        }
        r2 = run_readonly("cat docs/STATUS.md", project_dir)
        results["status"] = {
            "ok": r2.get("ok", False),
            "stdout": r2.get("stdout", "")[:3000],
            "stderr": r2.get("stderr", "")[:500],
            # K31c: status muss auch als .md-Datei markiert werden,
            # damit _extrahiere_pfade laeuft.
            "dateien": ["docs/STATUS.md"] if r2.get("ok") else [],
        }

    # K31b: Migrations-Stand IMMER messen (kostet 2ms, nuetzt immer).
    _mig = _migrations_stand(project_dir)
    if _mig:
        results["migrations"] = {
            "ok": True,
            "hoechste": _mig["hoechste"],
            "naechste": _mig["naechste"],
            "alle": _mig["alle"],
            "dateien": _mig["dateien"],
            "stdout": (
                f"Migrationsstand: hoechste {_mig['hoechste']}, "
                f"naechste frei {_mig['naechste']}"
            ),
        }

    # K54: Pfade aus der Aufgabe selbst extrahieren. Die Aufgabe
    # nennt oft explizit Zieldateien (z.B. "Timeline in dashboard.js
    # und routes_state.py"). Diese Dateien MUSS der Architect sehen,
    # auch wenn STATUS.md sie nicht referenziert.
    _aufgabe_pfade: list[str] = []
    _seen_ap: set[str] = set()
    for m in _CODE_PATH_RE.finditer(frage):
        _pf = m.group(1)
        if _pf in _seen_ap:
            continue
        # K61c: kurzen Aufgabe-Pfad gegen Projekt auflösen.
        # Auftrag sagt oft nur "routes_state.py", echte Datei
        # liegt unter apps/dashboard/. rglob findet sie.
        _target = Path(project_dir) / _pf
        if not _target.is_file():
            _candidates = [
                p for p in Path(project_dir).rglob(_pf)
                if p.is_file()
                and ".venv" not in p.parts
                and ".git" not in p.parts
            ]
            if len(_candidates) == 1:
                _target = _candidates[0]
                try:
                    _pf = str(_target.relative_to(project_dir))
                except ValueError:
                    pass
        if _target.is_file():
            _aufgabe_pfade.append(_pf)
            _seen_ap.add(_pf)
        if len(_aufgabe_pfade) >= 20:
            break
    if _aufgabe_pfade:
        results["aufgabe_pfade"] = {
            "ok": True,
            "dateien": _aufgabe_pfade,
            "stdout": (
                "Aus der Aufgabe genannte existierende Dateien:\n"
                + "\n".join(f"  - {f}" for f in _aufgabe_pfade)
            ),
        }



    return results


def _format_findings(messungen: dict[str, Any]) -> str:
    """Formatiert die Messungen als Klartext fuer den Planner."""
    lines = []
    for name, m in messungen.items():
        # K31d: Migrations-Stand prominent rendern.
        if name == "migrations" and m.get("hoechste"):
            lines.append(
                f"migrations: hoechste belegt {m['hoechste']}, "
                f"naechste frei {m['naechste']}"
            )
            if m.get("dateien"):
                lines.append(f"  Dateien: {', '.join(m['dateien'])}")
            continue
        # K54: Aufgabe-Pfade als eigener Block.
        if name == "aufgabe_pfade":
            _files = m.get("dateien") or []
            lines.append(
                f"aufgabe_pfade: {len(_files)} in der Aufgabe genannte "
                f"Datei(en) existieren:"
            )
            for _f in _files:
                lines.append(f"  - {_f}")
            continue
        n = len(m.get("dateien", []))
        if n > 0:
            lines.append(f"{name}: {n} Datei(en) betroffen")
            lines.append(f"  Dateien: {', '.join(m['dateien'])}")
        else:
            lines.append(f"{name}: {m.get('stdout', '')[:200] or '(keine)'}")
        if m.get("stdout") and n == 0:
            lines.append(f"  Ausgabe: {m['stdout'][:800]}")
    return "\n".join(lines)


def _explorer_system(frage: str) -> str:
    """Haengt systematic-debugging + using-werkstatt an."""
    skills = load_all_skills()
    parts = [EXPLORER_SYSTEM]
    # Meta-Skill IMMER
    uw = load_skill_by_name("using-werkstatt", skills)
    if uw and uw["body"]:
        parts.append("## Skill: Using-Werkstatt\n" + uw["body"])
    # systematic-debugging bei Trigger
    trigger = ("ruff", "test", "bug", "fehler", "debug", "pytest")
    if any(w in frage.lower() for w in trigger):
        sd = load_skill_by_name("systematic-debugging", skills)
        if sd and sd["body"]:
            parts.append("## Skill: Systematic-Debugging\n" + sd["body"])
    return "\n\n".join(parts)


# K31a: Pfad-Regex fuer Code-Dateien aus Doku (.py, .sql, .html, .css, .js).
# Nicht .md (Doku) und nicht .yaml/.json (Config).
_CODE_PATH_RE = __import__("re").compile(
    r"\b([a-zA-Z_][\w/.-]*\.(?:py|sql|html|css|js))\b"
)


def _extrahiere_pfade(project_dir: Path, md_datei: str) -> list[str]:
    """K31: Extrahiert Pfade aus .md-Datei.

    K31a: auch .sql/.html/.css/.js (vorher nur .py).
    K31:  max 30 Pfade (vorher 15).
    """
    try:
        text = (Path(project_dir) / md_datei).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    pfade: list[str] = []
    seen: set[str] = set()
    for m in _CODE_PATH_RE.finditer(text):
        pfad = m.group(1)
        if pfad in seen:
            continue
        if (Path(project_dir) / pfad).is_file():
            pfade.append(pfad)
            seen.add(pfad)
        if len(pfade) >= 30:
            break
    return pfade


def _datei_inhalt(
    project_dir: Path, rel: str,
    suchbegriffe: list[str] | None = None,
) -> str:
    """K31: Dateiinhalt fuer Explorer-Kontext.

    - <= 200 Zeilen: komplett.
    - > 200 Zeilen mit suchbegriffen: relevante Zeilen (100 davor +
      100 danach um jeden Treffer).
    - > 200 Zeilen ohne suchbegriffe: erste 100 + letzte 50.
    - Binaer/Fehler: "".
    """
    try:
        f = Path(project_dir) / rel
        if not f.is_file():
            return ""
        text = f.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        if len(lines) <= 200:
            return text

        # GOLD 2026-10-30: Relevante Zeilen um Suchbegriffe.
        # Live-Beleg: components.css (966 Zeilen) enthielt
        # nth-child bei Zeile 462, aber _datei_inhalt lieferte
        # nur erste 100 + letzte 50 -> Architect sah die
        # Tabellen-Regeln nicht.
        if suchbegriffe:
            treffer_zeilen: set[int] = set()
            for i, line in enumerate(lines):
                for begriff in suchbegriffe:
                    if begriff and begriff in line:
                        treffer_zeilen.add(i)
                        break
            if treffer_zeilen:
                # 100 Zeilen vor + 100 Zeilen nach jedem Treffer
                zeige: set[int] = set()
                for tz in treffer_zeilen:
                    start = max(0, tz - 100)
                    ende = min(len(lines), tz + 100)
                    zeige.update(range(start, ende))
                # Sortiert ausgeben, mit Truncation-Marker
                sortiert = sorted(zeige)
                teile: list[str] = []
                letzte = -2
                for i in sortiert:
                    if i > letzte + 1:
                        if teile:
                            teile.append(
                                f"[... {i - letzte - 1} Zeilen "
                                f"uebersprungen ...]"
                            )
                    teile.append(lines[i])
                    letzte = i
                return "\n".join(teile)

        # Fallback: erste 100 + letzte 50
        _skip = len(lines) - 150
        return (
            "\n".join(lines[:100])
            + f"\n[... {_skip} Zeilen gekuerzt ...]\n"
            + "\n".join(lines[-50:])
        )
    except (OSError, UnicodeDecodeError):
        return ""


def _migrations_stand(project_dir: Path) -> dict:
    """K31: Migrations-Inhalt immer listen.

    Rueckgabe: {hoechste: "0018", naechste: "0019",
                alle: ["0004", ..., "0018"],
                dateien: ["0018_x.sql", ...]}
    Leer wenn data/migrations/ fehlt.
    """
    mdir = Path(project_dir) / "data" / "migrations"
    if not mdir.is_dir():
        return {}
    try:
        files = sorted(f.name for f in mdir.glob("*.sql") if f.is_file())
    except OSError:
        return {}
    if not files:
        return {}
    nums = []
    for name in files:
        head = name.split("_", 1)[0]
        if head.isdigit():
            nums.append(head)
    if not nums:
        return {}
    hoechste = max(nums)
    naechste = f"{int(hoechste) + 1:04d}"
    return {
        "hoechste": hoechste,
        "naechste": naechste,
        "alle": sorted(set(nums)),
        "dateien": files[-20:],  # letzte 20 reichen
    }


def run_explorer(state: RunState, frage: str) -> dict:
    pd = state.project_dir
    pn = state.project_name
    api_key = getattr(state, "api_key", "")

    # === M-373: Deterministische Messung ZUERST ===
    messungen = _messen(frage, Path(pd))
    if messungen:
        audit("explorer_messung", {
            "befehle": list(messungen.keys()),
            "dateien_gesamt": sum(len(m.get("dateien", [])) for m in messungen.values()),
        }, pd, pn)

    # M-394: Dateien aus Messung extrahieren -> deterministische key_files.
    # ABER: Doku-Dateien (docs/*.md, README.md) NICHT als key_files —
    # sie sind Kontext (findings), nicht Task-Ziel. Der Planner waehlt
    # die Code-Dateien selbst.
    key_files: list[dict] = []
    _seen_files: set[str] = set()
    # FIX 2026-10-31 (Fix F): Aufgabe-genannte .md ist Ziel, nicht
    # Kontext — dann NICHT die Code-Pfade aus ihrem Body extrahieren.
    # Sonst landen 19 Code-Dateien als key_files fuer 1 .md-Aufgabe.
    _aufgabe_pfade_set = set(
        (messungen.get("aufgabe_pfade") or {}).get("dateien") or []
    )
    for name, m in messungen.items():
        for datei in m.get("dateien", []):
            if datei.endswith(".md") or datei.startswith("docs/"):
                if datei in _aufgabe_pfade_set:
                    continue  # Fix F: Ziel-.md, kein Kontext-Explorer
                # K31: Aus .md-Body alle Code-Pfade extrahieren (.py/.sql/.html/.css/.js).
                for _pfad in _extrahiere_pfade(Path(pd), datei):
                    if _pfad in _seen_files:
                        continue
                    _inhalt = _datei_inhalt(Path(pd), _pfad)
                    key_files.append({
                        "file": _pfad,
                        "why": f"aus {datei}",
                        "symbols": "",
                        "preview": _inhalt,
                        "confidence": "medium",
                    })
                    _seen_files.add(_pfad)
                continue  # M-394: Doku selbst ist findings
            if datei in _seen_files:
                continue
            key_files.append({
                "file": datei,
                "why": f"{name}-Fehler",
                "symbols": "",
                "confidence": "high",
            })
            _seen_files.add(datei)

    # K54: Aufgabe-Pfade als eigene key_files ergaenzen (hoechste
    # Prioritaet, weil Architect sie explizit bauen soll).
    _aufgabe_pfade_m = messungen.get("aufgabe_pfade") or {}
    for _pfad in (_aufgabe_pfade_m.get("dateien") or []):
        if _pfad in _seen_files:
            continue
        _inhalt = _datei_inhalt(Path(pd), _pfad)
        key_files.insert(0, {
            "file": _pfad,
            "why": "in der Aufgabe genannt",
            "symbols": "",
            "preview": _inhalt,
            "confidence": "high",
        })
        _seen_files.add(_pfad)

    # M-394: Auch ohne key_files: findings aus Messung liefern.
    if messungen:
        findings = _format_findings(messungen)
        audit("explorer_messung_findings", {
            "n_key_files": len(key_files),
            "findings_len": len(findings),
        }, pd, pn)
        return {
            "findings": findings,
            "key_files": key_files,
            "next_reads": [k["file"] for k in key_files],
        }

    # === Fallback: LLM-Explorer (bestehender Pfad) ===
    if not api_key:
        audit("explorer_kein_key", {}, pd, pn)
        return {"findings": "", "key_files": [], "next_reads": []}

    py_files = _list_py_files(Path(pd))
    context = (
        f"Frage: {frage}\n\n"
        f"Messungen (bereits ausgefuehrt):\n"
        + (_format_findings(messungen) if messungen else "(keine)")
        + f"\n\nPython-Dateien ({len(py_files)}):\n"
        + "\n".join(py_files[:50])
    )

    reply = ask_llm(
        api_key, _explorer_system(frage), context,
        model="deepseek-chat", temperature=0.0, max_tokens=3000,
    )
    if not reply.ok:
        audit("explorer_llm_fehler", {"fehler": reply.error}, pd, pn)
        return {"findings": "", "key_files": [], "next_reads": []}

    raw = reply.content.strip()
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start < 0 or end <= start:
        audit("explorer_json_fehler", {"raw": raw[:200]}, pd, pn)
        return {"findings": "", "key_files": [], "next_reads": []}

    try:
        result = json.loads(raw[start:end])
    except json.JSONDecodeError:
        audit("explorer_json_fehler", {"raw": raw[:200]}, pd, pn)
        return {"findings": "", "key_files": [], "next_reads": []}

    audit("explorer_result", {
        "findings_len": len(result.get("findings", "")),
        "key_files": len(result.get("key_files", [])),
    }, pd, pn)
    return result
