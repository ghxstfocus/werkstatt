"""Tests fuer M-377: Live-Spinner idempotent."""
from werkstatt import loop_renderer as r


def test_spinner_start_idempotent():
    """M-377: spinner_start darf nicht crashen, wenn schon aktiv."""
    # In CI/Test ist IS_LIVE False — wir testen den Codepfad nur
    # ueber direkten Aufruf (kein rich.Live).
    r.spinner_start("test", "detail1")
    r.spinner_start("test", "detail2")  # darf nicht crashen
    r.spinner_stop()
    r.spinner_stop()  # doppelt stoppen ist ok


def test_spinner_stop_ohne_start():
    """M-377: spinner_stop ohne vorherigen start crasht nicht."""
    r.spinner_stop()
    r.spinner_stop()
