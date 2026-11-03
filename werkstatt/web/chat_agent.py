"""Chat-Agent: LLM-First mit Function-Calling (OP-084 + OP-085).

Architektur:
- Fast-Path: `!cmd` (Shell), `starte Loop mit OP-NNN` (explizit)
- Alles andere: LLM mit Tool-Calling. DeepSeek entscheidet selbst,
  welche Tools es ruft (list_open_ops, read_file, grep, shell_exec,
  measure_status, start_loop).

Ersetzt die vorherige Pattern-FIRST-Version, die bei natürlichen
Fragen (\"nächste offene OP\") stumpf alle OPs zurueckgab.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Any

__all__ = ["TOOLS", "init", "verarbeite"]

_PROJEKT_DIR = Path("/opt/werkstatt")
_STATUS = _PROJEKT_DIR / "docs" / "STATUS.md"
_MAX_READ_BYTES = 50_000
_MAX_GREP_TREFFER = 30
_MAX_TOOL_ROUNDS = 5
_DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
_MODEL = "deepseek-chat"


def init(project_dir: Path | str) -> None:
    global _PROJEKT_DIR, _STATUS
    _PROJEKT_DIR = Path(project_dir).resolve()
    _STATUS = _PROJEKT_DIR / "docs" / "STATUS.md"


# --- Tools: OpenAPI-Schema ---

TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "list_open_ops",
            "description": (
                "Listet alle offenen OPs aus docs/STATUS.md. "
                "Nummer, Titel und Kurzstatus. Nutze dies fuer Fragen "
                "wie 'welche OPs sind offen', 'was ist die naechste OP'."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": (
                "Liest eine Datei aus dem Projekt (max 50KB). Liefert "
                "Zeilennummern. Nutze dies fuer 'was steht in X', "
                "'lies datei Y'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relativer Pfad zur Datei (z.B. docs/STATUS.md).",
                    },
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "grep",
            "description": (
                "Sucht einen Text in .py/.md/.js/.css Dateien im Projekt. "
                "Liefert Treffer mit Datei:Zeile. Nutze dies fuer "
                "'suche nach Y', 'wo steht Z'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string"},
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "shell_exec",
            "description": (
                "Fuehrt einen Shell-Befehl aus. Bei aktiver UI-Shell "
                "landet der Output dort; sonst subprocess in Chat. "
                "Nutze dies fuer 'ls', 'git status', 'pytest', "
                "Datei-Operationen."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "cmd": {"type": "string"},
                    "timeout_s": {"type": "number", "default": 30},
                },
                "required": ["cmd"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "measure_status",
            "description": (
                "Liefert git log (letzte 20), STATUS.md-OPs und ROADMAP-"
                "Phasen auf einmal. Nutze dies fuer 'miss status', "
                "'was wurde heute gemacht'."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "start_loop",
            "description": (
                "Startet den werkstatt.loop mit einer OP. Parameter "
                "op_id optional — leer = naechste offene OP."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "op_id": {
                        "type": "string",
                        "description": "OP-NNN oder leer fuer naechste offene OP.",
                    },
                },
            },
        },
    },
]


# --- Tool-Implementierungen ---

def _open_ops() -> list[tuple[str, str, str]]:
    """Liefert [(op_id, titel, status), ...] aus STATUS.md."""
    if not _STATUS.exists():
        return []
    src = _STATUS.read_text(encoding="utf-8")
    queue = src.split("## Erledigt (Auto-Log)")[0] if "## Erledigt" in src else src
    blocks = re.split(r"^### (OP-\d+):\s*([^\n]+)", queue, flags=re.MULTILINE)
    out = []
    for i in range(1, len(blocks), 3):
        op_id = blocks[i]
        titel = blocks[i+1].strip()
        body = blocks[i+2]
        m = re.search(r"^- \*\*Status:\*\*\s*(\w+)", body, re.MULTILINE)
        status = m.group(1) if m else "?"
        out.append((op_id, titel, status))
    return out


def _tool_list_open_ops(args: dict) -> str:
    ops = _open_ops()
    if not ops:
        return "Keine offenen OPs in STATUS.md."
    lines = [f"{len(ops)} offene OPs in docs/STATUS.md:"]
    for i, (op_id, titel, status) in enumerate(ops, 1):
        lines.append(f"{i:2d}. {op_id} [{status}]: {titel[:100]}")
    return "\n".join(lines)


def _resolved_safe(pfad: str) -> Path | None:
    try:
        p = (_PROJEKT_DIR / pfad).resolve()
        if not str(p).startswith(str(_PROJEKT_DIR)):
            return None
        return p
    except (OSError, ValueError):
        return None


def _tool_read_file(args: dict) -> str:
    pfad = str(args.get("path", "")).strip()
    if not pfad:
        return "FEHLER: kein path angegeben."
    p = _resolved_safe(pfad)
    if p is None:
        return f"FEHLER: Pfad '{pfad}' liegt ausserhalb des Projekts."
    if not p.exists():
        return f"FEHLER: Datei '{pfad}' existiert nicht."
    if not p.is_file():
        return f"FEHLER: '{pfad}' ist keine Datei."
    try:
        content = p.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return f"FEHLER beim Lesen: {e}"
    if len(content) > _MAX_READ_BYTES:
        content = content[:_MAX_READ_BYTES] + (
            f"\n\n[... {len(content) - _MAX_READ_BYTES} Bytes abgeschnitten]"
        )
    lines = content.splitlines()
    numbered = "\n".join(f"{i+1:4d}: {ln}" for i, ln in enumerate(lines))
    return f"# {pfad} ({len(lines)} Zeilen)\n{numbered}"


def _tool_grep(args: dict) -> str:
    pattern = str(args.get("pattern", "")).strip()
    if not pattern:
        return "FEHLER: kein pattern angegeben."
    try:
        result = subprocess.run(
            ["grep", "-rn", "--include=*.py", "--include=*.md",
             "--include=*.js", "--include=*.css",
             pattern, str(_PROJEKT_DIR)],
            capture_output=True, text=True, timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        return f"FEHLER: {e}"
    lines = result.stdout.splitlines()
    prefix = str(_PROJEKT_DIR) + "/"
    lines = [ln.replace(prefix, "") for ln in lines]
    if not lines:
        return f"Keine Treffer fuer '{pattern}'."
    truncated = len(lines) > _MAX_GREP_TREFFER
    shown = lines[:_MAX_GREP_TREFFER]
    head = f"# grep '{pattern}' ({len(lines)} Treffer"
    head += f", zeige {_MAX_GREP_TREFFER})" if truncated else ")"
    return head + "\n" + "\n".join(shown)


def _tool_shell_exec(args: dict) -> str:
    cmd = str(args.get("cmd", "")).strip()
    if not cmd:
        return "FEHLER: kein cmd angegeben."
    timeout_s = float(args.get("timeout_s", 30))
    from werkstatt.web import shell as _shell_mod
    project = "werkstatt"
    session = _shell_mod._AKTIVE_PTYS.get(project)
    is_multiline = "\n" in cmd

    if session is not None and not is_multiline:
        if session.inject(cmd):
            return (
                f"$ {cmd}\n\n→ ausgefuehrt in aktiver Shell. "
                f"Output im Terminal-Panel links."
            )

    try:
        result = subprocess.run(
            ["bash", "-c", cmd],
            capture_output=True, text=True, timeout=timeout_s,
            cwd=str(_PROJEKT_DIR), check=False,
        )
    except subprocess.TimeoutExpired:
        return f"$ {cmd}\n\nTIMEOUT nach {timeout_s:.0f}s."
    except OSError as exc:
        return f"$ {cmd}\n\nFEHLER: {exc}"

    output = (result.stdout or "") + (result.stderr or "")
    if len(output) > 3000:
        output = output[:3000] + f"\n... ({len(output) - 3000} Zeichen abgeschnitten)"
    if not output.strip():
        output = "(keine Ausgabe)"
    return f"$ {cmd}\n\nExit: {result.returncode}\n```\n{output}\n```"


def _tool_measure_status(args: dict) -> str:
    parts = ["# Projekt-Messung"]
    try:
        r = subprocess.run(
            ["git", "log", "--oneline", "-20"],
            capture_output=True, text=True, timeout=5,
            cwd=str(_PROJEKT_DIR), check=False,
        )
        if r.returncode == 0 and r.stdout.strip():
            parts.append("\n## Letzte 20 Commits")
            for line in r.stdout.splitlines():
                parts.append(f"  {line}")
    except (OSError, subprocess.TimeoutExpired):
        pass
    ops = _open_ops()
    parts.append(f"\n## Offene OPs ({len(ops)})")
    for op_id, titel, status in ops:
        parts.append(f"  - {op_id} [{status}]: {titel[:80]}")
    roadmap = _PROJEKT_DIR / "docs" / "ROADMAP.md"
    if roadmap.exists():
        try:
            src = roadmap.read_text(encoding="utf-8")
            phasen = re.findall(r"^### (Phase [^\n]+)", src, re.MULTILINE)
            parts.append(f"\n## ROADMAP-Phasen ({len(phasen)})")
            for ph in phasen:
                parts.append(f"  - {ph}")
        except OSError:
            pass
    return "\n".join(parts)


def _tool_start_loop(args: dict) -> str:
    op_id = str(args.get("op_id", "")).strip()
    if op_id:
        block = _op_block(op_id)
        if block is None:
            return f"OP {op_id} nicht in STATUS.md gefunden."
        aufgabe = f"Setze {op_id} um.\n\nLies docs/STATUS.md {op_id} fuer Details.\n\n{block}"
        op_name = op_id
    else:
        ops = _open_ops()
        if not ops:
            return "Keine offenen OPs."
        op_id, titel, _ = ops[0]
        block = _op_block(op_id) or ""
        aufgabe = f"Setze {op_id} um.\n\nLies docs/STATUS.md {op_id} fuer Details.\n\n{block}"
        op_name = f"{op_id} ({titel})"
    try:
        proc = subprocess.Popen(
            [sys.executable, "-m", "werkstatt.loop",
             "--project", "werkstatt", "--fresh",
             "--aufgabe", aufgabe],
            cwd=str(_PROJEKT_DIR),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError as exc:
        return f"FEHLER beim Loop-Start: {exc}"
    return f"Loop gestartet fuer {op_name} (PID {proc.pid})."


def _op_block(op_id: str) -> str | None:
    if not _STATUS.exists():
        return None
    src = _STATUS.read_text(encoding="utf-8")
    m = re.search(
        rf"^### {re.escape(op_id)}:.*?(?=^### OP-|^## Erledigt|\Z)",
        src, re.MULTILINE | re.DOTALL,
    )
    return m.group(0).strip() if m else None


_TOOL_DISPATCH = {
    "list_open_ops": _tool_list_open_ops,
    "read_file": _tool_read_file,
    "grep": _tool_grep,
    "shell_exec": _tool_shell_exec,
    "measure_status": _tool_measure_status,
    "start_loop": _tool_start_loop,
}


def _execute_tool(name: str, raw_args: str) -> str:
    fn = _TOOL_DISPATCH.get(name)
    if fn is None:
        return f"FEHLER: unbekanntes Tool '{name}'."
    try:
        args = json.loads(raw_args) if raw_args.strip() else {}
    except json.JSONDecodeError:
        return f"FEHLER: Tool-Argumente sind kein JSON: {raw_args[:80]}"
    try:
        return fn(args)
    except Exception as exc:  # noqa: BLE001
        return f"FEHLER im Tool {name}: {type(exc).__name__}: {exc}"


# --- DeepSeek-Call ---

def _deepseek_chat(messages: list[dict], tools: list[dict] | None = None) -> dict:
    """Direkter DeepSeek-API-Call. Liefert Roh-Dict der Response."""
    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY nicht gesetzt.")
    body: dict[str, Any] = {
        "model": _MODEL,
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 1500,
    }
    if tools:
        body["tools"] = tools
        body["tool_choice"] = "auto"
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        _DEEPSEEK_URL,
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="replace")[:300]
        raise RuntimeError(f"DeepSeek HTTP {exc.code}: {err_body}") from exc


# --- Agent-Loop ---

_SYSTEM_PROMPT = """Du bist der Werkstatt-Chat. Der User arbeitet an einem \
Python-Projekt mit einem autonomen Loop (werkstatt/). Du hast Tools:
- list_open_ops: offene OPs aus docs/STATUS.md
- read_file: Datei lesen
- grep: Text suchen
- shell_exec: Shell-Befehl ausfuehren
- measure_status: git log + STATUS + ROADMAP
- start_loop: Loop mit OP starten

