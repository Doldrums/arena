"""Explicit SCiEL v0.2.0 research configuration; preparation never grants runtime.

Native cells/tools need a separately reviewed executor capability and real pilot
artifacts. A flag, generated config or synthetic receipt cannot establish that.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import re

PROFILE = "arena.sciel-research-foreground/1"
ENGINE_COMMIT = "a6c0d215b61ee52dae608a6390c9f2c6d2f2554d"
RUNTIME_SOURCES = {
    "executor_sha256": "836a0455d8cdbbe9c8175a1fcc3da48d1b0aef3156c425ef2e8b9b8b85b66148",
    "runner_sha256": "a19034f5a17bb1a9b527fc8377058dfdc9edf7631c2e9f0e5055f796fb6d3f8e",
    "loader_sha256": "141e4224f72ff74bcd10916159d34ac55a4eb5e8ca04dc914fec1ed5d14f90f7",
}
LIMITS = {"wall_seconds": 30.0, "cpu_seconds": 20.0, "memory_bytes": 536870912,
          "pids": 64, "max_output_bytes": 65536, "max_stderr_bytes": 8192}
PARALLEL = {"enabled": True, "workers": 1, "host_evaluator_slots": 1, "host_research_slots": None}
CHECKS = ("native_identity_bound", "model_authored_tool", "committed_cell", "registered_tool",
          "tool_invoked", "tool_result_valid", "daemon_lifecycle_verified", "resource_receipt_verified",
          "observations_delivered", "continuation_executed", "canonical_result_verified", "cleanup_verified")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()


def _same(actual, expected):
    return canonical(actual) == canonical(expected)


def _image(value):
    if type(value) is not str or re.fullmatch(r"sha256:[0-9a-f]{64}", value) is None:
        raise ValueError("Research tools require an explicit immutable Docker image ID, not a tag or RepoDigest")
    return value


def _model(value):
    if (type(value) is not str or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:/-]{0,159}", value) is None
            or "astra" in value.lower()):
        raise ValueError("Select the explicit non-Astra model separately verified on the provider route")
    return value


def tools_config(image_id, model):
    """All fields are native a6c0d215 research_tools.config fields, explicitly set."""
    return {"enabled": True, "interval": 4, "proactive_every_attempts": 8, "attempt_stall_threshold": 8,
            "trigger_sources": ["population_stall", "search_attempt_stall", "controller_plateau"],
            "allow_shadow_triggers": False, "max_active_cells": 4, "max_requests": 2,
            "max_scientific_steps": 3, "yield_after_success": True, "independent_research": True,
            "research_jobs_per_wave": 1, "experimental_protocol": True, "shared_observations": True,
            "model": _model(model), "temperature": 0.4, "share_between_islands": True,
            "max_visible_tools": 8, "max_source_chars": 32000, "max_context_chars": 10000,
            "max_prompt_chars": 64000, "max_response_chars": 80000, "image_id": _image(image_id),
            # Native detached worker omits TMPDIR. Foreground staging is the only
            # reviewed integration target; background jobs need separate proof.
            "jobs": {"enabled": False, "max_active": 1, "max_pending": 16,
                     "max_cpu_seconds": 3600.0, "max_wall_seconds": 7200.0},
            "limits": deepcopy(LIMITS)}


def research_config(model):
    # Finite version of the pinned native structured G/C/R example. This aux
    # budget does not cap research_tools planner requests or tool executions.
    # 72-run audit observed <=33 outcomes: 33 conclusions + at most33 format
    # repairs + floor(33/4)=8 reflections =74 calls;80 is finite headroom, not
    # a guarantee for every future retry pattern. Measured calls remain logged.
    return {"enabled": True, "reflection_interval": 4, "max_aux_calls": 80,
            "max_lessons": 50, "max_experiments": 200, "max_fragments": 20, "retrieve_k": 3,
            "model": _model(model), "inject_lessons": True, "compact_lesson_memory": True,
            "conclusion_source_refs": True, "conclusion_repair_attempts": 1,
            "conclusion_max_tokens": 4096, "structured_auxiliary": True, "incomplete_auxiliary": "skip"}


def _canonical_budget(config):
    for name, expected in (("budget", 16), ("max_iterations", 32), ("confirm_records", True)):
        if name not in config or not _same(config[name], expected):
            raise ValueError("Research profile preserves the reviewed canonical budget16/max_iterations32/confirmation")


def apply_research_profile(native_config, *, image_id, model):
    """Return new configuration bytes; never mutate the caller or touch runtime."""
    if type(native_config) is not dict:
        raise ValueError("Expected an existing native configuration")
    _canonical_budget(native_config)
    if "research_tools" in native_config:
        raise ValueError("Use a fresh explicit profile; do not silently overwrite or resume research identity")
    image_id, model = _image(image_id), _model(model)
    config = deepcopy(native_config)
    llm, parallel, novelty = (config.get(name) for name in ("llm", "parallel_search", "candidate_novelty"))
    if any(type(value) is not dict for value in (llm, parallel, novelty)):
        raise ValueError("Existing native provider/parallel/novelty configuration is required")
    if llm.get("models") != [model] or not _same(llm.get("weights"), [1.0]) or llm.get("mock", False) is not False:
        raise ValueError("Preserve the explicitly selected single real model route")
    for name in ("kb_free", "c2_event_bets", "bet_enabled"):
        if config.get(name) not in (None, False):
            raise ValueError("Structured research replaces incompatible legacy research routes")
    if config.get("warm_start") is not None or config.get("resume") not in (None, False):
        raise ValueError("A research profile requires a fresh run, not a tool-disabled checkpoint")
    config["research_tools"] = tools_config(image_id, model)
    config["research"] = research_config(model)
    parallel.update(PARALLEL)
    novelty["enabled"] = True
    llm["max_retries"] = 1
    # A preparation statement, not executor/model availability or science success.
    profile_identity(config)
    return config


def profile_identity(config):
    """Strict full-native-config identity, including route, task and canonical budget."""
    if type(config) is not dict:
        raise ValueError("Expected native configuration")
    _canonical_budget(config)
    tools = config.get("research_tools")
    if type(tools) is not dict:
        raise ValueError("Research tools are absent")
    image, model = _image(tools.get("image_id")), _model(tools.get("model"))
    if not _same(tools, tools_config(image, model)) or not _same(config.get("research"), research_config(model)):
        raise ValueError("Research settings differ from the exact reviewed profile")
    parallel, llm, novelty = (config.get(k) for k in ("parallel_search", "llm", "candidate_novelty"))
    if (any(type(v) is not dict for v in (parallel, llm, novelty))
            or any(not _same(parallel.get(k), v) for k, v in PARALLEL.items())
            or novelty.get("enabled") is not True or not _same(llm.get("max_retries"), 1)
            or not _same(llm.get("models"), [model]) or not _same(llm.get("weights"), [1.0])
            or llm.get("mock", False) is not False):
        raise ValueError("Native scheduling/provider prerequisites differ")
    if (any(config.get(k) not in (None, False) for k in ("kb_free", "c2_event_bets", "bet_enabled", "resume"))
            or config.get("warm_start") is not None):
        raise ValueError("Research profile must be a fresh compatible run")
    task = config.get("task")
    if type(task) is not str or re.fullmatch(r"arena/[a-z0-9][a-z0-9-]{0,180}", task) is None:
        raise ValueError("Explicit Arena task identity required")
    identity = {"schema": PROFILE, "engine_commit": ENGINE_COMMIT, "task": task, "model": model,
                "tool_image_id": image, "runtime_sources": deepcopy(RUNTIME_SOURCES),
                "native_config_sha256": hashlib.sha256(canonical(config)).hexdigest()}
    return {**identity, "profile_sha256": hashlib.sha256(canonical(identity)).hexdigest(),
            "readiness": "pending_runtime_conformance"}


def require_conformance(config, evidence_bytes, *, expected_sha256, verifier=None):
    """Require a separate actual-artifact verifier; no built-in flag-only admission.

    The operator pins the evidence manifest's exact bytes. A trusted verifier
    must read/authenticate its referenced native/provider/daemon/canonical files
    and return the projection below. This module does not implement or replace
    that boundary and intentionally refuses admission without it.
    """
    identity = profile_identity(config)
    if not callable(verifier):
        raise ValueError("Actual research artifact verifier required; configuration alone cannot admit a run")
    if (type(evidence_bytes) is not bytes or not 0 < len(evidence_bytes) <= 1024 * 1024
            or type(expected_sha256) is not str or re.fullmatch(r"[0-9a-f]{64}", expected_sha256) is None
            or hashlib.sha256(evidence_bytes).hexdigest() != expected_sha256):
        raise ValueError("Expected exact bounded, operator-pinned evidence bytes")
    def unique(pairs):
        obj = {}
        for key, value in pairs:
            if key in obj:
                raise ValueError("Duplicate evidence key")
            obj[key] = value
        return obj
    evidence = json.loads(evidence_bytes, object_pairs_hook=unique,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Nonfinite evidence")))
    if (type(evidence) is not dict or evidence.get("schema") != "arena.sciel-research-conformance/1"
            or evidence.get("profile_sha256") != identity["profile_sha256"]):
        raise ValueError("Conformance manifest does not bind this exact native profile")
    # Never accept manifest-provided booleans as observed runtime proof.
    observed = verifier(deepcopy(evidence), deepcopy(identity))
    required = {"profile_sha256", "engine_commit", "model", "tool_image_id", "task", "run_id", "checks"}
    if (type(observed) is not dict or set(observed) != required
            or any(observed[k] != identity[k] for k in required - {"run_id", "checks"})
            or type(observed["run_id"]) is not str or re.fullmatch(r"[a-f0-9]{32}", observed["run_id"]) is None
            or type(observed["checks"]) is not dict or set(observed["checks"]) != set(CHECKS)
            or any(observed["checks"][key] is not True for key in CHECKS)):
        raise ValueError("Actual artifact verification did not establish the required native research loop")
    return {"profile_sha256": identity["profile_sha256"], "evidence_sha256": expected_sha256,
            "run_id": observed["run_id"], "status": "runtime_conformance_verified",
            "science_success": False, "production_admission": False}
