"""Bounded native PoetryEvolution / MAP-Elites pilot, with text transport port."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
import math
import os
from pathlib import Path
import sys

from .qdaif_gateway_transport import (GatewayTransport, MODELS, QDAIFGatewayStopped,
                                     REQUEST_LIMIT, install_transport, write_json)

COMMIT = "c844e149e3f59fef546e0bc55f4e12e0f192feb9"
ENGINE = "qdaif-poetry-gateway"
PROFILE = "poetry-mapelites-pilot"
HELPER = "src/openelm/mutation_model.py"
HELPER_SHA256 = "83d5968580ce15d3ba1a01536f9cd9ba9a9dae8999e6036ee01b3d9a6e7ad132"
PORT = '''def get_model(config: ModelConfig):
    from arena.frameworks.drivers.qdaif_gateway_transport import make_model
    return make_model(config)
'''


def sha(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 32 * 1024**2:
        raise ValueError("QDAIF evidence must be a bounded regular file")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ported_helper(source):
    path = Path(source) / HELPER
    if sha(path) != HELPER_SHA256:
        raise ValueError("QDAIF provider factory source differs from reviewed pin")
    text = path.read_text()
    begin, end = text.index("def get_model(config: ModelConfig):"), text.index("\n\nclass MutationModel")
    return text[:begin] + PORT + text[end:]


def evidence(source):
    paths = [source / p for p in ("LICENSE", "requirements.txt", "pyproject.toml", "run_elm.py")]
    paths += sorted((source / "src/openelm").rglob("*.py"))
    if any(p.is_symlink() for p in (source / "src").rglob("*")):
        raise ValueError("QDAIF source cannot contain symlinks")
    return {p.relative_to(source).as_posix(): sha(p) for p in paths}


def preparation(source, freeze, constraints):
    return {"schema": "arena.qdaif-preparation/1", "source_commit": COMMIT,
        "source_files": evidence(Path(source)), "dependency_freeze_sha256": sha(freeze),
        "dependency_constraints_sha256": sha(constraints),
        "native_helper_original_sha256": HELPER_SHA256,
        "native_helper_port_sha256": hashlib.sha256(ported_helper(source).encode()).hexdigest()}


def native_config(model, output):
    if model not in MODELS:
        raise ValueError("Unknown model")
    from openelm.configs import ELMConfig, MAPElitesConfig, PromptModelConfig, QDEnvConfig
    return ELMConfig(output_dir=str(output),
        model=PromptModelConfig(model_type="openai", model_path=model, cuda=False, gpus=0, fp16=False, seed=42),
        env=QDEnvConfig(batch_size=2, processes=1, seed=42),
        qd=MAPElitesConfig(init_steps=1, total_steps=4, save_history=True, save_snapshot_interval=1,
                          seed=42, output_dir=str(output / "native")))


def number(value):
    result = float(value)
    return result if math.isfinite(result) else {"nonfinite": str(result)}


def native_value(value):
    if isinstance(value, float) and not math.isfinite(value):
        return number(value)
    if isinstance(value, dict):
        return {key: native_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [native_value(item) for item in value]
    return value


def native_result(elm):
    """Export live native state; never deserialize the native pickle snapshots."""
    import numpy as np
    algorithm = elm.qd_algorithm
    archive = []
    for index in np.ndindex(algorithm.fitnesses.latest.shape):
        fitness = algorithm.fitnesses.latest[index]
        if np.isfinite(fitness):
            poem = algorithm.genomes.latest[index]
            archive.append({"cell": [int(v) for v in index], "fitness": number(fitness), "quality": native_value(poem.quality),
                            "genre": poem.genre, "tone": poem.tone, "poem": poem.poem})
    history = [{"cell": [int(v) for v in index], "candidates": [{"poem": p.poem, "quality": native_value(p.quality),
                    "genre": p.genre, "tone": p.tone} for p in values]}
               for index, values in algorithm.history.items()]
    return {"schema": "arena.qdaif-native-state/1", "canonical_evaluation": False,
        "niches_filled": int(algorithm.niches_filled()), "qd_score": number(algorithm.qd_score()),
        "max_fitness": number(algorithm.max_fitness()), "archive": archive, "history": history,
        "fitness_history": {key: [number(v) for v in values] for key, values in algorithm.fitness_history.items()}}


def run(source, model, output, manifest_path, freeze, constraints, *, session=None, sdk=None):
    source, output = Path(source).resolve(), Path(output).resolve()
    if output.exists():
        raise ValueError("QDAIF output must be new")
    if any((p / ".env").exists() or (p / ".env").is_symlink() for p in (source, *source.parents)):
        raise ValueError("QDAIF credentials must come from the explicit worker environment")
    if json.loads(Path(manifest_path).read_text()) != preparation(source, freeze, constraints):
        raise ValueError("QDAIF prepared source/environment provenance changed")
    output.mkdir(parents=True)
    receipt = {"schema": "arena.qdaif-pilot/1", "framework": ENGINE, "model": model,
        "source_commit": COMMIT, "canonical_evaluation": False, "status": "preparing",
        "preparation_sha256": sha(manifest_path),
        "port": {"file": HELPER, "before": HELPER_SHA256,
                 "after": hashlib.sha256(ported_helper(source).encode()).hexdigest()},
        "limits": {"iterations": 4, "initial_iterations": 1, "batch_size": 2, "poems": 8,
                   "native_judgments": 16, "http_attempt_limit": REQUEST_LIMIT,
                   "evaluation_workers": 1, "outer_timeout_seconds": 2400},
        "limitations": ["Native self-judged poem quality/diversity, not canonical evaluation or paper reproduction.",
            "Generation controls are recorded in native config but current gateway does not enforce them.",
            "Malformed JSON keeps native -inf behavior; unknown categories can fail the native search.",
            "Raw native quality is not clamped to the prompted 1–10 range."]}
    write_json(output / "pilot-receipt.json", receipt)
    transport = GatewayTransport(model, output, session=session, sdk=sdk)
    install_transport(transport)
    (source / HELPER).write_text(ported_helper(source))
    sys.path.insert(0, str(source / "src"))
    os.environ.update(MPLBACKEND="Agg", HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", WANDB_MODE="disabled")
    elm = None
    try:
        from openelm.elm import ELM
        config = native_config(model, output)
        write_json(output / "native-config.json", asdict(config))
        receipt["config_sha256"] = sha(output / "native-config.json")
        elm = ELM(config)
        best = elm.run()
        state = native_result(elm)
        state["native_best_text"] = best
        write_json(output / "native-result.json", state)
        receipt.update(status="completed", native_metrics={k: state[k] for k in ("niches_filled", "qd_score", "max_fitness")})
        return receipt
    except BaseException as error:
        receipt.update(status="stopped" if isinstance(error, QDAIFGatewayStopped) else "failed", error_type=type(error).__name__)
        if elm is not None:
            try:
                write_json(output / "native-partial-state.json", native_result(elm))
            except Exception as export_error:
                receipt["partial_export_error_type"] = type(export_error).__name__
        raise
    finally:
        transport.save()
        write_json(output / "pilot-receipt.json", receipt)


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--model", choices=MODELS, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--preparation", type=Path, required=True)
    parser.add_argument("--dependencies", type=Path, required=True)
    parser.add_argument("--constraints", type=Path, required=True)
    args = parser.parse_args()
    try:
        run(Path.cwd(), args.model, args.output, args.preparation, args.dependencies, args.constraints)
    except QDAIFGatewayStopped:
        parser.exit(1, "QDAIF provider/budget stopped; inspect bounded private receipt.\n")


if __name__ == "__main__":
    main()
