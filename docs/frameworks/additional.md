# Additional native research engines

These four profiles expose the source implementations and their native evaluation. `source_verified` records source inspection and offline adapter checks; it does not claim an installed environment or a completed research run. Their results have `canonical_evaluation: false`.

All commands use the framework runner described in [the native framework guide](README.md). Preparation checks immutable source and file hashes. Explicit execution takes place in an isolated copy, with a timeout and explicitly selected credential environment names. Dependency installation is a separate operator step.

| Framework / profile | Pinned implementation | Native interface and evidence |
| --- | --- | --- |
| EoB / `bbob` | [MetaEvo/EoB, 5d9f30cb](https://github.com/MetaEvo/EoB/tree/5d9f30cb19a0231a74f58d17926cff828db6857f) | [main.py](https://github.com/MetaEvo/EoB/blob/5d9f30cb19a0231a74f58d17926cff828db6857f/main.py), `AgenticFunctionGenerator.run`, `ScoreAgent` |
| EvoOR-Agent / `industry-or` | [EvoNexusX/2026HuangEvoORAgent, 1a255eaa](https://github.com/EvoNexusX/2026HuangEvoORAgent/tree/1a255eaade3b325706ab9b2ad1e20f2aafae0a06) | [initial.py](https://github.com/EvoNexusX/2026HuangEvoORAgent/blob/1a255eaade3b325706ab9b2ad1e20f2aafae0a06/initial.py), `generate_all`, `evaluate.evolve_generation` |
| DrEureka / `forward-locomotion` | [eureka-research/DrEureka, 1d4e0070](https://github.com/eureka-research/DrEureka/tree/1d4e00700423170717654516f4ef4b24cb0f3a84) | [dr_eureka/dr_eureka.py](https://github.com/eureka-research/DrEureka/blob/1d4e00700423170717654516f4ef4b24cb0f3a84/dr_eureka/dr_eureka.py), native Hydra entrypoint and RL training logs |
| LaSR / `symbolic-regression` | [trishullab/LibraryAugmentedSymbolicRegression.jl, 776196e3](https://github.com/trishullab/LibraryAugmentedSymbolicRegression.jl/tree/776196e339191736e20d4eb6eed7c468aa6e4472) | [example.jl](https://github.com/trishullab/LibraryAugmentedSymbolicRegression.jl/blob/776196e339191736e20d4eb6eed7c468aa6e4472/example.jl), `LaSROptions`, `equation_search`, `calculate_pareto_frontier` |

## EoB

The driver reconstructs the initialization in `main.py`, supplying the explicit API key instead of its placeholder, then calls the original asynchronous search. The native scorer combines landscape similarity and algorithm difficulty; generated objective functions and the native optimizer comparison are unchanged.

Request arguments must name a model, population and generation budget, for example `--model deepseek-v3.2 --N 8 --generation 2 --dim 10 --n_jobs 1`. The supported BBOB dimensions are 2, 10, 30 and 50. Native `--algo_diff_run_time` is **minutes per optimizer**, and the number of optimizer evaluations is separate from the LLM generation budget. Provider prefixes select the endpoints implemented by the pinned `LLMWrapper`: OpenAI, Gemini or DashScope. Explicit `OPENAI_API_KEY` supplies the key appropriate to that provider.

Results remain under native `save/`. Pickle artifacts are hashed and inventoried, never deserialized by the observer. This profile does not expose the upstream HPO, UAV or custom-data modes.

## EvoOR-Agent

The upstream CLI forcibly selects resume mode. This integration instead calls its published `generate_all` once, followed by `evolve_generation` for generations 2 through the requested total. It preserves native parent ranking, elite reuse, crossover, mutation and generated-agent validation. Example arguments: `--model MODEL --population 6 --generations 5 --seed 42`. Generation 1 is initialization, and a fresh native `populations/` directory is required.

The pinned `new_utils.py` contains anonymized provider environment names and a developer-specific Windows dataset path. At **explicit execution only**, the driver checks its exact SHA256 and makes five count-checked configuration substitutions in the isolated run copy: restores the OpenAI key/base URL and unused Anthropic client configuration, disables implicit dotenv discovery, and selects the included `Evo_agent/dataset/IndustryOR_test.json`. This is a source-compatible library integration with a recorded configuration port, not an unmodified upstream CLI. Native optimization and scoring code remains unchanged. `results/porting-receipt.json` records original/configured source hashes and the dataset hash; it contains no key values.

This profile uses only the native OpenAI-compatible branch. The native code constructs both provider clients, so its unused Anthropic client receives a noncredential placeholder. Generated agents may require solver dependencies and licenses. Native `eval_result.json` artifacts retain their original `solve_correct` and other fields; they are not promoted to a canonical Arena score.

## DrEureka

The profile invokes the published domain-randomization search stage directly, with `env=forward_locomotion`, `use_wandb=false` and a forced Hydra result directory. Optional native arguments include `model=gpt-4-0125-preview sample=4 env.train_iterations=1000`.

It requires the upstream IsaacGym/CUDA environment, native project packages, compatible legacy OpenAI SDK and prepared reward/template and RAPP parameter bounds. Reward discovery and RAPP are preceding upstream stages; this profile does not claim to orchestrate the full three-stage pipeline. Native training success/reward logs and generated configuration artifacts remain the measurement record. Physics simulation and GPU training have not been executed by these offline checks.

## LaSR

The Python driver launches an explicitly configured Julia executable using the native project. It does not install packages. Prepare Julia 1.11–1.12 and the pinned `Project.toml` dependencies first. Supply `request.executables.julia` as an absolute executable path; the generic run plan hashes and rechecks that executable.

Provide `inputs: {"data.json": "/absolute/data.json"}` and arguments such as `--model MODEL --iterations 40 --populations 20 --llm-probability 0.0001`. The dataset must contain exactly `X` and `y`, with sample rows in `X`, matching targets, rectangular finite numeric data, 2–100000 samples, 1–100 features and at most 16 MiB. The bridge transposes samples into Julia's native feature-by-sample layout. Explicit `OPENAI_API_KEY` and `OPENAI_BASE_URL` configure the model endpoint.

A fixed generated Julia entry script calls `LaSROptions` and `equation_search`, including native concept evolution. Model strings are passed as arguments rather than interpolated into Julia code. `results/native-frontier.json` records equation strings, complexity and native loss. Loss is the search dataset's native objective, not a held-out result. Nonfinite losses remain explicit markers. The outer runner owns process timeout and executable provenance.
