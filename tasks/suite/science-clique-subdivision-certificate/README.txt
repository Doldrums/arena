# Large clique subdivisions in a pinned graph

**Source collection:** [Problem-bank constructions: graphs and set systems: source-based research tasks](../../papers/science-prize_c.md)\
**Task id:** `science-clique-subdivision-certificate`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> {'branches': distinct vertices, 'paths': one simple path for each unordered pair of branches}. Path endpoints must be their branch pair; all path interiors must be pairwise disjoint and avoid every branch. All consecutive path vertices must be adjacent in the pinned graph. Maximize number of branch vertices. A local G(24,0.4) sample (random.Random(585)) is pinned. A certificate is a lower bound on this host’s largest subdivision order; no theorem about all chromatic graphs or reproduction of the paper’s proof is claimed.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> {'branches': distinct vertices, 'paths': one simple path for each unordered pair of branches}. Path endpoints must be their branch pair; all path interiors must be pairwise disjoint and avoid every branch. All consecutive path vertices must be adjacent in the pinned graph. Maximize number of branch vertices.

## State of the art

No value is published for this instance, which was fixed for this dataset; the task compares search methods. Jacob Fox, Choongbum Lee and Benny Sudakov (2011, Chromatic number, clique subdivisions, and the conjectures of Hajós and Erdős–Fajtlowicz) study the underlying problem.

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

- [Chromatic number, clique subdivisions, and the conjectures of Hajós and Erdős–Fajtlowicz](https://arxiv.org/abs/1107.1920), Jacob Fox, Choongbum Lee and Benny Sudakov (2011)

Parameters: `{"n": 24, "edges": [[0, 1], [0, 3], [0, 5], [0, 9], [0, 10], [0, 12], [0, 20], [0, 22], [1, 4], [1, 5], [1, 6], [1, 14], [1, 15], [1, 17], [1, 19], [1, 20], [1, 22], [2, 3], [2, 5], [2, 7], [2, 8], [3, 7], [3, 9], [3, 10], [3, 11], [3, 13], [3, 14], [3, 16], [3, 19], [3, 20], [4, 6], [4, 9], [4, 11], [4, 12], [4, 13], [4, 14], [4, 15], [4, 18], [4, 19], [4, 20], [4, 21], [4, 23], [5, 7], [5, 8], [5, 9], [5, 12], [5, 14], [5, 15], [5, 17], [5, 18], [5, 19], [5, 20], [5, 21], [6, 10], [6, 13], [6, 16], [6, 20], [6, 21], [6, 22], [7, 15], [7, 16], [7, 19], [7, 22], [8, 9], [8, 15], [8, 18], [8, 20], [8, 22], [9, 11], [9, 12], [9, 15], [9, 17], [9, 21], [9, 23], [10, 12], [11, 13], [11, 14], [11, 17], [11, 18], [11, 20], [11, 22], [12, 13], [12, 15], [12, 16], [12, 22], [12, 23], [13, 16], [14, 16], [14, 17], [14, 18], [14, 19], [15, 16], [15, 19], [15, 20], [15, 22], [16, 18], [16, 21], [17, 22], [18, 19], [18, 20], [19, 21], [20, 22], [20, 23], [21, 22], [21, 23], [22, 23]]}`

## Labels

Scientific contribution: `method` (tier 2); artifact `construction`, domain `mathematics`, data `synthetic`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Understand how large topological complete graphs must be relative to a host’s chromatic complexity.

Why it matters: The cited paper investigates this mathematical problem as a research objective. The task evaluates a finite construction or certificate for the same quantity, with the local restriction stated explicitly.

- [Jacob Fox, Choongbum Lee and Benny Sudakov, Chromatic number, clique subdivisions, and the conjectures of Hajós and Erdős–Fajtlowicz (2011 preprint)](https://arxiv.org/abs/1107.1920): Main research objective: Understand how large topological complete graphs must be relative to a host’s chromatic complexity. Task connection: A local G(24,0.4) sample (random.Random(585)) is pinned. A certificate is a lower bound on this host’s largest subdivision order; no theorem about all chromatic graphs or reproduction of the paper’s proof is claimed.

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

- paper: https://arxiv.org/abs/1107.1920 (Jacob Fox, Choongbum Lee and Benny Sudakov, Chromatic number, clique subdivisions, and the conjectures of Hajós and Erdős–Fajtlowicz (2011 preprint). Abstract defines sigma(G), the largest clique-subdivision order, and studies its relation to chromatic number.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0501-0600.md#JSP-000585 (JSP-000585; pinned revision bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2. Independently paraphrased finite adaptation; catalog contributor claims are not accepted as proof.)

## Limitations

- Independent finite computational adaptation. Not a Lean proof, prize submission, general conjecture solution, or guarantee of novelty.
- A local G(24,0.4) sample (random.Random(585)) is pinned. A certificate is a lower bound on this host’s largest subdivision order; no theorem about all chromatic graphs or reproduction of the paper’s proof is claimed.
- Candidate Python code is trusted code; the evaluator process is not a security sandbox.
