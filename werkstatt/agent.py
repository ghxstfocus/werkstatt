"""LLM-Agent (A8-1a-1).

ask_llm aus pipeline.py extrahiert (2026-10-22).
Wortwoertliche Extraktion, keine Verhaltensaenderung.

Konsumenten: pipeline.py (via Re-Export).
"""
from __future__ import annotations

import hashlib
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

import requests

import redaction
from werkstatt.audit import audit
from werkstatt.model_routing import route_for_role
from werkstatt.state import LLMReply, Measurement, Messung, RunState
from werkstatt.subprocess_env import subprocess_env

DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"

_PROMPT_DUMP_DIR = Path("/tmp/werkstatt-prompts")


def _dump_prompt(aufgabe: str, model: str,
                 system_prompt: str, user_content: str) -> None:
    """Schreibt die wortwoertlichen Prompts nach /tmp/werkstatt-prompts/.

    Aktiv nur wenn WERKSTATT_PROMPT_DUMP=1 gesetzt ist.
    Pro Call zwei Dateien: <agent>_<ts>_system.txt und _user.txt.
    Zusaetzlich eine .meta.txt mit Modell + Laengen.
    """
    import os as _os
    if _os.environ.get("WERKSTATT_PROMPT_DUMP") != "1":
        return
    try:
        _PROMPT_DUMP_DIR.mkdir(parents=True, exist_ok=True)
        _ts = time.strftime("%Y%m%d-%H%M%S")
        # Nanosekunden-Suffix, damit schnelle Calls nicht kollidieren.
        _suffix = f"{time.monotonic_ns() % 1_000_000:06d}"
        _base = _PROMPT_DUMP_DIR / f"{aufgabe}_{_ts}_{_suffix}"
        (_base.with_name(_base.name + "_system.txt")
         ).write_text(system_prompt, encoding="utf-8")
        (_base.with_name(_base.name + "_user.txt")
         ).write_text(user_content, encoding="utf-8")
        (_base.with_name(_base.name + "_meta.txt")).write_text(
            f"agent={aufgabe}\n"
            f"model={model}\n"
            f"system_len={len(system_prompt)}\n"
            f"user_len={len(user_content)}\n"
            f"system_tokens_approx={len(system_prompt) // 4}\n"
            f"user_tokens_approx={len(user_content) // 4}\n",
            encoding="utf-8",
        )
    except (OSError, UnicodeError) as _exc:
        # GOLD 2026-10-30: Dump-Fehler ins Audit (Diagnose).
        # Vorher wurde der Fehler still verschluckt; das machte
        # fehlende Architect-Dumps unerklaerbar.
        try:
            from werkstatt.audit import audit as _audit
            _audit(
                "prompt_dump_fehler",
                {"agent": aufgabe, "model": model,
                 "exc_type": type(_exc).__name__,
                 "exc_str": str(_exc)[:300]},
                Path("/tmp"), "werkstatt",
            )
        except Exception:
            pass


def _heartbeat_start(
        stage_name: str,
        *,
        state: RunState | None = None,
        progress_context: dict[str, Any] | None = None,
) -> tuple[threading.Thread, threading.Event]:
    """Print 5s heartbeats and persist contextual progress every 15s.

    Gibt (thread, stop_event) zurueck. Der Aufrufer MUSS
    stop_event.set() und thread.join(timeout=1.0) im finally
    ausfuehren, damit der Thread beendet wird.
    """
    stop_event = threading.Event()
    start = time.monotonic()
    next_audit_at = 15
    context = _progress_context(state, progress_context)

    def _tick() -> None:
        nonlocal next_audit_at
        while not stop_event.is_set():
            elapsed = int(time.monotonic() - start)
            print(f"  ... {stage_name} laeuft ({elapsed}s)", flush=True)
            if state is not None and elapsed >= next_audit_at:
                payload = {
                    "agent": stage_name,
                    "elapsed_s": elapsed,
                    **context,
                    "result_summary": (
                        f"{_aufgabe_zu_label(stage_name)} arbeitet noch "
                        f"({elapsed}s)."
                    ),
                    "decision_summary": (
                        "Der Modellaufruf ist weiterhin aktiv; der Run wartet "
                        "auf die Antwort."
                    ),
                    "next_step": (
                        "Antwort entgegennehmen und den Rollen-Schritt fortsetzen."
                    ),
                }
                try:
                    audit(
                        "llm_call_heartbeat",
                        payload,
                        state.project_dir,
                        state.project_name,
                    )
                except Exception:
                    # Observability must not interrupt an in-flight model call.
                    pass
                next_audit_at += 15
            stop_event.wait(5)

    thread = threading.Thread(
        target=_tick, daemon=True, name=f"heartbeat-{stage_name}")
    thread.start()
    return thread, stop_event


