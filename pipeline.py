#!/usr/bin/env python3
"""
pipeline.py - Projektunabhaengiger Multi-Agenten-Ablauf.
Block fuer Block. Ein Approval-Gate am Ende.

Verwendung:
  DEEPSEEK_API_KEY=sk-... runuser -u security-ai -- \
    /opt/security-ai/.venv/bin/python3 \
    /opt/werkstatt/pipeline.py --project <name> "<Block-Beschreibung>"

Liest /opt/werkstatt/projects/<name>.yaml. Laedt Agenten aus agents_dir.
Redaction: redaction.redact_all() vor jedem LLM-Call.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests
import yaml

# Redaction (lokal, projektunabhaengig)
sys.path.insert(0, str(Path(__file__).parent))
import redaction

DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
SUBPROCESS_TIMEOUT = 60
COVERAGE_MIN_PCT = 80.0
AUDIT_DIR_NAME = "audit-logs"
AUDIT_FILE_NAME = "agent-pipeline.jsonl"



# HR1-HR10. Werden jedem System-Prompt angehaengt, unabhaengig
# von der Rolle. Code, nicht Prompt. Nicht ueberschreibbar.
# In Anlehnung an docs/WORKFLOW.md.
HARD_RULES = """
## HARD RULES (projektunabhaengig, verbindlich)

HR1. Faktenlage vor Meinung.
     Keine API aus dem Gedaechtnis. Keine Datei-Inhalte annehmen.
     Keine Zahlen schaetzen. Immer messen, nicht erinnern.

HR2. Ein Ausfuehrungsblock pro logischer Einheit.
     Kein Vorab-Stapeln mehrerer unabhaengiger Bloecke.

HR3. Vor cat > auf eine angeblich neue Datei:
     git ls-files <pfad> UND git status --porcelain pruefen.

HR4. Nach jedem Patch einer bestehenden Datei:
     assert text.count(anker) == 1.
     Bei count != 1: STOP.

HR5. Nach jedem Patch, der Tests betrifft:
     pytest --collect-only -q <datei> VOR pytest -q <datei>.

HR6. git status --porcelain zeigt M bei einer Datei, die als
     "neu" angekuendigt war: STOP.

HR7. Kategorie 3: Code VOR Ausfuehrung an den Reviewer.
     Kein Improvisieren nach NO-GO.

HR8. Doku-Pflege ist Pflicht.
     Ein Commit ohne Doku-Nachzug ist ein unvollstaendiger Commit.

HR9. Patch-Skripte > ~3 KB in /tmp schreiben, dort
     verifizieren, dann ausfuehren. Kein Heredoc in die
     interaktive Shell.

