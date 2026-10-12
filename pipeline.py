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

# Auflage 2132: Format fuer Commit-Paket (Erstbau + Neubau).
# Wird an zwei Stellen verwendet (build_commit_paket und
# COMMIT-NO-GO-Builder-Neubau), damit sie nicht divergieren.
COMMIT_PAKET_FORMAT = (
    "Format (verbindlich):\n"
    "COMMIT-MESSAGE:\n"
    "<Message mit den fuenf Pflichtabschnitten>\n"
    "ENDE COMMIT-MESSAGE\n\n"
    "BETROFFENE DATEIEN:\n"
    "  - <pfad relativ zum Projekt>\n"
    "ENDE BETROFFENE DATEIEN\n\n"
    "Pflichtabschnitte der Commit-Message (alle fuenf):\n"
    "  - Ausgangslage: warum diese Aenderung?\n"
    "  - Aenderung: was wurde geaendert?\n"
    "  - Tests: welche Tests, Testzahl konkret gemessen.\n"
    "  - Verifikation: ruff, mypy, pytest.\n"
    "  - Reviewed: Reviewer-Verdict mit Auflagen.\n\n"
    "Platzhalter (wie '<N>') sind verboten. Zahlen MUESSEN konkret sein.\n\n"
    "HINWEIS: Die Datei-Aenderungen sind bereits angewendet.\n"
    "Der Commit uebernimmt den echten Zustand (git diff)."
)

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


def require_budget_time(state: RunState, max_minutes: int) -> None:
    """Auflage 2080: prueft das Zeitbudget vor LLM-Aufrufen.

    Wirft BudgetExhausted, wenn die verstrichene Zeit seit
    state.start_monotonic groesser ist als max_minutes * 60
    Sekunden. Bei genau == max*60 wird noch nicht ausgeloest
    (der erste Check nach Ueberschreitung greift).

    max_minutes <= 0 deaktiviert die Pruefung.
    start_monotonic <= 0 heisst "nicht gesetzt", ebenfalls
    keine Pruefung (Tests koennen den Wert so umgehen).
    """
    if max_minutes <= 0:
        return
    if state.start_monotonic <= 0:
        return
    verstrichen = time.monotonic() - state.start_monotonic
    grenze = max_minutes * 60
    if verstrichen > grenze:
        raise BudgetExhausted(
            f"Zeitbudget erschoepft: {verstrichen:.1f}s / {grenze}s"
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


def _werkstatt_home() -> Path:
    """Liefert das Werkstatt-Heimverzeichnis.

    Auflage 2110: Das ist der Pfad, in dem pipeline.py liegt.
    Nicht der CWD, nicht das Projekt. Damit landet Audit
    immer in /opt/werkstatt/audit-logs/, egal von wo der
    Aufruf kommt. Tests koennen diese Funktion mocken,
    um in ein tmp_path zu schreiben.
    """
    return Path(__file__).resolve().parent


def audit(kind: str, payload: dict[str, Any], project_dir: Path,
          project_name: str) -> None:
    """Schreibt einen Audit-Eintrag.

    Auflage 2043: project_name wird explizit uebergeben. Keine
    Modul-Variable mehr, keine unsichtbare Kopplung.
    """
    # Auflage 2110: Audit schreibt in die Werkstatt, nicht
    # ins Ziel-Projekt. Grund: Trennung Bau-User (Werkstatt)
    # von Service-User (Projekt). Werkstatt-Audit ist
    # projektuebergreifend, mit project-Feld im Eintrag.
    # project_dir wird nicht mehr fuer die Lokation genutzt,
    # bleibt aber Parameter (Aufrufer unveraendert).
    audit_dir = _werkstatt_home() / AUDIT_DIR_NAME
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



def subprocess_env() -> dict[str, str]:
    """Erlaubt nur die Umgebungsvariablen, die Subprozesse brauchen.

    Auflage 2086: DEEPSEEK_API_KEY und andere Secrets werden
    NICHT durchgereicht. Allowlist statt Blacklist, damit neue
    Secrets nicht automatisch im Subprozess-Env landen.

    Erweiterung: Wenn ein Subprozess eine weitere Variable
    braucht, wird sie hier EXPLIZIT ergaenzt.
    """
    erlaubt = (
        "PATH", "HOME", "LANG", "LC_ALL", "LC_CTYPE",
        "TMPDIR", "USER", "SHELL",
    )
    return {k: os.environ[k] for k in erlaubt if k in os.environ}


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
            (venv, "-m", "compileall", "-q", "apps", "core", "harness", "tools", "scripts", "tests"),
            "Python-Syntax-Check.", 300),
        "ruff": Measurement("ruff", (venv, "-m", "ruff", "check", "."), "Lint."),
        "mypy": Measurement("mypy",
            (venv, "-m", "mypy", "apps", "core", "harness", "tools", "scripts"), "Typen.", 300),
        # Auflage 2159: mypy ueber tests/ liefert 1337 Fehler
        # (fehlende Annotations). Deshalb nicht in always_run,
        # sondern optional. Der Reviewer-Agent kann es anfordern.
        "mypy_tests": Measurement("mypy_tests",
            (venv, "-m", "mypy", "tests"), "Typen in tests/.", 300),
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


def run_measurement_mit_argv(m: Measurement, whitelist: list[str],
                             project_dir: Path, extra_arg: str | None = None
                             ) -> tuple[str, bool, list[str]]:
    """Fuehrt eine Messung aus und gibt (out, ok, argv) zurueck.

    Auflage 2040: argv wird mitgegeben, damit der Aufrufer
    das tatsaechlich verwendete Kommando protokollieren kann.

    Auflage 2076: Dies ist die einzige Arbeitsfunktion.
    run_measurement() ist ein Wrapper, der argv wegwirft.
    """
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
                             text=True, timeout=m.timeout_s, check=False,
                             env=subprocess_env())
    except subprocess.TimeoutExpired:
        return f"TIMEOUT {m.timeout_s}s", False, argv
    except OSError as exc:
        return f"OSError: {exc}", False, argv
    out = (f"=== {m.mid} ===\nARGV: {' '.join(argv)}\nRC: {res.returncode}\n"
           f"STDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}\n")
    return out, res.returncode == 0, argv


def run_measurement(m: Measurement, whitelist: list[str], project_dir: Path,
                    extra_arg: str | None = None) -> tuple[str, bool]:
    """Wrapper um run_measurement_mit_argv, wirft argv weg.

    Auflage 2076: Konsolidierung. Die Arbeitslogik liegt
    in run_measurement_mit_argv.
    """
    out, ok, _argv = run_measurement_mit_argv(
        m, whitelist, project_dir, extra_arg,
    )
    return out, ok



@dataclass
class LLMReply:
    ok: bool
    content: str = ""
    error: str = ""