def _progress_context(
    state: RunState | None,
    explicit: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return bounded task/file metadata; never include prompt or file contents."""
    task = getattr(state, "aktuelle_task", None) if state is not None else None
    task = task if isinstance(task, dict) else {}
    supplied = explicit if isinstance(explicit, dict) else {}

    task_id = str(supplied.get("task_id") or task.get("id") or "")[:100]
    task_name = str(supplied.get("task_name") or task.get("name") or "")[:160]
    files = supplied.get("files") or task.get("task_files") or []
    if isinstance(files, str):
        files = [files]
    safe_files = [
        str(path)[:240] for path in files
        if isinstance(path, str) and path.strip()
    ][:10]

    context: dict[str, Any] = {}
    if task_id:
        context["task_id"] = task_id
    if task_name:
        context["task_name"] = task_name
    if safe_files:
        context["files"] = safe_files
    return context


def _rolle_aus_aufgabe(aufgabe: str) -> str:
    """Mappt stabile Rollenlabels; freie Task-Namen bleiben unbekannt."""
    label = (aufgabe or "").strip().lower().replace("_", "-")
    if label in {"architect", "planner", "builder", "reviewer",
                 "reflection", "explorer", "scout", "debugger"}:
        return label
    if label.startswith("planner-"):
        return "planner"
    if label.startswith("reflection-"):
        return "reflection"
    return "unbekannt"


def _run_budget_limit(state: RunState) -> tuple[str, str] | None:
    """Liefert die erste erreichte harte Run-Grenze, falls vorhanden."""
    budget = state.budget if isinstance(state.budget, dict) else {}
    max_calls = budget.get("max_llm_calls")
    if (isinstance(max_calls, int) and not isinstance(max_calls, bool)
            and max_calls > 0 and state.llm_calls >= max_calls):
        return "max_llm_calls", f"LLM-Aufrufbudget erreicht ({max_calls})."

    max_minutes = budget.get("max_minutes")
    if (isinstance(max_minutes, int) and not isinstance(max_minutes, bool)
            and max_minutes > 0 and state.start_monotonic > 0):
        elapsed = time.monotonic() - state.start_monotonic
        if elapsed >= max_minutes * 60:
            elapsed_s = int(elapsed)
            reason = (
                f"Zeitbudget erreicht ({max_minutes} Minuten; "
                f"vergangen {elapsed_s} Sekunden)."
            )
            return "max_minutes", reason
    return None


def _enforce_run_budget(state: RunState) -> bool:
    """Mark a reached limit once and return whether this run must stop."""
    if state.budget_exhausted_reason:
        return True
    limit = _run_budget_limit(state)
    if limit is None:
        return False
    dimension, reason = limit
    state.budget_exhausted_reason = reason
    budget = state.budget if isinstance(state.budget, dict) else {}
    audit(
        "loop_budget_exhausted",
        {
            "dimension": dimension,
            "reason": reason,
            "llm_calls": state.llm_calls,
            "max_llm_calls": budget.get("max_llm_calls"),
            "max_minutes": budget.get("max_minutes"),
        },
        state.project_dir,
        state.project_name,
    )
    return True


def _ask_llm_impl(api_key: str, system_prompt: str, user_content: str,
            model: str, temperature: float, timeout: int = 120,
            *, state: RunState | None = None,
            aufgabe: str = "unbekannt",
            rolle: str | None = None,
            heartbeat: bool = True,
            max_tokens: int = 4096,
            redact: bool = True,
            progress_context: dict[str, Any] | None = None) -> LLMReply:
    """Fragt das LLM.

    Auflage 2125: Wenn `state` uebergeben wird, zaehlt
    der Aufruf in state.llm_calls — unabhaengig davon,
    ob der Call erfolgreich ist. Fehlschlaege zaehlen
    ebenfalls (konservativ, Budget-Schutz).
    """
    route = route_for_role(rolle or aufgabe, model)
    model = route.model
    if state is not None:
        if _enforce_run_budget(state):
            return LLMReply(ok=False, error=state.budget_exhausted_reason)
        state.llm_calls += 1
    # Redaction: vor dem Senden anwenden
    # Auflage 2113: max_len=100_000, damit Block-Auftraege
    # groesser 2000 Zeichen nicht abgeschnitten werden.
    # Analog 2089 (System-Prompt).
    # OP-062a: redact=False fuer Code-Pruef-Pfade (Builder, Reviewer).
    # Private IPs (10/8, 172.16/12, 192.168/16, 127/8) werden auch
    # bei redact=True nicht maskiert. Fuer die semantische Code-
    # Pruefung braucht der Reviewer aber auch oeffentliche Werte
    # (z.B. 1.1.1.1 in einem Test), sonst sieht er '[IPV4]' und
    # '[IPV4]' und kann sie nicht unterscheiden.
    if redact:
        user_content, _ = redaction.redact_all(user_content, max_len=100000)
        system_prompt, _ = redaction.redact_all(system_prompt, max_len=100000)
    headers: dict[str, str] = {"Authorization": f"Bearer {api_key}",
                              "Content-Type": "application/json"}
    payload: dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "thinking": {"type": route.thinking},
    }
    if route.reasoning_effort is not None:
        payload["reasoning_effort"] = route.reasoning_effort
    else:
        payload["temperature"] = temperature

    # MESS-1: Laengen nach Redaktion, vor HTTP. Werden in jeden
    # LLMReply-Return gesetzt und einmal pro Call auditiert.
    _system_len = len(system_prompt)
    _user_len = len(user_content)
    if state is not None:
        audit("llm_call",
              {"agent": aufgabe,
               "model": model,
               "system_len": _system_len,
               "user_len": _user_len,
               "max_tokens": max_tokens},
              state.project_dir,
              state.project_name)

    # Prompt-Dump (nur bei WERKSTATT_PROMPT_DUMP=1).
    _dump_prompt(aufgabe, model, system_prompt, user_content)
    # Timeout-Fix 2026-10-16 (Option B, HR-R7):
    # B1 (Read-Timeout) bricht haengende Calls ab.
    # B2 (Deadline) verhindert Folge-Versuche nach
    # Ueberschreitung. B1 ist primaer, B2 sekundaer.
    _CONNECT_S = 15  # Timeout-A1: 15s statt 10s.
    _READ_S = 180
    _max_total_s = int(
        getattr(state, "max_total_llm_s", 240)
        if state is not None else 240)
    # Zeitout-Verhaeltnis (Timeout-A2): read=180 deckt
    # einen einzelnen Call ab. max_total=240 erlaubt
    # 180 s + 60 s Nachlauf fuer einen Retry.
    _t0 = time.monotonic()
    _deadline = _t0 + _max_total_s
    # Auflage 2087: Retry nur bei 429 (Rate Limit) und 5xx
    # (Server-Fehler). Kein Retry bei 4xx — ein Auth-Fehler
    # wuerde sich endlos wiederholen.
    # Max 2 Versuche. Backoff: 1s, dann 3s.
    backoffs = (1, 3)
    letzter_fehler: str = ""
    res = None
    _versuche_absolut = 0
    for versuch, warte in enumerate(backoffs, start=1):
        # Timeout-A4: adaptive Restzeit pruefen.
        _rest = _deadline - time.monotonic()
        if _rest <= 0:
            if state is not None:
                audit("llm_timeout_gesamt",
                      {"modell": model,
                       "aufgabe": aufgabe,
                       "dauer_s": round(
                           time.monotonic() - _t0, 2),
                       "versuche": _versuche_absolut,
                       "deadline_s": _max_total_s,
                       "letzter_fehler":
                           letzter_fehler[:200]},
                      state.project_dir,
                      state.project_name)
            return LLMReply(
                ok=False,
                error=f"Gesamt-Timeout {_max_total_s}s",
                system_len=_system_len,
                user_len=_user_len,
            )
        # Read-Timeout adaptiv: min(read, restzeit).
        _read_adapt = int(min(_READ_S, max(1, _rest)))
        _req_timeout = (_CONNECT_S, _read_adapt)
        # SIM113: Retry-Loop mit variabler Laenge
        # (max len(backoffs)), enumerate ist hier
        # nicht passend (Abbruch durch break).
        _versuche_absolut += 1  # noqa: SIM113
        if heartbeat:
            hb_thread, hb_stop = _heartbeat_start(
                aufgabe, state=state, progress_context=progress_context,
            )
        else:
            hb_thread, hb_stop = None, None
        try:
            try:
                res = requests.post(DEEPSEEK_API_URL, headers=headers,
                                    json=payload, timeout=_req_timeout)
            except requests.Timeout as exc:
                letzter_fehler = f"HTTP Timeout: {exc}"
                res = None
                if state is not None:
                    audit("llm_timeout_read",
                          {"modell": model,
                           "aufgabe": aufgabe,
                           "read_s": _read_adapt,
                           "versuch": _versuche_absolut},
                          state.project_dir,
                          state.project_name)
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
                        system_len=_system_len,
                        user_len=_user_len,
                    )
                letzter_fehler = f"HTTP {res.status_code}: {res.text[:200]}"
        finally:
            if hb_stop is not None:
                hb_stop.set()
            if hb_thread is not None:
                hb_thread.join(timeout=1.0)
        if versuch < len(backoffs):
            time.sleep(warte)

    if res is None:
        return LLMReply(ok=False, error=letzter_fehler,
                        system_len=_system_len,
                        user_len=_user_len)
    if res.status_code != 200:
        return LLMReply(ok=False, error=letzter_fehler,
                        system_len=_system_len,
                        user_len=_user_len)
    try:
        data = res.json()
        _usage = data.get("usage") or {}
        _pt = int(_usage.get("prompt_tokens", 0) or 0)
        _ct = int(_usage.get("completion_tokens", 0) or 0)
        _tt = int(_usage.get("total_tokens", 0) or 0)
        if state is not None and _tt > 0:
            audit("llm_usage",
                  {"rolle": rolle or _rolle_aus_aufgabe(aufgabe),
                   "model": model,
                   "provider_model": str(data.get("model") or model),
                   "prompt_tokens": _pt,
                   "completion_tokens": _ct,
                   "total_tokens": _tt},
                  state.project_dir,
                  state.project_name)
        msg = data["choices"][0]["message"]
        content = msg.get("content", "") or ""
        # W58: deepseek-reasoner liefert reasoning_content
        # (Denk-Tokens) + content (sichtbare Antwort). Wenn
        # das max_tokens-Budget im Reasoning erschoepft ist,
        # ist content leer. Fallback auf reasoning_content.
        if not content:
            reasoning = msg.get("reasoning_content", "") or ""
            if reasoning:
                # 2026-11-05: Fail-loud statt Fallback.
                # Wenn content leer ist und reasoning_content da ist,
                # hat das Modell sein Token-Budget mit CoT aufgebraucht.
                # Das Denkprotokoll als "Antwort" zu akzeptieren macht
                # den gesamten Loop kaputt (Denkprotokoll an Planner-
                # Split -> Kollaps). Lieber klar abbrechen.
                return LLMReply(
                    ok=False,
                    content="",
                    error=(
                        f"leerer content, reasoning_content vorhanden "
                        f"({len(reasoning)} Zeichen). Modell hat Budget "
                        f"mit CoT aufgebraucht. Pruefe max_tokens / "
                        f"CoT-Trigger im Prompt."
                    ),
                )
            if reasoning:
                # Letzte Zeilen des Reasonings als Antwort.
                content = reasoning
        if not content:
            return LLMReply(
                ok=False,
                error=("leere Antwort (content und "
                       "reasoning_content leer)"),
                system_len=_system_len,
                user_len=_user_len,
            )
        return LLMReply(ok=True, content=content,
                        system_len=_system_len,
                        user_len=_user_len,
                        prompt_tokens=_pt,
                        completion_tokens=_ct,
                        total_tokens=_tt)
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        return LLMReply(ok=False, error=f"Parsing: {exc}",
                        system_len=_system_len,
                        user_len=_user_len)

# =====================================================================
# A8-1b-0 (2026-10-23): aus pipeline.py extrahiert, wortwoertlich.
# Weg A: check=False ergaenzt, ISC004-noqa. Lazy Imports entfernt.
# =====================================================================

MAX_PROTOKOLL_PER_COMMAND = 10_000

def trim_output(out: str, grenze: int = MAX_PROTOKOLL_PER_COMMAND) -> str:
    """Kuerzt ein Messprotokoll-Stueck auf `grenze` Zeichen (Auflage 2041)."""
    if len(out) <= grenze:
        return out
    rest = len(out) - grenze
    return out[:grenze] + f"\n[... gekuerzt, {rest} Zeichen weggelassen ...]\n"


# Truncation-Fix (2026-10-16): gemeinsame Kontext-Grenze
# fuer Reviewer-Recovery-Kontexte.

def _schreibe_messung(
        state: RunState,
        pfad: str,
        inhalt: str,
        quelle: str,
        mtime: float,
) -> None:
    """W52b (2026-10-18): schreibt eine Messung als Datei.

    Ergaenzt state.messungen, state.gelesene_dateien
    (W59) und state.mess_protokoll (deprecated, fuer
    Bestandsleser).

    Pfad: .werkstatt/<run_id>/messungen/<sha1>.txt.
    """
    sha1 = hashlib.sha1(
        inhalt.encode("utf-8", errors="replace")).hexdigest()
    # Verzeichnis.
    run_id = state.run_id or "unbekannt"
    from werkstatt.paths import werkstatt_home as _wh
    mess_dir = _wh() / ".werkstatt" / run_id \
        / "messungen"
    try:
        mess_dir.mkdir(parents=True, exist_ok=True)
        datei = mess_dir / f"{sha1}.txt"
        datei.write_text(inhalt, encoding="utf-8")
    except OSError as exc:
        print(f"[WARN] Messung-Datei: {exc}")
        datei = None
    # state.messungen.
    state.messungen.append(Messung(
        pfad=pfad,
        sha1=sha1,
        mtime=mtime,
        groesse=len(inhalt.encode("utf-8",
                                  errors="replace")),
        quelle=quelle,
        datei=datei,
    ))
    # W59: gelesene Datei + mtime.
    state.gelesene_dateien[pfad] = mtime
    # Deprecated: String-Kanal.
    state.mess_protokoll += inhalt


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
    # W61: pytest mit Arg (Testdatei).
    if m.mid == "pytest":
        if not extra_arg:
            return "pytest ohne Pfad.", False, []
        if not isinstance(extra_arg, str):
            return "pytest arg ist kein str.", False, []
        # Whitelist-Pruefung.
        if not any(extra_arg.startswith(w) for w in whitelist):
            return (f"pytest arg {extra_arg!r} nicht in "  # noqa: ISC004
                    f"Whitelist.", False, [])
        argv = list(argv) + [extra_arg]
        res = subprocess.run(
            argv, cwd=project_dir, capture_output=True,
            text=True, timeout=m.timeout_s, check=False)
        stdout_gekuerzt = res.stdout.strip().splitlines()
        letzte = stdout_gekuerzt[-1] if stdout_gekuerzt else ""
        out = (f"=== {m.mid} ===\nARGV: {' '.join(argv)}\n"
               f"RC: {res.returncode}\nSTDOUT (letzte Zeile):\n"
               f"{letzte}\nSTDERR:\n{res.stderr}\n")
        return out, res.returncode == 0, argv
    if m.mid == "read_file":
        if not extra_arg:
            return "read_file ohne Pfad.", False, []
        if not isinstance(extra_arg, str):
            return "read_file arg ist kein str.", False, []
        # W6b-1 (2026-10-16): Zeilenbereich
        # <pfad>:<start>-<ende>. Auswertung via
        # sed -n "<start>,<ende>p".
        _zeilenbereich: tuple[int, int] | None = None
        _pfad_arg = extra_arg
        if ":" in extra_arg:
            _kopf, _rest = extra_arg.rsplit(":", 1)
            if "-" in _rest:
                _a, _b = _rest.split("-", 1)
                try:
                    _start = int(_a)
                    _ende = int(_b)
                    if _start >= 1 and _ende >= _start:
                        _zeilenbereich = (_start, _ende)
                        _pfad_arg = _kopf
                except ValueError:
                    pass
        cand = (project_dir / _pfad_arg).resolve()
        try:
            rel = str(cand.relative_to(project_dir.resolve()))
        except ValueError:
            return f"Pfad ausserhalb Projekt: {_pfad_arg}", False, []
        if not any(rel.startswith(p) for p in whitelist):
            return f"Pfad nicht in Whitelist: {rel}", False, []
        if _zeilenbereich is not None:
            argv = ["sed", "-n",
                    f"{_zeilenbereich[0]},{_zeilenbereich[1]}p",
                    str(cand)]
        else:
            argv.append(str(cand))
    try:
        res = subprocess.run(argv, cwd=str(project_dir), capture_output=True,
                             text=True, timeout=m.timeout_s, check=False,
                             env=subprocess_env())
    except subprocess.TimeoutExpired:
        return f"TIMEOUT {m.timeout_s}s", False, argv
    except OSError as exc:
        return f"OSError: {exc}", False, argv
    # Auflage 2176: test_count-Ausgabe kuerzen.
    # Sonst enthaelt sie 1312 Zeilen Testnamen; die
    # Testzahl steht erst am Ende.
    if m.mid == "test_count":
        stdout_gekuerzt = res.stdout.strip().splitlines()
        letzte = stdout_gekuerzt[-1] if stdout_gekuerzt else ""
        out = (f"=== {m.mid} ===\nARGV: {' '.join(argv)}\n"
               f"RC: {res.returncode}\nSTDOUT (letzte Zeile):\n{letzte}\n"
               f"STDERR:\n{res.stderr}\n")
    else:
        out = (f"=== {m.mid} ===\nARGV: {' '.join(argv)}\nRC: {res.returncode}\n"
               f"STDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}\n")
    return out, res.returncode == 0, argv


# =====================================================================
# A8-1b-1a (2026-10-23): Vorbereitung Position B.
# execute_commands + 5 Konstanten als DEFINITION.
# pipeline.py behaelt die Kopien (M-231 Zwischenzustand).
# In 1b wird die pipeline.py-Kopie entfernt.
# =====================================================================

MAX_PROTOKOLL_PER_COMMAND_READ_FILE = 20_000
MAX_PROTOKOLL_TOTAL = 150_000
_PLANNER_PROTOKOLL_PER_READ = 10_000
_PLANNER_PROTOKOLL_TOTAL = 200_000

ERLAUBTE_QUELLEN = {
    "reviewer", "builder", "test_generator",
    "pipeline_auto", "reviewer_command",
    "planner",
}

def execute_commands(state: RunState, commands: list[dict[str, str]],
                     quelle: str
                     ) -> dict[tuple[str, str], bool]:
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

    ergebnisse: dict[tuple[str, str], bool] = {}
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
        # W6a-4 (2026-10-16): read_file darf groesser
        # sein (Anker-Zeilen sind oft tief in
        # grossen Dateien).
        # W51d: quelle-abhaengige Grenzen.
        if quelle == "planner":
            _grenze = (
                _PLANNER_PROTOKOLL_PER_READ
                if cid == "read_file"
                else MAX_PROTOKOLL_PER_COMMAND)
            _total = _PLANNER_PROTOKOLL_TOTAL
        else:
            _grenze = (
                MAX_PROTOKOLL_PER_COMMAND_READ_FILE
                if cid == "read_file"
                else MAX_PROTOKOLL_PER_COMMAND)
            _total = MAX_PROTOKOLL_TOTAL
        out = trim_output(out, grenze=_grenze)

        # Auflage 2041: Gesamtlaenge begrenzen.
        rest_platz = _total - len(state.mess_protokoll)
        if rest_platz <= 0:
            print("[!] mess_protokoll Gesamtlimit "
                  "erreicht. Weitere Messungen "
                  "werden nur auditiert.")
            audit("mess_protokoll_limit_erreicht",
                  {"len": len(state.mess_protokoll),
                   "total": _total,
                   "quelle": quelle},
                  state.project_dir, state.project_name)
            audit("command_executed",
                  {"id": cid, "arg": arg[:200], "argv": argv,
                   "quelle": quelle, "ok": ok, "ausgabe_verworfen": True},
                  state.project_dir, state.project_name)
            continue
        if len(out) > rest_platz:
            out = out[:rest_platz] + "\n[... Gesamtlimit erreicht ...]\n"

        # W51g: Dedup nur fuer Planner + read_file.
        _dedup_skip = False
        if (quelle == "planner" and cid == "read_file"
                and ok):
            _gem = getattr(
                state, "_w51g_gemessen", None)
            if _gem is not None and arg in _gem:
                _dedup_skip = True
        if _dedup_skip:
            ergebnisse[(cid, arg)] = ok
            audit("command_executed",
                  {"id": cid, "arg": arg[:200],
                   "argv": argv, "quelle": quelle,
                   "ok": ok, "dedup_verworfen": True},
                  state.project_dir, state.project_name)
            continue
        # W52b (2026-10-18): Messung als Datei
        # + state.messungen + state.gelesene_dateien.
        # mtime nur bei read_file (Datei-Messung).
        _mtime = 0.0
        if cid == "read_file" and ok:
            try:
                _mtime = (state.project_dir / arg).stat().st_mtime
            except OSError:
                _mtime = 0.0
        if ok:
            _schreibe_messung(
                state, arg, out, quelle, _mtime)
            if (quelle == "planner"
                    and cid == "read_file"):
                _gem = getattr(
                    state, "_w51g_gemessen", None)
                if _gem is not None:
                    _gem.add(arg)
        else:
            _schreibe_messung(
                state, arg,
                "\n\n!!! COMMAND FEHLGESCHLAGEN: "
                f"{cid} {arg} !!!\n"
                "Der COMMAND hat ok=false geliefert. "
                "Ursache im Output unten.\n"
                "Wenn der Pfad falsch war: pruefe den "
                "Pfad woertlich aus dem Auftrag, aus "
                "dem ZIELDATEIEN-Header oder aus dem "
                "KUERZUNGS-MARKER. Rekonstruiere ihn "
                "nicht.\n\n"
                + out,
                quelle, _mtime)
        ergebnisse[(cid, arg)] = ok

        # Auflage 2040: argv ins Audit.
        audit("command_executed",
              {"id": cid, "arg": arg[:200], "argv": argv,
               "quelle": quelle, "ok": ok},
              state.project_dir, state.project_name)

    return ergebnisse


# =====================================================================
# A8-3 (2026-10-23): Anti-Pattern-Hook via subprocess.run.
# Fail-open: Hook-Fehler -> leerer Block + Audit.
# =====================================================================






# ============================================================
# OP-111 (2026-11-04): Oeffentliche ask_llm-API mit Progress-Events.
# ============================================================

_PROGRESS_LABELS: dict[str, str] = {
    "builder": "Builder",
    "scout": "Scout",
    "architect": "Architect",
    "planner-split": "Planner",
    "reviewer": "Reviewer",
    "explorer": "Explorer",
    "reflection": "Reflection",
}


def _aufgabe_zu_label(aufgabe: str) -> str:
    """Mappt ask_llm-Aufgabe auf Progress-Label (OP-111)."""
    if not aufgabe:
        return "Agent"
    return _PROGRESS_LABELS.get(aufgabe, aufgabe.capitalize())


def ask_llm(api_key: str, system_prompt: str, user_content: str,
            model: str, temperature: float, timeout: int = 120,
            *, state: RunState | None = None,
            aufgabe: str = "unbekannt",
            rolle: str | None = None,
            heartbeat: bool = True,
            max_tokens: int = 4096,
            redact: bool = True,
            progress_context: dict[str, Any] | None = None) -> LLMReply:
    """Oeffentliche LLM-API mit Progress-Events (OP-111)."""
    from werkstatt.render import _emit_progress
    route = route_for_role(rolle or aufgabe, model)
    model = route.model
    _label = _aufgabe_zu_label(aufgabe)
    _context = _progress_context(state, progress_context)
    _detail = ", ".join(_context.get("files", []))
    if _context.get("task_name"):
        _detail = f"{_context['task_name']}" + (f" · {_detail}" if _detail else "")
    _t0 = time.monotonic()
    progress_detail = (
        f"model={model}; {_detail}" if _detail else f"model={model}"
    )
    _emit_progress(_label, "prompt_sent", progress_detail)
    if state is not None:
        audit("llm_call_start",
              {"agent": aufgabe, "model": model,
               **_context,
               "result_summary": f"{_label} startet Modellaufruf.",
               "decision_summary": (
                   f"Der Auftrag wird an die Rolle {_label} übergeben."
               ),
               "next_step": "Modellantwort verarbeiten und den Task fortsetzen.",
               "system_len": len(system_prompt),
               "user_len": len(user_content)},
              state.project_dir, state.project_name)
    try:
        reply = _ask_llm_impl(
            api_key, system_prompt, user_content, model, temperature,
            timeout=timeout, state=state, aufgabe=aufgabe,
            rolle=rolle, heartbeat=heartbeat, max_tokens=max_tokens,
            redact=redact, progress_context=_context,
        )
    except Exception as exc:
        _emit_progress(_label, "response_failed", str(exc)[:80])
        raise
    _elapsed = time.monotonic() - _t0
    if reply.ok:
        _emit_progress(_label, "response_received", f"{_elapsed:.1f}s")
    else:
        _emit_progress(_label, "response_failed", (reply.error or "?")[:80])
    if state is not None:
        audit("llm_call_end",
              {"agent": aufgabe, "model": model,
               "ok": bool(reply.ok),
               "elapsed_s": round(_elapsed, 2),
               "content_len": len(reply.content or ""),
               **_context,
               "result_summary": (
                   f"{_label} Modellaufruf "
                   f"{'abgeschlossen' if reply.ok else 'fehlgeschlagen'}."
               ),
               "decision_summary": (
                   "Die Modellantwort wird dem laufenden Task zurückgegeben."
                   if reply.ok else
                   "Der Fehler wird dem bestehenden Recovery-Pfad übergeben."
               ),
               "next_step": (
                   "Builder-Ausgabe prüfen und gezielt anwenden."
                   if aufgabe == "builder" and reply.ok else
                   "Fehler klassifizieren und gezielt beheben."
                   if not reply.ok else
                   "Ergebnis des Rollen-Schritts auswerten."
               ),
               "error": (reply.error or "")[:200]},
              state.project_dir, state.project_name)
    return reply
