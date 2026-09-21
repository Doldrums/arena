"""The repository gate distinguishes reviewed data from source and secrets."""
import importlib.util
from pathlib import Path
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("repository_policy", ROOT / "scripts/check_repository_policy.py")
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)


def files(root, mapping):
    for name, body in mapping.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body)
    return list(mapping)


def test_physical_line_boundary_covers_source_configuration_and_extensionless_scripts(tmp_path):
    paths = files(tmp_path, {"src/pass.py": "\n" * 500, "web/fail.js": "\n" * 501,
        "schemas/task.schema.json": "\n" * 501, "examples/settings.jsonc": "\n" * 501,
        "registry/framework-recipes/example.json": "\n" * 501,
        "scripts/run": "#!/bin/sh\n" + "\n" * 500, "scripts/deployment/Dockerfile": "\n" * 501,
        "scripts/deployment/arena.service": "\n" * 501, ".env.example": "\n" * 501,
        "scripts/deployment/requirements-worker.txt": "\n" * 501, "web/icon.svg": "\n" * 501})
    failures = policy.check_paths(tmp_path, paths)
    assert len(failures) == 10
    assert not any("pass.py" in failure for failure in failures)
    assert all("501 physical lines" in failure for failure in failures)


def test_only_explicit_data_and_lockfiles_escape_line_count(tmp_path):
    paths = files(tmp_path, {name: "\n" * 501 for name in [
        "registry/catalog.json", "registry/results-overview.json", "registry/datasets/example.json",
        "registry/datasets/measurements.jsonl",
        "tests/observer/fixtures/journal.jsonl", "package-lock.json", "tests/web/package-lock.json", "uv.lock",
        "registry/unreviewed.json", "tests/observer/fixtures/helper.py", "examples/unreviewed/package-lock.json",
    ]})
    failures = policy.check_paths(tmp_path, paths)
    assert len(failures) == 3
    assert any("registry/unreviewed.json" in failure for failure in failures)
    assert any("fixtures/helper.py" in failure for failure in failures)
    assert any("unreviewed/package-lock.json" in failure for failure in failures)


def test_exact_markdown_locations_and_no_docs_or_reports(tmp_path):
    paths = files(tmp_path, {name: "content" for name in [
        "README.md", "CONTRIBUTING.md", "AGENTS.md", "nested/README.md", "notes.MD",
        "docs/architecture.html", "reports/results.json",
    ]})
    failures = policy.check_paths(tmp_path, paths)
    assert len(failures) == 5
    assert not any(failure.startswith(("README.md:", "CONTRIBUTING.md:")) for failure in failures)


@pytest.mark.parametrize("name", [
    ".dev.vars", ".dev.vars.production", ".env.production", "private/key.pem", "private/id_ed25519",
    "src/__pycache__/module.pyc", "node_modules/dependency/index.js", "dist/app.js", "outputs/run/result.json",
    ".wrangler/cache/data.json", ".coverage", "native/sciel_events.jsonl", "control.sqlite", "native/run.log",
])
def test_transient_and_private_files_are_rejected_even_if_small(tmp_path, name):
    paths = files(tmp_path, {name: "small"})
    assert policy.check_paths(tmp_path, paths)


def test_reviewed_fixture_journals_and_environment_example_remain_allowed(tmp_path):
    paths = files(tmp_path, {"tests/fixtures/sciel_events.jsonl": "{}\n", ".env.example": "KEY=\n"})
    assert policy.check_paths(tmp_path, paths) == []


def test_symlinks_cannot_follow_private_targets_or_bypass_the_line_limit(tmp_path):
    outside = tmp_path.parent / (tmp_path.name + "-outside.py")
    outside.write_text("private\n" * 501)
    try:
        (tmp_path / "src").mkdir()
        (tmp_path / "src/inside.py").symlink_to(outside)
        failures = policy.check_paths(tmp_path, ["src/inside.py"])
        assert failures == ["src/inside.py: repository symlinks are not supported by this policy"]
    finally:
        outside.unlink()


def test_git_inventory_finds_untracked_source_and_tracked_ignored_secrets(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    files(tmp_path, {".env": "fixture-only", ".gitignore": ".env\n.cache/\n",
        "src/new.py": "x = 1\n", ".cache/generated.txt": "ignored"})
    subprocess.run(["git", "-C", str(tmp_path), "add", "--force", ".env"], check=True)
    paths = policy.repository_paths(tmp_path)
    assert ".env" in paths and "src/new.py" in paths
    assert ".cache/generated.txt" not in paths
    assert any(failure.startswith(".env:") for failure in policy.check_paths(tmp_path, paths))


def test_deleted_tracked_paths_do_not_prevent_cleanup(tmp_path):
    assert policy.check_paths(tmp_path, ["docs/removed.md", "reports/removed.json"]) == []


@pytest.mark.parametrize("name", [
    "src/auth.json", "api/secrets.json", "examples/credentials.json", "src/notes/debug.txt",
    "tests/scratch/export.json", "src/docs/architecture.html", "examples/reports/export.json",
    "private/export.json", "notes/debug.txt", "scratch/export.json",
    "unapproved.json",
])
def test_force_added_ignored_paths_cannot_bypass_project_and_credential_rules(tmp_path, name):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    files(tmp_path, {".gitignore": (ROOT / ".gitignore").read_text(), name: "{}\n"})
    ignored = subprocess.run(["git", "-C", str(tmp_path), "check-ignore", name], capture_output=True)
    assert ignored.returncode == 0, "This regression must exercise a file ignored by the real rules"
    subprocess.run(["git", "-C", str(tmp_path), "add", "--force", name], check=True)
    paths = policy.repository_paths(tmp_path)
    assert name in paths
    assert any(failure.startswith(name + ":") for failure in policy.check_paths(tmp_path, paths))
