"""Explorer-Subagent. Read-only. Deterministische Messung VOR dem LLM.

M-338-Fix: Der Explorer MESS'T zuerst (ruff, pytest), extrahiert
die Dateien, und liefert sie als key_files. Das LLM formuliert
nur noch findings. Kein Raten.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
from pathlib import Path
from typing import Any

from werkstatt.agent import ask_llm
from werkstatt.audit import audit
from werkstatt.skills import load_all_skills
from werkstatt.state import RunState

EXPLORER_REQUEST_MAX_CHARS = 60_000
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
  - Das Python-Inventar ist eine begrenzte lexikalische Auswahl von
    Dateinamen, kein Vollstaendigkeits- oder Nichtexistenzbeleg.
    Wenn passende Quellpfade fehlen oder keine Namen passen, benenne die
    Belegluecke fuer gezieltes Nachladen statt aus der Auslassung zu folgern.

Antworte NUR mit validem JSON:
{
  "findings": "Kurze Zusammenfassung",
  "key_files": [{"file": "pfad/datei.py", "why": "warum", "symbols": "symbole", "confidence": "high|medium|low"}],
  "next_reads": ["pfad/datei.py"]
}
Keine Erklaerung, nur JSON."""


def _list_py_file_inventory(
    project_dir: Path,
    max_files: int = 200,
) -> tuple[list[str], bool, bool]:
    """Walk Python files deterministically without shell/platform dependencies."""
    paths: list[str] = []
    scan_error = False

    def record_scan_error(_error: OSError) -> None:
        nonlocal scan_error
        scan_error = True

    try:
        for directory, subdirs, filenames in os.walk(
            project_dir,
            topdown=True,
            onerror=record_scan_error,
            followlinks=False,
        ):
            subdirs[:] = sorted(
                name for name in subdirs
                if name not in {".venv", "__pycache__"}
            )
            for filename in sorted(filenames):
                if not filename.endswith(".py"):
                    continue
                paths.append(str(Path(directory) / filename))
                if len(paths) > max_files:
                    return paths[:max_files], not scan_error, True
    except OSError:
        scan_error = True
    return paths[:max_files], not scan_error, len(paths) > max_files


def _list_py_files(project_dir: Path, max_files: int = 200) -> list[str]:
    """Compatibility wrapper returning the bounded Python path list."""
    paths, _scan_succeeded, _index_truncated = _list_py_file_inventory(
        project_dir, max_files,
    )
    return paths


_EXPLORER_QUERY_STOPWORDS = frozenset({
    "and", "are", "das", "der", "die", "ein", "eine", "einer", "eines",
    "for", "from", "funktion", "funktioniert", "how", "ist", "mit", "modul",
    "oder", "projekt", "the", "und", "was", "wie", "works", "zum", "zur",
})


def _explorer_query_tokens(query: str) -> set[str]:
    return {
        token.casefold()
        for token in re.findall(r"[A-Za-z0-9]+", query)
        if len(token) >= 3 and token.casefold() not in _EXPLORER_QUERY_STOPWORDS
    }


