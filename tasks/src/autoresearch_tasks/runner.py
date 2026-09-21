
from arena_task_paths import cache_path
import datetime
import hashlib
import json
import math
import os
import signal
import re
from pathlib import Path
import subprocess
import sys
import tempfile
import time

from .archive_source import archive_path, setup_archive, verify_archive_checkout
from .source_assets import require_prepared


def run_process(argv, *, input=None, stdout=None, stderr=None, timeout=None, cwd=None, env=None):
    """Terminate the POSIX process group when a candidate/evaluator times out."""
    process=subprocess.Popen(argv,stdin=subprocess.PIPE if input is not None else None,
        stdout=stdout,stderr=stderr,cwd=cwd,env=env,start_new_session=(os.name=="posix"))
    try:
        process.communicate(input=input,timeout=timeout)
    except subprocess.TimeoutExpired:
        if os.name=="posix":
            try:os.killpg(process.pid,signal.SIGKILL)
            except ProcessLookupError:pass
        else:process.kill()
        process.communicate()
        raise
    return subprocess.CompletedProcess(argv,process.returncode)


def timestamp(): return datetime.datetime.now(datetime.timezone.utc).isoformat()

def checkout_path(root, ex):
    if ex.get("archive_source"):
        return archive_path(root, ex["archive_source"])
    slug=ex["repository"].rstrip("/").removesuffix(".git").split("github.com/")[-1].replace("/","--")
    return cache_path("upstreams") / slug / ex["commit"]


def source_metadata(ex):
    if ex.get("archive_source"):
        return {"source_type":"archive", "archive_source":ex["archive_source"],
                "repository":None, "commit":None}
    return {"source_type":"git", "repository":ex.get("repository"), "commit":ex.get("commit")}


def verify_source_checkout(target, ex):
    if ex.get("archive_source"):
        return verify_archive_checkout(target, ex["archive_source"])
    return verify_checkout(target, ex["commit"])


def setup_upstream(root, task):
    ex=task["execution"]
    if ex.get("archive_source"):
        result=setup_archive(root, ex["archive_source"])
        result.update(next_steps=ex.get("setup_instructions",[]), setup_steps=ex.get("setup_steps",[]))
        return result
    if not ex.get("repository") or not ex.get("commit"):
        raise ValueError("No verified, pinned implementation is available. See this task's limitations.")
    target=checkout_path(root,ex)
    if target.exists():
        actual=subprocess.check_output(["git","-C",str(target),"rev-parse","HEAD"],text=True).strip()
        if actual != ex["commit"]: raise ValueError("Cached repository is at a different commit")
        dirty=subprocess.check_output(["git","-C",str(target),"status","--porcelain"],text=True)
        return {"status":"ready","checkout":str(target),"commit":actual,"modified":bool(dirty),"dependencies_installed":False,"next_steps":ex.get("setup_instructions",[]),"setup_steps":ex.get("setup_steps",[])}
    target.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=target.parent,prefix="fetch-") as temp:
        subprocess.run(["git","init","--quiet",temp],check=True)
        subprocess.run(["git","-C",temp,"remote","add","origin",ex["repository"]],check=True)
        subprocess.run(["git","-C",temp,"fetch","--depth","1","origin",ex["commit"]],check=True)
        subprocess.run(["git","-C",temp,"checkout","--detach","FETCH_HEAD"],check=True)
        actual=subprocess.check_output(["git","-C",temp,"rev-parse","HEAD"],text=True).strip()
        if actual!=ex["commit"]: raise ValueError("Fetched commit did not match manifest")
        Path(temp).rename(target)
    return {"status":"source_fetched","checkout":str(target),"commit":actual,"dependencies_installed":False,
            "next_steps":ex.get("setup_instructions",[]),"setup_steps":ex.get("setup_steps",[])}


