# AEL native portfolio CPU/API pilot

`ael-portfolio-gateway` / `hourly-portfolio-pilot` is a separate recipe for
[`WujiangXu/AEL` at c95f5f961667e7df4bdddf750b22332158951bf2](https://github.com/WujiangXu/AEL/tree/c95f5f961667e7df4bdddf750b22332158951bf2).
The existing `ael-harness` / `portfolio` recipe and its hashes remain unchanged.
This profile is prepared and checked offline; it has not made model calls or
been admitted to the production queue.

The driver calls the released `build_components`, `ExperimentConfig` and
`PortfolioRunner.run`. Planner selection, bandit updates, credit assignment,
memory, reflection, native generated-planner validation and portfolio accounting
remain upstream code. The baseline configuration is `experiments/configs/ael_full.yaml`,
with all three evolution modules enabled and the native local memory backend.
It does not require the external XMem service.

The pilot uses bundled AAPL/MSFT data for 6, 7, 8 and 10 January 2025: four
cached hourly bars per day, 16 allocation/evaluation steps. Its native phase
labels are 8 train, 4 validation and 4 test bars. AEL continues learning during
validation and freezes learning on the test day; this is the released phase
behavior, not a newly added model-selection experiment. The final episode cap
skips the final evening; three nightly cycles can execute. Conditional skill,
architecture and planner branches need not all trigger in a short real pilot.
Portfolio mode itself executes all registered tools and injects selected planner
guidance; it is not every task or branch in the paper.

Hourly evaluation reads the bundled `data/returns_1h` files. Daily mode would
call yfinance and is not used. Preparation verifies every selected price timestamp
and all 32 one-bar return observations, rejects missing/nonfinite returns, and
hashes 218 source/config/data files. Native tools receive their bundled financial
snapshots. Known post-period inputs occur: `data/fundamentals/AAPL.json` contains
`income_statement["2025-09-30T00:00:00"]`, and `data/earnings/AAPL.json` contains
`quarterly_income["2025-12-31T00:00:00"]`, after the January 2025 pilot. Native
financial tools load the static snapshots without an as-of cutoff; derived DCF
and risk signals can expose this lookahead even when raw statements are omitted
from the compact allocation prompt. Freezing learning on test does not remove
that leakage. Native Sharpe/return/drawdown outputs therefore remain
integration observations, not canonical Arena scores, financial evidence or a
paper reproduction. Native annualization, return definitions and parsing are
retained without correction.

## Explicit transport and configuration changes

Only `ael/llm_utils.py` is replaced in the isolated workspace, after verifying
its original SHA-256 `407b32e5c14c9d182aa45839ad8ca14f722f949dab9e89a2f4add00a0fafc945`.
The replacement imports the reviewed centralized gateway helper. It sends the
exact selected model to `http://127.0.0.1:8789/v1` using the worker-supplied
`OPENAI_API_KEY`; no alias, alternate endpoint, provider prefix or fallback model
is accepted. Allocation, reflection, skills and generated-planner calls use the
same helper. The complete generated native configuration and its hash are saved.
The recipe plan fingerprints integration source files, preparation input and
dependency freeze; the runtime receipt records helper before/after hashes.

The transport serializes actual SDK requests and admits at most 64 calls.
SDK retries are zero and the per-request timeout is 330 seconds. Model token and
temperature requests are recorded but not enforced by the current gateway;
cost stays unknown. The template enforces the separate 2400-second whole-process
deadline, 2 CPU / 4096 MiB / 256 PIDs and one evaluation slot. Direct driver use
requires an equivalent outer process boundary. These limits do not constitute
a monetary budget or a security sandbox for arbitrary generated code.

Upstream catches ordinary provider exceptions and can substitute equal weights.
This profile raises a terminal integration exception for transport failure or
budget exhaustion, preserving partial receipts and preventing an API outage from
being counted as a completed heuristic experiment. Native parsing fallbacks for
returned model text remain unchanged; a returned response is not itself proof of
a valid allocation. Provider error details, credentials and prompt bodies are not
written to the integration usage ledger. Native artifact logs remain private.

## Preparation and evidence

The new files are:

- `src/arena/frameworks/drivers/ael_gateway_transport.py`
- `src/arena/frameworks/drivers/ael_portfolio_gateway.py`
- `registry/framework-recipes/ael-portfolio-gateway.json`
- `scripts/deployment/prepare_ael_pilots.py`
- `scripts/deployment/check_ael_pilot.py`
- `tests/frameworks/test_ael_pilot.py`
- this document.

The VM has an isolated Python 3.11.16 environment at
`/srv/arena/envs/ael-portfolio-gateway`. Its 83-package freeze is
`/srv/arena/build/ael-portfolio-preparation-20260921/dependencies.txt`, SHA-256
`08e42f15701ac2fe03fe5cb2c22677406e02004c7f912f669b17e213010ef8e9`.
`pip-check.txt` records the dependency check. Version ranges in native
requirements were resolved during this preparation; the freeze is an observation,
not a preexisting reproducible lock.

The same private preparation directory contains `templates/` with seven pure
plans, dependency/preparation inputs and blocked template fragments awaiting
operator review/deployment. No production configuration was changed. An isolated
copy under `app/` exercised the new driver without deploying it to the running
application. Subsequent deployment must regenerate plans against the deployed
integration files rather than treating preparation hashes as future run hashes.

For every exact model, the offline conformance CLI used the real OpenAI SDK with
`httpx.MockTransport`; socket connections were blocked. The genuine native loop
completed 16 allocations, three reflections/nightly cycles and 12 learning
episodes, with 21 mock SDK calls and a fixture-generated planner registered by
native code. Identical fixture metrics across model labels are expected and are
explicitly not model results. The per-model `conformance.json`, native artifacts,
preparation manifest and hashes remain in `fixture-*` directories. No real
model calls, external financial-data requests or research runs were performed.

The aggregate receipt is `operator-validation.json` in that preparation directory,
SHA-256 `02fd20e354f74c15c3a3f7a273514f14b6f75e255e9873071715bc76c9658e06`.
All seven plans also passed as worker UID 998; an additional complete native
mock run passed under that UID in `worker-fixtures/sol`. The source checkout
remained clean. The seven-template file SHA-256 is
`36101ed864c64968f3936ad1a5d51aed35205e7705e24264305e76b2b4be68a5`.
Focused unit tests passed locally and in the isolated VM environment (15 tests).

Example preparation after installing the pinned requirements in its separate
environment:

```sh
python scripts/deployment/prepare_ael_pilots.py \
  --root /srv/arena \
  --destination /srv/arena/configs/ael-portfolio-pilots-NEW \
  --dependencies /srv/arena/build/ael-portfolio-preparation-20260921/dependencies.txt
```

The command only creates plans and input files. Operator review, deployment,
explicit run authorization and first-model artifact assessment remain separate.
