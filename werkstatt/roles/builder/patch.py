"""_normalisiere_aider_patches _filtere_auf_funktionen _archite (OP-140 Phase 2b)."""
from __future__ import annotations

from pathlib import Path

from . import _common as _bglob


def _normalisiere_aider_patches(
    patches: list, *, pd: Path, pn: str,
) -> list:
    """K48: Aider-Format (context+old+new) auf old_string/new_string
    normalisieren. Idempotent: Legacy-Patches laufen unveraendert durch.

    Wird von BEIDEN Builder-Pfaden aufgerufen:
      - Architect-Pfad (_build_patches_fuer_datei)
      - Klassischer Pfad (run_builder, direkter ask_llm-Call)
    """
    _out: list = []
    for _p in patches:
        if not isinstance(_p, dict):
            _out.append(_p)
            continue
        if _p.get("context") and _p.get("old") and _p.get("new") is not None:
            # K53b: Aider-Fallback. Wenn context+old nicht in Datei
            # passt, aber old allein: context verwerfen.
            _ctx_raw = _p["context"]
            _old = _p["old"]
            _new_val = _p["new"]
            _target = Path(pd) / _p.get("file", "")
            _use_context = True
            if _target.is_file():
                try:
                    _content = _target.read_text(encoding="utf-8")
                except OSError:
                    _content = ""
                if _content:
                    _candidates = (
                        _ctx_raw.rstrip() + "\n\n" + _old,
                        _ctx_raw + _old,
                    )
                    _with_ctx_ok = any(c in _content for c in _candidates)
                    _old_only_ok = _old in _content
                    if _old_only_ok and not _with_ctx_ok:
                        _use_context = False
            if _use_context:
                _ctx = _ctx_raw.rstrip() + "\n\n"
                _p = {
                    **_p,
                    "old_string": _ctx + _old,
                    "new_string": _ctx + _new_val,
                }
            else:
                _p = {
                    **_p,
                    "old_string": _old,
                    "new_string": _new_val,
                }
                _bglob.audit("builder_aider_context_verworfen",
                      {"file": _p.get("file", "")}, pd, pn)
            _p.pop("context", None)
            _p.pop("old", None)
            _p.pop("new", None)
            _bglob.audit("builder_aider_patch_normalisiert",
                  {"file": _p.get("file", ""),
                   "with_context": _use_context}, pd, pn)
        _out.append(_p)
    return _out


def _filtere_auf_funktionen(abschnitt: str, task_text: str) -> str:
    """GOLD: Filtert Datei-Abschnitt auf in Task genannte Funktionen.

    No-op, wenn task_text leer oder keine Kandidaten gefunden.
    """
    import re
    if not abschnitt or not task_text:
        return abschnitt
    _kandidaten = set()
    for _m in re.finditer(r"`([_a-zA-Z][_a-zA-Z0-9]{2,})`", task_text):
        _kandidaten.add(_m.group(1))
    for _m in re.finditer(r"\bdef\s+([_a-zA-Z][_a-zA-Z0-9]{2,})", task_text):
        _kandidaten.add(_m.group(1))
    for _m in re.finditer(r"\bclass\s+([_a-zA-Z][_a-zA-Z0-9]{2,})", task_text):
        _kandidaten.add(_m.group(1))
    if not _kandidaten:
        return abschnitt
    _bloecke = re.findall(r"```(?:python)?\n(.*?)```", abschnitt, re.DOTALL)
    if not _bloecke:
        return abschnitt
    _gefiltert = []
    for _block in _bloecke:
        for _name in _kandidaten:
            if re.search(rf"\bdef\s+{re.escape(_name)}\b", _block) or \
               re.search(rf"\bclass\s+{re.escape(_name)}\b", _block):
                _gefiltert.append(_block)
                break
    if not _gefiltert:
        return abschnitt
    return "\n\n".join(_gefiltert)


