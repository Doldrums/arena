# Independently released implementations

These engines remain distinct from the original paper authors' private engines.
Their links in the research catalog describe an available implementation, not
author endorsement or reproduced paper performance. Both use the shared native
run spec in [the integration guide](README.md).

| Engine | Immutable source | Native evaluation |
| --- | --- | --- |
| `avo-community` | [austin1997/AVO, 0d36ada5](https://github.com/austin1997/AVO/tree/0d36ada5e149f6f86c845f9405381cf09b572d62) | `ScoringFunction` correctness checks, per-configuration values and native geometric mean |
| `openevolve` | [algorithmicsuperintelligence/openevolve, 411fb59c](https://github.com/algorithmicsuperintelligence/openevolve/tree/411fb59c886c18704caaffb611e17cf9e7d824d2) | Supplied Python evaluator and native cascade/metric logic |

AVO's driver loads the native `EvolutionConfig`, fixes its output directories
and explicit version/agent-step/wall budgets, then delegates to
`EvolutionRunner.run()`. The original loop performs variation, scoring,
lineage persistence and self-supervision. `native-summary.json` preserves
`get_results()` without inventing a validity label or normalizing its score.
This is the austin1997 reimplementation, not NVIDIA's original AVO engine.

Stage a credential-free YAML config, initial program, scorer and optional
knowledge base with `request.inputs`. Example `request.arguments`:

```json
["--config", "arena-inputs/config.yaml", "--max-versions", "2",
 "--hours", "0.1", "--max-agent-steps", "10"]
```

The config's `seed_file` and `scoring_module` can point to staged files such as
`arena-inputs/initial.py` and `arena-inputs/scorer.py`. The scorer must implement
the pinned native `ScoringFunction` contract. Keys come from explicit
`environment_names`; a literal `llm.api_key` in the config is rejected.

OpenEvolve delegates directly to `python -m openevolve.cli`. Stage the candidate,
evaluator and config through `request.inputs`, then supply arguments such as:

```json
["arena-inputs/initial.py", "arena-inputs/evaluate.py", "--config",
 "arena-inputs/config.yaml", "--iterations", "2"]
```

The native YAML controls models, provider endpoint, concurrency and evaluator
timeouts. Arena forces an output directory and rejects overrides of both
`--output` and its `-o` alias. Native checkpoint/best-program artifacts are
inventoried; committed historical files and unchanged staged inputs are excluded.
The checkpoint flag does not establish Arena pause/resume conformance.

Planning checks pinned source evidence without importing either native package.
Tests use controlled fake native APIs and source-only preparation; no model
calls or full native research runs are claimed. Prepare each native environment
explicitly and isolate generated-code execution on the worker.
