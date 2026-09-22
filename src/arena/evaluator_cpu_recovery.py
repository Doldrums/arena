"""CPU restart ownership bound to an approved immutable image and exact mounts."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
from urllib.parse import quote
import uuid

from .evaluator_policy import IMAGE, json_object, require

RECORD_LIMIT = 4096


def approved_image(config, reference):
    from .evaluator_gpu import IMAGE as GPU_IMAGE
    require(type(reference) is str and IMAGE.fullmatch(reference)
            and reference in config.images and reference != GPU_IMAGE,
            "CPU recovery requires an explicitly approved immutable CPU image")


def image_identity(request, config, reference):
    approved_image(config, reference)
    status, _, raw = request("GET", "/images/" + quote(reference, safe="") + "/json")
    require(status == 200, "CPU image identity is unavailable; preserve ownership")
    image = json_object(raw)
    ident = image.get("Id")
    require(type(ident) is str and re.fullmatch(r"sha256:[a-f0-9]{64}", ident))
    if reference.startswith("sha256:"):
        require(ident == reference, "Docker returned a different CPU image ID")
    else:
        require(type(image.get("RepoDigests")) is list and reference in image["RepoDigests"],
                "Docker image does not carry the approved exact repository digest")
    labels = image.get("Config", {}).get("Labels")
    if labels is None:
        labels = {}
    require(type(labels) is dict and all(type(k) is str and type(v) is str for k, v in labels.items()))
    return ident, labels


def bind_image(request, config, rebuilt):
    ident, inherited = image_identity(request, config, rebuilt["Image"])
    library = next(m["Source"] for m in rebuilt["HostConfig"]["Mounts"] if m["Target"] == "/tasks")
    return {"image": rebuilt["Image"], "image_id": ident,
            "labels": inherited | rebuilt["Labels"], "task_root": library}


def write_record(stage, record):
    """Persist bounded CPU ownership before POST and after its acknowledged ID."""
    raw = json.dumps(record, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    # Acknowledged creation replaces null with a 64-character Docker ID. Reserve
    # that space before POST so a successful create cannot overflow its record.
    acknowledged = json.dumps(record | {"id": "0" * 64}, sort_keys=True,
                              separators=(",", ":"), allow_nan=False).encode()
    require(max(len(raw), len(acknowledged)) <= RECORD_LIMIT,
            "CPU ownership metadata exceeds its bounded record including container ID")
    temporary = stage / (".record-" + uuid.uuid4().hex)
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(descriptor, "wb", closefd=False) as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(descriptor)
        os.replace(temporary, stage / "record.json")
        directory = os.open(stage, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        os.close(descriptor)
        temporary.unlink(missing_ok=True)


def validate_saved(config, record, canonical_labels):
    if "cpu" not in record:
        return None
    saved = record["cpu"]
    require(type(saved) is dict and set(saved) == {"image", "image_id", "labels", "task_root"},
            "Malformed persisted CPU image identity")
    approved_image(config, saved["image"])
    require(type(saved["image_id"]) is str and re.fullmatch(r"sha256:[a-f0-9]{64}", saved["image_id"])
            and type(saved["labels"]) is dict
            and all(type(k) is str and type(v) is str for k, v in saved["labels"].items())
            and all(saved["labels"].get(k) == v for k, v in canonical_labels.items())
            and type(saved["task_root"]) is str
            and saved["task_root"] in {str(p) for p in config.library_roots},
            "Persisted CPU record has invalid image/labels/task identity")
    return saved


def verify_container(request, config, stage, record, native, canonical_labels):
    """Legacy records derive identity only from the same approved daemon image."""
    ident = native.get("Id")
    require(type(ident) is str and re.fullmatch(r"[a-f0-9]{64}", ident)
            and record["id"] in (None, ident)
            and native.get("Name") == "/" + record["name"], "CPU container name/ID differs")
    actual_config = native.get("Config", {})
    reference = actual_config.get("Image")
    saved = validate_saved(config, record, canonical_labels)
    if saved is not None:
        require(saved["image"] == reference, "CPU persisted image binding differs")
    image_id, inherited = image_identity(request, config, reference)
    expected_labels = inherited | canonical_labels
    require(native.get("Image") == image_id and actual_config.get("Labels") == expected_labels,
            "CPU image ID or exact inherited/canonical labels differ")
    roots = {str(path) for path in config.library_roots}
    if saved is not None:
        require(saved["image_id"] == image_id and saved["labels"] == expected_labels
                and type(saved["task_root"]) is str and saved["task_root"] in roots,
                "CPU immutable ownership changed since creation")
        roots = {saved["task_root"]}
    require(native.get("HostConfig", {}).get("CgroupParent") ==
            config.cgroup_root + "/arena-control-" + record["run"], "CPU recovery cgroup differs")
    mounts = native.get("Mounts")
    require(type(mounts) is list and len(mounts) == 3)
    observed = {}
    for mount in mounts:
        require(type(mount) is dict and mount.get("Type") == "bind"
                and type(mount.get("RW")) is bool and mount.get("Destination") not in observed)
        observed[mount.get("Destination")] = (mount.get("Source"), mount["RW"])
    require(set(observed) == {"/tasks", "/candidate", "/results"}
            and observed["/tasks"][0] in roots and observed["/tasks"][1] is False
            and observed["/candidate"] == (str(stage / "candidate"), False)
            and observed["/results"] == (str(stage / "results"), True),
            "CPU recovery mounts do not belong to this staging record")
    return ident
