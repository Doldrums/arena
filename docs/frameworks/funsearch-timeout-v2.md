# Original FunSearch transport timeout v2

Recipe `funsearch-original-timeout-v2` delegates the original-author FunSearch
implementation at `cc53f274237d7ab05c19df939edbc1f9616a7c19`. The native
constant-weight admissible-set specification remains `(9,5)`, with one sampler,
one evaluator, two islands and the existing credential-free namespace sandbox.
No search, candidate reconstruction, task scoring or admission logic changes.

The v2 client fixes its OpenAI SDK timeout at 330 seconds with `max_retries=0`.
The operator gateway is expected to enforce its separately configured
300-second request deadline; the driver neither configures nor measures that
service setting. SDK timeout is per operation, not a compute/token cap. Pure
runtime templates retain their 2,400-second process-group bound. Six model
continuations are allowed; the seed sandbox call is additional. Timed-out
requests are not silently retried or counted as returned generations.

The new wrapper records these settings in `results/provider-seam.json` before
calling the unchanged native integration. A native failure still propagates,
and the original native driver retains its bounded error/trace artifacts.
Both old recipe JSON identities are unchanged, and the old shared driver's
keyword timeout defaults to 180 seconds. The reimplementation path is untouched.

```text
python scripts/deployment/prepare_funsearch_timeout_v2.py \
  --destination /srv/arena/configs/funsearch-original-timeout-v2-20260921
```

This operator command creates seven templates and pure plans, using existing
`/srv/arena/sources/funsearch-original`, its prepared environment, and a hashed
bubblewrap executable. It never admits a run, calls a model or evaluates a task.
The prepared specs inherit only the named `OPENAI_API_KEY` environment reference;
no credential values enter plans or artifacts.

The preparation snapshot is at
`/srv/arena/build/funsearch-timeout-v2-review`; no live application or service
configuration was replaced. Plans record that reviewed snapshot's helper paths
and hashes. Admission must occur after the approved application snapshot is
installed and plans are regenerated/validated against that actual runtime.

The actual installed native environment was tested with the real OpenAI SDK
using an HTTP mock transport and a mock sandbox. The pinned native main,
sampler, parser and island database were delegated. Network connections and
child execution were blocked by an audit hook; fixture scores are synthetic,
not research results. Both old/default 180 and new 330 settings reached the
SDK transport, with six returned mock samples and seven mock sandbox calls
per variant. The proof is retained at
`/srv/arena/build/funsearch-timeout-v2-mock-proof-v2/proof.json`.

The motivating failure and uncertainty around its gateway audit correlation
are documented in [the native pilot findings](../../reports/native-pilot-findings-20260921.md).

Validation: 25 focused tests passed, including the optional exact-source check
with `ARENA_FUNSEARCH_ORIGINAL_SOURCE` set. The existing native-source test now
selects its original `single-threaded-native` profile explicitly, as required
since the separate gateway profile was added earlier.

Mock proof SHA-256:
`3472addd22b966fc2405db16ae41b84a8acb19d7761033fabd659fad9a7efc83`.
The real installed SDK version was 1.90.0. Twelve mock HTTP requests and fourteen
mock sandbox calls covered both variants; one attempted subprocess operation
was blocked by the audit hook. There were zero network attempts, actual provider
calls or candidate executions, and the original checkout remained clean.

Seven pure templates/plans were written to
`/srv/arena/configs/funsearch-original-timeout-v2-20260921`.
Its `preparation.json` SHA-256 is
`8bbb618a8375a22ebb3e762a13fae78672aa32ef44befd1bdbbad449666ea043`.
No template was added to the live control configuration or admitted to its queue.
