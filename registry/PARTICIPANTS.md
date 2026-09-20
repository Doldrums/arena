# Participant research catalog

`participants.json` serves 99 entries: all 98 works in the supplied
`human-harness-corpus.md`, together with SCiEL. ShinkaEvolve and Darwin Gödel
Machine enrich their existing registrations instead of appearing twice.
Three entries retain immutable system registrations; 96 are literature-only
entries. All 98 works have a direct paper or technical-report link.

## Source and identity

`participant-corpus.json` captures selected source fields from the supplied
document, its SHA-256, each work's original heading, line span and section hash.
It preserves the mechanism and code-link sentences for review. Audit verdicts,
human-contribution judgments and unrelated notes are not imported into the API.
The source filename is portable; the user's machine path is not retained.

Every heading matches exactly one pinned bibliography title from
`search-family-sources.json`. Matching applies Unicode normalization and removes
punctuation; when needed, it removes one terminal parenthesized alias. It does
not use fuzzy title matching. The entire set of 98 bibliography IDs must be
covered exactly once. The captured bibliography includes immutable repository
revision and source-file hashes for paper titles and URLs.

The display year and venue come from the supplied corpus heading. Some entries
name an earlier preprint year and a later venue; these are preserved, rather
than silently replacing the source year with another catalog's publication year.
Agentic Optimization and Darwinian Evolver are marked `technical_report`.
SCiEL has no fabricated paper attachment and is not mapped to the distinct
upstream `sciel-supplement` task collection.

`participant-descriptions.json` contains short English editorial summaries of
the recorded mechanisms. They describe the research methods, without adding
performance comparisons, audit verdicts or claims about Arena execution.

## Research attribution

`participant-attributions.json` records creator credits for all 98 research
works. Each `by …` line uses organizations explicitly named in a primary paper
or official technical report. The source URL, page/section, verification date
and evidence note are retained. For large collaborations the card abbreviates
the byline; the participant detail lists every credited organization.

Work-done footnotes take precedence over later employment. Acknowledgements,
email domains, GitHub handles and predecessor systems do not establish creator
affiliations. Agentic Optimization credits its named author, Junye Pan, because
its report does not declare an institutional affiliation. SCiEL has no invented
organizational credit while the team's preferred attribution is being confirmed.
These credits describe the cited research; they do not imply endorsement or an
active Arena submission by those organizations.

## Public fields

- `attribution`: compact byline, full organizations or authors, primary source
  URL, source location, evidence note and verification date. Optional for
  registrations without an established research credit.
- `record_kind`: `system_registration` or `research_work`.
- `papers`: ID, full title, direct URL, corpus year, corpus venue and publication
  kind. An empty array is explicit when no paper is attached.
- `search_family`: the corpus's declared family, with a stable ID and original
  label. These are literature groupings, not capability or compatibility labels.
- `code_links`: URL, display label and `implementation`, `project` or `artifact`
  scope. A result notebook, evolved harness artifact and project page keep their
  own labels. Baseline repositories and the explicit FlowScout placeholder are
  excluded. Links are source declarations, not new live availability checks.
- `provenance`: document hash and span, source heading, section hash and the
  pinned bibliography file. Corpus details are absent for the SCiEL registration.

The existing `repository` field remains an immutable URL/commit pair only for
registered systems. Literature entries use `null`, even when a code link is
recorded. `registration_status: literature` does not create a build, conformance
check or evaluation queue. Execution capabilities remain separate and false
until a runner is implemented and verified.

The summary distinguishes `participant_count` (99), `research_work_count` (98),
`pinned_registration_count` (3), `literature_only_count` (96) and
`integrated_count` (0). Research works overlap the pinned registrations for
ShinkaEvolve and DGM; these counts are not all additive.

## Rebuild and review

```sh
python scripts/build_participants.py --check
python -m arena.registry validate
```

These commands run offline. The first checks exact reproducibility from the
captured document metadata, English summaries, bibliography, attributions and
registrations;
the registry validator and Python API also reject a stale scholarly snapshot.
The checked-in JSON is the equivalent snapshot used by the Cloudflare Worker.

To review a changed source document, pass its location explicitly:

```sh
python scripts/build_participants.py --corpus /path/to/human-harness-corpus.md
python scripts/build_participants.py --check --corpus /path/to/human-harness-corpus.md
```

The parser requires complete title coverage and reviewed descriptions before
writing the aggregate. New titles require bibliography review; they are not
silently omitted or assigned invented paper links. The task-catalog importer
rebuilds this same aggregate, so refreshing tasks cannot remove the literature
entries. Updates belong in the same team-reviewed registry PR as their sources.