def _architect_abschnitt(
    beschreibung: str, zieldatei: str, task_text: str = "",
) -> str:
    """M-408c/M-450 + GOLD: Extrahiert den Abschnitt fuer eine Datei.

    Unterstuetzt ZWEI Formate:
    A) '## <pfad>'-Ueberschriften (alter Architect-Prompt):
       -> exakter Abschnitt.
    B) '## 3. Wie sieht die Loesung aus?' + darin '## <pfad>'
       (Gold-Architect-Prompt):
       -> Abschnitt ab '## <pfad>' bis zum naechsten '## '.

    Fallback: ganze Prosa.
    """
    import re
    if not beschreibung:
        return ""
    _hat_ueberschriften = bool(
        re.search(r"^##\s+\S", beschreibung, re.MULTILINE)
    )
    if not _hat_ueberschriften:
        return beschreibung
    # Format A: '## <pfad>' direkt.
    pattern_direct = rf"^##\s*{re.escape(zieldatei)}\s*$"
    m = re.search(pattern_direct, beschreibung, re.MULTILINE)
    if m:
        start = m.end()
        _next = re.search(r"^##\s+\S", beschreibung[start:], re.MULTILINE)
        if _next:
            return _filtere_auf_funktionen(beschreibung[start:start + _next.start()].strip(), task_text)
        return _filtere_auf_funktionen(beschreibung[start:].strip(), task_text)
    # Format B: '## <pfad>' innerhalb einer Sektion. Suche im
    # gesamten Text nach '## <pfad>' — auch wenn davor '## 3.' steht.
    for _m in re.finditer(
        rf"^##\s*{re.escape(zieldatei)}\s*$", beschreibung, re.MULTILINE
    ):
        start = _m.end()
        _next = re.search(r"^##\s+\S", beschreibung[start:], re.MULTILINE)
        if _next:
            return _filtere_auf_funktionen(beschreibung[start:start + _next.start()].strip(), task_text)
        return _filtere_auf_funktionen(beschreibung[start:].strip(), task_text)
    return ""  # Datei nicht in der Prosa


def _extrahiere_verbote(abschnitt: str) -> str:
    """FIX 2026-10-31: Zieht negative Anweisungen aus der Prosa.

    LLMs ignorieren Negativ-Anweisungen in langer Prosa. Wir stellen
    sie isoliert VOR die Prosa als eigenen Block.
    """
    import re as _re_v
    if not abschnitt:
        return ""
    _marker = _re_v.compile(
        r"\b(nicht|kein|keine|keiner|behalte|behalten|erhalte|erhalten|"
        r"nur|ausschliesslich|vermeide|verboten)\b",
        _re_v.IGNORECASE,
    )
    _saetze = _re_v.split(r"(?<=[.!?])\s+", abschnitt)
    _verbote: list[str] = []
    for _s in _saetze:
        _s_clean = _s.strip()
        if len(_s_clean) < 15 or len(_s_clean) > 400:
            continue
        if _marker.search(_s_clean):
            _verbote.append(_s_clean)
        if len(_verbote) >= 5:
            break
    if not _verbote:
        return ""
    return (
        "<verbote verbindlich=\"true\">\n"
        "Diese Anweisungen sind HART. Verletze sie NICHT:\n"
        + "\n".join(f"- {v}" for v in _verbote)
        + "\n</verbote>"
    )


