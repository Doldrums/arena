"""Check repository layout and physical source length without running project code.

Versioned catalog snapshots, datasets and inert fixture data have explicit path
exceptions. Source files inside those directories are still source. Adding a
new large data family requires reviewing this allowlist, not disabling the gate.
"""
from __future__ import annotations

import argparse
from pathlib import Path, PurePosixPath
import subprocess
import sys


MAX_LINES = 500
MARKDOWN = frozenset({"README.md", "CONTRIBUTING.md"})
ROOT_DIRECTORIES = frozenset({
    ".github", "src", "api", "web", "registry", "schemas", "scripts", "examples", "tests", "tasks",
})
ROOT_FILES = MARKDOWN | frozenset({
    ".gitignore", ".env.example", "pyproject.toml", "package.json", "package-lock.json",
    "uv.lock", "tsconfig.json", "wrangler.jsonc", "wrangler.debug.jsonc",
})
LOCKFILES = frozenset({"package-lock.json", "tests/web/package-lock.json", "uv.lock"})
REGISTRY_DATA = frozenset({
    "registry/catalog.json", "registry/insights.json", "registry/participants.json",
    "registry/participant-attributions.json", "registry/participant-corpus.json",
    "registry/participant-descriptions.json", "registry/references.json",
    "registry/search-families.json", "registry/search-family-sources.json",
    "registry/taxonomy.json", "registry/results-overview.json",
    "registry/provenance/sciel-extraction.json",
    "registry/task-library-manifest.json",
})
SOURCE_SUFFIXES = frozenset({
    ".py", ".pyi", ".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx",
    ".css", ".scss", ".sass", ".less", ".html", ".htm", ".sh", ".bash",
    ".zsh", ".fish", ".ps1", ".json", ".jsonc", ".yaml", ".yml", ".toml",
    ".ini", ".cfg", ".conf", ".sql", ".puml", ".graphql", ".proto", ".xml",
    ".service", ".socket", ".timer", ".svg", ".cpp", ".cc", ".h", ".hpp", ".rs", ".jl", ".r", ".mlir",
})
SOURCE_NAMES = frozenset({
    "Dockerfile", "Makefile", "Justfile", "Procfile", ".gitignore", ".dockerignore", ".env.example",
})
DATA_SUFFIXES = frozenset({".json", ".jsonl", ".csv", ".tsv", ".txt", ".yaml", ".yml"})
TRANSIENT_DIRS = frozenset({
    ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache", ".mypy_cache",
    ".ruff_cache", ".cache", ".wrangler", "dist", "build", "htmlcov", "outputs",
    "autoresearch", "playwright-report", "test-results", "notes", "scratch", "docs", "reports",
})


def fixture_data(path: PurePosixPath) -> bool:
    return (path.parts[:1] == ("tests",) and "fixtures" in path.parts[1:-1]
        and path.suffix.lower() in DATA_SUFFIXES)


def data_exception(path: PurePosixPath) -> bool:
    """Data exceptions never exempt executable fixture scripts or schemas."""
    name = path.as_posix()
    return (name in LOCKFILES or name in REGISTRY_DATA or fixture_data(path) or task_data(path)
        or path.parts[:2] == ("registry", "datasets") and path.suffix.lower() in DATA_SUFFIXES)


def task_data(path: PurePosixPath) -> bool:
    """Task definitions, source receipts and benchmark records are inert data."""
    if path.parts[:1] != ("tasks",) or path.suffix.lower() not in DATA_SUFFIXES:
        return False
    return (path.parts[1:2] in (("catalog",), ("validation",), ("data",))
        or path.as_posix() in {"tasks/import-receipt.json", "tasks/suite/index.json",
                              "tasks/adapters/recovered/seeds/eurekagent_ac1.json"}
        or path.parts[1:2] == ("suite",) and path.name in {"task.json", "problem.json"})


