# Native framework adapters

Arena provides explicit local adapters for the available, source-verified
research implementations in its library. Native launch profiles preserve each
framework's search and evaluation interfaces, record source/input hashes and
process receipts, and inspect saved artifacts without importing participant
code. These commands are separate from the read-only board and API.

The [current coverage audit](../../reports/framework-coverage-20260921.md)
accounts for every participant, including shared engines, independent
reimplementations, artifact-only releases and sources without a verified
execution interface. `python -m arena.frameworks list` lists the exact engines,
profiles, setup requirements and limits. A source-verified profile is not a
claim that a model-driven research run has completed.

Recipe guides: [program search](program-search.md),
[agent and harness systems](agent-systems.md),
[prompt, ML, robotics and GPU systems](specialized.md),
[EoB, EvoOR-Agent, DrEureka and LaSR](additional.md), and
[independent AVO/OpenEvolve implementations](community.md).
[The Station](station.md) has a foreground session supervisor for its detached
workers; [original-author FunSearch](funsearch-original.md) has explicit model
and sandbox provider seams and is distinct from the later corpus reimplementation.

The three original system registrations also have dedicated adapters:

| Framework | Native launch and results | Evaluation adapter |
| --- | --- | --- |
| [SCiEL](sciel.md) | Ordinary Engine CLI, journal and checkpoint | Arena `reference-sat` profile; syntax-only smoke, one full evaluation |
| [ShinkaEvolve](shinka.md) | Native runner, `programs.sqlite` | Arena Python suite bridge; task-specific dependencies and conformance still required |
| [DGM](dgm.md) | Native outer loop in an isolated checkout, JSON records | Native SWE-bench or Polyglot episodes; Arena task-library episodes require a separate harness integration |

Source inspection and fixture tests verify the drivers. The shared evaluator
also has offline Docker conformance evidence; this does not establish a full
model-driven native run, broad task compatibility, or comparable performance.
The registry uses `native_cli` and `runtime_readiness: not_verified`. Its
`canonical_evaluation` capability stays false until an entire framework run
passes end-to-end conformance; `integrated_count` therefore remains zero.

The research library's 99 records are not 99 independently runnable engines.
Paper authorship and an available implementation's ownership are separate;
OpenEvolve and community AVO are explicitly identified as independent engines.

## Commands

Use the Arena Python environment. Listing and planning do not import or run a
framework, download dependencies, start containers or contact model providers.

```sh
python -m arena.frameworks list
python -m arena.frameworks plan /absolute/native-run.json
python -m arena.frameworks run /absolute/native-run.json
python -m arena.frameworks results shinka --output /absolute/new-run
```

## Recipe-based native interfaces

For a source-verified recipe, choose its engine ID and one of its named profiles.
Supply native arguments as a JSON array, without shell quoting or shell syntax.
Only `run` imports and invokes the external implementation.

```json
{
  "schema": "arena.native-run/1",
  "framework": "openevolve",
  "source_dir": "/absolute/clean-pinned-openevolve",
  "output_dir": "/absolute/new-experiment",
  "timeout_seconds": 600,
  "environment_names": ["OPENAI_API_KEY"],
  "request": {
    "python": "/absolute/native-env/bin/python",
    "profile": "native-evolution",
    "arguments": ["arena-inputs/initial.py", "arena-inputs/evaluate.py",
                  "--config", "arena-inputs/config.yaml", "--iterations", "2"],
    "inputs": {
      "arena-inputs/initial.py": "/absolute/experiment/initial.py",
      "arena-inputs/evaluate.py": "/absolute/experiment/evaluate.py",
      "arena-inputs/config.yaml": "/absolute/experiment/config.yaml"
    }
  }
}
```

Prepare the exact pinned native environment yourself; no dependency installer
runs during discovery, planning or validation. The source checkout must be
clean, complete and at the recipe's immutable revision. Source entrypoint and
evaluator file hashes are checked before launch.

Execution clones the source into `OUTPUT/workspace/ENGINE`. `request.inputs`
copies explicitly hashed files/directories into new relative paths there.
`request.config_overlays` can replace only config files declared by that profile;
it cannot replace evaluator source. The original checkout remains unchanged.
Profiles that need Julia or Codex declare `request.executables`: their exact
executable paths and hashes are recorded and checked again before launch.
Fixed algorithm/output arguments, including their abbreviations, cannot be
overridden. Native output ancestors containing an implicit `.env` are rejected.

Native result readers require the recorded recipe, source and a pre-run
artifact baseline. Unchanged checked-in results and staged inputs never count
as results of the new run. File traversal, sizes and hashing are bounded;
symlinks and Git/receipt internals are excluded. Pickle, SQLite and other opaque
artifacts are never deserialized by the generic observer. The inventory reports
artifact evidence, not a shared score, candidate validity or experiment success.

