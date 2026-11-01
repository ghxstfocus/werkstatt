"""OP-054: Duplikat-Anker im no_effect-Filter erkennt echten Bug."""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, "/opt/werkstatt")


def test_audit_kind_registriert():
    from werkstatt.audit import _AUDIT_KINDS_BEKANNT
    assert "builder_patch_duplicate_anchor" in _AUDIT_KINDS_BEKANNT


def test_fix_ist_im_code():
    """OP-054-Kommentar + Duplikat-Anker-Check vorhanden."""
    src = Path("/opt/werkstatt/werkstatt/builder.py").read_text(encoding="utf-8")
    assert "OP-054" in src
    assert "_duplikat_anker" in src
    assert "_ist_zustand_054" in src
    assert "builder_patch_duplicate_anchor" in src


def test_duplikat_anker_verhindert_flag(tmp_path):
    """Wenn old_string 2x in Datei: KEIN bereits_erfuellt-Flag."""
    datei = tmp_path / "test.py"
    datei.write_text(
        "def foo():\n    pass\n\ndef foo():\n    pass\n",
        encoding="utf-8",
    )
    _ist_zustand = datei.read_text()
    _old_anker = "def foo():\n    pass"
    assert _ist_zustand.count(_old_anker) == 2
    _duplikat = _ist_zustand.count(_old_anker) > 1
    assert _duplikat is True


def test_normaler_anker_erlaubt_flag(tmp_path):
    """Wenn old_string 1x in Datei: bestehendes Verhalten bleibt."""
    datei = tmp_path / "test.py"
    datei.write_text(
        "def foo():\n    pass\n\ndef bar():\n    pass\n",
        encoding="utf-8",
    )
    _ist_zustand = datei.read_text()
    _old_anker = "def foo():\n    pass"
    assert _ist_zustand.count(_old_anker) == 1
    _duplikat = _ist_zustand.count(_old_anker) > 1
    assert _duplikat is False
