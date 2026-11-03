"""Chat-Agent: Shell-Bridge + Projekt-Tools + LLM-Fallback.

Der Chat kennt deterministische Befehle (Shell-Befehl, Datei lesen,
suche, miss status, starte Loop), sonst antwortet er per LLM.

Shell-Integration: shell_exec schickt Befehle an die aktive PTY-Session
(Registry in werkstatt/web/shell.py). Output landet im xterm-Terminal.
Der Chat braucht also eine offene Shell-Session — sonst Fehlermeldung.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

__all__ = ["init", "verarbeite"]


_PROJEKT_DIR = Path("/opt/werkstatt")
_STATUS = _PROJEKT_DIR / "docs" / "STATUS.md"
_MAX_READ_BYTES = 50_000
_MAX_GREP_TREFFER = 30

# Erkannte Shell-Befehle (Single-Word-Prefix-Match)
_SHELL_BEFEHLE = frozenset({
    "ls", "ll", "la", "cd", "pwd", "cat", "head", "tail", "less", "more",
    "grep", "find", "tree", "file", "wc", "du", "df", "which", "whoami",
    "id", "date", "echo", "mkdir", "rm", "mv", "cp", "ln", "touch",
    "chmod", "chown", "ps", "kill", "top", "htop",
    "git", "python", "python3", "pip", "pip3",
    "ruff", "mypy", "pytest", "black", "isort",
    "tar", "zip", "unzip", "gzip", "gunzip",
    "curl", "wget", "ssh", "scp", "rsync",
    "vim", "nano", "code", "docker", "kubectl",
    "make", "cmake", "gcc",
})


def init(project_dir: Path | str) -> None:
    global _PROJEKT_DIR, _STATUS
    _PROJEKT_DIR = Path(project_dir).resolve()
    _STATUS = _PROJEKT_DIR / "docs" / "STATUS.md"


# --- STATUS.md Parser ---

def _open_ops() -> list[tuple[str, str]]:
    if not _STATUS.exists():
        return []
    src = _STATUS.read_text(encoding="utf-8")
    queue = src.split("## Erledigt (Auto-Log)")[0] if "## Erledigt" in src else src
    matches = re.findall(r"^### (OP-\d+):\s*([^\n]+)", queue, re.MULTILINE)
    return [(op, title.strip()) for op, title in matches]


def _op_block(op_id: str) -> str | None:
    if not _STATUS.exists():
        return None
    src = _STATUS.read_text(encoding="utf-8")
    m = re.search(
        rf"^### {re.escape(op_id)}:.*?(?=^### OP-|^## Erledigt|\Z)",
        src, re.MULTILINE | re.DOTALL,
    )
    return m.group(0).strip() if m else None


def _naechste_offene_op() -> tuple[str, str] | None:
    ops = _open_ops()
    return ops[0] if ops else None


# --- Pfad-Sicherheit ---

def _resolved_safe(pfad: str) -> Path | None:
    try:
        p = (_PROJEKT_DIR / pfad).resolve()
        if not str(p).startswith(str(_PROJEKT_DIR)):
            return None
        return p
    except (OSError, ValueError):
        return None


# --- Tools ---

def _read_file(pfad: str) -> str:
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
        content = content[:_MAX_READ_BYTES] + f"\n\n[... {len(content) - _MAX_READ_BYTES} Bytes abgeschnitten]"
    lines = content.splitlines()
    out = [f"{i+1:4d}: {ln}" for i, ln in enumerate(lines)]
    return f"# {pfad} ({len(lines)} Zeilen)\n" + "\n".join(out)


def _grep(pattern: str) -> str:
    try:
        result = subprocess.run(
            ["grep", "-rn", "--include=*.py", "--include=*.md",
             "--include=*.js", "--include=*.css",
             pattern, str(_PROJEKT_DIR)],
            capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        return f"FEHLER: {e}"
    lines = result.stdout.splitlines()
    prefix = str(_PROJEKT_DIR) + "/"
    lines = [ln.replace(prefix, "") for ln in lines]
    if not lines:
        return f"Keine Treffer fuer '{pattern}'."
    if len(lines) > _MAX_GREP_TREFFER:
        lines = lines[:_MAX_GREP_TREFFER] + [f"... ({len(lines) - _MAX_GREP_TREFFER} weitere)"]
    return f"# grep '{pattern}' ({len(lines)} Treffer)\n" + "\n".join(lines)


def _shell_exec(cmd: str) -> str:
    """Schickt Befehl an aktive PTY-Session. Output landet im Terminal."""
    from werkstatt.web import shell as _shell_mod
    project = "werkstatt"
    session = _shell_mod._AKTIVE_PTYS.get(project)
    if session is None:
        return (
            "Keine aktive Shell-Session. Oeffne zuerst das Terminal-Panel "
            "(Doppelklick auf 'Terminal' oder $-Button), dann kann ich "
            "Befehle dorthin schicken."
        )
    ok = session.inject(cmd)
    if ok:
        return (
            f"Befehl an Shell gesendet: `{cmd}`.\n"
            f"Output erscheint im Terminal-Panel links."
        )
    return "FEHLER: Konnte Befehl nicht senden (master_fd geschlossen)."


def _start_loop(op_id: str | None = None) -> str:
    if op_id:
        block = _op_block(op_id)
        if block is None:
            return f"OP {op_id} nicht in STATUS.md gefunden."
        aufgabe = f"Setze {op_id} um.\n\nLies docs/STATUS.md {op_id} fuer Details.\n\n{block}"
        op_name = op_id
    else:
        nxt = _naechste_offene_op()
        if nxt is None:
            return "Keine offenen OPs in STATUS.md."
        op_id_found, titel = nxt
        block = _op_block(op_id_found) or ""
        aufgabe = f"Setze {op_id_found} um.\n\nLies docs/STATUS.md {op_id_found} fuer Details.\n\n{block}"
        op_name = f"{op_id_found} ({titel})"

    try:
        prozess = subprocess.Popen(
            [sys.executable, "-m", "werkstatt.loop",
             "--project", "werkstatt", "--fresh",
             "--aufgabe", aufgabe],
            cwd=str(_PROJEKT_DIR),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError as e:
        return f"FEHLER beim Loop-Start: {e}"
    return (
        f"Loop gestartet fuer {op_name} (PID {prozess.pid}). "
        f"Der Loop wartet am Plan-Gate. Bestaetigen ueber /ws/terminal "
        f"(Audit-Tail) oder direkt im Loop-Prozess."
    )


def _measure_status() -> str:
    """Liest Commits + STATUS.md + ROADMAP.md. Basis fuer 'miss status'."""
    parts: list[str] = ["# Projekt-Messung (Stand jetzt)", ""]

    # 1. Git-Commits (letzte 20, alle Tage)
    try:
        r = subprocess.run(
            ["git", "log", "--oneline", "-20"],
            capture_output=True, text=True, timeout=5,
            cwd=str(_PROJEKT_DIR),
        )
        if r.returncode == 0:
            parts.append("## Commits (letzte 20)")
            for line in r.stdout.splitlines():
                parts.append(f"  - {line}")
            parts.append("")
    except (OSError, subprocess.TimeoutExpired):
        pass

    # 2. Offene OPs
    ops = _open_ops()
    parts.append(f"## Offene OPs ({len(ops)})")
    for op, title in ops:
        parts.append(f"  - {op}: {title[:70]}")
    parts.append("")

    # 3. ROADMAP Phasen
    roadmap = _PROJEKT_DIR / "docs" / "ROADMAP.md"
    if roadmap.exists():
        try:
            r_src = roadmap.read_text(encoding="utf-8")
            phasen = re.findall(r"^### (Phase [^\n]+)", r_src, re.MULTILINE)
            parts.append(f"## ROADMAP-Phasen ({len(phasen)})")
            for ph in phasen:
                parts.append(f"  - {ph}")
            parts.append("")
        except OSError:
            pass

    return "\n".join(parts)


# --- LLM-Fallback ---

def _llm_antwort(nachricht: str) -> str:
    from werkstatt.agent import ask_llm
    from werkstatt.env_loader import load_env

    load_env()
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        return (
            "Kein DEEPSEEK_API_KEY gesetzt. Ich kann nur deterministische "
            "Befehle: Shell-Befehl (`ls`, `git status`), 'welche OPs sind "
            "offen', 'miss status', 'starte Loop mit OP-045', "
            "'lies datei X', 'suche nach X'."
        )
    system = (
        "Du bist der Werkstatt-Chat. Der User arbeitet an einem Python-"
        "Projekt mit einem autonomen Loop. Antworte knapp, auf Deutsch, "
        "ohne Floskeln. Wenn du etwas nicht weisst, sag es."
    )
    reply = ask_llm(
        api_key=api_key,
        system_prompt=system,
        user_content=nachricht,
        model="deepseek-chat",
        temperature=0.2,
        max_tokens=500,
        aufgabe="chat",
        heartbeat=False,
    )
    if not reply.ok:
        return f"LLM-Fehler: {reply.error[:200]}"
    return reply.content.strip() or "(keine Antwort)"


# --- Pattern-Matching (deterministisch, ohne LLM) ---

def _ist_shell_befehl(text: str) -> bool:
    if not text or text.startswith("?"):
        return False
    first = text.strip().split()[0] if text.strip() else ""
    return first in _SHELL_BEFEHLE


def _pattern_verarbeite(text: str) -> str:
    """Deterministische Befehle ZUERST, dann None (LLM-Fallback)."""
    low = text.lower()

    # Miss status/roadmap
    if re.search(r"\b(miss|messe?n?)\s+(status|roadmap|beides)", low):
        return _measure_status()

    # Offene OPs
    if re.search(r"(welche\s+ops?|offene\s+ops?|was ist zu tun|op.liste)", low):
        ops = _open_ops()
        if not ops:
            return "Keine offenen OPs in STATUS.md."
        lines = [f"{len(ops)} offene OPs:"]
        for op, title in ops:
            lines.append(f"  - {op}: {title[:80]}")
        return "\n".join(lines)

    # Loop starten
    if re.search(r"starte?\s+(den\s+)?loop", low):
        m_op = re.search(r"(OP-\d+)", text, re.IGNORECASE)
        return _start_loop(m_op.group(1).upper() if m_op else None)

    # read_file
    m = re.search(
        r"(?:lies|zeige?|lese?|was ist in)\s+(?:datei\s+)?[`\"']?"
        r"(\S+\.(?:py|md|txt|json|yaml|yml|js|css|html))[`\"']?",
        text, re.IGNORECASE,
    )
    if m:
        return _read_file(m.group(1))

    # grep
    m = re.search(
        r"(?:suche?\s+(?:nach\s+)?|grep\s+)[`\"']?([^`\"']+?)[`\"']?$",
        text, re.IGNORECASE,
    )
    if m:
        return _grep(m.group(1).strip())

    return ""


# --- Orchestrator ---

def verarbeite(text: str, chat_id: str = "admin") -> str:
    """Verarbeitet Chat-Nachricht.

    Reihenfolge:
    1. `?`-Prefix -> explizit Chat (Pattern + LLM)
    2. Shell-Befehl erkannt -> an PTY-Session schicken
    3. Pattern-Match -> deterministisch antworten
    4. Fallback -> LLM
    """
    text = text.strip()
    if not text:
        return "(leer)"

    # 1. Expliziter Chat-Modus
    if text.startswith("?"):
        inner = text[1:].strip()
        answer = _pattern_verarbeite(inner)
        if answer:
            return answer
        return _llm_antwort(inner)

    # 2. Shell-Befehl
    if _ist_shell_befehl(text):
        return _shell_exec(text)

    # 3. Pattern
    answer = _pattern_verarbeite(text)
    if answer:
        return answer

    # 4. LLM
    return _llm_antwort(text)
