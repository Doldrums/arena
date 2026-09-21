# Code review — 2026-09-21

Scope: current uncommitted Arena implementation, including new framework
adapters, public/private release records, catalog generation and contribution
UI. Review only; no implementation changes were made.

## P1 — Shinka's native evaluator relocation loses the Arena configuration

Location: `src/arena/frameworks/shinka_evaluate.py:18–23`, generated at lines
80–82.

The generated evaluator resolves `evaluation.json` next to `__file__`. Pinned
Shinka reads this evaluator as a string, writes only that string to its results
directory and changes the evaluation program path to that copy. Its sidecar
configuration remains in the original task directory. A normal canonical run
therefore cannot load its configuration and reports every candidate incorrect
without invoking Arena's canonical evaluator.

Reproduction: create a task from the pinned circle-packing configuration, copy
only its `evaluate.py` into a fresh run directory as native Shinka does, and
invoke the copied wrapper with an inert candidate. Result: exit zero,
`correct:false`, `Canonical evaluation failed (ValueError)` and zero receipts.
No native search, model call or Docker evaluation was needed.

Fix direction: preserve a verified configuration reference through native
relocation, and test the actual CLI/runner handoff, not just direct invocation
of the original generated file.

## P2 — Abbreviated native credential options enter saved launch plans

Location: `src/arena/frameworks/recipes.py:244–251`.

The secret-option filter recognizes full option names, while upstream argparse
accepts their unique prefixes. The pinned L-AutoDA profile accepts
`arguments=["--api_k", "FAKE_REVIEW_KEY"]`; the adapter keeps that value in its
argument vector and hence in the serialized plan. Native argparse interprets
the option as `--api_key`. This contradicts the environment-only credential
contract and exposes a key in plan output and process arguments.

Reproduced using the actual pinned profile and a synthetic key. No provider
request occurred. Validate native credential aliases and abbreviations before
serializing the plan, or restrict accepted arguments to a reviewed contract.

## P2 — Factory loading breaks dataclasses with postponed annotations

Location: `src/arena/frameworks/drivers/_specialized.py:24–28`.

`module_from_spec()` is followed by `exec_module()` without registering the
module in `sys.modules`. A valid factory defining an `@dataclass` after
`from __future__ import annotations` fails during class creation with
`AttributeError: 'NoneType' object has no attribute '__dict__'`.

This shared loader affects GEPA, MIPROv2, EoH-S, LLaMEA-HPO and original FunSearch
factories. Register the module under a suitable identity during loading and
preserve its availability for returned objects that depend on that identity.
The minimal reproduction uses only Python's standard library.

## P2 — Git replacement objects can change supposedly pinned reference evidence

Location: `scripts/build_references.py:75`.

New immutable-blob reads use ordinary `git show`, which honors local
`refs/replace`. In a disposable source clone, replacing the
`reference-sat/evaluator.py` blob leaves HEAD at the expected pin and the working
tree clean. The builder succeeds, exporting the replacement's SHA-256 alongside
a GitHub URL pointing to the original immutable commit.

Disable replacement objects on all reads used to establish pinned evidence.
This requires altered local Git metadata; no corruption was found in the
current generated snapshot.

## P2 — Public release validation silently skips prohibited directory contents

Location: `scripts/check_releases.py:18–22`.

The validator visits only `*.json` and does not traverse symlinked directories.
A release directory containing `private-binding.yaml` with private source/image
pointers, or a symlinked system directory, returns
`valid:true, public_references:0`. Neither case reaches the file checks.

The directory's README forbids private bindings and pointers, CI invokes this
validator, and package builds include the entire registry. This check cannot
prevent initial disclosure in a public PR, but it should reject forbidden
contents before acceptance or packaging. Enumerate all entries, allowing the
intended README and regular `SYSTEM/VERSION.json` records only.

## P3 — Declaration-supplied adapter links bypass recipe-derived provenance

Location: `src/arena/participant_corpus.py:189`, declarations copied at line 211.

The builder appends derived links to any `native_adapters` supplied directly in
a participant declaration. A SCiEL declaration containing a link to blocked
AEvo with a nonexistent profile survives validation and publication. Current
declarations do not contain this defect. Either derive this field exclusively
from recipes or cross-check declaration-supplied links against recipe status,
profiles and participant association.

## P3 — Oversized private registrations succeed but cannot be resolved

Location: `src/arena/releases.py:152–158`.

The Python registration API validates an image string longer than 70 KiB,
publishes an immutable binding and returns success. Resolution subsequently
rejects that same record at its 64 KiB size limit, and registration cannot
replace the now unusable version. The CLI already bounds its input; the
in-process API and serialized output need the same bound before publication.

## Validation and limits

- 190 focused direct-adapter/evaluator tests passed; native evaluator relocation
  is not covered by those tests.
- 62 web tests passed; all 99 participant details and 12 domain previews were
  rendered against the current snapshots without exceptions.
- Reproductions used inert keys, temporary files or disposable Git repositories.
  No paid models, research loops or deployment were launched.
- Browser layout and the operating system's mail client were not exercised.
- Documented missing cloud dispatch, hardware environments and full native-run
  conformance are deployment limitations, not additional code findings.
