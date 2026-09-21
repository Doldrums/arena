"""Validate explicit run templates, resource admission and secret references."""
from __future__ import annotations

from pathlib import Path
import re

from .control_types import (ControlError, MODEL, SCHEMA, SECRET_KEY, SECRET_VALUE,
                            _id, _int, _plain)


def _spec_no_secrets(value, name="spec"):
    """Refuse credential fields and inline code; environment names are references."""
    if name == "environment_names":
        if type(value) is not list or any(not isinstance(item, str) or re.fullmatch(r"[A-Z][A-Z0-9_]{0,127}", item) is None for item in value):
            raise ControlError("environment_names must contain variable names, never values")
        return
    if isinstance(value, dict):
        for key, child in value.items():
            if SECRET_KEY.search(key) or key in {"code", "program", "source_code", "env", "environment"}:
                raise ControlError("Template specs must not contain credentials, environment values or code")
            _spec_no_secrets(child, key)
    elif isinstance(value, list):
        for child in value:
            _spec_no_secrets(child, name)
    elif isinstance(value, str):
        if SECRET_VALUE.search(value) or "\n" in value or "\x00" in value:
            raise ControlError("Template spec values must not contain credentials or inline code")
        if name == "arguments" and value.startswith("-") and SECRET_KEY.search(value):
            raise ControlError("Pass model credentials through explicitly named worker environment variables")


def validate_config(config):
    required = {"schema", "state_dir", "cgroup_root", "limits", "templates"}
    if type(config) is not dict or set(config) != required or config["schema"] != SCHEMA:
        raise ControlError("Expected arena.control/1 configuration")
    for name in ("state_dir", "cgroup_root"):
        if not isinstance(config[name], str) or not Path(config[name]).is_absolute():
            raise ControlError(f"{name} must be absolute")
    limits = config["limits"]
    names = {"cpus", "memory_mb", "evaluation_slots", "max_active", "max_queued", "max_runs_per_key", "max_reserved_seconds_per_key"}
    if type(limits) is not dict or set(limits) != names:
        raise ControlError("Resource, queue and key budget limits must be explicit")
    for key, value in limits.items():
        _int(value, key)
    _int(limits["evaluation_slots"], "evaluation_slots", high=32)
    if type(config["templates"]) is not list or len(config["templates"]) > 10000:
        raise ControlError("Invalid templates")
    seen = set()
    for template in config["templates"]:
        required = {"id", "name", "framework", "profile", "model", "status", "blocked_reason", "resources", "containment", "evaluation_concurrency_verified", "spec"}
        if type(template) is not dict or set(template) != required:
            raise ControlError("A template has missing or unknown fields")
        for name in ("id", "framework", "profile"):
            _id(template[name], name)
        _plain(template["name"], "template name")
        if template["id"] in seen:
            raise ControlError("Duplicate template id")
        seen.add(template["id"])
        if not isinstance(template["model"], str) or not MODEL.fullmatch(template["model"]):
            raise ControlError("A template needs an explicit model identifier")
        if template["status"] not in {"ready", "blocked"} or template["containment"] != "cgroup-v2":
            raise ControlError("Unsupported template status or containment")
        if type(template["evaluation_concurrency_verified"]) is not bool:
            raise ControlError("Evaluation concurrency verification must be explicit")
        resources = template["resources"]
        if type(resources) is not dict or set(resources) != {"cpus", "memory_mb", "evaluation_slots", "pids"}:
            raise ControlError("Each template needs explicit CPU, RAM, evaluation slots and process limits")
        for key, value in resources.items():
            _int(value, key)
        if template["status"] == "blocked":
            _plain(template["blocked_reason"], "blocked reason", 500)
        elif template["blocked_reason"] is not None or not template["evaluation_concurrency_verified"]:
            raise ControlError("Ready templates require verified native evaluation concurrency")
        if template["status"] == "ready":
            if any(resources[key] > limits[key] for key in ("cpus", "memory_mb", "evaluation_slots")):
                raise ControlError("Ready template resources exceed global capacity")
            spec = template["spec"]
            if type(spec) is not dict or spec.get("schema") != "arena.native-run/1" or spec.get("framework") != template["framework"]:
                raise ControlError("Ready templates require a matching native run spec")
            if set(spec) - {"schema", "framework", "source_dir", "output_dir", "timeout_seconds", "request", "environment_names"}:
                raise ControlError("Unknown native run spec fields")
            _int(spec.get("timeout_seconds"), "timeout_seconds", high=604800)
            if type(spec.get("request")) is not dict or not isinstance(spec.get("source_dir"), str) or not Path(spec["source_dir"]).is_absolute():
                raise ControlError("Native source and request must be explicit")
            if spec.get("output_dir") != "{output_dir}":
                raise ControlError("The control service must allocate output_dir")
            _spec_no_secrets(spec)
        elif template["spec"] is not None:
            _spec_no_secrets(template["spec"])
    return config
