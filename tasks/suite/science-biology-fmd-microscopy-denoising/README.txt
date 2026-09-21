# Biology: Measured fluorescence microscopy denoising

**Source collection:** [Biology and bioinformatics: source-based research tasks](../../papers/science-biology_expansion.md)\
**Task id:** `science-biology-fmd-microscopy-denoising`\
**Protocol:** `recreated`\
**Direction:** maximize\

## Task

Recover calibrated fluorescence intensities from real noisy acquisitions, using averaged acquired exposures as imperfect reference images.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

denoise(noisy_image, acquisition_metadata) -> finite nonnegative same-shape intensity image. Each case is a full measured field of view with acquired averaged reference. Maximize mean PSNR at source-calibrated data_range. Gaussian-window SSIM and signed intensity bias reported. Repeated acquisitions remain grouped.

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `natural_science`, data `real_measurements`, verification `sampled`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `biology`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Recover biological fluorescence signals from photon-limited microscopy images.

Why it matters: Restoration can reduce exposure needed to observe cellular structures, addressing phototoxicity and imaging-speed constraints.

- [Content-aware image restoration: pushing the limits of fluorescence microscopy](https://www.nature.com/articles/s41592-018-0216-7): Main research objective: Extend observable biological imaging conditions by restoring fluorescence images acquired with limited photons or sampling. Task connection: The paper restores experimentally acquired fluorescence images. The local FMD task measures intensity recovery from noisy acquisitions using averaged exposures as imperfect references; it does not reproduce the paper's biological demonstrations or prove that every restored structure is real.

This paper targets a physical imaging limitation with biological examples; the FMD benchmark introduction alone is not qualifying evidence.

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
- `file:../../.cache/science-biology/B09.json`
- `file:../../.cache/science-biology/B09.manifest.json`

## Sources

- paper: https://openaccess.thecvf.com/content_CVPR_2019/papers/Zhang_A_Poisson-Gaussian_Denoising_Dataset_With_Real_Fluorescence_Microscopy_Images_CVPR_2019_paper.pdf (FMD dataset acquisition/averaging and PSNR/SSIM evaluation sections.)
- repository: https://github.com/yinhaoz/denoising-fluorescence (Official author implementation/data reference; evaluator and seed are independently written, not copied.)

## Limitations

- Twelve official FMD test_mix fields, fixed128x128central crops from measured noisy/averaged-reference images. No generated noise; bounded crop protocol, not fullpaper leaderboard.
- Full fields/repeated exposures must remain grouped. Averaged references are not exact clean images; staging must document whether the input exposure contributes to the reference. No synthetic noise replacement.
- Public source subsets are development-visible. Freeze candidates before evaluating on additional independently chosen studies/instances; trusted candidate execution is not a security sandbox.
- Improving this benchmark is a scientific-method result; it does not alone establish a new biological discovery.
