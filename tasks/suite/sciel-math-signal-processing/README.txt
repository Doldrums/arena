# SCiEL: Adaptive signal processing

**Paper:** SCiEL — Scientific Closed-loop Evolutionary Learning: benchmark examples (https://github.com/luciferkonn/SCiEL)\
**Paper:** AdaEvolve: Adaptive LLM Driven Zeroth-Order Optimization (https://arxiv.org/pdf/2602.20133)\
**Paper:** CORAL: Towards Autonomous Multi-Agent Evolution for Open-Ended Discovery (https://arxiv.org/pdf/2604.01658)\
**Paper:** EvoX: Meta-Evolution for Automated Discovery (https://arxiv.org/pdf/2602.23413)\
**Paper:** Reward-Free Evolving Agents via Pairwise Validator (https://arxiv.org/pdf/2607.14408)\
**Task id:** `sciel-math-signal-processing`\
**Protocol:** `original`\
**Direction:** maximize\

## Task

Return filtered signal metrics for five synthetic signal cases; the original evaluator blends smoothness, error, noise reduction and reliability.

Benchmark named in the paper: SCiEL source example signal_processing. Paper metric: overall_score.

## Candidate interface

See evaluator.py and README.upstream.md.

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `numerical_computing`, data `synthetic`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Also evaluated by

The same problem (same evaluator and parameters) appears in these papers; their records were merged into this task and their pinned upstream routes remain reachable with `run.py evaluate sciel-math-signal-processing --route upstream --paper <paper>`.

- AdaEvolve: Signal processing (`adaevolve-signal-processing`; AlphaEvolve math)
- CORAL: Signal processing (`coral-signal-processing`)
- EvoX: Signal processing (`evox-signal-processing`; AlphaEvolve math)
- Pairwise Validator: signal_processing (`pairwise-validator-signal-processing`; ADRS / ShinkaEvolve)

## Evaluation protocol

Verbatim copy of the pinned SCiEL example `examples/signal_processing` (commit da80706f98f9); the evaluator, seed program and configuration are the upstream files. README.upstream.md is the upstream README when one exists.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:matplotlib`
- `py:numpy`
- `py:pykalman`
- `py:pywt`
- `py:scipy`
- `py:sklearn`

## Sources

- repository: https://github.com/luciferkonn/SCiEL/blob/da80706f98f9bf1295e502544cdf5a9200fe5f57/examples/signal_processing/evaluator.py (evaluate and helper validators at immutable commit)
- repository: https://github.com/luciferkonn/SCiEL/blob/da80706f98f9bf1295e502544cdf5a9200fe5f57/examples/signal_processing/initial_program.py (original baseline)
- paper: https://arxiv.org/pdf/2602.20133 (Math results and task-definition appendix)
- repository: https://github.com/skydiscover-ai/skydiscover/tree/0d932b690670a7e544388ad362e9876c8bd256a0 (benchmarks/math/signal_processing)
- paper: https://arxiv.org/pdf/2604.01658 (Section 4.1, Table 1)
- repository: https://github.com/Human-Agent-Society/CORAL/tree/0123dfb939b35228cf2c1fde224cd0561e727408 (examples/math/signal_processing)
- paper: https://arxiv.org/pdf/2602.23413 (Math results and task-definition appendix)
- paper: https://arxiv.org/pdf/2607.14408 (Section 5.4, Table 5)

## Limitations

- Source-inspected SCiEL example; not a reproduced paper result.
- The original evaluator and baseline are fetched at the immutable source commit; no upstream implementation is silently repaired.
- The evaluator generates noisy/clean reference signals but passes only signal length, noise level and window size to run_signal_processing(). Candidate output may correspond to a different generated input; the resulting signal comparison is not an independent check of filtering the intended input.
- The upstream evaluator provides no independently trusted validity boolean; a finite returned score remains unverified.
