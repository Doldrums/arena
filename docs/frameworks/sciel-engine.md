# Private SCiEL engine image

The image packages SCiEL commit
`0d67f813dd4ac21dee304f2b0de0b0ce59bf4157`, its complete pinned source/models,
the reviewed Arena evaluation bridge and registry snapshot, CPU PyTorch,
Docker CLI 28.1.1 and Git 2.55.0. Its engine version is
`0.1.0+arena.0d67f813.worker1`; the upstream Python package retains its real `0.1.0`
version. The image has no model credential, provider token, host source overlay
or research result.

The fixed image entrypoint is:

```json
["/opt/venv/bin/python", "-m", "sciel.cli.main"]
```

It runs as UID/GID `998:998`, from `/opt/sciel`, with source imports rooted at
`/opt/sciel/src` and `/opt/arena/src`. Git's exact `/opt/sciel` trust entry allows
native journal provenance from this root-owned, immutable checkout. The copied
Git executable supplies the local/read-only commands used by the engine and
evaluator; optional external Git helper programs are not included. The copied
Docker executable is the same binary exercised against the canonical proxy.

## Build evidence

`scripts/deployment/build_sciel_engine.py` is an explicit operator command. It
does not submit a run or call a model. It verifies the clean SCiEL pin, exports
its source, copies only Arena source/registry/schemas, and records every Arena
file hash. The only retained Git metadata belongs to the pinned SCiEL object
database and index: host remote URLs, hooks and user configuration are excluded.

The builder downloads exact versions from the recorded native environment.
PyPI and the official PyTorch CPU index provide the wheels. Top-level wheel
metadata must match the inventory exactly; each wheel's SHA-256 then becomes
a `--require-hashes` lock entry. Docker installs these wheels offline, with
network disabled for build steps. The image base is an actual repository digest
in the loopback registry, rather than a mutable Python tag. The source snapshot,
wheel bytes, Dockerfile, tool binaries and build manifest remain available in
the build directory. Their hashes make the inputs auditable; filesystem/build
timestamps are not normalized, so this is not a claim of bit-identical rebuilds.

Example on the prepared worker:

```sh
/opt/arena/venv/bin/python scripts/deployment/build_sciel_engine.py \
  --base-image 127.0.0.1:5000/empira/canonical-base@sha256:da7798bf96eb4578791705fc3fa8b77fef6329aa2cba770be6ee40e040fda122 \
  --destination /srv/arena/build/sciel-engine-new-build --push
```

The destination must be new. Push targets are restricted to
`127.0.0.1:5000`. Build containers are limited to two CPUs and 8 GiB via the
Docker legacy builder. `build-receipt.json` records both local image ID and
the actual repository digest, architecture, user, entrypoint and input-manifest
hash. Register the repository digest; a tag alone is not a release identity. Before push, the builder validates the exact source, version and `io.arena.sciel.contract=sciel-cli-v1` labels, native entrypoint, UID and architecture against the release contract. The earlier unapproved `0.1.0+arena.0d67f813` binding lacked the contract label and remains immutable; `worker1` is the corrected image identity.

An explicit `--bridge-file /absolute/reviewed/evaluation.py` stages a reviewed
bridge only into the image snapshot. Its bytes appear in the Arena snapshot
hash, while the live host application remains untouched during active pilots.

## Broker mounts and canonical evaluation

The root broker mounts the selected configuration at `/arena-input/config.json`
and generated native task tree at `/arena-input/tasks`, both read-only. The
pinned task checkout is also read-only at
`/srv/arena/sources/autoresearch-tasks`. Only the admitted run's logical artifacts
directory and a bounded `/tmp` are writable. The root filesystem is read-only,
capabilities are dropped and the process receives no raw Docker socket.

The broker preserves the native algorithm while staging path substitutions:

- `embed_grid_path`: `/opt/sciel/models/code_embed_v3.pt`;
- `embed_axis_path`: `/opt/sciel/models/behavior_axis/{task}_v3.npz`;
- capacity files: that run's private artifacts directory.

It records the original/staged configuration hashes. Host networking preserves
the existing loopback gateway route. The process receives only the scoped engine
gateway key, never the upstream provider token.

The restricted socket remains `/run/arena-evaluator/docker.sock`. Inside the
engine's private cgroup namespace, `/proc/self/cgroup` reports `/`; host cgroup
membership therefore cannot be checked from that namespace. The broker mounts
`/run/arena-engine/context.json` as a root-owned, mode0444, single-link regular
file and sets `ARENA_EVALUATION_BROKER_CONTEXT` to exactly that path. Its shape:

```json
{
  "schema": "arena.engine-context/1",
  "run_id": "32-lowercase-hex-characters",
  "container_id": "64-lowercase-hex-characters",
  "cgroup_parent": "/arena-workers/arena-control-RUN_ID",
  "receipts_dir": "/srv/arena/control/runs/RUN_ID/artifacts/canonical-evaluations"
}
```

The bridge accepts this mode only for a non-root process, private cgroup root,
the fixed restricted proxy socket, root-owned non-writable parent directories
and an exact same-run identity/path binding. Alternate files, links, writable
metadata, duplicate JSON keys and malformed identities fail closed. The receipt
records `authorization: engine_broker` and the bound container ID. The canonical
proxy independently authenticates the actual host peer cgroup against the
broker-registered engine container and run; the JSON is not a standalone
authorization capability. Existing host-worker membership checks are unchanged.

Building or importing this image proves neither a successful native research
run nor improvement on a task. Record native model proposals and canonical
candidate receipts from the explicit admitted run separately.
