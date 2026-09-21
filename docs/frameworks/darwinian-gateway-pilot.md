# Darwinian Evolver circle-packing pilot

The separately versioned `darwinian-evolver-gateway` recipe uses Imbue's pinned
native source `7f12365d2059c47e29068a5a6f498a293148d2a9`. The original
`darwinian-evolver` recipe is unchanged, preserving its historical recipe hash.

The gateway driver invokes the native CLI with its circle-packing problem,
packaged seed, weighted population, mutation parser and geometric evaluator.
Only the native Anthropic SDK constructor and model constant are rebound to the
private loopback gateway and the exact selected model. The gateway translates
the native nonstreaming Messages request; this does not imply that a GPT model
is Claude or that the original paper's model configuration was reproduced.

The pilot uses four iterations, one parent per iteration, one mutator and one
evaluator worker, and the native ancestor learning-log option. The seed is
evaluated separately. Failed or unparseable mutations can produce no offspring,
so requested iterations do not establish a count of valid generated programs.
The native 26-circle task and score are retained; there is no canonical Arena
receipt or controlled cross-framework comparison.

Each run reserves 4 CPUs, 8 GiB RAM, one evaluation slot and 512 PIDs, with a
2,400-second outer cgroup deadline. Numeric libraries use one thread. The
native function timeout remains unchanged; generated code executes under the
existing trusted-worker policy, not a new hostile-code sandbox. The SDK timeout
is 180 seconds with zero automatic retries. The gateway records but does not
enforce the native `max_tokens` parameter, so it is not a compute cap.

The original CLI writes JSONL populations and pickle snapshots. Arena treats
the pickle files as opaque artifacts and never deserializes them. This profile
does not expose native snapshot resume or S3 upload. Model credentials exist
only in the private environment and in the in-memory SDK client.

`prepare_darwinian_pilots.py` creates seven plans/templates without admitting a
run. `check_darwinian_gateway.py` checks the actual native SDK for all seven
model IDs using an in-memory HTTP transport and a network-denying audit hook.
It also checks native CLI/problem construction and two fixed geometric
validation fixtures. It never calls a provider, executes generated candidates
or runs the optimizer. Dependency freezing, live admission and real pilot
completion are separate deployment stages.
