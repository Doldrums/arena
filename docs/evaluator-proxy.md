# Canonical evaluator Docker boundary

Run native research frameworks as the `arena` worker UID, without membership in
the Docker group. A writable Docker socket otherwise gives that UID host-root
access, including access to the separately owned private provider token.

`python -m arena.evaluator_proxy --config /etc/arena/evaluator.json` exposes a
restricted Unix socket. The root service alone connects to the actual daemon.
It accepts the precise Docker CLI profile emitted by `frameworks/evaluation.py`;
it is not a general Docker API or a privileged native-framework runner.

Example operator-owned configuration (replace the image with the built digest):

```json
{
  "docker_socket": "/var/run/docker.sock",
  "socket_path": "/run/arena-evaluator/docker.sock",
  "staging_root": "/run/arena-evaluator/staging",
  "tasks_root": "/srv/arena/sources/autoresearch-tasks",
  "run_roots": ["/srv/arena/control/runs"],
  "images": ["sha256:REPLACE_WITH_64_HEXADECIMAL_CHARACTERS"],
  "worker_uid": 998,
  "worker_gid": 998,
  "cgroup_root": "/arena-workers",
  "max_containers": 16,
  "timeout_seconds": 3600
}
```

The worker environment uses
`DOCKER_HOST=unix:///run/arena-evaluator/docker.sock`. Explicitly preserve this
nonsecret variable through control template `environment_names`, the native
runtime, evaluator subprocess environment, and evaluator cleanup. Do not put the
real daemon socket or Docker group in the worker service. Keep the provider JWT
under the separate provider UID; the worker receives only its scoped gateway key.

The caller's kernel `SO_PEERCRED` must report the configured worker UID. Its
unified cgroup must be
`/arena-workers/arena-control-<32-hex-run-id>/main[/...]`. The create request must
include these exact labels and parent:

```text
--label arena.evaluator=canonical-v1
--label arena.control-run=<run-id>
--cgroup-parent /arena-workers/arena-control-<run-id>
```

The Docker daemon must use the `cgroupfs` driver for this parent syntax. All
containers remain inside the control run's outer resource limits and cancellation
group. Inside that group, each evaluation is limited to 1 CPU, 2 GiB memory with
no additional swap, and 128 processes. The root filesystem is read-only, network
is `none`, all capabilities are dropped, and `no-new-privileges` is enabled.
The proxy reconstructs the request; privileged mode, devices, GPUs, namespaces,
host networking, additional environment variables, alternate entrypoints, extra
binds, and resource overrides cannot pass through. The image must match an
operator-listed immutable digest.

Only the canonical command shape is accepted:

```text
python /tasks/run.py --root /tasks evaluate TASK_ID \
  --candidate /candidate/program.py --python python \
  --timeout SECONDS --output /results/native.json
```

`python3` is also accepted. The task checkout is one exact configured path and
must be root-owned, link-free and not writable by group or others, including its
ancestors. Provision and verify its registry pin before starting the service.
The proxy checks filesystem ownership, not the scientific correctness of that
checkout; source pin and evaluator hashes remain recorded by Arena evaluation.

Candidate and output directories must be siblings exactly here:

```text
RUNS_ROOT/<caller-run-id>/artifacts/canonical-evaluations/<evaluation-uuid>/input
RUNS_ROOT/<caller-run-id>/artifacts/canonical-evaluations/<evaluation-uuid>/native-output
```

`candidate` is accepted instead of `input` for equivalent bridge layouts. Generic
`/tmp`, `/srv`, other runs, provider directories, and control database paths are
not mount capabilities. The bridges should use the reserved control-provided
receipt root, rather than an arbitrary native configuration path.

## Staging and bounded storage

Path checks alone are insufficient: an untrusted worker can replace a checked
directory with a symlink before Docker opens it. The proxy opens each path
component with `O_NOFOLLOW`, snapshots only a stable worker-owned regular
`program.py` (at most 16 MiB, no hard links), and retains an open descriptor for
the original output directory. Docker receives root-protected staging paths,
never those mutable worker paths. Only a regular worker-owned `native.json` of
at most 4 MiB is copied back through that held descriptor, using an atomic rename
which does not follow an existing destination symlink. Other output files are
discarded. Receipt/request files are outside the writable container mount.

