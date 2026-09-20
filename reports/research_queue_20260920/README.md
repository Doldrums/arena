# Research continuation and shared observations UI

Read-only fixture QA, 20 September 2026. No experiment, generated program, provider, evaluator, or HTTP deployment was executed.

Desktop 1360 px and mobile 390 px: concrete question, experiment and next decision remain visible; the queue shows recorded scheduler status separately from scientific state. Shared observations distinguish the recipient prompt excerpt from the original receipt and from model interpretation. Unpublished negative checks remain inspectable; delivery does not claim adoption, actual model use or causal benefit.

Both layouts have no horizontal overflow or browser JavaScript errors. Images `queue-1360.png` and `queue-390.png` are synthetic fixtures, not live scientific results. `verify_fixture.cjs` reproduces them with an existing local Chromium installation. `fixture-review.json` preserves DOM evidence.

Validation: Arena focused observer suite 65 passed + 29 subtests; native SCiEL corresponding suite 67 passed + 42 subtests. Research cells and tools DOM suite: 34 passed. New observer cases authenticate full and projected measurements, negative/unpublished records, bounded terminal interpretation, exact recipient prompt hashes, original receipt/revision identity, omissions, rollback and absent model receipts. Queue pending status is authenticated from active WAL metadata and disappears on rollback; published checkpoints do not claim scheduled leases or running CPU.
