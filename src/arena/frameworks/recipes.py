"""Source-verified native launch recipes for external research implementations.

Recipes identify the actual native search/evaluation entrypoint. Planning reads
metadata only; source code is loaded exclusively by an explicit run command.
"""
from __future__ import annotations

import hashlib
import ast
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
from fnmatch import fnmatchcase
from functools import lru_cache

from arena.registry import resolve_registry_root

_ID = re.compile(r"[a-z0-9][a-z0-9-]*")
_HASH = re.compile(r"[0-9a-f]{64}")
_SECRET = re.compile(r"(?i)(?:^|[._-])(?:api[_-]?key|access[_-]?token|auth[_-]?token|password|secret|authorization|credential)(?:$|[._-])")


def relative(value, *, glob=False):
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise ValueError("Expected a contained relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or ".git" in path.parts:
        raise ValueError("Recipe path escapes its workspace")
    if not glob and any(c in value for c in "*?["):
        raise ValueError("Wildcards are only allowed in result globs")
    return value


def validate_recipe(recipe):
    required = {"id", "name", "participant_ids", "repository", "status", "license", "setup",
                "blocked_reason", "evidence", "profiles"}
    if type(recipe) is not dict or set(recipe) != required or not _ID.fullmatch(recipe["id"]):
        raise ValueError("Invalid native recipe identity or fields")
    if recipe["status"] not in {"source_verified", "blocked", "artifact_only"}:
        raise ValueError("Unknown native recipe status")
    if not isinstance(recipe["name"], str) or not recipe["name"].strip():
        raise ValueError("Recipe needs a name")
    for key in ("setup", "participant_ids"):
        if type(recipe[key]) is not list or any(not isinstance(s, str) or not s for s in recipe[key]):
            raise ValueError(f"Recipe {key} must be a string list")
    if len(recipe["participant_ids"]) != len(set(recipe["participant_ids"])):
        raise ValueError("Duplicate recipe participant identity")
    repository = recipe["repository"]
    if repository is not None:
        if (type(repository) is not dict or set(repository) != {"url", "commit"}
                or not re.fullmatch(r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository["url"])
                or not re.fullmatch(r"[0-9a-f]{40}", repository["commit"])):
            raise ValueError("Recipe repository must pin a credential-free GitHub commit")
    if type(recipe["profiles"]) is not list or type(recipe["evidence"]) is not dict:
        raise ValueError("Recipe requires profiles and source evidence")
    for path, digest in recipe["evidence"].items():
        relative(path)
        if not isinstance(digest, str) or not _HASH.fullmatch(digest):
            raise ValueError("Source evidence must carry file SHA256s")
    if recipe["status"] == "blocked":
        if recipe["profiles"] or not isinstance(recipe["blocked_reason"], str) or not recipe["blocked_reason"]:
            raise ValueError("Blocked recipe requires a reason and no launch profiles")
    elif recipe["profiles"]:
        if repository is None or not recipe["evidence"] or recipe["blocked_reason"] is not None:
            raise ValueError("Launchable recipe needs pinned source evidence")
    elif recipe["status"] == "source_verified":
        raise ValueError("Source-verified recipe needs an actual launch profile")
    seen = set()
    for profile in recipe["profiles"]:
        required_profile = {"id", "description", "invocation", "cwd", "fixed_args", "output", "required_files",
                            "config_files", "result_globs", "evaluation", "argument_help", "limitations"}
        optional = {"python_paths", "environment", "remove_files", "protected_args", "executable_args"}
        if (type(profile) is not dict or not required_profile <= profile.keys() or set(profile) - required_profile - optional
                or not _ID.fullmatch(profile["id"]) or profile["id"] in seen):
            raise ValueError("Invalid or duplicate native launch profile")
        seen.add(profile["id"])
        relative(profile["cwd"])
        invocation = profile["invocation"]
        if type(invocation) is not dict or set(invocation) != {"kind", "target"}:
            raise ValueError("Profile needs an explicit native invocation")
        kind, target = invocation["kind"], invocation["target"]
        if kind == "script":
            relative(target)
            if target not in recipe["evidence"] or not target.endswith(".py"):
                raise ValueError("Native Python script must have source evidence")
        elif kind in {"module", "driver"}:
            if not re.fullmatch(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*", target):
                raise ValueError("Invalid module entrypoint")
            if kind == "driver" and not target.startswith("arena.frameworks.drivers."):
                raise ValueError("Driver must be a reviewed Arena integration module")
        else:
            raise ValueError("Only native Python scripts, modules or reviewed drivers are supported")
        for key in ("fixed_args", "required_files", "config_files", "result_globs", "argument_help", "limitations",
                    "python_paths", "remove_files", "protected_args"):
            values = profile.get(key, [])
            if type(values) is not list or any(not isinstance(v, str) or "\x00" in v for v in values):
                raise ValueError(f"Profile {key} must be a string list")
        for key in ("required_files", "config_files", "python_paths"):
            for path in profile.get(key, []):
                relative(path)
        for path in profile["result_globs"]:
            relative(path, glob=True)
        for path in profile.get("remove_files", []):
            relative(path)
            if Path(path).name != ".env" and not (path == "model_config.json" and path in recipe["evidence"] and path in profile["required_files"]):
                raise ValueError("Only native dotenv files or an evidence-hashed credential template may be removed")
        evaluation = profile["evaluation"]
        if (type(evaluation) is not dict or set(evaluation) != {"mode", "description", "evidence"}
                or evaluation["mode"] != "native" or not isinstance(evaluation["description"], str)
                or not evaluation["description"] or type(evaluation["evidence"]) is not list
                or not evaluation["evidence"] or any(p not in recipe["evidence"] for p in evaluation["evidence"])):
            raise ValueError("Native evaluation must be supported by pinned source evidence")
        environment = profile.get("environment", {})
        if (type(environment) is not dict or any(not re.fullmatch(r"[A-Z][A-Z0-9_]*", k)
                or _SECRET.search(k) or k in {"PYTHONPATH", "PATH", "PYTHONHOME"} or not isinstance(v, str)
                for k, v in environment.items())):
            raise ValueError("Recipe environment must not contain credential or interpreter overrides")
        output = profile["output"]
        if output is not None:
            if type(output) is not dict or set(output) != {"flag", "path"} or not isinstance(output["flag"], str):
                raise ValueError("Invalid native output declaration")
            relative(output["path"])
            if not re.fullmatch(r"--?[A-Za-z][\w-]*|[A-Za-z_][\w.]*=", output["flag"]):
                raise ValueError("Invalid native output option")
        if set(profile["config_files"]) & set(profile["evaluation"]["evidence"]):
            raise ValueError("Evaluator source cannot be a mutable configuration overlay")
        executable_args = profile.get("executable_args", {})
        if type(executable_args) is not dict or any(not _ID.fullmatch(k) or not re.fullmatch(r"--[a-z][a-z-]*", v)
                                                   for k, v in executable_args.items()):
            raise ValueError("External runtimes need explicit names and fixed argument flags")
    return recipe


def load_recipes(root=None):
    directory = resolve_registry_root(root) / "framework-recipes"
    recipes = {}
    for path in sorted(directory.glob("*.json")):
        document = json.loads(path.read_text())
        if document.get("schema") != "arena.framework-recipes/1" or type(document.get("recipes")) is not list:
            raise ValueError(f"Invalid framework recipe file {path.name}")
        for recipe in document["recipes"]:
            validate_recipe(recipe)
            if recipe["id"] in recipes:
                raise ValueError("Duplicate native engine recipe")
            recipes[recipe["id"]] = recipe
    return recipes


def _option(value):
    return value.lstrip("+").split("=", 1)[0]


def _credential_options(source, evidence):
    """Read literal argparse aliases from verified source without importing it."""
    options = set()
    for filename in evidence:
        if not filename.endswith(".py"):
            continue
        path = source / filename
        if path.stat().st_size > 8 * 1024 * 1024:
            raise ValueError("Native parser source exceeds the inspection limit")
        try:
            tree = ast.parse(path.read_bytes(), filename=filename)
        except (SyntaxError, UnicodeError):
            continue  # Some evidence belongs to a different Python version.
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "add_argument"):
                continue
            aliases = [arg.value for arg in node.args if isinstance(arg, ast.Constant)
                       and isinstance(arg.value, str) and arg.value.startswith("-")]
            destinations = [kw.value.value for kw in node.keywords if kw.arg == "dest"
                            and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str)]
            if any(_SECRET.search(value.lstrip("-")) for value in aliases + destinations):
                options.update(aliases)
    return options


