# ShinkaEvolve native adapter

The adapter plans a native Shinka run and reads its saved program database. It
does not import Shinka, execute a candidate while planning, or turn native
scores into canonical Arena evaluations. Actual launches belong to Arena's
explicit native-run command and require a prepared Python environment.

The supported source revision is
`9912af12d423504b8d580f4179fd15f5f88b8c50` of
[SakanaAI/ShinkaEvolve](https://github.com/SakanaAI/ShinkaEvolve/tree/9912af12d423504b8d580f4179fd15f5f88b8c50).
The shared runner verifies this revision and a clean source checkout before
launching. No live model calls or native search run were used to validate this
adapter; its tests use inert task files and SQLite fixtures.

## Request

The `request` object inside `arena.native-run/1` is:

```json
{
  "python": "/absolute/path/to/shinka-venv/bin/python",
  "task_dir": "/absolute/path/to/task",
  "num_generations": 12,
  "native_config": {
    "llm_models": ["your-provider/model"],
    "embedding_model": null,
    "max_api_costs": 0.5,
    "evaluation_timeout": "00:02:00",
    "max_evaluation_jobs": 1,
    "max_proposal_jobs": 2,
    "max_db_workers": 1,
    "llm_kwargs": {"temperatures": [0.2], "max_tokens": 1000},
    "num_islands": 2,
    "archive_size": 10
  }
}
```

`python` must be an absolute existing executable. Its symlink path is preserved
so a virtual environment retains its identity. `task_dir` must be an absolute
existing directory with `evaluate.py` and exactly one supported `initial.<ext>`
file. The pin supports Python, Julia, Go, Verilog, Rust, Swift, C++, CUDA, JSON
and Fortran extensions; their task runtimes still need to be installed.

`num_generations` must be an integer from 1 through 100,000. The required native
configuration explicitly chooses models, embeddings (a model ID or `null`), a
positive finite API budget, evaluator timeout and all three concurrency limits.
Concurrency is bounded to 1–64, and evaluator timeout to one second–24 hours.
`llm_kwargs`, `num_islands` and `archive_size` are optional. Supported LLM kwargs
are `temperatures`, `max_tokens`, `top_p` and `reasoning_effort`. Unknown options
are rejected, including output-path and evaluator-path overrides.

Provider credentials belong in the launching process environment. They must not
appear in the request or model URLs. The adapter neither reads nor serializes
credential environment values. Configure the provider credentials required by
the chosen Shinka models in the native environment before an authorized run,
and list only their variable names in the outer spec's `environment_names`.
Preparation rejects a `.env` file, directory or symlink in the source checkout
without reading its contents. At this pin, Shinka's dotenv loader otherwise
loads the package-root and working-directory `.env` with `override=True`;
both locations are the checkout used by this adapter.
The Python environment must contain Shinka's dependencies and all evaluator
dependencies; planning does not install or probe them.

## Native launch contract

The adapter emits a literal argument vector beginning with:

```text
/absolute/python -m shinka.cli.run
  --task-dir /absolute/task
  --results_dir /absolute/output
  --num_generations 12
```

It adds Shinka's three concurrency flags and namespaced `--set` overrides for
the explicit model, budget, evaluator timeout and optional settings. The
working directory points to the verified Shinka checkout. `PYTHONPATH` contains
that checkout first, followed by Arena's `src` directory, so a generated evaluator can import
the bridge with the selected native Python interpreter. There
is no shell interpolation, generated launcher, YAML loading, or framework
import during planning. The task's two entry files are returned in
`input_paths` for the shared runner's provenance capture, together with
`evaluation.json` when present. Task-local imported
dependencies are not comprehensively hashed by this adapter.

The environment override `SHINKA_PRICING_MODE=offline` uses the native cached or
packaged pricing metadata. Shinka writes its own `pricing_snapshot.json`.
`max_api_costs` has the native framework's semantics; it is not proof that every
external service, embedding, infrastructure charge or in-flight request is
included. The shared runner's wall-clock timeout is a separate outer limit.

This launch interface is established by the pinned `shinka/cli/run.py:main`
module and `[project.scripts]` in `pyproject.toml`; it runs the whole native
search loop, not the task's evaluator alone.

## Native result inspection

The pin writes `programs.sqlite`, as specified in
`shinka/core/async_runner.py:_setup_async`. Some upstream WebUI examples still
name `evolution_db.sqlite`; this adapter uses the actual pinned source path.
`evolution_run.log` and `pricing_snapshot.json` are expected native artifacts.
`prompts.sqlite` is optional when prompt evolution is enabled.

`read_results` returns `arena.native-result/1` with
`canonical_evaluation: false`, an artifact SHA256 and bounded native records.
It preserves program IDs, parent and inspiration IDs, generation, timestamp,
island, raw `combined_score`, raw `correct`, public/private metric dictionaries
and administrative copy identity. Shinka's `combined_score` is maximized. A
null correctness value stays unknown; it is never converted to false or true.
No best-candidate claim or evaluation count is derived from this bounded view.

Metadata keys `_is_island_copy`, `_spawned_island` and
`_original_program_id` distinguish administrative island copies. These remain
separate program rows and are not presented as independent evaluations. Full
program code, embeddings, freeform model traces and other metadata are omitted.
Native metric names and units remain unchanged.

The reader opens an ordinary SQLite `programs` table with `mode=ro`,
`immutable=1`, `query_only` and untrusted-schema protections. It does not run
database migrations or create SQLite sidecar files. A nonempty WAL produces
`partial` results with no program records: close the native writer and let it
checkpoint before inspecting. The reader itself never checkpoints or mutates
the source. Database changes during inspection also withhold the records.

Inspection is bounded to a 256 MiB artifact, 500 newest records and 16,384
characters per JSON field, with a SQLite query deadline. Truncation, malformed
JSON, non-finite numbers, invalid native booleans, missing schema and corruption
are explicit in `status`, `warnings` or per-record `issues`. A missing database
returns `missing`, not a successful empty run. The original SQLite hash remains
the evidence for fields omitted from this view.

## Canonical Arena task bridge

Create a native Shinka task explicitly from an Arena evaluation configuration:

```text
python -m arena.frameworks create-task shinka /absolute/evaluation-config.json \
  --output /absolute/new-shinka-task
```

The configuration uses `schema: "arena.evaluation-config/1"` with an absolute
`tasks_dir`, an executable catalog `task_id`, integer `timeout_seconds`, and
an `execution` object. Choose `{"kind":"docker","image":"repo@sha256:…",
"python":"python"}` with a real immutable image digest for generated code,
or `{"kind":"local_trusted","python":"/absolute/python"}` for reviewed
trusted fixtures. These execution profiles are provided by Arena's shared
canonical evaluator. Configure dependencies in the selected environment first;
task creation neither installs them nor starts an evaluation.

Creation verifies the pinned task source and catalog contract, copies its
actual `initial_program.py` bytes into `initial.py`, and writes `evaluate.py`
and `evaluation.json`. The destination must be new and outside the source tree.
Optional `receipts_dir` selects an absolute external receipt directory and must
not overlap the generated task inputs. Point the native request's `task_dir`
at the resulting directory. The creation response reports
`evaluation_performed: false`; source preparation is not runtime conformance.

Shinka invokes the generated evaluator with `--program_path` and `--results_dir`.
Each invocation asks Arena for one canonical evaluation and a fresh receipt
directory. By default receipts are under `results_dir/arena-evaluation`; an
explicit `receipts_dir` keeps them elsewhere. The bridge checks task identity,
direction, the saved receipt and its location before publishing native metrics.
It includes the canonical receipt path, ID and SHA256 in private metrics.

Only a completed evaluation with `validity: true` and finite, consistently
normalized fitness yields `correct: true`. The native `combined_score` is the
canonical fitness: raw scores are unchanged for maximization and negated once
for minimization. Zero and negative valid fitness remain valid. Unknown,
invalid, interrupted, failed or nonfinite evaluations yield `correct: false`
and `combined_score: null`, preserving an absent fitness instead of inventing a
zero score. The pinned native top-program query excludes null scores. Native
bookkeeping and selection policies still belong to Shinka; the SQLite reader
does not promote its records to independent canonical evaluations.

The bridge publishes rejected result files before evaluation and writes
successful correctness last, so interruption cannot reuse a previous result.
Set Shinka's `evaluation_timeout` above the canonical timeout with enough margin
for startup and receipt publication, and set the outer run timeout for the
whole search. A timeout can still prevent a complete canonical receipt.

## Remaining boundaries

- Native task compatibility requires Shinka's `evaluate.py` contract:
  `metrics.json` with `combined_score`, and `correct.json` with `correct` and
  `error`. Generated tasks use the bridge above; arbitrary native tasks do not
  establish canonical evaluation merely by following that file format.
- This adapter does not implement pause/resume controls, deployment,
  credentials provisioning, environment installation or a live dashboard.
- The evaluator and candidate execute only in an explicitly launched native
  run. The framework's ordinary local job execution is not an Arena sandbox.

Validation: `python -m pytest tests/frameworks/test_shinka.py tests/frameworks/test_shinka_evaluate.py -q`.