def _rank_python_paths(
    paths: list[str], query: str,
) -> tuple[list[str], int, int, int]:
    """Rank only paths supported by query terms; never fill with arbitrary files."""
    query_tokens = _explorer_query_tokens(query)
    normalized_query = query.replace("\\", "/").casefold()
    path_tokens: list[tuple[str, set[str], set[str]]] = []
    for path in paths:
        normalized = path.replace("\\", "/")
        parts = [part.casefold() for part in normalized.split("/") if part]
        if not parts:
            continue
        basename_tokens = set(re.findall(r"[A-Za-z0-9]+", Path(parts[-1]).stem))
        parent_tokens = {
            token
            for part in parts[:-1]
            for token in re.findall(r"[A-Za-z0-9]+", part)
        }
        path_tokens.append((path, basename_tokens, parent_tokens))

    path_frequency = {
        token: sum(
            token in basename or token in parent
            for _path, basename, parent in path_tokens
        )
        for token in query_tokens
    }
    effective_tokens = {
        token for token, count in path_frequency.items()
        if count > 0 and (
            len(path_tokens) == 1 or count * 2 < len(path_tokens)
        )
    }
    common_tokens_ignored = len(query_tokens - effective_tokens)
    scored: list[tuple[int, int, str]] = []
    for index, (path, basename_tokens, parent_tokens) in enumerate(path_tokens):
        score = sum(
            (5 if token in basename_tokens else 2 if token in parent_tokens else 0)
            for token in effective_tokens
        )
        normalized = path.replace("\\", "/")
        if normalized_query and normalized_query in normalized.casefold():
            score += 20
        if score:
            scored.append((score, index, path))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return (
        [path for _score, _index, path in scored],
        len(scored),
        len(effective_tokens),
        common_tokens_ignored,
    )