def transient_reason(path: PurePosixPath) -> str | None:
    name = path.name.lower()
    if any(part in TRANSIENT_DIRS or part.endswith(".egg-info") for part in path.parts[:-1]):
        return "generated dependency, build, cache, experiment or scratch directory"
    if name.startswith(".dev.vars") or (name.startswith(".env") and name != ".env.example"):
        return "private environment configuration"
    if name in {"credentials.json", "auth.json", "secrets.json"}:
        return "private credential configuration"
    if name in {"id_rsa", "id_ed25519", "id_ecdsa"} or path.suffix.lower() in {".pem", ".key", ".p12", ".pfx"}:
        return "private key or credential container"
    if name == ".ds_store" or name.startswith(".coverage") or path.suffix.lower() in {".pyc", ".pyo", ".log"}:
        return "runtime or test output"
    if not data_exception(path) and (path.suffix.lower() in {".jsonl", ".sqlite", ".sqlite3", ".db"}
            or name.endswith((".sqlite-wal", ".sqlite-shm", ".db-wal", ".db-shm"))):
        return "runtime journal or database outside reviewed fixtures"
    return None


def check_paths(root: Path, paths) -> list[str]:
    """Inspect existing files; deleted tracked paths do not block a cleanup."""
    failures = []
    for name in sorted(set(paths)):
        relative = PurePosixPath(name)
        if relative.is_absolute() or ".." in relative.parts:
            failures.append(f"{name}: path is outside the repository")
            continue
        path = root / relative
        if not path.exists() and not path.is_symlink():
            continue
        if relative.parts[:1] in (("docs",), ("reports",)):
            failures.append(f"{name}: docs/ and reports/ do not belong in the repository")
            continue
        if not (len(relative.parts) == 1 and name in ROOT_FILES
                or len(relative.parts) > 1 and relative.parts[0] in ROOT_DIRECTORIES):
            failures.append(f"{name}: top-level path is outside the approved project surface")
            continue
        if relative.suffix.lower() == ".md" and name not in MARKDOWN:
            failures.append(f"{name}: Markdown is limited to root README.md and CONTRIBUTING.md")
        reason = transient_reason(relative)
        if reason:
            failures.append(f"{name}: {reason}")
        if path.is_symlink():
            # Do not follow an outside target, and do not allow source symlinks
            # to evade the source-size policy.
            failures.append(f"{name}: repository symlinks are not supported by this policy")
            continue
        if not path.is_file() or data_exception(relative):
            continue
        is_source = relative.suffix.lower() in SOURCE_SUFFIXES or relative.name in SOURCE_NAMES
        is_source = is_source or relative.match("requirements*.txt")
        with path.open("rb") as stream:
            prefix = stream.read(256)
        is_source = is_source or prefix.startswith(b"#!")
        if not is_source:
            continue
        try:
            length = len(path.read_text(encoding="utf-8").splitlines())
        except UnicodeError:
            failures.append(f"{name}: source/configuration is not UTF-8 text")
            continue
        if length > MAX_LINES:
            failures.append(f"{name}: {length} physical lines exceeds {MAX_LINES}")
    return failures


def repository_paths(root: Path) -> list[str]:
    """Include untracked source locally and tracked files even if now ignored."""
    result = subprocess.run(["git", "-C", str(root), "ls-files", "-z", "--cached",
        "--others", "--exclude-standard"], check=True, capture_output=True)
    return [name for name in result.stdout.decode("utf-8").split("\0") if name]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    try:
        paths = repository_paths(args.root)
        failures = check_paths(args.root, paths)
    except (OSError, subprocess.CalledProcessError, UnicodeError) as error:
        print(f"Repository policy could not inspect the checkout: {error}", file=sys.stderr)
        return 1
    if failures:
        for failure in failures:
            print(failure, file=sys.stderr)
        return 1
    print(f"Repository policy passed: {len(paths)} paths; source/configuration <= {MAX_LINES} lines")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
