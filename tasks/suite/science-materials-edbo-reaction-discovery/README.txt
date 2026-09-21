# Budgeted EDBO+ reaction-condition discovery

**Source collection:** [Chemistry and materials research: source-based research tasks](../../papers/science-materials_expansion.md)\
**Task id:** `science-materials-edbo-reaction-discovery`\
**Protocol:** `recreated`\
**Direction:** maximize\

## Task

suggest(observations, candidate_conditions, batch_size) -> list of unused integer row indices. Observations have index, yield (percent), cost (released accounting); pool contains categorical base/ligand/solvent and concentration/temperature. One experiment per call, 32 calls on each of three shuffled versions of the full 1,728-experiment BMS campaign. Score: mean area under normalized two-objective hypervolume trajectory (yield maximized, cost minimized). No unqueried outcomes may be accessed.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

suggest(observations, candidate_conditions, batch_size) -> list of unused integer row indices. Observations have index, yield (percent), cost (released accounting); pool contains categorical base/ligand/solvent and concentration/temperature. One experiment per call, 32 calls on each of three shuffled versions of the full 1,728-experiment BMS campaign. Score: mean area under normalized two-objective hypervolume trajectory (yield maximized, cost minimized). No unqueried outcomes may be accessed.

Parameters: `{"proposal_id": "C01"}`

## Labels

Scientific contribution: `method` (tier 2); artifact `optimizer`, domain `natural_science`, data `real_measurements`, verification `sampled`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `chemistry`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.

Underlying problem: Find chemical reaction conditions that balance product yield and experimental cost.

Why it matters: Efficient reaction development can reduce chemical experimentation and resource use.


The EDBO+ paper explicitly presents and tunes an active-learning platform and web app. The local BMS campaign is a retrospective yield-cost optimizer evaluation; the review has not located a problem-focused paper whose main objective is solving this campaign's substantive chemical-development problem. The paper's separate live yield/enantioselectivity demonstrations are not the local campaign. No qualifying primary-goal evidence is established for this local task in this review; this is not a finding that the broader subject is unimportant.

## Evaluation protocol

Locally authored implementation of the cited scientific task. Source data, generated mathematical instances, reference checks and adaptations are specified below; unit-test fixtures do not establish a benchmark reproduction.

- Independently implemented SCIEL adaptation. Source bundles are required except the specified PFHub and Cantera simulations; no generated replacement data. See docs/MATERIALS_EXPANSION.md for provenance, exact setup blockers and validation scope.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:numpy`
- `file:data/materials-expansion/C01/experiments_yield_and_cost.csv`

## Sources

- paper: https://doi.org/10.1021/jacs.2c08592 (EDBO+ multi-objective Bayesian reaction optimization; yield-cost BMS benchmark.)
- repository: https://github.com/doyle-lab-ucla/edboplus/tree/db06b8dd592056df03ae604da030b080acd32658/examples/publication/BMS_yield_cost (Pinned author preparation, optimization, hypervolume scripts and 1728-row experiment table.)

## Limitations

- Independent SCIEL adaptation of a cited scientific problem; no claim to reproduce author leaderboard scores.
- Candidate and evaluator run in one Python process; data access is separated by API, not an OS sandbox. Isolate evaluator data for adversarial or held-out evaluation.
- One complete experimental reaction campaign is used. Three candidate-pool permutations measure robustness, not transfer to unseen reaction campaigns.
- Costs reproduce the source accounting, not current reagent prices.
