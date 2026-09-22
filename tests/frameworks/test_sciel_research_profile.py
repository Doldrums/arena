"""Research configuration and admission are separate; no LLM, Docker or task calls."""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from arena.registry import get_catalog
from arena import sciel_research_profile as profile

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("research_profile_campaign", ROOT / "scripts/deployment/prepare_sciel_catalog_campaign.py")
campaign = importlib.util.module_from_spec(spec)
spec.loader.exec_module(campaign)
IMAGE = "sha256:" + "a" * 64
MODEL = "gpt-5.5"
TASKS = ("science-materials-cantera-mechanism-reduction", "science-biology-beeline-regulatory-network")


def native(task=TASKS[0]):
    actual = next(t for t in get_catalog()["tasks"] if t["id"] == task)
    return campaign.baseline_configuration(actual, MODEL, "research-profile-test", "fixture")


def prepared():
    return profile.apply_research_profile(native(), image_id=IMAGE, model=MODEL)


@pytest.mark.parametrize("task", TASKS)
def test_actual_task_native_configuration_gets_explicit_research_identity(task):
    original = native(task)
    before = deepcopy(original)
    config = profile.apply_research_profile(original, image_id=IMAGE, model=MODEL)
    assert original == before and "research_tools" not in original
    assert config["task"] == original["task"]
    assert config["budget"] == 16 and config["max_iterations"] == 32 and config["confirm_records"] is True
    assert config["llm"] == original["llm"]
    assert config["parallel_search"]["host_evaluator_slots"] == 1
    tools = config["research_tools"]
    assert tools["enabled"] and tools["independent_research"] and tools["experimental_protocol"]
    assert tools["proactive_every_attempts"] == 8 and tools["max_scientific_steps"] == 3
    assert tools["jobs"]["enabled"] is False
    assert tools["limits"] == profile.LIMITS
    assert config["research"]["max_aux_calls"] == 80 and config["research"]["compact_lesson_memory"]
    identity = profile.profile_identity(config)
    assert identity["readiness"] == "pending_runtime_conformance"
    assert identity["engine_commit"] == campaign.COMMIT
    assert identity["tool_image_id"] == IMAGE
    assert identity["native_config_sha256"] == hashlib.sha256(profile.canonical(config)).hexdigest()


@pytest.mark.parametrize("image", [None, "latest", "sha256:" + "A" * 64, "repo@sha256:" + "a" * 64])
def test_only_immutable_local_image_ids_are_native_supported(image):
    with pytest.raises(ValueError, match="image ID"):
        profile.apply_research_profile(native(), image_id=image, model=MODEL)


@pytest.mark.parametrize("change", ["existing_tools", "resume", "budget", "mock", "other_model", "legacy"])
def test_no_silent_resume_route_budget_or_profile_replacement(change):
    config = native()
    if change == "existing_tools": config["research_tools"] = {"enabled": False}
    elif change == "resume": config["resume"] = True
    elif change == "budget": config["budget"] = 17
    elif change == "mock": config["llm"]["mock"] = True
    elif change == "other_model": config["llm"]["models"] = ["another-model"]
    else: config["kb_free"] = True
    before = deepcopy(config)
    with pytest.raises(ValueError): profile.apply_research_profile(config, image_id=IMAGE, model=MODEL)
    assert config == before


@pytest.mark.parametrize("field,value", [("enabled", False), ("image_id", "sha256:" + "b" * 64),
    ("max_requests", 99), ("max_active_cells", True), ("proactive_every_attempts", None),
    ("independent_research", False), ("unexpected", True)])
def test_exact_profile_rejects_mutated_or_unknown_tool_fields(field, value):
    config = prepared(); config["research_tools"][field] = value
    if field == "image_id":
        assert profile.profile_identity(config)["profile_sha256"] != profile.profile_identity(prepared())["profile_sha256"]
    else:
        with pytest.raises(ValueError): profile.profile_identity(config)


