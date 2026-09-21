from pathlib import Path
import json
import os
import re
from urllib.parse import urlsplit

from .source_assets import records as source_asset_records

SCHEMA_VERSION = "1.0"
SUITE_PROTOCOLS = ("original", "recreated_verified", "recreated", "unsupported")
SUITE_RUNNABLE = ("original", "recreated_verified", "recreated")


def suite_runnable(task):
    """True when the task directory carries an executable suite evaluator."""
    suite = (task.get("execution") or {}).get("suite") or {}
    return suite.get("protocol") in SUITE_RUNNABLE


def repository_root():
    configured = os.environ.get("AUTORESEARCH_TASKS_ROOT")
    roots = ([Path(configured)] if configured else []) + [Path.cwd(), *Path(__file__).resolve().parents]
    for root in roots:
        if (root / "catalog" / "papers.json").is_file() and (root / "suite").is_dir():
            return root.resolve()
    raise ValueError("Run from the repository or set AUTORESEARCH_TASKS_ROOT to its absolute path.")


def tasks(root):
    return [json.loads(p.read_text()) for p in sorted((root / "suite").glob("*/task.json"))]


def get_task(root, task_id):
    if not isinstance(task_id, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]*", task_id):
        raise ValueError("Invalid task id")
    path = root / "suite" / task_id / "task.json"
    if not path.is_file():
        canonical = duplicate_canonical(root, task_id)
        if canonical:
            raise ValueError(f"{task_id} was merged into {canonical} (same problem); use that id, with --paper <paper> for its upstream route")
        raise ValueError(f"Unknown task: {task_id}")
    return json.loads(path.read_text())


def duplicate_canonical(root, task_id):
    """The canonical task id for a merged duplicate id (catalog/duplicates.json), or None."""
    path = root / "catalog" / "duplicates.json"
    if not path.is_file():
        return None
    try:
        return (json.loads(path.read_text()).get("canonical") or {}).get(task_id)
    except ValueError:
        return None


def merged_view(task, paper=None):
    """The task as one of its merged papers recorded it (upstream route, requirements), or the task itself."""
    if not paper or paper == task["paper_ids"][0]:
        return task
    for m in task.get("merged_from") or []:
        if paper in m["paper_ids"]:
            view = dict(task)
            view.update({k: m[k] for k in ("id", "kind", "sources", "requirements", "evaluation", "limitations", "validation") if k in m})
            view["execution"] = {**m["execution"], "suite": task["execution"].get("suite")}
            view["paper_ids"] = list(m["paper_ids"])
            return view
    raise ValueError(f"{task['id']} has no merged record for paper {paper}; papers: {', '.join(task['paper_ids'])}")


