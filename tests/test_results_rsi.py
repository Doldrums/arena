"""Public RSI process evidence: authored versus built-in, observed versus unknown."""
from copy import deepcopy
import json

import pytest

from arena.results_rsi import (
    COUNTERS, self_improvement_from_snapshot, validate_self_improvement,
)


def ident(number):
    return f"{number:064x}"


def event(phase, **fields):
    return dict(event="research_tool", schema="sciel-research-tool-event/1",
        phase=phase, **fields)


def snapshot(*events):
    start = dict(event="run_start", resumed=False, engine_contract="espalier-3.59")
    rows = [dict(data=dict(run_id="private-run", segment_id="private-segment", event_seq=i, **e))
        for i, e in enumerate((start, *events), 1)]
    return dict(schema="sciel-dashboard/1", run=dict(run_id="private-run",
        scope="recorded_run", event_count=len(rows)), events=rows)


def created():
    return event("cell_created", cell_id=ident(1), cell_revision_id=ident(2))


def registered(**extra):
    data = dict(cell_id=ident(1), tool_id=ident(3), source_sha256=ident(4), action_id=ident(5))
    data.update(extra)
    return event("registered", **data)


def invocation(**extra):
    data = dict(tool_id=ident(3), invocation_id=ident(6), receipt_id=ident(7),
        dispatch_status="invoked", status="failed")
    data.update(extra)
    return event("invocation_result", **data)


def test_counts_authored_versions_receipted_executions_and_deduplicated_revisions():
    source = snapshot(created(), registered(), registered(), invocation(), invocation(),
        event("cell_revision", cell_id=ident(1), cell_revision_id=ident(2)),
        event("cell_revision", cell_id=ident(1), cell_revision_id=ident(8)),
        event("cell_revision", cell_id=ident(1), cell_revision_id=ident(8)))
    result = self_improvement_from_snapshot(source)
    assert result["coverage"] == "complete"
    assert [result[k] for k in COUNTERS] == [1, 1, 1, 1, 1, 0]
    assert validate_self_improvement(result) == result
    assert not any(private in json.dumps(result) for private in
        ("private-run", "private-segment", ident(1), "source_sha256", "status"))


def test_builtins_inherited_cells_proposals_and_pending_executions_are_excluded():
    source = snapshot(created(), registered(cell_id=None), registered(cell_id=ident(99)),
        event("research_decision", cell_id=ident(1), tool_id=ident(3)),
        event("invocation_started", tool_id=ident(3), invocation_id=ident(6)),
        invocation(), event("cell_revision", cell_id=ident(99), cell_revision_id=ident(8)))
    source["research_tools"] = dict(cells=[{"id": ident(99)}], summary={"versions": 100})
    result = self_improvement_from_snapshot(source)
    assert [result[k] for k in COUNTERS] == [1, 0, 0, 0, 0, 0]


def test_delivery_counts_receipt_exposures_not_empty_broadcasts_or_adoption():
    delivery = event("shared_observations_delivered", action_id=ident(9), attempt=0,
        prompt_sha256=ident(10), delivered=[{"receipt_id": ident(11)}, {"receipt_id": ident(11)}])
    again = deepcopy(delivery)
    again["attempt"] = 1
    result = self_improvement_from_snapshot(snapshot(delivery, delivery, again,
        event("shared_observations_delivered", delivered=[])))
    assert result["shared_observation_deliveries"] == 2


@pytest.mark.parametrize("change", [
    {"receipt_id": None}, {"invocation_id": None}, {"dispatch_status": "pending"},
    {"dispatch_status": "unknown"}, {"tool_id": ident(77)},
])
def test_execution_requires_authored_source_and_actual_result_receipt(change):
    result = self_improvement_from_snapshot(snapshot(created(), registered(), invocation(**change)))
    assert result["tool_executions"] == result["tools_executed"] == 0


def test_full_fresh_empty_run_has_observed_zero_but_missing_or_partial_history_is_unknown():
    assert all(self_improvement_from_snapshot(snapshot())[k] == 0 for k in COUNTERS)
    missing = self_improvement_from_snapshot({})
    assert missing["coverage"] == "not_recorded"
    assert all(missing[k] is None for k in COUNTERS)
    partial = snapshot(created())
    partial["run"]["event_count"] += 1
    result = self_improvement_from_snapshot(partial)
    assert result["coverage"] == "partial" and result["cells_created"] == 1
    assert result["tools_registered"] is None


@pytest.mark.parametrize("mutation", [
    lambda s: s["events"][0]["data"].update(resumed=True),
    lambda s: s["events"][0]["data"].update(engine_contract="future-contract"),
    lambda s: s["events"][1]["data"].update(event_seq=3),
    lambda s: s["events"].append(deepcopy(s["events"][1])),
])
def test_resumed_unknown_or_gapped_history_is_only_a_lower_bound(mutation):
    source = snapshot(created())
    mutation(source)
    source["run"]["event_count"] = len(source["events"])
    result = self_improvement_from_snapshot(source)
    assert result["coverage"] == "partial"
    assert result["cells_created"] == 1


def test_other_run_events_do_not_count_even_with_valid_source_and_receipt_ids():
    source = snapshot(created(), registered(), invocation())
    source["events"][2]["data"]["run_id"] = "another-run"
    result = self_improvement_from_snapshot(source)
    assert result["coverage"] == "partial"
    assert result["cells_created"] == 1
    assert result["tools_registered"] is None and result["tool_executions"] is None


@pytest.mark.parametrize("bad", [None, [], {}, True, "invalid"])
def test_malformed_private_artifact_references_cannot_crash_or_escape_the_projection(bad):
    source = snapshot(created(), event("cell_created", cell_id=ident(1), cell_revision_id=bad),
        event("cell_created", cell_id=bad), event("cell_revision", cell_id=bad),
        registered(cell_id=bad), invocation(tool_id=bad))
    result = self_improvement_from_snapshot(source)
    assert result["cells_created"] == 1 and result["tools_registered"] == 0
    assert result["tool_executions"] == 0
    assert validate_self_improvement(result) == result


@pytest.mark.parametrize("mutate", [
    lambda r: r.update(private_path="/private"),
    lambda r: r.update(cells_created=True),
    lambda r: r.update(cells_created=-1),
    lambda r: r.update(cells_created=2**53),
    lambda r: r.update(tools_executed=2, tools_registered=1),
    lambda r: r.update(tools_executed=1, tool_executions=0),
    lambda r: r.update(coverage="not_recorded"),
    lambda r: r.update(coverage="complete", cells_created=None),
])
def test_strict_public_allowlist_rejects_invalid_counts_and_unreviewed_fields(mutate):
    result = self_improvement_from_snapshot(snapshot(created(), registered(), invocation()))
    mutate(result)
    assert validate_self_improvement(result) is None
