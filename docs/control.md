# Private queue and worker control

`python -m arena.control` adds an authenticated private control service to the
existing board. Serving HTTP never executes framework code. Separate `worker`
processes explicitly call `arena.frameworks.runtime.run` for admitted templates.
The implementation has local fixture coverage and passed an explicit inert Linux
VM conformance probe, including kernel resource limits and descendant cleanup;
see [the validation record](reportscontrolvm.md). These checks did not launch a
research framework or make a paid model call.

Copy [control.example.json](control.example.json) to a private location outside
the checkout, for example `/srv/arena/control/config.json`, set its mode to
`0600`, and set its `state_dir` to a directory owned by the service user with mode
`0700`. Keep sources, environments, and the installed Arena application read-only.
The example contains a blocked placeholder, not an executable framework claim.

```sh
/opt/arena/venv/bin/python -m arena.control check --config /srv/arena/control/config.json
/opt/arena/venv/bin/python -m arena.control create-key --config /srv/arena/control/config.json --owner research-agent --scope read --scope submit --scope cancel --scope logs:native --max-runs 100 --max-seconds 86400
/opt/arena/venv/bin/python -m arena.control serve --config /srv/arena/control/config.json --port 8080
/opt/arena/venv/bin/python -m arena.control worker --config /srv/arena/control/config.json --concurrency 50
```

The key creation command prints a newly generated bearer token once. Give it to
the intended agent through a private channel. SQLite stores only its SHA-256
digest, identity, scopes, and budgets. The `revoke-key --key-id …` command prevents
future requests and submissions; it does not cancel already authorized work.
Use `--scope admin` for a separate administrative key. An administrator can access
all runs and record explicitly blocked matrix cells. A `read` key sees the shared
sanitized queue and template inventory, but only its owner's run detail and logs.
`cancel` and `submit` do not implicitly grant `read`. Scope `logs:native` additionally
permits redacted native diagnostics for the same owner; admin includes this scope.

`serve` binds only `127.0.0.1`. Use an SSH tunnel or a separately authenticated
private proxy. The board, `/queue`, observer routes and control routes share port
8080. Without a control service passed to `DashboardServer`, the existing observer
remains read-only and has no control endpoints. Observer roots are explicit
`--observe` arguments; never point the unauthenticated observer at private control
state or sensitive worker output.

## Reviewed templates and admission

Every template binds a framework, native profile, model, complete native run spec,
CPU count, RAM in MiB, process limit, and evaluation-slot allocation. The service
accepts a template ID rather than caller-supplied code, paths, native arguments,
or concurrency settings. A ready template needs an exact native spec with
`output_dir: "{output_dir}"`, `containment: "cgroup-v2"`, and
`evaluation_concurrency_verified: true`. The only substitutions are
`{output_dir}` and `{control_cgroup}` in the reviewed spec. The latter identifies
the empty parent of the run's cgroup hierarchy, suitable for Station's native
child-cgroup driver. Credential values and inline code are forbidden in specs;
use `environment_names` to reference secrets supplied to the worker environment.
The worker sets and forwards reserved `ARENA_CONTROL_RUN_ID`,
`ARENA_EVALUATION_CGROUP_PARENT`, and `ARENA_EVALUATION_RECEIPTS_DIR` values after
admission. The receipt directory is unique to the run under
`artifacts/canonical-evaluations`. Canonical Docker bridges can require these
trusted values; an inherited environment value cannot replace the admitted run's
actual containment or receipt destination.

The operator must verify the template's native concurrency settings against its
pinned implementation, including nested evaluation pools, parallel agents,
numeric-library threads, memory use and external services. The verification flag
records that review; it cannot infer a framework's actual evaluation semantics.
Reserve the maximum simultaneously active native evaluations for the entire
research run. Unknown or unbounded concurrency, missing hardware, unprepared
dependencies and unmanaged external execution require a `blocked` template with
an explicit reason. Do not label every framework as one CPU/two GiB by default.

