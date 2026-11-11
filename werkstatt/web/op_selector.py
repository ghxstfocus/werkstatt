"""Konservative Auswahl startfaehiger OPs aus docs/STATUS.md (OP-398)."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

_OP_HEADING = re.compile(r"^### (OP-\d+[a-z]?):\s*(.+?)\s*$", re.MULTILINE)
_FIELD = re.compile(
    r"^\s*-\s+\*\*([^*]+):\*\*\s*(.*?)(?=^\s*-\s+\*\*|\Z)",
    re.MULTILINE | re.DOTALL,
)
_OP_ID = re.compile(r"OP-\d+[a-z]?", re.IGNORECASE)
_ADR_ID = re.compile(r"ADR-\d{4}", re.IGNORECASE)
_PLACEHOLDER = {"", "—", "-", "keine", "n/a", "nicht zutreffend"}
_COMPLETED_OP_HEADING = re.compile(
    r"^###\s+\d{4}-\d{2}-\d{2}\s+[—-]\s+"
    r"(OP-\d+[a-z]?)\s+abgeschlossen\b",
    re.MULTILINE | re.IGNORECASE,
)
_COMPLETED_OP_ROW = re.compile(
    r"^\s*-\s+\d{4}-\d{2}-\d{2}\s*\|\s*"
    r"(OP-\d+[a-z]?)\s*\|\s*done\s*\|",
    re.MULTILINE | re.IGNORECASE,
)


def parse_completed_op_ids(
    progress_text: str,
    status_text: str = "",
) -> set[str]:
    """Liest explizite Abschluesse aus PROGRESS und dem STATUS-Auto-Log."""
    ids: list[str] = []
    for document in (progress_text, status_text):
        ids.extend(_COMPLETED_OP_HEADING.findall(document))
        ids.extend(_COMPLETED_OP_ROW.findall(document))
    return {op_id.upper() for op_id in ids}


def load_accepted_adr_ids(adr_dir: Path) -> set[str]:
    """Liest nur explizit angenommene ADRs; fehlende/ungueltige Dateien bleiben gesperrt."""
    accepted: set[str] = set()
    try:
        paths = sorted(adr_dir.glob("ADR-*.md"))
    except OSError:
        return accepted
    for path in paths:
        match = re.fullmatch(r"(ADR-\d{4}).*\.md", path.name, re.IGNORECASE)
        if not match:
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        statuses = re.findall(
            r"^\s*-\s+\*\*Status:\*\*\s*([^\n]+)",
            content, re.MULTILINE | re.IGNORECASE,
        )
        if len(statuses) == 1 and statuses[0].strip().casefold() == "accepted":
            accepted.add(match.group(1).upper())
    return accepted


def _felder(block: str) -> dict[str, str]:
    return {
        match.group(1).strip().casefold(): match.group(2).strip()
        for match in _FIELD.finditer(block)
    }


def _ausfuellbar(value: str | None) -> bool:
    if value is None:
        return False
    normalisiert = re.sub(r"[\s*\x60]", "", value).casefold()
    return normalisiert not in _PLACEHOLDER


def select_next_op(
    status_text: str,
    completed_ids: set[str] | frozenset[str] = frozenset(),
    accepted_adrs: set[str] | frozenset[str] = frozenset(),
) -> dict[str, Any]:
    """Waehlt startfaehige OPs; erledigte Blocker kommen aus PROGRESS."""
    accepted = {adr_id.upper() for adr_id in accepted_adrs}
    completed = {op_id.upper() for op_id in completed_ids}
    treffer = list(_OP_HEADING.finditer(status_text))
    ops: list[dict[str, Any]] = []
    for index, match in enumerate(treffer):
        ende = treffer[index + 1].start() if index + 1 < len(treffer) else len(status_text)
        block = status_text[match.start():ende].strip()
        fields = _felder(block)
        statuses = re.findall(
            r"^\s*-\s+\*\*Status:\*\*\s*([^\n]+)",
            block, re.MULTILINE | re.IGNORECASE,
        )
        ops.append({
            "id": match.group(1).upper(),
            "titel": match.group(2).strip(),
            "text": block,
            "felder": fields,
            "status": statuses[0].strip().casefold() if len(statuses) == 1 else "conflict",
            "status_anzahl": len(statuses),
        })

    id_counts: dict[str, int] = {}
    for op in ops:
        id_counts[op["id"]] = id_counts.get(op["id"], 0) + 1
    by_id = {
        op["id"]: op for op in ops
        if id_counts[op["id"]] == 1
    }
    dogfooding_completed = "OP-382" in completed and "OP-382" not in id_counts
    candidates: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for op in ops:
        if id_counts[op["id"]] > 1:
            excluded.append({
                "id": op["id"],
                "titel": op["titel"],
                "gruende": ["OP-ID kommt mehrfach in STATUS.md vor"],
            })
            continue
        if op["status"] != "open":
            if op["status"] == "conflict":
                excluded.append({
                    "id": op["id"], "titel": op["titel"],
                    "gruende": ["Status fehlt oder ist mehrfach angegeben"],
                })
            continue
        fields = op["felder"]
        reasons: list[str] = []
        if op["status_anzahl"] != 1:
            reasons.append("Status fehlt oder ist mehrfach angegeben")
        tests = fields.get("tests")
        phase = fields.get("phase", "")
        if (
            re.search(r"\bphase[\s-]*3\b", phase, re.IGNORECASE)
            and not dogfooding_completed
        ):
            reasons.append("Phase-3 gesperrt bis OP-382 abgeschlossen")
        if not _ausfuellbar(fields.get("akzeptanzkriterien")):
            reasons.append("Akzeptanzkriterien fehlen")
        if not _ausfuellbar(tests):
            reasons.append("Tests oder ein pruefbarer Nachweis fehlen")

        adr_requirement = fields.get("architektur-voraussetzung", "")
        required_adrs = sorted({value.upper() for value in _ADR_ID.findall(adr_requirement)})
        if adr_requirement.strip().casefold() not in _PLACEHOLDER and not required_adrs:
            reasons.append("Architektur-Voraussetzung ist nicht eindeutig lesbar")
        unaccepted_adrs = [adr_id for adr_id in required_adrs if adr_id not in accepted]
        if unaccepted_adrs:
            reasons.append(
                "ADR-Voraussetzungen nicht angenommen: " + ", ".join(unaccepted_adrs)
            )

        blockers = fields.get("blockiert von", "")
        dep_ids = [value.upper() for value in _OP_ID.findall(blockers)]
        if blockers.strip().casefold() not in _PLACEHOLDER and not dep_ids:
            reasons.append("Blocker-Angabe ist nicht eindeutig lesbar")
        unresolved: list[str] = []
        stale: list[str] = []
        for dep_id in dep_ids:
            dependency = by_id.get(dep_id)
            if dependency is None:
                if dep_id not in id_counts and dep_id in completed:
                    continue
                stale.append(dep_id)
            elif dependency["status"] in {"done", "erledigt", "closed", "complete", "completed"}:
                continue
            elif dependency["status"] == "open":
                unresolved.append(dep_id)
            else:
                stale.append(dep_id)
        if unresolved:
            reasons.append("Abhaengigkeiten noch offen: " + ", ".join(unresolved))
        if stale:
            reasons.append("Unbekannte oder widerspruechliche Blocker: " + ", ".join(stale))
        if reasons:
            excluded.append({"id": op["id"], "titel": op["titel"], "gruende": reasons})
            continue

        priority = fields.get("prioritaet") or fields.get("priorität") or "nicht angegeben"
        risk = fields.get("risiko", "nicht angegeben")
        relevance = fields.get("projektziel", "nicht angegeben")
        candidates.append({
            "id": op["id"],
            "titel": op["titel"],
            "prioritaet": priority,
            "risiko": risk,
            "projektziel_relevanz": relevance,
            "verifikation": tests,
            "gruende": [
                "Status ist open; Abhaengigkeiten sind aufgeloest.",
                "Akzeptanzkriterien und Tests/Nachweis sind dokumentiert.",
                f"Prioritaet: {priority}; Risiko: {risk}; Projektziel-Relevanz: {relevance}.",
            ],
            "aufgabe": op["text"],
        })

    selected = candidates[0] if len(candidates) == 1 else None
    if selected:
        state = "selected"
        explanation = "Einziger startfaehiger Kandidat. Plan-Gate bleibt verpflichtend."
    elif candidates:
        state = "needs_input"
        explanation = "Mehrere startfaehige Kandidaten; ohne Auswahl wird kein Run gestartet."
    else:
        state = "no_candidate"
        explanation = "Kein OP erfuellt alle Startkriterien."

    def public(item: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in item.items() if key != "aufgabe"}
    return {
        "zustand": state,
        "begruendung": explanation,
        "auswahl": public(selected) if selected else None,
        "kandidaten": [public(item) for item in candidates],
        "ausgeschlossen": excluded,
        "aufgabe": selected["aufgabe"] if selected else None,
    }
