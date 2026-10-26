"""K7: _strip_xml_tags entfernt DSML/XML-Tool-Call-Tags."""
from werkstatt.planner import _strip_xml_tags


def test_einfacher_tag_entfernt() -> None:
    assert _strip_xml_tags("<read_file>foo.py</read_file>") == ""


def test_tag_mit_text() -> None:
    txt = "<shell_command>ls</shell_command>Beschreibung hier."
    assert _strip_xml_tags(txt) == "Beschreibung hier."


def test_selbstschliessend() -> None:
    assert _strip_xml_tags('<tool name="x"/>ok') == "ok"


def test_ohne_tags_unveraendert() -> None:
    assert _strip_xml_tags("Nur Prosa.") == "Nur Prosa."


def test_mehrere_tags() -> None:
    txt = "<read_file>a.py</read_file>Mitte<tool>b</tool>Ende"
    assert _strip_xml_tags(txt) == "MitteEnde"


def test_function_calls_block() -> None:
    txt = "<function_calls><invoke>x</invoke></function_calls>Rest"
    assert _strip_xml_tags(txt) == "Rest"


def test_leerer_string() -> None:
    assert _strip_xml_tags("") == ""


def test_whitespace_trim() -> None:
    assert _strip_xml_tags("   Prosa   ") == "Prosa"
