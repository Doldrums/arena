# QDAIF native poetry pilot

`qdaif-poetry-gateway / poetry-mapelites-pilot` runs the pinned OpenELM poetry environment and MAP-Elites implementation at `CarperAI/OpenELM@c844e149e3f59fef546e0bc55f4e12e0f192feb9` (MIT). It is a separate recipe; the existing `qdaif / poetry` recipe remains unchanged. Preparation and offline fixtures establish an integration, not live provider readiness or research performance. Generated templates remain blocked pending operator review and deployment.

The native path is `ELM(config).run()` → `MAPElites.search()` → `PoetryEvolution.random()/mutate()` → `PoetryGenotype.evaluate()`. The bundled seed poem, mutation prompts, quality prompt, genre/tone prompt, categorical behavior space, elite selection, replacement rule and native snapshots remain upstream code. Poetry uses text generation and two text judgments; it needs no embeddings, token log probabilities, external datasets or local model weights.

The only source port replaces `get_model` in `src/openelm/mutation_model.py`, after checking the whole original file SHA-256. Upstream selects chat/completion providers using old model-name substrings and its poetry code calls the selected model with both strings and `HumanMessage` lists. The replacement factory supplies exactly those interfaces: a string for generation and `.content` for judgments. It shares one selected exact gateway model across generation, quality and diversity. It does not rewrite prompts, parse JSON, repair judgments or alter the archive. Before/after hashes and the complete native dataclass config are recorded.

The native evaluator returns `-inf` for malformed judgment JSON; unknown categories can raise during map placement. Its quality field is not clamped to the prompted 1–10 range. These behaviors are preserved. A provider failure or exhausted request allowance stops the run; it is never recorded as a quality judgment. The result is native self-judged quality/diversity, not canonical Arena fitness or independent assessment of literary quality.

## Budgets and artifacts

The fixed native configuration uses seed42, batch2, one initial iteration and four total iterations, the native 5×5 map, history enabled and a snapshot each iteration. The normal complete path contains eight poems and sixteen judgments, all sequential. The template admits 2 CPUs, 4096 MiB, 256 PIDs and one evaluation slot, with a 2400-second outer timeout.

The gateway transport permits at most **24 physical HTTP attempts**, including retries inside the legacy SDK. HTTP adapter retries and redirects are disabled; each request has a 330-second timeout. OpenAI0.27.10 retries HTTP409 `TryAgain` responses internally: every attempt still passes the counter and exhaustion raises a terminal exception outside native parse fallbacks. No model alias or fallback is allowed, and returned model identity and exactly one text choice are checked. The transport refuses a pre-existing SDK session; each native run has a fresh process.

Native `temperature=1.1`, `top_p=0.95` and `gen_max_len=512` remain explicit in the saved native config. They are recorded as **unenforced** by the current gateway, and omitted from its request. These limits are request/evaluation/wall-time bounds, not token or monetary budgets. Cost remains unknown.

`native-result.json` exports live in-memory archive cells, raw quality/category values, fitness history and the native best text. Nonfinite values have explicit JSON markers. Native pickle snapshots remain native opaque files and are never deserialized by Arena. Partial state and a failed/stopped receipt are saved where available; an incomplete run is not a completed search. `gateway-usage.json` contains request counts, prompt hashes and returned usage, not prompts or credentials. `pilot-receipt.json` binds preparation/config/port evidence and labels evaluation noncanonical.

## Isolated preparation

The prepared environment is Python3.11.16 with the native `langchain==0.0.225` and `typing_extensions==4.5.0` constraints preserved. Compatibility constraints used for the actual environment are:

```text
numpy==1.26.4
transformers==4.29.2
tokenizers==0.13.3
openai==0.27.10
wandb==0.15.12
pydantic==1.10.13
```

CPU torch2.0.1 is supplied by the official CPython3.11 Linux wheel, avoiding CUDA packages. All upstream requirements are installed; native package metadata is installed from a separate exact-pin build copy with `--no-deps`. A full 85-package freeze and successful dependency compatibility check are retained. Transitive version ranges were resolved during preparation; the freeze records what was installed and is not claimed to be a historical reproducible lock.

The VM private preparation directory is `/srv/arena/build/qdaif-poetry-preparation-20260921`; environment `/srv/arena/envs/qdaif-poetry-gateway`; clean source `/srv/arena/sources/qdaif`. Production app, control configuration and services are untouched. Only the scoped worker `OPENAI_API_KEY` is needed for a later explicit run, using `http://127.0.0.1:8789/v1`; no credential enters templates or preparation receipts. Hugging Face/Transformers offline mode and disabled W&B prevent unintended model downloads/telemetry in this profile.

Generate the seven hash-bound plans without inference or queue submission:

```sh
python scripts/deployment/prepare_qdaif_pilots.py \
  --root /srv/arena --destination /absolute/new/templates \
  --dependencies /absolute/dependencies.txt \
  --constraints /absolute/constraints.txt
```

The preparation manifest hashes all native Python source files, the native entrypoint/license/build metadata, the dependency freeze and the compatibility constraints. It verifies the same files again before applying the sole factory port inside the runtime's isolated source clone. The three preparation inputs and Arena driver modules are covered by the runtime plan provenance.

## Offline conformance

`check_qdaif_pilot.py` uses the actual old OpenAI SDK with a fixture requests session and blocks socket connections. It executes the real ELM/PoetryEvolution/MAP-Elites loop separately for all seven exact aliases. It checks eight generated poems, sixteen native judgments, three mutation iterations, two final occupied archive cells, expected elite replacement/history and unchanged malformed/out-of-range judgment semantics. Fixture scores are deterministic protocol evidence, not research results.

```sh
/path/to/qdaif/python scripts/deployment/check_qdaif_pilot.py \
  --source /absolute/clean/qdaif --destination /absolute/new/fixture \
  --dependencies /absolute/dependencies.txt --constraints /absolute/constraints.txt \
  --model gpt-5.6-sol
```

A fresh-process `--sdk-budget-only` invocation exercises the actual SDK409 retry loop and proves it stops at24 mocked HTTP attempts. No provider/model calls occur in either mode. Core unit tests also cover exact model response identity, choice cardinality, endpoint/control rejection, credential-free usage records, source hash guards and fresh-session enforcement. These checks do not claim live service availability, evaluator calibration, paper reproduction or hostile-code sandboxing.
