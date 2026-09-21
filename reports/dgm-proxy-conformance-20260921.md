# DGM Docker capability: offline conformance, 2026-09-21

The separately deployed DGM proxy passed real Docker SDK conformance with the
three approved runnable images. This establishes container/API integration;
it is not a DGM research result. No model calls, benchmark evaluations or
optimizer runs were made, and no production queue rows were created.

## Immutable image approval

Root approval: `/etc/arena/dgm-image-approval.json`. Its source manifest is
`/srv/arena/build/dgm-image-receipts-20260921/built-images.json`, SHA-256
`6ffb36f68aa402a3ff27df68fe9d83fa0ee515f75a37d87a5650cbfb3982a7a4`.
The DGM source pin is `a565fd2d1dca504ef5104a7cc0f3bdc4ab9b4fd2`.

| Runnable alias | Actual repository digest | Actual local image ID |
| --- | --- | --- |
| `dgm:latest` | `127.0.0.1:5000/arena-dgm@sha256:a274eaba78cb253005cbb0252822974b420e3c3db54e2ec8d87a15e390c834c8` | `sha256:8496064efb8e2bf6a17fe44a9af1c20d8bc07b15f909d79a4ee7d32f27481085` |
| `pb.eval.x86_64.python__dominoes:latest` | `127.0.0.1:5000/arena-dgm@sha256:0496624210d11a7c0683902d0fe7c187febb230520cb588449046611a868a9ea` | `sha256:0fb75b03f31dc6e03e5387c04c999aa91f5142a2fec9a0761449c54b570ac804` |
| `pb.eval.x86_64.python__beer-song:latest` | `127.0.0.1:5000/arena-dgm@sha256:32c9f2a26d17e5f1c89eb36176f24a1f7cdc7fad9f562e8b6bcf8472aac9ef7a` | `sha256:656e64f1380d42960df01fbed75e3d7be936b9f1757de62422cee1cd4555b8b8` |

The separately approved base and environment images are available for genuine
native lookup and parent freshness checks, but cannot be run through the proxy.
Native SDK image inspection exposes only approved aliases/digests; unrelated
build tags are excluded.

## Real SDK fixture

Proof: `/srv/arena/build/dgm-sdk-conformance-acca6f87c7b749eca00eab8ed0eb20e3/proof.json`.
SHA-256: `3ce4bcce6321eb7f753e30542479f16bb4bbb1eca8f554478617b5d1eaf56546`.
The fixture used its own SQLite database, snapshots, root journals and
`/arena-dgm-conformance` cgroup hierarchy. Its process actually ran as worker
UID 998 in the admitted `main` cgroup; authorization was not monkeypatched.
The executable fixture is retained at `/srv/arena/build/check_dgm_sdk.py`.

Confirmed with the real native Docker SDK and daemon:

- All five approved aliases resolve to their exact image IDs; the base image
  cannot be started through the capability.
- All three runnable images create, start, finish bootstrap and execute real
  commands. Both stdout and an intentional exit code 7 are preserved.
- Nine successful archive transfers cover upload, file download and directory
  download in the live `/dgm` tmpfs. A tenth attempted transfer rejects a
  symlink and removes its owned container.
- Actual daemon inspection of all five fixture containers confirms read-only
  root, all capabilities dropped, no-new-privileges, private cgroup namespace,
  no host bind/device access, the dedicated internal network, 4 CPUs, 8 GiB
  memory/no extra swap and 512 PIDs per child. The shared parent is bounded by
  4 CPUs, 16 GiB memory and 1,024 PIDs.
- Host port 22 and external Internet connections fail. The fixed relay denies
  a non-API route. No permitted model route was called.
- Cancellation in the isolated fixture database triggers cleanup. All five
  containers were confirmed absent afterward; all five root journals retain
  `removed` state.

Docker's raw archive endpoints cannot perform these live tmpfs transfers with
read-only root: PUT rejects the read-only filesystem, and GET misses its live
mount view. The proxy uses private fixed exec-tar import/export and real stat,
validates/repackages both directions, and requires inspected exit code zero.
It exposes no general stdin capability and does not synthesize file existence.

## Final deployed service and checks

`arena-dgm-proxy.service` is active. Socket
`unix:///run/arena-dgm/docker.sock` is root:998, mode 0660. An actual unadmitted
root request to `/version` returns HTTP 403. The worker was not added to the
Docker group. Other evaluator/engine/worker services were not restarted.

Deployed module SHA-256:
`d016a1b47f0d6e8231de552c678c2ca03d010fa4833b0d3f1debbc98fd8d312b`.
Production configuration SHA-256:
`b7c8ea85ec3c0a904afb346e80f15953670205d713406b62933f6e99a0c12549`.
The real SDK proof used module SHA-256
`40a588e914b8b49cf92d82d0ce9edd290d0e5e258e0befc46c095aada9d2b4f2`.
The final subsequent change moves transfer-budget reservation under its lock,
checks the record is still live, and documents existing journal semantics.
A deterministic concurrent regression verifies exactly one admission when two
archive requests compete for the final transfer slot. Failure regressions
verify that persisting failed transfer evidence after deletion does not restore
container/exec capabilities or change the journal's removed state.

Final local validation: **146 passed**:

```text
.venv/bin/python -m pytest -q tests/test_dgm_proxy.py tests/test_evaluator_proxy.py tests/test_engine_broker.py
```

Coverage includes real Unix socket streams, fragmented/truncated Docker frames,
actual exit requirements, bounded output/deadlines, quiet client disconnect,
malicious tar members, resource reconstruction, cross-run denial and recovery.
The pilot profile also requires its native request model to equal the queue
model used inside its child containers. Research admission remains a separate
operator action; this report claims neither benchmark correctness nor an
improvement in DGM performance.
