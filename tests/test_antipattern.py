"""OP-064b: Deterministischer Antipattern-Scanner.

Kein LLM. Erkennt im Patch-Diff (`new_string`) Muster, die dazu
dienen, Verify-Gates zu umgehen — statt den Code zu reparieren:

- `# type: ignore` / `# noqa` / `eslint-disable`
- `|| true` in Shell/Makefile-Kontexten
- geloeschte Tests (`action: delete` auf `tests/test_*.py`)
- geschwaechte Assertions (weniger `==` in assert-Zeilen als vorher)

Der Scanner liefert nur die Treffer. Ob ein Treffer ein Veto
ausloest, entscheidet die Pipeline anhand der harten Verify-Zone
(verify.json-Stages mit hart=true). Diese Trennung haelt den
Scanner rein deterministisch und testbar.
"""
from __future__ import annotations

from werkstatt.antipattern import AntiPattern, scan_patches


# ---------- type: ignore ----------

def test_type_ignore_wird_erkannt() -> None:
    patches = [{
        "action": "update",
        "file": "core/x.py",
        "old_string": "x = f()\n",
        "new_string": "x = f()  # type: ignore[arg-type]\n",
    }]
    treffer = scan_patches(patches)
    assert len(treffer) == 1
    ap = treffer[0]
    assert isinstance(ap, AntiPattern)
    assert ap.kind == "type_ignore"
    assert ap.file == "core/x.py"
    assert "type: ignore" in ap.sample


# ---------- noqa ----------

def test_noqa_wird_erkannt() -> None:
    patches = [{
        "action": "update",
        "file": "core/x.py",
        "old_string": "def f(  a):\n",
        "new_string": "def f(  a):  # noqa: E201\n",
    }]
    treffer = scan_patches(patches)
    assert any(a.kind == "noqa" for a in treffer)
    assert treffer[0].file == "core/x.py"


# ---------- eslint-disable ----------

def test_eslint_disable_wird_erkannt() -> None:
    patches = [{
        "action": "update",
        "file": "apps/web/foo.js",
        "old_string": "const x = 1;\n",
        "new_string": "// eslint-disable-next-line\nconst x = 1;\n",
    }]
    treffer = scan_patches(patches)
    assert any(a.kind == "eslint_disable" for a in treffer)


# ---------- || true in Shell-Kontext ----------

def test_shell_oder_true_wird_in_sh_erkannt() -> None:
    patches = [{
        "action": "update",
        "file": "scripts/build.sh",
        "old_string": "pytest\n",
        "new_string": "pytest || true\n",
    }]
    treffer = scan_patches(patches)
    assert any(a.kind == "shell_or_true" for a in treffer), treffer


def test_shell_oder_true_wird_in_makefile_erkannt() -> None:
    patches = [{
        "action": "update",
        "file": "Makefile",
        "old_string": "test:\n\tpytest\n",
        "new_string": "test:\n\tpytest || true\n",
    }]
    treffer = scan_patches(patches)
    assert any(a.kind == "shell_or_true" for a in treffer)


def test_python_or_true_kein_treffer() -> None:
    """`assert x or True` in .py ist schlechter Stil, aber kein
    shell_or_true-Muster — das ist Python-Semantik, kein Shell.
    """
    patches = [{
        "action": "update",
        "file": "core/x.py",
        "old_string": "assert x\n",
        "new_string": "assert x or True\n",
    }]
    treffer = scan_patches(patches)
    assert not any(a.kind == "shell_or_true" for a in treffer), treffer


# ---------- geloeschter Test ----------

def test_geloeschter_test_wird_erkannt() -> None:
    patches = [{
        "action": "delete",
        "file": "tests/test_x.py",
        "old_string": "",
        "new_string": "",
    }]
    treffer = scan_patches(patches)
    assert len(treffer) == 1
    assert treffer[0].kind == "deleted_test"
    assert treffer[0].file == "tests/test_x.py"


def test_geloeschte_nicht_test_datei_kein_treffer() -> None:
    patches = [{
        "action": "delete",
        "file": "core/x.py",
        "old_string": "",
        "new_string": "",
    }]
    treffer = scan_patches(patches)
    assert not any(a.kind == "deleted_test" for a in treffer)


# ---------- geschwaechte Assertion ----------

def test_geschwaechte_assertion_wird_erkannt() -> None:
    """assert x == 5 -> assert x : Vergleich entfernt, Gate geschwaecht."""
    patches = [{
        "action": "update",
        "file": "tests/test_x.py",
        "old_string": "    assert result == 5\n",
        "new_string": "    assert result\n",
    }]
    treffer = scan_patches(patches)
    assert any(a.kind == "weakened_assertion" for a in treffer), treffer


