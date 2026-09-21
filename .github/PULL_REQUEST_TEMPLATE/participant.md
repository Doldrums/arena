## System or release contribution

- System:
- Version:
- Research paper / group, for a new system:

For a private engine update, add only `registry/releases/SYSTEM/VERSION.json`:

```json
{"schema":"arena.release/1","system":"YOUR_SYSTEM","version":"YOUR_VERSION"}
```

Private CI registers the immutable commit and image digest with the worker
before this PR. Keep the engine repository, image details and credentials out
of the public PR. Run `python scripts/check_releases.py`.

For a new public source integration, also include the pinned system declaration,
native launch/evaluation profiles, setup requirements and available conformance
evidence. Regenerate the participant snapshot and run
`python -m arena.registry validate`.

Accepting this contribution does not launch an experiment. Runs require separate
access and an explicit task/budget request. Contact arina.kharlamova@mbzuai.ac.ae
to arrange a run key or discuss a private worker integration.
