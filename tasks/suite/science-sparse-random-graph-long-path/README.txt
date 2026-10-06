# Long paths above the random-graph phase transition

**Source collection:** [Problem-bank constructions: graphs and set systems: source-based research tasks](../../papers/science-prize_c.md)\
**Task id:** `science-sparse-random-graph-long-path`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> a nonempty ordered list of distinct vertices in 0..99 forming a simple path in the pinned graph; all consecutive pairs must be edges. Maximize path vertex count. No path-closing edge is required. A locally generated G(100,1.8/100) sample, using random.Random(748), is pinned. The finite path score certifies a lower bound for this one graph, without proving a high-probability asymptotic result.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> a nonempty ordered list of distinct vertices in 0..99 forming a simple path in the pinned graph; all consecutive pairs must be edges. Maximize path vertex count. No path-closing edge is required.

## State of the art

No value is published for this instance, which was fixed for this dataset; the task compares search methods. Miklós Ajtai, János Komlós and Endre Szemerédi (1981, The longest path in a random graph) study the underlying problem.

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

- [The longest path in a random graph](https://scholarship.libraries.rutgers.edu/esploro/outputs/journalArticle/The-longest-path-in-a-random/991031550002004646), Miklós Ajtai, János Komlós and Endre Szemerédi (1981)

Parameters: `{"n": 100, "edges": [[0, 10], [0, 27], [0, 80], [1, 59], [2, 50], [2, 74], [3, 12], [3, 18], [3, 62], [3, 87], [4, 48], [4, 72], [4, 89], [5, 11], [6, 36], [8, 13], [8, 45], [8, 52], [8, 94], [9, 26], [9, 47], [9, 78], [10, 81], [11, 18], [11, 21], [11, 84], [12, 22], [12, 65], [12, 83], [13, 30], [13, 76], [15, 82], [17, 35], [19, 38], [19, 49], [19, 61], [19, 96], [20, 52], [21, 23], [21, 58], [22, 33], [22, 48], [24, 29], [24, 31], [24, 55], [24, 58], [24, 89], [25, 82], [26, 44], [26, 69], [30, 45], [30, 70], [32, 96], [33, 55], [34, 66], [35, 38], [35, 93], [36, 81], [37, 42], [37, 70], [39, 59], [40, 69], [40, 97], [41, 80], [42, 44], [42, 48], [42, 68], [43, 53], [44, 50], [46, 50], [46, 73], [46, 97], [47, 78], [48, 77], [49, 59], [50, 59], [50, 62], [51, 57], [53, 68], [53, 80], [56, 58], [58, 95], [60, 65], [60, 90], [61, 88], [62, 90], [68, 81], [69, 90], [70, 92], [74, 85], [75, 82]], "edge_probability": [9, 500]}`

## Labels

Scientific contribution: `method` (tier 2); artifact `construction`, domain `mathematics`, data `synthetic`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Understand the emergence of long paths in sparse random graphs.

Why it matters: The cited paper investigates this mathematical problem as a research objective. The task evaluates a finite construction or certificate for the same quantity, with the local restriction stated explicitly.

- [Miklós Ajtai, János Komlós and Endre Szemerédi, The longest path in a random graph (1981)](https://scholarship.libraries.rutgers.edu/esploro/outputs/journalArticle/The-longest-path-in-a-random/991031550002004646): Main research objective: Understand the emergence of long paths in sparse random graphs. Task connection: A locally generated G(100,1.8/100) sample, using random.Random(748), is pinned. The finite path score certifies a lower bound for this one graph, without proving a high-probability asymptotic result.

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

- paper: https://scholarship.libraries.rutgers.edu/esploro/outputs/journalArticle/The-longest-path-in-a-random/991031550002004646 (Miklós Ajtai, János Komlós and Endre Szemerédi, The longest path in a random graph (1981). Author-archive abstract and original introduction study linear-length paths just above the giant-component threshold in G(n,p).)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0701-0800.md#JSP-000748 (JSP-000748; pinned revision bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2. Independently paraphrased finite adaptation; catalog contributor claims are not accepted as proof.)

## Limitations

- Independent finite computational adaptation. Not a Lean proof, prize submission, general conjecture solution, or guarantee of novelty.
- A locally generated G(100,1.8/100) sample, using random.Random(748), is pinned. The finite path score certifies a lower bound for this one graph, without proving a high-probability asymptotic result.
- Candidate Python code is trusted code; the evaluator process is not a security sandbox.
