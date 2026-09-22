"""Exact science5 CPU image and data profile; seed readiness is separate.

The immutable image passed dependency and data checks, including a non-root
read-only smoke. Fresh canonical seeds still establish task runtime readiness.
The existing eight-task science environment is unchanged.
"""
from __future__ import annotations

import json

from arena.evaluation_resources import budget
from arena.task_library import read_task_file

PROFILE = "sciel-catalog-prepared-science5/1"
GROUP = "science5"
RESOURCE_PROFILE = "cpu-4g-p256-v1"
IMAGE = ("127.0.0.1:5000/empira/canonical-science5-cpu@sha256:"
         "d00f89512cadba58259d32532a6f66723d72a972843cb8ef84af47ab2945e6bf")
IMAGE_ID = "sha256:81dfea2c03da99ad501c44411165299aea97d644f465cc82161d61f4a5c0c606"
BUILD_RECEIPT_SHA256 = "91742d0ea06913de56893ae509eec3c7d2c7e639bdc39c3c0810fda5409be0a8"
DEPENDENCY_LOCK_SHA256 = "68bce8acef7f9cea18df7afbd8eeefae99733f7fc4cacc08654ec31c49adfc7b"
DATA_LOCK_SHA256 = "8a5a1e77b1a61ab625788b8066a0bfa6969ae065133907e28443ca43c4dd0be6"
RUNTIME_ADDITIONS = {"viennarna": "2.6.4", "rdkit": "2026.3.6"}
PRESERVED_RUNTIME = {"numpy": "2.2.6", "scipy": "1.15.3", "pillow": "12.3.0"}
# Raw task.json requirements are pinned separately from the sorted catalog.
TASKS = {
    "science-biology-eterna-rna-design": {
        "requirements": [
            "py:numpy",
            "py:scipy",
            "file:../../.cache/science-biology/B02.json",
            "file:../../.cache/science-biology/B02.manifest.json",
            "py:RNA"
        ],
        "direction": "maximize",
        "family": "science_biology_b02",
        "timeout": 600,
        "files": {
            "task.json": "9f375069fe3cc8dd2e3f46ecbd3d7f35441aa7f47a32af07caf4b32b43340b58",
            "problem.json": "48643a74cca9d6d6fc6e0a1c24b232814a4653d1f8742bf2f85832bdeefa61ef",
            "initial_program.py": "49ba56bc4dabff020809c8f3c9f36cf6e5894ae784964c5da17ebc3364ee2604",
            "evaluator.py": "1f94e8b7ede8b19b1208028d14face6013b6d24902e82bf456f103a66f40e00e"
        }
    },
    "science-biology-proteingym-fitness": {
        "requirements": [
            "py:numpy",
            "py:scipy",
            "file:../../.cache/science-biology/B01.json",
            "file:../../.cache/science-biology/B01.manifest.json"
        ],
        "direction": "maximize",
        "family": "science_biology_b01",
        "timeout": 600,
        "files": {
            "task.json": "1482d20d2e88334bdaaac08305e0d95ecd280b66aef9d7e3ee7d2b73db11e95d",
            "problem.json": "2e1c6c61a7550787b1fed20d3ca91ea4d2e371bd02bf1c784c397d6720534914",
            "initial_program.py": "d50b03467f4b452ce25b08b65b6878005b9710ee53ca3df85e3d246e7bbe25c4",
            "evaluator.py": "d5c41724c2f0b45222f4c49dbc7b59badb056519581b165ddc93c40efda65599"
        }
    },
    "science-cosmology-pantheon-plus-expansion-fit": {
        "requirements": [
            "py:numpy",
            "py:scipy",
            "file:data/pantheon-plus/Pantheon+SH0ES.dat",
            "file:data/pantheon-plus/Pantheon+SH0ES_STAT+SYS.npy"
        ],
        "direction": "minimize",
        "family": "science_pantheon",
        "timeout": 600,
        "files": {
            "task.json": "2c824db494efafcbb051c835178f39ceae47732883c89dbb0044581bea6ddb0e",
            "problem.json": "53a6a85d41156e8a9a91d74bb16479c9b8c1c074892e6f89499b901cefece8d6",
            "initial_program.py": "cd45eeb821de1ed3f16461fed4d01ff970fd511204f65d17e7dccec814a4283b",
            "evaluator.py": "4bab191e37348e7667d7b9f5c87d96ea66b7363fc7c4ec049795a20655ab4cea"
        }
    },
    "science-earth-oceanbench-satellite-ssh": {
        "requirements": [
            "py:numpy",
            "py:scipy",
            "file:../../.cache/science-earth-data/E06.json",
            "file:../../.cache/science-earth-data/E06.manifest.json"
        ],
        "direction": "minimize",
        "family": "science_earth_e06",
        "timeout": 600,
        "files": {
            "task.json": "d4c2fa31e76683cc9088c7098cfccbce7fe46c9efeeba350c172423d67a3507f",
            "problem.json": "5b37c25fdef5694fa69297da4c92e0548b978a5ec305d04fc6de77ab8c89cda1",
            "initial_program.py": "942a724509d98fdc09eb9d539c9f5fb53210a71c00cafe36cae4888744f1edc3",
            "evaluator.py": "8e0f2cd8d1407161dcef9b390029c562913371be209be8d5692c07bf974d9801"
        }
    },
    "science-materials-geom-conformer-search": {
        "requirements": [
            "py:numpy",
            "py:rdkit",
            "file:data/materials-expansion/C02/dataset.json"
        ],
        "direction": "maximize",
        "family": "science_materials_geom_conformer_search",
        "timeout": 180,
        "files": {
            "task.json": "5bcfd4df78e96ed59a53f361f60db724bed43d8c0f724f9b61745d2b7926316d",
            "problem.json": "3a193d7a98887e73135e0ad96ce5c55ba70337bf6641569af9665025516bce98",
            "initial_program.py": "761a5a00ac3ae2aa90c33ebbb9ee7161219855d1895a3dfb8cddd5d4c6c29111",
            "evaluator.py": "6028502f610fd659bfdb2753b70db8ee0711c4da6ef28729c4c55383704ec6e7"
        }
    }
}