Admission uses a SQLite `BEGIN IMMEDIATE` transaction across every worker. It
reserves CPU, RAM, evaluation slots, and an active-run slot together. Default
deployment planning reserves 96 CPUs, 300 GiB and at most 32 evaluation slots,
with initially eight active runs. `max_active` is reloadable and is not permanently
limited to eight. Starting 50 idle worker threads permits a later ramp without
restarting active workers. With conservative whole-run reservation and a minimum
of one evaluation slot per active run, 32 slots still permit at most 32 concurrent
research runs. Fifty simultaneous research runs would require separate admission
at evaluation boundaries, which this version does not provide.

Key limits reserve a run count and maximum wall seconds at submission, including
queued runs. Cancellation does not refund either budget, so retries cannot bypass
the cap. The gateway must separately enforce model access, token and monetary
budgets; wall-time admission is not a dollar-spend limit. A revoked key cannot
submit further work. Queue capacity is configurable (`max_queued: 2048` is suitable
for a matrix larger than 500 cells).

Replacing the private configuration atomically and calling authenticated
`POST /api/control/reload` installs a new revision in the HTTP service. Workers
reload valid configuration before claims. Invalid updates prevent new claims
until corrected; in-flight runs continue with their admitted snapshots. Lowering
limits does not kill existing runs; it stops additional admission until capacity
fits. State directory and cgroup root cannot change during a live service reload.
Each run's private snapshot and hash preserve its original template and cgroup
root even across service restarts. Public APIs expose neither snapshots nor paths.

## Linux containment and service setup

Use a dedicated non-root account on Linux with cgroup v2 `cpu`, `memory` and
`pids` delegation and writable `cgroup.kill`. The configured `cgroup_root` must be
an empty delegated child beneath `/sys/fs/cgroup`, with those controllers enabled
for children. The worker supervisor must start in a sibling leaf beneath that
same delegated root. Merely owning the destination cgroup does not permit a
non-root process to migrate from an unrelated `system.slice` or SSH session:
cgroup v2 also requires write permission at the common ancestor. Do not grant
write access to the kernel root's `cgroup.procs` to work around this restriction.
The deployment's privileged, fixed-path launcher moves itself to the dedicated
`supervisor` leaf and then resets supplementary groups and drops GID and UID before starting
Python. The unprivileged worker can subsequently migrate its helpers between
children of the delegated root. Merely creating a regular directory with the
same name does not satisfy kernel cgroup requirements.

For each run the worker creates a new owned child, writes `cpu.max`, `memory.max`,
`memory.swap.max=0`, and `pids.max`, enables child controllers and creates a `main`
leaf. An execution gate records the child PID and Linux boot/start identity before
allowing it to join the leaf and call the native runtime. All ordinary descendants,
including new process sessions, inherit the cgroup. The whole-run wall timeout
also includes preparation. Cancellation, timeout and normal completion kill any
remaining descendants before releasing reserved resources.

See the concrete [worker service](../scripts/deployment/arena-worker.service),
[fixed-path launcher](../scripts/deployment/start-worker.py) and
[delegation setup](../scripts/deployment/setup-cgroups.sh). Their installation
locations and ownership are part of deployment preparation. The ordinary
unprivileged CLI remains suitable when the caller already belongs to the
delegated subtree. Native programs never run with the launcher's root identity.

Supply the gateway client key to the worker through the deployment's private
environment mechanism. Never give native workers the provider's upstream JWT.
The HTTP service need not inherit worker credentials. Resource cgroups are not a
filesystem, network, credential or hostile-code security sandbox. This mode is
for reviewed native frameworks and trusted runs on a dedicated worker account.
It is not a multi-tenant arbitrary-code execution service.

A Docker daemon or cloud worker executes outside ordinary process ancestry.
Such profiles remain blocked unless their native driver provides owned-container
cleanup and explicitly places every local container under the reserved cgroup
with equivalent limits. The control layer does not pretend that killing the
client process kills external containers or remote jobs. There is no automatic
Docker-socket access or remote service launch in this module.

## Durable lifecycle and restart behavior

Runs transition through `queued`, `preparing`, `running`, then `completed`,
`failed`, `cancelled`, or `blocked`. A completed process is not a canonical
scientific success; API records retain `canonical_evaluation: false`. Native or
canonical evaluator receipts remain separate artifacts.

