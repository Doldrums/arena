# FiNER

**Paper:** Meta Context Engineering via Agentic Skill Evolution (https://arxiv.org/pdf/2601.21557)\
**Paper:** Meta-Harness: End-to-End Optimization of Model Harnesses (https://arxiv.org/pdf/2603.28052)\
**Task id:** `mce-finer`\
**Protocol:** `unsupported`\
**Direction:** maximize\

## Task

FiNER task evaluated in Meta Context Engineering via Agentic Skill Evolution.

Benchmark named in the paper: FiNER. Paper metric: pass@1 prediction accuracy.

## Candidate interface

See the docstring in `evaluator.py`.

## Labels

Scientific contribution: `benchmark` (tier 3); artifact `agent`, domain `language`, data `public_benchmark`, verification `none`, reference `none`, resources `model_api, unavailable`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Also evaluated by

The same problem (same evaluator and parameters) appears in these papers; their records were merged into this task and their pinned upstream routes remain reachable with `run.py evaluate mce-finer --route upstream --paper <paper>`.

- Meta-Harness: FiNER (`meta-harness-finer`; FiNER)

## Evaluation protocol

Not executable in this suite: Candidates are prompts, agent scaffolds or workflows whose fitness is measured by querying a language model on the FiNER benchmark. The suite embeds neither model calls nor the benchmark data.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `service:llm_api`
- `env:OPENROUTER_API_KEY`
- `dataset:FiNER`

## Sources

- paper: https://arxiv.org/pdf/2601.21557 (Section 4.1 and Appendix A)
- repository: https://github.com/metaevo-ai/mce-artifact/tree/c63300daef93404e22e2569b3d08e72843e7123b (env/finer/finer_environment.py)
- paper: https://arxiv.org/pdf/2603.28052 (Section 4.1; Table 5; Appendix C.1)
- repository: https://github.com/stanford-iris-lab/meta-harness-tbench2-artifact/tree/57fefdb2ff84af3fd81b69d67814acbe69bd0743

## Limitations

- Execution interface inspected in pinned source. Full paper experiments have not been reproduced here.
