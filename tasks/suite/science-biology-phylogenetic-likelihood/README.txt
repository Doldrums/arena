# Biology: Empirical phylogenetic tree likelihood search

**Source collection:** [Biology and bioinformatics: source-based research tasks](../../papers/science-biology_expansion.md)\
**Task id:** `science-biology-phylogenetic-likelihood`\
**Protocol:** `recreated`\
**Direction:** minimize\

## Task

Construct a valid evolutionary tree for an empirical DNA alignment; an independently written pruning evaluator recomputes its JC69 likelihood.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

infer_tree(alignment, substitution_model, budget_seconds) -> semicolon-terminated Newick tree. Alignment maps taxon names to DNA strings. Each input taxon exactly once; finite branch lengths0..100. Independently calculate JC69 pruning likelihood; minimize mean negative log-likelihood per alignment site. Empirical likelihood is not true-topology accuracy.

## Labels

Scientific contribution: `method` (tier 2); artifact `construction`, domain `natural_science`, data `real_measurements`, verification `simulation`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `biology`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Infer evolutionary relationships from observed DNA sequences.

Why it matters: Evolutionary trees are scientific hypotheses about common ancestry and sequence evolution.

- [Evolutionary trees from DNA sequences: a maximum likelihood approach](https://pubmed.ncbi.nlm.nih.gov/7288891/): Main research objective: Develop feasible maximum-likelihood inference of evolutionary trees from nucleic-acid sequences and evaluate evolutionary hypotheses. Task connection: The local task searches trees for an empirical alignment using independent JC69 likelihood calculations. It is a restricted substitution model and does not establish that the highest-likelihood tree is the true biological history.

The paper directly pursues evolutionary inference; a phylogenetics software-introduction citation alone would not be used as the evidence.

## Evaluation protocol

Locally authored implementation of the cited scientific task. Source data, generated mathematical instances, reference checks and adaptations are specified below; unit-test fixtures do not establish a benchmark reproduction.

- Independently written bounded scientific adaptation. Source data and SHA256 preparation receipts required. See docs/BIOLOGY_EXPANSION.md and task limitations; fixture tests never establish source benchmark reproduction.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:numpy`
- `py:scipy`
- `file:../../.cache/science-biology/B07.json`
- `file:../../.cache/science-biology/B07.manifest.json`

## Sources

- paper: https://pmc.ncbi.nlm.nih.gov/articles/PMC6821337/ (RAxML-NG paper: maximum-likelihood phylogenetic inference; local evaluator uses fixedJC69 rather than upstream GTR+Gamma.)
- repository: https://github.com/amkozlov/ng-tutorial (Official author implementation/data reference; evaluator and seed are independently written, not copied.)

## Limitations

- One complete empirical12-taxon898-site primate tutorial alignment. Not the full paper alignment collection, hidden-clade transfer, or empirical true-tree recovery. Independent JC69 score is not numerically comparable with upstreamGTR+Gamma.
- Public source subsets are development-visible. Freeze candidates before evaluating on additional independently chosen studies/instances; trusted candidate execution is not a security sandbox.
- Improving this benchmark is a scientific-method result; it does not alone establish a new biological discovery.
