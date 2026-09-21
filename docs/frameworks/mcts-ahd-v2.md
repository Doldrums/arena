# MCTS-AHD gateway pilot v2

This is a separate recipe, `mcts-ahd-gateway-v2`, associated with the existing
`mcts-ahd` participant. It uses the same upstream revision
`ee9c4f424503c65a5fd2b899e6620ce86079fedb`. The original recipe and cancelled
pilot remain unchanged; adding the variant does not invalidate the original
recipe hash recorded in historical run plans.

Two narrow integration changes are explicit:

- A reviewed configuration overlay changes the native BPP prompt signature to
  `priority_v{version}`. The pinned `Prompts` loader supplies version 2; the
  unmodified native evaluator imports `priority_v2`.
- An execution-only wrapper admits at most eight calls to the native
  `InterfaceEC._get_alg`, including at most three during initialization. It
  preserves native operators, response parsing, tree selection and scoring.
  Exhaustion escapes the native catch-and-retry loop, records
  `budget_exhausted`, and exits with code 75. It does not claim completion.

The native `max_fe=4` target is checked between complete tree rounds. With
initialization size 2, a healthy first round performs `e2` once, `m1` twice
and `m2` twice; `s1` skips the single-node ancestry. That is seven candidate
attempts including the two initial candidates. The separate total cap of
eight permits that complete round while bounding retries. Three initial
attempts leave five slots for the first round. Invalid or duplicate candidates
can exhaust either limit before a round finishes.

These counts are proposal attempts, **not provider requests or cost**. Native
parser retries, SDK retries and post-thought requests remain intact. The outer
2400-second timeout is still authoritative. Each template reserves four CPUs,
8192 MiB, one native evaluation slot and 512 processes. Numerical thread
environment variables are fixed to one. Generated Python executes within the
admitted worker cgroup; this profile uses native evaluation, not the canonical
Docker evaluation bridge.

`arena-provider-seam-v2.json` records the hooks and native target.
`arena-attempt-budget-v2.json` records each admitted operator and its phase.
Original native artifacts remain under `outputs/`. The exact API model is
preserved, credentials are an `OPENAI_API_KEY` environment reference, and the
gateway's unenforced temperature/token/sampling controls are recorded.

Preparation performs no native research:

```sh
python scripts/deployment/prepare_mcts_ahd_v2_pilots.py \
  --root /srv/arena \
  --destination /srv/arena/configs/mcts-ahd-v2-pilots-20260921
```

It creates seven new `cpu-mcts-ahd-v2-<model-slug>` templates and independent
configuration overlays for the seven exact gateway models. It neither writes
the live control configuration nor admits runs. The original CPU-four pilot
templates and files are preserved.

The explicit offline conformance command copies the pinned source, then uses
fixed responses and the actual native parser/evaluator:

```sh
/srv/arena/envs/mcts-ahd/bin/python scripts/deployment/check_mcts_ahd_v2_fixture.py \
  --source /srv/arena/sources/mcts-ahd \
  --destination /srv/arena/build/mcts-ahd-v2-conformance-fresh
```

On 2026-09-21 the fixed best-fit response with `priority` produced an infinite
native objective; changing the declared function name to `priority_v2` produced
the finite native objective `2.195017695282751`. The real native malformed-response
retry loop stopped at three attempts. A **separate synthetic control-flow
fixture**, using the real tree loop with fixed responses and synthetic
objectives, returned after two initialization attempts and five tree-operator
attempts. These fixtures made zero model calls and are not scientific search
results or cross-framework evaluations.

Final VM fixture evidence is at
`/srv/arena/build/mcts-ahd-v2-conformance-owner/full-offline-final-20260921/conformance.json`.
The cancelled original's accounting and archive are documented in
[`mcts-ahd-cancelled-20260921.md`](../../reports/mcts-ahd-cancelled-20260921.md).
