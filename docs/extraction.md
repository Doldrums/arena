# SCiEL dashboard extraction

Arena was created as an independent repository from `Doldrums/sciel` commit `0d67f813dd4ac21dee304f2b0de0b0ce59bf4157` on 2026-09-20. The original board lives under `src/sciel/web/`; the new board lives under `web/` and `src/arena/observers/sciel/`.

`extraction-source.json` records original paths, destination paths and SHA-256 hashes of the extracted baseline. Subsequent Arena edits are tracked by Git; the manifest is the provenance of extraction, not a claim that current files still match the baseline.

The original dashboard is kept in the active SCiEL worktrees during migration so existing running experiments and open dashboards continue to work. New Arena platform development belongs here. Removing the compatibility entrypoint from SCiEL can happen after callers switch to `arena --root ...`; no experiment outputs need to move.

The native view retains SCiEL protocol names and schema identifiers. Pure readers, validation helpers and geometry checks that were previously imported from SCiEL have been extracted into `observers/sciel/compat/`. They do not run the engine, candidates, model calls or evaluator processes. NumPy remains a dependency for the original geometry validation semantics.

The native view is `/experiments`; `/` now belongs to the Arena task catalog. Existing chart, population, source/diff, workflow and research views remain available. The original `style.css` is preserved as the baseline visual language.

No live run logs, credentials or framework source trees are included as application data. Tests contain synthetic fixtures and saved protocol evidence for regression checks. This extraction does not assign a new open-source license to the source material; see `NOTICE.md`.
