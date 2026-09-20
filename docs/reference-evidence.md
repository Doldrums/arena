# Scientific reference evidence

`registry/references.json` adds numerical context to the task catalog. It records
what the pinned source actually provides, with a commit, file digest and locator.
It is **not a current-SOTA survey**, an Arena leaderboard, or a reproduction run.
Missing evidence is an empty list, never an invented score of zero.

The source is the private [autoresearch-tasks repository at
995768fc462b8e327f90e6762846cc6ccb06cc2c](https://github.com/IMRUNya/autoresearch-tasks/tree/995768fc462b8e327f90e6762846cc6ccb06cc2c).
Links require repository access. The snapshot is tied to the same original
catalog/index digests as Arena's catalog. Generation reads JSON, source text and
CSV data; it never imports or executes a task, candidate, benchmark or model.

## What is known

| Evidence | Task packages | Meaning |
| --- | ---: | --- |
| Source-declared published numeric reference | 122 | `problem.json` → `parameters.published`; mathematical reference constructions, ranks or bounds, not task sizes or execution budgets |
| Recorded seed smoke baseline | 697 | Successful upstream smoke-report rows; 603 explicitly valid, 94 without a validity signal |
| Recorded reference-artifact check | 34 | 19 AlphaEvolve notebook-value receipts and 15 exact tensor-decomposition checks in upstream JSON reports |
| Any extracted numeric anchor | 697 | Published-reference packages also have a recorded seed baseline |
| No extracted numeric anchor | 441 | Includes unsupported or unexecuted/rejected seeds; no implication that scientific literature lacks a result |
| No extracted published reference | 1,016 | A seed baseline, when present, does not fill this literature-evidence gap |

Counts are **task packages**, not unique mathematical problems or independent
papers. Several papers have packages for the same mathematical construction.
An inherited reference is not necessarily the best number reported by the paper
that names a package. All records use `current_sota: not_assessed`; none are
promoted to `verified_current_sota`. `arena_reproduced_references` is zero because
Arena has not executed these checks. This does not erase the 34 upstream receipts.

`status=ok` in the [source smoke report](https://github.com/IMRUNya/autoresearch-tasks/blob/995768fc462b8e327f90e6762846cc6ccb06cc2c/validation/suite-report.json)
means a usable score was returned. It can coexist with `valid: null`; it is not
evidence of validity, benchmark quality, or successful paper reproduction. No
hostnames, interpreter paths or credentials from the report are copied.

## Examples and comparison boundaries

| Task | Numeric anchor | Necessary interpretation |
| --- | --- | --- |
| AlphaEvolve circle packing, n = 26 | Published sum of radii 2.6358627564136983; recorded seed 2.1406666666666663 | Unit square, exact task constraints; local geometry uses strict checks. A normalized SCiEL fitness or relaxed-overlap verifier is not the same metric. |
| AlphaEvolve matrix multiplication 4 × 4 × 4 | Published rank 48; recorded seed rank 64 | Gaussian half-integer coefficients, including complex values; exact coefficient-identity checking. This is not a claim about unrestricted real tensor rank. |
| CoEvo oscillation 1 | Recorded seed NMSE 0.09591592602181821 | Test-ID score after fitting ten parameters on train. Published numeric reference not extracted. Search sees this test-ID metric, so it is not an independent final audit split. |
| A2DEPT Van der Pol integration | Recorded seed 5.353009565958034 | Local score is −log10(relative endpoint error) − 0.5 log10(function calls). Recreated protocol, not a paper result. |
| Promptbreeder GSM8K package | Recorded seed 1.0 | Upstream documentation reports a five-item model smoke sample. This is not 100% performance on the full GSM8K test set. |
| CORAL CloudCast package | Recorded seed 0.0009652509652509653 | A maximizing wrapper fitness, not the paper's raw cross-cloud transfer cost. |

References preserve the **raw task score**, while a minimized task's
`combined_score` can be its negation. The smoke script falls back to selected
fitness when raw `score` is absent; unfamiliar wrappers therefore remain
`reported_score_or_selected_fitness`. Paper metric labels do not prove metric
equivalence. Two especially easy mistakes are explicitly corrected in labels:
the distance ratio is **squared**, and Heilbronn scores use normalized triangle
area. The notebook C3 `abs(max(convolution))` and signed-absolute C3′
`max(abs(convolution))` remain separate references.

Every anchor sets `automatic_comparison: false`. A future result may be compared
only after matching the task, candidate domain, evaluator and dependencies,
dataset/split/instance IDs, metric transformation, tolerances, model and sample
settings, budgets and validity rules. Current data do not justify a cross-task
bar chart of raw scores, an automatic percentage improvement, or a universal
participant ranking. Repeated trials and uncertainty estimates are absent.

## Evaluation size

423 packages expose usable size metadata, with its interpretation preserved:
77 generated instance counts, 20 declared public-case counts, 13 configured caps,
172 configurable LLM defaults, 122 single mathematical constructions, 11 named
initial-value problems and 8 regression test-ID row counts. The remaining 715
are marked `not_recorded`; task dimensions are never relabeled as test counts.

For LLM tasks, current source default `ARTASK_LLM_SAMPLES=10` is distinct from
the historical report's five-item smoke configuration. The latter is sourced
from [RESULTS.md](https://github.com/IMRUNya/autoresearch-tasks/blob/995768fc462b8e327f90e6762846cc6ccb06cc2c/docs/RESULTS.md),
not inferred from a score of 1.0. Exact sampled item IDs were not preserved in
the imported report. Regression train, test-ID and test-OOD counts carry
separate CSV hashes; a row count is not a count of independent scientific tasks.

## Rebuild and validate

```sh
# Read-only source extraction from a clean checkout at the required commit.
python scripts/build_references.py /path/to/autoresearch-tasks

# Offline CI/API validation; no private checkout, network or evaluator needed.
python -m arena.references validate
python -m pytest tests/test_references.py -q
```

The builder fails on another source commit, modified tracked source files,
catalog/index digest mismatches, or an unreviewed family containing `published`.
It only recognizes the explicit `published` field for literature references;
dimensions, budgets and generic targets cannot silently become SOTA values.
The reader validates complete task coverage, catalog revision/digest binding,
task direction/protocol, source URLs/digests, finite numbers, honest coverage
counts, reproduction status and the distinction between recorded smoke and
scientific comparison. The tests use only the distributed snapshot.

The source narrative says “18” notebook checks while its JSON receipt has 19
rows; our count uses the 19 individually bound rows. This is recorded evidence,
not a claim that Arena has independently rerun their verifier or search.
