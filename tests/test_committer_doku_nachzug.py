"""OP-048/055/056/057: Doku-Selbstpflege im Committer."""
from __future__ import annotations
import sys


sys.path.insert(0, "/opt/werkstatt")

from werkstatt import committer
from werkstatt.committer import (
    _doku_nachzug_aktiv,
    _op_nnn_aus_aufgabe,
    _status_md_op_entfernen,
    _delete_zone_op_append,
    _update_kennzahlen,
    _update_changelog,
    _architecture_drift_check,
)


# ---------- _doku_nachzug_aktiv ----------

def test_doku_nachzug_aktiv_aus(monkeypatch):
    monkeypatch.delenv("WERKSTATT_DOKU_NACHZUG", raising=False)
    assert _doku_nachzug_aktiv() is False


def test_doku_nachzug_aktiv_an(monkeypatch):
    monkeypatch.setenv("WERKSTATT_DOKU_NACHZUG", "1")
    assert _doku_nachzug_aktiv() is True


# ---------- _op_nnn_aus_aufgabe ----------

def test_op_nnn_aus_aufgabe_positiv():
    assert _op_nnn_aus_aufgabe("Baue OP-048 Ebene 1") == "OP-048"


def test_op_nnn_aus_aufgabe_subletter():
    assert _op_nnn_aus_aufgabe("OP-002b2 mit Duplikatschutz") == "OP-002b2"


def test_op_nnn_aus_aufgabe_negativ():
    assert _op_nnn_aus_aufgabe("keine Referenz hier") is None


def test_op_nnn_aus_aufgabe_leer():
    assert _op_nnn_aus_aufgabe("") is None


# ---------- _status_md_op_entfernen ----------

STATUS_MD_BSP = """# Status

## Offene Punkte

### OP-048: Doku-Nachzug
- **Status:** open
- **Tests:** keine

### OP-055: Kennzahlen
- **Status:** open

## Delete-Zone

| Pfad | Warum | Ersetzt |
|---|---|---|
| OP-001 | alt | - |
"""


def test_status_md_op_entfernen_erfolg(tmp_path):
    f = tmp_path / "STATUS.md"
    f.write_text(STATUS_MD_BSP, encoding="utf-8")
    ok, msg = _status_md_op_entfernen(f, "OP-048")
    assert ok, msg
    txt = f.read_text(encoding="utf-8")
    assert "OP-048" not in txt
    assert "OP-055" in txt  # naechste OP bleibt


def test_status_md_op_entfernen_nicht_gefunden(tmp_path):
    f = tmp_path / "STATUS.md"
    f.write_text(STATUS_MD_BSP, encoding="utf-8")
    ok, msg = _status_md_op_entfernen(f, "OP-999")
    assert not ok
    assert "nicht in STATUS.md" in msg


def test_status_md_op_entfernen_datei_fehlt(tmp_path):
    f = tmp_path / "missing.md"
    ok, msg = _status_md_op_entfernen(f, "OP-048")
    assert not ok
    assert "nicht gefunden" in msg


# ---------- _delete_zone_op_append ----------

def test_delete_zone_append_erfolg(tmp_path):
    f = tmp_path / "STATUS.md"
    f.write_text(STATUS_MD_BSP, encoding="utf-8")
    ok = _delete_zone_op_append(f, "OP-048", "Doku-Nachzug")
    assert ok
    txt = f.read_text(encoding="utf-8")
    assert "| OP-048 | erledigt" in txt


def test_delete_zone_keine_sektion(tmp_path):
    """OP-069: Sektion wird angelegt, OP eingetragen, True."""
    f = tmp_path / "STATUS.md"
    f.write_text("# Status\n\nKeine Delete-Zone.\n", encoding="utf-8")
    assert _delete_zone_op_append(f, "OP-048", "X") is True
    txt = f.read_text(encoding="utf-8")
    assert "## Delete-Zone" in txt
    assert "OP-048" in txt
    # Andere Zeilen unberuehrt
    assert "# Status" in txt
    assert "Keine Delete-Zone." in txt


def test_delete_zone_datei_fehlt(tmp_path):
    assert _delete_zone_op_append(tmp_path / "missing.md", "OP-1", "X") is False


# ---------- _update_kennzahlen ----------

def test_update_kennzahlen_erfolg(tmp_path, monkeypatch):
    f = tmp_path / "STATUS.md"
    f.write_text("## Kennzahlen\n\n- HEAD: old1234\n- Tests: 10\n", encoding="utf-8")
    # Fake git-Repo: wir mocken subprocess.run im committer-Modul
    def fake_run(*args, **kwargs):
        class R:
            stdout = "new5678\n"
            returncode = 0
        return R()
    monkeypatch.setattr(committer.subprocess, "run", fake_run)
    ok = _update_kennzahlen(f, tmp_path)
    assert ok
    txt = f.read_text(encoding="utf-8")
    assert "HEAD: new5678" in txt
    assert "old1234" not in txt


def test_update_kennzahlen_keine_sektion(tmp_path):
    f = tmp_path / "STATUS.md"
    f.write_text("# Status\n\nKeine Kennzahlen.\n", encoding="utf-8")
    assert _update_kennzahlen(f, tmp_path) is False


# ---------- _update_changelog ----------

def test_update_changelog_erfolg(tmp_path):
    p = tmp_path / "CHANGELOG.md"
    p.write_text("# Changelog\n\n## [Unreleased]\n\n- alt\n", encoding="utf-8")
    assert _update_changelog(tmp_path, "feat: neues Feature") is True
    txt = p.read_text(encoding="utf-8")
    assert "feat: neues Feature" in txt
    assert "## [Unreleased]" in txt


def test_update_changelog_datei_fehlt(tmp_path):
    assert _update_changelog(tmp_path, "x") is False


def test_update_changelog_keine_unreleased(tmp_path):
    p = tmp_path / "CHANGELOG.md"
    p.write_text("# Changelog\n\n## [1.0.0]\n\n- x\n", encoding="utf-8")
    assert _update_changelog(tmp_path, "neu") is False


# ---------- _architecture_drift_check ----------

def test_drift_ohne_aenderung(tmp_path, monkeypatch):
    def fake_run(*args, **kwargs):
        class R:
            stdout = ""
            returncode = 0
        return R()
    monkeypatch.setattr(committer.subprocess, "run", fake_run)
    r = _architecture_drift_check(tmp_path)
    assert r["drift"] is False


def test_drift_mit_neuer_py(tmp_path, monkeypatch):
    def fake_run(*args, **kwargs):
        class R:
            stdout = "A\twerkstatt/neu.py\n"
            returncode = 0
        return R()
    monkeypatch.setattr(committer.subprocess, "run", fake_run)
    r = _architecture_drift_check(tmp_path)
    assert r["drift"] is True
    assert ("A", "werkstatt/neu.py") in r["py"]


def test_drift_mit_py_und_doc(tmp_path, monkeypatch):
    def fake_run(*args, **kwargs):
        class R:
            stdout = "A\twerkstatt/neu.py\nM\tdocs/ARCHITECTURE.md\n"
            returncode = 0
        return R()
    monkeypatch.setattr(committer.subprocess, "run", fake_run)
    r = _architecture_drift_check(tmp_path)
    assert r["drift"] is False
