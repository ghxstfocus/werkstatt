"""Fortschritts-Log (M-307b, 2026-10-24).

Schreibt Ereignisse in PROGRESS.md im Zielprojekt.
Getrennt von phase_state.yaml:
  - phase_state.yaml = Maschinen-Zustand (Tasks, Status).
  - PROGRESS.md       = Ereignis-Log (append-only, versioniert).

Format pro Block (Parser-Anker A3):
  ## <ISO-timestamp> -- <name>
  - **Status:** done|failed|phase_ende
  - **Dateien:** file1.py, file2.py
  - **Patch:** +1 Zeile
  - **Info:** ...

Verhalten (A2):
  - Fail-open: Schreib-Fehler -> Audit + weiter.
  - Atomar: tmp.write + tmp.replace.
"""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

PROGRESS_FILE = "PROGRESS.md"
RECENT_ENTRIES = 10


def append(
    project_dir: str | Path,
    *,
    name: str,
    status: str,
    dateien: list[str] | None = None,
    patch: str | None = None,
    info: str | None = None,
) -> bool:
    """Appendiert einen Block an PROGRESS.md.

    Returns True on success, False on write error (fail-open).
    """
    pd = Path(project_dir)
    progress_path = pd / PROGRESS_FILE

    ts = datetime.now(UTC).isoformat(timespec="seconds")
    lines = [f"## {ts} -- {name}"]
    lines.append(f"- **Status:** {status}")
    if dateien:
        lines.append(f"- **Dateien:** {', '.join(dateien)}")
    if patch:
        lines.append(f"- **Patch:** {patch}")
    if info:
        lines.append(f"- **Info:** {info}")
    lines.append("")
    block = "\n".join(lines) + "\n"

    try:
        if progress_path.exists():
            current = progress_path.read_text(encoding="utf-8")
        else:
            current = f"# Fortschritt: {pd.name}\n\n"
        tmp = progress_path.with_suffix(".tmp")
        tmp.write_text(current + block, encoding="utf-8")
        tmp.replace(progress_path)
        return True
    except OSError as _exc:
        # GOLD 2026-10-30: Exception-Details ins Audit, damit die
        # Ursache diagnostizierbar ist. Der frueherer {file}-only-
        # Event hat den Rechte-Bug 4 Tage unentdeckt gelassen.
        try:
            from werkstatt.audit import audit
            audit(
                "progress_write_failed",
                {"file": str(progress_path),
                 "exc_type": type(_exc).__name__,
                 "exc_str": str(_exc)[:300]},
                pd, pd.name,
            )
        except Exception:  # noqa: BLE001, S110
            pass
        return False


def read_recent(project_dir: str | Path, n: int = RECENT_ENTRIES) -> str:
    """Liefert die letzten N Eintraege als Text.

    Parser-Anker (A3): Bloecke zwischen "## "-Headern.
    Kaputte Bloecke werden uebersprungen, nicht crashen.
    """
    pd = Path(project_dir)
    progress_path = pd / PROGRESS_FILE
    if not progress_path.exists():
        return ""

    try:
        content = progress_path.read_text(encoding="utf-8")
    except OSError:
        return ""

    blocks: list[str] = []
    current: list[str] = []
    for line in content.splitlines():
        if line.startswith("## "):
            if current:
                blocks.append("\n".join(current))
            current = [line]
        elif current:
            current.append(line)
    if current:
        blocks.append("\n".join(current))

    recent = blocks[-n:]
    return "\n\n".join(recent)
