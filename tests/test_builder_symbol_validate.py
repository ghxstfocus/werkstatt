"""M-444b: Symbol-Validierung + Feedback-Loop."""
from __future__ import annotations


def test_fehlendes_symbol_wird_erkannt(tmp_path):
    """Wenn Modul existiert, aber Symbol fehlt -> Fehler."""
    from werkstatt.builder import _validate_imports_in_patch
    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "__init__.py").write_text("")
    # models.py existiert, aber hat KEIN BackupRecord.
    (tmp_path / "core" / "models.py").write_text("class Change: pass\n")
    patch = "from core.models import BackupRecord\n"
    fehlend = _validate_imports_in_patch(patch, tmp_path)
    assert any("BackupRecord" in f for f in fehlend), f"fehlend={fehlend}"


def test_vorhandenes_symbol_wird_akzeptiert(tmp_path):
    """Symbol existiert im Modul -> OK."""
    from werkstatt.builder import _validate_imports_in_patch
    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "__init__.py").write_text("")
    (tmp_path / "core" / "models.py").write_text(
        "class BackupRecord: pass\nclass Change: pass\n"
    )
    patch = "from core.models import BackupRecord\n"
    fehlend = _validate_imports_in_patch(patch, tmp_path)
    assert fehlend == [], f"fehlend={fehlend}"


def test_symbol_im_patch_definiert_wird_akzeptiert(tmp_path):
    """Wenn Symbol im selben Patch definiert wird -> OK, auch wenn Modul es nicht hat."""
    from werkstatt.builder import _validate_imports_in_patch
    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "__init__.py").write_text("")
    (tmp_path / "core" / "models.py").write_text("class Change: pass\n")
    # Patch importiert BackupRecord, definiert es aber selbst.
    patch = (
        "from core.models import BackupRecord\n"
        "class BackupRecord:\n"
        "    pass\n"
    )
    fehlend = _validate_imports_in_patch(patch, tmp_path)
    # BackupRecord ist im selben Patch definiert -> kein Fehler.
    assert not any("BackupRecord" in f for f in fehlend), f"fehlend={fehlend}"
