"""Control-Dataclass: eine Loop-Kontrolle mit Metadaten."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from werkstatt.control.phases import Phase


@dataclass(frozen=True)
class Control:
    """Eine einzelne Loop-Kontrolle.

    Attributes:
        name: Eindeutiger Name (snake_case). Nie umbenennen (Audit-Kopplung).
        phase: Loop-Phase, in der die Kontrolle laeuft.
        fn: Callable, das die Kontrolle ausfuehrt. Signatur: fn(ctx) -> Any.
        source: Aktueller Import-Pfad (z.B. "werkstatt.verify._verify_patches").
            Ermoeglicht Drift-Check und schrittweise Migration nach
            werkstatt.control.*.
        description: Kurzbeschreibung (ein Satz).
        hart: True = blockiert bei Fail, False = Warnung/loggt nur.
        prioritaet: Niedrigere Zahl laeuft frueher. Default 100.
        legacy_imports: Alte Import-Pfade die noch funktionieren muessen
            (Deprecation-Proxy). Leer solange nichts verschoben ist.
        deprecated_by: Name der Nachfolge-Kontrolle, falls umbenannt.
    """
    name: str
    phase: Phase
    fn: Callable[..., Any]
    source: str
    description: str
    hart: bool = True
    prioritaet: int = 100
    legacy_imports: tuple[str, ...] = field(default_factory=tuple)
    deprecated_by: str | None = None

    def __post_init__(self) -> None:
        if not self.name or not self.name.isidentifier():
            raise ValueError(f"Control.name muss snake_case sein: {self.name!r}")
        if not callable(self.fn):
            raise TypeError(f"Control.fn muss callable sein: {self.name!r}")
