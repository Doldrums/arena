# Biology: Measured tandem-spectrum peptide reconstruction

**Source collection:** [Biology and bioinformatics: source-based research tasks](../../papers/science-biology_expansion.md)\
**Task id:** `science-biology-casanovo-peptide-decoding`\
**Protocol:** `recreated`\
**Direction:** maximize\

## Task

Decode physically mass-consistent peptide sequences from measured fragment spectra and rank confidence under exact-sequence and precision-coverage evaluation.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

decode_spectrum(peaks, precursor_mass, charge) -> (unmodified_peptide, confidence0..1). precursor_mass is NEUTRAL mass in Da (not m/z). Standard residues, I/L equivalent, mass error<=50ppm. Empty sequence/confidence0 is abstention. Maximize tie-grouped stepwise precision-coverage area; exact recall diagnostic. Measured-spectrum CPU decoder track, no learned encoder required.

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `natural_science`, data `real_measurements`, verification `sampled`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `biology`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine peptide amino-acid sequences from tandem mass spectra without requiring a matching sequence database.

Why it matters: De novo peptide sequencing supports protein characterization, including sequences absent from reference databases.

- [Sequence-to-sequence translation from mass spectra to peptides with a transformer model](https://www.nature.com/articles/s41467-024-49731-x): Main research objective: Reconstruct peptide sequences directly from measured tandem mass spectra. Task connection: The local task retains measured MS/MS sequence reconstruction, precursor-mass consistency and confidence evaluation. Its selected spectra and scoring are not a full Casanovo reproduction or validation of newly discovered proteins.

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
- `file:../../.cache/science-biology/B12.json`
- `file:../../.cache/science-biology/B12.manifest.json`

## Sources

- paper: https://www.nature.com/articles/s41467-024-49731-x (Casanovo Methods: de novo sequencing, precursor constraints and precision/coverage evaluation.)
- repository: https://github.com/Noble-Lab/casanovo (Official author implementation/data reference; evaluator and seed are independently written, not copied.)

## Limitations

- Classical CPU decoder adaptation of twelve unique unmodified peptides in the official measured mouse sample. Not full nine-species/generalization benchmark or learned-encoder reproduction; I/L are equivalent and precursor mass is neutralDa.
- Public source subsets are development-visible. Freeze candidates before evaluating on additional independently chosen studies/instances; trusted candidate execution is not a security sandbox.
- Improving this benchmark is a scientific-method result; it does not alone establish a new biological discovery.
