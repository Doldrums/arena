# Constant-weight ternary admissible-set construction

**Paper:** Monte Carlo Tree Search for Comprehensive Exploration in LLM-Based Automatic Heuristic Design (https://arxiv.org/pdf/2501.08603)\
**Task id:** `mcts-ahd-asp-constructive`\
**Protocol:** `original`\
**Direction:** maximize\

## Task

Evolve the priority rule used by the pinned MCTS-AHD symmetric greedy constructor for constant-weight ternary admissible sets at n=15, w=10. Maximize the cardinality of the expanded set. This is a distinct problem from narrow admissible integer tuples.

Benchmark named in the paper: Constant-weight ternary admissible set I(15,10). Paper metric: expanded admissible set cardinality.

## Candidate interface

priority(vector, n, w) -> finite float. The pinned MCTS-AHD solver greedily constructs a symmetric constant-weight admissible set of ternary vectors at n=15, w=10. Score: expanded set cardinality. This is not the prime-residue admissible-tuple problem.

Parameters: `{"checkout": "{checkout}", "problem": "asp_constructive", "max_instances": 2, "iterations": 5, "ants": 10, "random_seed": 1234, "black_box": false}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `program`, domain `mathematics`, data `none`, verification `simulation`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Evaluation protocol

Evaluation uses pinned implementation components through this repository's local adapter. The task contract and notes specify any reconstructed loop, reduced budget, checkpoint or data changes; source identity does not establish the exact paper experiment revision. Fetch the pinned source with `python3 run.py setup mcts-ahd-asp-constructive`; data preparation is described in the notes.

- MCTS-AHD Appendix B.1 Eq. (10) defines constant-weight ternary admissible sets. The original training solver uses n=15, w=10 and a symmetry-restricted greedy construction; the local adapter evaluates that single training instance, not the four-size validation profile or a complete MCTS search.
- The upstream construction code and recovered priority baseline retain their pinned source credits. The local adapter checks finite score and actual candidate calls but does not independently certify the expanded set; validity remains unknown.
- MCTS-AHD admissible sets consist of constant-weight ternary vectors under the triple-coordinate witness rule. The restored task uses the pinned original symmetry-block greedy evaluator at n15,w10; it is distinct from prime-residue narrow tuples. The extracted source seed returns1842 on the original route. Finite output and actual candidate calls are checked, but no independent solution certificate is available, so validity remains unknown rather than true.

## Implementation credit

Local adapter: `adapters/recovered/optimization_original.py`. The adapter files belong to this repository.

Borrowed runtime: https://github.com/zz1358m/MCTS-AHD-master at `ee9c4f424503c65a5fd2b899e6620ce86079fedb`.

See `problem.json` for immutable source receipts and component scope. Implementation provenance does not establish that this is the paper authors' experiment revision.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:numpy`
- `checkout:zz1358m/MCTS-AHD-master@ee9c4f424503c65a5fd2b899e6620ce86079fedb`
- `py:scipy`
- `py:torch`

## Sources

- paper: https://arxiv.org/pdf/2501.08603 (Appendix B.1 Eq. (10); Appendix F, admissible-set experiments)
- repository: https://github.com/zz1358m/MCTS-AHD-master/tree/ee9c4f424503c65a5fd2b899e6620ce86079fedb (problems/asp_constructive/eval.py)

## Limitations

- Execution interface inspected in pinned source. Full paper experiments have not been reproduced here.
- The single n=15,w=10 original training profile is evaluated through a local adapter. A finite source-solver score is not an independent certificate; validity remains unknown.
- MCTS-AHD admissible sets consist of constant-weight ternary vectors under the triple-coordinate witness rule. The restored task uses the pinned original symmetry-block greedy evaluator at n15,w10; it is distinct from prime-residue narrow tuples. The extracted source seed returns1842 on the original route. Finite output and actual candidate calls are checked, but no independent solution certificate is available, so validity remains unknown rather than true.
