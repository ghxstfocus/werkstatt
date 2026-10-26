"""K3: _reflection_loop ruft run_builder bei error_context auch wenn verify gruen."""
from pathlib import Path
from unittest.mock import patch

from werkstatt import loop as _loop


class _State:
    def __init__(self) -> None:
        self.project_dir = Path("/tmp")
        self.project_name = "k3"
        self.api_key = "x"
        self.last_verify_errors: list = []
        self.reviewer_bugs: list = []
        self.architect_prosa = ""


def test_k3_error_context_ruft_builder_obwohl_verify_gruen() -> None:
    """Reviewer hat abgelehnt (error_context), verify ist gruen -> Builder MUSS laufen."""
    st = _State()
    builder_calls = []

    def _fake_builder(state):
        builder_calls.append(1)
        return True

    # _verify_patches immer gruen, run_builder wird gezaehlt.
    with patch.object(_loop, "_verify_patches", return_value=True), \
         patch("werkstatt.builder.run_builder", side_effect=_fake_builder):
        ok = _loop._reflection_loop(st, error_context="reviewer sagt nein")

    assert len(builder_calls) >= 1, "K3: Builder muss bei error_context laufen"
    assert ok is True


def test_k3_ohne_error_context_verify_gruen_kein_builder() -> None:
    """Ohne error_context ist verify-gruen ein valider Abbruch (altes Verhalten)."""
    st = _State()
    builder_calls = []

    def _fake_builder(state):
        builder_calls.append(1)
        return True

    with patch.object(_loop, "_verify_patches", return_value=True), \
         patch("werkstatt.builder.run_builder", side_effect=_fake_builder):
        ok = _loop._reflection_loop(st, error_context=None)

    assert ok is True
    assert len(builder_calls) == 0, "ohne error_context: kein Builder bei verify gruen"


def test_k3_kein_key_returnt_false() -> None:
    st = _State()
    st.api_key = ""
    assert _loop._reflection_loop(st, error_context="x") is False
