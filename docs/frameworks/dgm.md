# DGM native runner

The adapter plans the unmodified `DGM_outer.py` CLI at
[`a565fd2d1dca504ef5104a7cc0f3bdc4ab9b4fd2`](https://github.com/jennyzzt/dgm/tree/a565fd2d1dca504ef5104a7cc0f3bdc4ab9b4fd2).
It runs DGM's whole coding-agent improvement loop with its native SWE-bench or
Polyglot evaluator. It does not run arbitrary Arena task packages, substitute an
Arena evaluator, or produce canonical Arena scores.

Planning validates paths and options without importing DGM, creating output
directories, installing dependencies, contacting providers, or launching Docker.
An explicit launcher execution is required to run the command. Tests use inert
fixtures and the pinned CLI's argument declarations; they do not reproduce a
paid DGM experiment.

## Prepared environment

Supply an **absolute path to a Python executable** in an environment prepared
according to the pinned repository's
[setup instructions](https://github.com/jennyzzt/dgm/blob/a565fd2d1dca504ef5104a7cc0f3bdc4ab9b4fd2/README.md#setup).
The adapter preserves a virtual environment's executable path, including a
symlink, and prefixes its directory to `PATH`: native evaluation also invokes
`python` as a subprocess. DGM needs Docker, its Python requirements and the
benchmark-specific dependencies. The adapter does not install them.

Provider credentials are inherited from the execution environment, never
serialized in the request. The pinned code reads `OPENAI_API_KEY`,
`ANTHROPIC_API_KEY` and, for its AWS provider branch, `AWS_REGION`,
`AWS_REGION_NAME`, `AWS_ACCESS_KEY_ID`, and `AWS_SECRET_ACCESS_KEY`.
Diagnosis and agent models are defined by upstream code; this adapter does not
offer a model override that the native CLI cannot honor.

DGM builds/reuses a Docker image named `dgm`. A pre-existing image may contain
different code; the adapter does not establish its provenance or rebuild it
automatically. Native execution can create containers, build images, download
datasets and packages, and make paid model calls. An outer process timeout does
not establish that Docker jobs have stopped or that all costs were recorded.

## Example specification

```json
{
  "schema": "arena.native-run/1",
  "framework": "dgm",
  "source_dir": "/research/sources/dgm",
  "output_dir": "/research/runs/dgm-swe-001",
  "timeout_seconds": 7200,
  "request": {
    "python": "/research/envs/dgm/bin/python",
    "benchmark": "swe-bench",
    "swe_bench_dir": "/research/dependencies/SWE-bench",
    "max_generation": 1,
    "selfimprove_size": 1,
    "selfimprove_workers": 1,
    "num_swe_evals": 1,
    "shallow_eval": true,
    "no_full_eval": true
  }
}
```

The source must be the clean, exact pinned checkout verified by the shared
launcher. SWE-bench setup requires a separate prepared checkout containing
`swebench/harness/run_evaluation.py`; the pinned DGM README specifies the
`dc4c087c2b9e4cefebf2e3d201d27e362d899e0f` SWE-bench revision. The adapter
checks the entrypoint exists and records the supplied dependency as an input;
it does not independently certify a dependency's results or installed version.

For Polyglot, set `benchmark` to `polyglot`, omit `swe_bench_dir`, and provide:

- `polyglot_metadata`: the prepared `polyglot_benchmark_metadata.json` file.
- `polyglot_benchmark_dir`: the prepared `polyglot-benchmark` directory, including
  each exercise's local `.git` repository and the commits referenced in metadata.

Use metadata from the native preparation process, with relative `repo` paths
of the form `polyglot/polyglot-benchmark/<language>/exercises/practice/<task>`.
Absolute or escaping paths are rejected. The adapter checks task identities,
commit syntax and the presence of exercise Git repositories. It does not
regenerate the dataset, alter metadata, validate every task's build tools, or
test that all referenced commits and benchmark dependencies are available.

Both dependency trees and Polyglot metadata are explicit `input_paths` for the
launcher's provenance manifest. They must meet the launcher's size/file-count
limits (currently 512 MiB and 10,000 files) and contain no symlinks. A dataset
above those limits needs a separately designed manifest workflow; this adapter
does not omit it from provenance to make a run fit.

## Options and bounds

| Request field | Accepted values / default |
| --- | --- |
| `python` | Required absolute executable path |
| `benchmark` | Required `swe-bench` or `polyglot` |
| `max_generation` | Required integer, 1–80 |
| `selfimprove_size` | Integer 1–8; default 1 |
| `selfimprove_workers` | Integer 1–8, no greater than size; default 1 |
| `num_swe_evals` | Integer 1–5; default 1, also used by Polyglot |
| `choose_selfimproves_method` | `random`, `score_prop`, or default `score_child_prop` |
| `update_archive` | `keep_all` (default) or `keep_better` |
| `eval_noise` | Finite number in 0–1; default 0.1 |
| `shallow_eval` | Boolean; default true |
| `no_full_eval` | Boolean; default true |
| `run_baseline` | Optional `no_selfimprove` or `no_darwin` |

The generation and worker limits bound native scheduling parameters, not tokens,
money, generated-code behavior, or external container lifetime. The default
shallow native subsets each contain ten tasks at this pin. The initial archive
contains previously recorded results from larger subsets, so its score must not
be treated as a matched fresh baseline for a new shallow run.

The pinned CLI accidentally concatenates `score_child_prop` and `best` in its
`choices` list. Its **default** `score_child_prop` still works when the flag is
omitted. The adapter omits the flag for that selection, accepts the other two
working explicit choices, and rejects `best` and the accidental concatenated
value. Resume, post-improvement diagnosis, arbitrary task selection, model
overrides, and generic extra CLI arguments are not exposed.

## Workspace and native outputs

The native outer loop has no output-directory argument: it writes
`./output_dgm/<timestamp>/`. Its SWE harness additionally walks up directories
until the working directory ends in `/dgm`. The shared launcher therefore
creates a fresh, independent **Git clone** at:

```text
<output_dir>/workspace/dgm/
```

The checkout must retain `.git`: native Docker code performs Git commits. An
archive without Git metadata is insufficient. The adapter returns
`workspace_copy: true` and the target `cwd`; execution stages prepared inputs
at these relative paths inside that clone:

| Input | Workspace destination |
| --- | --- |
| SWE-bench checkout | `swe_bench/SWE-bench` |
| Polyglot metadata | `polyglot/polyglot_benchmark_metadata.json` |
| Prepared Polyglot tree | `polyglot/polyglot-benchmark` |

Existing workspaces are rejected, and output paths cannot contain whitespace
because native commands split unquoted absolute paths. The original DGM
checkout is not a run directory. Arena metadata belongs in `<output_dir>/.arena/`.

Primary sources for these constraints are the pinned
[outer loop](https://github.com/jennyzzt/dgm/blob/a565fd2d1dca504ef5104a7cc0f3bdc4ab9b4fd2/DGM_outer.py),
[SWE harness](https://github.com/jennyzzt/dgm/blob/a565fd2d1dca504ef5104a7cc0f3bdc4ab9b4fd2/swe_bench/harness.py),
[self-improvement step](https://github.com/jennyzzt/dgm/blob/a565fd2d1dca504ef5104a7cc0f3bdc4ab9b4fd2/self_improve_step.py),
and [Polyglot preparation](https://github.com/jennyzzt/dgm/blob/a565fd2d1dca504ef5104a7cc0f3bdc4ab9b4fd2/polyglot/prepare_polyglot_dataset.py).

## Reading results

The result uses `arena.native-result/1`, `framework: dgm`, and
`canonical_evaluation: false`. The planned evaluator profile is
`dgm-native-swe-bench` or `dgm-native-polyglot`.

The reader inspects only timestamped run directories under
`workspace/dgm/output_dgm`, their `dgm_metadata.jsonl`, and referenced member
`metadata.json` files. Despite its suffix, the native generation journal consists
of consecutive **pretty-printed JSON objects**, not one JSON object per line.
Complete records before an unfinished tail are retained with `status: partial`.

Results retain each native `accuracy_score` and its recorded submitted/resolved
counts. `overall_performance_deep` is kept separate when present. Cached
`initial` metadata is explicitly marked `cached_initial: true`; no fresh score,
best-score comparison, zero for missing data, or canonical validity is inferred.
Every reported score has `validity: unknown`. `recorded` means that the native
receipts were read, not that DGM succeeded, that every attempt was evaluated, or
that improvement was independently verified.

JSON artifacts receive SHA-256 hashes. Symlinks, changing files, non-finite JSON
constants, duplicate keys, path-like member IDs, and unbounded files are rejected
or reported as partial evidence. Limits are eight runs, 80 generation records
per run, 1,024 distinct members per run, 8 MiB per journal, 4 MiB per member JSON,
and 64 MiB total read volume. Pickles, checkpoints, patches and saved programs are
never executed or deserialized as code.

A canonical Arena episode runner would need a separate integration: DGM's
outer loop currently selects its own native benchmark subsets, copies cached
initial metadata, and invokes its own harness. An arbitrary frozen Arena task
bundle cannot honestly be passed through an existing CLI flag at this revision.
