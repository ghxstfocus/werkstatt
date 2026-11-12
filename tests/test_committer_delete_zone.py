"""Tests fuer die Delete-Zone-Sektion in STATUS.md."""

from __future__ import annotations

from werkstatt.committer import _delete_zone_op_append


def test_legt_sektion_an(tmp_path):
    status = tmp_path / "STATUS.md"
    status.write_text("", encoding="utf-8")

    rc = _delete_zone_op_append(status, "OP-999", "Test-Subject")

    assert rc is True
    text = status.read_text(encoding="utf-8")
    assert text.count("## Delete-Zone") == 1
    assert "| OP | Status | Notiz | Commit |" in text
    assert "|---|---|---|---|" in text
    assert "| OP-999 |" in text
    assert text.index("| OP-999 |") > text.index("|---|---|---|---|")
    assert text.endswith("\n")


def test_delete_zone_deduplicates_op(tmp_path):
    status = tmp_path / "STATUS.md"
    status.write_text("", encoding="utf-8")

    assert _delete_zone_op_append(status, "OP-999", "Test") is True
    assert _delete_zone_op_append(status, "OP-999", "Test erneut") is True

    text = status.read_text(encoding="utf-8")
    assert text.count("| OP-999 |") == 1


def test_delete_zone_retains_only_latest_twenty_entries(tmp_path):
    status = tmp_path / "STATUS.md"
    status.write_text("", encoding="utf-8")

    for number in range(1, 26):
        assert _delete_zone_op_append(
            status, f"OP-{number:03}", f"Aufgabe {number}",
        ) is True

    text = status.read_text(encoding="utf-8")
    rows = [
        line for line in text.splitlines()
        if line.startswith("| OP-")
    ]
    assert len(rows) == 20
    assert "| OP-001 |" not in text
    assert "| OP-005 |" in text
    assert "| OP-025 |" in text


def test_sektion_existiert_bereits(tmp_path):
    status = tmp_path / "STATUS.md"
    status.write_text(
        "# Status\n\nEine Zeile Inhalt.\n\n"
        "## Delete-Zone\n\n"
        "| OP | Status | Notiz | Commit |\n"
        "|---|---|---|---|\n"
        "| OP-001 | erledigt 2026-01-01 | alt | abc123 |\n\n"
        "## Andere Sektion\n\nBleibt stehen.\n",
        encoding="utf-8",
    )

    rc = _delete_zone_op_append(status, "OP-999", "Neuer Eintrag")

    assert rc is True
    text = status.read_text(encoding="utf-8")
    assert text.count("## Delete-Zone") == 1
    assert "| OP-999 |" in text
    assert "# Status" in text
    assert "Eine Zeile Inhalt." in text
    assert "| OP-001 | erledigt 2026-01-01 | alt | abc123 |" in text
    assert "## Andere Sektion" in text
    assert "Bleibt stehen." in text
    assert text.index("| OP-999 |") > text.index("| OP-001 |")
    assert text.index("| OP-999 |") < text.index("## Andere Sektion")