def ask_llm(api_key: str, system_prompt: str, user_content: str,
            model: str, temperature: float, timeout: int = 120,
            *, state: RunState | None = None) -> LLMReply:
    """Fragt das LLM.

    Auflage 2125: Wenn `state` uebergeben wird, zaehlt
    der Aufruf in state.llm_calls — unabhaengig davon,
    ob der Call erfolgreich ist. Fehlschlaege zaehlen
    ebenfalls (konservativ, Budget-Schutz).
    """
    if state is not None:
        state.llm_calls += 1
    # Redaction: vor dem Senden anwenden
    # Auflage 2113: max_len=100_000, damit Block-Auftraege
    # groesser 2000 Zeichen nicht abgeschnitten werden.
    # Analog 2089 (System-Prompt).
    user_content, _ = redaction.redact_all(user_content, max_len=100000)
    system_prompt, _ = redaction.redact_all(system_prompt, max_len=100000)
    headers: dict[str, str] = {"Authorization": f"Bearer {api_key}",
                              "Content-Type": "application/json"}
    payload: dict[str, Any] = {"model": model,
                               "messages": [{"role": "system", "content": system_prompt},
                                            {"role": "user", "content": user_content}],
                               "temperature": temperature}
    # Auflage 2087: Retry nur bei 429 (Rate Limit) und 5xx
    # (Server-Fehler). Kein Retry bei 4xx — ein Auth-Fehler
    # wuerde sich endlos wiederholen.
    # Max 2 Versuche. Backoff: 1s, dann 3s.
    backoffs = (1, 3)
    letzter_fehler: str = ""
    res = None
    for versuch, warte in enumerate(backoffs, start=1):
        try:
            res = requests.post(DEEPSEEK_API_URL, headers=headers,
                                json=payload, timeout=timeout)
        except requests.RequestException as exc:
            letzter_fehler = f"HTTP: {exc}"
            res = None
        else:
            if res.status_code == 200:
                break
            # Nur 429 und 5xx werden wiederholt.
            if res.status_code != 429 and res.status_code < 500:
                return LLMReply(
                    ok=False,
                    error=f"HTTP {res.status_code}: {res.text[:200]}",
                )
            letzter_fehler = f"HTTP {res.status_code}: {res.text[:200]}"
        if versuch < len(backoffs):
            time.sleep(warte)

    if res is None:
        return LLMReply(ok=False, error=letzter_fehler)
    if res.status_code != 200:
        return LLMReply(ok=False, error=letzter_fehler)
    try:
        data = res.json()
        return LLMReply(ok=True, content=data["choices"][0]["message"]["content"])
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        return LLMReply(ok=False, error=f"Parsing: {exc}")


def classify_verdict(text: str) -> str:
    """Erkennt GO / NO-GO / ESKALATION / COMMIT-* / COMMAND.

    Auflage 2077: Satzzeichen am Wortende werden gestrippt,
    damit "GO.", "NO-GO:" und "ESKALATION!" erkannt werden.
    Der Bindestrich bleibt Teil des Tokens (NO-GO), sonst
    wuerde "NO-GO." als "NO" gelesen.
    """
    satzzeichen = ".,;:!?)"
    gezaehlt = 0
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        gezaehlt += 1
        if gezaehlt > 15:
            break
        w = s.split(maxsplit=1)[0].upper().rstrip(satzzeichen)
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
            timeout=30, check=False, env=subprocess_env(),
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
    start_monotonic: float = 0.0  # Auflage 2080: Zeitmessung
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
    basis_protokoll_nach_apply: str = ""  # UMB-1b
    mess_protokoll: str = ""
    code_entwurf: str = ""
    code_patches: list[dict[str, str]] = field(default_factory=list)  # UMB-1b
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
                            timeout=300, check=False, env=subprocess_env())
        protokoll += f"=== ruff check --fix ===\nRC: {r1.returncode}\n{r1.stdout}\n{r1.stderr}\n"
        r2 = subprocess.run((venv_python, "-m", "ruff", "format", "."),
                            cwd=str(project_dir), capture_output=True, text=True,
                            timeout=300, check=False, env=subprocess_env())
        protokoll += f"=== ruff format ===\nRC: {r2.returncode}\n{r2.stdout}\n{r2.stderr}\n"
        r3 = subprocess.run((venv_python, "-m", "ruff", "check", "."),
                            cwd=str(project_dir), capture_output=True, text=True,
                            timeout=300, check=False, env=subprocess_env())
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
    frage_an_menschen: str = ""
    rohantwort: str = ""


def aufgabe_block(state: RunState) -> str:
    """Auflage 2154: zentrale Formatierung des Auftrags.

    Liefert "AUFGABE: <auftrag>\n\n". Wird in allen
    Reviewer- und Builder-Prompts verwendet, damit
    der Auftrag konsistent ist.
    """
    return f"AUFGABE: {state.aufgabe}\n\n"


def ask_reviewer_for_recovery(state: RunState, art: str, kontext: str) -> RecoveryVorschlag:
    # Auflage 2153: Auftrag vor dem Kontext.
    kopf = aufgabe_block(state)
    if art == "basis_gate":
        aufgabe = ("Das Basis-Gate ist rot und der deterministische "
                   "Auto-Repair-Versuch ist gescheitert.\n\n"
                   f"{kopf}{kontext}\n\n"
                   "Liefere:\nDIAGNOSE: <Ursache>\nREPARATURPLAN:\n  1. ...\n"
                   "  2. ...\nBLOCKGROESSE: <ein Block | mehrere Bloecke | eigener Punkt>\n"
                   "EMPFEHLUNG: <was der Mensch tun soll>\n")
    elif art == "no_go":
        aufgabe = (f"Der Builder hat kein akzeptables Ergebnis geliefert.\n\n{kopf}{kontext}\n\n"
                   "Liefere:\nDIAGNOSE: <warum>\nLOESUNGSVORSCHLAG:\n  1. ...\n  2. ...\n"
                   "BLOCKGROESSE: <...>\nEMPFEHLUNG: <approve | reject | aufteilen | eskalieren>\n")
    elif art == "eskalation":
        aufgabe = (f"Du hast ESKALATION ausgesprochen.\n\n{kopf}{kontext}\n\n"
                   "Liefere:\nDIAGNOSE: <Kern>\nFRAGE AN DEN MENSCHEN: <was>\n"
                   "OPTIONEN:\n  A) ...\n  B) ...\nBLOCKGROESSE: <...>\n"
                   "EMPFEHLUNG: <welche Option>\n")
    elif art == "budget":
        aufgabe = (f"Das Budget ist erschoepft.\n\n{kopf}{kontext}\n\n"
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
        state=state,
    )
    if not reply.ok:
        return RecoveryVorschlag(art=art,
                                 diagnose="(Reviewer nicht erreichbar)",
                                 empfehlung=f"API-Fehler: {reply.error}",
                                 rohantwort=reply.error)
    v = RecoveryVorschlag(art=art, rohantwort=reply.content)
    abschnitt = None
    for line in reply.content.splitlines():
        s = line.strip()
        if s.upper().startswith("DIAGNOSE:"):
            v.diagnose = s.split(":", 1)[1].strip()
            abschnitt = None
        elif s.upper().startswith("FRAGE AN DEN MENSCHEN:"):
            v.frage_an_menschen = s.split(":", 1)[1].strip()
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
    if v.frage_an_menschen:
        print(f"\nFRAGE AN DEN MENSCHEN:\n  {v.frage_an_menschen}")
    if v.empfehlung:
        print(f"\nEMPFEHLUNG: {v.empfehlung}")
    print("\n--- ROHE ANTWORT ---")
    print(v.rohantwort)
    print("=" * 70)



