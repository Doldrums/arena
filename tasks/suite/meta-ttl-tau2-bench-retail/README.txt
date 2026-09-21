# tau2-bench Retail

**Paper:** Learning to Learn-at-Test-Time: Language Agents with Learnable Adaptation Policies (https://arxiv.org/pdf/2604.00830)\
**Task id:** `meta-ttl-tau2-bench-retail`\
**Protocol:** `unsupported`\
**Direction:** maximize\

## Task

tau2-bench Retail task evaluated in Learning to Learn-at-Test-Time: Language Agents with Learnable Adaptation Policies.

Benchmark named in the paper: tau2-bench. Paper metric: W-AUC and task success rate.

## Candidate interface

See the docstring in `evaluator.py`.

## Labels

Scientific contribution: `benchmark` (tier 3); artifact `agent`, domain `software_engineering`, data `public_benchmark`, verification `none`, reference `none`, resources `model_api, simulator`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Evaluation protocol

Not executable in this suite: Candidates are LLM agents scored inside the tau2-bench environment (tools, web, games or code sandboxes); the environment and model access are external.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `service:llm_api`
- `env:OPENROUTER_API_KEY`
- `environment:tau2-bench`

## Sources

- paper: https://arxiv.org/pdf/2604.00830 (Section 4.1)
- repository: https://github.com/zzzlou/meta-ttl/tree/b72db4b77e9ae01aec1cbfd36ae0edae902b6468

## Limitations

- No complete, verified execution adapter has been established for this exact task; this package is an explicit implementation gap.
