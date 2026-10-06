# High-quality coprime abc triples

**Source collection:** [Problem-bank constructions: additive combinatorics: source-based research tasks](../../papers/science-prize_a.md)\
**Task id:** `science-coprime-abc-quality`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> [a,b,c], positive Python integers <=1000000000000, a<=b, a+b=c, gcd(a,b)=1. Maximize log(c)/log(rad(a*b*c)). The radical is the product of DISTINCT prime factors and is independently factored exactly; only the logarithmic score uses floating arithmetic. Search coprime positive triples a+b=c with c<=10^12, maximizing log(c)/log(rad(abc)). Finite high quality cannot disprove the conjecture, which allows finitely many exceptions at each exponent. The optimum is Reyssat's quality 1.62991 for 2 + 3^10*109 = 23^5; complete tables of high-quality triples show nothing better below 10^20, so this is a rediscovery task.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> [a,b,c], positive Python integers <=1000000000000, a<=b, a+b=c, gcd(a,b)=1. Maximize log(c)/log(rad(a*b*c)). The radical is the product of DISTINCT prime factors and is independently factored exactly; only the logarithmic score uses floating arithmetic.

## State of the art

Reyssat's triple 2 + 3^10·109 = 23^5 (c = 6,436,343) has quality 1.62991. De Smit's complete tables of triples with quality at least 1.4 and at most twenty digits, surveyed by Martin and Miao, contain nothing of higher quality, so it is the maximum for c <= 10^12.

Reference value: proven optimum `1.6299116841` (reviewed 2026-09-24).

- [abc triples](https://arxiv.org/abs/1409.2974), Greg Martin, Winnie Miao (2014)
- [ABC triples (tables of high-quality triples)](https://www.math.leidenuniv.nl/~desmit/abc/), Bart de Smit (maintained)

Parameters: `{"maximum": 1000000000000}`

## Labels

Scientific contribution: `rediscovery` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Construct and understand integer triples with unusually small radical relative to height.

Why it matters: The abc conjecture of Masser and Oesterlé is a central open problem in number theory; triples of high quality are the extremal examples that test it, and finding them is the main goal of the cited paper.

- [LLL & ABC](https://arxiv.org/abs/math/0307322): Main research objective: Find abc triples of high quality, i.e. good examples for the abc and Szpiro conjectures, by lattice reduction. Task connection: Search coprime positive triples a+b=c with c<=10^12, maximizing log(c)/log(rad(abc)). Finite high quality cannot disprove the conjecture, which allows finitely many exceptions at each exponent.

A problem-focused primary paper (Tim Dokchitser, Journal of Number Theory 107 (2004), DOI 10.1016/j.jnt.2004.02.003) is devoted to finding high-quality abc triples, the quantity this task maximizes. No novelty claim is implied.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- Independent finite certificate evaluator and local seed; no source implementation copied. Exact constraints are verified, but no optimality, general theorem, Lean proof, published record, or prize eligibility is claimed. See task sources and adaptation limitations.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://arxiv.org/abs/1409.2974 (Greg Martin and Winnie Miao, abc triples. Primary survey full text inspected: p.3 defines logarithmic quality, p.10 explicitly uses the starter (1,8,9). Author computational catalog https://pub.math.leidenuniv.nl/~smitbde/abc/ also inspected.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0001-0100.md#JSP-000010 (JSP-000010; pinned discovery record, independently paraphrased. Source wording and paper-specific differences are explained in limitations.)

## Limitations

- Solved finite case: Reyssat's triple 2 + 3^10·109 = 23^5 (c = 6,436,343) has quality 1.62991.
- Search coprime positive triples a+b=c with c<=10^12, maximizing log(c)/log(rad(abc)). Finite high quality cannot disprove the conjecture, which allows finitely many exceptions at each exponent.
- All computations are bounded. A valid certificate is not an optimality proof, new theorem, Lean proof, or evidence of prize eligibility. Candidate Python is trusted research code.