Regeln:
- Wenn der User eine Frage zu Projekt-Zustand stellt, NUTZE die Tools.
- Antworte knapp, auf Deutsch, ohne Floskeln.
- Zitiere Zahlen und Datei-Pfade wo moeglich.
- Wenn du ein Tool brauchst, ruf es auf. Antworte erst wenn du genug
  Informationen hast.
"""


def _agent_loop(user_text: str) -> str:
    """LLM-First mit Tool-Calling. Max 5 Runden."""
    from werkstatt.env_loader import load_env
    load_env()
    messages: list[dict] = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user_text},
    ]
    for _ in range(_MAX_TOOL_ROUNDS):
        try:
            resp = _deepseek_chat(messages, tools=TOOLS)
        except RuntimeError as exc:
            return f"LLM-Fehler: {exc}"
        choices = resp.get("choices") or []
        if not choices:
            return "LLM-Fehler: keine choices in Response."
        msg = choices[0].get("message") or {}
        tool_calls = msg.get("tool_calls") or []
        if not tool_calls:
            content = (msg.get("content") or "").strip()
            return content or "(keine Antwort)"
        # Assistant-Message mit tool_calls in messages aufnehmen
        messages.append({
            "role": "assistant",
            "content": msg.get("content") or "",
            "tool_calls": tool_calls,
        })
        for tc in tool_calls:
            tc_id = tc.get("id", "")
            fn = tc.get("function") or {}
            name = fn.get("name", "")
            args = fn.get("arguments", "") or ""
            result = _execute_tool(name, args)
            messages.append({
                "role": "tool",
                "tool_call_id": tc_id,
                "content": result,
            })
    return f"(Agent hat {_MAX_TOOL_ROUNDS} Runden Tool-Calls ohne Antwort beendet)"


# --- Orchestrator ---

def verarbeite(text: str, chat_id: str = "admin") -> str:
    """Verarbeitet Chat-Nachricht.

    Drei Wege:
    1. `!cmd` -> direkter Shell-Befehl (fast-path, kein LLM)
    2. `starte Loop mit OP-NNN` -> deterministischer Loop-Start
    3. Alles andere -> LLM mit Tool-Calling
    """
    text = text.strip()
    if not text:
        return "(leer)"

    # 1. Erzwungener Shell-Befehl
    if text.startswith("!"):
        cmd = text[1:].strip()
        if not cmd:
            return "(leerer Shell-Befehl)"
        return _tool_shell_exec({"cmd": cmd})

    # 2. Expliziter Loop-Start (deterministisch, weil teuer + sichtbar)
    m = re.match(r"^(?:starte\s+(?:den\s+)?loop|loop\s+starten)(?:\s+mit\s+(OP-\d+))?$",
                 text, re.IGNORECASE)
    if m:
        op_id = (m.group(1) or "").upper()
        return _tool_start_loop({"op_id": op_id} if op_id else {})

    # 3. LLM-First mit Tools
    return _agent_loop(text)
