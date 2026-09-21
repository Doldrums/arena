# Private SCiEL image execution conformance

The operator-admitted pilot `5a72d1e3d80749fbbffb10f6174572b6` completed through
the private image broker on 2026-09-21. This verifies execution integration, not
scientific improvement or broad benchmark performance.

- Queue: completed, exit 0, resources released (`held=0`).
- Native SCiEL: 119 events, final event `run_end`.
- Canonical Docker evaluations: 7, all completed and valid, scores 0.8–1.0 on
  `reference-sat`. The seed already scored 1.0; no improvement is claimed.
- Every canonical receipt binds authorization `engine_broker` to actual engine
  container `7dea8d8a8f1386d3a51b931598e4560663ce35d45ef5382e83af345b98048b29`.
- All 139 published artifact hashes match the authoritative root journal.
- Worker receipt release/image/source pins match that journal.
- No run-labeled Docker containers remain; engine staging and registration were
  removed. Root journal confirms cleanup. Existing host-pilot proxy was never
  restarted for this deployment.

The root journal is
`/srv/arena/releases/engine-receipts/5a72d1e3d80749fbbffb10f6174572b6.json`, SHA-256
`8a55102cd307fb664159c2a9645e72bf1d80214ada0a4c6d5b9b22e9e874162e`.

Exact execution provenance:

| Identity | Value |
| --- | --- |
| Deployment manifest SHA-256 | `14e3316c6f98c09e95b156abe0a0643200c13048ddaaa746f1203dae63156e10` |
| Actual repository digest | `127.0.0.1:5000/empira/sciel@sha256:133c1f711acc5e498a86347e4bf763ad3ce2ee5d08d0cf873d9341e3e5e5fbcb` |
| Actual image ID | `sha256:9896de9283e1b25d0aebd58298f485946bfd099f201118570bd0428e673ca534` |
| SCiEL source commit | `0d67f813dd4ac21dee304f2b0de0b0ce59bf4157` |
| Canonical evaluator image | `sha256:a19df6207889b8b2e00faf732e8ac198210b1ebf81a57fdc75acbff244341968` |

The engine ran as 998:998 with a read-only root filesystem, private cgroup
namespace and exact admitted run cgroup. Initial engine deployment uses host
networking for the local provider gateway; canonical evaluators remain
network-disabled and access Docker solely through their restricted proxy.

Local validation: 117 tests passed across deployment manifests, private-image
adapter, broker and evaluator proxy. Fixtures cover real Unix client disconnect,
bounded partial evidence publication, interrupted-service recovery, provenance
checks, symlink rejection, stream bounds and root engine identity mapping. These
tests perform no model calls; the real pilot above is separate evidence.
