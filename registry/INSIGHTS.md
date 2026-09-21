# Scientific task overview

`taxonomy.json` is Arena's reviewed editorial classification, not a taxonomy or
scientific-importance ranking asserted by the source authors. `insights.json`
is its deterministic, endpoint-ready projection over `catalog.json`.

Each of the 959 task IDs receives exactly one primary **domain** and exactly
one **task type**. The domain follows the target or application; the type follows
the candidate operation. For example, fitting an E. coli growth equation is
biology + symbolic regression, while fitting an LLM scaling law is ML + symbolic
regression. GPQA and retrieval over a biology corpus remain ML capability and
retrieval benchmarks. CLRS BFS/Dijkstra packages evaluate discovered graph neural
networks according to their descriptions, so they are ML model-design tasks.

The denominator is **canonical task packages**, not unique scientific problems
or datasets. The source update adds 75 packages and merges 254 aliases from the
previous 1,138 entries: 1,138 + 75 − 254 = 959. Remaining parameter variants count
separately. Both distributions include unsupported packages. Each distribution
totals 959 packages and 100.0%; percentages use largest-remainder rounding at
0.1 percentage point with ties in taxonomy-definition order.

There are 98 corpus paper IDs and 113 source groups. The 15 supplemental groups
are `sciel-supplement`, `kaggle-santa-2025`, and 13 `science-*` collections, listed
explicitly in `non_paper_source_ids`. They are not academic papers.
`corpus_paper_count` and per-domain/type `paper_count` exclude them;
`source_group_count` includes them. The compatibility field `unique_paper_count`
also means source groups and must not be presented as 113 academic papers.
A source paper or evaluator family can occur in multiple groups; these coverage
counts are not additive.

## Rules and evidence

Rules are ordered, first match wins. Conditions are AND; alternative values in
a condition are OR. Explicit named scientific targets and mixed-family exceptions
come first, then reviewed task-specific packages, then defaults for every one of
the 151 non-null source families, then an explicit unknown fallback. Exact task-ID
lists preserve reviewed scope instead of extrapolating to future unseen tasks.
Mixed or opaque suite names remain unclassified when their metadata does not
establish one primary domain. Known task types can coexist with unknown domains.

This snapshot follows autoresearch-tasks commit
`5729caa7a3bd4e66c39a447c0d4ee56dc8fa0935`. Explicit task-ID rules were migrated
through `catalog/duplicates.json`; all previous domain/type assignments were
preserved under their canonical IDs. Historical rule IDs containing `unsupported`
are stable identifiers, not availability assertions. Current availability always
comes from the catalog.

The science expansion was classified using its source family and `area` labels,
catalog descriptions, and candidate interfaces. It adds 12 mathematics packages,
11 biology/health, 14 chemistry/materials, 14 earth/environment, 19 physics, and
5 finance/economics. Source area labels such as cosmology, particle physics and
quantum information are grouped under physics. Using a learned model does not
by itself move a scientific application into the ML domain. Candidate operations
still distinguish, for example, RNA search from microscopy denoising, parameter
inference from dynamical simulation, and policy design from equation discovery.
Source importance labels or open-problem descriptions are not verified claims
of this overview.

Every `task_annotations[task_id]` records the domain, task type, rule ID, rationale,
and the task's name, description, metric, family and source paper IDs. Catalog
provenance and `contract_source` provide the pinned source links. Supporting
paper-family labels for robotics were read from `papers/enpire.md`,
`papers/stride.md` and `papers/dreureka.md`. ENPIRE is classified as robot policy
improvement, distinct from reward design.

The `why_it_matters` prose describes what a target or evaluation measures. It
does not claim a discovery, experimental validation, clinical utility or relative
scientific importance. Synthetic physical equations remain synthetic benchmarks.

## Availability and evidence coverage

Domain/type rows preserve the source's 689 executable and 270 unsupported counts.
Executable means a declared evaluator package exists; no Arena runtime was
verified. In particular, the 15 new executable packages marked `requires_setup`
retain that source status; their environments were not installed or checked.
Source protocol labels comprise 130 `original`, 81 `recreated_verified`, and
478 `recreated` executable packages. These labels are not Arena conformance
certificates. `coverage` contains overlapping indicators with the full package
denominator; its percentages must not be summed.

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
