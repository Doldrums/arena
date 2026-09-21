# The Station native session

The `the-station` engine delegates a bounded session to the native research loop
at [commit 782088e561998bf357d95a838a0566a8229425d9](https://github.com/dualverse-ai/station/tree/782088e561998bf357d95a838a0566a8229425d9).
Its `circle-n32` profile uses the pinned 32-circle packing task, its original
evaluator, the Station agent lifecycle, Codex research workers and native archive
services. Source evidence and inert fixture tests have been checked. A complete
native session and its dependencies have not been verified on this host.

The driver uses the native initializer's copy/configuration functions, creates
explicitly requested agents with `dynamic_add_agent_to_station()`, then invokes
`prepare_for_run()` and `start_orchestration()`. It enables the native automatic
research evaluator. The normal initial agent roster is removed so a session
cannot silently choose six default models. Explicit OpenAI models are used for
agents, archive review and reflection; an explicit Codex model is used for coder
and surveyor services. This profile disables multistart through the upstream
configuration function. No dashboard, nginx, deployment hook or daemon launcher
is started.

## Prepared worker requirements

- Linux with cgroup v2 and a dedicated, writable delegated child directory under
  `/sys/fs/cgroup`. Its parent must already delegate `cpu`, `memory` and `pids`;
  the new child must expose `cgroup.kill`. An operator provisions this delegation.
  Arena does not configure the host's controllers or change unrelated cgroups.
- A prepared Python environment with the pinned Station requirements and native
  task dependencies, plus a prepared named conda evaluation environment. The
  native evaluator resolves that environment using Station's existing logic.
- An explicitly supplied Codex executable and authenticated Codex state for the
  worker user. The executable is fingerprinted by Arena's shared recipe planner.
- `OPENAI_API_KEY` supplied through the run's explicit `environment_names`.
  Codex uses its ordinary worker-owned authentication state. Add only required
  environment names, for example `CODEX_HOME` or `CONDA_BIN_PATH`, when the
  prepared worker needs them. No credential values belong in arguments, recipe
  metadata, configuration overlays or public records.

This is a local process implementation. It does not provision a VM, install
dependencies, build/run Docker images or create cloud resources. Use a dedicated
worker for generated code. Cgroups enforce process membership and resource
limits for this native session; they do not isolate files, networking, secrets
or privileges. A privileged process or one allowed to migrate itself into other
cgroups is outside this containment guarantee. Do not grant those privileges to
the research worker.

## Explicit RunSpec

Use the existing `arena.native-run/1` plan/run interface with a fresh output
directory. The following request is illustrative; model identifiers, worker
paths and credentials must be configured by the operator before an explicit
launch. These values do not claim that a session has run:

```json
{
  "schema": "arena.native-run/1",
  "framework": "the-station",
  "source_dir": "/srv/sources/station-782088e5",
  "output_dir": "/srv/runs/station-example",
  "timeout_seconds": 3630,
  "environment_names": ["OPENAI_API_KEY"],
  "request": {
    "python": "/srv/environments/station/bin/python",
    "profile": "circle-n32",
    "executables": {"codex": "/srv/tools/codex"},
    "arguments": [
      "--model", "OPERATOR_SELECTED_OPENAI_MODEL",
      "--coder-model", "OPERATOR_SELECTED_CODEX_MODEL",
      "--agents", "2", "--ticks", "20",
      "--context-tokens", "128000", "--response-tokens", "8192",
      "--wall-seconds", "3600", "--eval-seconds", "600",
      "--eval-workers", "2", "--cpus", "4", "--memory-gib", "16",
      "--max-processes", "512", "--conda-env", "station",
      "--cgroup-root", "/sys/fs/cgroup/arena-worker"
    ]
  }
}
```

The generic recipe fixes the task, isolated checkout, Codex executable flag and
native output destination. There are no mutable evaluator/configuration overlays
in this profile. Planning is read-only and does not import Station, authenticate,
check model availability or touch cgroups. All readiness requirements are checked
or exercised only when an operator explicitly starts a session.

## Session boundaries and evidence

Before executing participant code, the supervisor puts its worker process in a
new owned cgroup with the requested total CPU, memory and process limits. Native
Codex and evaluation subprocesses inherit that membership even when they create
new POSIX sessions. The supervisor stays in the foreground. It kills every member
of its own cgroup on timeout, interrupt, normal worker completion or launch
failure; it never kills a shared parent cgroup. The outer Arena timeout remains
an additional limit, and should exceed the requested wall time by a cleanup
allowance.

The native `PAUSE_AFTER_TICK_END` boundary stops new agent ticks at the requested
limit. The worker then waits for native research/coder/archive/external queues to
drain, within the same wall-clock limit. It calls `stop_orchestration()` and each
native service's shutdown method on ordinary completion or error. Whole-cgroup
cleanup covers detached workers and a blocked native shutdown path. Cancellation
can leave native YAML records pending or incomplete; those records are retained
as such. A worker that exits before the tick boundary fails rather than becoming
a successful run.

Tick and context/output limits are not a monetary API budget. Provider calls and
native retries can consume money within those bounds. A separately enforced
provider spending budget remains the operator's responsibility.

Artifacts live under `OUTPUT/native/`: `session.json` records process/session
termination, `native-session.json` records the native tick boundary when the
worker reached its finalizer, and `station_data/rooms/research/` preserves native
evaluations and candidate artifacts. The pinned evaluator returns its own
validity and sum-of-radii score. Arena inventories these files without treating
process exit, a published baseline or an unvalidated candidate as a canonical
score. `canonical_evaluation` remains `false` throughout.

Tests replace the native modules and process launcher with inert stand-ins. They
verify call order, explicit agent/model/budget arguments, native initialization,
evaluator shutdown, detached-worker containment hooks, timeout/cancellation
cleanup, failure status, immutable source evidence and an import-free plan. They
do not exercise Linux cgroups, Codex, model APIs or the native research loop.