def budget_or_recover(state: RunState, max_llm: int, kontext: str,
                      project_dir: Path, project_name: str,
                      max_minutes: int = 0) -> int | None:
    """Auflage 2081 + 2080: einheitlicher Budget-Check mit Recovery.

    Prueft LLM-Budget (max_llm) und Zeitbudget (max_minutes).
    Bei BudgetExhausted (aus beiden Dimensionen):
    - ruft ask_reviewer_for_recovery("budget", kontext) auf,
    - gibt den Vorschlag aus,
    - schreibt recovery_budget ins Audit,
    - liefert Exit-Code 13.
    Sonst None (Aufrufer faehrt normal fort).

    Der Recovery-Kontext enthaelt beide Dimensionen,
    damit der Reviewer weiss, welche erschoepft ist (P3).
    """
    try:
        require_budget(state, max_llm)
        require_budget_time(state, max_minutes)
    except BudgetExhausted as exc:
        print(f"[!] {exc}")
        # P3: Kontext um beide Dimensionen ergaenzen.
        verstrichen_s = 0.0
        if state.start_monotonic > 0:
            verstrichen_s = time.monotonic() - state.start_monotonic
        kontext_voll = (
            f"{kontext}\n"
            f"LLM: {state.llm_calls}/{max_llm}, "
            f"Zeit: {verstrichen_s:.0f}s/{max_minutes * 60}s"
        )
        v = ask_reviewer_for_recovery(state, "budget", kontext_voll)
        print_recovery(v)
        audit("recovery_budget", {"kontext": kontext_voll},
              project_dir, project_name)
        return 13
    return None


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
        paket["doku_patches"] = _parse_patches(m.group(1))

    return paket


def parse_code_patches(text: str) -> list[dict[str, str]]:
    """UMB-1a: parst die Builder-Antwort fuer Code-Patches.

    Format: direkt PATCH-BEGINN/PATCH-ENDE-Bloecke, ohne
    Container-Marker.

      PATCH-BEGINN
      pfad: tools/disk_usage.py
      anker: |
        <alter Text>
      ersatz: |
        <neuer Text>
      PATCH-ENDE

      PATCH-BEGINN
      ...
      PATCH-ENDE

    Liefert eine Liste von Patches. Leere Liste, wenn
    keine Patches gefunden wurden.
    """
    return _parse_patches(text)


def _shift_lines(text: str, prefix: str = "  ") -> str:
    """Auflage 2165: ergaenzt jede nicht-leere Zeile um prefix.

    Wird fuer die Einrueckungs-Normalisierung verwendet:
    Der Builder liefert Anker/Ersatz oft um 2 Spaces
    zu kurz. Wenn der Anker nur in der +2-Variante
    genau 1x matcht, korrigieren wir.
    """
    zeilen = text.split("\n")
    return "\n".join(
        (prefix + z) if z else z for z in zeilen
    )


def apply_code_patches(state: RunState,
                       patches: list[dict[str, str]],
                       dry_run: bool = False) -> bool:
    """UMB-1a: wendet Code-Patches an (In-Memory-Rollback).

    Pruefungen pro Patch:
      - pfad in state.file_whitelist
      - Datei existiert
      - pfad nicht doppelt in patches
      - Anker count == 1

    Bei dry_run: nur pruefen, nichts schreiben.

    Bei Fehler: nichts wurde geschrieben, return False.
    Wenn spaeter etwas fehlschlaegt (theoretisch nicht
    nach Vollvalidierung): In-Memory-Rollback.
    """
    # ---- Phase 1: Validierung ----
    if not patches:
        print("[!] apply_code_patches: keine Patches.")
        return False
    gesehen: set[Path] = set()
    original: dict[Path, str] = {}
    plan: list[tuple[Path, str, str]] = []
    for p in patches:
        pfad = p.get("pfad", "")
        anker = p.get("anker", "")
        ersatz = p.get("ersatz", "")
        if not pfad:
            print("[!] apply_code_patches: Patch ohne pfad.")
            return False
        if not any(pfad.startswith(w) for w in state.file_whitelist):
            print(f"[!] apply_code_patches: Pfad nicht in "
                  f"Whitelist: {pfad}")
            return False
        ziel = state.project_dir / pfad
        if not ziel.exists():
            print(f"[!] apply_code_patches: Datei fehlt: {pfad}")
            return False
        if ziel in gesehen:
            print(f"[!] apply_code_patches: Pfad doppelt: {pfad}")
            return False
        gesehen.add(ziel)
        inhalt = ziel.read_text(encoding="utf-8")
        count = inhalt.count(anker)
        # Auflage 2161: Pruefe Zeilen-Anfang.
        am_anfang = (
            inhalt.startswith(anker)
            or ("\n" + anker) in inhalt
        )
        # Auflage 2165: Einrueckungs-Normalisierung.
        # Der Builder liefert Anker/Ersatz oft um 2 Spaces
        # zu kurz. Korrektur, wenn:
        #   - count != 1 (kein exakter Match), ODER
        #   - nicht am Zeilen-Anfang (Substring-Match).
        # UND die +2-Variante genau 1x am Zeilen-Anfang
        # matcht.
        if count != 1 or not am_anfang:
            anker_plus = _shift_lines(anker, "  ")
            plus_count = inhalt.count(anker_plus)
            plus_am_anfang = (
                inhalt.startswith(anker_plus)
                or ("\n" + anker_plus) in inhalt
            )
            if plus_count == 1 and plus_am_anfang:
                print(f"[i] apply_code_patches: Anker in {pfad} "
                      f"um 2 Spaces verschoben. Korrigiere.")
                audit("anker_einrueckung_korrigiert",
                      {"pfad": pfad}, state.project_dir,
                      state.project_name)
                anker = anker_plus
                ersatz = _shift_lines(ersatz, "  ")
                p["anker"] = anker
                p["ersatz"] = ersatz
                count = 1
                am_anfang = True
        if count != 1:
            print(f"[!] apply_code_patches: Anker in {pfad} "
                  f"kommt {count}x vor. Erwartet 1x.")
            return False
        if not am_anfang:
            print(f"[!] apply_code_patches: Anker in {pfad} "
                  f"steht nicht am Zeilen-Anfang. Fail closed.")
            return False
        original[ziel] = inhalt
        plan.append((ziel, anker, ersatz))

    if dry_run:
        print(f"[i] apply_code_patches (dry_run): "
              f"{len(plan)} Patches validiert.")
        return True

    # ---- Phase 2: Anwendung ----
    geschrieben: list[Path] = []
    try:
        for ziel, anker, ersatz in plan:
            neu = original[ziel].replace(anker, ersatz, 1)
            ziel.write_text(neu, encoding="utf-8")
            geschrieben.append(ziel)
            print(f"[+] Code gepatcht: {ziel.relative_to(state.project_dir)}")
    except OSError as exc:
        print(f"[!] apply_code_patches: Schreibfehler: {exc}")
        # Rollback
        for ziel in geschrieben:
            try:
                ziel.write_text(original[ziel], encoding="utf-8")
            except OSError as exc2:
                print(f"[!] Rollback fehlgeschlagen fuer {ziel}: {exc2}")
        return False

    return True


def _parse_patches(block_text: str) -> list[dict[str, str]]:
    """Parst PATCH-BEGINN/PATCH-ENDE-Bloecke (Auflagen 2088 + 2098).

    Wird sowohl fuer DOKU-PATCHES (parse_commit_paket) als
    auch fuer CODE-PATCHES (parse_code_patches) verwendet.
    

    Format:
      PATCH-BEGINN
      pfad: docs/PHASES.md
      anker: |
        <mehrzeilig>
      ersatz: |
        <mehrzeilig, darf leer sein>
      PATCH-ENDE

    Regeln:
    - Reihenfolge von pfad/anker/ersatz ist frei (P2).
    - Einrueckung ist 2 Spaces, Tabs werden abgelehnt (P1).
    - anker fehlt oder leer -> Patch verworfen.
    - pfad fehlt oder leer -> Patch verworfen.
    - ersatz darf leer sein (Loeschung).
    """
    ergebnis: list[dict[str, str]] = []
    # Bloecke an PATCH-BEGINN/PATCH-ENDE trennen.
    for match in re.finditer(
        r"PATCH-BEGINN\s*\n(.*?)\n\s*PATCH-ENDE",
        block_text, re.DOTALL,
    ):
        block = match.group(1)
        gepatcht = _parse_einzelpatch(block)
        if gepatcht is not None:
            ergebnis.append(gepatcht)
    return ergebnis