def _pruefe_doku_patch_breite(
    patches: list, aufgabe: str, zieldatei: str, pd, pn,
) -> list:
    """FIX 2026-10-31: Reiner Loesch-Patch fuer Doku darf nicht
    mehrere nummerierte Punkte loeschen, wenn der Auftrag
    "nicht umnummerieren"/"behalte"/"unveraendert" sagt.

    Live-Beleg 2026-10-30 23:32: Builder loeschte Punkt 1+2,
    Nummerierung 2-7 rutschte auf 1-6.
    """
    import re as _re_breite
    if not patches:
        return patches
    _aufgabe_l = (aufgabe or "").lower()
    _negativ = (
        "nicht umnummerier" in _aufgabe_l
        or "keine umnummerier" in _aufgabe_l
        or "behalte" in _aufgabe_l
        or "unveraendert" in _aufgabe_l
        or "unverandert" in _aufgabe_l
        or "unverändert" in _aufgabe_l
    )
    if not _negativ:
        return patches
    _punkt_re = _re_breite.compile(r"^\s*\d+\.", _re_breite.MULTILINE)
    _ok: list = []
    for _p in patches:
        if not isinstance(_p, dict):
            _ok.append(_p)
            continue
        if _p.get("action", "update") != "update":
            _ok.append(_p)
            continue
        _new = _p.get("new_string", "") or ""
        _old = _p.get("old_string", "") or ""
        if _new.strip() != "":
            _ok.append(_p)
            continue
        _n_punkte = len(_punkt_re.findall(_old))
        if _n_punkte > 1:
            _bglob.audit("builder_patch_zu_breit", {
                "zieldatei": zieldatei,
                "nummerierte_punkte_im_old": _n_punkte,
                "old_prefix": _old[:200],
            }, pd, pn)
            continue
        _ok.append(_p)
    return _ok


def _korrigiere_doku_datum(
    patches: list[dict],
    heute: str,
    pd=None,
    pn: str = "?",
) -> list[dict]:
    """Sicherheitsnetz: korrigiert Zukunfts-Daten in Doku-Patches.

    Durchsucht new_string und content von STATUS.md/PROGRESS.md-Patches
    nach ISO-Daten (YYYY-MM-DD). Treffer, die in der Zukunft relativ
    zu `heute` liegen, werden durch `heute` ersetzt. Vergangene Daten
    bleiben unangetastet. Mutiert die dicts in-place.
    """
    import re as _re_dd
    if not patches:
        return patches
    _datum_re = _re_dd.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
    _doku_namen = {"STATUS.md", "PROGRESS.md"}
    for _p in patches:
        if not isinstance(_p, dict):
            continue
        _file = _p.get("file")
        if not isinstance(_file, str) or not _file:
            continue
        try:
            _name = Path(_file).name
        except (TypeError, ValueError):
            continue
        if _name not in _doku_namen:
            continue
        for _feld in ("new_string", "content"):
            _text = _p.get(_feld)
            if not isinstance(_text, str) or not _text:
                continue

            def _ersetze(
                m: _re_dd.Match[str],
                _file=_file,
            ) -> str:
                _treffer = m.group(1)
                if _treffer != heute and _treffer > heute:
                    if pd is not None:
                        _bglob.audit(
                            "builder_patch_datum_korrigiert",
                            {"file": _file,
                             "alt": _treffer, "neu": heute},
                            pd, pn,
                        )
                    return heute
                return _treffer

            _p[_feld] = _datum_re.sub(_ersetze, _text)
    return patches


def _korrigiere_builder_action(
    task: dict, pd: Path, pn: str,
) -> str:
    """K22b/c: Korrigiert Task-Action live gegen Dateisystem.

    - 'create' + Datei existiert -> 'update'
    - 'update' + Datei fehlt    -> 'create'

    Aendert task['action'] und gibt die (ggf. korrigierte)
    Action zurueck. Bei fehlendem task_files oder non-str:
    unveraendert.
    """
    act = task.get("action", "update")
    if act not in ("create", "update"):
        return act
    tf_list = task.get("task_files") or []
    if not tf_list or not isinstance(tf_list[0], str):
        return act
    ziel = pd / tf_list[0]
    exists = ziel.is_file()
    # K22b: NUR create->update bei existierender Datei
    # (Reflection-Runde 2: Datei ist aus Runde 1 da).
    # update->create wird NICHT korrigiert -- fail-closed bleibt.
    # Siehe test_builder_update_zieldatei_fehlt_bleibt_fail_closed.
    if act == "create" and exists:
        _bglob.audit("builder_action_korrigiert",
              {"datei": tf_list[0], "von": "create", "nach": "update",
               "grund": "datei_existiert"},
              pd, pn)
        task["action"] = "update"
        return "update"
    return act