HR10. Nach jedem abgeschlossenen Block: Update an den Menschen.
"""

# Auflage 2041: Groessenlimits fuer das Messprotokoll.
MAX_PROTOKOLL_PER_COMMAND = 10_000
MAX_PROTOKOLL_TOTAL = 100_000

# Auflage 2042: erlaubte Quellen-Marker fuer COMMAND-Audits.
ERLAUBTE_QUELLEN = {"reviewer", "builder", "test_generator"}



WERKSTATT_HOME = Path("/opt/werkstatt")
PROJECTS_DIR = WERKSTATT_HOME / "projects"


class BudgetExhausted(Exception):
    """Wird geworfen, wenn das LLM-Budget erschoepft ist."""


def require_budget(state: RunState, max_llm: int) -> None:
    """Auflage 2051: prueft das Budget VOR jedem LLM-Call.

    Wirft BudgetExhausted, wenn state.llm_calls >= max_llm.
    """
    if max_llm > 0 and state.llm_calls >= max_llm:
        raise BudgetExhausted(
            f"LLM-Budget erschoepft: {state.llm_calls}/{max_llm}"
        )


def load_project_config(project_name: str) -> dict[str, Any]:
    """Laedt die Projekt-Konfiguration aus /opt/werkstatt/projects/.

    Kein CWD-Bezug. Fail closed, wenn Projekt oder Datei fehlt.
    """
    if not project_name or "/" in project_name or ".." in project_name:
        print(f"[FAIL] Ungueltiger Projektname: {project_name!r}. Fail closed.")
        sys.exit(1)
    path = PROJECTS_DIR / f"{project_name}.yaml"
    if not path.exists():
        print(f"[FAIL] Projekt-Konfiguration fehlt: {path}. Fail closed.")
        sys.exit(1)
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        print(f"[FAIL] Projekt-Konfiguration ist kein dict: {path}. Fail closed.")
        sys.exit(1)
    return data


def load_agents(agents_dir: str) -> dict[str, dict[str, Any]]:
    base = Path(agents_dir).expanduser()
    if not base.exists():
        print(f"[FAIL] agents_dir fehlt: {base}. Fail closed.")
        sys.exit(1)
    agents: dict[str, dict[str, Any]] = {}
    for md in sorted(base.glob("*.md")):
        text = md.read_text(encoding="utf-8")
        if not text.startswith("---"):
            continue
        parts = text.split("---", 2)
        if len(parts) < 3:
            continue
        fm = yaml.safe_load(parts[1])
        fm["body"] = parts[2].strip()
        fm["path"] = str(md)
        agents[fm["name"]] = fm
    missing = {"reviewer", "builder", "test_generator"} - set(agents.keys())
    if missing:
        print(f"[FAIL] Pflicht-Agenten fehlen: {missing}. Fail closed.")
        sys.exit(1)
    return agents


def load_docs(docs_config: dict[str, str], project_dir: Path) -> dict[str, str]:
    docs: dict[str, str] = {}
    for key, rel in docs_config.items():
        path = project_dir / rel
        if not path.exists():
            print(f"[FAIL] Pflichtdokument fehlt: {rel}. Fail closed.")
            sys.exit(1)
        docs[key] = path.read_text(encoding="utf-8")
    return docs


def audit(kind: str, payload: dict[str, Any], project_dir: Path,
          project_name: str) -> None:
    """Schreibt einen Audit-Eintrag.

    Auflage 2043: project_name wird explizit uebergeben. Keine
    Modul-Variable mehr, keine unsichtbare Kopplung.
    """
    audit_dir = project_dir / AUDIT_DIR_NAME
    audit_dir.mkdir(parents=True, exist_ok=True)
    tag = datetime.now(UTC).strftime("%Y-%m-%d")
    datei = audit_dir / f"agent-pipeline-{tag}.jsonl"
    entry = {
        "audit_id": f"PIPE-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}-{int(time.time()*1000)%100000}",
        "timestamp": datetime.now(UTC).isoformat(timespec="milliseconds"),
        "agent": "agent_pipeline",
        "project": project_name,
        "kind": kind,
        **payload,
    }
    try:
        with datei.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=True) + "\n")
    except OSError as exc:
        print(f"[WARN] Audit-Schreibfehler: {exc}")



@dataclass(frozen=True)
class Measurement:
    mid: str
    argv: tuple[str, ...]
    beschreibung: str
    timeout_s: int = SUBPROCESS_TIMEOUT


def build_catalog(config: dict[str, Any], project_dir: Path
                  ) -> tuple[dict[str, Measurement], dict[str, Measurement]]:
    venv = config.get("venv_python", str(project_dir / ".venv/bin/python3"))
    all_m: dict[str, Measurement] = {
        "py_compile": Measurement("py_compile",
            (venv, "-m", "compileall", "-q", "apps", "core", "harness", "tools", "scripts"),
            "Python-Syntax-Check.", 300),
        "ruff": Measurement("ruff", (venv, "-m", "ruff", "check", "."), "Lint."),
        "mypy": Measurement("mypy",
            (venv, "-m", "mypy", "apps", "core", "harness", "tools", "scripts"), "Typen.", 300),
        "test_count": Measurement("test_count",
            (venv, "-m", "pytest", "--collect-only", "-q"), "Test-Anzahl."),
        "git_status": Measurement("git_status", ("git", "status", "--porcelain"), "Tree."),
        "git_head": Measurement("git_head", ("git", "rev-parse", "--short", "HEAD"), "HEAD."),
        "test_run": Measurement("test_run", (venv, "-m", "pytest", "-q"), "Vollsuite.", 600),
        "coverage": Measurement("coverage",
            (venv, "-m", "pytest", "--cov=core", "--cov-report=json:coverage.json", "-q"),
            "Coverage.", 600),
        "chaos_probe": Measurement("chaos_probe",
            (venv, str(project_dir / "scripts" / "chaos_probe.py")), "Chaos.", 120),
        "bandit": Measurement("bandit",
            (venv, "-m", "bandit", "-r", "core", "harness", "-q"), "Security-Lint.", 300),
        "pip_audit": Measurement("pip_audit",
            (venv, "-m", "pip_audit", "-r", "requirements.txt", "--format", "json"),
            "CVE-Check.", 120),
        "read_file": Measurement("read_file", ("cat",), "Datei lesen."),
    }
    always = {k: v for k, v in all_m.items() if k in set(config.get("always_run", []))}
    optional = {k: v for k, v in all_m.items() if k in set(config.get("optional_catalog", []))}
    if not always:
        print("[FAIL] always_run leer. Fail closed.")
        sys.exit(1)
    return always, optional


def run_measurement(m: Measurement, whitelist: list[str], project_dir: Path,
                    extra_arg: str | None = None) -> tuple[str, bool]:
    argv = list(m.argv)
    if m.mid == "read_file":
        if not extra_arg:
            return "read_file ohne Pfad.", False
        cand = (project_dir / extra_arg).resolve()
        try:
            rel = str(cand.relative_to(project_dir.resolve()))
        except ValueError:
            return f"Pfad ausserhalb Projekt: {extra_arg}", False
        if not any(rel.startswith(p) for p in whitelist):
            return f"Pfad nicht in Whitelist: {rel}", False
        argv.append(str(cand))
    try:
        res = subprocess.run(argv, cwd=str(project_dir), capture_output=True,
                             text=True, timeout=m.timeout_s, check=False)
    except subprocess.TimeoutExpired:
        return f"TIMEOUT {m.timeout_s}s", False
    except OSError as exc:
        return f"OSError: {exc}", False
    out = (f"=== {m.mid} ===\nARGV: {' '.join(argv)}\nRC: {res.returncode}\n"
           f"STDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}\n")
    return out, res.returncode == 0


def run_measurement_mit_argv(m: Measurement, whitelist: list[str],
                             project_dir: Path, extra_arg: str | None = None
                             ) -> tuple[str, bool, list[str]]:
    """Wie run_measurement, gibt aber argv mit zurueck (Auflage 2040)."""
    argv: list[str] = list(m.argv)
    if m.mid == "read_file":
        if not extra_arg:
            return "read_file ohne Pfad.", False, []
        if not isinstance(extra_arg, str):
            return "read_file arg ist kein str.", False, []
        cand = (project_dir / extra_arg).resolve()
        try:
            rel = str(cand.relative_to(project_dir.resolve()))
        except ValueError:
            return f"Pfad ausserhalb Projekt: {extra_arg}", False, []
        if not any(rel.startswith(p) for p in whitelist):
            return f"Pfad nicht in Whitelist: {rel}", False, []
        argv.append(str(cand))
    try:
        res = subprocess.run(argv, cwd=str(project_dir), capture_output=True,
                             text=True, timeout=m.timeout_s, check=False)
    except subprocess.TimeoutExpired:
        return f"TIMEOUT {m.timeout_s}s", False, argv
    except OSError as exc:
        return f"OSError: {exc}", False, argv
    out = (f"=== {m.mid} ===\nARGV: {' '.join(argv)}\nRC: {res.returncode}\n"
           f"STDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}\n")
    return out, res.returncode == 0, argv



@dataclass
class LLMReply:
    ok: bool
    content: str = ""
    error: str = ""


def ask_llm(api_key: str, system_prompt: str, user_content: str,
            model: str, temperature: float, timeout: int = 120) -> LLMReply:
    # Redaction: vor dem Senden anwenden
    user_content, _ = redaction.redact_all(user_content)
    system_prompt, _ = redaction.redact_all(system_prompt, max_len=200000)
    headers: dict[str, str] = {"Authorization": f"Bearer {api_key}",
                              "Content-Type": "application/json"}
    payload: dict[str, Any] = {"model": model,
                               "messages": [{"role": "system", "content": system_prompt},
                                            {"role": "user", "content": user_content}],
                               "temperature": temperature}
    try:
        res = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=timeout)
    except requests.RequestException as exc:
        return LLMReply(ok=False, error=f"HTTP: {exc}")
    if res.status_code != 200:
        return LLMReply(ok=False, error=f"HTTP {res.status_code}: {res.text[:200]}")
    try:
        data = res.json()
        return LLMReply(ok=True, content=data["choices"][0]["message"]["content"])
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        return LLMReply(ok=False, error=f"Parsing: {exc}")


def classify_verdict(text: str) -> str:
    gezaehlt = 0
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        gezaehlt += 1
        if gezaehlt > 15:
            break
        w = s.split(maxsplit=1)[0].upper()
        if w in {"GO", "NO-GO", "ESKALATION"}:
            return w
        if w in {"COMMIT-GO", "COMMIT-NO-GO", "COMMIT-ESKALATION"}:
            return w
        if s.upper().startswith("COMMAND:"):
            return "COMMAND"
    return "UNKLAR"


def parse_commands(text: str) -> list[dict[str, str]]:
    """Parst COMMAND-Zeilen aus einer LLM-Antwort.

    Auflage 2039: arg muss str sein. Kein dict/list.
    Wenn der LLM einen JSON-Block liefert, wird das
    verworfen und der Eintrag nicht uebernommen.
    """
    cmds: list[dict[str, str]] = []
    for line in text.splitlines():
        s = line.strip()
        if not s.upper().startswith("COMMAND:"):
            continue
        body = s[len("COMMAND:"):].strip()
        if not body.upper().startswith("RUN "):
            continue
        rest = body[4:].strip()
        parts = rest.split(maxsplit=1)
        if not parts:
            continue
        cmd_id = parts[0]
        if not isinstance(cmd_id, str) or not cmd_id:
            continue
        arg_roh = parts[1].strip() if len(parts) > 1 else ""
        # Auflage 2039: arg MUSS str sein. Bei nicht-str: verwerfen.
        if not isinstance(arg_roh, str):
            continue
        cmds.append({"id": cmd_id, "arg": arg_roh})
    return cmds


def parse_auflagen(text: str) -> list[str]:
    auflagen: list[str] = []
    for line in text.splitlines():
        m = re.match(r"\s*Auflage\s+([A-Z]?\d+)\s*:?\s*(.*)", line, re.IGNORECASE)
        if m:
            auflagen.append(f"{m.group(1)}: {m.group(2).strip()}")
    return auflagen


def parse_empfehlung(text: str) -> dict[str, str]:
    emp = {"tests": "", "art": "", "prioritaet": ""}
    for line in text.splitlines():
        s = line.strip()
        if s.upper().startswith("EMPFEHLUNG TESTS:"):
            emp["tests"] = s.split(":", 1)[1].strip()
        elif s.upper().startswith("EMPFEHLUNG ART:"):
            emp["art"] = s.split(":", 1)[1].strip()
        elif s.upper().startswith("EMPFEHLUNG PRIORITAET:"):
            emp["prioritaet"] = s.split(":", 1)[1].strip()
    return emp



def build_system_prompt(agent: dict[str, Any], docs: dict[str, str],
                        doc_keys: list[str]) -> str:
    """Baut System-Prompt aus Rollen-Body + HARD_RULES + Projekt-Doku.

    Reihenfolge: HR-Regeln zuerst (stabil), dann Projekt-Doku.
    """
    parts = [agent["body"], HARD_RULES]
    if doc_keys:
        parts.append("\n\n--- PROJEKT-DOKU ---")
        for key in doc_keys:
            if key in docs:
                parts.append(f"\n--- {key} ---\n{docs[key]}")
    return "\n".join(parts)


def load_recent_commits(project_dir: Path, n: int = 10) -> str:
    try:
        res = subprocess.run(
            ("git", "log", f"-{n}", "--format=%h %an%n%s%n%b%n---"),
            cwd=str(project_dir), capture_output=True, text=True,
            timeout=30, check=False,
        )
    except (subprocess.TimeoutExpired, OSError):
        return "(git log nicht verfuegbar)"
    if res.returncode != 0:
        return f"(git log: {res.stderr[:200]})"
    return res.stdout


@dataclass
class RunState:
    block_id: str
    aufgabe: str
    start_ts: str
    docs: dict[str, str]
    agents: dict[str, dict[str, Any]]
    always: dict[str, Measurement]
    optional: dict[str, Measurement]
    file_whitelist: list[str]
    api_key: str
    budget: dict[str, int]
    agent_docs: dict[str, list[str]]
    project_dir: Path
    reviewer_verdict_model: str = "deepseek-chat"
    reviewer_recovery_model: str = "deepseek-reasoner"
    builder_model: str = "deepseek-chat"
    builder_temp: float = 0.3
    test_gen_model: str = "deepseek-chat"
    llm_timeout_s: int = 180
    git_author_name: str = ""
    git_author_email: str = ""
    project_name: str = ""
    coverage_pct: int = -1  # -1 = nicht gemessen
    basis_protokoll: str = ""
    mess_protokoll: str = ""
    code_entwurf: str = ""
    test_vorschlaege: str = ""
    commit_paket: dict[str, Any] = field(default_factory=dict)
    commit_review: dict[str, Any] = field(default_factory=dict)
    review_runden: list[dict[str, Any]] = field(default_factory=list)
    commands_log: list[dict[str, str]] = field(default_factory=list)
    auflagen_log: list[list[str]] = field(default_factory=list)
    empfehlung_log: list[dict[str, str]] = field(default_factory=list)
    llm_calls: int = 0



@dataclass
class RepairAttempt:
    nummer: int
    fehler_vor: list[str]
    massnahme: str
    erfolg: bool
    protokoll: str


def auto_repair_ruff(project_dir: Path, venv_python: str) -> tuple[bool, str]:
    """Nur deterministische Fixes. Kein LLM."""
    protokoll = ""
    try:
        r1 = subprocess.run((venv_python, "-m", "ruff", "check", ".", "--fix"),
                            cwd=str(project_dir), capture_output=True, text=True,
                            timeout=300, check=False)
        protokoll += f"=== ruff check --fix ===\nRC: {r1.returncode}\n{r1.stdout}\n{r1.stderr}\n"
        r2 = subprocess.run((venv_python, "-m", "ruff", "format", "."),
                            cwd=str(project_dir), capture_output=True, text=True,
                            timeout=300, check=False)
        protokoll += f"=== ruff format ===\nRC: {r2.returncode}\n{r2.stdout}\n{r2.stderr}\n"
        r3 = subprocess.run((venv_python, "-m", "ruff", "check", "."),
                            cwd=str(project_dir), capture_output=True, text=True,
                            timeout=300, check=False)
        return r3.returncode == 0, protokoll
    except (subprocess.TimeoutExpired, OSError) as exc:
        return False, protokoll + f"\nFEHLER: {exc}"


def snapshot_tests_dir(project_dir: Path) -> dict[str, int]:
    tests = project_dir / "tests"
    snap: dict[str, int] = {}
    if not tests.exists():
        return snap
    for f in tests.rglob("*.py"):
        try:
            snap[str(f.relative_to(project_dir))] = f.stat().st_size
        except OSError:
            pass
    return snap


def check_tests_dir_unveraendert(project_dir: Path, vorher: dict[str, int]
                                 ) -> tuple[bool, list[str]]:
    """Prueft, dass keine Test-Datei geloescht oder kleiner wurde."""
    nachher = snapshot_tests_dir(project_dir)
    probleme: list[str] = []
    for pfad, groesse in vorher.items():
        if pfad not in nachher:
            probleme.append(f"GELOESCHT: {pfad}")
        elif nachher[pfad] < groesse:
            probleme.append(f"KLEINER: {pfad} ({groesse} -> {nachher[pfad]})")
    return (len(probleme) == 0), probleme



@dataclass
class RecoveryVorschlag:
    art: str
    diagnose: str = ""
    reparaturplan: list[str] = field(default_factory=list)
    empfehlung: str = ""
    blockgroesse: str = ""
    rohantwort: str = ""


def ask_reviewer_for_recovery(state: RunState, art: str, kontext: str) -> RecoveryVorschlag:
    if art == "basis_gate":
        aufgabe = ("Das Basis-Gate ist rot und der deterministische "
                   "Auto-Repair-Versuch ist gescheitert.\n\n"
                   f"{kontext}\n\n"
                   "Liefere:\nDIAGNOSE: <Ursache>\nREPARATURPLAN:\n  1. ...\n"
                   "  2. ...\nBLOCKGROESSE: <ein Block | mehrere Bloecke | eigener Punkt>\n"
                   "EMPFEHLUNG: <was der Mensch tun soll>\n")
    elif art == "no_go":
        aufgabe = (f"Der Builder hat kein akzeptables Ergebnis geliefert.\n\n{kontext}\n\n"
                   "Liefere:\nDIAGNOSE: <warum>\nLOESUNGSVORSCHLAG:\n  1. ...\n  2. ...\n"
                   "BLOCKGROESSE: <...>\nEMPFEHLUNG: <approve | reject | aufteilen | eskalieren>\n")
    elif art == "eskalation":
        aufgabe = (f"Du hast ESKALATION ausgesprochen.\n\n{kontext}\n\n"
                   "Liefere:\nDIAGNOSE: <Kern>\nFRAGE AN DEN MENSCHEN: <was>\n"
                   "OPTIONEN:\n  A) ...\n  B) ...\nBLOCKGROESSE: <...>\n"
                   "EMPFEHLUNG: <welche Option>\n")
    elif art == "budget":
        aufgabe = (f"Das Budget ist erschoepft.\n\n{kontext}\n\n"
                   "Liefere:\nDIAGNOSE: <warum>\nLOESUNGSVORSCHLAG:\n  1. ...\n  2. ...\n"
                   "BLOCKGROESSE: <...>\nEMPFEHLUNG: <naechster Schritt>\n")
    else:
        return RecoveryVorschlag(art=art, rohantwort="(unbekannt)")

    reply = ask_llm(
        state.api_key,
        build_system_prompt(state.agents["reviewer"], state.docs,
                            state.agent_docs.get("reviewer", [])),
        aufgabe,
        state.reviewer_recovery_model,
        0.0,
        state.llm_timeout_s,
    )
    if not reply.ok:
        return RecoveryVorschlag(art=art,
                                 diagnose="(Reviewer nicht erreichbar)",
                                 empfehlung=f"API-Fehler: {reply.error}",
                                 rohantwort=reply.error)
    state.llm_calls += 1
    v = RecoveryVorschlag(art=art, rohantwort=reply.content)
    abschnitt = None
    for line in reply.content.splitlines():
        s = line.strip()
        if s.upper().startswith("DIAGNOSE:"):
            v.diagnose = s.split(":", 1)[1].strip()
            abschnitt = None
        elif s.upper().startswith(("REPARATURPLAN:", "LOESUNGSVORSCHLAG:", "OPTIONEN:")):
            abschnitt = "plan"
        elif s.upper().startswith("BLOCKGROESSE:"):
            v.blockgroesse = s.split(":", 1)[1].strip()
            abschnitt = None
        elif s.upper().startswith("EMPFEHLUNG:"):
            v.empfehlung = s.split(":", 1)[1].strip()
            abschnitt = None
        elif abschnitt == "plan" and s:
            m = re.match(r"^\s*(?:\d+\.|[-*]|[A-Z]\))\s*(.+)$", s)
            if m:
                v.reparaturplan.append(m.group(1).strip())
    return v


def print_recovery(v: RecoveryVorschlag) -> None:
    print("\n" + "=" * 70)
    print(f"LOESUNGSVORSCHLAG DES REVIEWERS (Stop: {v.art})")
    print("=" * 70)
    if v.diagnose:
        print(f"\nDIAGNOSE:\n  {v.diagnose}")
    if v.reparaturplan:
        print("\nPLAN:")
        for i, s in enumerate(v.reparaturplan, 1):
            print(f"  {i}. {s}")
    if v.blockgroesse:
        print(f"\nBLOCKGROESSE: {v.blockgroesse}")
    if v.empfehlung:
        print(f"\nEMPFEHLUNG: {v.empfehlung}")
    print("\n--- ROHE ANTWORT ---")
    print(v.rohantwort)
    print("=" * 70)



def trim_output(out: str, grenze: int = MAX_PROTOKOLL_PER_COMMAND) -> str:
    """Kuerzt ein Messprotokoll-Stueck auf `grenze` Zeichen (Auflage 2041)."""
    if len(out) <= grenze:
        return out
    rest = len(out) - grenze
    return out[:grenze] + f"\n[... gekuerzt, {rest} Zeichen weggelassen ...]\n"


def execute_commands(state: RunState, commands: list[dict[str, str]],
                     quelle: str) -> None:
    """Fuehrt COMMAND-Zeilen aus. NUR wenn id in state.always oder state.optional.

    Auflagen 2039, 2040, 2041, 2042:
      - arg muss str sein.
      - argv geht ins Audit.
      - mess_protokoll wird begrenzt.
      - quelle ist ein Marker, kein Prompt-Text.
    """
    # Auflage 2042: quelle auf erlaubte Marker beschraenken.
    if quelle not in ERLAUBTE_QUELLEN:
        audit("quelle_invalid", {"quelle": str(quelle)[:80]}, state.project_dir, state.project_name)
        print(f"[WARN] Ungueltiger quelle-Marker: {str(quelle)[:80]}")
        quelle = "unknown"

    erlaubt = set(state.always.keys()) | set(state.optional.keys())
    katalog: dict[str, Measurement] = {}
    katalog.update(state.always)
    katalog.update(state.optional)

    for cmd in commands:
        cid = cmd.get("id", "")
        arg = cmd.get("arg", "")

        # Auflage 2039: id und arg muessen str sein.
        if not isinstance(cid, str) or not cid:
            audit("command_rejected",
                  {"id": str(cid)[:80], "arg": str(arg)[:80],
                   "quelle": quelle, "grund": "id_kein_str"},
                  state.project_dir, state.project_name)
            continue
        if not isinstance(arg, str):
            audit("command_rejected",
                  {"id": cid, "arg": str(arg)[:80],
                   "quelle": quelle, "grund": "arg_kein_str"},
                  state.project_dir, state.project_name)
            continue

        if cid not in erlaubt:
            print(f"[!] COMMAND abgelehnt (nicht in Whitelist): {cid}")
            audit("command_rejected",
                  {"id": cid, "arg": arg[:200], "quelle": quelle,
                   "grund": "nicht_in_whitelist"},
                  state.project_dir, state.project_name)
            continue

        m = katalog[cid]
        out, ok, argv = run_measurement_mit_argv(
            m, state.file_whitelist, state.project_dir,
            arg if cid == "read_file" else None,
        )
        out = trim_output(out)

        # Auflage 2041: Gesamtlaenge begrenzen.
        rest_platz = MAX_PROTOKOLL_TOTAL - len(state.mess_protokoll)
        if rest_platz <= 0:
            print("[!] mess_protokoll Gesamtlimit erreicht. Weitere Messungen werden nur auditiert.")
            audit("command_executed",
                  {"id": cid, "arg": arg[:200], "argv": argv,
                   "quelle": quelle, "ok": ok, "ausgabe_verworfen": True},
                  state.project_dir, state.project_name)
            continue
        if len(out) > rest_platz:
            out = out[:rest_platz] + "\n[... Gesamtlimit erreicht ...]\n"

        state.mess_protokoll += out

        # Auflage 2040: argv ins Audit.
        audit("command_executed",
              {"id": cid, "arg": arg[:200], "argv": argv,
               "quelle": quelle, "ok": ok},
              state.project_dir, state.project_name)



def parse_commit_paket(text: str) -> dict[str, Any]:
    """Parst die Builder-Antwort fuer das Commit-Paket.

    Erwartet:
      COMMIT-MESSAGE:
      <...>
      ENDE COMMIT-MESSAGE
      BETROFFENE DATEIEN:
        - <pfad>
      ENDE BETROFFENE DATEIEN
      DOKU-PATCHES:
        - pfad: <pfad>
          anker: <text>
          ersatz: <text>
      ENDE DOKU-PATCHES
    """
    paket: dict[str, Any] = {"message": "", "dateien": [], "doku_patches": []}

    m = re.search(r"COMMIT-MESSAGE:\s*\n(.*?)\nENDE COMMIT-MESSAGE",
                  text, re.DOTALL)
    if m:
        paket["message"] = m.group(1).strip()

    m = re.search(r"BETROFFENE DATEIEN:\s*\n(.*?)\nENDE BETROFFENE DATEIEN",
                  text, re.DOTALL)
    if m:
        for line in m.group(1).splitlines():
            s = line.strip().lstrip("-*").strip()
            if s:
                paket["dateien"].append(s)

    m = re.search(r"DOKU-PATCHES:\s*\n(.*?)\nENDE DOKU-PATCHES",
                  text, re.DOTALL)
    if m:
        # Jeder Patch beginnt mit "- pfad: ...".
        # Wir splitten an den Zeilenanfaengen, die mit "- pfad:" beginnen,
        # und behalten den Trenner NICHT, sondern parsen den Block selbst.
        block_text = "\n" + m.group(1).strip()
        # Trenner: Zeilenanfang, dann "- pfad:"
        bloecke = re.split(r"\n\s*-\s*pfad:\s*", block_text)
        # Erster Block ist leer (vor dem ersten Trenner).
        for block in bloecke[1:]:
            block = block.strip()
            if not block:
                continue
            lines = block.splitlines()
            pfad = lines[0].strip()
            anker, ersatz = "", ""
            for line in lines[1:]:
                if "anker:" in line:
                    anker = line.split("anker:", 1)[1].strip()
                elif "ersatz:" in line:
                    ersatz = line.split("ersatz:", 1)[1].strip()
            if pfad and anker:
                paket["doku_patches"].append(
                    {"pfad": pfad, "anker": anker, "ersatz": ersatz})

    return paket


def build_commit_paket(state: RunState) -> dict[str, Any]:
    """Bittet den Builder um einen Commit-Paket-Vorschlag.

    Der Builder sieht: letzten Commit, Code-Entwurf, Reviewer-Verdict,
    sowie die betroffenen Dateien.
    """
    letzter = subprocess.run(
        ("git", "log", "-1", "--format=%B"),
        cwd=str(state.project_dir), capture_output=True, text=True,
        timeout=30, check=False,
    ).stdout

    aufgabe = (
        "Der Block wurde approved. Erstelle:\n\n"
        "1. Eine Commit-Message im Format des letzten Commits.\n"
        "2. Eine Liste der betroffenen Dateien.\n"
        "3. Doku-Patches fuer PHASES.md, SECURITY_REVIEW_LOG.md, "
        "ggf. DESIGN_DECISIONS.md.\n\n"
        f"LETZTER COMMIT (Format-Referenz):\n{letzter}\n\n"
        f"CODE-ENTWURF (gekuerzt):\n{state.code_entwurf[:3000]}\n\n"
        f"REVIEWER-VERDICT:\n"
        f"{state.review_runden[-1]['raw'] if state.review_runden else '(keins)'}\n\n"
        "Antworte in genau diesem Format:\n\n"
        "COMMIT-MESSAGE:\n"
        "<die vollstaendige Commit-Message>\n"
        "ENDE COMMIT-MESSAGE\n\n"
        "BETROFFENE DATEIEN:\n"
        "  - <pfad relativ zum Projekt>\n"
        "ENDE BETROFFENE DATEIEN\n\n"
        "DOKU-PATCHES:\n"
        "  - pfad: docs/PHASES.md\n"
        "    anker: <exakter Text aus der Datei>\n"
        "    ersatz: <neuer Text>\n"
        "ENDE DOKU-PATCHES"
    )

    reply = ask_llm(
        state.api_key,
        build_system_prompt(state.agents["builder"], state.docs,
                            state.agent_docs.get("builder", [])),
        aufgabe,
        state.builder_model,
        state.builder_temp,
        state.llm_timeout_s,
    )
    if not reply.ok:
        return {"message": "", "dateien": [], "doku_patches": [],
                "error": reply.error}
    state.llm_calls += 1
    paket = parse_commit_paket(reply.content)
    paket["roh"] = reply.content
    return paket


def apply_commit_and_doku(state: RunState, paket: dict[str, Any]) -> bool:
    """Wendet Doku-Patches an und committet.

    NUR nach Human-Gate. Explizite Datei-Liste, kein git add -A.
    """
    # 1. Doku-Patches anwenden (assert count == 1)
    for patch in paket.get("doku_patches", []):
        ziel = state.project_dir / patch["pfad"]
        if not ziel.exists():
            print(f"[!] Doku-Datei fehlt: {patch['pfad']}")
            return False
        text = ziel.read_text(encoding="utf-8")
        count = text.count(patch["anker"])
        if count != 1:
            print(f"[!] Anker in {patch['pfad']} kommt {count}x vor. "
                  f"Erwartet: 1x. Abbruch.")
            return False
        text = text.replace(patch["anker"], patch["ersatz"], 1)
        ziel.write_text(text, encoding="utf-8")
        print(f"[+] Doku gepatcht: {patch['pfad']}")

    # 2. Datei-Liste pruefen: alle in file_whitelist und existierend
    dateien = paket.get("dateien", [])
    if not dateien:
        print("[!] Keine betroffenen Dateien angegeben. Abbruch.")
        return False
    for pfad in dateien:
        if not any(pfad.startswith(w) for w in state.file_whitelist):
            print(f"[!] Datei nicht in Whitelist: {pfad}")
            return False
        # Auflage 2048: Datei muss existieren.
        # Sonst scheitert git add spaeter unspezifisch.
        if not (state.project_dir / pfad).exists():
            print(f"[!] Datei existiert nicht: {pfad}")
            return False

    # 3. git add (explizite Liste)
    argv_add = ("git", "add", "--") + tuple(dateien)
    res_add = subprocess.run(
        argv_add, cwd=str(state.project_dir),
        capture_output=True, text=True, timeout=60, check=False,
    )
    if res_add.returncode != 0:
        print(f"[!] git add fehlgeschlagen: {res_add.stderr}")
        return False

    # 4. Commit-Message in temp-Datei schreiben (kein Heredoc-Problem)
    msg_datei = state.project_dir / ".commit-msg.tmp"
    msg_datei.write_text(paket["message"], encoding="utf-8")
    # Autor aus der Konfiguration setzen.
    # So steht im Git-Log immer der Mensch (ghxstfocus), nicht der Linux-User.
    commit_argv: list[str] = ["git"]
    if state.git_author_name:
        commit_argv += ["-c", f"user.name={state.git_author_name}"]
    if state.git_author_email:
        commit_argv += ["-c", f"user.email={state.git_author_email}"]
    commit_argv += ["commit", "-F", str(msg_datei)]

    # Auflage 2049: try/finally, damit die Temp-Datei auch bei
    # einer Exception verschwindet. Sonst bleibt .commit-msg.tmp
    # im Projektverzeichnis liegen.
    try:
        res_commit = subprocess.run(
            tuple(commit_argv),
            cwd=str(state.project_dir), capture_output=True, text=True,
            timeout=60, check=False,
        )
    finally:
        msg_datei.unlink(missing_ok=True)

    if res_commit.returncode != 0:
        print(f"[!] git commit fehlgeschlagen: {res_commit.stderr}")
        return False

    # 5. Bestaetigung
    log = subprocess.run(
        ("git", "log", "-1", "--oneline"),
        cwd=str(state.project_dir), capture_output=True, text=True,
        timeout=30, check=False,
    ).stdout
    print(f"[+] Commit erstellt: {log.strip()}")
    return True



def print_approval_dokument(state: RunState) -> None:
    """Zeigt das Approval-Dokument mit vollstaendiger Reviewer-Argumentation."""
    print("\n" + "=" * 70)
    print("APPROVAL-DOKUMENT")
    print("=" * 70)
    print(f"Block:     {state.block_id}")
    print(f"Aufgabe:   {state.aufgabe}")
    print(f"Start:     {state.start_ts}")
    print(f"Runden:    {len(state.review_runden)}")
    print(f"LLM-Calls: {state.llm_calls}")

    print("\n--- BASIS-GATE (immer, vor Reviewer) ---")
    print(state.basis_protokoll)

    if state.mess_protokoll:
        print("\n--- OPTIONALE MESSUNGEN ---")
        print(state.mess_protokoll)

    print("\n--- REVIEWER-ARGUMENTATION ---")
    for r in state.review_runden:
        print(f"\n[ROUND {r['runde']} - VERDICT: {r['verdict']}]")
        print(r["raw"])

    if state.commit_review:
        print("\n--- COMMIT-REVIEW ---")
        print(f"Verdikt: {state.commit_review.get('verdict', '?')}")
        print(state.commit_review.get("raw", ""))

    print("\n--- AUFLAGEN ---")
    for i, auflagen in enumerate(state.auflagen_log, 1):
        if auflagen:
            print(f"Runde {i}: " + "; ".join(auflagen))

    print("\n--- EMPFEHLUNGEN ---")
    for i, emp in enumerate(state.empfehlung_log, 1):
        print(f"Runde {i}: Tests={emp['tests']}, Art={emp['art']}, Prio={emp['prioritaet']}")

    print("\n--- CODE-ENTWURF ---")
    print(state.code_entwurf)

    if state.test_vorschlaege:
        print("\n--- TEST-VORSCHLAEGE ---")
        print(state.test_vorschlaege)

    if state.commit_paket:
        print("\n--- COMMIT-PAKET ---")
        print(f"Commit-Message:\n{state.commit_paket.get('message', '')}")
        print(f"Betroffene Dateien: {state.commit_paket.get('dateien', [])}")
        print(f"Doku-Patches: {len(state.commit_paket.get('doku_patches', []))}")


def run_pipeline(project_name: str, aufgabe: str) -> int:
    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        print("[FAIL] DEEPSEEK_API_KEY fehlt. Fail closed.")
        return 1

    config = load_project_config(project_name)
    project_dir = Path(config.get("project_dir", str(Path.cwd()))).expanduser()
    agents = load_agents(config.get("agents_dir", "/opt/werkstatt/agents"))
    docs = load_docs(config.get("docs", {}), project_dir)
    always, optional = build_catalog(config, project_dir)
    file_whitelist = config.get("file_whitelist", [])
    budget = config.get("budget", {"max_review_rounds": 5, "max_llm_calls": 20})
    max_llm = budget.get("max_llm_calls", 20)

    git_author = config.get("git_author", {}) or {}
    state = RunState(
        block_id=config.get("project", "unknown"),
        aufgabe=aufgabe,
        start_ts=datetime.now(UTC).isoformat(timespec="seconds"),
        docs=docs, agents=agents, always=always, optional=optional,
        file_whitelist=file_whitelist, api_key=api_key, budget=budget,
        agent_docs=config.get("agent_docs", {}),
        project_dir=project_dir,
        git_author_name=str(git_author.get("name", "")),
        git_author_email=str(git_author.get("email", "")),
        project_name=project_name,
    )

    audit("pipeline_start",
          {"aufgabe_hash": __import__("hashlib").sha256(aufgabe.encode()).hexdigest(),
           "aufgabe_kurz": aufgabe[:200],
           "llm_calls_start": 0},
          project_dir, project_name)

    # ==================================================================
    # SCHRITT 0: BASIS-GATE (HARD FAIL)
    # ==================================================================
    print("[*] Schritt 0: Basis-Gate (immer).")
    print(f"[i] Messungen: {list(always.keys())}")
    basis_fehler: list[str] = []
    for mid, m in always.items():
        out, ok = run_measurement(m, file_whitelist, project_dir)
        state.basis_protokoll += out
        if not ok:
            basis_fehler.append(mid)
            print(f"[!] Basis-Gate rot: {mid}")
        else:
            print(f"[+] Basis-Gate gruen: {mid}")

    if basis_fehler:
        print("\n" + "=" * 70)
        print(f"[!] Basis-Gate rot. Fehler: {basis_fehler}")
        print("[*] Auto-Repair (nur deterministisch).")
        print("=" * 70)
        audit("basis_gate_rot", {"fehler": basis_fehler}, project_dir, project_name)

        # Nur deterministischer Fix: ruff --fix
        nur_ruff = basis_fehler == ["ruff"]
        if nur_ruff:
            tests_snap = snapshot_tests_dir(project_dir)
            ok, _ = auto_repair_ruff(
                project_dir,
                config.get("venv_python", str(project_dir / ".venv/bin/python3")),
            )
            audit("auto_repair_ruff", {"ok": ok}, project_dir, project_name)
            tests_ok, probleme = check_tests_dir_unveraendert(project_dir, tests_snap)
            if not tests_ok:
                print(f"[!] Auto-Repair hat tests/ veraendert: {probleme}")
                ok = False
            if ok:
                # Nachmessen
                state.basis_protokoll = ""
                neue_fehler: list[str] = []
                for mid, m in always.items():
                    out, ok_m = run_measurement(m, file_whitelist, project_dir)
                    state.basis_protokoll += out
                    if not ok_m:
                        neue_fehler.append(mid)
                if not neue_fehler:
                    print("[+] Basis-Gate gruen nach Auto-Repair.")
                    basis_fehler = []
                else:
                    basis_fehler = neue_fehler

        if basis_fehler:
            kontext = (
                f"Basis-Gate-Fehler: {basis_fehler}\n\n"
                f"Basis-Protokoll:\n{state.basis_protokoll[:3000]}"
            )
            v = ask_reviewer_for_recovery(state, "basis_gate", kontext)
            print_recovery(v)
            audit("recovery_basis_gate",
                  {"diagnose": v.diagnose, "plan": v.reparaturplan,
                   "empfehlung": v.empfehlung},
                  project_dir, project_name)
            return 11

    print("[+] Basis-Gate gruen. Block startet.")

    # ==================================================================
    # SCHRITT 1: Reviewer waehlt optionale Messungen
    # ==================================================================
    print("\n[*] Schritt 1: Reviewer waehlt optionale Messungen.")

    doc_keys_reviewer = state.agent_docs.get("reviewer", [])
    reviewer_prompt = build_system_prompt(state.agents["reviewer"], state.docs,
                                          doc_keys_reviewer)

    historie = load_recent_commits(project_dir, n=10)

    overview = (
        "Basis-Gate (immer gelaufen, gruen):\n"
        + state.basis_protokoll[:1500]
        + "\n\nVerfuegbare optionale Messungen:\n"
        + "\n".join(f"  - {m.mid}: {m.beschreibung}" for m in optional.values())
    )
    reviewer_input = (
        f"AUFGABE: {aufgabe}\n\n"
        f"LETZTE COMMITS:\n{historie[:3000]}\n\n"
        f"{overview}\n\n"
        "Waehle optionale Messungen. Antworte mit COMMAND-Zeilen:\n"
        "COMMAND: RUN <id>\n"
        "COMMAND: RUN read_file <pfad>"
    )
    try:
        require_budget(state, max_llm)
    except BudgetExhausted as exc:
        print(f"[!] {exc}")
        return 13
    reply = ask_llm(api_key, reviewer_prompt, reviewer_input,
                    state.reviewer_verdict_model, 0.0, state.llm_timeout_s)
    if not reply.ok:
        print(f"[FAIL] Reviewer: {reply.error}")
        audit("reviewer_call_failed", {"error": reply.error}, project_dir, project_name)
        return 2
    state.llm_calls += 1

    commands = parse_commands(reply.content)
    if commands:
        print(f"[i] Reviewer fordert {len(commands)} optionale Messungen.")
        execute_commands(state, commands, quelle="reviewer")
    else:
        print("[i] Reviewer fordert keine optionalen Messungen.")

    # ==================================================================
    # SCHRITT 2: Builder baut Code-Entwurf
    # ==================================================================
    print("\n[*] Schritt 2: Builder baut Code-Entwurf.")
    builder_prompt = build_system_prompt(state.agents["builder"], state.docs,
                                         state.agent_docs.get("builder", []))
    try:
        require_budget(state, max_llm)
    except BudgetExhausted as exc:
        print(f"[!] {exc}")
        return 13
    reply = ask_llm(
        api_key, builder_prompt,
        f"BASIS-GATE:\n{state.basis_protokoll[:1500]}\n\n"
        f"OPTIONALE MESSUNGEN:\n{state.mess_protokoll or '(keine)'}\n\n"
        f"AUFGABE: {aufgabe}\n\n"
        "Liefere einen Code-Entwurf als Text.",
        state.builder_model, state.builder_temp, state.llm_timeout_s,
    )
    if not reply.ok:
        print(f"[FAIL] Builder: {reply.error}")
        audit("builder_call_failed", {"error": reply.error}, project_dir, project_name)
        return 4
    state.llm_calls += 1
    state.code_entwurf = reply.content

    # ==================================================================
    # SCHRITT 3: Review-Schleife (Phase 1)
    # ==================================================================
    max_rounds = budget.get("max_review_rounds", 5)
    verdict = "UNKLAR"
    for runde in range(1, max_rounds + 1):
        if state.llm_calls >= max_llm:
            print(f"[!] LLM-Budget erschoepft ({state.llm_calls}/{max_llm}).")
            v = ask_reviewer_for_recovery(state, "budget",
                                          f"Runden: {runde-1}, LLM: {state.llm_calls}")
            print_recovery(v)
            return 13

        print(f"\n[--- Review-Runde {runde} ---]")

        # Auflage 2045: bisherige Runden mitgeben.
        # Der Reviewer soll sehen, was er in Runde 1..N-1 gesagt hat,
        # damit er pruefen kann, ob die Auflagen umgesetzt wurden.
        runden_block = ""
        if state.review_runden:
            zeilen = ["BISHERIGE RUNDEN:"]
            for r in state.review_runden:
                raw = r.get("raw", "")
                if len(raw) > 1500:
                    raw = raw[:1500] + " [... gekuerzt ...]"
                zeilen.append(f"[ROUND {r['runde']} - {r['verdict']}]")
                zeilen.append(raw)
            runden_block = "\n".join(zeilen) + "\n\n"

        szenario = (
            f"{runden_block}"
            f"BASIS-GATE:\n{state.basis_protokoll[:800]}\n\n"
            f"OPTIONALE MESSUNGEN:\n{state.mess_protokoll or '(keine)'}\n\n"
            f"CODE-ENTWURF:\n{state.code_entwurf}\n\n"
            f"TEST-VORSCHLAEGE:\n{state.test_vorschlaege or '(keine)'}\n\n"
            "Bewerte. Erste Zeile: GO, NO-GO oder ESKALATION."
        )
        try:
            require_budget(state, max_llm)
        except BudgetExhausted as exc:
            print(f"[!] {exc}")
            v = ask_reviewer_for_recovery(state, "budget",
                                          f"Runden: {runde-1}, LLM: {state.llm_calls}")
            print_recovery(v)
            return 13
        reply = ask_llm(api_key, reviewer_prompt, szenario,
                        state.reviewer_verdict_model, 0.0, state.llm_timeout_s)
        if not reply.ok:
            print(f"[FAIL] Reviewer: {reply.error}")
            audit("reviewer_call_failed", {"error": reply.error, "runde": runde},
                  project_dir, project_name)
            return 5
        state.llm_calls += 1

        verdict = classify_verdict(reply.content)
        state.review_runden.append(
            {"runde": runde, "verdict": verdict, "raw": reply.content})
        state.auflagen_log.append(parse_auflagen(reply.content))
        state.empfehlung_log.append(parse_empfehlung(reply.content))
        audit("review_round", {"runde": runde, "verdict": verdict}, project_dir, project_name)

        if verdict == "COMMAND":
            cmds = parse_commands(reply.content)
            execute_commands(state, cmds, quelle="reviewer")
            continue

        if verdict == "ESKALATION":
            print(f"[!] ESKALATION:\n{reply.content[:500]}")
            v = ask_reviewer_for_recovery(state, "eskalation", reply.content)
            print_recovery(v)
            return 14

        if verdict == "NO-GO":
            print(f"[-] NO-GO:\n{reply.content[:300]}")
            try:
                require_budget(state, max_llm)
            except BudgetExhausted as exc:
                print(f"[!] {exc}")
                v = ask_reviewer_for_recovery(state, "budget",
                                              f"Runden: {runde}, LLM: {state.llm_calls}")
                print_recovery(v)
                return 13
            bauer_reply = ask_llm(
                api_key, builder_prompt,
                f"Reviewer NO-GO:\n{reply.content}\n\nUeberarbeite.",
                state.builder_model, state.builder_temp, state.llm_timeout_s,
            )
            if bauer_reply.ok:
                state.code_entwurf = bauer_reply.content
                state.llm_calls += 1
            continue

        if verdict == "GO":
            print("[+] Code-GO erhalten.")
            break

    if verdict != "GO":
        kontext = (
            f"Nach {max_rounds} Runden kein GO. Letzte Antwort:\n"
            f"{state.review_runden[-1]['raw'] if state.review_runden else '(keine)'}"
        )
        v = ask_reviewer_for_recovery(state, "no_go", kontext)
        print_recovery(v)
        audit("recovery_no_go", {"empfehlung": v.empfehlung}, project_dir, project_name)
        return 15

    # ==================================================================
    # SCHRITT 4: Coverage + ggf. Test-Generator + Chaos
    # ==================================================================
    print("\n[*] Schritt 4: Coverage und optionale Test-Generierung.")

    # Coverage laeuft nur, wenn im Katalog vorhanden
    if "coverage" in state.optional:
        print("[*] Coverage-Lauf.")
        execute_commands(state, [{"id": "coverage", "arg": ""}], quelle="reviewer")
        cov_file = project_dir / "coverage.json"
        if cov_file.exists():
            try:
                cov = json.loads(cov_file.read_text(encoding="utf-8"))
                state.coverage_pct = int(
                    cov.get("totals", {}).get("percent_covered", -1))
                print(f"[i] Coverage: {state.coverage_pct}%")
            except (OSError, ValueError):
                print("[WARN] coverage.json nicht lesbar.")
                state.coverage_pct = -1
        else:
            print("[WARN] coverage.json fehlt nach Coverage-Lauf.")
            state.coverage_pct = -1

        # Fail closed: unbekannte Coverage wird wie "< 80%" behandelt.
        if state.coverage_pct < 0 or state.coverage_pct < int(COVERAGE_MIN_PCT):
            print(f"[i] Coverage < {COVERAGE_MIN_PCT}%. Test-Generator wird gerufen.")
            tg_prompt = build_system_prompt(
                state.agents["test_generator"], state.docs,
                state.agent_docs.get("test_generator", []))
            reply = ask_llm(
                api_key, tg_prompt,
                f"Ungetestete Bereiche (Coverage {state.coverage_pct}%):\n"
                f"CODE-BASIS:\n{state.code_entwurf[:3000]}\n\n"
                "Liefere Test-Vorschlaege als Text. Kein Schreiben.",
                state.test_gen_model, 0.3, state.llm_timeout_s,
            )
            if reply.ok:
                state.test_vorschlaege = reply.content
                state.llm_calls += 1

    if "chaos_probe" in state.optional:
        print("[*] Chaos-Probe.")
        execute_commands(state, [{"id": "chaos_probe", "arg": ""}], quelle="reviewer")

    # ==================================================================
    # SCHRITT 5: Reviewer-Phase 2 (Commit-Review)
    # ==================================================================
    if config.get("review_commit_package", True):
        print("\n[*] Schritt 5: Commit-Paket bauen und reviewen.")

        state.commit_paket = build_commit_paket(state)
        if not state.commit_paket.get("message"):
            print("[!] Commit-Paket leer. Kein Commit moeglich.")
            state.commit_paket["message"] = "(leer, Builder hat nichts geliefert)"

        commit_input = (
            f"CODE-GO ist erteilt. Pruefe das Commit-Paket.\n\n"
            f"COMMIT-MESSAGE:\n{state.commit_paket.get('message', '')}\n\n"
            f"BETROFFENE DATEIEN:\n" +
            "\n".join(f"  - {d}" for d in state.commit_paket.get("dateien", [])) +
            "\n\nDOKU-PATCHES:\n" +
            "\n".join(
                f"  - {p['pfad']}: {p['anker'][:60]}... -> {p['ersatz'][:60]}..."
                for p in state.commit_paket.get("doku_patches", [])) +
            "\n\nAUFLAGEN AUS DIESER RUNDE:\n"
            + "; ".join(state.auflagen_log[-1] if state.auflagen_log else [])
            + "\n\nAntworte mit COMMIT-GO, COMMIT-NO-GO oder COMMIT-ESKALATION."
        )
        try:
            require_budget(state, max_llm)
        except BudgetExhausted as exc:
            print(f"[!] {exc}")
            return 13
        reply = ask_llm(api_key, reviewer_prompt, commit_input,
                        state.reviewer_verdict_model, 0.0, state.llm_timeout_s)
        if not reply.ok:
            print(f"[FAIL] Reviewer Commit-Review: {reply.error}")
            return 6
        state.llm_calls += 1

        commit_verdict = classify_verdict(reply.content)
        state.commit_review = {"verdict": commit_verdict, "raw": reply.content}
        audit("commit_review", {"verdict": commit_verdict}, project_dir, project_name)

        if commit_verdict == "COMMIT-NO-GO":
            print(f"[-] Commit-NO-GO:\n{reply.content[:400]}")
            # Zurueck an den Builder: neues Commit-Paket
            try:
                require_budget(state, max_llm)
            except BudgetExhausted as exc:
                print(f"[!] {exc}")
                return 13
            bauer_reply = ask_llm(
                api_key, builder_prompt,
                f"Reviewer hat das Commit-Paket abgelehnt:\n{reply.content}\n\n"
                "Liefere ein ueberarbeitetes Commit-Paket (Message, Dateien, Doku-Patches).",
                state.builder_model, state.builder_temp, state.llm_timeout_s,
            )
            if bauer_reply.ok:
                state.commit_paket = parse_commit_paket(bauer_reply.content)
                state.llm_calls += 1

    # ==================================================================
    # SCHRITT 6: Approval-Dokument + Human-Gate
    # ==================================================================
    print_approval_dokument(state)

    print("\n" + "=" * 70)
    print("ENTSCHEIDUNG: [j] approve / [n] reject / [e] eskalation")
    print("=" * 70)
    try:
        wahl = input("Deine Wahl: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\n[*] Abbruch.")
        audit("pipeline_abgebrochen", {}, project_dir, project_name)
        return 0

    if wahl in {"j", "ja", "y", "yes"}:
        print("[+] Approved.")
        audit("pipeline_approved", {"runden": len(state.review_runden)},
              project_dir, project_name)

        if not config.get("require_human_approval", True):
            print("[!] require_human_approval=False. Ueberspringe Commit.")
            return 0

        if apply_commit_and_doku(state, state.commit_paket):
            audit("commit_applied", {}, project_dir, project_name)
            return 0
        else:
            print("[!] Commit fehlgeschlagen. Manuell nachholen.")
            return 20

    if wahl in {"n", "no", "nein"}:
        print("[-] Rejected.")
        grund = ""
        try:
            grund = input("Begruendung (leer = keine): ").strip()
        except (EOFError, KeyboardInterrupt):
            pass
        audit("pipeline_rejected",
              {"runden": len(state.review_runden), "grund_kurz": grund[:200]},
              project_dir, project_name)
        return 0

    print("[!] Eskalation.")
    audit("pipeline_escalated", {"runden": len(state.review_runden)},
          project_dir, project_name)
    return 0



def main() -> int:
    """CLI-Einstieg.

    Nutzung:
      pipeline.py --project <name> "<Block-Beschreibung>"

    Erwartet DEEPSEEK_API_KEY in der Umgebung.
    Liest die Projekt-Konfiguration aus /opt/werkstatt/projects/<name>.yaml.
    Darf NICHT als root laufen (Audit-Rechte, Git-Rechte).
    """
    # Guard: nicht als root. Sonst Exit 66.
    # Die Pipeline laeuft als Projekt-User (z.B. security-ai, xyapp).
    # Als root wuerden Audit-Logs root:root gehoeren und der
    # Service-User koennte sie nicht mehr lesen (SECURITY_REVIEW_LOG Punkt 12).
    import getpass
    aktueller_user = getpass.getuser()
    if aktueller_user == "root":
        print("[FAIL] Pipeline darf NICHT als root laufen.")
        print("[FAIL] Aufruf: runuser -u <projekt-user> -- ...")
        print("[FAIL] Beispiel: runuser -u security-ai -- ...")
        return 66

    args = sys.argv[1:]
    project_name: str | None = None

    if args and args[0] == "--project":
        if len(args) < 3:
            print("[FAIL] --project braucht einen Namen und eine Aufgabe.")
            print('Nutzung: pipeline.py --project <name> "<Block-Beschreibung>"')
            return 64
        project_name = args[1].strip()
        aufgabe = args[2].strip()
    else:
        print("[FAIL] --project <name> fehlt.")
        print('Nutzung: pipeline.py --project <name> "<Block-Beschreibung>"')
        print()
        print("Beispiel:")
        print('  DEEPSEEK_API_KEY=sk-... runuser -u security-ai -- \\')
        print("    /opt/security-ai/.venv/bin/python3 \\")
        print('    /opt/werkstatt/pipeline.py --project security-ai "Punkt 58 Schritt 6"')
        return 64

    if not project_name:
        print("[FAIL] Leerer Projektname.")
        return 65
    if not aufgabe:
        print("[FAIL] Leere Block-Beschreibung.")
        return 65

    try:
        return run_pipeline(project_name, aufgabe)
    except KeyboardInterrupt:
        print("\n[*] Abbruch durch Strg+C.")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"[FAIL] Unerwarteter Fehler: {exc}")
        import traceback
        traceback.print_exc()
        return 99


if __name__ == "__main__":
    sys.exit(main())