def _parse_einzelpatch(block: str) -> dict[str, str] | None:
    """Parst einen einzelnen PATCH-BEGINN-Block.

    Liefert dict oder None, wenn der Block ungueltig ist.
    """
    pfad = ""
    anker: str | None = None
    ersatz: str | None = None
    aktives_feld: str | None = None
    aktuelle_zeilen: list[str] = []

    def _flush() -> None:
        nonlocal aktives_feld, aktuelle_zeilen
        if aktives_feld is None:
            return
        wert = "\n".join(aktuelle_zeilen)
        if aktives_feld == "anker":
            nonlocal anker
            anker = wert
        elif aktives_feld == "ersatz":
            nonlocal ersatz
            ersatz = wert
        elif aktives_feld == "pfad":
            nonlocal pfad
            pfad = wert.strip()
        aktives_feld = None
        aktuelle_zeilen = []

    for raw_line in block.splitlines():
        # Tabs ablehnen (P1).
        if "\t" in raw_line:
            return None
        # Feld-Anfang?
        m_feld = re.match(r"^(pfad|anker|ersatz):\s*(.*)$", raw_line)
        if m_feld:
            _flush()
            name, rest = m_feld.group(1), m_feld.group(2)
            if name == "pfad":
                if rest.startswith("|"):
                    # pfad als Block-Scalar ist erlaubt,
                    # wird aber praktisch selten genutzt.
                    aktives_feld = "pfad"
                    aktuelle_zeilen = []
                else:
                    pfad = rest.strip()
            else:
                # anker / ersatz muessen "|" haben (YAML-Block).
                if not rest.startswith("|"):
                    return None
                aktives_feld = name
                aktuelle_zeilen = []
            continue
        # Fortsetzungszeile (eingrueckt, 2 Spaces).
        if aktives_feld is not None:
            if raw_line.startswith("  "):
                aktuelle_zeilen.append(raw_line[2:])
            elif raw_line.strip() == "":
                # Leerzeile im Block erlaubt.
                aktuelle_zeilen.append("")
            else:
                # Ende des Block-Scalars.
                _flush()
        # Sonst: ignorieren (z.B. Leerzeile ausserhalb).

    _flush()

    # Validierung.
    if not pfad:
        return None
    if anker is None or anker == "":
        return None
    if ersatz is None:
        ersatz = ""
    return {"pfad": pfad, "anker": anker, "ersatz": ersatz}


def apply_and_recheck(state: RunState,
                      always: dict[str, Measurement],
                      file_whitelist: list[str]) -> int | None:
    """UMB-1d: wendet Code-Patches an und prueft das Basis-Gate erneut.

    Liefert None bei Erfolg, sonst einen Exit-Code:
      16: keine Code-Patches (Code-GO ohne Patches).
      17: apply_code_patches fehlgeschlagen.
      18: Basis-Gate nach Anwendung rot (Recovery wurde gerufen).
    """
    if not state.code_patches:
        print("[!] Code-GO, aber keine Code-Patches. Fail closed.")
        audit("code_patches_leer", {}, state.project_dir, state.project_name)
        return 16
    print(f"\n[*] Code-Patches anwenden ({len(state.code_patches)}).")
    ok_apply = apply_code_patches(state, state.code_patches)
    # Auflage 2157: Rohtext der Patches ins Audit (Diagnose).
    # Redaction auf anker/ersatz. Groesse begrenzt.
    patches_audit: list[dict[str, str]] = []
    for p in state.code_patches:
        anker = p.get("anker", "")
        ersatz = p.get("ersatz", "")
        anker_red, _ = redaction.redact_all(anker[:3000],
                                             max_len=100000)
        ersatz_red, _ = redaction.redact_all(ersatz[:3000],
                                              max_len=100000)
        patches_audit.append({
            "pfad": p.get("pfad", ""),
            "anker": anker_red,
            "ersatz": ersatz_red,
        })
    audit("code_patches_apply", {"ok": ok_apply,
                                  "anzahl": len(state.code_patches),
                                  "patches": patches_audit},
          state.project_dir, state.project_name)
    if not ok_apply:
        print("[!] apply_code_patches fehlgeschlagen. Fail closed.")
        return 17

    print("[*] Basis-Gate nach Anwendung (ohne git_status).")
    state.basis_protokoll_nach_apply = ""
    nach_fehler: list[str] = []
    for mid, m in always.items():
        if mid in ("git_status", "git_head"):
            continue
        out, ok_m = run_measurement(m, file_whitelist, state.project_dir)
        state.basis_protokoll_nach_apply += out
        if not ok_m:
            nach_fehler.append(mid)
            print(f"[!] Basis-Gate-nach-apply rot: {mid}")
        else:
            print(f"[+] Basis-Gate-nach-apply gruen: {mid}")
    if nach_fehler:
        print(f"[!] Basis-Gate-nach-apply rot: {nach_fehler}")
        v = ask_reviewer_for_recovery(
            state, "basis_gate",
            f"Nach Anwendung der Code-Patches: {nach_fehler}\n\n"
            f"Protokoll:\n{state.basis_protokoll_nach_apply[:3000]}")
        print_recovery(v)
        audit("recovery_basis_gate_nach_apply",
              {"fehler": nach_fehler, "empfehlung": v.empfehlung},
              state.project_dir, state.project_name)
        return 18
    return None


def collect_messwerte(state: RunState) -> dict[str, Any]:
    """Auflage 2135: extrahiert Messwerte aus dem Basis-Protokoll.

    Liefert ein dict mit den Werten, die der Builder fuer die
    Commit-Message braucht:
      - test_anzahl (int | None)
      - ruff (gruen|rot)
      - mypy (gruen|rot)
      - py_compile (gruen|rot)
      - git_status (clean|geaendert)
      - git_head (str)
      - verstrichene_zeit_s (float)

    Basis: state.basis_protokoll (geschrieben vom Basis-Gate).
    Fallback bei Parse-Fehler: test_anzahl = None, sonst "rot".
    """
    import re as _re
    basis = state.basis_protokoll or ""

    # Pro Messung: (mid, rc, stdout)
    treffer = _re.findall(
        r"=== (\w+) ===\nARGV: [^\n]*\nRC: (\d+)\nSTDOUT:\n(.*?)STDERR:",
        basis, _re.DOTALL,
    )
    werte: dict[str, Any] = {
        "test_anzahl": None,
        "ruff": "rot",
        "mypy": "rot",
        "py_compile": "rot",
        "git_status": "geaendert",
        "git_head": "",
        "verstrichene_zeit_s": 0.0,
    }
    for mid, rc_str, stdout in treffer:
        rc = int(rc_str)
        if mid == "test_count":
            m = _re.search(r"(\d+) tests? collected", stdout)
            if m:
                werte["test_anzahl"] = int(m.group(1))
        elif mid == "ruff":
            werte["ruff"] = "gruen" if rc == 0 else "rot"
        elif mid == "mypy":
            werte["mypy"] = "gruen" if rc == 0 else "rot"
        elif mid == "py_compile":
            werte["py_compile"] = "gruen" if rc == 0 else "rot"
        elif mid == "git_status":
            werte["git_status"] = ("clean"
                                   if stdout.strip() == ""
                                   else "geaendert")
        elif mid == "git_head":
            werte["git_head"] = stdout.strip()

    # Verstrichene Zeit aus start_monotonic
    if state.start_monotonic > 0:
        werte["verstrichene_zeit_s"] = (
            time.monotonic() - state.start_monotonic)

    return werte