def _glob_matches(path, pattern):
    """Match relative path components, with ** spanning zero or more levels."""
    names, pieces = PurePosixPath(path).parts, PurePosixPath(pattern).parts
    @lru_cache(maxsize=None)
    def match(i, j):
        if j == len(pieces):
            return i == len(names)
        if pieces[j] == "**":
            return match(i, j + 1) or i < len(names) and match(i + 1, j)
        return i < len(names) and fnmatchcase(names[i], pieces[j]) and match(i + 1, j + 1)
    return match(0, 0)


def artifact_files(output, workspace, patterns):
    """Bounded traversal without following symlinks or scanning Git/receipt data."""
    visited = 0
    for directory, dirs, files in os.walk(output, followlinks=False):
        parent = Path(directory)
        dirs[:] = sorted(d for d in dirs if d not in {".git", ".arena", "__pycache__"}
                         and not (parent / d).is_symlink())
        visited += len(dirs) + len(files)
        if visited > 50000:
            raise ValueError("Native artifact traversal limit exceeded")
        for name in sorted(files):
            path = parent / name
            if not stat.S_ISREG(path.lstat().st_mode):
                continue
            names = [path.relative_to(output)]
            if path.is_relative_to(workspace):
                names.append(path.relative_to(workspace))
            if any(_glob_matches(value, pattern)
                   for value in names for pattern in patterns):
                yield path


