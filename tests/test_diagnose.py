"""Tests fuer werkstatt.diagnose (OP-081)."""
from __future__ import annotations

import ast
from types import SimpleNamespace

import pytest

from werkstatt.diagnose import (
    _deterministische_diagnose,
    _diagnose_import_fehlt,
    _diagnose_pfad_not_found,
)


@pytest.fixture
def op082_projekt(tmp_path):
    """Simuliert OP-082: app.py benutzt `chat` ohne Import."""
    (tmp_path / "werkstatt" / "web").mkdir(parents=True)
    (tmp_path / "werkstatt" / "__init__.py").write_text("")
    (tmp_path / "werkstatt" / "web" / "__init__.py").write_text("")
    (tmp_path / "werkstatt" / "web" / "chat.py").write_text(
        "router = object()\n"
    )
    app_py = tmp_path / "werkstatt" / "web" / "app.py"
    app_py.write_text(
        "from werkstatt.web import ws\n"
        "\n"
        "def create_app():\n"
        "    app = object()\n"
        "    app.include_router(chat.router)\n"
        "    return app\n"
    )
    return tmp_path, app_py


def _state(tmp_path, patches, errors):
    return SimpleNamespace(
        project_dir=str(tmp_path),
        patches=patches,
        last_verify_errors=errors,
    )


def test_import_fehlt_erkennt_chat(op082_projekt):
    tmp_path, app_py = op082_projekt
    state = _state(
        tmp_path,
        [{"file": "werkstatt/web/app.py"}],
        ["pytest_changed: NameError: name 'chat' is not defined"],
    )
    diag = _diagnose_import_fehlt(state, app_py, state.last_verify_errors[0])
    assert diag is not None
    assert diag["klasse"] == "import_fehlt"
    assert "from werkstatt.web import chat" in diag["new_string"]


def test_import_fehlt_patch_ist_anwendbar(op082_projekt):
    tmp_path, app_py = op082_projekt
    state = _state(
        tmp_path,
        [{"file": "werkstatt/web/app.py"}],
        ["pytest_changed: NameError: name 'chat' is not defined"],
    )
    diag = _deterministische_diagnose(state)
    assert diag is not None
    content = app_py.read_text()
    assert diag["old_string"] in content
    new_content = content.replace(diag["old_string"], diag["new_string"], 1)
    ast.parse(new_content)  # syntaktisch gueltig
    assert "from werkstatt.web import chat" in new_content


def test_import_fehlt_kein_match_wenn_importiert(op082_projekt):
    tmp_path, app_py = op082_projekt
    # `chat` jetzt importiert -> kein Patch
    app_py.write_text(
        "from werkstatt.web import ws\n"
        "from werkstatt.web import chat\n"
        "\n"
        "def create_app():\n"
        "    app = object()\n"
        "    app.include_router(chat.router)\n"
        "    return app\n"
    )
    state = _state(
        tmp_path,
        [{"file": "werkstatt/web/app.py"}],
        ["pytest_changed: NameError: name 'chat' is not defined"],
    )
    diag = _diagnose_import_fehlt(state, app_py, state.last_verify_errors[0])
    assert diag is None


def test_pfad_not_found(tmp_path):
    (tmp_path / "static").mkdir()
    (tmp_path / "static" / "layout.html").write_text("<html></html>")
    pkg = tmp_path / "werkstatt" / "web"
    pkg.mkdir(parents=True)
    (tmp_path / "werkstatt" / "__init__.py").write_text("")
    (pkg / "__init__.py").write_text("")
    app_py = pkg / "app.py"
    app_py.write_text(
        "from pathlib import Path\n"
        "\n"
        "static_dir = Path(__file__).parent / 'static'\n"
    )
    fehler = (
        f"pytest_changed: RuntimeError: Directory "
        f"'{pkg}/static' does not exist"
    )
    state = _state(
        tmp_path,
        [{"file": "werkstatt/web/app.py"}],
        [fehler],
    )
    diag = _diagnose_pfad_not_found(state, app_py, fehler)
    assert diag is not None
    assert diag["klasse"] == "pfad_falsch"
    assert "Path(__file__).resolve()" in diag["new_string"]
    assert ".parent" in diag["new_string"]
    assert '"/static"' in diag["new_string"] or "'static'" in diag["new_string"] or "/ \"static\"" in diag["new_string"]


def test_diagnose_kein_match(tmp_path):
    state = _state(tmp_path, [], ["unknown error"])
    assert _deterministische_diagnose(state) is None


def test_diagnose_orchestrator_erster_treffer(op082_projekt):
    tmp_path, app_py = op082_projekt
    state = _state(
        tmp_path,
        [{"file": "werkstatt/web/app.py"}],
        ["pytest_changed: NameError: name 'chat' is not defined"],
    )
    diag = _deterministische_diagnose(state)
    assert diag is not None
    assert diag["klasse"] == "import_fehlt"

def test_diagnose_fallback_ohne_patches(tmp_path):
    """Fallback ohne patches: scans alle .py, findet Datei die `mod`
    benutzt ohne Import, liefert `import mod`-Patch.

    Datei ohne Imports (nur def) -> Anker-Fallback greift (Zeile vor def).
    """
    (tmp_path / "mod.py").write_text("x = 1\n")
    nutzer = tmp_path / "nutzer.py"
    nutzer.write_text(
        "def nutze():\n"
        "    return mod.x\n"
    )
    state = SimpleNamespace(
        project_dir=str(tmp_path),
        patches=[],
        last_verify_errors=[
            "py_compile_changed: NameError: name 'mod' is not defined",
        ],
    )
    diag = _deterministische_diagnose(state)
    assert diag is not None, "Fallback ohne patches griff nicht"
    assert diag["klasse"] == "import_fehlt"
    assert "import mod" in diag["new_string"]
