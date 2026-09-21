"""Load a pinned upstream evaluator in its own environment and emit JSON."""
import asyncio
import contextlib
import importlib
import importlib.util
import inspect
import json
import os
from pathlib import Path
import sys
import tempfile


def plain(value):
    if isinstance(value,dict): return {str(k):plain(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)): return [plain(v) for v in value]
    if hasattr(value,"to_dict"): return plain(value.to_dict())
    if hasattr(value,"metrics"):
        result={"metrics":plain(value.metrics)}
        if hasattr(value,"artifacts"): result["artifacts"]=plain(value.artifacts)
        return result
    if hasattr(value,"tolist"): return plain(value.tolist())
    if hasattr(value,"item"): return plain(value.item())
    return value


def main():
    sys.dont_write_bytecode = True
    payload=json.loads(sys.stdin.read());adapter=payload["adapter"]
    root=Path(payload["checkout"]).resolve()
    repository=Path(payload.get("repository_root",root)).resolve()
    scope=adapter.get("evaluator_scope","upstream")
    if scope not in ("upstream","repository"):raise ValueError("Invalid evaluator scope")
    evaluator_root=repository if scope=="repository" else root
    relative=adapter["evaluator_path"]
    if not isinstance(relative,str) or Path(relative).is_absolute() or ".." in Path(relative).parts:
        raise ValueError("Evaluator must be a contained relative path")
    evaluator=(evaluator_root/relative).resolve()
    cwd=(root/adapter.get("cwd",".")).resolve()
    if not evaluator.is_relative_to(evaluator_root) or not cwd.is_relative_to(root): raise ValueError("Evaluator paths escape declared scope")
    environment=payload.get("environment",adapter.get("environment",{}))
    if not isinstance(environment,dict) or not all(isinstance(k,str) and isinstance(v,str) for k,v in environment.items()):
        raise ValueError("Adapter environment must be a string map")
    os.environ.update(environment)
    os.chdir(cwd)
    sys.path[:0]=[entry for entry in environment.get("PYTHONPATH", "").split(os.pathsep) if entry]
    sys.path[:0]=[str(evaluator.parent),str(cwd),str(root)]
    with contextlib.redirect_stdout(sys.stderr):
        if adapter.get("import_module"):
            module=importlib.import_module(adapter["import_module"])
            if Path(module.__file__).resolve()!=evaluator:raise ValueError("Canonical module does not match pinned evaluator path")
        else:
            name="upstream_evaluator"
            spec=importlib.util.spec_from_file_location(name,evaluator)
            module=importlib.util.module_from_spec(spec);sys.modules[name]=module
            spec.loader.exec_module(module)
        function=getattr(module,adapter.get("callable","evaluate"))
        def resolve(value):
            if value == "{python}":return sys.executable
            if value == "{checkout}":return str(root)
            if value == "{repository}":return str(repository)
            if isinstance(value,list):return [resolve(v) for v in value]
            if isinstance(value,dict):return {k:resolve(v) for k,v in value.items()}
            return value
        args=[];kwargs=resolve(dict(adapter.get("kwargs",{})))
        if adapter.get("candidate_argument","positional")=="keyword":
            kwargs[adapter["candidate_keyword"]]=payload["candidate"]
        else:args.append(payload["candidate"])
        with tempfile.TemporaryDirectory(prefix="artask-result-") as tmp:
            output=Path(tmp)/"metrics.json"
            if adapter.get("return_style")=="json_file":
                if adapter.get("output_argument","positional")=="keyword":kwargs[adapter["output_keyword"]]=str(output)
                else:args.append(str(output))
            result=function(*args,**kwargs)
            if inspect.isawaitable(result):result=asyncio.run(result)
            if adapter.get("return_style")=="json_file":result=json.loads(output.read_text())
    print(json.dumps(plain(result),allow_nan=False))

if __name__=="__main__": main()
