"""Repeated explicit catalog appends preserve every previously admitted run."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("chain_fixture",
    Path(__file__).with_name("test_sciel_control_transition.py"))
single = importlib.util.module_from_spec(spec)
spec.loader.exec_module(single)
transition_fixture = single.transition_fixture
submit, write, sha, revision, template = single.submit, single.write, single.sha, single.revision, single.template
from sciel_control_transition import current_revision, load_transition, validate_resume_transition


def chain(f, length=2):
    entries = [{"path": str(f["path"]), "sha256": sha(f["path"])}]
    previous, snapshot = f["new"], Path(f["descriptor"]["next"]["path"])
    configs = [f["old"], previous]
    for index in range(2, length + 1):
        following = deepcopy(previous)
        following["templates"].append(template(100 + index))
        next_path = write(f["root"] / f"frozen/next-{index}.json", following)
        descriptor = {"schema": "arena.control-append-transition/1",
            "previous": {"path": str(snapshot), "sha256": sha(snapshot), "revision": revision(previous)},
            "next": {"path": str(next_path), "sha256": sha(next_path), "revision": revision(following)},
            "added_template_ids": [f"template-{100 + index}"]}
        child = write(f["root"] / f"transition-{index}.json", descriptor)
        entries.append({"path": str(child), "sha256": sha(child)})
        configs.append(following)
        previous, snapshot = following, next_path
    path = write(f["root"] / f"chain-{length}.json", {
        "schema": "arena.control-append-chain/1", "transitions": entries})
    argv = list(f["argv"])
    argv[argv.index("--control-transition") + 1] = str(path)
    return path, configs, argv


def load(f, path):
    return load_transition(path, control_path=f["config"], read=submit.read_bytes, encode=submit.encoded)


def test_extend_completed_single_transition_without_duplicate_admissions(transition_fixture):
    f = transition_fixture
    assert submit.main(f["argv"]) == 0
    bindings = json.loads(f["status"].read_text())["run_bindings"]
    snapshots = {key: (f["root"] / "state/runs" / key / "snapshot.json").read_bytes() for key in bindings}
    path, configs, argv = chain(f)
    write(f["config"], configs[-1])
    assert submit.main(argv) == 0 and len(f["posts"]) == 2
    status = json.loads(f["status"].read_text())
    assert status["run_bindings"] == bindings
    assert status["control_revision"] == revision(configs[0])
    assert status["active_control_revision"] == revision(configs[-1])
    assert status["control_transition"] == load(f, path)["identity"]
    for key, raw in snapshots.items():
        assert (f["root"] / "state/runs" / key / "snapshot.json").read_bytes() == raw


def test_extend_after_lost_post_preserves_old_middle_and_new_admissions(transition_fixture):
    f = transition_fixture
    f["hooks"]["crash_after_post"] = True
    assert submit.main(f["argv"]) == 2 and len(f["posts"]) == 1
    _, configs, argv = chain(f)
    write(f["config"], configs[-1])
    assert submit.main(argv) == 0 and len(f["posts"]) == 2
    assert [row["revision"] for row in f["rows"].values()] == [revision(config) for config in configs]
    assert len(json.loads(f["status"].read_text())["run_bindings"]) == 3


def test_explicit_chain_can_be_extended_again_but_not_reverted(transition_fixture):
    f = transition_fixture
    _, configs, argv = chain(f)
    write(f["config"], configs[-1])
    assert submit.main(argv) == 0
    _, extended, expanded = chain(f, 3)
    write(f["config"], extended[-1])
    assert submit.main(expanded) == 0
    before = f["status"].read_bytes()
    write(f["config"], configs[-1])
    with pytest.raises(ValueError, match="revert"):
        submit.main(expanded)
    with pytest.raises(ValueError, match="same explicit"):
        submit.main(argv)
    assert f["status"].read_bytes() == before and len(f["posts"]) == 2


def test_intermediate_live_revisions_advance_monotonically(transition_fixture):
    f = transition_fixture
    path, configs, _ = chain(f, 3)
    transition, summary = load(f, path), {}
    for config in configs:
        assert current_revision(transition, config, summary, read=submit.read_bytes,
                                encode=submit.encoded) == revision(config)
    with pytest.raises(ValueError, match="revert"):
        current_revision(transition, configs[1], summary, read=submit.read_bytes, encode=submit.encoded)


@pytest.mark.parametrize("mutation", ["reorder", "repeat", "missing_link", "wrong_hash", "public_link", "linked_file", "nested_chain"])
def test_chain_rejects_untrusted_or_disconnected_links(transition_fixture, mutation):
    f = transition_fixture
    path, _, _ = chain(f, 3)
    value = json.loads(path.read_text())
    entries = value["transitions"]
    if mutation == "reorder":
        entries[0], entries[1] = entries[1], entries[0]
    elif mutation == "repeat":
        entries[1] = entries[0]
    elif mutation == "missing_link":
        del entries[1]
    elif mutation == "wrong_hash":
        entries[1]["sha256"] = "0" * 64
    elif mutation == "public_link":
        Path(entries[1]["path"]).chmod(0o644)
    elif mutation == "linked_file":
        child = Path(entries[1]["path"])
        actual = child.with_name("actual-link.json")
        child.rename(actual)
        child.symlink_to(actual)
    else:
        nested, _, _ = chain(f, 2)
        entries[1] = {"path": str(nested), "sha256": sha(nested)}
    write(path, value)
    with pytest.raises((ValueError, OSError)):
        load(f, path)
    assert not f["posts"]


def test_changed_accepted_prefix_cannot_be_hidden_by_rehashing_new_chain(transition_fixture):
    f = transition_fixture
    assert submit.main(f["argv"]) == 0
    f["path"].write_bytes(f["path"].read_bytes() + b" ")
    _, configs, argv = chain(f)
    write(f["config"], configs[-1])
    with pytest.raises(ValueError, match="same explicit"):
        submit.main(argv)
    assert len(f["posts"]) == 2


def test_same_chain_must_keep_exact_descriptor_bytes(transition_fixture):
    f = transition_fixture
    path, configs, argv = chain(f)
    write(f["config"], configs[-1])
    assert submit.main(argv) == 0
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="same explicit"):
        submit.main(argv)


def test_chain_link_mutation_during_run_stops_next_wave(transition_fixture):
    f = transition_fixture
    path, configs, argv = chain(f)
    write(f["config"], configs[-1])
    child = Path(json.loads(path.read_text())["transitions"][1]["path"])
    f["hooks"]["after_first_poll"] = lambda: child.write_bytes(child.read_bytes() + b" ")
    assert submit.main(argv) == 2 and len(f["posts"]) == 1


def test_resume_rejects_unlisted_prior_revision_even_when_current_is_latest(transition_fixture):
    f = transition_fixture
    path, configs, _ = chain(f)
    summary = {"control_transition": load(f, path)["identity"],
               "active_control_revision": revision(configs[-1])}
    previous = {"control_revision": revision(configs[0]), "active_control_revision": "0" * 64}
    with pytest.raises(ValueError, match="revert"):
        validate_resume_transition(previous, summary)
