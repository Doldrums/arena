# Source research families → task packages

`search-families.json` powers the method-family view of the task atlas. It
preserves the ten labels declared in the pinned source's
[`catalog/papers.json`](https://github.com/IMRUNya/autoresearch-tasks/blob/5729caa7a3bd4e66c39a447c0d4ee56dc8fa0935/catalog/papers.json):

| Source label | Corpus papers | Additional source groups |
| --- | ---: | ---: |
| AlphaEvolve / OpenEvolve | 16 | 0 |
| FunSearch / EoH | 18 | 0 |
| DGM / ADAS | 16 | 0 |
| Eureka | 7 | 0 |
| LLM-SR | 4 | 0 |
| Promptbreeder / EvoPrompt | 13 | 0 |
| Other | 24 | 0 |
| SCiEL supplement | 0 | 1 |
| Science supplement | 0 | 13 |
| Community supplement | 0 | 1 |

These are the source corpus curator's labels, not a new Arena taxonomy or a
claim of identical algorithms within a group. **Other** remains the source's
mixed bucket. The **SCiEL**, **Science** and **Community supplements** are
additional task collections, not research-paper method families. Short
descriptions are editorial navigation text.

The source metadata was checked in all three committed files:
`catalog/papers.json` (113 source groups), `catalog/corpus.json` (98 corpus papers)
and `catalog/research.json` (98 investigated paper IDs). Papers/corpus family
labels agree. The 15 supplementary collection IDs and their family labels are
explicitly reviewed; an unknown ID or supplement-looking label cannot bypass
corpus membership verification. `search-family-sources.json` preserves an allowlisted capture of
the paper names, titles, family labels, public links and declared task IDs, plus
the source revision and SHA256 hashes of the original committed files. It does
not import runtime configuration, credentials, code, commands or run results.
Declared task associations are deduplicated after upstream merges: the source
FunBO inventory repeats three canonical IDs for former in/out-of-distribution
packages. The captured file hash still identifies the original source bytes.

## Meaning and counting

A graph edge means **the catalog associates this task package with a paper or
supplementary collection in this family**. It does not mean a registered
participant solved the task, has run it, or supports its runtime or adapter.
The snapshot has 689 executable definitions and 270 unsupported definitions.

For a readable nonoverlapping layout, each task is placed under the family of
the first entry in its catalog `paper_ids`. This is a deterministic display
convention, not scientific priority. Every task retains all paper IDs and all
related source-family IDs. The 959 `task_ids` across groups form an exact
partition. The source merged 254 duplicate IDs into 145 retained task packages;
parameter variants remain separate where the source retains them.

There are 26 cross-family task packages. For example, `eoh-online-bin-packing`
links eight source papers across FunSearch / EoH, AlphaEvolve / OpenEvolve and
Other. Its primary placement is FunSearch / EoH, and both secondary family
associations are kept after merging the former task aliases.
`addressed_task_ids` includes all paper associations and therefore overlaps;
never sum this field to report unique catalog coverage.

Task-level catalog `paper_ids` is authoritative. Source `papers.json.task_ids`
omits some `reference-*` example packages; these are retained separately as
`additional_catalog_task_ids`. They are catalog associations, not invented
claims that the exact reference package was evaluated in the publication.

Each `paper_annotations[id]` carries its original family label, source kind,
paper link, pinned evidence URL/hash and locator. Unknown or new source labels
map to `unknown` and keep their original value. Currently zero source groups
and zero task packages are unknown; the empty unknown display group is omitted.

## API and offline maintenance

`arena.search_families.get_search_families(registry_root=None)` loads the same
static JSON used by the API and uses the packaged-registry fallback. It checks
catalog/source digests and reconstructs all memberships, counts and evidence.
Stale data raises `RegistryError`.

```sh
# Rebuild from the committed sanitized source capture; entirely offline.
python scripts/build_search_families.py

# CI: validate without modifying anything.
python scripts/build_search_families.py --check

# Optional source refresh/verification from an existing local Git checkout.
# The commit comes from catalog.json; these commands never fetch or run tasks.
python scripts/build_search_families.py --checkout /path/to/task-repository
python scripts/build_search_families.py --check --checkout /path/to/task-repository

python -m pytest tests/test_search_families.py -q
```

Source refresh currently supports the initial `autoresearch-tasks` collection
and rejects multiple collections. Git reads the immutable committed objects,
not dirty working-tree files. Default validation needs no source checkout,
network, credentials, framework installation or runtime environment.
