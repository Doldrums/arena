# Aider Polyglot

**Paper:** Darwin Gödel Machine: Open-Ended Evolution of Self-Improving Agents (https://arxiv.org/pdf/2505.22954)\
**Paper:** Group-Evolving Agents: Open-Ended Self-Improvement via Experience Sharing (https://arxiv.org/pdf/2602.04837)\
**Paper:** HyperAgents (https://arxiv.org/pdf/2603.19461)\
**Task id:** `dgm-aider-polyglot`\
**Protocol:** `unsupported`\
**Direction:** maximize\

## Task

Aider Polyglot

Benchmark named in the paper: Aider Polyglot. Paper metric: pass@1 task success.

## Candidate interface

See the docstring in `evaluator.py`.

## Labels

Scientific contribution: `benchmark` (tier 3); artifact `agent`, domain `software_engineering`, data `public_benchmark`, verification `none`, reference `none`, resources `model_api, simulator`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Also evaluated by

The same problem (same evaluator and parameters) appears in these papers; their records were merged into this task and their pinned upstream routes remain reachable with `run.py evaluate dgm-aider-polyglot --route upstream --paper <paper>`.

- GEA: Aider Polyglot (`gea-aider-polyglot`)
- HyperAgents: Aider Polyglot (`hyperagents-aider-polyglot`)

## Evaluation protocol

Not executable in this suite: Candidates are LLM agents scored inside the Aider Polyglot environment (tools, web, games or code sandboxes); the environment and model access are external.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `service:llm_api`
- `env:OPENROUTER_API_KEY`
- `environment:Aider Polyglot`

## Sources

- paper: https://arxiv.org/pdf/2505.22954 (Experiments and evaluation appendix)
- repository: https://github.com/jennyzzt/dgm/tree/a565fd2d1dca504ef5104a7cc0f3bdc4ab9b4fd2 (polyglot)
- paper: https://arxiv.org/pdf/2602.04837 (Evaluation protocol)
- repository: https://github.com/UCSB-AI/GEA/tree/d185edffd1f9fbd2297f4de8c6c9f94547448b6d
- paper: https://arxiv.org/pdf/2603.19461 (Section 4 and Appendix C)
- repository: https://github.com/facebookresearch/Hyperagents/tree/59a68f672dfb92c74aeb7e61535d776fb36e172d (domains/polyglot)

## Limitations

- No complete, verified execution adapter has been established for this exact task; this package is an explicit implementation gap.
