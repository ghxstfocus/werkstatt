"""Architect-Agent (Fix AZ Stufe 10, 2026-10-31).

Extrahiert aus planner.py. Baut den Architect-Prompt und ruft den
LLM-Call. Re-Export in planner.py erhaelt API-Kompatibilitaet
(Tests patchen werkstatt.planner._architect_system_with_builder).

Late-Binding-Proxies fuer _with_spinner, ask_llm, audit,
_strip_xml_tags, _get_architect_model -- alle werden in
werkstatt.planner aufgeloest, damit Test-Patches wirken.
"""
from __future__ import annotations

from pathlib import Path


def audit(*args, **kwargs):
    """Late-Binding-Proxy fuer werkstatt.planner.audit."""
    from werkstatt.planner import audit as _orig
    return _orig(*args, **kwargs)


def _with_spinner(*args, **kwargs):
    """Late-Binding-Proxy fuer werkstatt.planner._with_spinner."""
    from werkstatt.planner import _with_spinner as _orig
    return _orig(*args, **kwargs)


def ask_llm(*args, **kwargs):
    """Late-Binding-Proxy fuer werkstatt.planner.ask_llm."""
    from werkstatt.planner import ask_llm as _orig
    return _orig(*args, **kwargs)


def _strip_xml_tags(*args, **kwargs):
    """Late-Binding-Proxy fuer werkstatt.planner._strip_xml_tags."""
    from werkstatt.planner import _strip_xml_tags as _orig
    return _orig(*args, **kwargs)


def _get_architect_model() -> str:
    """Late-Binding-Getter fuer werkstatt.planner._ARCHITECT_MODEL."""
    from werkstatt.planner import _ARCHITECT_MODEL
    return _ARCHITECT_MODEL


ARCHITECT_SYSTEM = """Du bist ein elite Software-Architekt.
Beschreibe die Loesung in Prosa. KEIN JSON, KEIN Patch-Format.

Format (STRIKT einhalten):
  1. Was ist das Problem?
  2. Welche Datei(en) muessen geaendert werden?
  3. Wie sieht die Loesung aus?
     PRO DATEI EIN BLOCK. Innerhalb eines Blocks: EINE
     Funktion/Methode komplett (Signatur, Logik, Fehler,
     Rueckgabe) als zusammenhaengender Absatz. NICHT als
     nummerierte Schritte.
     Der Planner-Split schneidet die Prosa an Datei- und
     Funktionsgrenzen. Eine Task = ein reviewbares Interface.
     Beispiel GUT:
       "In app/foo.py: neue Funktion bar(x, y). Validiert
        x > 0, ruft helper(y), gibt Result zurueck. Bei
        Fehler: BarError."
     Beispiel SCHLECHT:
       "1. In bar(): validiere x. 2. In bar(): rufe
        helper(y). 3. In bar(): gib Result zurueck."
     Jede Funktion/Klasse ist EIN Block. Wenn eine Datei
     mehrere Funktionen hat: EIN Block pro Funktion.
  4. Welche Tests brauchen wir?

REGELN:
  - KEINE XML-Tags, KEINE DSML-Tool-Calls.
    Verboten: <shell_command>, <read_file>, <tool>, <function>,
    <function_calls>, <invoke>.
    Du bist Architekt, nicht Tool-Caller. Beschreibe die
    Loesung als Prosa.
  - Code muss ruff-konform sein (E, F, I, SIM, RUF, BLE).
  - __all__ sortiert.
  - Kein `except Exception` ohne `# noqa: BLE001`.
  - Max line-length 100.
  - Keine unbenutzten Variablen (F841).

API-STABILITAET (WICHTIG):
  - Bestehende API NIE umbenennen (z.B. ApplierError bleibt ApplierError).
  - Bestehende Signaturen NIE aendern ohne Not.
  - Bestehende Rueckgabetypen NIE aendern.
  - Neue Features: ADDITIV (neue Methoden, neue Klassen), nicht ersetzend.

FROZEN DATACLASSES:
  - Wenn ein Parameter `frozen=True` ist: NICHT setattr() aufrufen.
  - Nutze dict/separate Struktur fuer Zusatz-Daten.

DATEI-UEBERSCHRIFTEN (PFLICHT fuer jede Datei):

Fuer JEDE Datei, die du aenderst, schreibe eine eigene
Ueberschrift im Format "## <voller-pfad>". Diese Ueberschrift
wird vom Builder genutzt, um den richtigen Abschnitt zu finden.

Beispiel:
  ## 3. Wie sieht die Loesung aus?

  ## apps/dashboard/routes_state.py
  Neue Funktion _section_timeline()...

  ## apps/dashboard/static/js/dashboard.js
  Neue Funktion renderTimeline()...

Regeln:
  - Ueberschrift EXAKT der Dateipfad, KEIN Backtick, KEIN "Datei:".
  - Format: "## <pfad>" (zwei Rauten, dann Pfad).
  - Fuer jede Datei ein eigener Block.
  - Der Builder sucht "## <pfad>", um den Abschnitt zu finden.
  - Wenn du eine Datei ohne "## <pfad>"-Ueberschrift beschreibst,
    findet der Builder sie NICHT.

WENN NUR EINE DATEI BETROFFEN IST:
  Beschreibe sie direkt, mit "## <pfad>"-Ueberschrift.

GROESSEN-ZIEL:
  Eine Funktion/Methode = 50-150 Zeilen Code. Zu klein
  (< 30 Zeilen) -> kein reviewbares Interface. Zu gross
  (> 200 Zeilen) -> Semantik-Verlust im Builder.

TESTS SIND OUT-OF-SCOPE:
  Beschreibe KEINE Test-Dateien (tests/*, test_*.py, *_test.py).
  Beschreibe KEINE Aenderungen an Test-Dateien. Tests werden
  vom Menschen geschrieben, nicht vom Loop. Wenn deine Loesung
  Tests braucht: beschreibe nur, welche Faelle getestet werden
  sollten, nicht den Test-Code selbst.

MIGRATIONS-NUMMERN:
  - Wenn eine Migration noetig ist: pruefe data/migrations/.
  - Nimm die hoechste vorhandene Nummer +1.
  - Nummern-Kollision ist ein Review-Fail.
  - Nutze NIEMALS eine Nummer, die bereits als Datei existiert.

Antworte NUR mit diesem Prosa-Text. Kein Code, nur Beschreibung.

## GOLD: SCOUT-KONTEXT
Du bekommst im User-Content:
- "SCOUT-AUFTRAG" (vorformuliert).
- "VERFUEGBARE APIS (aus Code-Index)".

Nutze die APIs aus "VERFUEGBARE APIS" -- NICHT die aus der Aufgabe.
Wenn die Aufgabe eine API nennt, die nicht im API-Auszug steht:
  Nenne sie NICHT. Nutze die aehnlichste echte API.
Beispiel: Aufgabe sagt "read_events". API-Auszug hat
"list_recent_assessments". Nutze list_recent_assessments.
"""


