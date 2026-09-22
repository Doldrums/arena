"""Real CLI interoperability with an inert proxy/daemon; never needs a GPU."""
import importlib.util
from pathlib import Path
import shutil

import pytest

from arena import evaluator_policy as policy
from arena.frameworks import evaluation_gpu_client as client
from evaluator_gpu_helpers import NAME, RUN, prepared, setup

_PATH = Path(__file__).parent / "fixtures/evaluator_gpu_cli_probe.py"
_SPEC = importlib.util.spec_from_file_location("gpu_cli_probe", _PATH)
probe = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(probe)


def test_gpu_client_body_matches_the_root_policy_without_passing_device_capabilities(prepared):
    config, _, candidate, output = prepared
    body = client.create_body(probe.configuration(), config.tasks_root, candidate, output,
        {"run_id": RUN, "cgroup_parent": "/arena-workers/arena-control-" + RUN})
    rebuilt, cpath, opath = policy.canonical_config(body, NAME, RUN, config)
    assert cpath == candidate and opath == output
    assert rebuilt["HostConfig"]["Runtime"] == "runc" and len(rebuilt["HostConfig"]["Devices"]) == 3
    assert "Devices" not in body["HostConfig"] and len(body["HostConfig"]["Mounts"]) == 3


@pytest.mark.skipif(shutil.which("docker") is None, reason="Installed Docker CLI needed; no real daemon used")
def test_real_cli_starts_and_attaches_once_after_structured_create():
    result = probe.main()
    assert result["create_requests"] == result["container_starts"] == 1
    assert result["cli_returncode"] == result["model_calls"] == result["real_daemon_calls"] == 0
    assert result["candidate_executions"] == 0 and result["stdout"] == "OK\n"
