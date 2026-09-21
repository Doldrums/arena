# SWE-bench Verified

**Paper:** A Self-Improving Coding Agent (https://arxiv.org/pdf/2504.15228)\
**Paper:** Agentic Harness Engineering: Observability-Driven Automatic Evolution of Coding-Agent Harnesses (https://arxiv.org/pdf/2604.25850)\
**Paper:** Darwin Gödel Machine: Open-Ended Evolution of Self-Improving Agents (https://arxiv.org/pdf/2505.22954)\
**Paper:** Group-Evolving Agents: Open-Ended Self-Improvement via Experience Sharing (https://arxiv.org/pdf/2602.04837)\
**Task id:** `sica-swe-bench-verified`\
**Protocol:** `unsupported`\
**Direction:** maximize\

## Task

SWE-bench Verified: optimize the candidate specified by the paper and evaluate against the named benchmark.

Benchmark named in the paper: SWE-bench Verified. Paper metric: benchmark score; time and API cost enter combined utility.

## Candidate interface

See the docstring in `evaluator.py`.

## Labels

Scientific contribution: `benchmark` (tier 3); artifact `agent`, domain `software_engineering`, data `public_benchmark`, verification `none`, reference `none`, resources `model_api, simulator`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Also evaluated by

The same problem (same evaluator and parameters) appears in these papers; their records were merged into this task and their pinned upstream routes remain reachable with `run.py evaluate sica-swe-bench-verified --route upstream --paper <paper>`.

- AHE: SWE-bench Verified (`ahe-swe-bench-verified`; SWE-bench Verified)
- DGM: SWE-bench Verified (`dgm-swe-bench-verified`; SWE-bench Verified)
- GEA: SWE-bench Verified (`gea-swe-bench-verified`)

## Evaluation protocol

Not executable in this suite: Candidates are LLM agents scored inside the SWE-bench Verified environment (tools, web, games or code sandboxes); the environment and model access are external.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `service:llm_api`
- `env:OPENROUTER_API_KEY`
- `environment:SWE-bench Verified`

## Sources

- paper: https://arxiv.org/pdf/2504.15228 (Sections 4 and 4.1)
- repository: https://github.com/MaximeRobeyns/self_improving_coding_agent/tree/ed8275dca4d3c5dbf77229964351fe9b424797dc (base_agent/src/benchmarks/swebench_verified.py)
- paper: https://arxiv.org/pdf/2604.25850 (Section 4 cross-benchmark transfer)
- repository: https://github.com/china-qijizhifeng/agentic-harness-engineering/tree/8b2a55d97590363fe50c3cc6b5e833b020a4bb4c
- paper: https://arxiv.org/pdf/2505.22954 (Experiments and evaluation appendix)
- repository: https://github.com/jennyzzt/dgm/tree/a565fd2d1dca504ef5104a7cc0f3bdc4ab9b4fd2 (swe_bench)
- paper: https://arxiv.org/pdf/2602.04837 (Evaluation protocol)
- repository: https://github.com/UCSB-AI/GEA/tree/d185edffd1f9fbd2297f4de8c6c9f94547448b6d

## Limitations

- Upstream commands and dependencies were inspected; costly training, paid APIs, and hardware experiments were not executed.
- No complete, verified execution adapter has been established for this exact task; this package is an explicit implementation gap.
