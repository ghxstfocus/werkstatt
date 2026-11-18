"""The control catalog must not expose the retired phase runner."""


def test_control_catalog_has_no_phase_runner_or_phase_fields():
    from werkstatt import control

    assert not hasattr(control, "Phase")
    assert not hasattr(control, "run_phase")
    controls = control.list_controls()
    assert controls
    assert [item.name for item in controls] == sorted(
        item.name for item in controls
    )
    assert all(not hasattr(item, "phase") for item in controls)


def test_named_control_dispatch_remains_available(tmp_path):
    from werkstatt.control import CONTROL_REGISTRY, run_control

    name = "stage_ids"
    result = run_control(name, tmp_path)

    assert name in CONTROL_REGISTRY
    assert isinstance(result, list)
