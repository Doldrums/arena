# DGM Docker capability

`arena.dgm_proxy` is a separate privileged service for the pinned DGM two-task
Polyglot pilot. Importing its module and running its inert tests do not deploy resources, build
images, run native code, or call a model. The existing canonical evaluator and
SCiEL broker are unchanged.

The native source is `jennyzzt/dgm` at
`a565fd2d1dca504ef5104a7cc0f3bdc4ab9b4fd2`. Native Docker operation evidence and
task preparation are recorded in [the pilot contract](frameworks/dgm-pilot-contract.md).
The provider overlay records the one-line `dgm` → `dgm:latest` lookup correction.
Without this correction the native equality test cannot find Docker's real
`dgm:latest` RepoTag and unnecessarily attempts a build. Dynamic build/pull/tag
and image deletion endpoints remain unavailable; the proxy never reports a
simulated build success.

## Approval and image contract

An operator supplies root-owned mode-0600 `/etc/arena/dgm-proxy.json` containing:

| Field | Value |
| --- | --- |
| `socket_path` | `/run/arena-dgm/docker.sock` |
| `docker_socket` | `/var/run/docker.sock` |
| `state_root` | `/srv/arena/releases/dgm-proxy` (root:root, 0700) |
| `runs_root` | `/srv/arena/control/runs` |
| `queue_database` | `/srv/arena/control/queue.sqlite` |
| `source_path` | `/srv/arena/sources/dgm` |
| `gateway_key_file` | `/etc/arena/engine-gateway.key` (local gateway key, never upstream JWT) |
| `network_id` | The actual 64-character ID of the dedicated internal bridge |
| `relay_url` | `http://172.30.88.1:8789/v1` |
| `models` | Exact operator-approved model IDs |
| `images` | Actual immutable image approvals, described below |
| `container_cpus` | `4` for the approved pilot |
| `container_memory_mb` | `8192` for the approved pilot |
| `container_pids` | `512` for the approved pilot |

Each `images` item has exactly `alias`, `reference`, `image_id`, `parent`, and
`runnable`. `reference` is an actual repository `@sha256:` digest; `image_id` is
the actual Docker image ID. Neither may be inferred from the other. `parent` is
another approved alias or null. The parent chain is base → environment → task;
`dgm:latest` has no parent. Base/environment are inspected but not runnable.
The approved aliases are:

- `dgm:latest`
- `pb.base.x86_64:latest`
- `pb.env.x86_64.ce9e95520b42abb86d1825:latest`
- `pb.eval.x86_64.python__dominoes:latest`
- `pb.eval.x86_64.python__beer-song:latest`

Startup and each runnable image lookup verify real RepoTags, RepoDigests, ID,
Linux/amd64 architecture and required labels. Native parent `Created` ordering
must hold so the native builder genuinely uses its prebuilt branch. Runnable
images have no declared volumes or healthcheck, and must declare:

```text
Entrypoint: /usr/local/bin/arena-dgm-bootstrap
Cmd: tail -f /dev/null
io.arena.dgm.contract=dgm-prebuilt-v1
org.opencontainers.image.revision=a565fd2d1dca504ef5104a7cc0f3bdc4ab9b4fd2
```

Bootstrap copies immutable `/opt/arena-dgm-template` to `/dgm` and
`/opt/arena-testbed-template` to `/testbed`, including Git metadata. It must not
require chown capabilities (`cp -a --no-preserve=ownership` is suitable).
Any necessary reviewed home configuration is restored to the `/root` tmpfs.
Only after both copies finish does it create `/tmp/.arena-dgm-ready`, then exec
the native idle command. The proxy tests that actual marker through Docker
before returning a successful start. A bootstrap failure is not treated as
native success.

The original Python PATH is retained. In particular, Polyglot's executed
`harness.py` evaluation script runs plain `pytest`; it does not activate the
otherwise-prepared `testbed` conda environment. Dependencies and pytest must be
preinstalled in the coding/base interpreter as well as the native testbed
environment. Native pip invocations are preserved. A newly requested dependency
that is unavailable offline fails explicitly; no pip commands are silently
filtered, and no algorithm or test is replaced.

## Admission and containment

Only Linux SO_PEERCRED worker UID 998 in the exact admitted host
`/arena-workers/arena-control-<run UUID>/main` cgroup may call the Unix API.
Every request checks a running, held, uncancelled queue row and the hashed
snapshot. Framework must be `dgm`, benchmark `polyglot`, source path approved,
model exact, and resources/timeout equal the admission. The runtime remains
responsible for exact clean source-pin and input provenance validation.

Containers have real daemon IDs, root-issued physical names and labels.
An original native name resolves only within its own run. Unknown/foreign
containers return 404 without querying arbitrary daemon objects. Exec IDs are
usable only by their owning run. Neither the worker nor the containers receive
the real Docker socket. The worker must **not** join the Docker group.

Each child has a read-only root filesystem, private cgroup namespace, dropped
capabilities, no-new-privileges, no devices, no host namespaces and no host
mounts. The operator-approved pilot explicitly sets **4 CPU and 8 GiB RAM/no
swap per child**, inside a **4 CPU, 16 GiB admitted parent**; the parent's CPU is
shared across concurrent native children and the host loop. The library's
fallback child defaults (1 CPU/2 GiB) are not the intended pilot configuration.
Default child PID limit is 256. The admitted parent cgroup bounds aggregate
child and native process consumption.
Per run: at most four live containers and 128 container creations. Writable
tmpfs sizes are `/dgm` 768 MiB, `/testbed` 768 MiB, `/tmp` 256 MiB and `/root`
64 MiB; their resident pages also count against the child memory limit.
Docker disk logs rotate at 4 MiB. Up to 8,192 journal records are retained before
the service requires operator archival.