Claims and leases are persisted. An expired lease never requeues or relaunches a
run. Reconciliation checks the original cgroup and recorded PID identity. Live
or unreadable containment retains its full reservation and is shown as blocked
when the liveness check confirms an orphan. An empty, dead run can recover a
bounded terminal result, otherwise it becomes blocked without retry. Explicit
cancellation of an orphan kills only its owned run cgroup. A failed cleanup
retains reservations until a later reconciliation can establish that all members
have exited. Do not delete private state to recover capacity while processes may
still exist.

## Agent HTTP contract

All control requests require `Authorization: Bearer <key>`:

| Method and path | Purpose |
| --- | --- |
| `GET /api/control/templates` | Reviewed template IDs, framework/profile/model, status, resources, revision and limits |
| `GET /api/queue?limit=200&offset=0` | Shared sanitized overview, state counts and reserved/global capacity |
| `GET /api/control/results` | Bounded scalar results for own runs; admin can inspect all runs |
| `POST /api/queue` | Submit one reviewed cell or, for an admin, record a blocked cell |
| `GET /api/queue/{id}` | Own run detail, or any run for admin |
| `GET /api/queue/{id}/logs` | Own bounded lifecycle log; native diagnostics require extra scope |
| `POST /api/queue/{id}/cancel` | Request cancellation; empty body or `{}` |
| `POST /api/control/reload` | Admin-only atomic configuration reload; empty body or `{}` |

Submission body:

```json
{
  "schema": "arena.control-submit/1",
  "template": "reviewed-profile-model-cell",
  "model": "configured-model-id",
  "label": "Initial comparison",
  "batch_id": "comparison-001",
  "idempotency_key": "comparison-001-cell-001"
}
```

`model` must exactly match the template. Optional `idempotency_key` is bound to
the submitting key and complete submission identity; identical retries return
the original run and `duplicate: true`, while rebinding returns HTTP 409. Different
keys can intentionally submit separate runs. `batch_id` groups a matrix for the
board. Unknown fields are rejected. Run-count, reserved-runtime and queue limits
return HTTP 429. Missing/bad credentials return 401 and insufficient scope 403;
another owner's private detail/log/cancellation returns 404.

Queue responses contain `runs`, `counts`, `resources: {used, limits}`, `total`,
`offset`, `limit`, and `revision`. Detail and submission responses contain `run`.
Each run includes identity/model/profile, state/reason, timestamps, resource
allocation and `resources_reserved`; private source paths, specs and token hashes
are omitted. `logs` accepts `stream`, byte `cursor`, `limit` up to 65536, and
`tail=true`. Its response contains `text`, `cursor`, `next_cursor`, `size`, `eof`,
`truncated` and `policy`.

`stdout` and `stderr` contain fixed control lifecycle messages only.
`native_stdout` and `native_stderr` require `logs:native` (or admin) and contain
worker-redacted diagnostic snapshots. The worker reads at most 8 MiB per native
stream, removes exact credential values from its inherited credential environment,
redacts JWT/Bearer/common provider-key patterns, and writes an atomic private
snapshot. Growing partial known credential suffixes are redacted too. Pagination
happens after whole-snapshot redaction, so a cursor cannot slice around a token.
The HTTP process never falls back to raw framework logs or other prompt/config
artifacts. Missing snapshots return `pending: true` and empty text.

Native logs can contain generated code or other research data and are available
only through the extra scope. Pattern redaction cannot guarantee removal of
arbitrarily encoded, transformed, split or previously unknown secrets. Keep
upstream credentials out of native environments and use revocable gateway-only
keys. Snapshots can lag raw output or stop updating after a worker crash; the API
does not weaken access or redaction to recover that gap. Live cursor positions
refer to the latest redacted snapshot; use bounded tail requests for live viewing.

Tests use temporary SQLite stores, fake kernel control files, inert runtime
stand-ins and loopback HTTP. No paid calls, native research runs or deployment
changes are part of this validation.
