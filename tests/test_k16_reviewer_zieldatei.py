"""K16: run_reviewer haengt die volle Zieldatei immer an."""
from pathlib import Path
from unittest.mock import patch

from werkstatt import reviewer as _rv


class _State:
    def __init__(self, tmp: Path):
        self.project_dir = tmp
        self.project_name = "k16"
        self.api_key = "x"
        self.aufgabe = "x"
        self.baseline_gruen = True
        self.aktuelle_task = {
            "name": "t", "description": "d",
            "task_files": ["zieldatei.py"],
        }


def _fake_llm(api_key, system, user_content, **_):
    """LLM-Mock: gibt approved zurueck, sammelt user_content."""
    class _R:
        ok = True
        content = '{"approved": true, "bugs": [], "summary": "ok"}'
    _fake_llm.last_user = user_content
    return _R()


def test_zieldatei_kontext_immer_angehaengt(tmp_path: Path) -> None:
    (tmp_path / "zieldatei.py").write_text(
        "import re\n\nCONSTANT = 42\n\ndef existierende():\n    pass\n",
        encoding="utf-8",
    )
    st = _State(tmp_path)

    with patch.object(_rv, "_get_git_diff", return_value="diff..."), \
         patch.object(_rv, "ask_llm", side_effect=_fake_llm):
        _rv.run_reviewer(st)

    user = _fake_llm.last_user
    assert "VOLLE ZIELDATEI" in user, "K16: Zieldatei fehlt im Prompt"
    assert "import re" in user, "Import muss sichtbar sein"
    assert "CONSTANT = 42" in user
    assert "def existierende" in user


def test_ohne_task_files_kein_zieldatei_block(tmp_path: Path) -> None:
    st = _State(tmp_path)
    st.aktuelle_task = {"name": "t", "description": "d", "task_files": []}

    with patch.object(_rv, "_get_git_diff", return_value="diff..."), \
         patch.object(_rv, "ask_llm", side_effect=_fake_llm):
        _rv.run_reviewer(st)

    user = _fake_llm.last_user
    assert "VOLLE ZIELDATEI" not in user
