# ARC

**Paper:** Automated Design of Agentic Systems (https://arxiv.org/pdf/2408.08435)\
**Paper:** LLM-based Evolution as a Universal Optimizer (Darwinian Evolver) (https://imbue.com/blog/2026-02-27-darwinian-evolver)\
**Paper:** SePO: Self-Evolving Prompt Agent for System Prompt Optimization (https://arxiv.org/pdf/2606.04465)\
**Task id:** `adas-arc`\
**Protocol:** `recreated`\
**Direction:** maximize\

## Task

ARC: optimize the candidate specified by the paper and evaluate against the named benchmark.

Benchmark named in the paper: ARC. Paper metric: exact match / benchmark accuracy.

## Candidate interface

solve(task, llm) -> list of output grids, one per test input; task = {'train': [{'input','output'}], 'test': [{'input'}]}. Score: fraction of test grids reproduced exactly on a seeded sample of public evaluation tasks

Parameters: `{"version": 1, "split": "evaluation", "seed": 0}`

## Labels

Scientific contribution: `benchmark` (tier 3); artifact `agent`, domain `language`, data `public_benchmark`, verification `sampled`, reference `none`, resources `model_api`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Also evaluated by

The same problem (same evaluator and parameters) appears in these papers; their records were merged into this task and their pinned upstream routes remain reachable with `run.py evaluate adas-arc --route upstream --paper <paper>`.

- Darwinian Evolver: ARC-AGI solution evolution (`darwinian-evolver-arc-agi-solution-evolution`; ARC-AGI)
- SePO: ARC-AGI-1 (`sepo-arc-agi-1`; ARC-AGI-1)

## Evaluation protocol

Reimplemented in this repository from the paper's task description; instances are generated locally with a fixed seed, so scores are comparable within the suite but not with the paper's numbers.

- Public ARC-AGI data (GitHub) converted to the Kaggle layout; the model, sample size and budget follow the llm family environment variables.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:numpy`
- `env:OPENROUTER_API_KEY`
- `network:openrouter`
- `file:data/arc-prize-2025/arc-agi_evaluation_challenges.json`

## Sources

- paper: https://arxiv.org/pdf/2408.08435 (Sections 4.1–4.2)
- repository: https://github.com/ShengranHu/ADAS/tree/2702bee8fefda42255efc5be9f60e3bd3db96ae4 (_arc/search.py)
- paper: https://imbue.com/blog/2026-02-27-darwinian-evolver (Blog and repository README)
- repository: https://github.com/imbue-ai/darwinian_evolver/tree/7f12365d2059c47e29068a5a6f498a293148d2a9 (darwinian_evolver/problems/arc_agi.py)
- paper: https://arxiv.org/pdf/2606.04465 (Section 4.1; Appendix B)
- repository: https://github.com/taowangcheng/SePO/tree/83083782a9487ef61962d933fc72abbe95f9fa76

## Limitations

- Upstream commands and dependencies were inspected; costly training, paid APIs, and hardware experiments were not executed.
- Execution interface inspected in pinned source. Full paper experiments have not been reproduced here.
