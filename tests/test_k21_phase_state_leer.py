"""K21: Leerer aber existierender Phase-State triggert init_new."""
import yaml
from pathlib import Path

from werkstatt.phase_state import PhaseState


def test_leerer_state_wird_erkannt(tmp_path: Path):
    """{} in Datei -> data = {} -> kein tasks-Feld."""
    ps = PhaseState("testproj", base_dir=tmp_path)
    ps.path.write_text("{}\n")
    assert ps.load() is True
    assert ps.data == {}
    assert not ps.data.get("tasks")


def test_leerer_state_dann_init_new(tmp_path: Path):
    """Nach load mit {} -> init_new ueberschreibt."""
    ps = PhaseState("testproj", base_dir=tmp_path)
    ps.path.write_text("{}\n")
    ps.load()
    ps.init_new(
        "aufgabe",
        [{"id": "t1", "name": "A", "task_files": ["a.py"]}],
        tests=[],
        akzeptanzkriterien=[],
    )
    with ps.path.open() as fh:
        d = yaml.safe_load(fh)
    assert d.get("tasks")
    assert len(d["tasks"]) == 1
