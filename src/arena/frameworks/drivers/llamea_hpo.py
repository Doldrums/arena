"""Run native LLaMEA with a user-supplied HPO evaluation contract."""
import argparse

from ._specialized import bounded_positive, load_factory


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--factory", required=True)
    parser.add_argument("--generations", type=bounded_positive, required=True)
    args = parser.parse_args(argv)
    payload = load_factory(args.factory)
    if not {"f", "llm"} <= payload.keys():
        raise ValueError("LLaMEA-HPO factory requires an HPO evaluator f and native llm")
    from llamea import LLaMEA
    payload.update(HPO=True, budget=args.generations, log=True)
    LLaMEA(**payload).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
