# Prepared FunSearch gateway pilots

Two distinct pinned implementations use their native search and evaluation
admission. The original-author engine uses its packaged constant-weight
admissible-set specification at `(n=9, w=5)`. The kitft re-implementation uses
its packaged cap-set specification at `n=6`. Their scores concern different
problems and are not interchangeable. Both use the exact selected gateway
model ID, one sampler/evaluator, two islands, and a 2,400-second outer timeout.

The operator generator is `scripts/deployment/prepare_funsearch_pilots.py`.
It verifies source revisions and input/executable hashes and creates fourteen
seven-model templates without making a model call. Native environments and
namespace conformance are separate prepared worker assets.

The original engine retains native `main`, `Sampler`, `Evaluator`, code
reconstruction, island selection and reset logic. Its published repository
requires a model and sandbox provider; the new profile supplies both. The
model receives the native unfinished program and returns an indented function
body. Six model samples are permitted, with one sample per prompt and no SDK
retry. Gateway usage is recorded alongside the existing native trace.

The kitft profile calls native `run_agents`, using native `LLMModel`, `LLM`,
`Sampler`, `Evaluator`, database workers and cleanup. Its native
`openai%<model>` provider prefix preserves the model identifier. SDK endpoint
routing uses `OPENAI_BASE_URL`; no model is renamed. Six generated samples
plus the native connectivity check give a maximum of seven native complete
calls. The native model retry setting is one and SDK retries are disabled.
The CLI's `runasync --iterations` argument is unused at this revision, so the
profile installs an explicit sample-budget observer instead. On the next
request after the budget, it cancels `run_agents`, whose native cleanup drains
the evaluator queue and joins its workers. No replacement response or candidate
is invented. One sample per prompt ensures that the final completed sample is
queued before shutdown. The native connectivity timeout is explicitly 180
seconds, matching the provider request deadline.

Both supplied Sandbox.run implementations execute the native reconstructed
program and unchanged scorer in an unprivileged Linux user/mount/PID/network
namespace. Only the native Python environment, its base runtime, system
libraries, the candidate and its input are mounted read-only. A per-call result
directory is writable. The environment contains no model credential; the host
configuration directory and provider socket are absent, and networking is
unshared. Bubblewrap's exact executable is hashed through
`request.executables.bubblewrap`. Each scorer has a deadline of at most 60
seconds (native calls request 30), 2 GiB virtual address space, bounded file
size and no core dumps. The admitted run's cgroup remains the outer resource
boundary. This replaces the repositories' intentionally omitted or weak
execution boundary; the search and numerical scoring functions stay native.

On the prepared worker, no-model conformance as UID 998 verified namespace
startup, absence of the gateway key/host configuration, inability to connect
to the host gateway, and termination of an infinite-loop fixture. The unchanged
original seed scored 125 at `(9,5)` in about 0.47 seconds; the kitft seed scored
64 at dimension 6. These are seed conformance observations, not generated
research outcomes or claims of optimality. The earlier `(6,3)` original smoke
scored 20, its support-count bound, so the pilot uses the larger `(9,5)` input.

Native scores remain noncanonical Arena observations. Kitft temperature,
top-p and maximum-token requests follow the gateway's `codex-native` policy
and are explicitly unenforced. The namespace tests establish the checked
filesystem/network/deadline behavior, not a universal adversarial-security
certification of the kernel or native scorer.
