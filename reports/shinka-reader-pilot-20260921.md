# Completed Shinka pilot reader diagnosis

All seven host Shinka pilots completed with exit 0. Four stored reader summaries
were `partial` because valid native `metadata` exceeded the 16,384-character
exported-field limit. Their scores, correctness, metrics and program rows were
already represented. This was a bounded reader mapping issue, not a failed run.

Pinned Shinka stores full `llm_result`, patch descriptions, timing and diagnostic
fields in the same metadata object as island-copy provenance. The reader exports
only `_is_island_copy`, `_spawned_island` and `_original_program_id`. Requiring the
entire unexported trace to fit the small exported-field limit unnecessarily lost
those provenance fields. Actual metadata reached 45,708 characters.

`src/arena/frameworks/shinka.py` now uses a separate 128 KiB metadata parse limit;
other field, row, SQLite length, database-size and inspection-time bounds remain
in place. Malformed/nonfinite or over-limit metadata still produces explicit
issues and `partial`. Model traces are not added to the exported result. Native
scores are not relabeled as canonical results, and the island-copy/evaluation
count caution remains.

The corrected reader was loaded from an isolated temporary module on the VM and
read all seven completed databases. No framework execution or model calls were
started. Original databases and stored historical summaries were not rewritten.
For every row, score, correctness, validity, public/private metrics, generation,
parent, timestamp and island index were unchanged. Database hashes matched before
and after each inspection.

| Model | Run | Stored status | Reinspection | Metadata max chars | Former issue rows |
| --- | --- | --- | --- | ---: | ---: |
| gpt-5.6-sol | `ddf85eb7dc18473d8833845b8d2c713f` | partial | recorded |45,708|3|
| gpt-5.6-terra | `69c10818abb94e9bb85d767d7f3671b0` | recorded | recorded |16,249|0|
| gpt-5.6-luna | `a4264708d691485da231d46c8d8517ac` | recorded | recorded |12,642|0|
| gpt-6-astra | `39c26d2ce2ee49b39db3d10d43b43b30` | partial | recorded |37,922|5|
| gpt-5.5 | `e476fc7d83994f4e8ce1b8af2a89aa50` | partial | recorded |23,552|4|
| gpt-reserve | `7800eec0e94141918d8e245a3f4cc7e8` | partial | recorded |29,768|2|
| codex-auto-review | `20005d5d2e934b0fa6d92dfd5805742d` | recorded | recorded |16,220|0|

Each reinspection returns 7 native program rows with zero mapping issues. Rows
include administrative island copies; they are not an evaluation count. The
separate canonical receipts remain the evaluation evidence.

Validation: 77 reader/evaluator tests passed. New regressions cover realistic
large model metadata, preservation of copy identity and score/validity, no trace
export, unchanged SQLite bytes, malformed JSON, nonfinite JSON and metadata above
the new bound. Historical summaries remain evidence of the original reader
version; the table records the subsequent read-only reinspection.
