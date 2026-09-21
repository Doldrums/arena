# Biology: PEtab biochemical kinetic parameter inference

**Source collection:** [Biology and bioinformatics: source-based research tasks](../../papers/science-biology_expansion.md)\
**Task id:** `science-biology-petab-kinetic-inference`\
**Protocol:** `recreated`\
**Direction:** minimize\

## Task

Fit mechanistic biochemical ODE parameters from measured signaling trajectories and predict complete held-out stimulation conditions with an independent source-model solver.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

fit_kinetics(petab_problem, training_objective, budget) -> {parameters,intervals}. problem includes parameter names, transformed bounds, initial_parameters, and training observations. Enforce bounds, finite intervals containing estimates, objective-call budget. Independently use pinned source-specific PEtab simulator on held-out whole conditions. No source-fitted held-out parameter values in candidate input.

## Labels

Scientific contribution: `method` (tier 2); artifact `optimizer`, domain `natural_science`, data `real_measurements`, verification `simulation`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `biology`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Infer the mechanisms and kinetic parameters underlying insulin-signaling dynamics.

Why it matters: Quantitative receptor-signaling models help explain how cells respond to insulin and how feedback affects the response.

- [Mass and Information Feedbacks through Receptor Endocytosis Govern Insulin Signaling as Revealed Using a Parameter-free Modeling Framework](https://pmc.ncbi.nlm.nih.gov/articles/PMC2888430/): Main research objective: Determine which receptor-endocytosis and feedback mechanisms explain measured insulin-signaling responses. Task connection: The local Brannmark_JBC2010 ODE task fits parameters and predicts held-out stimulation conditions of the source mechanistic model. It does not rerun the paper's complete model-selection or experimental argument.

The qualifying evidence is the original mechanistic insulin-signaling study; the PEtab model-format/software paper alone is excluded.

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
- `file:../../.cache/science-biology/B10.json`
- `file:../../.cache/science-biology/B10.manifest.json`

## Sources

- paper: https://doi.org/10.1371/journal.pcbi.1008646 (PEtab specification: parameters, measurements, observables, condition-dependent simulation and noise likelihood. Brannmark_JBC2010 model in official collection.)
- repository: https://github.com/Benchmarking-Initiative/Benchmark-Models-PEtab (Official author implementation/data reference; evaluator and seed are independently written, not copied.)
- paper: https://pmc.ncbi.nlm.nih.gov/articles/PMC2888430/ (Fits and tests quantitative insulin-signaling models against phosphorylation observations. The local PEtab Brannmark_JBC2010 parameter-inference problem uses this biological model, with a restricted inference protocol.)

## Limitations

- Source Brannmark insulin-signaling SBML transcribed independently and integrated bySciPyBDF. Source-fitted nominal parameters are excluded from candidate inputs. Bounds-wide intervals are only a valid seed, not calibrated uncertainty.
- Public source subsets are development-visible. Freeze candidates before evaluating on additional independently chosen studies/instances; trusted candidate execution is not a security sandbox.
- Improving this benchmark is a scientific-method result; it does not alone establish a new biological discovery.