def _rank_python_source_files(
    project_dir: Path,
    query: str,
    *,
    exclude: set[str] | None = None,
    limit: int = 5,
    max_file_bytes: int = 1_000_000,
    max_total_bytes: int = 20_000_000,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Find query-relevant source by content with explicit index/read limits."""
    indexed, scan_succeeded, index_truncated = _list_py_file_inventory(
        project_dir,
    )
    query_tokens = _explorer_query_tokens(query)
    excluded = {item.replace("\\", "/") for item in (exclude or set())}
    documents: list[tuple[str, set[str]]] = []
    read_failures = 0
    large_files_skipped = 0
    total_budget_skipped = 0
    scanned_bytes = 0
    for path in indexed:
        try:
            resolved = Path(path).resolve(strict=True)
            rel = resolved.relative_to(Path(project_dir).resolve()).as_posix()
            file_size = resolved.stat().st_size
            if file_size > max_file_bytes:
                large_files_skipped += 1
                continue
            if scanned_bytes + file_size > max_total_bytes:
                total_budget_skipped += 1
                continue
            content = resolved.read_bytes().decode("utf-8", errors="replace")
        except (OSError, RuntimeError, ValueError):
            read_failures += 1
            continue
        scanned_bytes += file_size
        tokens = {token.casefold() for token in re.findall(r"[A-Za-z0-9]+", content)}
        documents.append((rel, tokens))

    frequencies = {
        term: sum(term in tokens for _path, tokens in documents)
        for term in query_tokens
    }
    if len(documents) <= 5:
        discriminative = {
            term for term, count in frequencies.items()
            if count > 0 and (
                count < len(documents) or len(documents) == 1
            )
        }
    else:
        discriminative = {
            term for term, count in frequencies.items()
            if count > 0 and count * 2 < len(documents)
        }
    scored: list[tuple[float, int, str, list[str]]] = []
    for index, (path, tokens) in enumerate(documents):
        if path in excluded:
            continue
        matched = sorted(term for term in discriminative if term in tokens)
        if not matched:
            continue
        score = sum(
            math.log1p((len(documents) - frequencies[term] + 0.5)
                       / (frequencies[term] + 0.5))
            for term in matched
        )
        scored.append((score, index, path, matched))
    scored.sort(key=lambda row: (-row[0], row[1]))
    selected = [
        {
            "file": path,
            "why": "Inhaltstreffer fuer spezifische Auftragsbegriffe",
            "confidence": "medium",
            "matched_terms": terms[:20],
        }
        for _score, _index, path, terms in scored[:max(0, limit)]
    ]
    manifest = {
        "indexed_file_scope": "Python-Dateien, kein Vollindex des Projekts",
        "query_token_count": len(query_tokens),
        "discriminative_token_count": len(discriminative),
        "common_or_unmatched_tokens_ignored": len(query_tokens - discriminative),
        "indexed_file_count": len(indexed),
        "content_scanned_file_count": len(documents),
        "index_scan_succeeded": scan_succeeded,
        "index_truncated": index_truncated,
        "read_failures": read_failures,
        "large_files_skipped": large_files_skipped,
        "content_scanned_bytes": scanned_bytes,
        "content_scan_byte_cap": max_total_bytes,
        "files_skipped_total_byte_cap": total_budget_skipped,
        "matching_file_count": len(scored),
        "selected_files": [item["file"] for item in selected],
        "matching_files_omitted": max(0, len(scored) - len(selected)),
        "file_size_cap_bytes": max_file_bytes,
        "omissions_are_not_negative_evidence": True,
    }
    return selected, manifest


def _python_inventory_context(
    paths: list[str],
    *,
    scan_succeeded: bool,
    index_truncated: bool,
    query: str = "",
    index_cap: int = 200,
    prompt_cap: int = 50,
) -> tuple[str, dict[str, Any]]:
    """Offer query-matched paths only; describe every unmatched/omitted path."""
    (
        ranked, query_matched, query_token_count, common_tokens_ignored,
    ) = _rank_python_paths(paths, query)
    offered = ranked[:prompt_cap]
    prompt_omitted = max(0, len(paths) - len(offered))
    if not scan_succeeded:
        status = (
            "Scan fehlgeschlagen oder teilweise; die angezeigten Treffer "
            "sind unvollstaendig, fehlende Pfade sind unbekannt."
        )
    elif index_truncated:
        status = (
            f"Indexlimit {index_cap} erreicht; weitere Pfade koennen "
            "fehlen und sind unbekannt."
        )
    elif not paths:
        status = "Inventar vollstaendig; keine Python-Dateien gefunden."
    elif query_matched:
        status = (
            f"{query_matched} Pfade passen lexikalisch zu Auftragsbegriffen; "
            "sie sind nach Dateiname und Pfad priorisiert."
        )
    else:
        status = "Kein Pfad wurde aus dem Inventar ausgewaehlt."
    if paths and not query_matched:
        status += (
            " Kein hinreichend spezifischer Pfad passt lexikalisch zu den "
            "Auftragsbegriffen; es werden keine beliebigen Dateien angeboten. "
            "Das ist kein Negativbeleg. Fehlende Quellinformation muss "
            "gezielt nachgeladen werden."
        )
    if query_matched > len(offered):
        status += (
            f" {query_matched - len(offered)} passende Pfade wegen des "
            "Promptlimits nicht angeboten; bei Bedarf gezielt nachladen."
        )
    if len(paths) > query_matched:
        status += (
            f" {len(paths) - query_matched} weitere Indexpfade passten nicht "
            "lexikalisch und wurden nicht angeboten; das ist kein "
            "Negativbeleg und kein Vollstaendigkeitsbeweis."
        )
    inventory_prefix = (
        f"Python-Datei-Inventar: {status}\n"
        f"Im Index beobachtet: {len(paths)}\n"
        "Angebotene Pfade:\n"
    )
    offered_text = "\n".join(offered) if offered else "(keine Pfade angeboten)"
    inventory = inventory_prefix + offered_text
    path_manifest: list[dict[str, object]] = []
    offered_offsets: dict[str, tuple[int, int]] = {}
    cursor = len(inventory_prefix)
    for path in offered:
        offered_start = cursor
        offered_end = offered_start + len(path)
        offered_offsets[path] = (offered_start, offered_end)
        cursor = offered_end + 1
    for path in paths:
        prompt_start: int | None = None
        prompt_end: int | None = None
        if path in offered_offsets:
            prompt_start, prompt_end = offered_offsets[path]
            status = "included"
        else:
            status = (
                "omitted_prompt_cap" if path in ranked[prompt_cap:]
                else "not_selected_by_query"
            )
        path_manifest.append({
            "path": path,
            "status": status,
            "chars": len(path),
            "sha256": hashlib.sha256(path.encode("utf-8")).hexdigest(),
            **({"prompt_start": prompt_start, "prompt_end": prompt_end}
               if prompt_start is not None and prompt_end is not None else {}),
        })
    manifest = {
        "file_count": len(paths),
        "file_scan_succeeded": scan_succeeded,
        "file_index_truncated": index_truncated,
        "file_scan_complete": scan_succeeded and not index_truncated,
        "file_scan_cap": index_cap,
        "file_selection_strategy": "query_path_terms_v1",
        "query_tokens_used": query_token_count,
        "query_common_tokens_ignored": common_tokens_ignored,
        "query_matched_file_count": query_matched,
        "files_unmatched_by_query": max(0, len(paths) - query_matched),
        "query_matches_omitted_due_to_prompt_cap": max(
            0, query_matched - len(offered),
        ),
        "files_offered": offered,
        "files_omitted_from_prompt": prompt_omitted,
        "prompt_file_cap": prompt_cap,
        "path_manifest": path_manifest,
    }
    return inventory, manifest


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
    normalized_files = [rel.replace("\\", "/") for rel in dateien]
    gesehen: set[str] = set(normalized_files)
    for rel in normalized_files:
        p = project_dir / rel
        if not p.exists():
            continue
        # 1. Gleicher Ordner: alle *.py.
        for nachbar in sorted(p.parent.glob("*.py")):
            nrel = nachbar.relative_to(project_dir).as_posix()
            if nrel not in gesehen:
                gesehen.add(nrel)
                verwandt.append(nrel)
        # 2. Tests, die den Modul-Stamm nennen.
        stamm = p.stem
        tests_dir = project_dir / "tests"
        if tests_dir.exists():
            for t in tests_dir.rglob(f"*{stamm}*.py"):
                trel = t.relative_to(project_dir).as_posix()
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
                    _pf = _target.relative_to(project_dir).as_posix()
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


def _explorer_system() -> str:
    """EXPLORER_SYSTEM + Registry-Skills (using-werkstatt).

    OP-178b: systematic-debugging gehoert nicht hierher (Debugger
    kommt spaeter, OP-128/OP-160). Registry ist Soll: nur
    using-werkstatt fuer den Explorer.
    """
    from werkstatt.rollen import ROLLEN
    skills = load_all_skills()
    parts = [EXPLORER_SYSTEM]
    for s in ROLLEN["explorer"].lade_skills(skills):
        body = s.get("body") or ""
        if body:
            parts.append(
                f"## Skill: {s.get('name', '?')}\n" + body
            )
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
                    if i > letzte + 1 and teile:
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


def _datei_inhalt_mit_fundstellen(
    project_dir: Path,
    rel: str,
    suchbegriffe: list[str] | None = None,
) -> dict[str, Any]:
    """Return a project-local excerpt with stable original line numbers.

    Unlike `_datei_inhalt`, this rendering is intended for role handoffs:
    every included source line carries its original file line number. Missing,
    external, or unreadable paths return an explicit empty evidence record.
    """
    empty: dict[str, Any] = {
        "text": "",
        "line_ranges": [],
        "total_lines": 0,
        "complete": False,
        "reason": "source_unavailable",
        "source_sha256": None,
    }
    try:
        root = Path(project_dir).resolve(strict=True)
        target = (root / rel).resolve(strict=True)
        target.relative_to(root)
        if not target.is_file():
            return empty
        source_bytes = target.read_bytes()
        text = source_bytes.decode("utf-8", errors="replace")
    except (OSError, RuntimeError, ValueError):
        return empty

    lines = text.splitlines()
    total = len(lines)
    if total <= 200:
        selected = list(range(total))
    else:
        folded_terms = [term.casefold() for term in (suchbegriffe or [])]
        hits = {
            index
            for index, line in enumerate(lines)
            if any(term and term in line.casefold() for term in folded_terms)
        }
        if hits:
            selected = sorted({
                line_index
                for hit in hits
                for line_index in range(max(0, hit - 100), min(total, hit + 100))
            })
        else:
            selected = list(range(100)) + list(range(total - 50, total))

    ranges: list[list[int]] = []
    rendered: list[str] = []
    previous = -2
    for index in selected:
        if index > previous + 1:
            if previous >= 0:
                rendered.append(f"[... Zeilen {previous + 2}-{index} ausgelassen ...]")
            ranges.append([index + 1, index + 1])
        else:
            ranges[-1][1] = index + 1
        rendered.append(f"{index + 1:06d} | {lines[index]}")
        previous = index

    complete = total <= 200
    return {
        "text": "\n".join(rendered),
        "line_ranges": ranges,
        "total_lines": total,
        "complete": complete,
        "reason": "complete_file" if complete else "bounded_line_excerpt",
        "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
    }


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


def _emittiere_explorer_result(
    project_dir: Path,
    project_name: str,
    findings: str,
    key_files: list[dict],
    context_budget: dict[str, object] | None = None,
) -> None:
    """Emittiert genau ein explorer_result-Audit-Event."""
    audit("explorer_result", {
        "findings_len": len(findings or ""),
        "key_files": [
            k.get("file", "")
            for k in (key_files or [])
            if isinstance(k, dict)
        ],
        **({"context_budget": context_budget} if context_budget else {}),
    }, project_dir, project_name)


def _git_dirty(pd: Path) -> bool:
    """Helper (OP-135a): deterministischer git-status-Check."""
    try:
        return bool(__import__("subprocess").run(
            ["git", "-C", str(pd), "status", "--porcelain"],
            capture_output=True, text=True, timeout=5,
        ).stdout.strip())
    except Exception:
        return False


def run_explorer(state: RunState, frage: str) -> dict:
    pd = state.project_dir
    pn = state.project_name
    api_key = state.api_key

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
        # OP-050: migrations ist Kontext (Migrationsstand), KEINE Fehler-
        # Dateien. Die SQL-Files in data/migrations/ sind Projekt-
        # Struktur, keine Task-Ziele. Live-Beleg 2026-11-01: Architect
        # bekam 17 SQL-Files als "gemessene Dateien mit Fehlern" fuer
        # eine Ollama-Aufgabe.
        if name == "migrations":
            continue
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
        _ruff = messungen.get("ruff") or {}
        state.explorer_findings = {
            "git_dirty": _git_dirty(Path(pd)),
            "pytest_laufzeit_s": int(
                getattr(state, "explorer_pytest_laufzeit_s", 0) or 0),
            "ruff_befunde": list(_ruff.get("dateien") or [])[:50],
        }
        audit("explorer_messung_findings", {
            "n_key_files": len(key_files),
            "findings_len": len(findings),
            "diagnostics_befuellt": True,
        }, pd, pn)
        _emittiere_explorer_result(pd, pn, findings, key_files)
        return {
            "findings": findings,
            "key_files": key_files,
            "next_reads": [k["file"] for k in key_files],
        }

    # === Fallback: LLM-Explorer (bestehender Pfad) ===
    if not api_key:
        audit("explorer_kein_key", {}, pd, pn)
        return {"findings": "", "key_files": [], "next_reads": []}

    py_files, _scan_succeeded, _index_truncated = _list_py_file_inventory(
        Path(pd),
    )
    project_root = Path(pd).absolute()
    project_paths: list[str] = []
    path_normalization_failures = 0
    for candidate in py_files:
        try:
            project_paths.append(
                Path(candidate).absolute().relative_to(project_root).as_posix(),
            )
        except ValueError:
            path_normalization_failures += 1
    file_inventory, inventory_manifest = _python_inventory_context(
        project_paths,
        scan_succeeded=_scan_succeeded and path_normalization_failures == 0,
        index_truncated=_index_truncated,
        query=frage,
    )
    inventory_manifest["path_normalization_failures"] = path_normalization_failures
    context_sections = [
        ("question", f"Frage: {frage}"),
        (
            "measurements",
            "Messungen (bereits ausgefuehrt):\n"
            + (_format_findings(messungen) if messungen else "(keine)"),
        ),
        ("file_inventory", file_inventory),
    ]
    context = "\n\n".join(content for _name, content in context_sections)
    context_section_manifest: list[dict[str, object]] = []
    cursor = 0
    section_offsets: dict[str, int] = {}
    for name, content in context_sections:
        start = context.find(content, cursor)
        if start < 0:
            raise ValueError(f"Explorer-Kontextabschnitt {name!r} fehlt.")
        end = start + len(content)
        section_offsets[name] = start
        context_section_manifest.append({
            "name": name,
            "status": "included",
            "chars": len(content),
            "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
            "prompt_start": start,
            "prompt_end": end,
        })
        cursor = end + 2
    for path_record in inventory_manifest["path_manifest"]:
        if not isinstance(path_record, dict) or path_record.get("status") != "included":
            continue
        inventory_start = section_offsets["file_inventory"]
        path_start = path_record.get("prompt_start")
        path_end = path_record.get("prompt_end")
        if isinstance(path_start, int) and isinstance(path_end, int):
            path_record["prompt_start"] = inventory_start + path_start
            path_record["prompt_end"] = inventory_start + path_end

    system_prompt = _explorer_system()
    request_chars = len(system_prompt) + len(context)
    context_budget = {
        "max_request_chars": EXPLORER_REQUEST_MAX_CHARS,
        "request_chars": request_chars,
        "system_chars": len(system_prompt),
        "user_chars": len(context),
        "required_context_complete": request_chars <= EXPLORER_REQUEST_MAX_CHARS,
        "action": (
            "send" if request_chars <= EXPLORER_REQUEST_MAX_CHARS else "blocked"
        ),
        "sections": context_section_manifest,
        "path_manifest": inventory_manifest["path_manifest"],
    }
    if request_chars > EXPLORER_REQUEST_MAX_CHARS:
        reason = (
            "Explorer-Modellaufruf blockiert: Frage und Inventar ueberschreiten "
            f"das Requestbudget ({request_chars}/{EXPLORER_REQUEST_MAX_CHARS} Zeichen). "
            "Der Scan ist damit nicht als vollstaendige Antwort zu werten."
        )
        _emittiere_explorer_result(
            pd, pn, reason, [], context_budget=context_budget,
        )
        return {
            "findings": reason,
            "key_files": [],
            "next_reads": [],
            "context_budget": context_budget,
        }
    reply = ask_llm(
        api_key, system_prompt, context,
        model="deepseek-chat", temperature=0.0, max_tokens=3000,
        state=state, aufgabe="explorer",
        context_manifest={
            "budget_event": "explorer_context",
            "user_sha256": hashlib.sha256(context.encode("utf-8")).hexdigest(),
            "system_sha256": hashlib.sha256(system_prompt.encode("utf-8")).hexdigest(),
            "measurement_count": len(messungen),
            **inventory_manifest,
            "user_chars": len(context),
            "sections": context_section_manifest,
            "request_chars": request_chars,
            "max_request_chars": EXPLORER_REQUEST_MAX_CHARS,
            "required_context_complete": True,
        },
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

    _emittiere_explorer_result(
        pd, pn,
        result.get("findings", ""),
        result.get("key_files", []),
        context_budget=context_budget,
    )
    try:
        state.explorer_findings = {
            "git_dirty": bool(
                __import__("subprocess").run(
                    ["git", "-C", str(getattr(state, "project_dir", ".")),
                     "status", "--porcelain"],
                    capture_output=True, text=True, timeout=5,
                ).stdout.strip()
            ),
            "pytest_laufzeit_s": int(
                getattr(state, "explorer_pytest_laufzeit_s", 0) or 0
            ),
            "ruff_befunde": list(
                state.explorer_ruff_befunde or []
            ),
        }
    except Exception:
        audit("explorer_findings_fehler", {}, pd, pn)
    return result
