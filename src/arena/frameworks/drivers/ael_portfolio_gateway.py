"""Four-day native AEL portfolio pilot with immutable bundled data."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import sys

from .ael_gateway_transport import (AELGatewayStopped, GatewayTransport, MODELS,
                                    REQUEST_LIMIT, install_transport, write_json)

COMMIT = "c95f5f961667e7df4bdddf750b22332158951bf2"
ENGINE = "ael-portfolio-gateway"
PROFILE = "hourly-portfolio-pilot"
HELPER_SHA256 = "407b32e5c14c9d182aa45839ad8ca14f722f949dab9e89a2f4add00a0fafc945"
CONFIG_SHA256 = "0d60516b09df117c62faa0ef8104f98afd8e23a6ae58196b9e763026ca5e16b3"
CONFIG_PATH = "experiments/configs/ael_full.yaml"
TICKERS = ("AAPL", "MSFT")
DAYS = ("2025-01-06", "2025-01-07", "2025-01-08", "2025-01-10")
EPISODES = 16
PORT = "from arena.frameworks.drivers.ael_gateway_transport import llm_call, normalize_model\n"


def sha(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 32 * 1024**2:
        raise ValueError("AEL evidence must be a bounded regular file")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evidence(source):
    paths = [source / "LICENSE", source / "requirements.txt", source / CONFIG_PATH,
             source / "experiments/run_experiment.py", source / "experiments/run_portfolio.py"]
    paths += sorted((source / "ael").rglob("*.py"))
    paths += sorted(p for p in (source / "data").rglob("*") if not p.is_dir())
    if any(p.is_symlink() for p in source.joinpath("data").rglob("*")):
        raise ValueError("AEL data cannot contain symlinks")
    return {p.relative_to(source).as_posix(): sha(p) for p in paths}


def data_schedule(source):
    """Validate all 32 native return observations before importing the evaluator."""
    schedules = []
    for ticker in TICKERS:
        with (source / f"data/prices_1h/{ticker}.csv").open() as stream:
            bars = [r["Datetime"] for r in csv.DictReader(stream) if r["Datetime"].split()[0] in DAYS]
        with (source / f"data/returns_1h/{ticker}.csv").open() as stream:
            returns = {r["datetime"]: r for r in csv.DictReader(stream)}
        if len(bars) != EPISODES or len(set(bars)) != EPISODES:
            raise ValueError("AEL pilot needs exactly sixteen actual cached bars per ticker")
        for bar in bars:
            value = returns.get(bar, {})
            if value.get("direction_1bar") not in {"up", "down", "flat"} or not math.isfinite(float(value.get("return_1bar", "nan"))):
                raise ValueError("AEL pilot is missing native realized return evidence")
        for category in ("fundamentals", "analyst", "options", "earnings"):
            sha(source / f"data/{category}/{ticker}.json")
        schedules.append(bars)
    if schedules[0] != schedules[1]:
        raise ValueError("AEL ticker schedules differ")
    return schedules[0]


def preparation(source, freeze):
    source = Path(source)
    if sha(source / "ael/llm_utils.py") != HELPER_SHA256 or sha(source / CONFIG_PATH) != CONFIG_SHA256:
        raise ValueError("AEL source helper/config is not the reviewed pin")
    return {"schema": "arena.ael-preparation/1", "source_commit": COMMIT,
            "source_files": evidence(source), "bars": data_schedule(source),
            "dependency_freeze_sha256": sha(freeze),
            "native_helper_original_sha256": HELPER_SHA256,
            "native_helper_port_sha256": hashlib.sha256(PORT.encode()).hexdigest()}


def native_config(source, model, output):
    if model not in MODELS:
        raise ValueError("Unknown model")
    import yaml
    config = yaml.safe_load((source / CONFIG_PATH).read_text())
    config.update(name=ENGINE, llm_model=model, num_episodes=EPISODES, seed=42,
                  log_dir=str(output / "native"), warm_up_episodes=0)
    config["benchmark"].update(tickers=list(TICKERS), frequency="1h", bars_per_day=4,
        flat_threshold=0.001, start_date=DAYS[0], end_date=DAYS[-1],
        train_end_date=DAYS[1], val_end_date=DAYS[2], prediction_horizons=[1])
    # These are explicit native configuration fields, not replacement methods.
    config["reflection"] = {"enabled": True, "llm_model": model, "meta_llm_model": model,
                            "evolve_planners": True}
    config["cold_start"] = {"enabled": True, "llm_model": model}
    return config


def run(source, model, output, manifest_path, freeze_path, *, client=None):
    source, output = Path(source).resolve(), Path(output).resolve()
    if output.exists():
        raise ValueError("AEL output must be new")
    if any((p / ".env").exists() or (p / ".env").is_symlink() for p in (source, *source.parents)):
        raise ValueError("AEL credentials must come from the explicit worker environment")
    manifest = json.loads(Path(manifest_path).read_text())
    if manifest != preparation(source, freeze_path):
        raise ValueError("AEL prepared source/data/environment provenance changed")
    output.mkdir(parents=True)
    config = native_config(source, model, output)
    write_json(output / "native-config.json", config)
    receipt = {"schema": "arena.ael-pilot/1", "framework": ENGINE, "model": model,
               "source_commit": COMMIT, "canonical_evaluation": False, "status": "preparing",
               "preparation_sha256": sha(manifest_path), "config_sha256": sha(output / "native-config.json"),
               "port": {"file": "ael/llm_utils.py", "before": HELPER_SHA256,
                        "after": hashlib.sha256(PORT.encode()).hexdigest()},
               "native_evaluator": "PortfolioRunner / compute_portfolio_metrics / cached return_1bar",
               "limits": {"episodes": EPISODES, "days": len(DAYS), "request_limit": REQUEST_LIMIT,
                          "evaluation_workers": 1, "outer_timeout_seconds": 2400},
               "limitations": ["Small native portfolio integration, not paper reproduction or financial evidence.",
                  "Bundled static financial inputs include post-period statements (AAPL September/December2025 versus this January2025 pilot); native tools have no as-of cutoff. This known lookahead prevents historical predictive-performance claims; native semantics retained.",
                  "Native parse failures may choose equal weights; a returned completion is not proof of valid allocation.",
                  "Native full configuration enables all modules, but conditional branches need not trigger in this short pilot.",
                  "Central provider errors/budget stops are terminal rather than native equal-weight fallbacks."]}
    write_json(output / "pilot-receipt.json", receipt)
    transport = GatewayTransport(model, output, client=client)
    install_transport(transport)
    (source / "ael/llm_utils.py").write_text(PORT)
    os.environ["AEL_DATA_DIR"] = str(source / "data")
    os.environ.pop("USSTOCK_PATH", None)
    sys.path.insert(0, str(source))
    try:
        import numpy as np
        from ael.config import ExperimentConfig
        from experiments.run_experiment import build_components
        from ael.benchmarks.portfolio_runner import PortfolioRunner
        np.random.seed(42)
        cfg = ExperimentConfig.from_yaml(output / "native-config.json")
        loop = build_components(cfg, model=model)
        runner = PortfolioRunner(config=cfg, evolution_loop=loop)
        result = runner.run(predict_fn=loop.predict_fn, max_episodes=EPISODES)
        if result["total_episodes"] != EPISODES or {k:v["n_bars"] for k,v in result["phase_metrics"].items()} != {"train":8,"val":4,"test":4}:
            raise ValueError("Native AEL result does not cover the prepared phases")
        receipt.update(status="completed", native_activity={"episodes": result["total_episodes"],
            "nightly_cycles": loop._day_index, "reflections": len(loop._reflections),
            "planner_names": loop.planners.all_names, "tool_names": loop.tools.all_names,
            "meta_episodes_elapsed": loop.meta._episodes_elapsed},
            native_metrics=result["metrics"], phase_metrics=result["phase_metrics"])
        write_json(output / "native-result.json", result)
        return receipt
    except BaseException as error:
        receipt.update(status="stopped" if isinstance(error, AELGatewayStopped) else "failed", error_type=type(error).__name__)
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
    args = parser.parse_args()
    try:
        run(Path.cwd(), args.model, args.output, args.preparation, args.dependencies)
    except AELGatewayStopped:
        parser.exit(1, "AEL provider request/budget stopped; inspect bounded private receipt.\n")


if __name__ == "__main__":
    main()
