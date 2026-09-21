# Online bin packing

**Paper:** Evolution of Heuristics: Towards Efficient Automatic Algorithm Design Using Large Language Model (https://arxiv.org/pdf/2401.02051)\
**Paper:** CodeEvolve: an open-source evolutionary framework for algorithmic discovery and optimization (https://arxiv.org/pdf/2510.14150)\
**Paper:** EoH-S: Evolution of Heuristic Set using LLMs for Automated Heuristic Design (https://arxiv.org/pdf/2508.03082)\
**Paper:** HSEvo: Elevating Automatic Heuristic Design with Diversity-Driven Harmony Search and Genetic Algorithm Using LLMs (https://arxiv.org/pdf/2412.14995)\
**Paper:** In-the-loop Hyper-Parameter Optimization for LLM-Based Automated Design of Heuristics (https://arxiv.org/pdf/2410.16309)\
**Paper:** Monte Carlo Tree Search for Comprehensive Exploration in LLM-Based Automatic Heuristic Design (https://arxiv.org/pdf/2501.08603)\
**Paper:** Multi-objective Evolution of Heuristic Using Large Language Model (https://arxiv.org/pdf/2409.16867)\
**Paper:** RedAHD: Reduction-Based End-to-End Automatic Heuristic Design with Large Language Models (https://arxiv.org/pdf/2505.20242)\
**Task id:** `eoh-online-bin-packing`\
**Protocol:** `recreated`\
**Direction:** minimize\

## Task

Online bin packing: optimize the candidate specified by the paper and evaluate against the named benchmark.

Benchmark named in the paper: Online bin packing. Paper metric: mean excess over L1 lower bound (fraction).

## Candidate interface

priority(item: float, bins: np.ndarray) -> np.ndarray of one score per bin with enough remaining capacity; the item goes to the highest-scoring bin (FunSearch/EoH contract). Score: mean excess over the L1 lower bound in percent

Parameters: `{"n_instances": 5, "n_items": 1000, "capacity": 100, "seed": 0}`

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `combinatorial_optimisation`, data `synthetic`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Also evaluated by

The same problem (same evaluator and parameters) appears in these papers; their records were merged into this task and their pinned upstream routes remain reachable with `run.py evaluate eoh-online-bin-packing --route upstream --paper <paper>`.

- CodeEvolve: Online bin packing (`codeevolve-online-bin-packing`; EoH)
- EoH-S: Online bin packing (`eoh-s-online-bin-packing`; BPPLib / TSPLIB / CVRPLIB)
- HSEvo: Online bin packing (`hsevo-online-bin-packing`; Online bin packing, Pinned official training instances or exact official training generator; see docs/TASKS.md for subset and limits.)
- LLaMEA-HPO: Online bin packing (`llamea-hpo-online-bin-packing`; Online bin packing, 5 Weibull instances with 5000 items each and bin capacity 100 during search)
- MCTS-AHD: bpp_online (`mcts-ahd-bpp-online`; bpp_online, Pinned official training instances or exact official training generator; see docs/TASKS.md for subset and limits.)
- MEoH: Online bin packing (`meoh-online-bin-packing`; Online bin packing)
- RedAHD: Online bin packing (`redahd-online-bin-packing`; MCTS-AHD evaluation datasets, MCTS-AHD evaluation datasets)
- EoH, EoH-S, MEoH, HSEvo, LLaMEA-HPO: Online one-dimensional bin packing (`reference-online-bin-packing`; Generated locally with documented seed.)

## Evaluation protocol

Reimplemented in this repository from the paper's task description; instances are generated locally with a fixed seed, so scores are comparable within the suite but not with the paper's numbers.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:numpy`

## Sources

- paper: https://arxiv.org/pdf/2401.02051 (Section 4 and Appendices B–D)
- repository: https://github.com/FeiLiu36/EoH/tree/472545785c936dcfc863d2bc0d6109cf23c7ce62 (examples/bp_online/evaluation/runEval.py)
- paper: https://arxiv.org/pdf/2510.14150 (Appendix A.2)
- repository: https://github.com/inter-co/science-codeevolve/tree/c077959e1ab24b060aaa6d4c563bca2e9cbe8617 (problems/eoh-problems/bp_online/input)
- paper: https://arxiv.org/pdf/2508.03082 (Section 4, Tables 1-3)
- repository: https://github.com/FeiLiu36/EoH-S/tree/8310b056ab0d4ea83d194f1d9e8c7873c0a3b892
- paper: https://arxiv.org/pdf/2412.14995 (Section 5.1 and Appendix A)
- repository: https://github.com/datphamvn/HSEvo/tree/f3afffabc2b458fddf70a42a8678758039671297 (problems/bpp_online)
- paper: https://arxiv.org/pdf/2410.16309 (Sections 4.1–4.3)
- archive: https://zenodo.org/api/records/14917719/files/LLaMEA-HPO.zip/content (run_BP_HPO.py)
- paper: https://arxiv.org/pdf/2501.08603 (Section 4; Appendices B-D and F)
- repository: https://github.com/zz1358m/MCTS-AHD-master/tree/ee9c4f424503c65a5fd2b899e6620ce86079fedb (problems/bpp_online/eval.py)
- paper: https://arxiv.org/pdf/2409.16867 (Section 4)
- repository: https://github.com/Optima-CityU/LLM4AD/tree/ffb6acf64497be93932c98d25369352efd3865cf (llm4ad/task/optimization/online_bin_packing/evaluation.py)
- paper: https://arxiv.org/pdf/2505.20242 (Section 5.1 and Appendix C)

## Limitations

- Upstream commands and dependencies were inspected; costly training, paid APIs, and hardware experiments were not executed.
- Execution interface inspected in pinned source. Full paper experiments have not been reproduced here.
