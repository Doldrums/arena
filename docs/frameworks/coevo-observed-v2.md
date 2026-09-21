# CoEvo observed pilot v2

This is a separate adapter identity, `coevo-observed-v2`, for the same CoEvo
participant and upstream commit `dcad65e9799961cf67cf29865ff41dda2902a808`.
It preserves the original optimizer, evaluator, retry behavior, registration,
selection, generation counter and native artifact writes. The original `coevo`
recipe stays unchanged, so its previously recorded recipe hashes remain valid.

## Confirmed native accounting behavior

`CoEvoMethod._register_chain` appends each chain solution to history, generation
history and sample count, then calls the inherited
`PopulationMethod._register_population_solution` for the representative. That
inherited method appends it again. A one-solution chain therefore contributes
two history rows for the same registered solution. Removing the duplicate from
native state could affect future use of history; this adapter does not do so.

`PopulationMethod._save_artifacts` labels a save with
`max(state.generation - 1, 0)`. Initialization leaves generation at zero and
the first evolution step increments it to one. Both saves consequently target
`history/gen_0.json`; native `RunStore.save_generation_history` opens the file
for replacement. The adapter preserves that native behavior and captures a
separate observation after each successful real save.

The historical pilot `cecf087e405246028b04e6e5d9a7cde3` supplied an initialization
snapshot with SHA-256
`4b8175ae80dd0c8cf76f847a60dd86b1255dbec41fac62742d687a6dcb66b8a0` (41,532 bytes).
It contains eight native history rows: four distinct full registered records,
each repeated twice, with chain IDs 0–3. Two distinct records are parse failures
and two are native-valid records. Its eight usage records include empty entries.
Neither count establishes physical model requests or task evaluations. This
snapshot is preserved separately; the active run and original native files
were not rewritten.

Native `_prompt_parse_evaluate` may retry the provider, then records only the
last usage object for that pipeline. Failed parsing avoids `task.evaluate`.
Continuation results may be evaluated but discarded before chain registration.
Accordingly, deduplicating history is not a way to reconstruct physical work.

## Observation contract

The versioned driver reuses the existing gateway/cache/TLS setup. Only after
that setup does it install a scoped wrapper around
`RunStore.save_generation_history`. The wrapper calls the actual method exactly
once with the same arguments, leaves its return value unchanged, and snapshots
the bytes it wrote. No pickle/checkpoint is loaded.

Before capture, hashes must match the pinned repository files and these actual
`evotoolkit==1.0.2` installed sources:

| File | SHA-256 |
| --- | --- |
| `core/method.py` | `04d0b0d7ca506c1eb3d479aa2e1d72d96001d7c2f3871b3b45707c5e546b08d6` |
| `core/store.py` | `1f1b6ce8c5148755f885a2402096fc0dc4cff899e2848288ea71f5a6220ca03b` |
| `core/solution.py` | `cd2134a5cf404b8094eeff81dd607245274af0d763f2955e0baaef377da7576f` |

Installed immutable source files may use uv's regular-file hardlinks; only reads
are performed. Mutable output snapshots use a stricter single-link, no-symlink
reader. Every snapshot has an exclusive, monotonic name:

```text
workspace/coevo-observed-v2/results/oscillation_1_coevo/arena-history/
  save_000000.native.json
  save_000000.receipt.json
  save_000001.native.json
  save_000001.receipt.json
```

Sequence IDs identify persistence events, **not corrected generation numbers**.
Both receipts can truthfully carry native generation 0. A receipt records the
source hashes, native relative path, exact snapshot hash/length and a limited
accounting projection. It exposes native history rows, distinct full registered
records, repeated rows, native usage records and nonempty usage records.
`task_evaluation_calls` and `physical_model_requests` remain null. Distinct
records include chain metadata and are not a unique-program count.

Native `-Infinity` invalid scores remain unchanged in the raw byte snapshots.
Receipt accounting contains no inferred finite score or canonical validity.
The public generic recipe reader continues to inventory opaque native artifacts.
`coevo_history.read_sidecars(output_dir)` provides the separately labelled,
hash-checked accounting projection with canonical run-relative artifact paths.
It rejects changed/malformed receipts, missing sequences, unpaired files and
symlinks; it never loads pickle or candidate code. These are native provenance
checks, not a root-authenticated evaluation certificate.

Bounds are 100 saves, 8 MiB per native snapshot and 128 MiB total. A capture
failure stops the observed profile with a visible error; it does not fabricate
missing evidence or resume with silently incomplete accounting. Existing
sidecars are never overwritten or reused for a fresh sequence.

## Preparation and validation

`scripts/deployment/prepare_coevo_observed_v2.py --root /srv/arena` prepares seven
model-specific templates and pure plans in the new directory
`/srv/arena/configs/program-pilots-20260921-coevo-observed-v2`. It preserves the
same native Oscillation-1 task, population 2, native max_gen 1, 4 CPU/8 GiB parent,
2400-second timeout and one evaluation slot. It verifies source/cache/dependency
evidence and does not alter control configuration, admit work or call a model.

Local inert tests cover duplicated exact rows, both real-shaped saves to
`gen_0.json`, unchanged original arguments/return/state, byte preservation,
source hashes, tamper/sequence/symlink failures and separate recipe identity.
An additional fixture ran the **actual installed RunStore as worker UID 998**
under an audit hook rejecting network/subprocess execution: two saves with
native labels `[0, 0]` preserved both snapshots and the original overwrite;
raw row counts `[4, 2]` projected to distinct-record counts `[2, 1]`.
No candidate, optimizer, evaluator or model was executed. This establishes
persistence compatibility; a v2 research run still needs separate admission.
