"""K12: _extrahiere_py_pfade zieht .py-Pfade aus .md-Body."""
from pathlib import Path

from werkstatt.explorer import _extrahiere_py_pfade


def test_py_pfade_aus_md(tmp_path: Path) -> None:
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "foo.py").write_text("x")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "STATUS.md").write_text(
        "Naechster Punkt: `app/foo.py` erweitern. Siehe app/bar.py (fehlt)."
    )
    pfade = _extrahiere_py_pfade(tmp_path, "docs/STATUS.md")
    assert "app/foo.py" in pfade
    assert "app/bar.py" not in pfade  # existiert nicht


def test_keine_py_pfade(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "STATUS.md").write_text("Nur Prosa, kein Code.")
    assert _extrahiere_py_pfade(tmp_path, "docs/STATUS.md") == []


def test_md_fehlt(tmp_path: Path) -> None:
    assert _extrahiere_py_pfade(tmp_path, "docs/fehlt.md") == []


def test_duplikate(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("x")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "X.md").write_text("a.py und a.py und a.py")
    assert _extrahiere_py_pfade(tmp_path, "docs/X.md") == ["a.py"]


def test_limitiert(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    lines = []
    for i in range(30):
        (tmp_path / f"m{i}.py").write_text("x")
        lines.append(f"m{i}.py")
    (tmp_path / "docs" / "X.md").write_text(" ".join(lines))
    pfade = _extrahiere_py_pfade(tmp_path, "docs/X.md")
    assert len(pfade) <= 15
