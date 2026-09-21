# Private control VM conformance — 2026-09-21

The private queue, native runtime handoff, scoped diagnostics and Linux resource
containment passed an isolated conformance run on the deployment VM. Every
program in this probe was an inert fixture. No research framework, model API,
paid call, provider upstream token, Docker evaluator or cloud job was used.

The test ran as the unprivileged `arena` account in a private validation directory,
with a separate SQLite queue and configuration. A small root launcher first moved
it into an empty supervisor leaf under the delegated cgroup tree and then dropped
all supplementary groups, GID and UID. Its environment was rebuilt from an
allowlist and contained only a deliberately fake provider credential. Production
queue records and real provider credentials were not read or modified.

The reproducible probe is [tests/test_control_vm.py](../tests/test_control_vm.py).
It is not executed by ordinary pytest. Its private test-only adapter invoked the
actual `arena.frameworks.runtime.run` implementation against a fresh, exact-pinned
Git repository containing a short sleep/exit fixture. This verifies the control
contract without asserting compatibility or scientific quality for any framework.

| Check | Observed result |
| --- | --- |
| Actual `python -m arena.control serve` | Anonymous queue/template requests returned 401; read-only submission returned 403 |
| Owner access | Another owner's native-log request returned 404 |
| Native runtime handoff | Exact-pinned fixture completed with a real `arena.native-process/1` receipt and `canonical_evaluation: false` |
| Live diagnostic publication | A flushed native message became available while its process remained running |
| Credential redaction | The fake worker credential was absent from scoped native output; its redaction marker was present |
| Cancellation | Native process and a descendant that started a new session both exited; the owned cgroup disappeared |
| Worker crash and restart | Killing only the supervisor left native work alive; stale-lease reconciliation marked it blocked and retained its allocation |
| Duplicate prevention | A restarted worker could not claim or relaunch the orphaned run |
| Orphan cancellation | Explicit cancellation killed the owned group; resources were released only after exit was established |
| CPU enforcement | Three busy-loop fixture children under one CPU produced 20 throttled periods; `cpu.max` was `100000 100000` |
| Memory enforcement | A 384 MiB allocation under a 128 MiB cap produced one kernel OOM kill; `memory.max` was `134217728` |
| Token storage | The freshly generated validation bearer token was absent from SQLite file bytes |
| Final state | One completed fixture, two cancelled fixtures; active runs, CPUs, RAM reservations and evaluation slots all returned to zero |

The host kernel was `6.8.0-59-generic`. The production worker pool's kernel limits
were independently read as `cpu.max = 9600000 100000` (96 CPUs) and
`memory.max = 322122547200` (300 GiB). A subsequent anonymous request to the
production board's `/api/queue` returned 401. Production templates were not
submitted by this probe.

Exact code evidence for the successful isolated run:

| Artifact | Identity |
| --- | --- |
| `src/arena/control.py` | SHA-256 `96f492eae0d4529084579c15f33b9f1003c4252dd818af9ecbd8425b45c94c7a` |
| `src/arena/frameworks/runtime.py` | SHA-256 `8b406789e642b97984070722c2a19a999b3e1ccaf9dd6ec6ceb96e0c8599af89` |
| Inert source repository | Commit `5c7e26cb3be1e9feccb98002183d9f72fc16ba79` |

Initial attempts found three integration problems that were corrected before the
successful run: CLI module identity downgraded authentication errors to HTTP 400;
an unrelated SSH/systemd cgroup could not migrate into the delegated tree; and
buffered runtime capture hid short live messages. The control entrypoint now uses
one canonical module identity, the deployment launcher enters the delegated
supervisor before dropping privileges, and native capture uses incremental reads
and flushes. Cgroup-entry failures also produce bounded, redacted diagnostics
under the additional native-log scope.

Earlier failed fixture sessions were reconciled without relaunching anything.
The temporary supervisor cgroup was removed after confirming it was empty. The
private validation artifacts were retained for inspection; no validation process
or resource reservation from the successful session remained active.

These results establish the tested control and kernel behavior. They do not turn
cgroups into a hostile-code sandbox, prove a framework's declared evaluation
concurrency, validate Docker-daemon containment, or establish scientific evaluator
correctness. Those require their own profile-specific checks. The 32-slot budget
still depends on conservatively reviewed fixed native concurrency settings.

Local focused validation after the changes: 61 tests passed, plus 37 observer
subtests, with `tests/test_control.py` and
`tests/observer/test_dashboard_server.py`.
