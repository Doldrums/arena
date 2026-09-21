# Biology: Perturb-seq response generalization

**Source collection:** [Biology and bioinformatics: source-based research tasks](../../papers/science-biology_expansion.md)\
**Task id:** `science-biology-gears-perturbation`\
**Protocol:** `recreated`\
**Direction:** minimize\

## Task

Predict expression shifts for complete held-out genetic perturbations using measured GEARS study pseudobulks and training-only gene selection.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

predict_shift(training_profiles, training_perturbations, query_perturbations, gene_context) -> finite query x gene matrix of expression shifts relative to controls. Whole perturbation groups are disjoint. Minimize query MSE divided by error of training-perturbation-mean baseline; report mean-reference-corrected perturbation retrieval.

## Labels

Scientific contribution: `method` (tier 2); artifact `model`, domain `natural_science`, data `real_measurements`, verification `sampled`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `biology`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Predict cellular transcriptional responses to unseen genetic perturbations.

Why it matters: Perturbation-response prediction can help identify gene interactions and prioritize experiments on cellular mechanisms.

- [Predicting transcriptional outcomes of novel multigene perturbations with GEARS](https://www.nature.com/articles/s41587-023-01905-6): Main research objective: Predict expression responses to previously unmeasured single- and multigene perturbations. Task connection: The local task uses measured GEARS study pseudobulks and holds out complete perturbations. It tests a reduced gene-expression prediction problem rather than reproducing the paper's full network or all multigene results.

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
- `file:../../.cache/science-biology/B03.json`
- `file:../../.cache/science-biology/B03.manifest.json`

## Sources

- paper: https://www.nature.com/articles/s41587-023-01905-6 (GEARS Methods: data processing, perturbation splits and combinatorial prediction.)
- repository: https://github.com/snap-stanford/GEARS (Official author implementation/data reference; evaluator and seed are independently written, not copied.)
- paper: https://doi.org/10.1038/s41587-025-02777-8 (Systema: correcting shared perturbation effects and reporting perturbation-specific evaluation.)

## Limitations

- Independent training-mean-normalized error and retrieval metric inspired by Systema; not the entire published GEARS/Systema metric suite. Official Dataverse source access returned403 during preparation.
- Public source subsets are development-visible. Freeze candidates before evaluating on additional independently chosen studies/instances; trusted candidate execution is not a security sandbox.
- Improving this benchmark is a scientific-method result; it does not alone establish a new biological discovery.
