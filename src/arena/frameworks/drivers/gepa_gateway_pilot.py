"""Native GEPA prompt optimization over a pinned, split GSM8K pilot."""
from __future__ import annotations

import argparse
from pathlib import Path

from ._gsm8k_pilot import MODELS, SEED, GatewayCallBudgetExhausted, GatewayTransport, extract_answer, heldout_report, is_correct, load_dataset, protocol, write_json


def build_native(dataset, transport, output):
    from gepa.adapters.default_adapter.default_adapter import DefaultAdapter, EvaluationResult
    def evaluator(data, response):
        correct = is_correct(response, data)
        feedback = ("Correct." if correct else "Incorrect. The expected answer is #### " + extract_answer(data["answer"]) + ".")
        return EvaluationResult(float(correct), feedback)
    adapter = DefaultAdapter(model=transport.text, evaluator=evaluator, max_litellm_workers=1)
    def convert(rows):
        return [{"input": row["question"], "answer": row["answer"], "additional_context": {}} for row in rows]
    return {"seed_candidate": {"instructions": SEED}, "trainset": convert(dataset["selected_records"]["train"]),
            "valset": convert(dataset["selected_records"]["validation"]), "adapter": adapter,
            "reflection_lm": transport.text, "reflection_minibatch_size": 3, "max_metric_calls": 24,
            "run_dir": str(output), "use_wandb": False, "use_mlflow": False, "use_cloudpickle": False,
            "seed": 9, "raise_on_exception": True}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--model", choices=MODELS, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    dataset = load_dataset(args.dataset)
    args.output.mkdir(parents=True, exist_ok=True)
    transport = GatewayTransport(args.model, args.output / "gateway-usage.json")
    write_json(args.output / "protocol.json", protocol(dataset, "gepa-gateway-gsm8k", args.model,
        {"max_metric_calls": 24, "reflection_minibatch_size": 3, "seed": 9,
         "note": "Native stopping is checked between iterations; one complete proposal/validation can overshoot the metric target. Gateway requests have a separate hard cap."}))
    native_completed = False
    try:
        from gepa import optimize
        kwargs = build_native(dataset, transport, args.output / "native")
        result = optimize(**kwargs)
        native_completed = True
        write_json(args.output / "gepa-result.json", result.to_dict())
        # Heldout is consulted only after the validation-selected candidate freezes.
        reports = {}
        for label, candidate in (("seed", kwargs["seed_candidate"]), ("selected", result.best_candidate)):
            transport.phase = "heldout_" + label
            def predict(question):
                return transport.text([{"role": "system", "content": candidate["instructions"]}, {"role": "user", "content": question}])
            reports[label] = heldout_report(dataset["selected_records"]["heldout"], predict,
                                             args.output / ("heldout-" + label + ".json"))
        write_json(args.output / "heldout.json", {"schema": "arena.prompt-pilot-heldout/1", "selection_split": "validation", "reports": reports, "canonical_evaluation": False})
    except GatewayCallBudgetExhausted:
        write_json(args.output / "status.json", {"status": "gateway_budget_exhausted", "native_completed": native_completed, "heldout_completed": False})
        return 75
    except BaseException as error:
        write_json(args.output / "status.json", {"status": "error", "native_completed": native_completed, "heldout_completed": False, "error_type": type(error).__name__})
        raise
    else:
        write_json(args.output / "status.json", {"status": "completed", "native_completed": True, "heldout_completed": True})
        return 0
    finally:
        transport.save()


if __name__ == "__main__":
    raise SystemExit(main())