_BUILDER_SCHNITTSTELLE = """## DER BUILDER (Schnittstelle)
- Modell: deepseek-chat, max 8000 Tokens.
- Input: eine Zieldatei + dein Abschnitt fuer diese Datei.
- Output: JSON-Patch mit old_string (aus Datei) + new_string (deine Beschreibung).
- Grenzen: keine Tools, keine API-Raterei, keine Imports ohne explizite Nennung.
- Du musst liefern: "## <pfad>", Interface (Signatur), Logik, Integration, Imports.
"""

_ARCHITECT_SCHNITTSTELLE = """## DER ARCHITECT (Schnittstelle)
- Liefert: Prosa mit "## <pfad>", Interface, Logik, Integration.
- Plant modular: welche Datei, welche Klasse, welcher Datenfluss.
- Modell: deepseek-reasoner.
"""

_REVIEWER_SCHNITTSTELLE = """## DER REVIEWER (Schnittstelle)
- Prueft: bricht der Code? Task erfuellt? Bestehende Aufrufe erhalten?
- HIGH-Bug wenn: bestehender Aufruf entfernt, Funktion ueberschrieben, API erfunden.
"""


def _architect_system_with_builder() -> str:
    """GOLD: ARCHITECT_SYSTEM + _BUILDER_SCHNITTSTELLE."""
    return ARCHITECT_SYSTEM + "\n\n" + _BUILDER_SCHNITTSTELLE


