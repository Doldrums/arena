# Private SCiEL image execution

`arena.engine_broker` runs an operator-approved immutable SCiEL image. It accepts
only an admitted run ID and the SHA-256 of a private deployment manifest. It
never accepts client-selected commands, Docker options, mounts, or credentials.
Planning, manifest creation, and page loads do not run the image.

The Unix API at `/run/arena-engine/sciel-images.sock` authenticates Linux peer UID
and the caller's run cgroup. `POST /v1/run` accepts exactly
`{"run_id":"<32 hex>","deployment_sha256":"<64 hex>"}`. Its NDJSON stream has
`started`, bounded `stdout`/`stderr`, and one terminal `result` frame. The terminal
frame binds the deployment digest, actual image ID, repository digest, source
commit, status and exit code. Only `completed` with exit zero is success. A
disconnect or `DELETE /v1/run/<same run>` terminates the owned engine. Missing
terminal evidence is failure. A run ID cannot be replayed after its root receipt.

## Operator installation

Use the versioned `scripts/deployment/arena-engine-{staging,broker}.service` and
`setup-engine-staging.sh`. The staging service creates a **host-visible** 1 GiB
tmpfs; a systemd private temporary filesystem cannot substitute because Docker
must mount the same files. The services require Linux cgroup v2 and Docker's
`cgroupfs` driver. The worker UID is not in the Docker group.

Root creates `/srv/arena/releases/{approved,engine-receipts}` with mode 0700 and
`/etc/arena/engine-gateway.key` with mode 0600. The key is a local provider gateway
credential, never the upstream JWT. Copy reviewed manifests, byte for byte, to
`approved/<raw SHA-256>.json`, mode 0600. Approval binds the actual RepoDigest and
image ID observed from the local daemon. Image labels are review metadata, not a
cryptographic build attestation.

Example root0600 `/etc/arena/engine-broker.json`:

```json
{
  "socket_path": "/run/arena-engine/sciel-images.sock",
  "docker_socket": "/var/run/docker.sock",
  "evaluator_socket": "/run/arena-evaluator-engine/docker.sock",
  "approvals": "/srv/arena/releases/approved",
  "runs_root": "/srv/arena/control/runs",
  "queue_database": "/srv/arena/control/queue.sqlite",
  "staging_root": "/run/arena-engine/staging",
  "registrations": "/run/arena-engine/registrations",
  "receipts": "/srv/arena/releases/engine-receipts",
  "tasks_root": "/srv/arena/sources/autoresearch-tasks",
  "gateway_key_file": "/etc/arena/engine-gateway.key",
  "config_roots": ["/srv/arena/configs"],
  "task_roots": ["/srv/arena/tasks"],
  "models": ["gpt-5.6-sol"],
  "worker_uid": 998,
  "worker_gid": 998,
  "cgroup_root": "/arena-workers",
  "max_active": 4,
  "max_seconds": 7200
}
```

For a parallel rollout that leaves host pilots untouched, install
`arena-evaluator-engine.service`. Its separate config uses socket
`/run/arena-evaluator-engine/docker.sock` and staging
`/run/arena-evaluator-engine/staging`; both are created by the engine staging
service. The broker mounts that socket at the fixed canonical path inside the
container. Add `engine_registry: /run/arena-engine/registrations` and
`engine_staging_root: /run/arena-engine/staging` to the canonical proxy config.
Its service has read/write access to `/run/arena-engine/staging`
for result publication (the registrations directory needs only read access).
The existing host-pilot proxy is neither reconfigured nor restarted.

## Execution boundaries

The broker independently reads the running queue row and matching snapshot. It
verifies the worker manifest against its root approval, the selected model and
bounded CPU, memory, process and time allocation. It checks the installed image
before creation and the container's actual image after termination. It never
pulls or builds an image. Queue storage currently shares the worker UID: it is
not a separate tamper-proof admission authority against malicious host native
code. Root image, mount, command and resource policies remain independently
enforced. Its database connection uses `mode=ro` and fixed `SELECT` statements.
The service mounts the database read-only but permits its directory for SQLite's
transient WAL/shared-memory coordination; `immutable=1` would wrongly omit live
WAL transactions.

The engine is UID 998, has a read-only rootfs, no capabilities, no new privileges,
a private cgroup namespace and bounded `/tmp`. Initial deployment uses host
networking to reach the local gateway; this is **not network isolation**. It has
no host PID/IPC namespace, host source overlay, real Docker socket, provider JWT,
or control access tokens. Its scoped gateway key exists in process/container
environment and is redacted from streamed logs. Provider and queue limits remain
necessary because native code can use its permitted model credential.

The broker snapshots regular, link-free configs and tasks under a root-protected
tmpfs. SCiEL config is JSON (also valid YAML), with one approved model and the
loopback provider base. Embedded credentials, inherited config and enabled
W&B are rejected. Embedding paths map to `/opt/sciel/models`; the parallel
capacity directory maps to the run's writable artifacts. Original and staged
config digests are both recorded. Input trees and published artifacts are
bounded to 512 MiB, 10,000 entries and 64 MiB per file; symlinks and hardlinks are
rejected. Logs are bounded to 4 MiB and NDJSON frames remain below 64 KiB.

Only root-staged inputs, the run's own artifact directory, reviewed canonical
tasks, restricted evaluator socket and a root context file are mounted. The
context binds the actual engine container ID and run cgroup. The evaluator proxy
independently authenticates the connecting host PID's actual container cgroup
against a root registration, and translates logical artifact paths into that
engine's protected staging tree. Client environment values cannot grant access.

After confirmed engine deletion, the root journal in `engine-receipts` records
pins, snapshot/config/task/artifact hashes and cleanup. The worker gets only a
bounded receipt copy and native artifacts, never authority to rewrite the root
journal. Restart recovery deletes only containers with matching ownership labels
and records interrupted attempts as failures. A cleanup failure never reports
success. Native SCiEL results are not automatically canonical Arena evaluation;
canonical receipts are recorded separately.

Local tests use inert Docker fixtures and never call a model:

```sh
.venv/bin/python -m pytest -q tests/test_engine_broker.py tests/test_evaluator_proxy.py
```

An actual image run through the broker must be recorded separately from these
tests. Image import/CLI checks alone do not prove the research loop executed.
