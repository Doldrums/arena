"""Explicit launch of austin1997's AVO reimplementation, not NVIDIA's engine."""
import argparse
import json
import math
from pathlib import Path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--max-versions", type=int, required=True)
    parser.add_argument("--hours", type=float, required=True)
    parser.add_argument("--max-agent-steps", type=int, required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    if (not 1 <= args.max_versions <= 100000 or not 1 <= args.max_agent_steps <= 100000
            or not math.isfinite(args.hours) or not 0 < args.hours <= 168):
        parser.error("Specify positive bounded versions, agent steps and hours (at most 168)")
    config_path = Path(args.config).resolve()
    if not config_path.is_relative_to(Path.cwd()) or not config_path.is_file():
        parser.error("Config must be an explicitly staged workspace input")
    # The native package and all model/scoring code are loaded only here.
    from avo.config import EvolutionConfig
    from avo.core.evolution import EvolutionRunner
    config = EvolutionConfig.from_yaml(config_path)
    if config.llm.api_key:
        parser.error("Use explicit provider environment credentials, not keys in the config")
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    config.workspace_dir = str(output / "population")
    config.log_dir = str(output / "logs")
    config.max_versions = args.max_versions
    config.max_agent_steps_per_variation = args.max_agent_steps
    config.max_wall_time_hours = args.hours
    runner = EvolutionRunner(config)
    runner.run()
    (output / "native-summary.json").write_text(json.dumps({
        "implementation": "austin1997/AVO", "canonical_evaluation": False,
        "native": runner.get_results(),
    }, indent=2, allow_nan=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