def _planner_system(aufgabe: str, explorer_ctx: dict | None = None) -> str:
    """M-376: Explorer-Dateien ZUERST (Lost-in-the-Middle).

    Goldstandard: Relevante Information an den Anfang des
    Kontexts. Die gemessenen Dateien sind die wichtigste
    Information — sie stehen VOR PLANNER_SYSTEM.
    """
    parts: list[str] = []

    # === K32: MIGRATIONSSTAND ZUERST (hoechste Prioritaet) ===
    # Der Architect darf Migrationsnummern NICHT raten.
    _mig_ctx = None
    if isinstance(explorer_ctx, dict):
        _mig_ctx = explorer_ctx.get("migrations")
    if isinstance(_mig_ctx, dict) and _mig_ctx.get("hoechste"):
        parts.append(
            "<migrationsstand pflicht=\"true\">\n"
            f"Hoechste belegte Migrationsnummer: {_mig_ctx['hoechste']}\n"
            f"Naechste freie Nummer: {_mig_ctx['naechste']}\n"
            f"VERBOTEN (belegt): {', '.join(n + '_*' for n in _mig_ctx.get('alle', [])[-5:])}\n"
            "Verwende fuer neue Migrationen NUR die naechste freie Nummer.\n"
            "Kollisionen fuehren zu Review-Fail und Loop-Abbruch.\n"
            "</migrationsstand>"
        )

    # === M-376: GEMESSENE DATEIEN ZUERST (hoechste Prioritaet) ===
    if isinstance(explorer_ctx, dict):
        _key = explorer_ctx.get("key_files") or []
        _files = [
            k.get("file") for k in _key
            if isinstance(k, dict) and k.get("file")
        ]
        if _files:
            _files_str = "\n".join(f"  - {f}" for f in _files)
            parts.append(
                "<measured_files>\n"
                f"Der Explorer hat {len(_files)} Datei(en) mit Fehlern "
                f"gemessen (deterministisch, nicht geraten):\n"
                f"{_files_str}\n"
                "</measured_files>"
            )
            parts.append(
                "<measured_files_hinweis>\n"
                f"Der Explorer hat {len(_files)} Datei(en) gemessen. "
                "Diese sind KONTEXT, keine Aufgabenliste.\n"
                "Wenn die Aufgabe explizit Funktionen oder Dateien nennt: "
                "halte dich an die Aufgabe.\n"
                "Nur wenn die Aufgabe keine Dateien nennt: waehle aus "
                "diesen Dateien.\n"
                "</measured_files_hinweis>"
            )
            # GOLD 2026-10-30: Datei-Inhalte der gemessenen Dateien.
            # Der Architect muss den Ist-Zustand kennen, sonst plant
            # er Aenderungen, die schon erledigt sind.
            _previews = []
            for _k in _key[:5]:
                if not isinstance(_k, dict):
                    continue
                _pf = _k.get("file", "")
                _pv = _k.get("preview", "")
                if _pf and _pv:
                    _previews.append(
                        f'<datei_inhalt datei="{_pf}">\n'
                        f'{_pv[:4000]}\n'
                        f'</datei_inhalt>'
                    )
            if _previews:
                parts.append(
                    "<ist_zustand>\n"
                    "Aktueller Inhalt der genannten Dateien:\n"
                    + "\n\n".join(_previews)
                    + "\n</ist_zustand>"
                )

        else:
            # M-405: Keine key_files -> KEIN <pflicht>
            parts.append(
                "<hinweis>\n"
                "Keine Dateien gemessen. Nutze <tools> (grep, read_file).\n"
                "Die findings enthalten Hinweise.\n"
                "</hinweis>"
            )

    # === GOLD: Architect-Modus IMMER (nicht nur bei "architect") ===
    # FIX 2026-10-30: bis hier wurde `parts` gebaut, aber am Ende
    # verworfen (Bug: alter if-True-Zweig gab nur _arch_parts zurueck).
    # Jetzt: `parts` (Migrationsstand + measured_files + pflicht/hinweis)
    # werden VOR ARCHITECT_SYSTEM gefuehrt. Sonst bleibt K32/M-376/M-405
    # toter Code.
    parts.append(ARCHITECT_SYSTEM)
    return "\n\n".join(parts)


def run_architect(
    state, aufgabe: str, user_content: str, api_key: str,
    explorer_ctx: dict | None,
) -> bool:
    """Ruft den Architect-LLM-Call (Fix AZ Stufe 10, 2026-10-31).

    Baut den Prompt aus _planner_system + _BUILDER_SCHNITTSTELLE.
    Setzt state.architect_prosa bei Erfolg. Rueckgabe: ok.
    """
    pd = state.project_dir
    pn = state.project_name
    _arch_sys_base = _planner_system(aufgabe, explorer_ctx)
    _arch_sys = _arch_sys_base + "\n\n" + _BUILDER_SCHNITTSTELLE
    _arch_reply = _with_spinner(
        "Architect",
        lambda: ask_llm(
            api_key, _arch_sys, user_content,
            model=_get_architect_model(),
            temperature=0.2, max_tokens=16000,
            aufgabe="architect",
        ),
    )
    if not _arch_reply.ok:
        audit("planner_architect_llm_fehler",
              {"fehler": _arch_reply.error}, pd, pn)
        return False
    _arch_prosa = _strip_xml_tags(_arch_reply.content.strip())
    if len(_arch_prosa.strip()) < 50:
        audit("planner_architect_prosa_zu_kurz",
              {"len": len(_arch_prosa),
               "raw_prefix": _arch_reply.content[:200]}, pd, pn)
        return False
    audit("planner_architect_ok",
          {"prosa_len": len(_arch_prosa)}, pd, pn)
    state.architect_prosa = _arch_prosa
    return True


__all__ = [
    'ARCHITECT_SYSTEM',
    '_BUILDER_SCHNITTSTELLE',
    '_architect_system_with_builder',
    '_planner_system',
    'run_architect',
]
