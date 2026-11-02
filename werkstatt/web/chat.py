"""Chat-Fenster-Logik fuer das Web-Dashboard (OP-076).

Zwei Chats pro Tab (admin/bau), Maximize/Minimize-Layout, Intent-Parsing.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

__all__ = [
    "CHAT_IDS",
    "ChatFensterZustand",
    "ChatMessageIn",
    "hole_tab_zustand",
    "layout_fuer",
    "neuer_tab_zustand",
    "parse_intent",
    "router",
    "setze_aktion",
    "wende_aktion_an",
]

CHAT_IDS: tuple[str, ...] = ("admin", "bau")
CHAT_LABELS: dict[str, str] = {"admin": "Architect", "bau": "Builder"}
INTENTS: frozenset[str] = frozenset({"plan", "build", "approve", "chat_only"})
ZIEL_PRAEFIXE: tuple[tuple[str, str], ...] = (
    ("admin:", "admin"),
    ("bau:", "bau"),
)
STANDARD_ZIEL: str = "bau"
STANDARD_INTENT: str = "chat_only"
BESTAETIGUNG_JA: frozenset[str] = frozenset({"ja", "j", "yes", "y"})
BESTAETIGUNG_NEIN: frozenset[str] = frozenset({"nein", "n", "no"})
AKTIONEN: frozenset[str] = frozenset({"maximize", "minimize", "restore"})

MAX_NACHRICHTEN: int = 200


@dataclass
class ChatFensterZustand:
    maximiert: bool = False
    minimiert: bool = False
    nachrichten: list[dict[str, str]] = field(default_factory=list)

    def als_dict(self) -> dict[str, object]:
        return {
            "maximiert": self.maximiert,
            "minimiert": self.minimiert,
            "anzahl_nachrichten": len(self.nachrichten),
        }

    def anhaengen(self, rolle: str, text: str) -> None:
        self.nachrichten.append({"rolle": rolle, "text": text})
        if len(self.nachrichten) > MAX_NACHRICHTEN:
            self.nachrichten = self.nachrichten[-MAX_NACHRICHTEN:]


class ChatMessageIn(BaseModel):
    text: str = ""
    chat_id: str = STANDARD_ZIEL


def parse_intent(text: str) -> dict[str, str]:
    """Zerlegt Chat-Text in ziel / intent / rest (und bestaetigt bei approve).

    Beispiel: "admin: plan Refactor" -> ziel=admin, intent=plan, rest=Refactor
    Standard ohne Praefix: ziel=bau, intent=chat_only.
    """
    roh = text if isinstance(text, str) else ""
    rest = roh.strip()

    # 1. Ziel-Prefix (admin:/bau:)
    ziel_id = STANDARD_ZIEL
    for praefix, ziel in ZIEL_PRAEFIXE:
        if rest.lower().startswith(praefix):
            ziel_id = ziel
            rest = rest[len(praefix):].strip()
            break

    intent = STANDARD_INTENT
    bestaetigt = ""
    lowered = rest.lower()

    # 2. Bestaetigung (ja/nein/approve)
    if lowered in BESTAETIGUNG_JA:
        intent = "approve"
        bestaetigt = "true"
        rest = ""
    elif lowered in BESTAETIGUNG_NEIN:
        intent = "approve"
        bestaetigt = "false"
        rest = ""
    elif lowered.startswith("approve"):
        intent = "approve"
        rest_approve = lowered[len("approve"):].strip()
        if rest_approve in BESTAETIGUNG_JA:
            bestaetigt = "true"
        elif rest_approve in BESTAETIGUNG_NEIN:
            bestaetigt = "false"
        rest = rest[len("approve"):].strip()
    # 3. Explizite Intents plan/build
    elif lowered.startswith("plan"):
        intent = "plan"
        rest = rest[len("plan"):].strip()
    elif lowered.startswith("build"):
        intent = "build"
        rest = rest[len("build"):].strip()

    return {
        "roh": roh,
        "ziel": ziel_id,
        "intent": intent,
        "rest": rest,
        "bestaetigt": bestaetigt,
    }


def neuer_tab_zustand() -> dict[str, ChatFensterZustand]:
    return {chat_id: ChatFensterZustand() for chat_id in CHAT_IDS}


def layout_fuer(zustand: dict[str, ChatFensterZustand]) -> dict[str, object]:
    """Leitet das Layout aus dem Tab-Zustand ab.

    Rueckgabe:
      modus:   "split" (beide sichtbar) oder "focus" (eines maximiert)
      fokus:   chat_id des maximierten Fensters, oder ""
      sichtbar: {chat_id: bool} — welches Fenster ist aktuell sichtbar
    """
    fokus = ""
    for chat_id, panel in zustand.items():
        if panel.maximiert:
            fokus = chat_id
            break
    modus = "focus" if fokus else "split"
    sichtbar = {chat_id: not panel.minimiert for chat_id, panel in zustand.items()}
    return {"modus": modus, "fokus": fokus, "sichtbar": sichtbar}


def setze_aktion(zustand: ChatFensterZustand, aktion: str) -> ChatFensterZustand:
    """Setzt eine Aktion auf einen einzelnen Chat (nicht tab-bezogen)."""
    if aktion not in AKTIONEN:
        raise ValueError("unbekannte Aktion")
    if aktion == "maximize":
        zustand.maximiert = True
        zustand.minimiert = False
    elif aktion == "minimize":
        zustand.minimiert = True
        zustand.maximiert = False
    elif aktion == "restore":
        zustand.maximiert = False
        zustand.minimiert = False
    return zustand


def wende_aktion_an(
    zustand: dict[str, ChatFensterZustand],
    aktion: str,
) -> dict[str, ChatFensterZustand]:
    """Wendet eine Aktion auf den Tab-Zustand an (Toggle auf Default-Chat).

    maximize: admin maximieren, bau minimieren. Wenn admin schon
              maximiert war -> split (Toggle).
    minimize: admin minimieren (Toggle).
    restore:  split (beide normal).

    Unbekannte Aktion -> ValueError.
    """
    if aktion not in AKTIONEN:
        raise ValueError(f"unbekannte Aktion: {aktion}")

    admin = zustand["admin"]
    bau = zustand["bau"]

    if aktion == "maximize":
        if admin.maximiert:
            admin.maximiert = False
            admin.minimiert = False
            bau.maximiert = False
            bau.minimiert = False
        else:
            admin.maximiert = True
            admin.minimiert = False
            bau.maximiert = False
            bau.minimiert = True

    elif aktion == "minimize":
        if admin.maximiert:
            admin.maximiert = False
            admin.minimiert = True
            bau.minimiert = False
        else:
            admin.minimiert = not admin.minimiert

    elif aktion == "restore":
        admin.maximiert = False
        admin.minimiert = False
        bau.maximiert = False
        bau.minimiert = False

    return zustand


router = APIRouter()
_TAB_ZUSTAND: dict[str, dict[str, ChatFensterZustand]] = {}


def hole_tab_zustand(tab_id: str) -> dict[str, ChatFensterZustand]:
    if tab_id not in _TAB_ZUSTAND:
        _TAB_ZUSTAND[tab_id] = neuer_tab_zustand()
    return _TAB_ZUSTAND[tab_id]


@router.post("/api/chat/{chat_id}")
def post_chat(chat_id: str, nachricht: ChatMessageIn) -> dict[str, object]:
    if chat_id not in CHAT_IDS:
        raise HTTPException(status_code=404, detail="unbekannter Chat")
    zustand = hole_tab_zustand(chat_id)
    panel = zustand[chat_id]
    panel.anhaengen("user", nachricht.text)
    intent = parse_intent(nachricht.text)
    antwort = f"[{CHAT_LABELS[chat_id]}] intent={intent['intent']}"
    panel.anhaengen("assistant", antwort)
    return {
        "chat_id": chat_id,
        "intent": intent,
        "zustand": panel.als_dict(),
        "layout": layout_fuer(zustand),
    }