def extract_paths_from_aufgabe(aufgabe: str,
                                file_whitelist: list[str],
                                project_dir: Path) -> list[str]:
    """Auflage 2146: extrahiert Datei-Pfade aus dem Auftrag.

    Regex findet Pfade mit Endung .py/.md/.yaml/.yml.
    Filter: Pfad muss in file_whitelist liegen und
    Datei muss existieren. Dedupliziert.
    """
    if not aufgabe:
        return []
    kandidaten = re.findall(
        r"[a-zA-Z0-9_./-]+\.(?:py|md|yaml|yml)",
        aufgabe,
    )
    ergebnis: list[str] = []
    gesehen: set[str] = set()
    for p in kandidaten:
        # Fuehrende Slashes entfernen (z.B. aus "/opt/...").
        p = p.lstrip("/")
        if p in gesehen:
            continue
        if not any(p.startswith(w) for w in file_whitelist):
            continue
        if not (project_dir / p).exists():
            continue
        gesehen.add(p)
        ergebnis.append(p)
    return ergebnis


def read_target_snippets(paths: list[str],
                        project_dir: Path,
                        file_whitelist: list[str],
                        max_len: int = 3000) -> str:
    """Auflage 2146: Ausschnitte aus den Zieldateien.

    Fail closed bei Pfad ausserhalb file_whitelist.
    Redaction auf die Ausschnitte.
    """
    if not paths:
        return "(keine Zieldateien im Auftrag erkannt)"
    teile = ["ZIELDATEIEN (Ausschnitte aus den zu patchenden Dateien):"]
    for p in paths:
        if not any(p.startswith(w) for w in file_whitelist):
            print(f"[WARN] read_target_snippets: "
                  f"Pfad ausserhalb Whitelist: {p}")
            continue
        ziel = project_dir / p
        if not ziel.exists():
            print(f"[WARN] read_target_snippets: "
                  f"Datei fehlt: {p}")
            continue
        try:
            inhalt = ziel.read_text(encoding="utf-8")
        except OSError as exc:
            print(f"[WARN] read_target_snippets: "
                  f"Lesefehler {p}: {exc}")
            continue
        ausschnitt = inhalt[:max_len]
        ausschnitt, _ = redaction.redact_all(
            ausschnitt, max_len=100000)
        teile.append(f"--- {p} ---")
        teile.append(ausschnitt)
    return "\n".join(teile)


def format_doc_snippets(docs: dict[str, str],
                        max_len: int = 3000) -> str:
    """Auflage 2142: Ausschnitte aus den Doku-Dateien fuer den Builder.

    Der Builder braucht konkrete Anker-Texte aus den
    Zieldateien, um gueltige Doku-Patches zu bauen.
    Ohne diese Ausschnitte liefert er eine Rueckfrage
    (Befund S aus Probebetrieb 10).

    Pro Datei: max_len Zeichen Anfang. Redaction zuerst
    (Secrets-Schutz), max_len=100000 damit die Grenze
    nicht durch Redaction weiter gekuerzt wird.
    """
    if not docs:
        return "(keine Doku geladen)"
    teile = ["DOKU-AUSSCHNITTE (Auszug aus den Zieldateien):"]
    for key, inhalt in docs.items():
        ausschnitt = inhalt[:max_len]
        ausschnitt, _ = redaction.redact_all(
            ausschnitt, max_len=100000)
        teile.append(f"--- {key} ---")
        teile.append(ausschnitt)
    return "\n".join(teile)


def format_messwerte_block(werte: dict[str, Any]) -> str:
    """Formatiert die Messwerte fuer den Builder-Prompt.

    Auflage 2135: Der Builder verwendet diese Werte woertlich.
    """
    test_anzahl = werte.get("test_anzahl")
    test_str = str(test_anzahl) if test_anzahl is not None else "nicht gemessen"
    return (
        "MESSWERTE (von der Werkstatt gemessen, nicht schaetzen):\n"
        f"  test_anzahl: {test_str}\n"
        f"  ruff: {werte.get('ruff', 'rot')}\n"
        f"  mypy: {werte.get('mypy', 'rot')}\n"
        f"  py_compile: {werte.get('py_compile', 'rot')}\n"
        f"  git_status: {werte.get('git_status', 'geaendert')}\n"
        f"  git_head: {werte.get('git_head', '')}\n"
        f"  verstrichene_zeit_s: {werte.get('verstrichene_zeit_s', 0.0):.0f}"
    )


