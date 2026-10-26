"""K10: _sammle_projekt_py_files filtert .venv, site-packages etc."""
from pathlib import Path

from werkstatt.builder import _sammle_projekt_py_files


def test_venv_wird_gefiltert(tmp_path: Path) -> None:
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "x.py").write_text("import os\n")
    (tmp_path / ".venv" / "lib" / "site-packages" / "pkg").mkdir(parents=True)
    (tmp_path / ".venv" / "lib" / "site-packages" / "pkg" / "y.py").write_text("x")

    files = _sammle_projekt_py_files(tmp_path)
    names = [str(f.relative_to(tmp_path)) for f in files]
    assert "app/x.py" in names
    assert not any(".venv" in n for n in names), names


def test_pycache_wird_gefiltert(tmp_path: Path) -> None:
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "x.py").write_text("import os\n")
    (tmp_path / "app" / "__pycache__").mkdir()
    (tmp_path / "app" / "__pycache__" / "x.cpython.py").write_text("x")

    files = _sammle_projekt_py_files(tmp_path)
    names = [str(f.relative_to(tmp_path)) for f in files]
    assert "app/x.py" in names
    assert not any("__pycache__" in n for n in names), names


def test_node_modules_wird_gefiltert(tmp_path: Path) -> None:
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "x.py").write_text("import os\n")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "z.py").write_text("x")

    files = _sammle_projekt_py_files(tmp_path)
    names = [str(f.relative_to(tmp_path)) for f in files]
    assert not any("node_modules" in n for n in names), names


def test_limit_wird_eingehalten(tmp_path: Path) -> None:
    (tmp_path / "app").mkdir()
    for i in range(50):
        (tmp_path / "app" / f"m{i:02d}.py").write_text("x")

    files = _sammle_projekt_py_files(tmp_path, limit=10)
    assert len(files) == 10


def test_leeres_projekt(tmp_path: Path) -> None:
    assert _sammle_projekt_py_files(tmp_path) == []
