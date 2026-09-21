"""Delegate set-based heuristic discovery to the released EoHS implementation."""
import argparse

from ._specialized import bounded_positive, load_factory, output_directory


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--factory", required=True)
    parser.add_argument("--max-samples", type=bounded_positive, required=True)
    parser.add_argument("--generations", type=bounded_positive, required=True)
    parser.add_argument("--population", type=bounded_positive, default=10)
    parser.add_argument("--workers", type=bounded_positive, default=1)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    payload = load_factory(args.factory)
    if set(payload) != {"llm", "evaluation"}:
        raise ValueError("EoH-S factory requires llm and evaluation")
    output = output_directory(args.output)
    from llm4ad.method.eohs import EoHS, EoHSProfiler
    method = EoHS(**payload, profiler=EoHSProfiler(log_dir=str(output), log_style="simple"),
                  max_sample_nums=args.max_samples, max_generations=args.generations,
                  pop_size=args.population, num_samplers=args.workers, num_evaluators=args.workers,
                  debug_mode=False)
    method.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