def run_upstream(root, task, command_index, execute, timeout, python=None):
    ex=task["execution"]
    commands=ex.get("commands",[])
    if not commands:
        raise ValueError("No verified execution entry point is available. Read task README and limitations.")
    if command_index<0 or command_index>=len(commands): raise ValueError("Command index out of range")
    command=commands[command_index]
    target=checkout_path(root,ex)
    relative=Path(command.get("cwd","."))
    cwd=(target/relative).resolve()
    if not cwd.is_relative_to(target.resolve()): raise ValueError("Command cwd escapes upstream checkout")
    argv=command.get("argv")
    if not argv or not all(isinstance(x,str) for x in argv): raise ValueError("Command is documentation-only; no vetted argv")
    source_argv=argv[:]
    environment=None
    if python:
        python=Path(python).resolve()
        if not python.is_file():raise ValueError("Upstream Python executable does not exist")
        environment={**os.environ,"PATH":str(python.parent)+os.pathsep+os.environ.get("PATH","")}
        if re.fullmatch(r"python(?:[0-9]+(?:\.[0-9]+)*)?",Path(argv[0]).name):argv=[str(python),*argv[1:]]
    result={"schema_version":"1.0","task_id":task["id"],"mode":"upstream",**source_metadata(ex),"source_command":source_argv,
        "command":argv,"cwd":str(cwd),"score":None,"valid":None,
        "metric":task["evaluation"].get("metric"),"direction":task["evaluation"].get("direction"),
        "evaluation_note":"Exit code only. Use the upstream evaluator's reports to establish benchmark score and validity."}
    if not execute:
        result.update(status="planned",next_step="Use setup to fetch sources, follow setup instructions, then run with --execute.")
        return result
    if not target.is_dir(): raise ValueError("Run setup for this task first")
    if timeout<=0 or not math.isfinite(timeout): raise ValueError("Timeout must be finite and positive")
    result.update(verify_source_checkout(target,ex))
    logdir=cache_path("runs")/(task["id"]+"-"+datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    logdir.mkdir(parents=True)
    result.update(started_at=timestamp(),logs=str(logdir))
    try:
        with (logdir/"stdout.log").open("wb") as stdout,(logdir/"stderr.log").open("wb") as stderr:
            completed=run_process(argv,cwd=cwd,stdout=stdout,stderr=stderr,timeout=timeout,env=environment)
        result.update(status="completed" if completed.returncode==0 else "failed",exit_code=completed.returncode)
    except subprocess.TimeoutExpired:
        result.update(status="timeout",exit_code=None)
    result["finished_at"]=timestamp()
    (logdir/"result.json").write_text(json.dumps(result,indent=2)+"\n")
    return result


def verify_checkout(target, expected):
    actual=subprocess.check_output(["git","-C",str(target),"rev-parse","HEAD"],text=True).strip()
    if actual!=expected:raise ValueError("Upstream checkout HEAD differs from pinned manifest commit")
    changes=subprocess.check_output(["git","-C",str(target),"status","--porcelain"],text=True)
    diff=subprocess.check_output(["git","-C",str(target),"diff","HEAD","--binary"])
    return {"actual_commit":actual,"working_tree_modified":bool(changes),"tracked_diff_sha256":hashlib.sha256(diff).hexdigest()}


def nested(data, key):
    for part in key.split("."):
        if not isinstance(data,dict) or part not in data:return None
        data=data[part]
    return data


def adapter_file(root, checkout, adapter, role):
    """Resolve an original or explicitly attributed repository-owned adapter asset."""
    if role not in ("evaluator", "baseline"):
        raise ValueError("Unknown adapter asset role")
    scope = adapter.get(role + "_scope", "upstream")
    if scope not in ("upstream", "repository"):
        raise ValueError("Adapter asset scope must be upstream or repository")
    base = Path(root if scope == "repository" else checkout).resolve()
    relative = adapter.get(role + "_path")
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute() or ".." in Path(relative).parts:
        raise ValueError("Adapter asset must be a contained relative path")
    path = (base / relative).resolve()
    if not path.is_relative_to(base):
        raise ValueError("Adapter asset path escapes its declared scope")
    return path


def repository_assets(root, adapter):
    """Verify separately pinned helper/data files for an attributed local adapter."""
    files = adapter.get("repository_files", {})
    if not isinstance(files, dict):
        raise ValueError("repository_files must map relative paths to SHA256 digests")
    actual = {}
    for relative, expected in files.items():
        if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise ValueError("Repository asset lacks an immutable SHA256")
        path = adapter_file(root, root, {"evaluator_scope":"repository","evaluator_path":relative}, "evaluator")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != expected:
            raise ValueError("Repository asset differs from its pinned hash: " + relative)
        actual[relative] = digest
    return actual


def adapter_environment(root, checkout, adapter, base=None):
    environment = adapter.get("environment", {})
    if not isinstance(environment, dict) or not all(isinstance(k,str) and isinstance(v,str) for k,v in environment.items()):
        raise ValueError("Adapter environment must be a string map")
    substitutions = {"{repository}":str(Path(root).resolve()), "{checkout}":str(Path(checkout).resolve()),
                     "{PATH}":(base if base is not None else os.environ).get("PATH", "")}
    result = {}
    for key, value in environment.items():
        for marker, replacement in substitutions.items():
            value = value.replace(marker, replacement)
        result[key] = value
    return result


def _bridge(root, checkout, adapter, candidate, python, timeout, result, environment):
    """Run an evaluator through bridge.py in its own interpreter and fold the metrics into ``result``."""
    payload={"repository_root":str(Path(root).resolve()),"checkout":str(Path(checkout).resolve()),"candidate":str(candidate),"adapter":adapter,
             "environment":environment}
    try:
        with tempfile.TemporaryFile() as stdout,tempfile.TemporaryFile() as stderr:
            run=run_process([str(python or sys.executable),str(Path(__file__).with_name("bridge.py"))],input=json.dumps(payload).encode(),stdout=stdout,stderr=stderr,timeout=timeout)
            stdout.seek(0);stderr.seek(0);raw=stdout.read(4_194_305);diagnostic=stderr.read(16384).decode(errors="replace")
        if run.returncode:raise ValueError(f"Evaluator exited {run.returncode}: {diagnostic[-4000:]}")
        if len(raw)>4_194_304:raise ValueError("Evaluator JSON exceeds 4 MiB")
        metrics=json.loads(raw,parse_constant=lambda x: (_ for _ in ()).throw(ValueError(f"Nonfinite JSON: {x}")))
        result["upstream_result"]=metrics
        rejection=str(nested(metrics,adapter["error_key"])) if adapter.get("error_key") and nested(metrics,adapter["error_key"]) else None
        if adapter.get("score_key"):
            value=nested(metrics,adapter["score_key"])
            if value is None:raise ValueError(rejection or ("Configured score key was missing or null: "+adapter["score_key"]))
            if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
                raise ValueError("Score must be a finite number")
            result["score"]=value
        if adapter.get("validity_key"):
            value=nested(metrics,adapter["validity_key"])
            if isinstance(value,bool):result["valid"]=value
            elif value in (0,1):result["valid"]=bool(value)
        if adapter.get("status_key"):
            status=nested(metrics,adapter["status_key"])
            result["valid"]=status==adapter.get("status_success_value","success")
        if adapter.get("error_key") and nested(metrics,adapter["error_key"]):
            result["valid"]=False
            result["error"]=str(nested(metrics,adapter["error_key"]))
        result["status"]="failed" if result["valid"] is False else "completed"
        if diagnostic:result["diagnostic_tail"]=diagnostic[-4000:]
    except subprocess.TimeoutExpired:result.update(status="timeout",error=f"Evaluator exceeded {timeout} seconds")
    except (ValueError,TypeError,KeyError,OSError) as error:result.update(error=str(error))
    result["finished_at"]=timestamp()
    return result


def suite_directory(root, task):
    directory=(Path(root).resolve()/"suite"/task["id"]).resolve()
    if not directory.is_relative_to(Path(root).resolve()/"suite") or not directory.is_dir():raise ValueError("Suite directory is missing for this task")
    return directory


def suite_adapter(root, task):
    """Translate the task's suite entry into the bridge adapter vocabulary."""
    suite=task["execution"].get("suite") or {}
    if suite.get("protocol") not in ("original","recreated_verified","recreated"):
        raise ValueError("This task has no executable suite evaluator ("+str(suite.get("protocol") or "none")+"): "+str(suite.get("unsupported_reason") or "see its README"))
    lib=str((Path(root).resolve()/"suite"/"_lib"))
    environment={k:re.sub(r"\$\{([A-Z_][A-Z0-9_]*)\}",lambda m:os.environ.get(m.group(1),""),str(v).replace("{suite_lib}",lib)) for k,v in (suite.get("env") or {}).items()}
    environment["PYTHONPATH"]=os.pathsep.join([lib+"/vendor/algotune",lib]+([os.environ["PYTHONPATH"]] if os.environ.get("PYTHONPATH") else []))
    environment.setdefault("PYTHONDONTWRITEBYTECODE","1");environment.setdefault("MPLBACKEND","Agg")
    if "vendor:algotune" in suite.get("requires", []):
        environment.setdefault("ALGOTUNE_HF_CACHE_DIR", str(cache_path("algotune", "huggingface")))
        environment.setdefault("DATA_DIR", str(cache_path("algotune", "data")))
    adapter={"evaluator_scope":"repository","evaluator_path":"suite/"+task["id"]+"/"+suite.get("evaluator","evaluator.py"),
             "baseline_scope":"repository","baseline_path":"suite/"+task["id"]+"/"+suite["initial_program"],
             "callable":suite.get("callable") or "evaluate","candidate_argument":"positional","cwd":".",
             "score_key":suite.get("score_key") or "score","error_key":suite.get("error_key") or "error","environment":environment}
    if suite.get("validity_key"):adapter["validity_key"]=suite["validity_key"]
    return adapter,environment


def evaluate_suite(root, task, candidate=None, python=None, timeout=300):
    """Evaluate a candidate with the task's own suite/<id>/evaluator.py (the default route)."""
    if timeout<=0 or not math.isfinite(timeout):raise ValueError("Timeout must be finite and positive")
    require_prepared(root, task["id"])
    directory=suite_directory(root,task)
    adapter,environment=suite_adapter(root,task)
    candidate=(Path(candidate) if candidate else directory/task["execution"]["suite"]["initial_program"]).resolve()
    if not candidate.is_file():raise ValueError(f"Candidate does not exist: {candidate}")
    evaluator=directory/adapter["evaluator_path"].rsplit("/",1)[1]
    suite=task["execution"]["suite"]
    result={"schema_version":"1.0","task_id":task["id"],"mode":"suite","status":"failed","valid":None,"score":None,
            "protocol":suite.get("protocol"),"family":suite.get("family"),"metric":task["evaluation"].get("metric"),"direction":task["evaluation"].get("direction"),
            "candidate_sha256":hashlib.sha256(candidate.read_bytes()).hexdigest(),"evaluator_sha256":hashlib.sha256(evaluator.read_bytes()).hexdigest(),
            "evaluator_scope":"repository","implementation_label":"suite_"+str(suite.get("protocol")),"started_at":timestamp()}
    return _bridge(root,directory,adapter,candidate,python,timeout,result,environment)


def evaluate_upstream(root, task, candidate=None, python=None, timeout=300):
    """Evaluate a candidate with the pinned upstream evaluator adapter (the provenance route)."""
    ex=task["execution"];adapter=ex.get("evaluator_adapter")
    if not adapter:raise ValueError("No direct evaluator adapter. Use run to inspect source-verified upstream commands.")
    target=checkout_path(root,ex)
    if not target.is_dir():raise ValueError("Run setup for this task first")
    if timeout<=0 or not math.isfinite(timeout):raise ValueError("Timeout must be finite and positive")
    provenance=verify_source_checkout(target,ex)
    if candidate is None:
        baseline=adapter.get("baseline_path")
        if not baseline:raise ValueError("Supply --candidate; no verified upstream seed available")
        candidate=adapter_file(root,target,adapter,"baseline")
    candidate=candidate.resolve()
    if not candidate.is_file():raise ValueError(f"Candidate does not exist: {candidate}")
    evaluator=adapter_file(root,target,adapter,"evaluator")
    asset_hashes=repository_assets(root,adapter)
    result={"schema_version":"1.0","task_id":task["id"],"mode":"upstream","status":"failed","valid":None,"score":None,
            **source_metadata(ex),"metric":task["evaluation"].get("metric"),"direction":task["evaluation"].get("direction"),
            "candidate_sha256":hashlib.sha256(candidate.read_bytes()).hexdigest(),"evaluator_sha256":hashlib.sha256(evaluator.read_bytes()).hexdigest(),
            "evaluator_scope":adapter.get("evaluator_scope","upstream"),
            "implementation_label":adapter.get("implementation_label","original_upstream"),
            "repository_asset_sha256":asset_hashes,
            "started_at":timestamp(),**provenance}
    return _bridge(root,target,adapter,candidate,python,timeout,result,adapter_environment(root,target,adapter))
