"""Call LLaMEA-BO's native experiment without placing its key in CLI/logs."""
import argparse
import os

from ._specialized import bounded_positive


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parents", type=bounded_positive, default=1)
    parser.add_argument("--offspring", type=bounded_positive, default=1)
    parser.add_argument("--populations", type=bounded_positive, required=True)
    parser.add_argument("--elitist", action="store_true")
    args = parser.parse_args(argv)
    key = os.environ["GEMINI_API_KEY"]
    from run_es_search import run_exp
    run_exp(args.parents, args.offspring, args.elitist, key, n_population=args.populations)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
