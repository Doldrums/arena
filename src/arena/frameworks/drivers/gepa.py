"""Delegate an explicit research factory to GEPA's complete native optimizer."""
import argparse
import json

from ._specialized import bounded_positive, load_factory, output_directory


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--factory", required=True)
    parser.add_argument("--max-metric-calls", type=bounded_positive, required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    kwargs = load_factory(args.factory)
    if not {"seed_candidate", "trainset"} <= kwargs.keys():
        raise ValueError("GEPA factory requires seed_candidate and trainset")
    output = output_directory(args.output)
    from gepa import optimize
    kwargs.update(max_metric_calls=args.max_metric_calls, run_dir=str(output),
                  use_wandb=False, use_mlflow=False, use_cloudpickle=False)
    result = optimize(**kwargs)
    (output / "gepa-result.json").write_text(json.dumps(result.to_dict(), indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
