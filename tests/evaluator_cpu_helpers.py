"""Small actual-Docker-shaped CPU image/container fixtures, without a daemon."""
from copy import deepcopy


def image(reference):
    return {"Id": reference, "RepoDigests": [], "Config": {"Labels": {}}}


def native_container(config, stage, record, inspected=None):
    inspected = inspected or image(config.images[0])
    reference = record.get("cpu", {}).get("image", config.images[0])
    labels = {"arena.evaluator": "canonical-v1", "arena.control-run": record["run"]}
    if "resource_profile" in record:
        labels["arena.evaluation-profile"] = record["resource_profile"]
    return {"Id": record["id"] or "d" * 64, "Name": "/" + record["name"],
        "Image": inspected["Id"],
        "Config": {"Image": reference, "Labels": (inspected["Config"]["Labels"] or {}) | labels},
        "HostConfig": {"CgroupParent": config.cgroup_root + "/arena-control-" + record["run"]},
        "Mounts": [{"Type": "bind", "Source": str(source), "Destination": target, "RW": writable}
            for source, target, writable in [(record.get("cpu", {}).get("task_root", config.tasks_root), "/tasks", False),
                                            (stage / "candidate", "/candidate", False),
                                            (stage / "results", "/results", True)]]}


def cpu_binding(config, body, inspected=None):
    inspected = inspected or image(body["Image"])
    return {"image": body["Image"], "image_id": inspected["Id"],
        "labels": (inspected["Config"]["Labels"] or {}) | body["Labels"],
        "task_root": next(m["Source"] for m in body["HostConfig"]["Mounts"] if m["Target"] == "/tasks")}