Most recipes use their own native evaluators. They do not yet accept every
Arena catalog task or produce canonical Arena evaluation receipts. Hardware,
data, native provider APIs, model cost and environment conformance remain
profile-specific. The direct task bridges below are a narrower, separately
validated contract.

## Direct adapter request

The run spec selects an existing clean checkout at the exact registered commit
and an existing environment containing that framework's dependencies. Arena
does not install dependencies implicitly. Keep the checkout separate from a
working development tree.

```json
{
  "schema": "arena.native-run/1",
  "framework": "shinka",
  "source_dir": "/absolute/pinned-shinka-checkout",
  "output_dir": "/absolute/new-run",
  "timeout_seconds": 600,
  "environment_names": ["OPENAI_API_KEY"],
  "request": {
    "python": "/absolute/shinka-venv/bin/python",
    "task_dir": "/absolute/arena-shinka-task",
    "num_generations": 2,
    "native_config": {
      "llm_models": ["your-provider/model"],
      "embedding_model": null,
      "max_api_costs": 0.5,
      "evaluation_timeout": "00:01:00",
      "max_evaluation_jobs": 1,
      "max_proposal_jobs": 1,
      "max_db_workers": 1
    }
  }
}
```

Only explicit `environment_names` and basic operating-system paths/locales are
inherited. Credential values are never included in the plan or receipt.
Native logs remain raw local artifacts and can contain native diagnostic data.
The `.arena` metadata directory is private to the current user. Existing output
directories are never overwritten or silently resumed.

`.arena/plan.json` records the source commit/tree, explicit input SHA256s, exact
argument vector, interpreter hash and a plan hash. It does not claim to lock
every installed dependency, externally referenced configuration file or data
source. `.arena/receipt.json` reports process completion/failure/timeout;
process exit zero is not scientific success. `.arena/native-result.json` keeps
native scores separate from task evaluation receipts.

The driver terminates the launched POSIX process group at its timeout. Native
frameworks can create detached groups, Docker containers or remote jobs; these
are not all governed by that group. Run native research in a dedicated worker
environment with external resource limits. The driver is not a general sandbox,
Vast supervisor, remote queue, monetary budget enforcer or pause/resume service.

## Pinned task evaluation

An evaluation config selects a catalog task, the exact task-source checkout,
a per-evaluation timeout and an execution environment. Images must already be
available locally and use a repository digest or immutable local image ID.
Evaluation never pulls an image or starts a model call.

```json
{
  "schema": "arena.evaluation-config/1",
  "tasks_dir": "/absolute/autoresearch-tasks",
  "task_id": "alphaevolve-circle-packing-in-unit-square",
  "timeout_seconds": 30,
  "execution": {
    "kind": "docker",
    "image": "your-evaluation-image@sha256:REPLACE_WITH_64_HEX_DIGEST",
    "python": "python"
  }
}
```

```sh
python -m arena.frameworks evaluate /absolute/evaluation.json \
  --candidate /absolute/program.py --output /absolute/new-evaluation --plan
python -m arena.frameworks evaluate /absolute/evaluation.json \
  --candidate /absolute/program.py --output /absolute/new-evaluation
python -m arena.frameworks create-task shinka /absolute/evaluation.json \
  --output /absolute/arena-shinka-task
```

Docker runs have no network, a read-only root and task/candidate mounts, a
temporary filesystem, one CPU, 2 GiB memory and 128 PIDs. The candidate is copied
and hashed before evaluation. The task repository, problem manifest and
evaluator are bound to the registry's immutable revision and hashes. Generated
candidates and the upstream evaluator still share a process/container; these
receipts are not a proof of resistance to an adversarial candidate that tampers
with its evaluator.

The explicit `local_trusted` profile with an absolute `python` path is for
reviewed fixtures on the host; it provides no sandbox. Use Docker for generated
code. Dataset/GPU/network-dependent tasks need additional reviewed environment
profiles; they do not become runnable merely by appearing in the catalog.

Every invocation creates a unique `arena.evaluation/1` receipt, native result
and bounded logs. There are no automatic retries or caches. A repeated request
with the same output path is rejected; an intentional repeat gets a new path
and evaluation ID. Raw score and objective direction remain unchanged. Fitness
is the raw score for maximization and its negation for minimization, only when
the evaluator explicitly validates the candidate. Unknown validity remains
unknown and is not admitted as a successful search candidate.

SCiEL's currently pinned refinement/binning logic requires a narrower profile.
Its task creator accepts only the source-verified `reference-sat` unit-interval
profile and requires an explicit receipts directory. See its [adapter guide](sciel.md)
for the generated config overlay. Do not use a sign flip to pretend arbitrary
minimization is supported by that SCiEL version.

Neither registry validation, the board nor the cloud Worker calls these launch
or evaluation commands. No paid native experiments are part of the local tests.

Private engines can use the separate [private release contract](../private-releases.md):
the public PR contains only the system/version reference, while the worker
resolves immutable private source/image pins. The release resolver does not
yet dispatch container runs or issue access keys.
