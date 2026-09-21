"""Native DSPy MIPROv2 over pinned GSM8K splits; not MIPRO paper replication."""
from __future__ import annotations

import argparse
from pathlib import Path

from ._gsm8k_pilot import MODELS, SEED, GatewayCallBudgetExhausted, GatewayTransport, heldout_report, is_correct, load_dataset, protocol, write_json


def build_native(dataset, transport, output):
    import dspy
    from .mipro_gateway_lm import GatewayLM
    lm = GatewayLM(transport.model, transport=transport)
    signature = dspy.Signature("question -> answer", instructions=SEED)
    student = dspy.ChainOfThought(signature)
    student.set_lm(lm)
    def convert(rows):
        return [dspy.Example(question=row["question"], answer=row["answer"]).with_inputs("question") for row in rows]
    def metric(gold, pred, trace=None):
        return is_correct(str(pred.answer), {"answer": str(gold.answer)})
    optimizer = dspy.MIPROv2(metric=metric, prompt_model=lm, task_model=lm,
        max_bootstrapped_demos=1, max_labeled_demos=1, auto=None, num_candidates=3,
        num_threads=1, max_errors=2, seed=9, init_temperature=1.0, log_dir=str(output))
    compile_args = {"student": student, "trainset": convert(dataset["selected_records"]["train"]),
                    "valset": convert(dataset["selected_records"]["validation"]),
                    "num_trials": 3, "minibatch": False, "view_data_batch_size": 8, "seed": 9}
    return lm, optimizer, compile_args


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--model", choices=MODELS, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    dataset = load_dataset(args.dataset)
    args.output.mkdir(parents=True, exist_ok=True)
    transport = GatewayTransport(args.model, args.output / "gateway-usage.json")
    write_json(args.output / "protocol.json", protocol(dataset, "miprov2-gateway-gsm8k", args.model,
        {"num_candidates": 3, "num_trials": 3, "max_bootstrapped_demos": 1, "max_labeled_demos": 1,
         "minibatch": False, "num_threads": 1, "seed": 9,
         "note": "Native bootstrap, grounded instruction proposal and Optuna selection remain. Trials exclude bootstrap/proposer calls and initial validation evaluation."}))
    native_completed = False
    try:
        import dspy
        lm, optimizer, kwargs = build_native(dataset, transport, args.output / "native")
        seed_program = kwargs["student"].deepcopy()
        with dspy.context(lm=lm):
            compiled = optimizer.compile(**kwargs)
            native_completed = True
            compiled.save(str(args.output / "compiled-program.json"), save_program=False)
            reports = {}
            for label, program in (("seed", seed_program), ("selected", compiled)):
                transport.phase = "heldout_" + label
                reports[label] = heldout_report(dataset["selected_records"]["heldout"],
                                               lambda question: str(program(question=question).answer),
                                               args.output / ("heldout-" + label + ".json"))
        write_json(args.output / "heldout.json", {"schema": "arena.prompt-pilot-heldout/1", "selection_split": "validation", "reports": reports, "canonical_evaluation": False})
        write_json(args.output / "native-summary.json", {"validation_score_percent": getattr(compiled, "score", None), "native_optimizer": "MIPROv2", "paper_replication": False})
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
