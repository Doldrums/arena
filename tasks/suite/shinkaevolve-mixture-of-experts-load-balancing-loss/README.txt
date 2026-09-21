# Mixture-of-experts load balancing loss

**Paper:** ShinkaEvolve: Towards Open-Ended And Sample-Efficient Program Evolution (https://arxiv.org/pdf/2509.19349)\
**Task id:** `shinkaevolve-mixture-of-experts-load-balancing-loss`\
**Protocol:** `unsupported`\
**Direction:** maximize\

## Task

Mixture-of-experts load balancing loss: optimize the candidate specified by the paper and evaluate against the named benchmark.

Benchmark named in the paper: Mixture-of-experts load balancing loss. Paper metric: perplexity; seven downstream benchmark accuracies; load imbalance.

## Candidate interface

See the docstring in `evaluator.py`.

## Labels

Scientific contribution: `engineering` (tier 3); artifact `program`, domain `machine_learning`, data `public_benchmark`, verification `none`, reference `none`, resources `gpu`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Evaluation protocol

Not executable in this suite: The candidate is a load-balancing loss whose fitness is the perplexity of a mixture-of-experts model trained on GPU.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `hardware:gpu`
- `py:torch`

## Sources

- paper: https://arxiv.org/pdf/2509.19349 (Section 3.4 and Appendix C.4)
- repository: https://github.com/SakanaAI/ShinkaEvolve/tree/9912af12d423504b8d580f4179fd15f5f88b8c50

## Limitations

- Upstream commands and dependencies were inspected; costly training, paid APIs, and hardware experiments were not executed.
- Current public examples retain circle packing but do not include verified AIME, ALE-Bench LITE, or MoE experiment drivers. Later added examples are not included as paper evaluations.
- Original public release v0.0.1 (commit23decc6bf118d783ddff5a3c03d2269cbf149971) was also inspected: its example directories are circle_packing, game_2048, julia_prime_counting and novelty_generator, with no released AIME, ALE or MoE evaluator.
- No complete, verified execution adapter has been established for this exact task; this package is an explicit implementation gap.