def build_commit_paket(state: RunState) -> dict[str, Any]:
    """Bittet den Builder um einen Commit-Paket-Vorschlag.

    Der Builder sieht: letzten Commit, Code-Entwurf, Reviewer-Verdict,
    sowie die betroffenen Dateien.
    """
    letzter = subprocess.run(
        ("git", "log", "-1", "--format=%B"),
        cwd=str(state.project_dir), capture_output=True, text=True,
        timeout=30, check=False, env=subprocess_env(),
    ).stdout
    # UMB-1c: git diff als Basis (die Aenderungen sind angewendet).
    git_diff = subprocess.run(
        ("git", "diff", "--stat"),
        cwd=str(state.project_dir), capture_output=True, text=True,
        timeout=30, check=False, env=subprocess_env(),
    ).stdout
    git_diff_voll = subprocess.run(
        ("git", "diff"),
        cwd=str(state.project_dir), capture_output=True, text=True,
        timeout=30, check=False, env=subprocess_env(),
    ).stdout
    git_status = subprocess.run(
        ("git", "status", "--porcelain"),
        cwd=str(state.project_dir), capture_output=True, text=True,
        timeout=30, check=False, env=subprocess_env(),
    ).stdout

    aufgabe = (
        "Der Code-Review ist abgeschlossen. Der Reviewer hat "
        "in der letzten Runde GO gegeben. Die Code-Patches "
        "sind bereits angewendet.\n\n"
        "Baue das Commit-Paket:\n"
        "1. Commit-Message im Format des letzten Commits.\n"
        "2. Liste der betroffenen Dateien (basierend auf "
        "git status/git diff).\n\n"
        "Achte auf die Auflagen des Reviewers (unten).\n\n"
        f"LETZTER COMMIT (Format-Referenz):\n{letzter}\n\n"
        f"GIT STATUS (die zu committenden Dateien):\n{git_status}\n\n"
        f"GIT DIFF --STAT:\n{git_diff}\n\n"
        f"GIT DIFF (gekuerzt):\n{git_diff_voll[:4000]}\n\n"
        f"REVIEWER-VERDICT:\n"
        f"{state.review_runden[-1]['raw'] if state.review_runden else '(keins)'}\n\n"
        + format_messwerte_block(collect_messwerte(state)) + "\n\n"
        "Antworte in genau diesem Format:\n\n"
        + COMMIT_PAKET_FORMAT
    )

    # Auflage 2124: einmaliger Retry bei reply.ok=False.
    # Kein Retry bei reply.ok=True und leerem Paket
    # (das ist ein Prompt-Problem, kein Transport-Problem).
    antworten: list = []
    for versuch in (1, 2):
        reply = ask_llm(
            state.api_key,
            build_system_prompt(state.agents["builder"], state.docs,
                                state.agent_docs.get("builder", [])),
            aufgabe,
            state.builder_model,
            state.builder_temp,
            state.llm_timeout_s,
            state=state,
        )
        antworten.append(reply)
        if reply.ok:
            break
        if versuch == 1:
            # Nur einmal wiederholen.
            print(f"[i] build_commit_paket: Versuch 1 "
                  f"fehlgeschlagen ({reply.error}). "
                  f"Einmaliger Retry.")
            audit("builder_commit_paket_failed",
                  {"error": reply.error, "versuch": 1},
                  state.project_dir, state.project_name)
            max_llm = state.budget.get("max_llm_calls", 20)
            rc = budget_or_recover(
                state, max_llm, "Vor Commit-Paket-Retry.",
                state.project_dir, state.project_name)
            if rc is not None:
                # Recovery wurde bereits aufgerufen.
                return {"message": "", "dateien": [],
                        "doku_patches": [],
                        "error": f"budget_or_recover rc={rc}"}
            continue
        # Versuch 2: endgueltig fehlgeschlagen.
        print(f"[!] build_commit_paket: Versuch 2 "
              f"fehlgeschlagen ({reply.error}). Kein weiterer Retry.")
        audit("builder_commit_paket_failed_retry",
              {"error": reply.error, "versuch": 2},
              state.project_dir, state.project_name)
        return {"message": "", "dateien": [], "doku_patches": [],
                "error": reply.error}

    if not reply.ok:
        # Fallback (nicht erreichbar nach dem Loop).
        return {"message": "", "dateien": [], "doku_patches": [],
                "error": reply.error}

    paket = parse_commit_paket(reply.content)
    paket["roh"] = reply.content
    # Auflage 2123: Audit, wenn das Paket leer geparst wurde.
    if not paket.get("message") and not paket.get("dateien") \
            and not paket.get("doku_patches"):
        # Auflage 2133: Roh-Text ins Audit (Debug).
        # Redaction zuerst (Secrets-Schutz), max_len=100000
        # damit die 3000 Zeichen nicht weiter gekuerzt werden.
        roh, _ = redaction.redact_all(
            reply.content[:3000], max_len=100000)
        audit("commit_paket_leer",
              {"roh_len": len(reply.content),
               "roh": roh}, state.project_dir,
              state.project_name)
    return paket


