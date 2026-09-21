<p>
  <img src="web/favicon.svg" alt="Empira — yellow logo with white eyes" width="72" height="72">
</p>

# Empira

**An arena for research on recursive self-improvement.**

Empira connects scientific tasks, research systems and experiment records to study a specific question: **when do changes to a system’s research methods improve its ability to make further improvements?**

Researchers can inspect the problems a system works on, follow changes to its code and research process, and examine results alongside the resources used to obtain them. Frameworks keep their own search algorithms, memory and learning mechanisms.

<p>
  Made by
  <a href="https://cpil-lab.github.io/"><img src="web/brand/cpil.png" alt="CPIL logo" width="48" height="48" align="middle"> CPIL Research Group</a>
  at
  <a href="https://mbzuai.ac.ae/"><img src="web/brand/mbzuai.png" alt="MBZUAI logo" width="48" height="48" align="middle"> MBZUAI</a>.
</p>

[Research board](https://research-arena.small-pine-3af7.workers.dev) · [Contributing](CONTRIBUTING.md) · [Code style](CONTRIBUTING.md#code-style) · [Local setup](#quick-start)

[![Empira board with research statistics and the interactive task atlas](.github/assets/board.png)](https://research-arena.small-pine-3af7.workers.dev)

## Release snapshot — v0.1.0

As of **22 September 2026**, the collection contains **959 task packages** across **151 task families** and **11 research domains**, drawing on a **98-paper research corpus** and supplementary scientific collections.

Our contribution is turning research problems into task packages with a shared evaluation interface. Of the **689 packages with executable evaluator definitions**, **81.13% use evaluators implemented or adapted in the task library**; **18.87% reuse upstream evaluators**.

| How evaluation is provided | Task packages | Share of the full catalog |
| --- | ---: | ---: |
| Implemented or adapted in the task library | **559** | **58.29%** |
| Reused from upstream implementations | 130 | 13.56% |
| Research tasks awaiting evaluation integration | 270 | 28.15% |
| **Total** | **959** | **100.00%** |

Evaluator definitions cover **71.85%** of the catalog. The source library labels **81** of the adapted definitions as verified reconstructions. Recorded numeric seed baselines are available for **667 packages (69.55%)**; **75 (7.82%)** include published numeric references.

Counts refer to task packages, including distinct parameter settings and protocols. The split describes evaluator implementation; validation and runtime requirements are recorded separately for each task.

Snapshot: [`autoresearch-tasks@5729caa7`](https://github.com/IMRUNya/autoresearch-tasks/blob/5729caa7a3bd4e66c39a447c0d4ee56dc8fa0935/README.md). Counts: [task catalog](registry/catalog.json), [research domains](registry/insights.json), [reference evidence](registry/references.json). The source library defines the [implementation categories](https://github.com/IMRUNya/autoresearch-tasks/blob/5729caa7a3bd4e66c39a447c0d4ee56dc8fa0935/docs/SCIENCE_EXPANSION_IMPLEMENTATION.md#L134).

## Inside the arena

| View | What you can investigate |
| --- | --- |
| **Tasks** | Explore research domains and the task atlas; inspect problem descriptions, evaluator contracts and pinned source evidence. |
| **Participants** | Find research systems, their authors and papers, implementation revisions and available launch profiles. |
| **Experiments** | Follow native SCiEL runs through source changes, candidate lineages, research cells, authored tools, model calls and recorded artifacts. |
| **Results** | Examine solution quality, recorded effort and research activity, with comparisons grouped by evaluator contract and model. |

Results connect back to the experiment evidence. Research-cell creation, code revisions and tool use describe how a run developed; demonstrating recursive improvement also requires evaluating what those changes enable in subsequent experiments.

The catalog includes both research works and executable integrations. A paper entry, a prepared launch environment and a completed evaluation each have their own status. Framework profiles record the supported interface and its requirements.

## Working with Empira

1. **Choose a task.** Review its scientific context, candidate interface and evaluation contract.
2. **Select a system version.** Use a pinned implementation or a private engine release, with a prepared environment and an explicit budget.
3. **Run through an authorized worker.** The worker executes approved queue entries and records their artifacts.
4. **Inspect and compare.** Follow the experiment in the workspace and publish reviewed measurements to Results.

Tasks and system versions enter through GitHub PRs. Run access is granted separately; request a key through the board or contact [arina.kharlamova@mbzuai.ac.ae](mailto:arina.kharlamova@mbzuai.ac.ae). An engine’s repository and container image can remain private: its Arena PR can contain only the system name and version. See [private engine releases](CONTRIBUTING.md#private-engine-releases).

## Quick start

Requires **Python 3.11+**. From the repository root:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m arena
```

Open <http://127.0.0.1:8787>. The local board serves the catalog and published results without model credentials. Native experiment views read existing archives; they do not require the SCiEL engine to be installed.

To inspect your own runs, provide their directories:

```sh
python -m arena --root /path/to/outputs --root /path/to/other-runs
```

| URL | View |
| --- | --- |
| `/` | Tasks and research domains |
| `/?view=participants` | Participants and papers |
| `/results` | Published results |
| `/experiments` | Experiment workspace |

The workspace retains its own Results and Queue pages. Queue operations require a configured private control service and a scoped key.

## Architecture

The discovery board and experiment workspace share task, system and result contracts. A Python observer reads native journals, checkpoints and heartbeat files. Execution belongs to a separate Linux worker with bounded resources and private engine/evaluator services.

| Layer | Implementation |
| --- | --- |
| Interface | JavaScript ES modules, HTML and CSS in `web/` |
| Observer and execution services | Python in `src/arena/`; NumPy for numerical projections |
| Edge API | TypeScript on Cloudflare Workers, with Cloudflare Access authentication |
| Registry | Versioned JSON snapshots and schemas in `registry/` and `schemas/` |
| Private queue | SQLite-backed control service, worker leases, quotas and cancellation |

The cloud board serves published result snapshots and connects to the private observer through a Cloudflare VPC Service. Experiment views read native run state; published Results change through an explicit export and deployment. The public Worker exposes read-only routes; execution credentials stay on the private side.

The Python package and CLI use the name `arena`. See [running the services](CONTRIBUTING.md#running-the-services) for worker configuration and Cloudflare deployment.

## Validation

For development, install the test dependencies and use **Node 22.12+**:

```sh
python -m pip install -e '.[dev]'
npm ci
npm ci --prefix tests/web
python scripts/check_repository_policy.py
python -m pytest -q
npm run test:web
npm run test:api
npm run typecheck
```

CI also checks generated registry snapshots and package/Worker builds. See the [complete check list](CONTRIBUTING.md#checks). Default tests use fixtures and local transports; Linux execution conformance has separate opt-in checks.
