# Rough integer witnesses inside consecutive prime gaps

**Source collection:** [Problem-bank constructions: graphs and set systems: source-based research tasks](../../papers/science-prize_c.md)\
**Task id:** `science-rough-numbers-in-consecutive-prime-gaps`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> a list aligned with the 32 pinned consecutive-prime pairs. Each entry is either None (no certificate) or an integer STRICTLY between its pair whose least prime factor is at least the prime gap. Supply at least one witness; maximize certified gaps. The verifier checks primality, consecutiveness and every least factor independently. None never asserts nonexistence. Thirty-two consecutive gaps beginning at 10007 are pinned. Some gaps may have no witness and a skipped gap does not prove that. This finite certificate count does not imply a universal all-gap result or the paper’s density estimate.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> a list aligned with the 32 pinned consecutive-prime pairs. Each entry is either None (no certificate) or an integer STRICTLY between its pair whose least prime factor is at least the prime gap. Supply at least one witness; maximize certified gaps. The verifier checks primality, consecutiveness and every least factor independently. None never asserts nonexistence.

## State of the art

No value is published for this instance, which was fixed for this dataset; the task compares search methods. Ayla Gafni and Terence Tao (2025, Rough numbers between consecutive primes) study the underlying problem.

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

- [Rough numbers between consecutive primes](https://arxiv.org/abs/2508.06463), Ayla Gafni and Terence Tao (2025)

Parameters: `{"gaps": [[10007, 10009], [10009, 10037], [10037, 10039], [10039, 10061], [10061, 10067], [10067, 10069], [10069, 10079], [10079, 10091], [10091, 10093], [10093, 10099], [10099, 10103], [10103, 10111], [10111, 10133], [10133, 10139], [10139, 10141], [10141, 10151], [10151, 10159], [10159, 10163], [10163, 10169], [10169, 10177], [10177, 10181], [10181, 10193], [10193, 10211], [10211, 10223], [10223, 10243], [10243, 10247], [10247, 10253], [10253, 10259], [10259, 10267], [10267, 10271], [10271, 10273], [10273, 10289]]}`

## Labels

Scientific contribution: `method` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Find and understand rough integers inside consecutive prime gaps.

Why it matters: The cited paper investigates this mathematical problem as a research objective. The task evaluates a finite construction or certificate for the same quantity, with the local restriction stated explicitly.

- [Ayla Gafni and Terence Tao, Rough numbers between consecutive primes (2025)](https://arxiv.org/abs/2508.06463): Main research objective: Find and understand rough integers inside consecutive prime gaps. Task connection: Thirty-two consecutive gaps beginning at 10007 are pinned. Some gaps may have no witness and a skipped gap does not prove that. This finite certificate count does not imply a universal all-gap result or the paper’s density estimate.

Supported by the inspected primary problem statement, rather than the prize listing or an agent benchmark. Finite progress is not automatically a novel scientific result.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- Exact finite certificate validation; independently implemented from the cited mathematical definition. Resource bounds and source adaptation are recorded per task. No Lean verification or general theorem is claimed.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://arxiv.org/abs/2508.06463 (Ayla Gafni and Terence Tao, Rough numbers between consecutive primes (2025). Author abstract: for almost all consecutive-prime pairs, an interior integer has least prime factor at least the gap; also bounds the exceptional set.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0501-0600.md#JSP-000554 (JSP-000554; pinned revision bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2. Independently paraphrased finite adaptation; catalog contributor claims are not accepted as proof.)

## Limitations

- Independent finite computational adaptation. Not a Lean proof, prize submission, general conjecture solution, or guarantee of novelty.
- Thirty-two consecutive gaps beginning at 10007 are pinned. Some gaps may have no witness and a skipped gap does not prove that. This finite certificate count does not imply a universal all-gap result or the paper’s density estimate.
- Candidate Python code is trusted code; the evaluator process is not a security sandbox.
- The bank’s abbreviated question and Solved label omit the primary paper’s almost-all qualifier. The local task preserves that limitation; e.g. the gap (7,11) has no such witness.
