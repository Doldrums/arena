# Original-author FunSearch

The `funsearch-original` recipe runs the single-threaded implementation released
by Google DeepMind for Romera-Paredes et al.,
[Mathematical discoveries from program search with large language models](https://www.nature.com/articles/s41586-023-06924-6)
(Nature, 2023). Source is pinned to
[`cc53f274237d7ab05c19df939edbc1f9616a7c19`](https://github.com/google-deepmind/funsearch/tree/cc53f274237d7ab05c19df939edbc1f9616a7c19).
This is a separate implementation from the corpus entry
`funsearch-re-implementation`, which refers to Ellenberg et al. (2025) and
`kitft/funsearch`. No participant identity is borrowed from that paper.

The released source contains the evolutionary algorithm, program manipulation,
evaluator and pipeline. Its `sampler.LLM` and `evaluator.Sandbox` deliberately
raise `NotImplementedError`. A researcher supplies those two interfaces through
a staged factory. An explicit run then calls the original `funsearch.main`;
Arena does not substitute its own search algorithm or objective.

## Prepared environment and inputs

Prepare an isolated interpreter containing the source imports `absl-py`, `numpy`
and `scipy`, plus the dependencies of your providers. Arena does not install
these packages or initialize providers while planning. All executable factory
code and associated datasets should be staged with the native request's
`inputs` mapping so the runtime hashes their provenance.

A factory has the following contract. The provider imports below are examples
of your own staged integration modules, not included Arena packages:

```python
# inputs/provider.py
def build():
    from inputs.my_model import draw_continuation
    from inputs.my_sandbox import IsolatedSandbox

    return {
        "draw_sample": draw_continuation,
        "sandbox_factory": IsolatedSandbox,
        "inputs": [50, 100],
        "programs_database": {"num_islands": 10},
    }
```

`draw_sample(prompt: str) -> str` must return a Python function-body continuation
in the format expected by upstream `Evaluator.analyse`. `sandbox_factory()`
must construct an object with:

```python
def run(program: str, function_to_run: str, test_input, timeout_seconds: int):
    # Execute in your prepared isolated worker, enforcing its timeout.
    return native_numeric_output_or_none, boolean_execution_succeeded
```

There is no default in-process candidate executor. The supplied sandbox owns
isolation, task scoring and enforcement of the native 30-second timeout
argument. A factory is trusted executable research code; model credentials
belong in environment variables selected by the outer request's
`environment_names`, not command-line arguments or returned factory fields.
Avoid credentials in task prompts because prompts and candidate programs are
deliberately recorded as research artifacts.

`inputs` is a nonempty sequence of distinct, hashable JSON scalar values or
tuples. Native input keys must also be mutually sortable because the upstream
database sorts them into score signatures. The optional `programs_database`
dictionary accepts the fields of upstream `ProgramsDatabaseConfig`. Positive
finite temperatures/reset periods and bounded positive integer counts are
validated. No evaluator source can be replaced through a configuration overlay.

The specification is a staged UTF-8 file of at most 1 MiB. It must contain exactly
one `@funsearch.run` function and one `@funsearch.evolve` function, as required by
the native parser. The pinned repository includes an admissible-set example at
`implementation/specification_nonsymmetric_admissible_set.txt`; its dependencies
and execution still require a suitable sandbox.

## Native request

Inside the existing `arena.native-run/1` specification, use framework
`funsearch-original` and this request shape (replace paths with prepared local
paths):

```json
{
  "python": "/absolute/prepared-environment/bin/python",
  "profile": "single-threaded-native",
  "arguments": [
    "--factory", "inputs/provider.py:build",
    "--specification", "inputs/specification.py",
    "--max-samples", "100",
    "--samples-per-prompt", "4",
    "--trace-mib", "32"
  ],
  "inputs": {
    "inputs": "/absolute/prepared-input-bundle"
  }
}
```

The recipe fixes `--output` to the run's `results` directory. The driver aliases
the isolated clone as the `funsearch` namespace so upstream absolute imports
resolve to this exact implementation even though the clone directory is called
`funsearch-original`. No source files are edited. Only one sampler and one
evaluator are constructed: upstream `main` enters the first sampler's infinite
loop before it can start another sampler.

`--max-samples` bounds calls to the supplied continuation provider, including
failed calls; it must be between 1 and 1,000,000. The final partial batch is
returned to the native evaluator before termination. Initial seed evaluation
is additional to this budget. Provider-internal retries or multiple underlying
model requests remain the provider's responsibility. The outer native runtime
timeout bounds its process group; it does not cancel work already submitted to
external model, sandbox or cluster services.

## What is recorded

`results/native-trace.jsonl` records native database prompts, provider requests
and continuations, sandbox requests/observations, and programs registered in
each native island. Native registration is observed after the original method
has executed, including registrations during resets. This is an observation
stream, not a resumable serialization of the whole database.

`results/native-result.json` includes provider/evaluation counts, termination
reason and native island leaders with their per-input scores. Final leader
source is limited to 64 KiB per program, with a SHA256 of the full source and an
explicit truncation marker. Nonfinite native values are tagged as observations
instead of being emitted as nonstandard JSON numbers. Provider exception
messages are not copied into this result.

`--trace-mib` bounds the event stream to 1–256 MiB (default 32). Exhausting that
capacity stops the driver, writes `native_status: trace_limit_reached` and exits
nonzero; the incomplete trace is not represented as a completed sample budget.
An outer forced termination can leave only the flushed trace and runtime
receipt, without the driver result. The generic reader hashes these artifacts;
it does not infer fitness from them.

Native `runs_ok` means execution succeeded according to the supplied sandbox.
The original evaluator may register a candidate that succeeds on only a subset
of test inputs, and the database's scalar reduction uses the last recorded
input score. Neither observation establishes canonical Arena validity or
cross-task comparability. All results explicitly retain
`canonical_evaluation: false`.

## Local verification

```sh
ARENA_FUNSEARCH_ORIGINAL_SOURCE=/tmp/arena-framework-sources/funsearch-original \
  .venv/bin/python -m pytest -q tests/frameworks/test_funsearch_original.py
```

This checks the exact commit and source hashes, nonexecuting request preparation,
namespace isolation, and controlled provider/native-interface fixtures for
budget termination, partial batches, error receipts and bounded trace output.
It does not import the external scientific dependencies, execute generated
programs, contact a model provider or establish benchmark performance.