Native exec commands, including Git, pip, patches, agents and pytest, remain
native. They run only in owned containers, with bounded command arguments,
output, wall time and resources. Host PID fields and container Env are omitted
from inspection projections: the native fallback must not issue `os.kill` on a
host Docker PID. Interactive stdin, TTY, detached exec and privileged exec are
unsupported. The reviewed two-task path uses synchronous noninteractive exec.
No extra command emulation or synthetic score is provided.

## Network and provider relay

An explicitly invoked operator helper,
`scripts/deployment/setup-dgm-network.sh`, creates an internal bridge with
inter-container connectivity disabled. It refuses to change the policy while
DGM containers are running. A dedicated INPUT firewall chain allows only TCP
8789 at the bridge gateway and drops access to every other host address/port.
Startup checks the chain contents and requires its INPUT jump first. Docker
internal-network rules block external routing; IPv6 is disabled and container
DNS is set to loopback. No internet or package-registry access is provided.

The same service hosts a fixed relay at `172.30.88.1:8789`. Only actual IPs of
owned, labelled, admitted containers are accepted. Routes are exactly GET
`/v1/models`, POST `/v1/responses`, and POST `/v1/chat/completions`; no arbitrary
host, URL, port or method is forwarded. Bearer credentials must match the local
gateway key and request model must equal the admitted model. The relay forwards
to fixed `127.0.0.1:8789`, preserving gateway compatibility-policy headers.
Request bodies are limited to 1 MiB and responses to 16 MiB.
Socket read deadlines apply from connection setup, including incomplete HTTP
headers before authentication, so quiet clients cannot reserve all relay slots
indefinitely.

The upstream provider JWT is never read or mounted. The local gateway credential
necessarily exists inside the native model process; this is a limited model API
capability, not access to the upstream JWT or control APIs. Generated code shares
its native container and can see that capability. This is not a separate
security boundary between an agent and its generated code.

## Archives, cancellation and recovery

Both archive directions are validated and repacked before crossing the boundary.
Only relative regular files/directories are accepted; absolute/traversal paths,
duplicates, file/directory collisions, symlinks, hardlinks, devices, FIFOs,
sparse files, control characters, and privileged metadata are rejected. This
protects the host native helper's upstream `tar.extractall` calls. Upload and
download roots are only `/dgm` and `/testbed`. Limits are 32 MiB wire/repacked
size, 128 MiB expanded contents, 10,000 entries and 1,024 transfers per container.
API root paths are ASCII and at most 512 characters; archive members retain
their bounded native names. Downloaded members must match the daemon's requested
archive root, so a different relative target cannot be substituted.
Host state access uses held directory descriptors without symlink traversal.

On the reviewed Docker daemon, its archive endpoints reject writes when the
root filesystem is read-only and fail to observe files in the live tmpfs mount
view on reads. The proxy therefore uses fixed, internal exec commands: tar
imports already sanitized bytes into the allowed directory, while stat and tar
export the actual live files. The SDK stat header comes from actual container
stat output. Each command must finish with inspected exit code zero before a
successful response is sent. Caller-controlled interactive stdin remains
unavailable; only this internal archive transport accepts bounded input.

Archive commands have a 120-second deadline (30 seconds for stat), at most two
concurrent transfers, 32 MiB stdout for export, and 64 KiB stderr. Docker stream
frames are checked and demultiplexed; incomplete output, failed commands or a
lost client remove the owned container and record failure. Actual exported and
repacked hashes are journaled separately. No raw archive daemon success or file
existence is synthesized.

Docker exec uses actual hijacked multiplexed stdout/stderr, with a 4 MiB output
limit. A lost client, attempted stdin, exceeded output/deadline, cancellation or
expired admission causes deletion of the owned container. Every two seconds a
reaper checks admission and deadlines. Root-owned journal records are written
before Docker creation, so recovery can also find a container when transport
failed before its ID was received. Deletion requires actual labels/image to
match the root record. Failed cleanup retains the record for recovery; no
cleanup success is fabricated. Archive hashes and image/model/snapshot pins are
recorded without prompts or credentials.

DGM normally retrieves its evidence before native cleanup. Container files that
were not retrieved before a cancellation or crash are ephemeral tmpfs data and
are not claimed as published artifacts. The proxy does not invent missing
native results. The queue DB/snapshots currently share the worker UID trust
model, as in the existing worker: peer and snapshot checks do not turn a
compromised authorized host worker into a separately root-authenticated queue.

## Validation and deployment status

`tests/test_dgm_proxy.py` exercises SDK request shapes captured from the prepared
DGM environment with transport replaced, malicious archives, cross-run handles,
admission/hash/model mismatches, image pin mismatches, resource reconstruction,
recovery, a real Unix HTTP upgrade, quiet-client disconnect cleanup and the
fixed model relay. Fixtures run without Docker, root, framework imports or model
calls. The service/unit/network helper are operator deployment artifacts; their
existence does not mean a DGM pilot is admitted or proven by a native run.

Before deployment, actual built image IDs/digests, parent creation times, fixed
bridge ID and root approval are required. Then run offline image/bootstrap and
SDK conformance before separately authorizing any research/model execution.
The `gateway-polyglot-pilot` profile additionally binds its native request model
to the queue model, so the host outer loop and broker-created children cannot
receive different operator-selected models.
