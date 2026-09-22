"""Explicit scheduling allowances preserve native search and evaluator budgets."""
import json
from pathlib import Path

import pytest

from test_sciel_catalog_campaign import prepared_inputs, campaign


@pytest.mark.parametrize("seconds", [1, 7200, 14400, 32400, 57600, 86400])
def test_allowance_propagates_to_template_inventory_and_reservation(prepared_inputs, monkeypatch, seconds):
    args, _, _, _ = prepared_inputs
    validated = []
    original = campaign.validate_control
    def capture(value):
        validated.append(value)
        return original(value)
    monkeypatch.setattr(campaign, "validate_control", capture)
    result = campaign.prepare(**args, timeout_seconds=seconds)
    templates = json.loads((args["config_destination"] / "templates.json").read_text())
    inventory = json.loads((args["config_destination"] / "campaign-inventory.json").read_text())
    assert templates[0]["spec"]["timeout_seconds"] == seconds
    assert inventory["budgets"]["wall_seconds"] == result["timeout_seconds"] == seconds
    assert inventory["tasks"][0]["timeout_seconds"] == seconds
    assert inventory["reservation_seconds"] == result["reservation_seconds"] == sum(
        row["spec"]["timeout_seconds"] for row in templates)
    assert validated[-1]["limits"]["max_reserved_seconds_per_key"] == seconds
    assert "not guaranteed" in inventory["wall_time_scope"]
    request = templates[0]["spec"]["request"]
    native = json.loads(Path(request["config"]).read_bytes())
    bridge = json.loads((Path(request["tasks_root"]) / "arena/fixture/evaluation.json").read_bytes())
    assert request["budget"] == native["budget"] == 16
    assert native["max_iterations"] == 32 and native["confirm_records"] is True
    assert bridge["evaluation"]["timeout_seconds"] == 30
    assert bridge["confirmation"] == {"stochastic": True, "samples": 3}
    assert bridge["fitness"]["kind"] == "atan" and bridge["fitness"]["scale"] == 12


@pytest.mark.parametrize("seconds", [True, False, 0, -1, 86401, 3600.0, "3600", None])
def test_invalid_allowance_fails_before_creating_preparation_files(prepared_inputs, seconds):
    args, _, _, _ = prepared_inputs
    with pytest.raises(ValueError, match="integer between 1 and 86400"):
        campaign.prepare(**args, timeout_seconds=seconds)
    assert not args["config_destination"].exists() and not args["native_tasks"].exists()


def test_default_remains_one_hour_and_excluded_tasks_reserve_nothing(prepared_inputs):
    args, _, _, _ = prepared_inputs
    result = campaign.prepare(**args, exclude_tasks=["fixture"])
    inventory = json.loads((args["config_destination"] / "campaign-inventory.json").read_bytes())
    assert result["timeout_seconds"] == inventory["budgets"]["wall_seconds"] == 3600
    assert result["reservation_seconds"] == inventory["reservation_seconds"] == 0


def test_cli_passes_explicit_allowance_without_preparing_or_dispatching(monkeypatch, capsys):
    captured = []
    monkeypatch.setattr(campaign, "prepare", lambda **kwargs: captured.append(kwargs) or {"prepared": False})
    arguments = []
    for name in ("tasks-root", "config-destination", "native-tasks", "preflight-manifest", "deployment", "approval", "python"):
        arguments.extend(["--" + name, "/inert/" + name])
    assert campaign.main([*arguments, "--campaign", "inert", "--timeout-seconds", "57600"]) == 0
    assert captured[0]["timeout_seconds"] == 57600
    assert json.loads(capsys.readouterr().out) == {"prepared": False}
