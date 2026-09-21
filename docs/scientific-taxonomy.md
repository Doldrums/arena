# Scientific taxonomy

The versioned rules in [registry/taxonomy.json](../registry/taxonomy.json) assign a primary scientific/application domain and a task type to each catalog package. These are distinct questions: a chemical kinetics task can have the type numerical solver, while a biology task can have the type symbolic regression or prediction.

The taxonomy is Arena's editorial reading of pinned task names, family labels, source descriptions and candidate interfaces. Rules have stable IDs and an explicit rationale. Conditions within a rule are combined with AND; alternatives in a condition are combined with OR. The first matching rule wins. Task-specific rules precede general family rules. The final fallback assigns mixed/unclassified metadata instead of inventing a domain from an opaque benchmark name.

`task_annotations` exposes the matched rule and source catalog fields for each task. The current rules cover all 151 named evaluator families and classify unsupported packages where their metadata supplies enough context. Classification does not change executable status. Historical rule IDs containing `unsupported` do not determine current availability.

The source snapshot is autoresearch-tasks commit `5729caa7a3bd4e66c39a447c0d4ee56dc8fa0935`. Its `catalog/duplicates.json` maps 254 former package aliases to canonical IDs. Explicit task-ID rules follow those mappings, preserving the previous domain/type assignments. Together with 75 additions, this changes the denominator from 1,138 to 959 canonical packages. It does not establish 959 unique scientific problems: remaining parameter variants still count separately.

Each domain/type distribution is a partition of all 959 packages, including 689 declared executable packages and 270 unsupported packages. Percentages use the largest-remainder method at 0.1 percentage-point precision so each complete partition sums to 100.0%. A rounded percentage may differ by 0.1 point from independently rounding one count; counts are authoritative. Family and paper coverage within domains can overlap across domains and must not be summed as distinct totals.

There are 11 named domain groups plus a mixed/unclassified group, and 17 named task types plus an unclassified type. Source-group coverage has 113 IDs: 98 corpus papers and 15 supplemental collections. The latter comprise the SCiEL supplement, Santa 2025, and 13 science collections; all are excluded from academic-paper counts through the explicit `non_paper_source_ids` list.

The 75 additions are assigned to mathematics (12), biology/health (11), chemistry/materials (14), earth/environment (14), physics (19), and finance/economics (5). Source `area`, family labels and candidate interfaces support these assignments. Cosmology, particle physics and quantum-information applications belong to physics; a learned model used to solve a scientific task does not automatically make its primary domain ML. The taxonomy does not endorse upstream scientific-importance labels or claims that a problem remains open.

Availability and protocol evidence remain separate from scientific classification. Fifteen new packages declare `requires_setup`; their evaluators exist in the source but their environments have not been verified here. Source `recreated_verified` status is recorded evidence, not an Arena runtime or conformance certificate.

Change rules in a reviewed PR, regenerate with `python scripts/build_insights.py`, and verify with `python scripts/build_insights.py --check`. The check recomputes every assignment and aggregate and rejects catalog/taxonomy digest drift. It is offline and never executes task code. See [registry/INSIGHTS.md](../registry/INSIGHTS.md) for counting and maintenance details.
