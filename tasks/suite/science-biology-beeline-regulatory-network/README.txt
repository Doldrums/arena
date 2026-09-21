# Biology: Regulatory network inference from expression

**Source collection:** [Biology and bioinformatics: source-based research tasks](../../papers/science-biology_expansion.md)\
**Task id:** `science-biology-beeline-regulatory-network`\
**Protocol:** `recreated`\
**Direction:** maximize\

## Task

Rank directed regulator-target hypotheses from the official BEELINE GSD expression example and score all allowed edges using tie-aware average precision.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

infer_network(expression, genes, allowed_regulators, optional_ordering) -> list(regulator,target,finite_score). expression cells x genes. No self edges/unknown IDs/duplicates. Unsubmitted edges tie below submitted scores. Maximize tie-grouped average precision across all allowed directed edges; incomplete biological references caveat retained.

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `natural_science`, data `simulator`, verification `sampled`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `biology`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.

Underlying problem: Infer directed gene-regulatory interactions from expression measurements.

Why it matters: Understanding transcriptional regulation is a substantive biological goal, but that does not by itself validate a synthetic benchmark adaptation.


The local task uses the official BEELINE GSD synthetic expression example. The cited BEELINE paper primarily evaluates network-inference methods. GENIE3 addresses regulatory inference more broadly, but this review did not establish that the particular synthetic GSD instance addresses a substantive biological question rather than serving as a method testbed. No qualifying primary-goal evidence is established for this local task in this review; this is not a finding that the broader subject is unimportant.

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
- `file:../../.cache/science-biology/B11.json`
- `file:../../.cache/science-biology/B11.manifest.json`

## Sources

- paper: https://www.nature.com/articles/s41592-019-0690-6 (BEELINE Methods: simulated/curated networks and precision-recall evaluation.)
- repository: https://github.com/Murali-group/Beeline (Official author implementation/data reference; evaluator and seed are independently written, not copied.)

## Limitations

- Initial official example uses simulated expression grounded in a curated developmental network, not measured expression. One complete network, no cross-network generalization claim. All genes permitted as regulators; no true-regulator list leaked.
- Public source subsets are development-visible. Freeze candidates before evaluating on additional independently chosen studies/instances; trusted candidate execution is not a security sandbox.
- Improving this benchmark is a scientific-method result; it does not alone establish a new biological discovery.
