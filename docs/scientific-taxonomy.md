# Scientific taxonomy

The versioned rules in [registry/taxonomy.json](../registry/taxonomy.json) assign a primary scientific/application domain and a task type to each catalog package. These are distinct questions: a chemical kinetics task can have the type numerical solver, while a biology task can have the type symbolic regression or prediction.

The taxonomy is Arena's editorial reading of the pinned task names, family labels, paper IDs and source descriptions. Rules have stable IDs and an explicit rationale. Conditions within a rule are combined with AND; alternatives in a condition are combined with OR. The first matching rule wins. Task-specific rules precede general family rules. The final fallback assigns mixed/unclassified metadata instead of inventing a domain from an opaque benchmark name.

`task_annotations` exposes the matched rule and source catalog fields for each task. The current rules cover all 73 named evaluator families and classify unsupported packages where their metadata supplies enough context. Classification does not change executable status.

Each domain/type distribution is a partition of all 1,138 packages. Counts include copies and parameter variants, and count unsupported packages too. Percentages use the largest-remainder method at 0.1 percentage-point precision so each complete partition sums to 100.0%. A rounded percentage may differ by 0.1 point from independently rounding one count; counts are authoritative. Family and paper coverage within domains can overlap across domains and must not be summed as distinct totals.

There are 11 named domain groups plus a mixed/unclassified group, and 17 named task types plus an unclassified type. Source-group coverage has 99 IDs: 98 corpus papers and the SCiEL supplement. The supplement is excluded from the academic-paper count.

Change rules in a reviewed PR, regenerate with `python scripts/build_insights.py`, and verify with `python scripts/build_insights.py --check`. The check recomputes every assignment and aggregate and rejects catalog/taxonomy digest drift. It is offline and never executes task code.