Provision the staging directory as a **host-visible dedicated tmpfs**, for
example, as root:

```sh
install -d -o root -g root -m 0755 /run/arena-evaluator
install -d -o root -g root -m 0700 /run/arena-evaluator/staging
mount -t tmpfs -o size=128m,mode=0700,nodev,nosuid,noexec tmpfs /run/arena-evaluator/staging
```

The service validates an exact tmpfs mount sized between 16 and 256 MiB. A
128 MiB tmpfs bounds aggregate candidate snapshots and container output, even if
malicious code fills `/results`. It can exhaust this shared allowance and cause
other evaluations to fail; this is a bounded denial of service, not a per-run
storage quota. `/tmp` inside each container is separately limited to 256 MiB and
counted by the container memory limit. Docker's local log driver is limited to
one 1 MiB file. The proxy bounds incoming JSON to 128 KiB, regular responses to
4 MiB, and attached output to 16 MiB, with 64 concurrent connections and at most
the configured number of containers. Containers exceeding their requested
evaluation timeout plus 60 seconds are force-removed by the proxy reaper.

Do **not** use a service-private `TemporaryFileSystem` for this path: Docker's
daemon must see the same host mount. Keep the staging parent root-owned and mode
0700. Do not grant the worker write access to the socket's parent; the socket
itself is root-owned, worker-group mode0660.

## Service and lifecycle

Use the checked-in `scripts/deployment/arena-evaluator-staging.service` and
`arena-evaluator-proxy.service`, with `setup-evaluator-staging.sh` executable.
The root proxy service uses `NoNewPrivileges=yes`, `ProtectSystem=strict`,
`ProtectHome=yes`, and narrowly scoped writable paths for the socket/staging and
`/srv/arena/control/runs` (result publication).
Add `InaccessiblePaths=/etc/arena/provider /etc/arena/admin-access.json
/etc/arena/agent-access.json` as defense in depth. The proxy needs neither model
credentials nor control database contents. The actual Docker daemon remains a
privileged service; its image and source allowlists must be managed by the
operator. Do not grant the proxy untrusted configuration write access.

Allowed HTTP operations are ping/version; create; and start, attach, wait, logs,
inspect, kill, delete for containers created by this proxy and the same caller
run. There is no image pull/build, exec, archive, volume, network, or system API.
One synthetic `/info` response supports the Docker CLI preflight: it exposes
only `CgroupDriver` and `CgroupVersion`, checked against the actual daemon's
`cgroupfs`/`2` values. General daemon inventory and system fields are discarded.
Docker's upgraded attach channel relays stdout/stderr from daemon to client
only; it does not forward stdin. Wait headers are forwarded before container
start, and the bounded result is published before the wait body or attach EOF
reaches Docker CLI. JSON errors are generic and the service emits
no prompt, candidate, credential, or Docker body logs.

Normal shutdown force-removes owned containers and publishes any available
bounded result. Root-owned staging records permit label-verified orphan cleanup
after restart; a stale root-owned Unix socket is replaced only if no listener
accepts a connection. Interrupted evaluations are not silently retried. Existing
results and canonical receipts continue to determine whether a run succeeded.

This proxy confines host Docker capabilities. The candidate and task evaluator
still share one container/process environment: it is not an adversarial scoring
verifier. Likewise, peer cgroup membership proves location, not independent
queue authorization when the worker UID itself can create/move cgroups. Strict
per-run admission additionally requires control-owned cgroup creation or an
independent admission capability. These limits do not grant access to extra host
mounts, images, the provider token, or unrestricted Docker APIs.

Verification without Docker or paid calls:

```sh
.venv/bin/python -m pytest -q tests/test_evaluator_proxy.py
```

The create fixture was captured from the installed Docker CLI against an inert
Unix HTTP server. Tests exercise its actual request shape, forbidden capabilities,
file/link/rename attacks, caller identity, and upgraded multiplexed attach.
Real VM conformance must additionally confirm the daemon cgroup driver, mount
visibility, socket permissions, canonical result copy-back, cancellation, and
that the worker cannot open the real Docker socket or provider token.
