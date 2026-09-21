# SCiEL native adapter

`SCiELAdapter` targets ordinary SCiEL at
[`0d67f813dd4ac21dee304f2b0de0b0ce59bf4157`](https://github.com/Doldrums/sciel/tree/0d67f813dd4ac21dee304f2b0de0b0ce59bf4157).
The command contract is read from that revision's `src/sciel/cli/main.py`;
the result format is from `engine/checkpoint.py`, `engine/db.py` and `run_log.py`.
This is a native launch adapter, not a universal adapter for the Arena task
catalog. The bounded canonical task bridge below is separate from the general
native result reader. Arena-controlled resume remains unavailable.

The inner `request` of an `arena.native-run/1` spec accepts:

| Field | Meaning |
| --- | --- |
| `python` | Required absolute existing executable, with SCiEL's dependencies installed. A virtualenv symlink is preserved. |
| `config` | Required absolute existing native SCiEL YAML configuration. Its contents are not copied into the returned plan or result. |
| `tasks_root` | Optional absolute existing directory of native SCiEL task packages; defaults to the pinned checkout's `tasks/`. |
| `seed` | Optional nonnegative integer forwarded as `--seed`. |
| `budget` | Optional positive integer forwarded as `--budget`: native `B_evals`, not a dollar or complete physical-evaluation budget. |
| `campaign`, `arm` | Optional short identifiers, containing letters, digits, `_`, `-` or `.`. |
| `action` | Only `run` is accepted; omission means `run`. |

Unknown request options and reuse of a nonempty native run directory are
rejected. Native SCiEL validates configuration semantics when the explicit
launch occurs; `prepare()` does not import it. The adapter preserves the full
native algorithm selected by that config, including configured G/C/R and tools.
It does not turn off those features to impersonate a generic optimizer.

The prepared command is:

```text
<python> -P -m sciel.cli.main run <config>
  --outputs <output_dir> --run-id native --tasks-root <tasks_root>
  [--seed N] [--budget N] [--campaign ID] [--arm ID]
```

The launcher supplies `PYTHONPATH=<source_dir>/src:<Arena package parent>` (using
the platform path separator) and uses the pinned source directory as cwd. The
native evaluator subprocess preserves this import path. The launcher owns source/commit verification, process isolation, explicit
credential injection, time limits and child-process termination. The interpreter
and its installed dependency environment still need independent verification.
SCiEL reads `llm.api_key_env` (default `OPENROUTER_API_KEY`). The adapter rejects a
checkout whose parent contains `.env`, because this SCiEL revision would load
that file implicitly. It neither reads nor stores credential values.

`input_paths` contains the resolved config and task root for the launcher's
content provenance. Always passing `--tasks-root` selects explicit local tasks
and disables native Hugging Face task-repository resolution. Native config can
still refer to `extends`, models, embeddings, warm-start state and research
artifacts outside those paths. Their dependencies must be resolved and captured
by the launcher before claiming complete provenance; the adapter does not parse
arbitrary YAML or claim that these two paths capture all runtime inputs.

Expected native outputs are `native/sciel_events.jsonl`,
`native/checkpoint.json` and `native/config.yaml`. The directory name `native`
is not the journal's native run UUID. `read_results()` reads only checkpoint and
journal data and never executes the stored source. It retains native UUID,
segment, task identity/hash, engine contract, counters and the best candidate's
source hash/JSON locator. Native `score` is maximizing **engine fitness**, not
necessarily the original task's raw metric; validity stays unknown. Native
`cost_total` is a recorded counter, not a verified total infrastructure cost.

`status=recorded` means the checkpoint's journal-prefix binding and final
`run_end` checkpoint hash/identity agree. It does not mean the process succeeded,
the candidate passed an independent evaluator, or the scientific objective was
achieved: the native stopping reason is retained separately. Missing files,
incomplete tails, changed files and mismatched identities produce missing/partial
evidence rather than a zero score. Symlinked artifacts are rejected. This reader
has bounds of 64 MiB per checkpoint, 1 GiB per journal and 16 MiB per journal line.

Contract tests use synthetic native artifacts, including a candidate that would
write a marker if executed. No SCiEL research loop, evaluator or paid API is run
by adapter preparation, result reading or these tests. Runtime conformance for
the selected interpreter, configuration and native task remains a separate step.

## Canonical SAT evaluation bridge

`arena.frameworks.sciel_evaluate.create_task(config, destination)` materializes a
native task package with a canonical evaluator bridge. The initial profile is
deliberately bound to `reference-sat` at task-source commit
`5729caa7a3bd4e66c39a447c0d4ee56dc8fa0935`. Its `sat_score` counts solved instances
and divides by their count: the raw score is a maximizing fraction in `[0, 1]`.
The adapter verifies the reviewed problem and seed hashes. Other task IDs,
revisions, minimizing objectives and scores outside this interval are rejected;
this avoids the pinned engine's negative-fitness refinement and grid-bin issues.

The bridge config adds `profile` and `receipts_dir` to the evaluator config:

```json
{
  "schema": "arena.evaluation-config/1",
  "tasks_dir": "/absolute/pinned/autoresearch-tasks",
  "task_id": "reference-sat",
  "timeout_seconds": 300,
  "execution": {
    "kind": "docker",
    "image": "your-image@sha256:<64-hex-digest>",
    "python": "python"
  },
  "profile": "sciel-unit-interval/1",
  "receipts_dir": "/absolute/run-artifacts/arena-evaluations"
}
```

Use a prepared immutable evaluator image with the pinned task's dependencies.
`local_trusted` with an absolute `python` executable is only for reviewed code;
it does not isolate generated candidates. Generation validates configuration and
source metadata without running either execution profile. Place the generated
package at `<native_tasks_root>/arena/reference-sat`, select
`task: arena/reference-sat` in the native config and pass that task root to the
native launch request. `create_task` returns a native config overlay containing
the actual task instructions and `confirm_records: false`; merge its
`llm.system_message` into the desired native LLM configuration.

The pinned SCiEL cascade always calls smoke then full; `tiers` cannot disable
that. Generated `smoke()` performs only an AST syntax check, without importing or
executing the candidate. `full()` invokes the canonical evaluator exactly once
and gives each call a fresh receipt directory and physical evaluation ID. A
second full call is a new measurement, not a cache hit. `stochastic: false` in
this bridge disables native automatic confirmation; it is not a claim that all
submitted candidates are deterministic.

Only a completed receipt with explicit `validity: true` and equal finite
raw/fitness values in `[0,1]` can enter the SCiEL archive. The native top-level
`score` receives fitness; `cases.raw_score` preserves the raw metric. Invalid,
unknown-validity, timeout and error receipts produce `ok: false`. A native zero
failure sentinel is never promoted into a canonical score. Every returned
evaluation includes its receipt ID, path and SHA256 in artifacts. The receipts
directory must be outside both source and generated-task trees, keeping growing
results out of task-input fingerprinting.

These measurements use ten fixed, generated 3-CNF instances (50 variables,
evaluator seed 0); this development-visible protocol is neither the paper's
benchmark nor a held-out scientific audit. The general native result reader
continues to report `canonical_evaluation: false`: linking every native program
and cost to these receipts requires separate run-level conformance. Creating a
task and passing synthetic contract tests does not establish runtime readiness.
