# Cantera chemical-mechanism reduction

**Source collection:** [Chemistry and materials research: source-based research tasks](../../papers/science-materials_expansion.md)\
**Task id:** `science-materials-cantera-mechanism-reduction`\
**Protocol:** `recreated`\
**Direction:** maximize\

## Task

reduce_mechanism(full_mechanism, training_conditions, tolerance) -> {'species': unique species-name list, 'reaction_indices': unique integer list}. Full mechanism provides canonical Cantera 3.2 h2o2 YAML, species, reaction equations, and required_species. Retain only original species thermochemistry and original reactions; independent Cantera validates balance. Three withheld temperature/pressure/equivalence-ratio cases compare temperature, H2/O2/H2O/OH histories and sampled ignition delay. Worst normalized error must be <=0.05. Score 1 - 0.5*(retained species fraction + retained reaction fraction). This is reference-mechanism agreement, not experimental validation.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

reduce_mechanism(full_mechanism, training_conditions, tolerance) -> {'species': unique species-name list, 'reaction_indices': unique integer list}. Full mechanism provides canonical Cantera 3.2 h2o2 YAML, species, reaction equations, and required_species. Retain only original species thermochemistry and original reactions; independent Cantera validates balance. Three withheld temperature/pressure/equivalence-ratio cases compare temperature, H2/O2/H2O/OH histories and sampled ignition delay. Worst normalized error must be <=0.05. Score 1 - 0.5*(retained species fraction + retained reaction fraction). This is reference-mechanism agreement, not experimental validation.

Parameters: `{"proposal_id": "C09"}`

## Labels

Scientific contribution: `method` (tier 2); artifact `optimizer`, domain `natural_science`, data `simulator`, verification `simulation`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `chemistry`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.

Underlying problem: Reduce chemical reaction mechanisms while preserving ignition and concentration predictions.

Why it matters: Smaller faithful reaction models can make combustion simulation more practical.


The current task compresses the compact built-in h2o2 mechanism. pyMARS is a software paper, while the inspected problem-focused DRGEPSA study reduces much larger hydrocarbon-fuel mechanisms. That establishes the broader research area but not scientific usefulness of this particular compact teaching-model reduction and its three withheld cases. No qualifying primary-goal evidence is established for this local task in this review; this is not a finding that the broader subject is unimportant.

## Evaluation protocol

Locally authored implementation of the cited scientific task. Source data, generated mathematical instances, reference checks and adaptations are specified below; unit-test fixtures do not establish a benchmark reproduction.

- Independently implemented SCIEL adaptation. Source bundles are required except the specified PFHub and Cantera simulations; no generated replacement data. See docs/MATERIALS_EXPANSION.md for provenance, exact setup blockers and validation scope.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:numpy`
- `py:cantera`

## Sources

- paper: https://joss.theoj.org/papers/10.21105/joss.01543 (pyMARS chemical kinetic mechanism reduction.)
- repository: https://github.com/Niemeyer-Research-Group/pyMARS (Author reduction algorithms and examples, reference only; no source evaluator code copied.)
- benchmark: https://cantera.org/3.2/examples/python/kinetics/mechanism_reduction.html (Cantera official mechanism-reduction construction. Local compact h2o2.yaml model, Cantera 3.2.x, is an explicit SCIEL adaptation.)

## Limitations

- Independent SCIEL adaptation of a cited scientific problem; no claim to reproduce author leaderboard scores.
- Candidate and evaluator run in one Python process; data access is separated by API, not an OS sandbox. Isolate evaluator data for adversarial or held-out evaluation.
- Compact hydrogen/oxygen h2o2.yaml model replaces the large pyMARS example mechanism explicitly; physical ODE model is solved with actual Cantera. Agreement with the reference model does not establish experimental adequacy.