def test_gleichbleibende_assertion_kein_treffer() -> None:
    patches = [{
        "action": "update",
        "file": "tests/test_x.py",
        "old_string": "    assert result == 5\n",
        "new_string": "    assert result == 5  # kommentar hinzugefuegt\n",
    }]
    treffer = scan_patches(patches)
    assert not any(a.kind == "weakened_assertion" for a in treffer), treffer


# ---------- sauberer Patch ----------

def test_sauberer_patch_keine_treffer() -> None:
    patches = [{
        "action": "update",
        "file": "core/x.py",
        "old_string": "return a <= b\n",
        "new_string": "return int(a) <= int(b)\n",
    }]
    treffer = scan_patches(patches)
    assert treffer == []


# ---------- leere Eingabe ----------

def test_leere_eingabe_keine_treffer() -> None:
    assert scan_patches([]) == []


# ---------- Live-Pfad: Antipattern blockiert task_ok ----------

def test_live_pfad_antipattern_veto(
    tmp_path: Path, monkeypatch,
) -> None:
    """_refl_ok=True + _rev_ok=True + Patch mit # type: ignore
    -> human_review, KEIN loop_task_ok, verdict=vetoed.

    Live-Beleg: der LLM-Reviewer sieht den Diff, findet ihn
    'funktional richtig' (weil das Verify-Gate mit type: ignore
    durchgeht), wuerde approven. Der deterministische Scanner
    muss das VOR dem Erfolgs-Pfad abfangen.
    """
    from pathlib import Path as _P  # noqa: F401 -- local guard
    from werkstatt import loop as loop_mod
    from werkstatt.state import RunState

    (tmp_path / ".werkstatt").mkdir(exist_ok=True)
    (tmp_path / ".werkstatt" / "verify.json").write_text(
        '{"stages": [{"id": "pc", "command": ["python3", "-c", "pass"]}]}'
    )
    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "x.py").write_text("b = 2\n")

    st = RunState(
        block_id="p", aufgabe="a", start_ts="", docs={}, agents={},
        always={}, optional={}, file_whitelist=[], api_key="dummy",
        budget={}, agent_docs={}, project_dir=tmp_path, project_name="p",
    )
    st.tasks = [{"id": "t1", "name": "T1", "action": "update",
                 "task_files": ["core/x.py"]}]
    st.phasen = []

    _audits: list[tuple] = []
    monkeypatch.setattr(loop_mod, "audit",
                        lambda k, p, *a, **kw: _audits.append((k, p)))
    monkeypatch.setattr(loop_mod, "_plan_gate", lambda s: True)
    monkeypatch.setattr(
        loop_mod, "run_explorer",
        lambda s, a: {"key_files": [], "findings": "", "next_reads": []},
    )

    def _fake_builder(_s):
        # Patch enthaelt # type: ignore — Verify wuerde durchgehen,
        # aber das ist genau das Gameable-Muster.
        _s.patches = [{
            "action": "update", "file": "core/x.py",
            "old_string": "a = 1\n",
            "new_string": "b = 2  # type: ignore[no-untyped-def]\n",
        }]
        _s.applied_count = 1
        return True

    monkeypatch.setattr(loop_mod, "run_builder", _fake_builder)
    monkeypatch.setattr(loop_mod, "_verify_patches_soft",
                        lambda s, phase=None: (True, []))
    monkeypatch.setattr(loop_mod, "_call_hook",
                        lambda n, p: {"allow": True})

    def _fake_reviewer(_s):
        _s.reviewer_bugs = []
        return True

    monkeypatch.setattr(loop_mod, "run_reviewer", _fake_reviewer)

    from werkstatt import reviewer as _rv_mod
    monkeypatch.setattr(_rv_mod, "run_phase_end_review", lambda s: True)
    for _fn in ("header", "step", "task", "task_ok", "task_failed",
                "group_start", "group_end", "footer"):
        if hasattr(loop_mod, _fn):
            monkeypatch.setattr(loop_mod, _fn, lambda *a, **kw: None)

    loop_mod.run_pipeline_loop("p", "a", [st])

    kinds = [k for k, _ in _audits]
    assert "loop_task_antipattern_veto" in kinds, (
        f"kein Antipattern-Audit; kinds={kinds[-10:]}"
    )
    assert "loop_task_ok" not in kinds, (
        f"loop_task_ok darf NICHT kommen; kinds={kinds[-10:]}"
    )

    from werkstatt.phase_state import PhaseState
    ps = PhaseState("p", base_dir=tmp_path / ".werkstatt")
    ps.load()
    _t = ps.get_task("t1")
    assert _t is not None
    assert _t.get("status") == "human_review", (
        f"Status nicht human_review: {_t.get('status')}"
    )
    assert _t.get("verdict") == "vetoed", (
        f"Verdict nicht vetoed: {_t.get('verdict')}"
    )
