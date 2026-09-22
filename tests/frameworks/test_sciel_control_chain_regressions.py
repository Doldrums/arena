"""Adversarial revision and run-identity regressions for explicit append chains."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("chain_regression_fixture",
    Path(__file__).with_name("test_sciel_control_chain.py"))
chain_tests = importlib.util.module_from_spec(spec)
spec.loader.exec_module(chain_tests)
single = chain_tests.single
transition_fixture = single.transition_fixture
submit, write, sha, revision = single.submit, single.write, single.sha, single.revision


def copy_run_files(f, previous, replacement):
    for name in ("snapshot.json", "artifacts/.arena/native-result.json"):
        source = f["root"] / "state/runs" / previous / name
        write(f["root"] / "state/runs" / replacement / name, json.loads(source.read_text()))


def test_contiguous_links_require_the_same_canonical_revision_not_python_equality(transition_fixture):
    f = transition_fixture
    path, configs, _ = chain_tests.chain(f)
    descriptor = json.loads(path.read_text())
    second_path = Path(descriptor["transitions"][1]["path"])
    second = json.loads(second_path.read_text())
    # Each individual link is still a valid exact append. Only the handoff
    # changes: Python equates 16 and 16.0, canonical control JSON does not.
    for key, config in (("previous", configs[1]), ("next", configs[2])):
        changed = deepcopy(config)
        changed["templates"][0]["spec"]["request"]["budget"] = 16.0
        frozen = write(f["root"] / f"frozen/type-changed-{key}.json", changed)
        second[key] = {"path": str(frozen), "sha256": sha(frozen), "revision": revision(changed)}
    write(second_path, second)
    descriptor["transitions"][1]["sha256"] = sha(second_path)
    write(path, descriptor)
    assert configs[1] == json.loads(Path(second["previous"]["path"]).read_text())
    assert revision(configs[1]) != second["previous"]["revision"]
    with pytest.raises(ValueError):
        chain_tests.load(f, path)
    assert not f["posts"]


def test_single_append_cannot_change_existing_json_number_types(transition_fixture):
    f = transition_fixture
    changed = deepcopy(f["new"])
    changed["templates"][0]["spec"]["request"]["budget"] = 16.0
    next_path = Path(f["descriptor"]["next"]["path"])
    write(next_path, changed)
    f["descriptor"]["next"].update(sha256=sha(next_path), revision=revision(changed))
    write(f["path"], f["descriptor"])
    with pytest.raises(ValueError):
        single.load(f)
    assert not f["posts"]


def test_prepared_template_comparison_keeps_canonical_json_types(transition_fixture):
    f = transition_fixture
    planned = json.loads(f["templates"].read_text())
    changed = deepcopy(f["new"])
    changed["templates"][0]["spec"]["request"]["budget"] = 16.0
    assert planned[0] == changed["templates"][0]
    with pytest.raises(ValueError):
        submit.validate_templates(planned, changed)
    assert not f["posts"]


def test_post_observed_new_revision_sets_floor_before_next_admission(transition_fixture, monkeypatch):
    f = transition_fixture
    _, configs, argv = chain_tests.chain(f)
    write(f["config"], configs[1])
    original = submit.Control

    class RevisionRace(original):
        changed = False

        def call(self, path, body=None):
            if body is not None and not type(self).changed:
                type(self).changed = True
                write(f["config"], configs[2])
                result = super().call(path, body)
                # POST really admitted at r2. The next live observation r1
                # must be a rollback even if check_live never previously saw r2.
                write(f["config"], configs[1])
                return result
            return super().call(path, body)

    monkeypatch.setattr(submit, "Control", RevisionRace)
    assert submit.main(argv) == 2
    assert len(f["posts"]) == 1, "A later task must not be admitted under r1 after observing r2"
    assert [row["revision"] for row in f["rows"].values()] == [revision(configs[0]), revision(configs[2])]
    status = json.loads(f["status"].read_text())
    assert status["state"] == "paused_control_error"
    assert status["active_control_revision"] == revision(configs[2])


def test_resume_cannot_replace_known_run_with_new_id_for_same_template_and_batch(transition_fixture):
    f = transition_fixture
    _, configs, argv = chain_tests.chain(f)
    write(f["config"], configs[-1])
    assert submit.main(argv) == 0
    existing_posts = len(f["posts"])
    previous = next(iter(f["rows"]))
    replacement = "f" * 32
    row = f["rows"].pop(previous)
    row["id"] = replacement
    f["rows"][replacement] = row
    copy_run_files(f, previous, replacement)
    assert submit.main(argv) == 2
    assert len(f["posts"]) == existing_posts
    status = json.loads(f["status"].read_text())
    assert status["state"] == "paused_control_error"
    assert replacement not in status["run_bindings"]


def test_missing_known_run_in_inventory_stops_before_any_post(transition_fixture):
    f = transition_fixture
    _, configs, argv = chain_tests.chain(f)
    write(f["config"], configs[-1])
    # The legacy status already records this ID in batches, before explicit
    # chain bindings existed. Losing it is not permission for a fresh run.
    previous = next(iter(f["rows"]))
    del f["rows"][previous]
    assert submit.main(argv) == 2
    assert not f["posts"]
    status = json.loads(f["status"].read_text())
    assert status["state"] == "paused_control_error"
    assert previous in status["run_bindings"]


def test_get_response_must_match_requested_run_id(transition_fixture, monkeypatch):
    f = transition_fixture
    _, configs, argv = chain_tests.chain(f)
    write(f["config"], configs[-1])
    previous = next(iter(f["rows"]))
    replacement = "e" * 32
    copy_run_files(f, previous, replacement)
    original = submit.Control

    class WrongIdentity(original):
        def call(self, path, body=None):
            result = super().call(path, body)
            if body is None and path == "/api/queue/" + previous:
                result["run"]["id"] = replacement
            return result

    monkeypatch.setattr(submit, "Control", WrongIdentity)
    assert submit.main(argv) == 2
    assert len(f["posts"]) == 1, "Do not admit a later wave after the wrong detail response"
    status = json.loads(f["status"].read_text())
    assert status["state"] == "paused_control_error"
    assert replacement not in status["run_bindings"]


def legacy_bindings_only(f):
    """Old submitter persisted verified bindings before its first batch record."""
    _, configs, argv = chain_tests.chain(f)
    previous = next(iter(f["rows"]))
    snapshot = f["root"] / "state/runs" / previous / "snapshot.json"
    binding = {"revision": f["rows"][previous]["revision"], "snapshot_sha256": sha(snapshot)}
    status = json.loads(f["status"].read_text())
    status.update(batches=[], control_transition=single.load(f)["identity"],
                  active_control_revision=revision(configs[1]), run_bindings={previous: binding})
    status.pop("run_assignments", None)
    write(f["status"], status)
    write(f["config"], configs[-1])
    return argv, previous, binding, snapshot.read_bytes()


def test_legacy_bindings_only_status_migrates_without_replacing_admitted_run(transition_fixture):
    f = transition_fixture
    argv, previous, binding, snapshot = legacy_bindings_only(f)
    assert submit.main(argv) == 0
    assert len(f["posts"]) == 2
    status = json.loads(f["status"].read_text())
    assert status["run_bindings"][previous] == binding
    assert status["run_assignments"]["template-0"] == {"id": previous, "batch_id": "original-b001"}
    assert len(status["run_bindings"]) == len(status["run_assignments"]) == 3
    assert (f["root"] / "state/runs" / previous / "snapshot.json").read_bytes() == snapshot


@pytest.mark.parametrize("mutation", ["missing", "replaced"])
def test_legacy_bindings_only_status_checks_every_saved_id_before_post(transition_fixture, mutation):
    f = transition_fixture
    argv, previous, binding, _ = legacy_bindings_only(f)
    row = f["rows"].pop(previous)
    replacement = "d" * 32
    if mutation == "replaced":
        row["id"] = replacement
        f["rows"][replacement] = row
        copy_run_files(f, previous, replacement)
    assert submit.main(argv) == 2
    assert not f["posts"], "A legacy binding is not permission to run the experiment again"
    status = json.loads(f["status"].read_text())
    assert status["state"] == "paused_control_error"
    assert status["run_bindings"][previous] == binding
    assert replacement not in status["run_bindings"]
