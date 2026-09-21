"""Small public projection of recorded SCiEL research-method activity.

Counts describe transitions in one recorded run, not unique inventions across
runs, verified utility, or evidence of recursive capability gain. Execution
counts require journal receipt references; this pure projection does not open
or independently verify artifact bodies. Built-in tools, inherited checkpoint
cells, prepared contexts and merely scheduled invocations are excluded.
"""
from __future__ import annotations

import re
from collections import defaultdict


SCHEMA = "sciel-self-improvement/1"
SCOPE = "recorded_run"
COUNTERS = (
    "cells_created", "cell_revisions", "tools_registered", "tools_executed",
    "tool_executions", "shared_observation_deliveries",
)
_KEYS = frozenset(("schema", "scope", "coverage", *COUNTERS))
_HASH = re.compile(r"[a-f0-9]{64}\Z")
_EVENT_SCHEMA = "sciel-research-tool-event/1"
# These recorded engine contracts implement the research-tool event protocol.
# Unknown future contracts may provide observed lower bounds, never zero totals.
_CONTRACTS = frozenset(f"espalier-3.{v}" for v in range(30, 60))
_MAX_INTEGER = 2**53 - 1


def _hash(value):
    return isinstance(value, str) and _HASH.fullmatch(value) is not None


def _count(value):
    return type(value) is int and 0 <= value <= _MAX_INTEGER


def validate_self_improvement(value):
    """Return a detached fixed-field payload, or None for unreviewed data."""
    if not isinstance(value, dict) or set(value) != _KEYS:
        return None
    if value.get("schema") != SCHEMA or value.get("scope") != SCOPE:
        return None
    coverage = value.get("coverage")
    if coverage not in ("complete", "partial", "not_recorded"):
        return None
    for key in COUNTERS:
        number = value[key]
        if number is not None and not _count(number):
            return None
        if coverage == "complete" and number is None:
            return None
        if coverage == "not_recorded" and number is not None:
            return None
    registered, executed, calls = (value[k] for k in
        ("tools_registered", "tools_executed", "tool_executions"))
    if registered is not None and executed is not None and executed > registered:
        return None
    if executed is not None and calls is not None and executed > calls:
        return None
    if value["cells_created"] == 0 and registered not in (0, None):
        return None
    return {key: value[key] for key in ("schema", "scope", "coverage", *COUNTERS)}


def _events(snapshot):
    """Select current-run events and assess coverage without reading files."""
    if not isinstance(snapshot, dict) or snapshot.get("schema") != "sciel-dashboard/1":
        return [], False
    run = snapshot.get("run")
    rows = snapshot.get("events")
    if not isinstance(run, dict) or run.get("scope") != SCOPE or not isinstance(rows, list):
        return [], False
    run_id = run.get("run_id")
    if not isinstance(run_id, str) or not run_id:
        return [], False
    complete = _count(run.get("event_count")) and run["event_count"] == len(rows)
    selected, seen, segments = [], set(), defaultdict(list)
    for row in rows:
        event = row.get("data") if isinstance(row, dict) else None
        if not isinstance(event, dict) or event.get("run_id") != run_id:
            complete = False
            continue
        segment, seq = event.get("segment_id"), event.get("event_seq")
        if not isinstance(segment, str) or not segment or not _count(seq) or seq == 0:
            complete = False
            continue
        identity = (segment, seq)
        if identity in seen:
            complete = False
            continue
        seen.add(identity)
        selected.append(event)
        segments[segment].append(event)
    starts = [e for e in selected if e.get("event") == "run_start"]
    if not starts or sum(e.get("resumed") is False for e in starts) != 1:
        complete = False
    if any(not isinstance(e.get("engine_contract"), str) or
            e["engine_contract"] not in _CONTRACTS for e in starts):
        complete = False
    for events in segments.values():
        ordered = sorted(events, key=lambda e: e["event_seq"])
        if (ordered[0].get("event") != "run_start" or
                [e["event_seq"] for e in ordered] != list(range(1, len(ordered) + 1))):
            complete = False
    return selected, bool(complete)


def self_improvement_from_snapshot(snapshot):
    """Project six within-run counts, preserving unknowns and lower bounds.

    A cell counts only when its creation is recorded in this run. A tool counts
    only when a source-bound registration identifies one of those cells and an
    author action. Execution requires an invoked result with an invocation ID
    and receipt ID for one of those authored tool versions. Failed executions
    count as executions, not successful tools. An observation delivery is one
    receipt exposed to one prompt; exposure is not adoption or measured benefit.
    """
    events, complete = _events(snapshot)
    tool_events = [e for e in events if e.get("event") == "research_tool"
        and e.get("schema") == _EVENT_SCHEMA]
    if any(e.get("event") == "research_tool" and e.get("schema") != _EVENT_SCHEMA
            for e in events):
        complete = False
    created = {e["cell_id"] for e in tool_events if e.get("phase") == "cell_created"
        and _hash(e.get("cell_id")) and _hash(e.get("cell_revision_id"))}
    initial_revisions = {(e["cell_id"], e["cell_revision_id"]) for e in tool_events
        if e.get("phase") == "cell_created" and _hash(e.get("cell_id"))
        and e["cell_id"] in created and _hash(e.get("cell_revision_id"))}
    revisions = {(e["cell_id"], e["cell_revision_id"]) for e in tool_events
        if e.get("phase") == "cell_revision" and _hash(e.get("cell_id")) and e["cell_id"] in created
        and _hash(e.get("cell_revision_id"))} - initial_revisions
    registered = {e["tool_id"] for e in tool_events if e.get("phase") == "registered"
        and _hash(e.get("cell_id")) and e["cell_id"] in created and _hash(e.get("tool_id"))
        and _hash(e.get("source_sha256")) and _hash(e.get("action_id"))}
    invocations, executed, deliveries = set(), set(), set()
    for event in tool_events:
        if (event.get("phase") == "invocation_result" and _hash(event.get("tool_id"))
                and event["tool_id"] in registered
                and event.get("dispatch_status") == "invoked"
                and _hash(event.get("invocation_id")) and _hash(event.get("receipt_id"))):
            invocations.add((event["invocation_id"], event["receipt_id"]))
            executed.add(event["tool_id"])
        if (event.get("phase") == "shared_observations_delivered"
                and _hash(event.get("prompt_sha256")) and _hash(event.get("action_id"))
                and _count(event.get("attempt")) and isinstance(event.get("delivered"), list)):
            for item in event["delivered"]:
                if isinstance(item, dict) and _hash(item.get("receipt_id")):
                    deliveries.add((event["action_id"], event["attempt"],
                        event["prompt_sha256"], item["receipt_id"]))
    values = (len(created), len(revisions), len(registered), len(executed),
        len(invocations), len(deliveries))
    coverage = "complete" if complete else "partial" if events else "not_recorded"
    result = dict(schema=SCHEMA, scope=SCOPE, coverage=coverage)
    result.update({key: value if complete or value else None
        for key, value in zip(COUNTERS, values)})
    return result
