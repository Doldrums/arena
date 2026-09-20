# Scientific task overview

`taxonomy.json` is Arena's reviewed editorial classification, not a taxonomy or
scientific-importance ranking asserted by the source authors. `insights.json`
is its deterministic, endpoint-ready projection over `catalog.json`.

Each of the 1,138 task IDs receives exactly one primary **domain** and exactly
one **task type**. The domain follows the target or application; the type follows
the candidate operation. For example, fitting an E. coli growth equation is
biology + symbolic regression, while fitting an LLM scaling law is ML + symbolic
regression. GPQA and retrieval over a biology corpus remain ML capability and
retrieval benchmarks. CLRS BFS/Dijkstra packages evaluate discovered graph neural
networks according to their descriptions, so they are ML model-design tasks.

The denominator is **task packages**, including repeated benchmarks under
different paper prefixes and parameter variants. It is not unique scientific
problems or unique datasets. Both distributions include unsupported packages.
Each distribution totals 1,138 packages and 100.0%; percentages use largest
remainder rounding at 0.1 percentage point with ties in taxonomy-definition order.

There are 98 corpus paper IDs and 99 source groups: `sciel-supplement` is an
additional source group, not an academic paper. `corpus_paper_count` excludes it;
`source_group_count` includes it. The compatibility field `unique_paper_count`
also means source groups and must not be presented as 99 academic papers.
Per-domain/type `paper_count` excludes the supplement. A source paper or evaluator
family can occur in multiple groups; these coverage counts are not additive.

## Rules and evidence

Rules are ordered, first match wins. Conditions are AND; alternative values in
a condition are OR. Explicit named scientific targets and mixed-family exceptions
come first, then reviewed unsupported packages, then defaults for every one of
the 73 non-null source families, then an explicit unknown fallback. Exact task-ID
lists preserve reviewed scope instead of extrapolating to future unseen tasks.
Mixed or opaque suite names remain unclassified when their metadata does not
establish one primary domain. Known task types can coexist with unknown domains.

Every `task_annotations[task_id]` records the domain, task type, rule ID, rationale,
and the task's name, description, metric, family and source paper IDs. Catalog
provenance and `contract_source` provide the pinned source links. Supporting
paper-family labels for robotics were read from `papers/enpire.md`,
`papers/stride.md` and `papers/dreureka.md` at the same source commit
`995768fc462b8e327f90e6762846cc6ccb06cc2c`. ENPIRE is classified as robot policy
improvement; it is not incorrectly grouped with every reward-design task.

The `why_it_matters` prose describes what a target or evaluation measures. It
does not claim a discovery, experimental validation, clinical utility or relative
scientific importance. Synthetic physical equations remain synthetic benchmarks.

## Availability and evidence coverage

Domain/type rows preserve the source's 710 executable and 428 unsupported counts.
Executable means a declared evaluator package exists; no Arena runtime was
verified. Source protocol labels, including 122 `recreated_verified` packages,
are not Arena conformance certificates. `coverage` contains overlapping indicators
with the full package denominator; its percentages must not be summed.

## Offline maintenance

```sh
python scripts/build_insights.py
python scripts/build_insights.py --check
python -m pytest tests/test_insights.py -q
```

Neither command fetches sources, imports task code, installs environments nor
runs evaluations. The first writes only `insights.json`; `--check` never writes.
Regenerate after catalog or taxonomy edits, and review the two snapshots together
in the registry PR. SHA256 digests use UTF-8 JSON with sorted keys, compact
separators and no non-finite numbers. Validation recomputes every membership,
rationale and aggregate; missing/duplicate task membership, stale digests and
changed counts are rejected. Exact-ID rules referring to deleted tasks also fail.

`arena.insights.get_insights(registry_root=None)` loads and validates this data,
including the installed-wheel registry fallback. It raises `RegistryError` for
stale snapshots, allowing the API to report unavailable metadata instead of
silently presenting an old overview. The Cloudflare build consumes the same
committed static snapshot; CI runs the offline check before bundling.
