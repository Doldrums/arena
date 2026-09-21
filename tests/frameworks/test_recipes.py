"""Generic integrations use real isolated fixture processes; no model calls."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from arena.frameworks import get_adapter, describe, recipes, runtime


def git(path, *args):
    return subprocess.check_output(["git", "-C", str(path), *args], text=True).strip()


@pytest.fixture
def native_recipe(tmp_path, monkeypatch):
    source = tmp_path / "source"
    (source / "sub").mkdir(parents=True)
    (source / "sub/main.py").write_text('''import argparse, json, os
from pathlib import Path
parser = argparse.ArgumentParser()
parser.add_argument('--output')
parser.add_argument('--algorithm')
args = parser.parse_args()
assert args.algorithm == 'native'
config = json.loads(Path('config.json').read_text())
root = Path(args.output)
root.mkdir(parents=True)
(root / 'new.json').write_text(json.dumps({'value': config['value'], 'key_present': bool(os.getenv('FIXTURE_API_KEY'))}))
''')
    (source / "sub/config.json").write_text('{"value": 3}')
    (source / "historical.json").write_text('{"score": 9000}')
    (source / ".env").write_text('FIXTURE_API_KEY=placeholder\n')
    git(source, "init", "-q")
    git(source, "config", "user.name", "Fixture")
    git(source, "config", "user.email", "fixture@example.invalid")
    git(source, "add", ".")
    git(source, "commit", "-qm", "native fixture")
    recipe = {"id": "fixture", "name": "Fixture", "participant_ids": ["paper"],
              "repository": {"url": "https://github.com/example/fixture", "commit": git(source, "rev-parse", "HEAD")},
              "status": "source_verified", "license": "MIT", "setup": [], "blocked_reason": None,
              "evidence": {p: hashlib.sha256((source / p).read_bytes()).hexdigest()
                           for p in ["sub/main.py", "sub/config.json", ".env"]},
              "profiles": [{"id": "native", "description": "Fixture evaluation", "invocation": {"kind": "script", "target": "sub/main.py"},
                            "cwd": "sub", "fixed_args": ["--algorithm", "native"],
                            "output": {"flag": "--output", "path": "native"},
                            "required_files": ["sub/main.py"], "config_files": ["sub/config.json"],
                            "result_globs": ["**/*.json"], "evaluation": {"mode": "native", "description": "Fixture result", "evidence": ["sub/main.py"]},
                            "argument_help": [], "limitations": [], "remove_files": [".env"]}]}
    monkeypatch.setattr(recipes, "load_recipes", lambda root=None: {"fixture": recipe})
    spec = {"schema": "arena.native-run/1", "framework": "fixture", "source_dir": str(source),
            "output_dir": str(tmp_path / "output"), "timeout_seconds": 10,
            "request": {"python": sys.executable, "profile": "native"}}
    return recipe, spec


def test_discovery_and_planning_do_not_import_native_code(native_recipe):
    recipe, spec = native_recipe
    assert get_adapter("paper").recipe["id"] == "fixture"
    listing = describe()
    assert next(x for x in listing if x["id"] == "fixture")["runtime_readiness"] == "not_verified"
    plan = runtime.prepare_plan(spec)
    assert plan["command"]["cwd"].endswith("workspace/fixture/sub")
    assert not Path(spec["output_dir"]).exists()
    assert any(x["path"].endswith("recipes.py") for x in plan["inputs"])


def test_isolated_run_preserves_source_and_excludes_committed_results(native_recipe, tmp_path, monkeypatch):
    recipe, spec = native_recipe
    overlay = tmp_path / "config.json"
    overlay.write_text('{"value": 7}')
    spec["request"]["config_overlays"] = {"sub/config.json": str(overlay)}
    spec["environment_names"] = ["FIXTURE_API_KEY"]
    monkeypatch.setenv("FIXTURE_API_KEY", "not-a-real-secret")
    receipt = runtime.run(spec)
    assert receipt["status"] == "process_completed"
    source, output = Path(spec["source_dir"]), Path(spec["output_dir"])
    assert json.loads((source / "sub/config.json").read_text())["value"] == 3
    assert (source / ".env").is_file()
    assert not (output / "workspace/fixture/.env").exists()
    assert git(source, "status", "--porcelain") == ""
    assert json.loads((output / "native/new.json").read_text()) == {"value": 7, "key_present": True}
    result = get_adapter("fixture").read_results(output)
    assert result["status"] == "recorded"
    assert [a["path"] for a in result["artifacts"]] == ["native/new.json"]
    assert result["canonical_evaluation"] is False
    assert "not-a-real-secret" not in (output / ".arena/plan.json").read_text()


@pytest.mark.parametrize("args", [["--algorithm", "other"], ["--algorithm=other"], ["--alg", "other"], ["--out=/tmp/escape"], ["--output", "/tmp/escape"],
                                  ["--api-key=secret"], ["++search.method=other"]])
def test_fixed_profile_and_credential_options_cannot_be_overridden(native_recipe, args):
    recipe, spec = native_recipe
    recipe["profiles"][0]["fixed_args"].append("search.method=native")
    spec["request"]["arguments"] = args
    with pytest.raises(ValueError):
        runtime.prepare_plan(spec)


@pytest.mark.parametrize("arguments", [["--api_k", "FAKE_REVIEW_KEY"], ["--api_k=FAKE_REVIEW_KEY"],
                                       ["-k", "FAKE_REVIEW_KEY"], ["-kFAKE_REVIEW_KEY"],
                                       ["--provider-c", "FAKE_REVIEW_KEY"]])
def test_native_argparse_credential_aliases_and_abbreviations_are_rejected_before_planning(native_recipe, arguments):
    recipe, spec = native_recipe
    source = Path(spec["source_dir"])
    entry = source / "sub/main.py"
    entry.write_text(entry.read_text().replace("args = parser.parse_args()", '''parser.add_argument('-k', '--api_key')
parser.add_argument('--provider-credential', dest='access_token')
args = parser.parse_args()'''))
    recipe["evidence"]["sub/main.py"] = hashlib.sha256(entry.read_bytes()).hexdigest()
    git(source, "add", ".")
    git(source, "commit", "-qm", "credential argument fixture")
    recipe["repository"]["commit"] = git(source, "rev-parse", "HEAD")
    spec["request"]["arguments"] = arguments
    with pytest.raises(ValueError, match="credentials through explicit environment_names") as error:
        runtime.prepare_plan(spec)
    assert "FAKE_REVIEW_KEY" not in str(error.value)
    assert not Path(spec["output_dir"]).exists()


def test_source_evidence_and_configuration_boundaries(native_recipe, tmp_path):
    recipe, spec = native_recipe
    config = tmp_path / "bad.py"
    config.write_text("raise RuntimeError('not allowed')")
    spec["request"]["config_overlays"] = {"sub/main.py": str(config)}
    with pytest.raises(ValueError, match="not declared"):
        runtime.prepare_plan(spec)
    del spec["request"]["config_overlays"]
    recipe["evidence"]["sub/main.py"] = "0" * 64
    with pytest.raises(ValueError, match="evidence mismatch"):
        runtime.prepare_plan(spec)


def test_implicit_dotenv_ancestor_is_rejected_without_reading_it(native_recipe, tmp_path):
    _, spec = native_recipe
    (tmp_path / ".env").write_text("SECRET=do-not-load")
    with pytest.raises(ValueError, match="implicitly loaded"):
        runtime.prepare_plan(spec)


def test_external_runtime_identity_is_required_and_hashed(native_recipe):
    recipe, spec = native_recipe
    recipe["profiles"][0]["executable_args"] = {"julia": "--julia"}
    with pytest.raises(ValueError, match="executables"):
        runtime.prepare_plan(spec)
    spec["request"]["executables"] = {"julia": sys.executable}
    plan = runtime.prepare_plan(spec)
    assert plan["command"]["executables"][0]["sha256"] == runtime._digest_file(Path(sys.executable))
    spec["request"]["arguments"] = ["--julia", "/somewhere/else"]
    with pytest.raises(ValueError, match="fixes this option"):
        runtime.prepare_plan(spec)


def test_reader_requires_baseline_and_never_follows_output_symlinks(native_recipe, tmp_path):
    _, spec = native_recipe
    runtime.run(spec)
    output = Path(spec["output_dir"])
    (output / "native/linked.json").symlink_to(tmp_path / "private.json")
    (tmp_path / "private.json").write_text('{"private": true}')
    result = get_adapter("fixture").read_results(output)
    assert all(not a["path"].endswith("linked.json") for a in result["artifacts"])
    (output / ".arena/artifact-baseline.json").unlink()
    assert get_adapter("fixture").read_results(output)["status"] == "missing"


def test_reader_has_bounded_tree_walk(native_recipe, monkeypatch):
    _, spec = native_recipe
    runtime.run(spec)
    def oversized(*args, **kwargs):
        yield spec["output_dir"], [], [str(n) for n in range(50001)]
    monkeypatch.setattr(os, "walk", oversized)
    result = get_adapter("fixture").read_results(spec["output_dir"])
    assert result["status"] == "partial" and not result["artifacts"]


@pytest.mark.parametrize("path", ["results/a.json", "results/deep/a.json", "results/deep/deeper/a.json"])
def test_recursive_artifact_globs_cover_zero_and_multiple_subdirectories(path):
    assert recipes._glob_matches(path, "results/**/*.json")
    assert not recipes._glob_matches("elsewhere/" + path, "results/**/*.json")


def test_old_artifacts_cannot_be_reinterpreted_with_changed_evaluation_metadata(native_recipe):
    recipe, spec = native_recipe
    runtime.run(spec)
    recipe["profiles"][0]["evaluation"]["description"] = "A different interpretation"
    result = get_adapter("fixture").read_results(spec["output_dir"])
    assert result["status"] == "missing" and not result["artifacts"]


def test_checkout_ignores_global_line_ending_conversion_and_rechecks_source_bytes(native_recipe, tmp_path, monkeypatch):
    recipe, spec = native_recipe
    source = Path(spec["source_dir"])
    (source / ".gitattributes").write_text("* text=auto\n")
    git(source, "add", ".gitattributes")
    git(source, "commit", "-qm", "attributes fixture")
    recipe["repository"]["commit"] = git(source, "rev-parse", "HEAD")
    config = tmp_path / "global-git-config"
    config.write_text("[core]\n    autocrlf = true\n")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(config))
    receipt = runtime.run(spec)
    assert receipt["status"] == "process_completed"
    copied = Path(spec["output_dir"]) / "workspace/fixture/sub/main.py"
    assert copied.read_bytes() == (source / "sub/main.py").read_bytes()