def test_background_and_numeric_boolean_cannot_bypass_identity():
    for key, value in [("jobs", {"enabled": True}), ("limits", dict(profile.LIMITS, pids=True))]:
        config = prepared(); config["research_tools"][key] = value
        with pytest.raises(ValueError): profile.profile_identity(config)
    config = prepared(); config["llm"]["max_retries"] = True
    with pytest.raises(ValueError): profile.profile_identity(config)


def test_full_native_task_and_provider_route_are_hashed():
    config = prepared(); before = profile.profile_identity(config)
    config["llm"]["api_base"] = "http://another.invalid/v1"
    assert profile.profile_identity(config)["profile_sha256"] != before["profile_sha256"]
    config["task"] = "arena/" + TASKS[1]
    assert profile.profile_identity(config)["profile_sha256"] != before["profile_sha256"]


def conformance(config):
    identity = profile.profile_identity(config)
    # Inert fixture; only the independently supplied verifier can establish the checks.
    evidence = {"schema": "arena.sciel-research-conformance/1", "profile_sha256": identity["profile_sha256"],
                "artifacts": [{"path": "inert-no-file", "sha256": "c" * 64}]}
    raw = profile.canonical(evidence)
    observed = {key: identity[key] for key in ("profile_sha256", "engine_commit", "model", "tool_image_id", "task")}
    observed.update(run_id="f" * 32, checks={key: True for key in profile.CHECKS})
    return raw, hashlib.sha256(raw).hexdigest(), observed


def test_flags_and_forged_positive_manifest_cannot_establish_conformance():
    config = prepared(); raw, digest, _ = conformance(config)
    with pytest.raises(ValueError, match="artifact verifier"):
        profile.require_conformance(config, raw, expected_sha256=digest)
    with pytest.raises(ValueError, match="did not establish"):
        profile.require_conformance(config, raw, expected_sha256=digest, verifier=lambda *_: {})


def test_operator_pinned_proof_is_checked_before_artifact_verifier():
    config = prepared(); raw, digest, observed = conformance(config)
    verifier = Mock(return_value=observed)
    with pytest.raises(ValueError, match="operator-pinned"):
        profile.require_conformance(config, raw + b" ", expected_sha256=digest, verifier=verifier)
    verifier.assert_not_called()


def test_positive_actual_verifier_projection_does_not_grant_production_or_science():
    config = prepared(); raw, digest, observed = conformance(config)
    verifier = Mock(return_value=observed)
    result = profile.require_conformance(config, raw, expected_sha256=digest, verifier=verifier)
    assert result["status"] == "runtime_conformance_verified"
    assert result["science_success"] is False and result["production_admission"] is False
    assert verifier.call_count == 1


@pytest.mark.parametrize("missing", profile.CHECKS)
def test_each_observed_stage_is_required_independently(missing):
    config = prepared(); raw, digest, observed = conformance(config)
    observed["checks"][missing] = False
    with pytest.raises(ValueError, match="did not establish"):
        profile.require_conformance(config, raw, expected_sha256=digest, verifier=lambda *_: observed)


@pytest.mark.parametrize("field,value", [("model", "other-model"), ("tool_image_id", "sha256:" + "b" * 64),
    ("engine_commit", "e" * 40), ("run_id", "not-a-run"), ("task", "arena/other")])
def test_valid_looking_artifacts_from_other_identity_cannot_qualify(field, value):
    config = prepared(); raw, digest, observed = conformance(config)
    observed[field] = value
    with pytest.raises(ValueError):
        profile.require_conformance(config, raw, expected_sha256=digest, verifier=lambda *_: observed)


def test_duplicate_json_or_wrong_profile_is_rejected_before_verifier():
    config = prepared(); raw, digest, observed = conformance(config)
    for bad in [b'{"schema":"x","schema":"y"}', raw.replace(profile.profile_identity(config)["profile_sha256"].encode(), b"0" * 64)]:
        verifier = Mock(return_value=observed)
        with pytest.raises(ValueError):
            profile.require_conformance(config, bad, expected_sha256=hashlib.sha256(bad).hexdigest(), verifier=verifier)
        verifier.assert_not_called()
