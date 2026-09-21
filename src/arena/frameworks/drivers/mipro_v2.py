"""Run pinned DSPy MIPROv2; this is not the original MIPRO paper artifact."""
import argparse

from ._specialized import bounded_positive, load_factory, output_directory


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--factory", required=True)
    parser.add_argument("--trials", type=bounded_positive, required=True)
    parser.add_argument("--candidates", type=bounded_positive, required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    payload = load_factory(args.factory)
    if set(payload) != {"optimizer", "compile"}:
        raise ValueError("Factory requires optimizer and compile dictionaries")
    optimizer, compile_args = payload["optimizer"], payload["compile"]
    if (type(optimizer) is not dict or type(compile_args) is not dict
            or "metric" not in optimizer or not {"student", "trainset"} <= compile_args.keys()):
        raise ValueError("MIPROv2 requires metric, student and trainset")
    output = output_directory(args.output)
    from dspy import MIPROv2
    optimizer.update(auto=None, num_candidates=args.candidates, log_dir=str(output))
    compile_args.update(num_trials=args.trials)
    compiled = MIPROv2(**optimizer).compile(**compile_args)
    compiled.save(str(output / "compiled-program.json"), save_program=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
