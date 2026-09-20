# Scientific overview on Tasks

The Tasks page combines a catalog with an overview of the research problems it covers. Charts link to the underlying task packages, and a task detail links back to the pinned source of its evaluation contract and recorded reference values.

## What the counts mean

A count is a **task package**. Parameter variants and paper-specific copies count separately; a package is not necessarily a unique scientific problem. The imported library has 1,138 packages and 73 named executable evaluator families. Its paper identifiers contain 98 corpus papers plus the SCiEL supplement; the supplement is not an additional academic paper.

Domain and task type are separate dimensions. A domain describes the application or scientific subject; a task type describes what a candidate program does. Each package has one primary assignment in each dimension so the percentages have a clear denominator. Taxonomy rules and their rationale are reviewed in Git under `registry/taxonomy.json`. This is Arena's editorial classification of source metadata, not an assertion that the source paper assigned these labels.

Domain descriptions explain the use of the tasks in research. They are not rankings of scientific importance, novelty, publication quality or expected impact. Unknown classifications remain visible.

## Reference evidence

The reference panel distinguishes a source's published reference or task target from the recorded result of a seed program. Numeric anchors retain their source, metric and interpretation. A successful seed smoke test is evidence that the source evaluator ran in that recorded environment; it is not an Arena run, full-paper reproduction or a current world-best result.

Reported scores with different task instances, objectives, transforms or evaluation budgets are not combined into a leaderboard or universal SOTA percentage. The absence of a reference remains missing data, never zero. The metadata does not certify current SOTA.

## Reproducibility

- `/api/catalog` is the pinned package catalog.
- `/api/insights` is the deterministic taxonomy and coverage snapshot, including per-task assignments.
- `/api/references` contains source-bound comparison evidence.
- Chart buttons and filters retain their selection in the URL. A failed overview request leaves the task catalog accessible.
- Python reads reviewed local snapshots; Cloudflare bundles the same JSON. CI checks the snapshots without fetching private repositories or executing task code.

Changing the catalog requires regenerating the associated summaries in the same PR. Build/check commands are documented alongside the snapshot modules and in the registry guide.
