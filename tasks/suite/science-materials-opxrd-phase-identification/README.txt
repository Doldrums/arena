# opXRD experimental phase identification

**Source collection:** [Chemistry and materials research: source-based research tasks](../../papers/science-materials_expansion.md)\
**Task id:** `science-materials-opxrd-phase-identification`\
**Protocol:** `recreated`\
**Direction:** maximize\

## Task

identify_phases(two_theta_degrees, intensity, wavelength_angstrom, candidate_library) -> unique phase identifiers. Eight measured HKUST-A opXRD evaluation scans, including real2/3/4-phase mixtures;13 development scans use disjoint connected compound groups. The fixed25-phase library supplies source refined lattices and atomic bases, never held-out measured intensities. Score macro F1 of all source-reported curated phase labels. Annotation exhaustiveness and unreported impurities are unknown; no phase-fraction metric. Single-contributor study, no cross-laboratory claim. Seed computes approximate kinematic structural templates; observations are always actual source scans.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

identify_phases(two_theta_degrees, intensity, wavelength_angstrom, candidate_library) -> unique phase identifiers. Eight measured HKUST-A opXRD evaluation scans, including real2/3/4-phase mixtures;13 development scans use disjoint connected compound groups. The fixed25-phase library supplies source refined lattices and atomic bases, never held-out measured intensities. Score macro F1 of all source-reported curated phase labels. Annotation exhaustiveness and unreported impurities are unknown; no phase-fraction metric. Single-contributor study, no cross-laboratory claim. Seed computes approximate kinematic structural templates; observations are always actual source scans.

Parameters: `{"proposal_id": "C08", "data_sha256": "b223818dfbb1ac489ba4ba0941d3e9451814cc223988bad4f83f803b22e6e886"}`

## Labels

Scientific contribution: `method` (tier 2); artifact `model`, domain `natural_science`, data `real_measurements`, verification `sampled`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `materials_science`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Identify crystalline phases present in powder X-ray diffraction measurements of mixtures.

Why it matters: Phase identification determines which materials were formed and informs interpretation of their properties.

- [A deep-learning technique for phase identification in multiphase inorganic compounds using synthetic XRD powder patterns](https://www.nature.com/articles/s41467-019-13749-3): Main research objective: Identify constituent crystalline phases in multiphase compounds from powder diffraction patterns. Task connection: The local task classifies phases in eight measured opXRD mixture scans using a fixed phase library. It addresses the same inverse diffraction problem with a different source subset; F1 against reported labels does not prove absence of unreported phases or determine phase fractions.

A phase-identification solution paper provides the evidence; the opXRD data-collection paper alone would not qualify.

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
- `py:scipy`
- `file:data/materials-expansion/C08/dataset.json`

## Sources

- paper: https://doi.org/10.1002/aidi.202500044 (Section3.2 HKUST-A/XRed:21 measured phase-identification patterns, corresponding refined CIF structures and single-/multiphase mixtures. Full structural labels are not an exhaustive-impurity certificate.)
- repository: https://github.com/aimat-lab/opXRD (Official loaders.)
- benchmark: https://zenodo.org/records/15298026 (Pinned record15298026, only HKUST/HKUST-A/pattern_0.json through pattern_20.json;21uncompressed members SHA256 pinned in data/science/materials_expansion/opxrd_hkust_a_sources.json. Verified ZIP CRC and HTTP byte ranges; not a full-archive digest claim.)
- paper: https://www.nature.com/articles/s41467-019-13749-3 (Develops and tests phase identification from diffraction patterns, including real-data tests. The local opXRD experimental collection is separate, and complete phase annotations are required before scoring.)

## Limitations

- Independent source-reported phase-label recovery adaptation; no claim to reproduce author leaderboard scores or identify every chemically present impurity.
- All curated released HKUST-A phase labels are evaluated. annotation_complete remains null because unreported phases/impurities are unknown; no phase-fraction metrics.
- Thirteen development/eight evaluation scans use connected compound groups; mixtures sharing a compound stay together. One source contributor, so no cross-laboratory generalization claim.
- Closed25-phase structure library is available to candidates; it contains source refined lattices/bases, not held-out experimental intensities. Near-identical beta-Sn refinements are treated as one phase.
- The seed uses approximate constant atomic-number form factors and fixed broadening; this is a candidate heuristic, not full Rietveld refinement. Source scans and experimental mixtures are never generated.
- Candidate and evaluator share a Python process; API separation is cooperative, not an OS sandbox. Public cases are development data.
