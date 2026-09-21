# Binary error-correcting codes of length 17 and distance 6

**Source collection:** [Theoretical computer science: source-based research tasks](../../papers/science-tcs.md)\
**Task id:** `science-tcs-binary-code-17-6`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

Construct the largest set of 17-bit words with pairwise Hamming distance at least 6, the extremal quantity A_2(17,6). Brouwer's table lists 258..340: the lower bound is Milshtein's 2019 nonlinear code, the upper bound comes from semidefinite programming. The 256-word linear reference is the [18,9,6] extended quadratic-residue code shortened by one coordinate; the seed has 32 words.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> nonempty list of distinct integers in [0, 2**N). Each integer encodes one N-bit binary codeword, including leading zeros. Every pair must have Hamming distance at least MINIMUM_DISTANCE. Linear and nonlinear codes are allowed. Score: number of codewords, maximized.

Parameters: `{"n": 17, "minimum_distance": 6, "reference": 256}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `theoretical_computer_science`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine large binary codes of length 17 with minimum Hamming distance six.

Why it matters: The maximum possible size of distance-constrained binary codes is the central extremal problem of the source.

- [Semidefinite code bounds based on quadruple distances](https://arxiv.org/abs/1005.4959): Main research objective: Bound the maximum size of binary codes with prescribed length and minimum distance. Task connection: The local task constructs length-17, distance-six codes, giving lower bounds. The paper chiefly derives upper bounds; the directions are complementary, not the same algorithm or claimed record.

Both concern the extremal code-size problem itself. The citation does not certify the local reference as optimal.

## Evaluation protocol

Reimplemented in this repository and cross-checked against the paper's published constructions/values.

- Independent exact pairwise Hamming-distance verifier for A_2(18,6). The seed is a 32-word Reed-Muller subconstruction. Tests reconstruct the 512-word extended quadratic-residue reference using g(x)=x^8+x^5+x^4+x^3+1 and verify all 130,816 pairs. The 2012 source establishes an upper bound of 673, and Brouwer's table lists 512..673 when inspected on 2026-09-20; the evaluator does not assume that bound or claim global optimality. This task searches constructions, not the paper's semidefinite upper-bound program.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:numpy`

## Sources

- paper: https://arxiv.org/abs/1005.4959 (Gijswijt, Mittelmann and Schrijver: definition of A(n,d) and semidefinite upper bounds.)
- benchmark: https://aeb.win.tue.nl/codes/binary-1.html (Brouwer's table, n=17, d=6: 258..340 (lower bound Milshtein 2019), inspected 2026-09-20.)

## Limitations

- The 256-word reference is verified in tests by shortening the extended quadratic-residue code; the 258-word record is not reproduced here.
- A code larger than 258 words would be a new lower bound and needs independent verification against current tables.
