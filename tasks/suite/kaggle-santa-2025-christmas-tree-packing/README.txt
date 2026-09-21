# Santa 2025: Christmas tree packing (n = 1..200)

**Paper:** Santa 2025 - Christmas Tree Packing Challenge (Kaggle competition) (https://www.kaggle.com/competitions/santa-2025)\
**Task id:** `kaggle-santa-2025-christmas-tree-packing`\
**Protocol:** `recreated_verified`\
**Direction:** minimize\

## Task

For every n from 1 to 200 place n copies of the competition's fixed 15-vertex tree polygon (rotations allowed, no overlaps, coordinates within [-100, 100]) so that the bounding square of each configuration is as small as possible; the score is the sum over n of (bounding-square area / n), lower is better.

Benchmark named in the paper: Kaggle Santa 2025 - Christmas Tree Packing Challenge. Paper metric: sum over n of bounding-square area / n.

## Candidate interface

construct(n) -> array of shape (n, 3): rows (x, y, deg) placing n copies of the fixed Christmas-tree polygon without overlap (deg rotates about the tree origin, x and y within [-100, 100]); called once for every n from n_min to n_max

Parameters: `{"n_min": 1, "n_max": 200, "reference": 176.60550959158516}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `leaderboard`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Evaluation protocol

Reimplemented in this repository and cross-checked against the paper's published constructions/values.

- The reference value is the competition's getting-started sample submission scored with the official metric; the seed grid scores 162.58.
- Independent implementation of the Kaggle Santa 2025 metric (same polygon, 1e18 scaling, touch-but-not-overlap rule, bounding-square area over n summed over n = 1..200); reproduces the official metric's doctest value and the getting-started sample submission's score exactly (validation/santa-2025-crosscheck.json).

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:numpy`
- `py:shapely`

## Sources

- benchmark: https://www.kaggle.com/competitions/santa-2025 (Competition overview and evaluation page (task statement, metric definition, submission format))
- benchmark: https://www.kaggle.com/code/inversion/santa-2025-getting-started (Getting-started notebook (tree geometry, collision rule, greedy sample submission))
- repository: https://github.com/jsebdev/kaggle_santa_challenge_2025/tree/9f0fff6e53fb653dc067214ff19bcb647ee54311 (santa-2025-metric.py (official metric, shapely 2.1.2), sample_submission.csv)

## Limitations

- The evaluator is an independent reimplementation of the competition metric (same polygon, scaling factor, overlap rule and bounding-square formula) and reproduces the official code's doctest value and the sample submission's score exactly; it is not the Kaggle scoring service.
- No leaderboard value is embedded; the reference value is the getting-started sample submission (176.60550959158516).