def validate(root):
    """Validate untrusted JSON shapes before accessing nested values.

    Invalid files and individual records are reported while the remaining
    inventory is checked. Validation never follows a manifest-supplied task ID
    outside the directory that actually contains its manifest.
    """
    root = Path(root)
    problems = []
    try:
        external_assets = {entry["path"]: entry for entry in source_asset_records(root)}
    except (OSError, ValueError) as error:
        problems.append(str(error))
        external_assets = {}

    def read(path):
        try:
            return json.loads(path.read_text())
        except (OSError, UnicodeError, ValueError) as error:
            problems.append(f"{path.relative_to(root)}: cannot read JSON: {error}")
            return None

    def text(value):
        return isinstance(value, str) and bool(value.strip())

    def matches(pattern, value):
        return isinstance(value, str) and re.fullmatch(pattern, value) is not None

    def https(value):
        return isinstance(value, str) and value.startswith("https://") and len(value) > 8

    def relative(value, label, allow_empty=False):
        if not isinstance(value, str) or "\x00" in value or (not value and not allow_empty):
            problems.append(f"{label} must be a relative path string")
            return False
        path = Path(value)
        if path.is_absolute() or ".." in path.parts:
            problems.append(f"{label} escapes checkout")
            return False
        return True

    def string_list(value, label, nonempty=False):
        valid = isinstance(value, list) and all(isinstance(x, str) for x in value)
        if not valid or (nonempty and not value):
            problems.append(f"{label} must be a {'nonempty ' if nonempty else ''}string list")
            return []
        return value

    raw_papers = read(root / "catalog" / "papers.json")
    if not isinstance(raw_papers, list):
        problems.append("catalog/papers.json: expected a list")
        raw_papers = []
    papers = []
    paper_ids = set()
    for index, paper in enumerate(raw_papers):
        if not isinstance(paper, dict) or not text(paper.get("id")):
            problems.append(f"catalog/papers.json[{index}]: paper must be an object with a string id")
            continue
        pid = paper["id"]
        if pid in paper_ids:
            problems.append(f"Duplicate paper: {pid}")
        paper_ids.add(pid)
        papers.append(paper)
    coverage = {pid: 0 for pid in paper_ids}
    paths = sorted((root / "suite").glob("*/task.json"))
    records = []
    indexed = {}
    task_papers = {}
    for path in paths:
        t = read(path)
        if not isinstance(t, dict):
            problems.append(f"{path.relative_to(root)}: task manifest must be an object")
            continue
        records.append(t)
        raw_id = t.get("id")
        valid_id = matches(r"[a-z0-9][a-z0-9-]*", raw_id)
        tid = raw_id if valid_id else path.parent.name
        for key in ("schema_version", "id", "name", "description", "paper_ids", "kind", "status", "sources", "requirements", "evaluation", "execution", "limitations", "validation"):
            if key not in t:
                problems.append(f"{tid}: missing {key}")
        if not valid_id:
            problems.append(f"{tid}: invalid id")
        else:
            if raw_id in indexed:
                problems.append(f"Duplicate task: {raw_id}")
            indexed[raw_id] = t
            if path.parent.name != raw_id:
                problems.append(f"{tid}: id differs from task directory")
        if t.get("schema_version") != SCHEMA_VERSION:
            problems.append(f"{tid}: unsupported schema")
        kind = t.get("kind")
        if not isinstance(kind, str) or kind not in ("native", "upstream", "specification"):
            problems.append(f"{tid}: invalid kind")
            kind = None
        suite = (t.get("execution") or {}).get("suite") if isinstance(t.get("execution"), dict) else None
        if suite is not None and not isinstance(suite, dict):
            problems.append(f"{tid}: execution.suite must be an object")
            suite = None
        runnable = bool(suite) and suite.get("protocol") in SUITE_RUNNABLE
        expected_status = "ready" if runnable else {"native": "ready", "upstream": "requires_setup", "specification": "blocked"}.get(kind)
        declared_status = (t.get("execution") or {}).get("declared_status") if isinstance(t.get("execution"), dict) else None
        if declared_status is not None:
            if declared_status not in ("ready", "requires_setup", "blocked"):
                problems.append(f"{tid}: invalid declared readiness status")
            else:
                expected_status = declared_status
        if t.get("status") != expected_status:
            problems.append(f"{tid}: status inconsistent with suite protocol and implementation kind")
        if suite:
            if suite.get("protocol") not in SUITE_PROTOCOLS:
                problems.append(f"{tid}: invalid suite protocol")
            for field in ("evaluator", "initial_program"):
                if not text(suite.get(field)) or "/" in suite[field] or suite[field].startswith("."):
                    problems.append(f"{tid}: suite {field} must be a file name inside the task directory")
                elif not (path.parent / suite[field]).is_file():
                    asset_relative = str((path.parent / suite[field]).relative_to(root))
                    declared_asset = external_assets.get(asset_relative, {})
                    if tid not in declared_asset.get("task_ids", []):
                        problems.append(f"{tid}: suite {field} file is missing")
            if not isinstance(suite.get("requires", []), list):
                problems.append(f"{tid}: suite requires must be a list")
        for field in ("name", "description"):
            if not text(t.get(field)):
                problems.append(f"{tid}: {field} must be a nonempty string")
        pids = string_list(t.get("paper_ids"), f"{tid}: paper_ids", nonempty=True)
        if len(pids) != len(set(pids)):
            problems.append(f"{tid}: duplicate paper_ids")
        if valid_id:
            task_papers[raw_id] = pids
        for pid in pids:
            if pid not in paper_ids:
                problems.append(f"{tid}: unknown paper {pid}")
            else:
                coverage[pid] += 1
        string_list(t.get("limitations"), f"{tid}: limitations")
        relevance = t.get("science_relevance")
        labels = t.get("labels") if isinstance(t.get("labels"), dict) else {}
        importance = labels.get("important_to_science")
        if importance is not None and type(importance) is not bool:
            problems.append(f"{tid}: important_to_science must be boolean")
        if relevance is not None:
            if not isinstance(relevance, dict):
                problems.append(f"{tid}: science_relevance must be an object")
                relevance = {}
            if relevance.get("status") not in ("supported", "unreviewed"):
                problems.append(f"{tid}: invalid science_relevance status")
            if not text(relevance.get("definition")):
                problems.append(f"{tid}: science_relevance needs a definition")
            citations = relevance.get("papers")
            if not isinstance(citations, list):
                problems.append(f"{tid}: science_relevance papers must be a list")
                citations = []
            for citation in citations:
                if not isinstance(citation, dict) or not all(text(citation.get(k)) for k in ("title", "url", "task_relation")):
                    problems.append(f"{tid}: science paper needs title, URL and task relation")
                    continue
                try:
                    url = urlsplit(citation["url"])
                    valid_url = url.scheme in ("http", "https") and bool(url.netloc)
                except ValueError:
                    valid_url = False
                if not valid_url:
                    problems.append(f"{tid}: science paper URL must be HTTP(S)")
            supported = relevance.get("status") == "supported"
            if supported and not citations:
                problems.append(f"{tid}: supported science relevance needs a solving paper")
            if supported:
                if relevance.get("criterion") != "primary_research_goal":
                    problems.append(f"{tid}: scientific importance requires the primary research goal criterion")
                if not all(text(relevance.get(k)) for k in ("scientific_problem", "importance_rationale")):
                    problems.append(f"{tid}: scientific importance needs the scientific problem and why it matters")
                if any(not isinstance(citation, dict) or not text(citation.get("primary_goal"))
                       or citation.get("evidence_role") != "primary_problem" for citation in citations):
                    problems.append(f"{tid}: science papers must primarily solve the underlying problem, not evaluate a framework")
            if importance is not supported:
                problems.append(f"{tid}: important_to_science conflicts with science_relevance")
        elif importance is True:
            problems.append(f"{tid}: important_to_science needs science_relevance paper evidence")
        objects = {}
        for field in ("requirements", "evaluation", "execution", "validation"):
            value = t.get(field)
            if not isinstance(value, dict):
                problems.append(f"{tid}: {field} must be an object")
                value = {}
            objects[field] = value
        for filename in ("task.json", "README.txt", "evaluator.py", "problem.json", "config.yaml"):
            if not (path.parent / filename).is_file():
                problems.append(f"{tid}: missing {filename}")
        evaluation = objects["evaluation"]
        if evaluation.get("direction") not in ("maximize", "minimize", None):
            problems.append(f"{tid}: invalid objective direction")
        if evaluation.get("metric") is not None and not isinstance(evaluation.get("metric"), str):
            problems.append(f"{tid}: evaluation metric must be a string or null")
        if evaluation.get("protocol") not in ("portable_reference", "upstream", "specified_only", "paper_reimplementation"):
            problems.append(f"{tid}: invalid evaluation protocol")
        for field in ("metric", "direction", "protocol"):
            if field not in evaluation:
                problems.append(f"{tid}: evaluation missing {field}")
        validation = objects["validation"]
        if not text(validation.get("level")):
            problems.append(f"{tid}: validation level must be a nonempty string")
        if not isinstance(validation.get("upstream_reproduction"), bool):
            problems.append(f"{tid}: validation upstream_reproduction must be boolean")
        ex = objects["execution"]
        commands = ex.get("commands", [])
        if not isinstance(commands, list):
            problems.append(f"{tid}: commands must be a list")
            commands = []
        for command in commands:
            if not isinstance(command, dict):
                problems.append(f"{tid}: command must be an object")
                continue
            argv = command.get("argv")
            if not isinstance(argv, list) or not argv or not all(text(x) for x in argv):
                problems.append(f"{tid}: command argv must be a nonempty list of strings")
            if not https(command.get("source_url")):
                problems.append(f"{tid}: command needs HTTPS source provenance")
            relative(command.get("cwd", "."), f"{tid}: command cwd")
        adapter = ex.get("evaluator_adapter")
        if adapter is not None:
            if not isinstance(adapter, dict):
                problems.append(f"{tid}: evaluator_adapter must be an object or null")
                adapter = None
            else:
                relative(adapter.get("evaluator_path"), f"{tid}: adapter evaluator_path")
                for scope_field in ("evaluator_scope", "baseline_scope"):
                    if scope_field in adapter and adapter[scope_field] not in ("upstream", "repository"):
                        problems.append(f"{tid}: adapter {scope_field} must be upstream or repository")
                assets = adapter.get("repository_files", {})
                if not isinstance(assets, dict):
                    problems.append(f"{tid}: adapter repository_files must be an object")
                else:
                    for name, digest in assets.items():
                        relative(name, f"{tid}: repository asset")
                        if not matches(r"[0-9a-f]{64}", digest):
                            problems.append(f"{tid}: repository asset lacks SHA256: {name}")
                for field in ("baseline_path", "cwd"):
                    if field in adapter and adapter[field] is not None:
                        relative(adapter[field], f"{tid}: adapter {field}")
                for field in ("callable", "candidate_keyword", "output_keyword", "score_key", "status_key", "validity_key", "error_key"):
                    if field in adapter and adapter[field] is not None and not text(adapter[field]):
                        problems.append(f"{tid}: adapter {field} must be a nonempty string")
                if "import_module" in adapter and not matches(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*", adapter["import_module"]):
                    problems.append(f"{tid}: adapter import_module must be a dotted module name")
                for field in ("candidate_argument", "output_argument"):
                    if field in adapter and adapter[field] not in ("positional", "keyword"):
                        problems.append(f"{tid}: adapter {field} must be positional or keyword")
                if adapter.get("candidate_argument") == "keyword" and not text(adapter.get("candidate_keyword")):
                    problems.append(f"{tid}: adapter needs candidate_keyword")
                if adapter.get("output_argument") == "keyword" and not text(adapter.get("output_keyword")):
                    problems.append(f"{tid}: adapter needs output_keyword")
                if "kwargs" in adapter and not isinstance(adapter["kwargs"], dict):
                    problems.append(f"{tid}: adapter kwargs must be an object")
                environment = adapter.get("environment", {})
                if not isinstance(environment, dict) or not all(text(k) and isinstance(v, str) and "\x00" not in k + v and "=" not in k for k, v in environment.items()):
                    problems.append(f"{tid}: adapter environment must map valid variable names to strings")
        sources = t.get("sources")
        if not isinstance(sources, list) or not sources:
            problems.append(f"{tid}: sources must be a nonempty list")
            sources = []
        for source in sources:
            if not isinstance(source, dict):
                problems.append(f"{tid}: source must be an object")
                continue
            if not https(source.get("url")):
                problems.append(f"{tid}: invalid source URL")
            if source.get("type") not in ("paper", "repository", "corpus", "benchmark", "archive"):
                problems.append(f"{tid}: invalid source type")
        archive = ex.get("archive_source")
        archive_pinned = False
        if archive is not None:
            if not isinstance(archive, dict):
                problems.append(f"{tid}: archive_source must be an object")
            else:
                archive_pinned = True
                if not https(archive.get("url")):
                    problems.append(f"{tid}: archive_source needs an HTTPS URL")
                    archive_pinned = False
                if not matches(r"[0-9a-f]{64}", archive.get("sha256")):
                    problems.append(f"{tid}: archive_source SHA256 must be pinned")
                    archive_pinned = False
                if not relative(archive.get("strip_prefix"), f"{tid}: archive_source strip_prefix", allow_empty=True):
                    archive_pinned = False
                if not text(archive.get("license")):
                    problems.append(f"{tid}: archive_source license must be a nonempty string")
                    archive_pinned = False
        if kind == "native" and not text(ex.get("native_kind")):
            problems.append(f"{tid}: incomplete native implementation")
        if kind == "upstream":
            git_pinned = https(ex.get("repository")) and matches(r"[0-9a-f]{40}", ex.get("commit"))
            if not git_pinned and not archive_pinned:
                problems.append(f"{tid}: upstream requires a pinned git repository/commit or pinned archive_source")
            if not commands and not adapter:
                problems.append(f"{tid}: upstream entry point not specified")
    for pid, count in coverage.items():
        if not count:
            problems.append(f"{pid}: no task or explicit coverage gap")
    catalog_path = root / "catalog" / "tasks.json"
    if catalog_path.exists():
        catalog = read(catalog_path)
        expected = {}
        if not isinstance(catalog, list):
            problems.append("catalog/tasks.json: expected a list")
        else:
            for index, entry in enumerate(catalog):
                if not isinstance(entry, dict) or not matches(r"[a-z0-9][a-z0-9-]*", entry.get("id")):
                    problems.append(f"catalog/tasks.json[{index}]: invalid task record")
                    continue
                if entry["id"] in expected:
                    problems.append(f"catalog/tasks.json: duplicate task {entry['id']}")
                expected[entry["id"]] = entry
            if expected != indexed:
                problems.append("catalog/tasks.json differs from per-task manifests; rebuild catalog")
    for paper in papers:
        pid = paper["id"]
        declared = string_list(paper.get("task_ids"), f"{pid}: paper task_ids")
        expected = {tid for tid, pids in task_papers.items() if pid in pids and not tid.startswith("reference-")}
        if set(declared) != expected:
            problems.append(f"{pid}: paper task_ids differ from manifest coverage")
    return {"schema_version": SCHEMA_VERSION, "valid": not problems,
            "paper_count": sum(not p.get('supplemental') for p in papers),
            "source_collection_count": len(raw_papers), "task_count": len(paths), "errors": problems}