def snapshot_artifacts(output, workspace, patterns):
    from .runtime import _digest_file
    files, size = {}, 0
    for path in artifact_files(output, workspace, patterns):
        size += path.stat().st_size
        if size > 512 * 1024 * 1024 or len(files) >= 10000:
            raise ValueError("Pre-run artifact baseline exceeds its provenance limit")
        files[str(path.relative_to(output))] = _digest_file(path)
    return {"schema": "arena.native-artifact-baseline/1", "files": files}


class RecipeAdapter:
    def __init__(self, recipe, *, identity=None):
        self.recipe = validate_recipe(recipe)
        self.id = identity or recipe["id"]
        self.commit = recipe["repository"]["commit"] if recipe["repository"] else None

    def prepare(self, source_dir, request, output_dir):
        from .runtime import _digest_file
        allowed = {"python", "profile", "arguments", "inputs", "config_overlays", "executables"}
        if type(request) is not dict or set(request) - allowed or "python" not in request:
            raise ValueError("Recipe request needs python, profile and explicit native arguments")
        if not self.recipe["profiles"]:
            raise ValueError(self.recipe["blocked_reason"] or "This artifact has no native launch profile")
        profile_id = request.get("profile")
        if profile_id is None and len(self.recipe["profiles"]) == 1:
            profile_id = self.recipe["profiles"][0]["id"]
        profile = next((p for p in self.recipe["profiles"] if p["id"] == profile_id), None)
        if profile is None:
            raise ValueError(f"Choose an explicit profile: {[p['id'] for p in self.recipe['profiles']]}")
        source, output = Path(source_dir).resolve(), Path(output_dir).resolve()
        if any((parent / ".env").exists() or (parent / ".env").is_symlink() for parent in (output, *output.parents)):
            raise ValueError("Native output ancestors must not contain an implicitly loaded .env")
        python = Path(request["python"])
        if not python.is_absolute() or not python.is_file() or not os.access(python, os.X_OK):
            raise ValueError("python must be an absolute executable in the prepared native environment")
        for path, digest in self.recipe["evidence"].items():
            actual = source / path
            if actual.is_symlink() or not actual.is_file() or not actual.resolve().is_relative_to(source) or _digest_file(actual) != digest:
                raise ValueError(f"Native source evidence mismatch: {path}")
        for name in profile["required_files"]:
            if not (source / name).is_file() or not (source / name).resolve().is_relative_to(source):
                raise ValueError(f"Native required source file is missing: {name}")
        if not (source / profile["cwd"]).is_dir():
            raise ValueError("Native working directory is missing")
        workspace = output / "workspace" / self.recipe["id"]
        cwd = workspace / profile["cwd"]
        arguments = request.get("arguments", [])
        if type(arguments) is not list or len(arguments) > 512 or any(not isinstance(a, str) or "\x00" in a or len(a) > 16384 for a in arguments):
            raise ValueError("arguments must be a bounded native argument vector")
        protected = {_option(a) for a in profile["fixed_args"] if a.startswith("-") or "=" in a}
        protected.update(_option(a) for a in profile.get("protected_args", []))
        protected.update(profile.get("executable_args", {}).values())
        if profile["output"]:
            protected.add(_option(profile["output"]["flag"]))
        credential_options = _credential_options(source, self.recipe["evidence"])
        for argument in arguments:
            key = _option(argument)
            if (key in protected
                    or key.startswith("--") and any(k.startswith(key) for k in protected)
                    or any(k.startswith("-") and not k.startswith("--") and argument.startswith(k) for k in protected)):
                raise ValueError(f"Native profile fixes this option: {key}")
            if (_SECRET.search(key.lstrip("-")) or key in credential_options
                    or key.startswith("--") and any(option.startswith(key) for option in credential_options)
                    or any(option.startswith("-") and not option.startswith("--")
                           and argument.startswith(option) for option in credential_options)):
                raise ValueError("Pass provider credentials through explicit environment_names, not arguments")
        inputs, overlays, input_paths = [], [], []
        for key, target in (("inputs", inputs), ("config_overlays", overlays)):
            mapping = request.get(key, {})
            if type(mapping) is not dict:
                raise ValueError(f"{key} must map workspace paths to absolute input paths")
            for dest, value in mapping.items():
                relative(dest)
                if key == "config_overlays" and dest not in profile["config_files"]:
                    raise ValueError(f"Configuration overlay is not declared by this profile: {dest}")
                origin = Path(value)
                if not origin.is_absolute() or not origin.exists() or origin.is_symlink():
                    raise ValueError("Native inputs must be existing absolute non-symlink paths")
                if key == "config_overlays" and not origin.is_file():
                    raise ValueError("Configuration overlays must be regular files")
                target.append({"source": str(origin), "destination": dest})
                input_paths.append(str(origin))
        invocation = profile["invocation"]
        if invocation["kind"] == "script":
            argv = [str(python), str(workspace / invocation["target"])]
        else:
            argv = [str(python), "-m", invocation["target"]]
        replacements = {"{workspace}": str(workspace), "{output}": str(output), "{source}": str(source)}
        def expand(text):
            for marker, value in replacements.items():
                text = text.replace(marker, value)
            return text
        argv += [expand(a) for a in profile["fixed_args"]] + arguments
        runtimes = request.get("executables", {})
        if type(runtimes) is not dict or set(runtimes) != set(profile.get("executable_args", {})):
            raise ValueError("Provide exactly the external executables declared by this native profile")
        executables = []
        for name, value in runtimes.items():
            executable = Path(value)
            if not executable.is_absolute() or not executable.is_file() or not os.access(executable, os.X_OK):
                raise ValueError("External runtime must be an absolute executable")
            argv += [profile["executable_args"][name], str(executable)]
            executables.append({"name": name, "path": str(executable), "sha256": _digest_file(executable)})
        if profile["output"]:
            flag = profile["output"]["flag"]
            value = str(output / profile["output"]["path"])
            argv += [flag + value] if flag.endswith("=") else [flag, value]
        python_paths = [workspace, workspace / "src", *[workspace / p for p in profile.get("python_paths", [])],
                        Path(__file__).resolve().parents[2]]
        environment = {k: expand(v) for k, v in profile.get("environment", {}).items()}
        environment.update(PYTHONPATH=os.pathsep.join(map(str, python_paths)),
                           PATH=str(python.parent) + os.pathsep + os.environ.get("PATH", ""),
                           PYTHONDONTWRITEBYTECODE="1")
        integration_sources = [Path(__file__).resolve(), Path(__file__).with_name("runtime.py").resolve()]
        if invocation["kind"] == "driver":
            integration_sources += sorted(Path(__file__).with_name("drivers").glob("*.py"))
        input_paths += [str(path) for path in integration_sources]
        return {"argv": argv, "cwd": str(cwd), "env": environment, "workspace_copy": True,
                "workspace_root": str(workspace), "workspace_inputs": inputs, "workspace_overlays": overlays,
                "workspace_remove_files": profile.get("remove_files", []), "input_paths": input_paths,
                "expected_artifacts": profile["result_globs"], "engine": self.recipe["id"], "profile": profile["id"],
                "evaluation": profile["evaluation"], "source_evidence": self.recipe["evidence"],
                "executables": executables,
                "recipe_sha256": hashlib.sha256(json.dumps(self.recipe, sort_keys=True).encode()).hexdigest()}

    def read_results(self, output_dir):
        from .runtime import _digest_file
        output = Path(output_dir).resolve()
        result = {"schema": "arena.native-result/1", "framework": self.id, "engine": self.recipe["id"],
                  "canonical_evaluation": False, "status": "missing", "native": {}, "artifacts": [],
                  "warnings": ["Native artifact evidence; no cross-framework score or validity is inferred."]}
        metadata = output / ".arena"
        if metadata.is_symlink():
            return result
        def read_metadata(name):
            path = metadata / name
            if not path.is_file() or path.is_symlink() or path.stat().st_size > 4 * 1024 * 1024:
                raise ValueError("Missing or invalid native metadata")
            return json.loads(path.read_text())
        try:
            plan = read_metadata("plan.json")
            baseline = read_metadata("artifact-baseline.json")
            if (plan.get("command", {}).get("engine") != self.recipe["id"]
                    or plan.get("source", {}).get("commit") != self.commit
                    or plan.get("command", {}).get("recipe_sha256") != hashlib.sha256(json.dumps(self.recipe, sort_keys=True).encode()).hexdigest()
                    or baseline.get("schema") != "arena.native-artifact-baseline/1"
                    or type(baseline.get("files")) is not dict):
                raise ValueError("Native evidence does not match this engine and source")
        except (ValueError, OSError, AttributeError):
            result["warnings"].append("Matching run provenance and a pre-run artifact baseline are required")
            return result
        profile_id = plan.get("command", {}).get("profile")
        profile = next((p for p in self.recipe["profiles"] if p["id"] == profile_id), None)
        if profile is None:
            result["warnings"].append("No matching recorded native profile")
            return result
        result["native"] = {"profile": profile_id, "evaluation": profile["evaluation"]}
        workspace = output / "workspace" / self.recipe["id"]
        total = 0
        try:
            for path in artifact_files(output, workspace, profile["result_globs"]):
                size = path.stat().st_size
                if len(result["artifacts"]) >= 64 or size > 64 * 1024 * 1024 or total + size > 256 * 1024 * 1024:
                    raise ValueError("Native artifact inventory reached its size limit")
                total += size
                before = path.stat()
                digest = _digest_file(path)
                after = path.stat()
                if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
                    result["status"] = "partial"
                    result["warnings"].append("Native artifact changed during observation")
                    continue
                relative_path = str(path.relative_to(output))
                if baseline["files"].get(relative_path) == digest:
                    continue
                result["artifacts"].append({"path": relative_path, "bytes": size, "sha256": digest})
        except (ValueError, OSError):
            result["status"] = "partial"
            result["warnings"].append("Native artifact inventory is incomplete or exceeded its observation limit")
        if result["artifacts"] and result["status"] != "partial":
            result["status"] = "recorded"
        return result
