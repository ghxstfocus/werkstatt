"""K8: BUILDER_SYSTEM enthaelt create-Format."""
from werkstatt.builder import BUILDER_SYSTEM


def test_create_format_im_prompt() -> None:
    assert '"action": "create"' in BUILDER_SYSTEM


def test_content_feld_im_prompt() -> None:
    assert '"content"' in BUILDER_SYSTEM


def test_neue_datei_hinweis() -> None:
    assert "NEUE Dateien" in BUILDER_SYSTEM or "neue Datei" in BUILDER_SYSTEM.lower()


def test_update_format_weiterhin_da() -> None:
    assert '"action": "update"' in BUILDER_SYSTEM


def test_old_string_regel_bleibt() -> None:
    assert "old_string MUSS exakt" in BUILDER_SYSTEM
