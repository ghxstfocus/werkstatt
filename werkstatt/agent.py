"""LLM-Agent (A8-1a-1).

ask_llm aus pipeline.py extrahiert (2026-10-22).
Wortwoertliche Extraktion, keine Verhaltensaenderung.

Konsumenten: pipeline.py (via Re-Export).
"""
from __future__ import annotations

import time
from typing import Any

import requests  # type: ignore[import-untyped]

import redaction
from werkstatt.audit import audit
from werkstatt.state import LLMReply, RunState

DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"

def ask_llm(api_key: str, system_prompt: str, user_content: str,
            model: str, temperature: float, timeout: int = 120,
            *, state: RunState | None = None,
            aufgabe: str = "unbekannt",
            max_tokens: int = 4096) -> LLMReply:
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
        "max_tokens": max_tokens,
                               "messages": [{"role": "system", "content": system_prompt},
                                            {"role": "user", "content": user_content}],
                               "temperature": temperature}
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
            )
        # Read-Timeout adaptiv: min(read, restzeit).
        _read_adapt = int(min(_READ_S, max(1, _rest)))
        _req_timeout = (_CONNECT_S, _read_adapt)
        # SIM113: Retry-Loop mit variabler Laenge
        # (max len(backoffs)), enumerate ist hier
        # nicht passend (Abbruch durch break).
        _versuche_absolut += 1  # noqa: SIM113
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
        msg = data["choices"][0]["message"]
        content = msg.get("content", "") or ""
        # W58: deepseek-reasoner liefert reasoning_content
        # (Denk-Tokens) + content (sichtbare Antwort). Wenn
        # das max_tokens-Budget im Reasoning erschoepft ist,
        # ist content leer. Fallback auf reasoning_content.
        if not content:
            reasoning = msg.get("reasoning_content", "") or ""
            if reasoning:
                # Letzte Zeilen des Reasonings als Antwort.
                content = reasoning
        if not content:
            return LLMReply(
                ok=False,
                error=("leere Antwort (content und "
                       "reasoning_content leer)"))
        return LLMReply(ok=True, content=content)
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        return LLMReply(ok=False, error=f"Parsing: {exc}")
