# SCiEL research profiles

SCiEL v0.2.0 is pinned to `a6c0d215b61ee52dae608a6390c9f2c6d2f2554d`.
`research.enabled` enables conclusions and reflections. Cells and executable
research tools additionally require `research_tools.enabled` and a working
native Docker executor. They are distinct capabilities.

## Audit of the September 22 campaign

The catalog campaign generator omitted `research_tools`; that release defaults
it to disabled. The existing results therefore measure candidate search with
conclusions/reflections under the recorded configuration. They do not establish
the effectiveness of the cell/tool mechanism or its causal contribution.

A read-only snapshot of 72 catalog runs using gpt-5.5 found 905 of 1,435 research
attempts delivered no lessons specifically because of card-size omissions.
It also recorded 1,164 conclusions and 377 reflections skipped by the auxiliary
call cap. Seventy-one configurations allowed four auxiliary calls; an earlier
pilot allowed one. These counts describe that snapshot, not every Arena run.

The snapshot contained 135 retained lessons. Full cards ranged from 13,533 to
34,350 characters; only five fit the native 16,000-character per-card limit.
The native compact renderer produced 3,772–5,522-character cards, all within
that limit. This is a projection of final retained lessons, not a replay of
historical prompts or evidence that a model used the memory. Compact cards
preserve references to full evidence while omitting some detail from prompts.

Audit input SHA256:
`faddc4c06ab2f76d268b050d6017aeff3be240294d0cc63bb5c742085a4b8f08`.
Private audit report SHA256:
`1433e51ac2bdd314db9b930f4d6f7115cafa1f1306ea9bbd17140ee15d84a04e`.

## Preparing a new profile

`prepare_sciel_catalog_campaign.py` defaults to foreground research and requires
`--research-tool-image-id sha256:<immutable-image-id>`. It explicitly sets:

- compact lesson memory, three retrieved lessons, source-bound conclusions;
- 80 auxiliary calls, one bounded conclusion-format repair, reflection interval 4;
- foreground research cells and tools, with background jobs disabled;
- the existing 16-evaluation, 32-iteration and three-confirmation task protocol.

The auxiliary cap is an operating allowance based on observed demand, not a
proof that future calls cannot exhaust it. Tool-planner calls have a separate
schedule. Report auxiliary skips, all model calls and tokens in pilot results.

An intentional ablation uses `--research-mode code-search-baseline`; it cannot
also specify a research-tool image. New profile identities and output paths
must remain separate from the earlier tools-disabled runs.

## Runtime admission

Configuration preparation is not runtime readiness. The engine requires an
explicit root-owned grant for each pilot's exact configuration bytes, exact
native source commit and immutable tool image. CLI overrides cannot change
the granted seed or evaluation budget.

The separate research socket admits only the pinned native supervisor:
one tool per run, four globally, 1 CPU, 512 MiB, 64 PIDs, bounded output and
30-second wall/20-second CPU limits. It snapshots the four read-only inputs,
disables network access, and binds execution to the authenticated engine's
parent cgroup. The supervisor drops tool execution to UID/GID 10001.

First verify the actual Docker CLI lifecycle with an inert tool. That check
does not count as a scientific experiment. Before bulk admission, a real model
pilot must show committed cell creation, model-authored tool registration,
successful execution with bound receipts, delivery of observations and compact
lessons in subsequent prompts, and an actual continuation. Any generated
candidate still needs independent canonical evaluation. Preserve failures and
unknown outcomes; do not replay an ambiguously dispatched model request.

## Interpreting effort

Elapsed time stops at a recorded run end or a same-run terminal runtime record.
If neither exists and the process is not verified live, show the last recorded
boundary rather than a growing archive age.

Keep provider-reported USD, historical token-rate estimates and amounts without
verified provenance separate. A subscription token does not establish a zero
per-run dollar cost. Without CPU/infrastructure receipts and a comparable
baseline protocol, total-cost savings are not established. HTTP status recorded
by the engine identifies an error on its model route; gateway versus upstream
attribution requires separate evidence.
