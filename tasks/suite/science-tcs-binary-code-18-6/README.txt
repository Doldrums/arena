# Binary error-correcting codes of length 18 and distance 6

**Source collection:** [Theoretical computer science: source-based research tasks](../../papers/science-tcs.md)\
**Task id:** `science-tcs-binary-code-18-6`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

Construct the largest possible collection of 18-bit words with pairwise Hamming distance at least 6, the extremal quantity A_2(18,6). Both linear and nonlinear codes are allowed. Every pair is checked exactly using integer XOR and population count. The initial Reed-Muller construction has 32 words; a 512-word extended quadratic-residue construction is independently verified as a reference.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> nonempty list of distinct integers in [0, 2**N). Each integer encodes one N-bit binary codeword, including leading zeros. Every pair must have Hamming distance at least MINIMUM_DISTANCE. Linear and nonlinear codes are allowed. Score: number of codewords, maximized.

Parameters: `{"n": 18, "minimum_distance": 6, "reference": 512}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `theoretical_computer_science`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine large binary codes of length 18 with minimum Hamming distance six.

Why it matters: The maximum possible size of distance-constrained binary codes is the central extremal problem of the source.

- [Semidefinite code bounds based on quadruple distances](https://arxiv.org/abs/1005.4959): Main research objective: Bound the maximum size of binary codes with prescribed length and minimum distance. Task connection: The local task constructs length-18, distance-six codes, giving lower bounds. The paper chiefly derives upper bounds; the directions are complementary, not the same algorithm or claimed record.

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

- paper: https://arxiv.org/abs/1005.4959 (Gijswijt, Mittelmann and Schrijver, Semidefinite code bounds based on quadruple distances (2012): definition of A(n,d), and the upper bound A(18,6) <= 673.)
- benchmark: https://aeb.win.tue.nl/codes/binary-1.html (Brouwer's table of general binary codes, row n=18 and column d=6, lists 512..673; inspected 2026-09-20. Used as dated research context, not as an evaluator-enforced bound.)
- benchmark: https://www.etsi.org/deliver/etsi_TS/102300_102399/10236101/02.03.01_60/ts_10236101v020301p.pdf (ETSI TS 102 361-1 V2.3.1, Annex B.3.2, printed page 132, equation (B.2): primitive (17,9,5) quadratic-residue generator g(x)=x^8+x^5+x^4+x^3+1. Tests use all nine message bits and append even parity to obtain a verified (18,512,6) reference, rather than the standard's shortened (16,7,6) code.)

## Limitations

- The source paper derives upper bounds with semidefinite programming. This task recreates its finite code-construction question and objective, not its SDP algorithm or experiments.
- The reference is reconstructed from a published quadratic-residue generator and verified over every pair; the encoder is a local implementation and is extended to 18 bits rather than shortened as in the ETSI example.
- The 512..673 interval is dated source context, not a claim of an optimum or a permanently current record. The evaluator assumes only the elementary Hamming bound, derived directly from disjoint Hamming balls.
- Improving the 32-word seed or reaching 512 words does not settle the open extremal problem. Any proposed new record needs separate comparison with current constructions and upper bounds.
