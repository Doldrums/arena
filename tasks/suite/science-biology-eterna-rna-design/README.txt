# Biology: Eterna RNA inverse folding

**Source collection:** [Biology and bioinformatics: source-based research tasks](../../papers/science-biology_expansion.md)\
**Task id:** `science-biology-eterna-rna-design`\
**Protocol:** `recreated`\
**Direction:** maximize\

## Task

Search for RNA sequences whose independently evaluated minimum-free-energy structures match Eterna100-v2 targets under a folding-call budget.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

design(dot_bracket, constraints, oracle) -> ACGU sequence of matching length. constraints uses N for free bases. oracle(sequence) returns (MFE_structure,energy), exposes budget, and rejects calls beyond budget. ViennaRNA 2.6.4, 37 C. Objective fraction of exact deterministic MFE matches. Search runs in trusted protocol (direct engine calls cannot be policed in-process).

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `natural_science`, data `public_benchmark`, verification `simulation`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `biology`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Design RNA sequences that fold into a prescribed secondary structure.

Why it matters: Controlling RNA structure supports studies of RNA function and the design of ribozymes and molecular structures.

- [A New Algorithm for RNA Secondary Structure Design](https://pubmed.ncbi.nlm.nih.gov/15095976/): Main research objective: Find RNA sequences predicted to fold into specified target secondary structures. Task connection: RNA-SSD solves the same inverse-folding problem as the local Eterna100-v2 task. Local structures and folding-call limits differ; agreement with a minimum-free-energy model does not establish experimental folding or biological function.

The cited primary paper develops or applies a solution to the stated scientific problem; its task is not merely an agent or general-purpose framework evaluation. Support concerns the scientific problem family, not a claim of new discovery or full-paper reproduction by this local task.

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
- `file:../../.cache/science-biology/B02.json`
- `file:../../.cache/science-biology/B02.manifest.json`
- `py:RNA`

## Sources

- paper: https://pmc.ncbi.nlm.nih.gov/articles/PMC4833017/ (Eterna100 benchmark target construction and RNA secondary-structure inverse-design protocol.)
- repository: https://github.com/eternagame/eterna100-benchmarking (Official author implementation/data reference; evaluator and seed are independently written, not copied.)

## Limitations

- Twelve public length<=100 Eterna100-v2 targets, 64 oracle calls each. Thermodynamic folding is not experimental structure confirmation; no concealed-motif generalization claim. Exact pinned engine required.
- Public source subsets are development-visible. Freeze candidates before evaluating on additional independently chosen studies/instances; trusted candidate execution is not a security sandbox.
- Improving this benchmark is a scientific-method result; it does not alone establish a new biological discovery.
