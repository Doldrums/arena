# stanford-covid-vaccine

**Paper:** LoongFlow: Directed Evolutionary Search via a Cognitive Plan-Execute-Summarize Paradigm (https://arxiv.org/pdf/2512.24077)\
**Task id:** `loongflow-stanford-covid-vaccine`\
**Protocol:** `unsupported`\
**Direction:** minimize\

## Task

Predict RNA reactivity, deg_Mg_pH10 and deg_Mg_50C; score the mean of three RMSE values on rows selected by the answers keep mask.

Benchmark named in the paper: MLE-bench. Paper metric: mean columnwise root mean squared error.

## Candidate interface

See the docstring in `evaluator.py`.

## Labels

Scientific contribution: `engineering` (tier 3); artifact `model`, domain `machine_learning`, data `undistributed`, verification `none`, reference `none`, resources `gpu, unavailable`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Evaluation protocol

Not executable in this suite: MLE-bench competitions require the Kaggle data and model training; neither is redistributed.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `dataset:MLE-bench`
- `hardware:gpu`

## Sources

- paper: https://arxiv.org/pdf/2512.24077 (Table 2)
- repository: https://github.com/baidu-baige/LoongFlow/tree/945c78bc1554f8281aac40320b3599bd68d528d7 (agents/ml_agent/examples/mlebench/eval_program.py)

## Limitations

- Direct CPU checks found upstream square seed rejected by strict overlap test and rectangle seed incompatible with its evaluator. Original Autocorrelation II and Erdos overlap seeds passed; a new simple square grid fixture passed. These are integration checks, not reproduced paper results.
- No complete, verified execution adapter has been established for this exact task; this package is an explicit implementation gap.
