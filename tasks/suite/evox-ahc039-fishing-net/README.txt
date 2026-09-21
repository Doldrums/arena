# ahc039 Fishing net

**Paper:** EvoX: Meta-Evolution for Automated Discovery (https://arxiv.org/pdf/2602.23413)\
**Paper:** ShinkaEvolve: Towards Open-Ended And Sample-Efficient Program Evolution (https://arxiv.org/pdf/2509.19349)\
**Task id:** `evox-ahc039-fishing-net`\
**Protocol:** `original`\
**Direction:** maximize\

## Task

ahc039 Fishing net

Benchmark named in the paper: ALE-Bench-Lite. Paper metric: official AtCoder heuristic score.

## Candidate interface

A C++20 program for AtCoder heuristic contest ahc039 (EVOLVE-BLOCK markers optional); scored by ALE-Bench on 50 public cases, score sign-adjusted so higher is better

Parameters: `{"problem": "ahc039", "public_cases": 50}`

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `combinatorial_optimisation`, data `public_benchmark`, verification `simulation`, reference `none`, resources `docker`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Also evaluated by

The same problem (same evaluator and parameters) appears in these papers; their records were merged into this task and their pinned upstream routes remain reachable with `run.py evaluate evox-ahc039-fishing-net --route upstream --paper <paper>`.

- ShinkaEvolve: ALE-Bench LITE ahc039 (`shinkaevolve-ale-bench-lite-ahc039`; ALE-Bench LITE, ahc039)

## Evaluation protocol

Verbatim EvoX ALE-Bench evaluator (skydiscover benchmarks) with a shim for its unpublished session helper; the judge is the public ALE-Bench package.

- ALE-Bench compiles its Rust judge tools in a rust:1.79.0-buster container at every session and runs candidates in the ale-bench:cpp20-202301 judge image (both must be the same CPU architecture: on Apple silicon pull the Rust image with --platform linux/amd64 because the judge images are amd64). On macOS run with TMPDIR under $HOME so the Docker VM can mount the build directory.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:ale_bench`
- `docker`
- `bin:cargo`

## Sources

- paper: https://arxiv.org/pdf/2602.23413 (Appendix A.3 Table 6)
- repository: https://github.com/skydiscover-ai/skydiscover/tree/0d932b690670a7e544388ad362e9876c8bd256a0 (benchmarks/ale_bench/ale-bench-lite-problems/ahc039)
- paper: https://arxiv.org/pdf/2509.19349 (Section 3.3 and Appendix C.3)
- benchmark: https://huggingface.co/datasets/SakanaAI/ALE-Bench/raw/main/problem_ids_lite.txt (Lite problem registry)
- benchmark: https://github.com/SakanaAI/ALE-Bench/blob/main/src/ale_bench/data.py (list_problem_ids(lite_version=True))
- repository: https://github.com/SakanaAI/ShinkaEvolve/tree/9912af12d423504b8d580f4179fd15f5f88b8c50

## Limitations

- Appendix task prose conflicts with standard circle-packing/Heilbronn definitions; the pinned evaluator is authoritative. Telemetry-repair directory is not present at inspected commit.
- Execution interface inspected in pinned source. Full paper experiments have not been reproduced here.