def apply_commit_and_doku(state: RunState, paket: dict[str, Any]) -> bool:
    """Wendet Doku-Patches an und committet.

    NUR nach Human-Gate. Explizite Datei-Liste, kein git add -A.

    Auflage 2082: Validieren vor Schreiben. In-Memory-Rollback
    fuer Doku-Dateien, falls git add oder git commit fehlschlaegt.
    """
    # ---- Phase 1: Validieren (nichts schreiben) ----
    dateien = paket.get("dateien", [])
    if not dateien:
        print("[!] Keine betroffenen Dateien angegeben. Abbruch.")
        return False
    for pfad in dateien:
        if not any(pfad.startswith(w) for w in state.file_whitelist):
            print(f"[!] Datei nicht in Whitelist: {pfad}")
            return False
        # Auflage 2048: Datei muss existieren.
        if not (state.project_dir / pfad).exists():
            print(f"[!] Datei existiert nicht: {pfad}")
            return False

    doku_patches = paket.get("doku_patches", [])
    doku_ziele: dict[Path, str] = {}
    for patch in doku_patches:
        ziel = state.project_dir / patch["pfad"]
        if not ziel.exists():
            print(f"[!] Doku-Datei fehlt: {patch['pfad']}")
            return False
        if ziel in doku_ziele:
            print(f"[!] Doku-Datei mehrfach im Paket: {patch['pfad']}")
            return False
        text = ziel.read_text(encoding="utf-8")
        count = text.count(patch["anker"])
        if count != 1:
            print(f"[!] Anker in {patch['pfad']} kommt {count}x vor. "
                  f"Erwartet: 1x. Abbruch.")
            return False
        doku_ziele[ziel] = text

    # ---- Phase 2: Doku-Patches schreiben + Original merken ----
    original: dict[Path, str] = {}
    for patch in doku_patches:
        ziel = state.project_dir / patch["pfad"]
        original[ziel] = doku_ziele[ziel]
        neu = doku_ziele[ziel].replace(patch["anker"], patch["ersatz"], 1)
        ziel.write_text(neu, encoding="utf-8")
        print(f"[+] Doku gepatcht: {patch['pfad']}")

    def _rollback_doku() -> None:
        """Schreibt Doku-Dateien auf Original-Inhalt zurueck."""
        for ziel, inhalt in original.items():
            try:
                ziel.write_text(inhalt, encoding="utf-8")
            except OSError as exc:
                print(f"[!] Rollback fehlgeschlagen fuer {ziel}: {exc}")

    # ---- Phase 3: git add ----
    argv_add = ("git", "add", "--") + tuple(dateien)
    res_add = subprocess.run(
        argv_add, cwd=str(state.project_dir),
        capture_output=True, text=True, timeout=60, check=False,
        env=subprocess_env(),
    )
    if res_add.returncode != 0:
        print(f"[!] git add fehlgeschlagen: {res_add.stderr}")
        _rollback_doku()
        return False

    # ---- Phase 4: git commit ----
    msg_datei = state.project_dir / ".commit-msg.tmp"
    msg_datei.write_text(paket["message"], encoding="utf-8")
    commit_argv: list[str] = ["git"]
    if state.git_author_name:
        commit_argv += ["-c", f"user.name={state.git_author_name}"]
    if state.git_author_email:
        commit_argv += ["-c", f"user.email={state.git_author_email}"]
    commit_argv += ["commit", "-F", str(msg_datei)]

    try:
        res_commit = subprocess.run(
            tuple(commit_argv),
            cwd=str(state.project_dir), capture_output=True, text=True,
            timeout=60, check=False, env=subprocess_env(),
        )
    finally:
        msg_datei.unlink(missing_ok=True)

    if res_commit.returncode != 0:
        print(f"[!] git commit fehlgeschlagen: {res_commit.stderr}")
        # git add rueckgaengig, dann Doku zurueck.
        subprocess.run(
            ("git", "reset", "HEAD", "--") + tuple(dateien),
            cwd=str(state.project_dir),
            capture_output=True, text=True, timeout=60, check=False,
            env=subprocess_env(),
        )
        _rollback_doku()
        return False

    # ---- Phase 5: Bestaetigung ----
    log = subprocess.run(
        ("git", "log", "-1", "--oneline"),
        cwd=str(state.project_dir), capture_output=True, text=True,
        timeout=30, check=False, env=subprocess_env(),
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
    if state.start_monotonic > 0:
        verstr = time.monotonic() - state.start_monotonic
        print(f"Verstrichen: {verstr:.0f}s")

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
    max_minutes = budget.get("max_minutes", 0)  # Auflage 2080: 0 = aus

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
    # Auflage 2080: Startzeitpunkt fuer das Zeitbudget.
    state.start_monotonic = time.monotonic()

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
        aufgabe_block(state)
        + f"LETZTE COMMITS:\n{historie[:3000]}\n\n"
        f"{overview}\n\n"
        "Waehle optionale Messungen. Antworte mit COMMAND-Zeilen:\n"
        "COMMAND: RUN <id>\n"
        "COMMAND: RUN read_file <pfad>"
    )
    rc = budget_or_recover(state, max_llm,
                          "Vor Reviewer-Auswahl optionale Messungen.",
                          project_dir, project_name,
                          max_minutes=max_minutes)
    if rc is not None:
        return rc
    reply = ask_llm(api_key, reviewer_prompt, reviewer_input,
                    state.reviewer_verdict_model, 0.0, state.llm_timeout_s,
                    state=state)
    if not reply.ok:
        print(f"[FAIL] Reviewer: {reply.error}")
        audit("reviewer_call_failed", {"error": reply.error}, project_dir, project_name)
        return 2

    commands = parse_commands(reply.content)
    if commands:
        print(f"[i] Reviewer fordert {len(commands)} optionale Messungen.")
        execute_commands(state, commands, quelle="reviewer")
    else:
        print("[i] Reviewer fordert keine optionalen Messungen.")

    # ==================================================================
    # SCHRITT 2: Builder baut Code-Entwurf
    # ==================================================================
    print("\n[*] Schritt 2: Builder baut Code-Patches (UMB-1b).")
    builder_prompt = build_system_prompt(state.agents["builder"], state.docs,
                                         state.agent_docs.get("builder", []))
    rc = budget_or_recover(state, max_llm,
                          "Vor Builder-Aufruf (Code-Patches).",
                          project_dir, project_name,
                          max_minutes=max_minutes)
    if rc is not None:
        return rc
    ziel_pfade = extract_paths_from_aufgabe(
        aufgabe, file_whitelist, project_dir)
    ziel_snippets = read_target_snippets(
        ziel_pfade, project_dir, file_whitelist)
    reply = ask_llm(
        api_key, builder_prompt,
        f"BASIS-GATE:\n{state.basis_protokoll[:1500]}\n\n"
        f"OPTIONALE MESSUNGEN:\n{state.mess_protokoll or '(keine)'}\n\n"
        + format_doc_snippets(state.docs) + "\n\n"
        + ziel_snippets + "\n\n"
        + aufgabe_block(state)
        + "Liefere strukturierte Code-Patches im Format "
        "PATCH-BEGINN/PATCH-ENDE.\n"
        "Format und Einrueckungs-Regeln stehen im "
        "System-Prompt (Abschnitt 'EINRUECKUNG UND "
        "YAML-BLOCK').\n\n"
        "Mehrere Patches hintereinander "
        "(jeweils PATCH-BEGINN/PATCH-ENDE).\n"
        "Kein freier Text. Kein Markdown. Nur Patches.\n"
        "Wenn du einen Anker nicht im Ausschnitt findest: "
        "keinen Patch fuer diese Datei. Kein Erfinden.",
        state.builder_model, state.builder_temp, state.llm_timeout_s,
        state=state,
    )
    if not reply.ok:
        print(f"[FAIL] Builder: {reply.error}")
        audit("builder_call_failed", {"error": reply.error}, project_dir, project_name)
        return 4
    state.code_entwurf = reply.content
    state.code_patches = parse_code_patches(reply.content)
    print(f"[i] {len(state.code_patches)} Code-Patches geparst.")

    # ==================================================================
    # SCHRITT 3: Review-Schleife (Phase 1)
    # ==================================================================
    max_rounds = budget.get("max_review_rounds", 5)
    verdict = "UNKLAR"
    for runde in range(1, max_rounds + 1):
        # Auflage 2078: der inline-Budget-Check ist entfernt.
        # Der Check erfolgt direkt vor dem Reviewer-Call via
        # budget_or_recover (siehe unten).

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
            # Auflage 2152: Auftrag MUSS im Szenario stehen.
            aufgabe_block(state)
            + f"{runden_block}"
            f"BASIS-GATE:\n{state.basis_protokoll[:800]}\n\n"
            f"OPTIONALE MESSUNGEN:\n{state.mess_protokoll or '(keine)'}\n\n"
            f"CODE-ENTWURF:\n{state.code_entwurf}\n\n"
            f"TEST-VORSCHLAEGE:\n{state.test_vorschlaege or '(keine)'}\n\n"
            "Bewerte. Erste Zeile: GO, NO-GO oder ESKALATION."
        )
        rc = budget_or_recover(state, max_llm,
                              f"Vor Reviewer-Verdict Runde {runde}.",
                              project_dir, project_name,
                              max_minutes=max_minutes)
        if rc is not None:
            return rc
        reply = ask_llm(api_key, reviewer_prompt, szenario,
                        state.reviewer_verdict_model, 0.0, state.llm_timeout_s,
                        state=state)
        if not reply.ok:
            print(f"[FAIL] Reviewer: {reply.error}")
            audit("reviewer_call_failed", {"error": reply.error, "runde": runde},
                  project_dir, project_name)
            return 5

        verdict = classify_verdict(reply.content)
        state.review_runden.append(
            {"runde": runde, "verdict": verdict, "raw": reply.content})
        state.auflagen_log.append(parse_auflagen(reply.content))
        state.empfehlung_log.append(parse_empfehlung(reply.content))
        audit("review_round", {"runde": runde, "verdict": verdict}, project_dir, project_name)

        if verdict == "COMMAND":
            cmds = parse_commands(reply.content)
            execute_commands(state, cmds, quelle="reviewer")
            # Auflage 2145: Audit fuer COMMAND in der Review-
            # Schleife. Sonst ist nicht sichtbar, wann der
            # Reviewer COMMAND nutzt.
            audit("review_command",
                  {"runde": runde, "anzahl": len(cmds)},
                  project_dir, project_name)
            continue

        if verdict == "ESKALATION":
            print(f"[!] ESKALATION:\n{reply.content[:500]}")
            v = ask_reviewer_for_recovery(state, "eskalation", reply.content)
            print_recovery(v)
            audit("recovery_eskalation",
                  {"frage_an_menschen": v.frage_an_menschen[:500],
                   "empfehlung": v.empfehlung[:500]},
                  project_dir, project_name)
            return 14

        if verdict == "NO-GO":
            print(f"[-] NO-GO:\n{reply.content[:300]}")
            rc = budget_or_recover(state, max_llm,
                                  f"Vor Builder-Neubau (NO-GO Runde {runde}).",
                                  project_dir, project_name,
                                  max_minutes=max_minutes)
            if rc is not None:
                return rc
            bauer_reply = ask_llm(
                api_key, builder_prompt,
                f"Reviewer NO-GO:\n{reply.content}\n\nUeberarbeite.",
                state.builder_model, state.builder_temp, state.llm_timeout_s,
                state=state,
            )
            if bauer_reply.ok:
                state.code_entwurf = bauer_reply.content
            continue

        if verdict == "GO":
            # Auflage 2117: GO mit Auflagen -> eine weitere Runde.
            auflagen = (state.auflagen_log[-1]
                        if state.auflagen_log else [])
            if auflagen and runde < max_rounds:
                print(f"[i] Code-GO mit {len(auflagen)} Auflagen. "
                      "Weitere Runde zur Umsetzung.")
                rc = budget_or_recover(
                    state, max_llm,
                    f"Vor Builder-Aufruf (Auflagen-Umsetzung Runde {runde}).",
                    project_dir, project_name,
                    max_minutes=max_minutes)
                if rc is not None:
                    return rc
                auflagen_text = "\n".join(f"- {a}" for a in auflagen)
                bauer_reply = ask_llm(
                    api_key, builder_prompt,
                    f"Der Reviewer hat GO gegeben, aber folgende "
                    f"Auflagen formuliert:\n{auflagen_text}\n\n"
                    "Ueberarbeite die Code-Patches, um die Auflagen "
                    "umzusetzen. Antworte mit den ueberarbeiteten "
                    "PATCH-BEGINN/PATCH-ENDE-Bloecken. Kein freier Text.",
                    state.builder_model, state.builder_temp,
                    state.llm_timeout_s,
                    state=state,
                )
                if bauer_reply.ok:
                    state.code_entwurf = bauer_reply.content
                    state.code_patches = parse_code_patches(
                        bauer_reply.content)
                    print(f"[i] {len(state.code_patches)} Code-Patches "
                          f"nach Auflagen-Umsetzung geparst.")
                continue
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
    # UMB-1d: Code-Patches anwenden + Basis-Gate erneut
    # ==================================================================
    rc_apply = apply_and_recheck(state, always, file_whitelist)
    if rc_apply is not None:
        return rc_apply

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
                state=state,
            )
            if reply.ok:
                state.test_vorschlaege = reply.content

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

        # Auflage 2118: Commit-NO-GO-Loop, max 2 Versuche.
        max_commit_versuche = 2
        commit_versuche = 0
        while True:
            # Auflage 2120: leere Auflagen explizit 'keine'.
            auflagen_letzte = (state.auflagen_log[-1]
                               if state.auflagen_log
                                  and state.auflagen_log[-1]
                               else [])
            auflagen_text = ("; ".join(auflagen_letzte)
                             if auflagen_letzte else "keine")

            commit_input = (
                f"CODE-GO ist erteilt. Pruefe das Commit-Paket.\n\n"
                f"COMMIT-MESSAGE:\n{state.commit_paket.get('message', '')}\n\n"
                f"BETROFFENE DATEIEN:\n" +
                "\n".join(
                    f"  - {d}"
                    for d in state.commit_paket.get("dateien", [])) +
                "\n\nDOKU-PATCHES:\n" +
                "\n".join(
                    f"  - {p['pfad']}: {p['anker'][:60]}... -> "
                    f"{p['ersatz'][:60]}..."
                    for p in state.commit_paket.get("doku_patches", [])) +
                f"\n\nAUFLAGEN AUS DIESER RUNDE:\n{auflagen_text}\n\n"
                "Antworte mit COMMIT-GO, COMMIT-NO-GO oder "
                "COMMIT-ESKALATION."
            )
            rc = budget_or_recover(state, max_llm,
                                  "Vor Commit-Review.",
                                  project_dir, project_name,
                                  max_minutes=max_minutes)
            if rc is not None:
                return rc
            reply = ask_llm(api_key, reviewer_prompt, commit_input,
                            state.reviewer_verdict_model, 0.0,
                            state.llm_timeout_s,
                            state=state)
            if not reply.ok:
                print(f"[FAIL] Reviewer Commit-Review: {reply.error}")
                return 6

            commit_verdict = classify_verdict(reply.content)
            state.commit_review = {"verdict": commit_verdict,
                                   "raw": reply.content}
            # Auflage 2138: Rohtext ins Audit (Debug).
            roh, _ = redaction.redact_all(
                reply.content[:3000], max_len=100000)
            audit("commit_review",
                  {"verdict": commit_verdict,
                   "runde": commit_versuche,
                   "roh": roh},
                  project_dir, project_name)

            if commit_verdict == "COMMIT-GO":
                print("[+] Commit-GO erhalten.")
                break

            if commit_verdict != "COMMIT-NO-GO":
                # ESKALATION / UNKLAR: Stop, Mensch entscheidet am Gate.
                print(f"[i] Commit-Review-Verdict: {commit_verdict}. "
                      "Kein Loop.")
                break

            # COMMIT-NO-GO
            print(f"[-] Commit-NO-GO (Versuch {commit_versuche + 1}/"
                  f"{max_commit_versuche}):\n{reply.content[:400]}")
            commit_versuche += 1
            if commit_versuche >= max_commit_versuche:
                print("[!] Commit-Review: maximale Versuche erreicht.")
                return 7

            rc = budget_or_recover(state, max_llm,
                                  "Vor Builder-Neubau (Commit-NO-GO).",
                                  project_dir, project_name,
                                  max_minutes=max_minutes)
            if rc is not None:
                return rc
            bauer_reply = ask_llm(
                api_key, builder_prompt,
                f"Der Reviewer hat das vorherige Commit-Paket "
                f"mit COMMIT-NO-GO abgelehnt.\n"
                f"Begruendung (Kontext, NICHT die "
                f"Reviewed-Zeile):\n{reply.content}\n\n"
                + format_messwerte_block(collect_messwerte(state)) + "\n\n"
                + format_doc_snippets(state.docs) + "\n\n"
                "Liefere ein ueberarbeitetes Commit-Paket.\n\n"
                "WICHTIG: Der Reviewed-Block der neuen Message "
                "spiegelt den Code-Review-Verdict DIESER Runde "
                "(CODE-GO), nicht den vorherigen COMMIT-NO-GO. "
                "Der vorherige NO-GO ist Kontext, keine "
                "Verdict-Quelle.\n\n"
                + COMMIT_PAKET_FORMAT,
                state.builder_model, state.builder_temp,
                state.llm_timeout_s,
                state=state,
            )
            if not bauer_reply.ok:
                print(f"[FAIL] Builder Commit-Paket-Neubau: "
                      f"{bauer_reply.error}")
                # Auflage 2128: Audit fuer den Fehlerpfad.
                audit("builder_commit_paket_failed_retry",
                      {"error": bauer_reply.error,
                       "versuch": commit_versuche},
                      project_dir, project_name)
                return 8
            state.commit_paket = parse_commit_paket(bauer_reply.content)
            # Auflage 2128: Audit, wenn der Neubau leer ist.
            if not state.commit_paket.get("message") \
                    and not state.commit_paket.get("dateien") \
                    and not state.commit_paket.get("doku_patches"):
                # Auflage 2133: Roh-Text ins Audit (Debug).
                roh, _ = redaction.redact_all(
                    bauer_reply.content[:3000], max_len=100000)
                audit("commit_paket_leer",
                      {"runde": commit_versuche,
                       "roh_len": len(bauer_reply.content),
                       "roh": roh},
                      project_dir, project_name)

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
    #
    # Auflage 2085: primär os.getuid() == 0 pruefen (deterministisch,
    # nicht von Env abhaengig). getpass.getuser() nur ergaenzend und
    # in try/except, weil es bei fehlenden Env-Variablen fehlschlagen
    # kann (KeyError/OSError). Bei Fehler: nicht abstuerzen, sondern
    # nur informieren.
    if os.getuid() == 0:
        print("[FAIL] Pipeline darf NICHT als root laufen "
              "(os.getuid() == 0).")
        print("[FAIL] Aufruf: runuser -u <projekt-user> -- ...")
        print("[FAIL] Beispiel: runuser -u security-ai -- ...")
        return 66
    import getpass
    try:
        aktueller_user = getpass.getuser()
    except (KeyError, OSError) as exc:
        print(f"[WARN] getpass.getuser() fehlgeschlagen: {exc}")
        aktueller_user = ""
    if aktueller_user == "root":
        print("[FAIL] Pipeline darf NICHT als root laufen "
              "(getpass.getuser() == 'root').")
        print("[FAIL] Aufruf: runuser -u <projekt-user> -- ...")
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
