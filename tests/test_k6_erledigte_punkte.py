"""K6: _erledigte_punkte sammelt git log + ROADMAP ✅-Signale."""
from pathlib import Path
from unittest.mock import patch

from werkstatt.planner import _erledigte_punkte


def test_ohne_alles_leer(tmp_path: Path) -> None:
    assert _erledigte_punkte(tmp_path) == ""


def test_roadmap_mit_haken(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "ROADMAP.md").write_text(
        "# Roadmap\n- Punkt A ✅\n- Punkt B\n- Punkt C ✅\n",
        encoding="utf-8",
    )

    def _fake_run(*a, **kw):
        class _R:
            stdout = ""
            returncode = 0
        return _R()

    with patch("subprocess.run", side_effect=_fake_run):
        out = _erledigte_punkte(tmp_path)

    assert "Punkt A" in out
    assert "Punkt C" in out
    assert "Punkt B" not in out


def test_git_log_mit_haken(tmp_path: Path) -> None:
    def _fake_run(cmd, *a, **kw):
        class _R:
            stdout = "abc1234 feat: x ✅\ndef5678 feat: y ✅\n"
            returncode = 0
        return _R()

    with patch("subprocess.run", side_effect=_fake_run):
        out = _erledigte_punkte(tmp_path)

    assert "abc1234" in out
    assert "def5678" in out


def test_git_und_roadmap_kombiniert(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "ROADMAP.md").write_text("- A ✅\n", encoding="utf-8")

    def _fake_run(*a, **kw):
        class _R:
            stdout = "abc feat ✅\n"
            returncode = 0
        return _R()

    with patch("subprocess.run", side_effect=_fake_run):
        out = _erledigte_punkte(tmp_path)

    assert "Commits mit" in out
    assert "ROADMAP" in out


def test_roadmap_im_root_fallback(tmp_path: Path) -> None:
    (tmp_path / "ROADMAP.md").write_text("- X ✅\n", encoding="utf-8")

    def _fake_run(*a, **kw):
        class _R:
            stdout = ""
            returncode = 0
        return _R()

    with patch("subprocess.run", side_effect=_fake_run):
        out = _erledigte_punkte(tmp_path)

    assert "X" in out
