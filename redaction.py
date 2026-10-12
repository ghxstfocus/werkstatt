# Copyright (C) 2026 Alexander Nohl
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Prompt-Injection-Schutz fuer den Kontext-Bauer.

Aufgabe: Rohdaten (Events, Logs, DB-Felder) so filtern, dass
das lokale LLM keine Instruktionen aus unbekannten Quellen
ausfuehren kann.

Regeln (fail closed):
- Steuerzeichen entfernen (\\x00, \\r, \\x0b, \\x0c).
- Instruktions-Marker entfernen (case-insensitive):
  "ignore previous", "ignore all", "system:", "assistant:",
  "user:", "<|im_start|>", "<|im_end|>", "###instruction",
  "[INST]", "[/INST]", "<<SYS>>", "<</SYS>>".
- Laenge pro Feld begrenzen (max_len, Default 2000 Zeichen).
- Bei Verstoss: betroffene Passage durch [REDACTED] ersetzen.

redact_text liefert (sauberer_text, wurde_redigiert).
redact_field ist der Wrapper fuer ein einzelnes Feld mit
Laengenbegrenzung.
"""
from __future__ import annotations

import re
from typing import Any

# ---------------------------------------------------------------------- #
# Konstanten
# ---------------------------------------------------------------------- #

MAX_FIELD_LEN = 2000

_REDACTION_PLACEHOLDER = "[REDACTED]"

# Steuerzeichen, die in Textfeldern nichts zu suchen haben.
# \\t und \\n bleiben (mehrzeilige Logs sind erlaubt).
_CONTROL_CHARS_RE = re.compile(r"[\x00\r\x0b\x0c]")

# Instruktions-Marker. Case-insensitive. Werden durch
# [REDACTED] ersetzt.
_INJECTION_MARKERS = (
    "ignore previous",
    "ignore all",
    "ignore the above",
    "system:",
    "assistant:",
    "user:",
    "<|im_start|>",
    "<|im_end|>",
    "###instruction",
    "[inst]",
    "[/inst]",
    "<<sys>>",
    "<</sys>>",
)

# Ein Regex, der alle Marker in einem Durchgang findet.
_INJECTION_RE = re.compile(
    "|".join(re.escape(m) for m in _INJECTION_MARKERS),
    re.IGNORECASE,
)


# ---------------------------------------------------------------------- #
# Oeffentliche API
# ---------------------------------------------------------------------- #

def redact_text(text: str, *, max_len: int = MAX_FIELD_LEN
                ) -> tuple[str, bool]:
    """
    Filtert einen Text und liefert (sauberer_text, wurde_redigiert).

    - None/nicht-String -> ("", True) (fail closed, markiert als redigiert)
    - Steuerzeichen entfernt
    - Instruktions-Marker ersetzt
    - Laenge auf max_len gekuerzt (Ueberlaenge wird als Redaktion gezaehlt)
    """
    if not isinstance(text, str):
        return ("", True)
    if max_len < 0:
        raise ValueError("redact_text: max_len muss >= 0 sein")

    redacted = False
    out = text

    # Steuerzeichen
    cleaned = _CONTROL_CHARS_RE.sub("", out)
    if cleaned != out:
        redacted = True
        out = cleaned

    # Instruktions-Marker
    substituted = _INJECTION_RE.sub(_REDACTION_PLACEHOLDER, out)
    if substituted != out:
        redacted = True
        out = substituted

    # Laenge
    # Auflage 2044-Nachtrag: max_len gilt HART. Der Platzhalter
    # muss in das Limit hineinpassen, sonst waere max_len irrefuehrend.
    if len(out) > max_len:
        platzhalter_len = len(_REDACTION_PLACEHOLDER)
        schneide = max(0, max_len - platzhalter_len)
        out = out[:schneide] + _REDACTION_PLACEHOLDER
        redacted = True

    return (out, redacted)


def redact_field(value: object, *, max_len: int = MAX_FIELD_LEN
                 ) -> tuple[str, bool]:
    """
    Wrapper fuer ein einzelnes Feld.

    Akzeptiert str, int, float, bool, None. Alles andere -> "" + redigiert.
    """
    if value is None:
        return ("", False)
    if isinstance(value, str):
        # Auflage 2074: redact_all statt redact_text.
        # Damit greift auch die Secret-Maskierung (IPs, MACs, Keys).
        return redact_all(value, max_len=max_len)
    if isinstance(value, (int, float, bool)):
        return (str(value), False)
    # dict, list, Objekte: nicht inline rendern (fail closed)
    return ("", True)


def redact_mapping(
    data: dict, *, max_len: int = MAX_FIELD_LEN
) -> tuple[dict[str, Any], bool]:
    """
    Filtert ein dict[str, Any] auf dict[str, Any].
    Skalare werden per redact_field stringifiziert,
    Listen/Objekte fail closed (leerer String,
    redigiert). Liefert (sauberes_dict, wurde_redigiert).
    """
    if not isinstance(data, dict):
        return ({}, True)
    out: dict[str, Any] = {}
    redacted = False
    for k, v in data.items():
        if not isinstance(k, str):
            redacted = True
            continue
        cleaned, was = redact_field(v, max_len=max_len)
        if was:
            redacted = True
        out[k] = cleaned
    return (out, redacted)


__all__ = [
    "MAX_FIELD_LEN",
    "redact_field",
    "redact_mapping",
    "redact_text",
]


# ---------------------------------------------------------------------- #
# === ERWEITERUNG: DATA-LEAK-SCHUTZ ===
# ---------------------------------------------------------------------- #
# Diese Erweiterung maskiert sensible Daten (IPs, Keys, MACs), die
# nicht an einen Cloud-LLM gehen sollen. Reihenfolge:
#   1. redact_secrets (Datenleck-Schutz)
#   2. redact_text    (Prompt-Injection-Schutz + Laengenlimit)

_IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
# Auflage 2072: IPv6 deckt jetzt auch ::1, fe80::/10 und andere
# Kurzformen ab. Der Regex ist der klassische Ausdruck fuer IPv6.
# MAC-Adressen werden NICHT erfasst:
#   - Vollform braucht 8 Bloecke (MAC hat 6).
#   - Kurzformen brauchen "::" (MAC hat kein "::").
# Zusaetzlich laeuft die MAC-Regex VOR der IPv6-Regex.
#
# Reihenfolge der Alternation ist wichtig: laengere/spezifischere
# Formen zuerst, sonst matcht eine kuerzere Form zu frueh und laesst
# Reste stehen (z.B. "fe80::1" -> "fe80::" + "1").
_IPV6_RE = re.compile(
    r"(?:"
    r"(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}"                       # Vollform
    r"|(?:[0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}"                    # :: mittig
    r"|(?:[0-9a-fA-F]{1,4}:){1,5}(?::[0-9a-fA-F]{1,4}){1,2}"
    r"|(?:[0-9a-fA-F]{1,4}:){1,4}(?::[0-9a-fA-F]{1,4}){1,3}"
    r"|(?:[0-9a-fA-F]{1,4}:){1,3}(?::[0-9a-fA-F]{1,4}){1,4}"
    r"|(?:[0-9a-fA-F]{1,4}:){1,2}(?::[0-9a-fA-F]{1,4}){1,5}"
    r"|[0-9a-fA-F]{1,4}:(?::[0-9a-fA-F]{1,4}){1,6}"
    r"|(?:[0-9a-fA-F]{1,4}:){1,7}:"                                    # :: am Ende
    r"|:(?:(?::[0-9a-fA-F]{1,4}){1,7}|:)"                              # :: Start
    r")"
)
_MAC_RE = re.compile(r"\b(?:[0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}\b")
_API_KEY_RES = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bBearer\s+[A-Za-z0-9_.-]{16,}\b"),
    re.compile(r"\bNTFY_TOKEN[=:]\s*[A-Za-z0-9_-]{16,}\b"),
)
_LONG_HEX_RE = re.compile(r"\b[0-9a-fA-F]{32,}\b")


def redact_secrets(text: str) -> tuple[str, bool]:
    """Maskiert IPs, MACs, API-Keys, lange Hex-Strings.

    Liefert (sauberer_text, wurde_redigiert).
    Nicht-String -> ("", True) (fail closed).
    """
    if not isinstance(text, str):
        return "", True
    wurde = False

    for regex, ersatz in (
        (_API_KEY_RES[0], "[KEY]"),
        (_API_KEY_RES[1], "[KEY]"),
        (_API_KEY_RES[2], "[KEY]"),
        (_API_KEY_RES[3], "[BEARER]"),
        (_API_KEY_RES[4], "[TOKEN]"),
        (_MAC_RE, "[MAC]"),
        (_IPV4_RE, "[IPV4]"),
        (_IPV6_RE, "[IPV6]"),
        (_LONG_HEX_RE, "[HEX]"),
    ):
        neu, anzahl = regex.subn(ersatz, text)
        if anzahl > 0:
            wurde = True
            text = neu

    return text, wurde


def redact_all(text: str, *, max_len: int = MAX_FIELD_LEN) -> tuple[str, bool]:
    """Komplette Redaction: Secrets zuerst, dann Injection + Laenge.

    Liefert (sauberer_text, wurde_redigiert).
    """
    text, s1 = redact_secrets(text)
    text, s2 = redact_text(text, max_len=max_len)
    return text, (s1 or s2)
