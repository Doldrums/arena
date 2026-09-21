# Public release references

A reviewed release PR adds `SYSTEM/VERSION.json` containing only:

```json
{"schema":"arena.release/1","system":"sciel","version":"1.0.4"}
```

This is an example, not a published SCiEL release. No versions are registered by
this README. Private CI must first create the immutable source/image binding
in the worker's private store. Never add that binding, engine code, image URL,
access key or provider credentials to this directory.

Run `python scripts/check_releases.py` for the public format check. It does not
access private infrastructure. Reviewers separately verify that private CI has
registered the requested version. Merge accepts the public version reference;
it neither proves runtime conformance nor starts an experiment.

The worker resolver and complete workflow are documented in
[private releases](../../docs/private-releases.md). Image dispatch, key issuance
and cloud experiment orchestration remain separate implementation work.
