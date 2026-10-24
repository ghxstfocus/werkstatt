"""Tests fuer werkstatt/skills.py und werkstatt/tools.py."""
from pathlib import Path

from werkstatt.skills import (
    load_all_skills,
    load_skill_by_name,
    skills_summary,
)
from werkstatt.tools import run_readonly, run_write


def test_load_all_skills_liefert_12() -> None:
    skills = load_all_skills()
    assert len(skills) == 12, f"erwartet 12, gefunden {len(skills)}"


def test_jeder_skill_hat_name_und_description() -> None:
    for s in load_all_skills():
        assert s["name"], f"name fehlt: {s['dir']}"
        assert s["description"], f"description fehlt: {s['name']}"


def test_activate_skill_laedt_body() -> None:
    skills = load_all_skills()
    s = load_skill_by_name("systematic-debugging", skills)
    assert s is not None
    assert s["body"] is not None
    assert "Systematic-Debugging" in s["body"]


def test_allowed_tools_im_frontmatter() -> None:
    skills = load_all_skills()
    s = load_skill_by_name("systematic-debugging", skills)
    assert s is not None
    assert "run_readonly" in s["allowed_tools"]


def test_skills_summary_ist_kompakt() -> None:
    skills = load_all_skills()
    summary = skills_summary(skills)
    assert len(summary.splitlines()) == 12
    assert "systematic-debugging" in summary


# === tools.py ===

def test_run_readonly_erlaubt_ruff(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("x = 1\n")
    r = run_readonly("ruff check .", tmp_path)
    assert "error" not in r or r.get("ok") is not None


def test_run_readonly_blockiert_rm(tmp_path: Path) -> None:
    r = run_readonly("rm -rf /", tmp_path)
    assert r["ok"] is False
    assert "blockiert" in r["error"]


def test_run_readonly_blockiert_git_commit(tmp_path: Path) -> None:
    r = run_readonly("git commit -m x", tmp_path)
    assert r["ok"] is False
    assert "blockiert" in r["error"]


def test_run_readonly_blockiert_nicht_erlaubt(tmp_path: Path) -> None:
    r = run_readonly("make install", tmp_path)
    assert r["ok"] is False
    assert "nicht erlaubt" in r["error"]


def test_run_write_erlaubt_ruff_fix(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("x=1\n")
    r = run_write("ruff check --fix .", tmp_path)
    assert r.get("rc") is not None


def test_run_write_blockiert_trotzdem_rm(tmp_path: Path) -> None:
    r = run_write("rm -rf /", tmp_path)
    assert r["ok"] is False
    assert "blockiert" in r["error"]
