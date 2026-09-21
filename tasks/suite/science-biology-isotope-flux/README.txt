# Biology: Isotope-constrained metabolic flux inference

**Source collection:** [Biology and bioinformatics: source-based research tasks](../../papers/science-biology_expansion.md)\
**Task id:** `science-biology-isotope-flux`\
**Protocol:** `recreated`\
**Direction:** minimize\

## Task

Infer steady-state reaction fluxes and uncertainty intervals from isotope measurements using a verified source-specific atom-mapping forward model.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

infer_fluxes(network, atom_maps, training_measurements, training_objective, budget) -> {fluxes,intervals}. network includes stoichiometry, bounds, feasible_initial_fluxes. Enforce S@v tolerance1e-6 and flux bounds. Trusted source-specific isotope simulator produces held-out Gaussian NLL. intervals nflux x2 must contain estimates. Forward-model source/hash required; no synthetic fallback.

## Labels

Scientific contribution: `method` (tier 2); artifact `optimizer`, domain `natural_science`, data `real_measurements`, verification `simulation`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `biology`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Infer intracellular metabolic reaction rates and uncertainty from isotope-labeling observations.

Why it matters: Metabolic fluxes describe how cells process nutrients and support quantitative understanding of metabolism.

- [BayFlux: A Bayesian method to quantify metabolic Fluxes and their uncertainty at the genome scale](https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1011111): Main research objective: Infer probability distributions of metabolic fluxes consistent with experimental isotope and physiological measurements. Task connection: BayFlux directly solves isotope-constrained flux inference with uncertainty. The local task uses a separately specified atom-mapping model and source measurements; its restricted steady-state network and intervals do not reproduce the paper's genome-scale experiments.

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
- `file:../../.cache/science-biology/B05.json`
- `file:../../.cache/science-biology/B05.manifest.json`

## Sources

- paper: https://doi.org/10.1016/j.ymben.2024.03.005 (Theorell et al. model/likelihood formulation, metabolic flux posterior inference; Supplementary Data1 model files.)
- repository: https://github.com/JuBiotech/Supplement-to-Theorell-et-al.-Metabolic_Engineering-2024 (Official author implementation/data reference; evaluator and seed are independently written, not copied.)

## Limitations

- Source FML atom-map models require a verified isotope simulator port; generic linear surrogates are not substituted. Adapter enforces flux constraints and held-out likelihood but interval calibration requires separate known-flux experiments.
- Public source subsets are development-visible. Freeze candidates before evaluating on additional independently chosen studies/instances; trusted candidate execution is not a security sandbox.
- Improving this benchmark is a scientific-method result; it does not alone establish a new biological discovery.