def supports_science5_task(task_id, requirements):
    """Accept only exact membership, never duplicate aliases or inferred paths."""
    return (type(task_id) is str and task_id in TASKS and type(requirements) is list
            and all(type(item) is str for item in requirements)
            and len(requirements) == len(set(requirements))
            and set(requirements) == set(TASKS[task_id]["requirements"]))


def science5_environment(image):
    """Bind the reviewed image closure without asserting a successful seed."""
    if IMAGE is None or IMAGE_ID is None:
        raise ValueError("Science5 immutable image review is pending")
    if type(image) is not str or image not in (IMAGE, IMAGE_ID):
        raise ValueError("Science5 requires its exact reviewed immutable image")
    return {"profile": PROFILE, "group": GROUP, "image_reference": IMAGE,
            "image_id": IMAGE_ID, "data_lock_sha256": DATA_LOCK_SHA256,
            "build_receipt_sha256": BUILD_RECEIPT_SHA256,
            "dependency_lock_sha256": DEPENDENCY_LOCK_SHA256,
            "runtime_additions": dict(RUNTIME_ADDITIONS),
            "preserved_runtime": dict(PRESERVED_RUNTIME),
            "resource_profile": RESOURCE_PROFILE, "resources": budget(RESOURCE_PROFILE)}


def validate_science5_task(task, evaluation):
    if not supports_science5_task(task.get("id"), task.get("requirements")):
        raise ValueError("Task and requirements are outside the exact science5 cohort")
    expected = TASKS[task["id"]]
    if (task.get("protocol") != "recreated" or task.get("metric") != "score"
            or task.get("direction") != expected["direction"]
            or task.get("family") != expected["family"]
            or task.get("contract_source", {}).get("sha256") != expected["files"]["problem.json"]):
        raise ValueError("Science5 scientific task contract changed")
    execution = evaluation.get("execution", {})
    if (execution.get("kind") != "docker" or execution.get("python") != "python"
            or execution.get("require_control_cgroup") is not True
            or execution.get("resource_profile") != RESOURCE_PROFILE
            or type(evaluation.get("timeout_seconds")) is not int
            or evaluation["timeout_seconds"] != expected["timeout"]):
        raise ValueError("Science5 requires its explicit canonical resource and timeout contract")
    return science5_environment(execution.get("image"))


def validate_science5_metadata(task, metadata, problem, root, files):
    """Check actual immutable bytes, including unchanged scientific cuts and seed."""
    if not supports_science5_task(task.get("id"), task.get("requirements")):
        raise ValueError("Task is outside the exact science5 cohort")
    expected = TASKS[task["id"]]
    for name, digest in expected["files"].items():
        relative = f"suite/{task['id']}/{name}"
        if files.get(relative) != digest:
            raise ValueError("Science5 task, seed or evaluator bytes changed")
        raw = read_task_file(root, relative, digest)
        supplied = {"task.json": metadata, "problem.json": problem}.get(name)
        if supplied is not None and json.loads(raw) != supplied:
            raise ValueError("Science5 supplied metadata differs from pinned bytes")
    suite = metadata["execution"]["suite"]
    if (suite["requires"] != expected["requirements"]
            or suite["env"] != {} or suite["timeout"] != expected["timeout"]
            or problem["direction"] != expected["direction"]
            or problem["protocol"] != "recreated"):
        raise ValueError("Science5 metadata differs from the declared scientific protocol")
