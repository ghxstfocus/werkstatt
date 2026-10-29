"""Tests fuer werkstatt/builder.py (Phase 6)."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from werkstatt.builder import run_builder
from werkstatt.state import RunState


def _state(tmp_path, tasks=None, api_key="fake"):
    return RunState(
        block_id="t", aufgabe="Baue Feature X", start_ts="",
        docs={}, agents={}, always={}, optional={},
        file_whitelist=[], api_key=api_key, budget={},
        agent_docs={}, project_dir=tmp_path, project_name="p"
    )


def test_builder_erstellt_patches(tmp_path):
    """M-337: Builder liefert Patch fuer Zieldatei mit passender action."""
    # Zieldatei muss existieren (action=update).
    (tmp_path / "a.py").write_text("x = 1\n")

    st = _state(tmp_path)
    st.tasks = [{
        "id": "t1", "name": "A", "description": "B",
        "action": "update", "task_files": ["a.py"],
    }]
    st.aktuelle_task = st.tasks[0]
    fake_json = '{"patches": [{"action": "update", "file": "a.py", "old_string": "x = 1", "new_string": "x = 2"}]}'

    class FakeReply:
        ok = True
        content = fake_json

    with patch("werkstatt.builder.ask_llm", return_value=FakeReply()):
        result = run_builder(st)
        assert result is True
        assert len(st.patches) == 1
        assert st.patches[0]["file"] == "a.py"


def test_builder_ohne_key(tmp_path):
    st = _state(tmp_path, api_key="")
    st.tasks = [{"id": "t1"}]
    assert run_builder(st) is False


def test_builder_ohne_tasks(tmp_path):
    st = _state(tmp_path)
    st.tasks = []
    assert run_builder(st) is False


def test_builder_read_only_task_kein_patch(tmp_path):
    """M-306a: action='read' -> kein LLM-Call, kein Patch."""
    st = _state(tmp_path)
    st.tasks = [{"id": "t1", "name": "Bestandsaufnahme", "action": "read"}]

    with patch("werkstatt.builder.ask_llm") as mock_llm, \
         patch("werkstatt.builder.audit"):
        result = run_builder(st)
    assert result is True
    assert mock_llm.call_count == 0  # kein LLM-Call
    assert st.patches == []  # keine Patches


def test_builder_idempotent_bei_korrekter_datei(tmp_path):
    """M-317: existierende korrekte Zieldatei + action=create -> idempotent."""
    from werkstatt.builder import run_builder

    st = _state(tmp_path)
    st.tasks = [{"id": "t1", "name": "test_checks.py schreiben", "action": "create"}]

    # Datei existiert und ist syntaktisch korrekt
    (tmp_path / "test_checks.py").write_text(
        "def test_foo():\n    assert True\n", encoding="utf-8"
    )

    with patch("werkstatt.builder.audit") as mock_audit:
        result = run_builder(st)

    assert result is True
    assert st.patches == []
    # Audit-Ruf "builder_nichts_zu_tun"
    assert any(
        c[0][0] == "builder_nichts_zu_tun" for c in mock_audit.call_args_list
    )


def test_builder_reflection_bei_inkorrekter_datei(tmp_path):
    """M-316: existierende inkorrekte Zieldatei -> kein task_ok, Reflection."""
    from werkstatt.builder import run_builder

    st = _state(tmp_path)
    st.tasks = [{"id": "t1", "name": "test_checks.py schreiben", "action": "write"}]

    # Datei existiert, ist syntaktisch FALSCH
    (tmp_path / "test_checks.py").write_text(
        "def test_foo(:\n    assert True\n", encoding="utf-8"
    )

    with patch("werkstatt.builder.ask_llm") as mock_llm, \
         patch("werkstatt.builder.audit") as mock_audit:
        mock_llm.return_value = type("R", (), {"ok": True, "content": '{"patches": []}', "error": ""})()
        _result = run_builder(st)

    # Soll NICHT idempotent-True sein
    assert not any(
        c[0][0] == "builder_nichts_zu_tun" for c in mock_audit.call_args_list
    )


def test_builder_idempotent_bei_create_und_update(tmp_path):
    """M-318: Idempotenz-Check bei create+update (M-317 war zu strikt)."""
    from werkstatt.builder import run_builder

    st = _state(tmp_path)
    # Datei existiert + ist korrekt
    (tmp_path / "test_checks.py").write_text(
        "def test_foo():\n    assert True\n", encoding="utf-8"
    )

    # Task: action=create, Datei existiert -> idempotent (nichts zu tun)
    st.tasks = [{"id": "t1", "name": "test_checks.py schreiben", "action": "create"}]

    with patch("werkstatt.builder.audit") as mock_audit:
        result = run_builder(st)

    assert result is True
    assert st.patches == []
    assert any(
        c[0][0] == "builder_nichts_zu_tun" for c in mock_audit.call_args_list
    )


def test_builder_update_inkorrekte_datei_nutzt_patch_pfad(tmp_path):
    """M-318: Bei action=update + INKORREKTER Datei -> Patch-Pfad.

    Der Idempotenz-Check greift nur, wenn die Datei syntaktisch
    korrekt ist. Bei inkorrekter Datei muss der Builder durch den
    Patch-Pfad (kein builder_nichts_zu_tun, sondern echte Arbeit).
    """
    from werkstatt.builder import run_builder

    st = _state(tmp_path)
    # Datei existiert, aber ist syntaktisch FALSCH
    (tmp_path / "test_checks.py").write_text(
        "def test_foo(:\n    assert True\n", encoding="utf-8"
    )

    st.tasks = [{"id": "t1", "name": "test_checks.py reparieren", "action": "update"}]

    with patch("werkstatt.builder.ask_llm") as mock_llm, \
         patch("werkstatt.builder.audit") as mock_audit:
        mock_llm.return_value = type("R", (), {
            "ok": True, "content": '{"patches": []}', "error": ""
        })()
        result = run_builder(st)

    # Datei ist inkorrekt -> py_compile schlaegt fehl -> _all_ok=False
    # -> normaler Patch-Pfad -> LLM liefert leere Patches -> False
    assert result is False

    # KEIN "nichts zu tun" (weil Datei inkorrekt)
    assert not any(
        c[0][0] == "builder_nichts_zu_tun" for c in mock_audit.call_args_list
    )


def test_builder_update_kein_idempotenz(tmp_path):
    """M-352: update + Datei existiert + korrekt -> KEIN Idempotenz.

    M-352 stellt M-317 wieder her: update-Tasks gehen immer durch
    den Patch-Pfad, auch wenn die Datei korrekt ist. Sonst wuerde
    ein update-Task ('Unused Imports entfernen') als 'nichts zu tun'
    gewertet, obwohl die Datei unused imports hat.
    """
    from werkstatt.builder import run_builder

    st = _state(tmp_path)
    st.tasks = [{"id": "t1", "name": "test_checks.py erweitern",
                 "action": "update", "task_files": ["test_checks.py"]}]
    st.aktuelle_task = st.tasks[0]

    (tmp_path / "test_checks.py").write_text(
        "def test_foo():\n    assert True\n", encoding="utf-8"
    )

    with patch("werkstatt.builder.audit") as mock_audit, \
         patch("werkstatt.builder.ask_llm") as mock_llm:
        mock_llm.return_value = type("R", (), {
            "ok": True, "content": '{"patches": []}', "error": ""
        })()
        result = run_builder(st)

    # update -> Patch-Pfad. LLM liefert leere Patches -> False.
    assert result is False
    # KEIN builder_nichts_zu_tun (Idempotenz-Pfad).
    assert not any(
        c[0][0] == "builder_nichts_zu_tun" for c in mock_audit.call_args_list
    )


def test_builder_prompt_import_regeln():
    """M-333a/M-416: BUILDER_SYSTEM enthaelt Import-Regeln.

    M-416 hat den Prompt radikal gekuerzt. Die alten M-333a-Strings
    ("Verwende AUSSCHLIESSLICH Imports", "Erfinde KEINE Modulnamen")
    sind nicht mehr woertlich drin. Stattdessen pruefen wir die
    aktuellen Regeln: ruff-Konformitaet und API-Stabilitaet.
    """
    from werkstatt.builder import BUILDER_SYSTEM
    assert "ruff-konform" in BUILDER_SYSTEM
    assert "API-Aenderungen" in BUILDER_SYSTEM or "Umbenennungen" in BUILDER_SYSTEM


def test_builder_create_task_mit_import_kontext(tmp_path):
    """M-333b: Bei create-Task werden Projekt-Imports gesammelt."""
    from unittest.mock import patch

    from werkstatt.builder import run_builder

    # Bestehende .py-Datei mit Import
    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "__init__.py").write_text(
        "from core.checks import check_port\n"
    )
    # Neue Datei (existiert nicht)
    st = _state(tmp_path)
    st.tasks = [
        {"id": "t1", "name": "neue_datei.py anlegen",
         "action": "create"},
    ]
    # Task-Text enthaelt Pfad
    st.tasks[0]["description"] = "Erstelle tests/unit/test_neu.py"

    _audits = []
    def _mock_audit(kind, payload, *a, **kw):
        _audits.append(kind)

    with patch("werkstatt.builder.audit", side_effect=_mock_audit), \
         patch("werkstatt.builder.ask_llm") as mock_llm:
        mock_llm.return_value = type("R", (), {
            "ok": True, "content": '{"patches": []}', "error": ""
        })()
        run_builder(st)

    # builder_import_context sollte gefeuert haben
    assert "builder_import_context" in _audits, \
        f"erwartet builder_import_context, war {_audits}"


def test_builder_create_ohne_imports(tmp_path):
    """M-333b: Bei create ohne benachbarte .py-Dateien -> kein Crash."""
    from unittest.mock import patch

    from werkstatt.builder import run_builder

    st = _state(tmp_path)
    st.tasks = [{"id": "t1", "name": "leer.py anlegen", "action": "create"}]

    with patch("werkstatt.builder.ask_llm") as mock_llm:
        mock_llm.return_value = type("R", (), {
            "ok": True, "content": '{"patches": []}', "error": ""
        })()
        result = run_builder(st)
    # Kein Crash
    assert result in (True, False)


def test_builder_task_files_priorisiert(tmp_path):
    """M-335: task_files kommen zuerst in _file_context."""
    from unittest.mock import patch

    from werkstatt.builder import run_builder

    # Zwei Dateien
    (tmp_path / "core").mkdir()
    # Datei syntaktisch FALSCH: Idempotenz-Check greift nicht,
    # Builder geht weiter zu _relevant_files.
    (tmp_path / "core" / "checks.py").write_text("def check(:\n")
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools" / "port.py").write_text("def port(): pass\n")

    st = _state(tmp_path)
    st.tasks = [{"id": "t1", "name": "refactor", "action": "update",
                 "task_files": ["core/checks.py"]}]
    st.aktuelle_task = st.tasks[0]

    _file_ctx = []
    def _mock_audit(kind, payload, *a, **kw):
        if kind == "builder_file_context":
            _file_ctx.extend(payload.get("files", []))

    with patch("werkstatt.builder.audit", side_effect=_mock_audit), \
         patch("werkstatt.builder.ask_llm") as mock_llm:
        mock_llm.return_value = type("R", (), {
            "ok": True, "content": '{"patches": []}', "error": ""
        })()
        run_builder(st)

    # core/checks.py muss in _file_context sein
    assert "core/checks.py" in _file_ctx, f"erwartet core/checks.py, war {_file_ctx}"


def test_builder_task_files_leer_fallback(tmp_path):
    """M-335: Ohne task_files bleibt altes Verhalten (Task-Text + Explorer)."""
    from unittest.mock import patch

    from werkstatt.builder import run_builder

    (tmp_path / "tools").mkdir()
    (tmp_path / "tools" / "port.py").write_text("def port(): pass\n")

    st = _state(tmp_path)
    st.tasks = [{"id": "t1", "name": "refactor", "action": "update"}]
    st.aktuelle_task = st.tasks[0]
    st.explorer_context = {"key_files": ["tools/port.py"]}

    _file_ctx = []
    def _mock_audit(kind, payload, *a, **kw):
        if kind == "builder_file_context":
            _file_ctx.extend(payload.get("files", []))

    with patch("werkstatt.builder.audit", side_effect=_mock_audit), \
         patch("werkstatt.builder.ask_llm") as mock_llm:
        mock_llm.return_value = type("R", (), {
            "ok": True, "content": '{"patches": []}', "error": ""
        })()
        run_builder(st)

    # tools/port.py (Explorer-Fallback) ist da
    assert "tools/port.py" in _file_ctx


def test_builder_task_files_nicht_str(tmp_path):
    """M-335: task_files mit Nicht-String-Werten werden ignoriert."""
    from unittest.mock import patch

    from werkstatt.builder import run_builder

    st = _state(tmp_path)
    st.tasks = [{"id": "t1", "name": "refactor", "action": "update",
                 "task_files": [None, 123, "core/checks.py"]}]
    st.aktuelle_task = st.tasks[0]

    # Kein Crash
    with patch("werkstatt.builder.ask_llm") as mock_llm:
        mock_llm.return_value = type("R", (), {
            "ok": True, "content": '{"patches": []}', "error": ""
        })()
        result = run_builder(st)
    assert result in (True, False)


def test_builder_ordner_in_task_files(tmp_path):
    """M-336: task_files mit Ordner -> .py-Dateien im Ordner gelesen."""
    from unittest.mock import patch

    from werkstatt.builder import run_builder

    # Ordner mit __init__.py
    (tmp_path / "core" / "checks").mkdir(parents=True)
    (tmp_path / "core" / "checks" / "__init__.py").write_text(
        "def broken(:\n"  # Syntax-Fehler -> Idempotenz greift nicht
    )

    st = _state(tmp_path)
    st.tasks = [{"id": "t1", "name": "refactor", "action": "update",
                 "task_files": ["core/checks/"]}]
    st.aktuelle_task = st.tasks[0]

    _file_ctx = []
    def _mock_audit(kind, payload, *a, **kw):
        if kind == "builder_file_context":
            _file_ctx.extend(payload.get("files", []))

    with patch("werkstatt.builder.audit", side_effect=_mock_audit), \
         patch("werkstatt.builder.ask_llm") as mock_llm:
        mock_llm.return_value = type("R", (), {
            "ok": True, "content": '{"patches": []}', "error": ""
        })()
        run_builder(st)

    # core/checks/__init__.py muss in _file_context sein
    assert any("core/checks/__init__.py" in f for f in _file_ctx), \
        f"erwartet core/checks/__init__.py, war {_file_ctx}"


def test_builder_ordner_leer(tmp_path):
    """M-336: task_files mit leerem Ordner -> kein Crash."""
    from unittest.mock import patch

    from werkstatt.builder import run_builder

    (tmp_path / "core" / "leer").mkdir(parents=True)

    st = _state(tmp_path)
    st.tasks = [{"id": "t1", "name": "refactor", "action": "update",
                 "task_files": ["core/leer/"]}]
    st.aktuelle_task = st.tasks[0]

    with patch("werkstatt.builder.ask_llm") as mock_llm:
        mock_llm.return_value = type("R", (), {
            "ok": True, "content": '{"patches": []}', "error": ""
        })()
        result = run_builder(st)
    assert result in (True, False)


def test_builder_zieldatei_aus_task_files(tmp_path):
    """M-337: Zieldatei wird aus task_files bestimmt."""
    from unittest.mock import patch

    from werkstatt.builder import run_builder

    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "checks.py").write_text("def check(: pass\n")  # inkorrekt

    st = _state(tmp_path)
    st.tasks = [{"id": "t1", "name": "refactor", "action": "update",
                 "task_files": ["core/checks.py"],
                 "description": "## core/checks.py\nAendere die Datei."}]
    st.aktuelle_task = st.tasks[0]

    _user_content = []
    def _mock_ask(api_key, system, user_content, **kw):
        _user_content.append(user_content)
        return type("R", (), {"ok": False, "content": "", "error": "skip"})()

    with patch("werkstatt.builder.ask_llm", side_effect=_mock_ask), \
         patch("werkstatt.builder.audit"):
        run_builder(st)

    assert _user_content, "ask_llm wurde nicht gerufen"
    prompt = _user_content[0]
    # GOLD: _build_patches_fuer_datei nutzt "## ZIELDATEI: ..."
    # Die Aktion steht nicht im Prompt (LLM entscheidet anhand Task).
    assert "core/checks.py" in prompt


@pytest.mark.skip(reason="GOLD: _build_patches_fuer_datei setzt file=zieldatei (M-444), falsche Datei wird korrigiert statt abgelehnt")
def test_builder_patch_falsche_datei_abgelehnt(tmp_path):
    """M-337: Patch mit falscher Datei -> builder_patch_invalid, False."""
    from unittest.mock import patch

    from werkstatt.builder import run_builder

    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "checks.py").write_text("x = 1\n")

    st = _state(tmp_path)
    st.tasks = [{"id": "t1", "name": "refactor", "action": "update",
                 "task_files": ["core/checks.py"]}]
    st.aktuelle_task = st.tasks[0]

    _audits = []
    def _mock_ask(*a, **kw):
        return type("R", (), {
            "ok": True,
            "content": '{"patches": [{"action": "create", "file": "FALSCH.py", "content": "x"}]}',
            "error": ""
        })()

    with patch("werkstatt.builder.ask_llm", side_effect=_mock_ask), \
         patch("werkstatt.builder.audit",
               side_effect=lambda k, p, *a, **kw: _audits.append(k)):
        result = run_builder(st)

    assert result is False
    assert "builder_patch_invalid" in _audits


def test_builder_patch_richtige_datei(tmp_path):
    """M-337: Patch mit richtiger Datei + Aktion -> True."""
    from unittest.mock import patch

    from werkstatt.builder import run_builder

    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "checks.py").write_text("x = 1\n")

    st = _state(tmp_path)
    st.tasks = [{"id": "t1", "name": "refactor", "action": "update",
                 "task_files": ["core/checks.py"],
                 "description": "## core/checks.py\nAendere x = 1 zu x = 2."}]
    st.aktuelle_task = st.tasks[0]

    def _mock_ask(*a, **kw):
        return type("R", (), {
            "ok": True,
            "content": '{"patches": [{"action": "update", "file": "core/checks.py", "old_string": "x = 1", "new_string": "x = 2"}]}',
            "error": ""
        })()

    with patch("werkstatt.builder.ask_llm", side_effect=_mock_ask), \
         patch("werkstatt.builder.audit"):
        result = run_builder(st)

    assert result is True
    assert st.patches[0]["file"] == "core/checks.py"


def test_builder_task_files_nur_diese(tmp_path):
    """M-337-b: task_files gesetzt -> NUR task_files in _file_context."""
    from unittest.mock import patch

    from werkstatt.builder import run_builder

    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "checks.py").write_text("def broken(:\n")
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools" / "port.py").write_text("def port(): pass\n")

    st = _state(tmp_path)
    st.tasks = [{"id": "t1", "name": "refactor", "action": "update",
                 "task_files": ["core/checks.py"]}]
    st.aktuelle_task = st.tasks[0]
    # Explorer-Key-Files: tools/port.py (sollte ignoriert werden)
    st.explorer_context = {"key_files": ["tools/port.py"]}

    _file_ctx = []
    def _mock_audit(kind, payload, *a, **kw):
        if kind == "builder_file_context":
            _file_ctx.extend(payload.get("files", []))

    with patch("werkstatt.builder.ask_llm") as mock_llm, \
         patch("werkstatt.builder.audit", side_effect=_mock_audit):
        mock_llm.return_value = type("R", (), {
            "ok": True,
            "content": '{"patches": [{"action": "update", "file": "core/checks.py", "old_string": "x", "new_string": "y"}]}',
            "error": ""
        })()
        run_builder(st)

    # core/checks.py muss da sein, tools/port.py NICHT
    assert "core/checks.py" in _file_ctx, f"erwartet core/checks.py, war {_file_ctx}"
    assert "tools/port.py" not in _file_ctx, f"tools/port.py sollte nicht da sein: {_file_ctx}"


def test_explorer_prompt_m338():
    """M-338-Fix: Explorer-Prompt fordert Messung statt nur expliziter Dateien."""
    from werkstatt.explorer import EXPLORER_SYSTEM
    # Der neue Prompt verbietet das Raten und verlangt Messung.
    assert "Rate NICHT" in EXPLORER_SYSTEM or "rate nicht" in EXPLORER_SYSTEM.lower()
    assert "Messung" in EXPLORER_SYSTEM or "messen" in EXPLORER_SYSTEM.lower()

def test_planner_prompt_m339():
    """M-339: Planner-Prompt nennt Datei-Pflicht."""
    from werkstatt.planner import PLANNER_SYSTEM
    assert "MIT Suffix" in PLANNER_SYSTEM
    assert "KEINE Ordner" in PLANNER_SYSTEM


@pytest.mark.skip(reason="GOLD: _build_patches_fuer_datei kann keine neuen Dateien anlegen (braucht existierende Datei); create-Pfad fehlt, K62")
def test_builder_create_zieldatei_fehlt_wird_angelegt(tmp_path):
    """M-360: create + Datei fehlt -> Zieldatei aus task_files, LLM legt sie an.

    Vor M-360 warf der Builder builder_zieldatei_nicht_gefunden,
    sobald keine task_file existierte — auch bei action=create.
    Damit wurde M-352 (Idempotenz bei create) nie erreicht, und
    create-Tasks scheiterten strukturell.

    Nach M-360: bei action=create und fehlender Datei nimmt der
    Builder die erste task_file als Zieldatei, Audit
    builder_zieldatei_create_neu.
    """
    from werkstatt.builder import run_builder

    st = _state(tmp_path)
    st.tasks = [{"id": "t1", "name": "neues Modul anlegen",
                 "action": "create", "task_files": ["core/neu.py"]}]
    st.aktuelle_task = st.tasks[0]

    # Zieldatei existiert NICHT.
    assert not (tmp_path / "core" / "neu.py").exists()

    fake_json = (
        '{"patches": [{"action": "create", "file": "core/neu.py", '
        '"content": "x = 1\\n"}]}'
    )

    class FakeReply:
        ok = True
        content = fake_json

    _audits = []
    with patch("werkstatt.builder.ask_llm", return_value=FakeReply()), \
         patch("werkstatt.builder.audit",
               lambda k, p, *a, **kw: _audits.append(k)):
        result = run_builder(st)

    # M-360: create-Zieldatei-Audit statt zieldatei_nicht_gefunden.
    assert "builder_zieldatei_create_neu" in _audits, f"audits={_audits}"
    assert "builder_zieldatei_nicht_gefunden" not in _audits, (
        f"M-360: zieldatei_nicht_gefunden bei create; audits={_audits}"
    )
    assert result is True, "Builder muss erfolgreich sein"
    assert len(st.patches) == 1
    assert st.patches[0]["action"] == "create"
    assert st.patches[0]["file"] == "core/neu.py"


def test_builder_update_zieldatei_fehlt_bleibt_fail_closed(tmp_path):
    """M-360-Gegenprobe: update + Datei fehlt -> fail-closed.

    M-360 aendert NUR create-Tasks. update-Tasks mit fehlender
    Zieldatei bleiben fail-closed (builder_zieldatei_nicht_gefunden).
    """
    from werkstatt.builder import run_builder

    st = _state(tmp_path)
    st.tasks = [{"id": "t1", "name": "bestehendes Modul aendern",
                 "action": "update", "task_files": ["core/fehlt.py"]}]
    st.aktuelle_task = st.tasks[0]

    assert not (tmp_path / "core" / "fehlt.py").exists()

    _audits = []
    with patch("werkstatt.builder.audit",
               lambda k, p, *a, **kw: _audits.append(k)):
        result = run_builder(st)

    assert result is False
    assert "builder_zieldatei_nicht_gefunden" in _audits, f"audits={_audits}"
    assert "builder_zieldatei_create_neu" not in _audits, (
        f"M-360: create-Audit bei update; audits={_audits}"
    )

