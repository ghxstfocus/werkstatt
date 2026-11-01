"""OP-053: git_author aus Manifest wird in RunState geladen."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, "/opt/werkstatt")


def test_runstate_hat_git_author_felder():
    from werkstatt.state import RunState
    # Felder muessen existieren (auch wenn leer)
    s = RunState(
        block_id="t", aufgabe="t", start_ts="t", docs={}, agents={},
        always={}, optional={}, file_whitelist=[], api_key="x",
        budget={}, agent_docs={}, project_dir=Path("/tmp"),
    )
    assert hasattr(s, "git_author_name")
    assert hasattr(s, "git_author_email")


def test_committer_fallback_ohne_author():
    """Ohne git_author -> Fallback builder@local."""
    src = Path("/opt/werkstatt/werkstatt/committer.py").read_text(encoding="utf-8")
    assert 'or "builder"' in src
    assert 'or "builder@security-ai.local"' in src


def test_loop_setzt_git_author_aus_cfg():
    """loop.py liest git_author aus projects/<name>.yaml."""
    src = Path("/opt/werkstatt/werkstatt/loop.py").read_text(encoding="utf-8")
    assert "_git_author_cfg" in src
    assert 'git_author_name=' in src
    assert 'git_author_email=' in src
