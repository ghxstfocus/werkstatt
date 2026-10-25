"""M-444: Builder verwirft Patches mit unaufloesbaren Imports."""
from __future__ import annotations


def test_validate_imports_findet_fehlendes_modul(tmp_path):
    from werkstatt.builder import _validate_imports_in_patch
    patch = "from core.changeapplier.errors import ApplierError\n"
    fehlend = _validate_imports_in_patch(patch, tmp_path)
    assert "core" in fehlend


def test_validate_imports_ok_fuer_stdlib(tmp_path):
    from werkstatt.builder import _validate_imports_in_patch
    patch = "import os\nfrom pathlib import Path\nimport json\n"
    fehlend = _validate_imports_in_patch(patch, tmp_path)
    assert fehlend == []


def test_validate_imports_ok_fuer_projektmodul(tmp_path):
    from werkstatt.builder import _validate_imports_in_patch
    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "__init__.py").write_text("")
    patch = "from core import something\n"
    fehlend = _validate_imports_in_patch(patch, tmp_path)
    assert fehlend == []


def test_validate_imports_findet_mehrere(tmp_path):
    from werkstatt.builder import _validate_imports_in_patch
    patch = "import foo_xyz\nfrom bar_abc import X\nimport os\n"
    fehlend = _validate_imports_in_patch(patch, tmp_path)
    assert "foo_xyz" in fehlend
    assert "bar_abc" in fehlend
    assert "os" not in fehlend
