# symbolic_regression_bench: self-contained SR drop-in

The proposal's 3rd benchmark, as a **drop-in OpenEvolve example** (one
`initial_program.py` + `evaluator.py` + `config.yaml`, numpy-only, no
network/keys) that plugs into `scripts/run_ablation.py` like
`function_minimization` / `circle_packing`.

Task: evolve `propose_models()` to recover a hidden 2-feature target
`y = 2.5·sin(1.3·x0) + 0.7·x1² − 0.4·x0·x1 + 1.1` from deterministically
sampled data. A **revert-proof training-fit budget** (`MAX_FITS`, enforced in
fixed code outside the `EVOLVE-BLOCK`) defeats brute force; scoring is
held-out test NMSE with ground truth re-derived independently in the
evaluator. Seed (linear) ≈ 0.18, recovered ≈ 1.50 combined_score (~8.5×).

Design + calibration: `docs/experiments/symbolic_regression_bench.md` (mirrors
`function_minimization_budget.md`). Test:
`tests/test_symbolic_regression_bench.py`.

**Not** the LLM-SRBench study; that is the separate upstream sub-project in
`examples/symbolic_regression/` (datasets + `data_api.py`), left untouched.
