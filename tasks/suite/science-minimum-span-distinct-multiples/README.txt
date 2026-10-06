# Pack distinct multiples of a fixed integer set

**Source collection:** [Problem-bank constructions: graphs and set systems: source-based research tasks](../../papers/science-prize_c.md)\
**Task id:** `science-minimum-span-distinct-multiples`\
**Protocol:** `recreated_verified`\
**Direction:** minimize\

## Task

construct() -> ten DISTINCT positive Python integers <=1000000, aligned with the pinned input [6,10,14,15,21,22,26,33,35,39]. Each representative must be divisible by its corresponding input. Minimize max(representatives)-min(representatives), the length of their closed enclosing interval. The bank’s full-matching minimum-span question is used literally for one fixed ten-element input and a representative cap. The cited related paper instead optimizes guaranteed partial cardinality in every fixed-length interval. Its theorem is not evidence of a solution or precise importance classification for this changed objective.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> ten DISTINCT positive Python integers <=1000000, aligned with the pinned input [6,10,14,15,21,22,26,33,35,39]. Each representative must be divisible by its corresponding input. Minimize max(representatives)-min(representatives), the length of their closed enclosing interval.

## State of the art

No value is published for this instance, which was fixed for this dataset; the task compares search methods. Wouter van Doorn, Yanyang Li and Quanyu Tang (2026, Optimal bounds for an Erdős problem on matching integers to distinct multiples) study the underlying problem.

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

- [Optimal bounds for an Erdős problem on matching integers to distinct multiples](https://arxiv.org/abs/2603.28636), Wouter van Doorn, Yanyang Li and Quanyu Tang (2026)

Parameters: `{"divisors": [6, 10, 14, 15, 21, 22, 26, 33, 35, 39], "maximum": 1000000}`

## Labels

Scientific contribution: `method` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.

Underlying problem: Pack divisibility representatives of a finite integer set into a short interval.

Why it matters: Precise attribution is verified, but direct primary-goal evidence for this exact task is not established.


The bank’s full-matching minimum-span question is used literally for one fixed ten-element input and a representative cap. The cited related paper instead optimizes guaranteed partial cardinality in every fixed-length interval. Its theorem is not evidence of a solution or precise importance classification for this changed objective.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- Exact finite certificate validation; independently implemented from the cited mathematical definition. Resource bounds and source adaptation are recorded per task. No Lean verification or general theorem is claimed.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://arxiv.org/abs/2603.28636 (Wouter van Doorn, Yanyang Li and Quanyu Tang, Optimal bounds for an Erdős problem on matching integers to distinct multiples (2026). Section 1 defines divisibility matching of an arbitrary finite A into interval integers. The main result determines guaranteed PARTIAL matching cardinality in every open interval of length twice max(A).)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0501-0600.md#JSP-000578 (JSP-000578; pinned revision bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2. Independently paraphrased finite adaptation; catalog contributor claims are not accepted as proof.)

## Limitations

- Independent finite computational adaptation. Not a Lean proof, prize submission, general conjecture solution, or guarantee of novelty.
- The bank’s full-matching minimum-span question is used literally for one fixed ten-element input and a representative cap. The cited related paper instead optimizes guaranteed partial cardinality in every fixed-length interval. Its theorem is not evidence of a solution or precise importance classification for this changed objective.
- Candidate Python code is trusted code; the evaluator process is not a security sandbox.
- Primary-source credit is explicitly related mathematical background, not a claim that this exact full-matching movable-window objective is the cited paper’s main problem. The preprint acknowledges a ChatGPT GPT-5.4 Pro proof draft and Aristotle Lean formalization; no such code is reused locally.
