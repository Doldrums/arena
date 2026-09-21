"""CPU dependency eligibility is shared by inventory and the native bridge."""
import importlib.util
from pathlib import Path

import pytest

from arena.frameworks.sciel_catalog_profile import CPU_DEPENDENCIES, requirement_group, supports_requirements

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("cpu_preflight_inventory",
    ROOT / "scripts/deployment/sciel_catalog_preflight.py")
preflight = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preflight)


@pytest.mark.parametrize("requirement", list(CPU_DEPENDENCIES))
def test_declared_cpu_aliases_are_eligible_but_not_seed_verified(tmp_path, requirement):
    seed = tmp_path / "suite/fixture/initial_program.py"
    seed.parent.mkdir(parents=True)
    seed.write_text("raise AssertionError('inventory must never run the seed')\n")
    task = {"id": "fixture", "family": "fixture", "protocol": "recreated",
            "metric": "score", "direction": "maximize", "executable": True,
            "requirements": [requirement]}
    assert supports_requirements(task["requirements"])
    row = preflight.inventory([task], tmp_path)[0]
    assert row["status"] == "seed_check_pending"


@pytest.mark.parametrize("requirements", [
    ["py:torch"], ["py:jax"], ["py:mujoco"], ["py:brax"], ["py:pygame"],
    ["network"], ["network:https://example.com"], ["env:TOKEN"], ["file:dataset"],
    ["bin:g++"], ["vendor:algotune"], ["py:scikit-learn"], ["py:PyWavelets"],
    "py:numpy", None, [None], [["py:numpy"]],
])
def test_undeclared_or_non_cpu_requirements_are_not_silently_admitted(requirements):
    assert not supports_requirements(requirements)


def test_distribution_aliases_are_documented_explicitly():
    assert CPU_DEPENDENCIES["py:sklearn"] == "scikit-learn"
    assert CPU_DEPENDENCIES["py:bs4"] == "beautifulsoup4"
    assert CPU_DEPENDENCIES["py:pywt"] == "PyWavelets"


@pytest.mark.parametrize("selected,pending,deferred", [
    ("base", {"base", "stdlib"}, {"extended"}),
    ("extended", {"extended"}, {"base", "stdlib"}),
    ("all", {"base", "extended", "stdlib"}, set()),
])
def test_group_selection_defers_other_cpu_tasks_without_losing_inventory(tmp_path, selected, pending, deferred):
    requirements = {"base": ["py:numpy", "py:scipy"], "stdlib": [],
                    "extended": ["py:sklearn", "py:numpy"], "unsupported": ["py:torch"]}
    tasks = []
    for name, values in requirements.items():
        seed = tmp_path / "suite" / name / "initial_program.py"
        seed.parent.mkdir(parents=True)
        seed.write_text("raise AssertionError('Do not execute inventory')\n")
        tasks.append({"id": name, "family": "fixture", "protocol": "recreated", "metric": "score",
                      "direction": "maximize", "executable": True, "requirements": values})
    rows = {row["task_id"]: row for row in preflight.inventory(tasks, tmp_path, selected)}
    assert set(rows) == set(requirements)
    assert {key for key, value in rows.items() if value["status"] == "seed_check_pending"} == pending
    assert {key for key, value in rows.items() if value["status"] == "seed_check_deferred"} == deferred
    for key in deferred:
        assert f"{requirement_group(requirements[key])} CPU profile" in rows[key]["reason"]
    assert rows["unsupported"]["status"] == "environment_preparation_pending"


def test_invalid_group_cannot_silently_select_all_tasks(tmp_path):
    with pytest.raises(ValueError, match="CPU seed group"):
        preflight.inventory([], tmp_path, "other")
