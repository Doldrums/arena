# Generated evaluator bridge conformance — 2026-09-21

**Passed for the two selected bridges/tasks**, including invalid-candidate rejection. These are real offline Docker evaluations through Arena-generated wrappers. No SCiEL/Shinka native search loop, DGM episode, or LLM call ran. This does not establish compatibility with all tasks or complete framework-run conformance.

Task source: `5729caa7a3bd4e66c39a447c0d4ee56dc8fa0935` (clean checkout). Docker image: `sha256:ff59425be3cb209f0dfe6bb607d37ae8db1254f8e8a1173b1dde0e6c2e18cb29`, `linux/arm64`. The canonical Docker profile disabled network access, mounted task/candidate inputs read-only, and applied memory/CPU/process limits. The existing image was used without a pull or model credentials.

| Case | Canonical status | Validity | Raw score / fitness | Bridge output |
| --- | --- | --- | --- | --- |
| SCiEL `reference-sat` seed | completed | true | 1.0 / 1.0 | smoke syntax-only; full `ok: true`, score 1.0 |
| Shinka circle-packing seed | completed | true | 2.1406666666666663 / same | `correct: true`, matching `combined_score` |
| Shinka invalid packing after fix (`construct() -> []`) | invalid | false | null / null | `correct: false`, `combined_score: null` |

Each full evaluation dispatched once, with zero retries. SCiEL smoke created no receipt; full created exactly one. Shinka's generated `evaluate.py` was invoked as a CLI for both candidates and produced `metrics.json` plus `correct.json`. All owned Docker containers were confirmed absent after cleanup. Four physical evaluations ran in total, including the initial invalid-candidate diagnostic below. A score of 1.0 concerns the fixed ten-instance SAT development task, not the full paper benchmark.

## Diagnostic found and resolved

The first invalid packing candidate was already rejected by Shinka, but its canonical receipt was `error` / `validity: null`. In pinned upstream `src/autoresearch_tasks/runner.py:204`, `score: null` raises before the validity field is read at line 208. The saved `upstream_result.valid` was explicitly false, with the wrong-shape error. The original receipt is retained unchanged.

The reviewed normalizer now preserves that explicit negative decision only for the verified suite/repository-owned failed envelope. Unknown validity is not inferred from a generic error, and nested true does not grant validity. Repeating only this failed assertion in a fresh output directory produced `invalid` / `false` and no fitness. The recheck also exercised the revised Docker mount that exposes only `native-output` for evaluator output; final receipts remain host-written outside it.

## Receipt artifacts

- **SCiEL SAT seed:** [receipt](/private/var/folders/56/90x6gg5x5ggfqgjf81xpllg80000gn/T/arena-framework-conformance-20260921-cuiit4mv/sciel-receipts/064d143adddf44bab5ae47fc8df12610/receipt.json)
  SHA256 `8726d3f51654c8dc2818cd4edc5fc03bd6f3765d91647f054c4256b4a95326a2`.
- **Shinka packing seed:** [receipt](/private/var/folders/56/90x6gg5x5ggfqgjf81xpllg80000gn/T/arena-framework-conformance-20260921-cuiit4mv/shinka-receipts/d6d48e46b76f4817ac8807e123d25c76/receipt.json)
  SHA256 `bda216f4bcebfa25209256d2336c9d4f1b0a750b2d2344caf710251c11dae7ff`.
- **Initial invalid-candidate diagnostic:** [receipt](/private/var/folders/56/90x6gg5x5ggfqgjf81xpllg80000gn/T/arena-framework-conformance-20260921-cuiit4mv/shinka-receipts/be4a6be51db3467696bea4a8bd0494ec/receipt.json)
  SHA256 `e34d7c0db1d3dd4fd1fda073d0ac4d05abb44ac4f6778f5fb714beea67518cfa`.
- **Shinka invalid candidate after fix:** [receipt](/private/var/folders/56/90x6gg5x5ggfqgjf81xpllg80000gn/T/arena-framework-invalid-recheck-20260921-3ang2wp1/receipts/fd90315999d44af69c85290e0ebe7c5c/receipt.json)
  SHA256 `714ec28efcbe66b15a697f2014fc663c726081a5b3760b4e58c0553074f79af3`.

Native bridge outputs and their hashes:

- SCiEL smoke: [JSON](/private/var/folders/56/90x6gg5x5ggfqgjf81xpllg80000gn/T/arena-framework-conformance-20260921-cuiit4mv/sciel-smoke-result.json) — SHA256 `7c570fc686145c959cf5cae45435f15c43e8a54188f3b3041383149a0fb4030d`.
- SCiEL full: [JSON](/private/var/folders/56/90x6gg5x5ggfqgjf81xpllg80000gn/T/arena-framework-conformance-20260921-cuiit4mv/sciel-full-result.json) — SHA256 `1e2554b449be61afd2d657914a069662c783e78eebf170e7da004df57f75d289`.
- Shinka seed metrics: [JSON](/private/var/folders/56/90x6gg5x5ggfqgjf81xpllg80000gn/T/arena-framework-conformance-20260921-cuiit4mv/shinka_packing_seed/metrics.json) — SHA256 `00f93f55a9ef6162852a7e8bffc0b10b2447a3f92307fc8eef96dcbc14578a78`.
- Shinka seed correctness: [JSON](/private/var/folders/56/90x6gg5x5ggfqgjf81xpllg80000gn/T/arena-framework-conformance-20260921-cuiit4mv/shinka_packing_seed/correct.json) — SHA256 `8d7ddd5825df9b351cb248205036e4745754ebc9919377c90b3d16952d79e36b`.
- Shinka invalid metrics: [JSON](/private/var/folders/56/90x6gg5x5ggfqgjf81xpllg80000gn/T/arena-framework-invalid-recheck-20260921-3ang2wp1/results/metrics.json) — SHA256 `637c6da91ad7fab859a1439027fb4619e50c6b7493ab964b7b0cba08ff6e9f3a`.
- Shinka invalid correctness: [JSON](/private/var/folders/56/90x6gg5x5ggfqgjf81xpllg80000gn/T/arena-framework-invalid-recheck-20260921-3ang2wp1/results/correct.json) — SHA256 `6e318606120aaca029c89f8de06227cde7b1f6020ef4035de0ffb89992ebe152`.

[Invalid-recheck summary](/private/var/folders/56/90x6gg5x5ggfqgjf81xpllg80000gn/T/arena-framework-invalid-recheck-20260921-3ang2wp1/summary.json) records the implementation hashes, all unchanged during that recheck. Receipt/artifact paths are local retained conformance outputs, not published participant benchmark results. Full native-loop launch, resume, cross-framework budget accounting and other task profiles remain outside this check.
