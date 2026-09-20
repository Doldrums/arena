"""Initialization provenance and incomplete historical request accounting."""
import json
from pathlib import Path
import tempfile
import unittest

from arena.observers.sciel.architecture import architecture, start_protocol
from arena.observers.sciel.data import RunStore


class StartProtocolTests(unittest.TestCase):
    def test_warm_start_exposes_only_recorded_parent_identifiers(self):
        start = {"config": {"portfolio_seed": False, "warm_start": {
            "schema": "sciel-warm-start/1", "source": "PRIVATE SOURCE BODY",
            "parent": {"run_id": "parent-run", "program_id": "p17"}}}}
        protocol = start_protocol(start, {}, [])
        self.assertEqual(protocol, dict(kind="warm_start", label="Warm start",
            source_run="parent-run", source_candidate="p17", portfolio_seed=False))
        self.assertNotIn("PRIVATE SOURCE BODY", json.dumps(protocol))
        section = next(item for item in architecture(start, {}, [])["sections"] if item["id"] == "initialization")
        self.assertNotIn("PRIVATE SOURCE BODY", json.dumps(section))

    def test_explicit_warm_event_wins_over_missing_or_conflicting_config(self):
        event = dict(event="decision", policy="initialization", action="warm_start",
            schema="sciel-warm-start/1", parent=dict(run_id="source", program_id="p9"))
        for start in ({}, {"config": {"warm_start": None}}):
            with self.subTest(start=start):
                self.assertEqual(start_protocol(start, {}, [event])["kind"], "warm_start")

    def test_fresh_requires_recorded_config_and_initialization_evidence(self):
        seed = dict(event="decision", policy="initialization", action="seed_program", schema="sciel-initialization/1")
        self.assertEqual(start_protocol({}, {}, [seed])["kind"], "unknown")
        self.assertEqual(start_protocol({"config": {}}, {}, [])["kind"], "unknown")
        self.assertEqual(start_protocol({"config": {"portfolio_seed": True}}, {}, [seed])["kind"], "fresh")
        self.assertEqual(start_protocol({"config": {"warm_start": None}}, {}, [])["kind"], "fresh")
        self.assertEqual(start_protocol({"config": {"warm_start": {}}}, {}, [seed])["kind"], "unknown")
        self.assertIsNone(start_protocol({}, {}, [])["portfolio_seed"])


class StopAccountingTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.log = self.root / "sciel_events.jsonl"
        self.store = RunStore([self.root])
        self.append(event="run_start", counters={"cost_total": .1})

    def append(self, **row):
        with self.log.open("a") as stream:
            stream.write(json.dumps(dict(run_id="run", segment_id="segment", **row)) + "\n")

    def snapshot(self):
        return self.store.snapshot(self.store.discover()[0]["id"])

    def test_historical_llmerror_without_receipt_marks_counter_incomplete(self):
        self.append(event="research", phase="aux_start", kind="reflection", reference=3, call_index=2)
        self.append(event="research", phase="aux_stopped", kind="reflection", reference=3, error_type="LLMError")
        self.append(event="run_end", reason="research_stopped", cost_total=.1)
        (self.root / "checkpoint.json").write_text(json.dumps(dict(
            cost_total=.1, research=dict(stopped_reason="research auxiliary request stopped: LLMError"))))
        result = self.snapshot()
        self.assertEqual(result["stats"]["cost_total"], .1)
        self.assertEqual(result["stats"]["cost_status"], "known_logged_lower_bound")
        self.assertEqual(result["run"]["stop_detail"], "Research auxiliary request stopped: LLMError")
        self.assertIn("timing", result)
        self.assertEqual(result["start_protocol"]["kind"], "unknown")

    def test_matched_known_aux_result_does_not_become_unknown(self):
        self.append(event="research", phase="aux_start", kind="conclusion", reference="r1", call_index=1)
        self.append(event="research", phase="aux_result", kind="conclusion", reference="r1", call_index=1, cost=.02)
        self.append(event="research", phase="aux_stopped", kind="conclusion", reference="r1", error_type="LLMError")
        self.append(event="run_end", reason="research_stopped", cost_total=.12)
        self.assertEqual(self.snapshot()["stats"]["cost_status"], "reported")

    def test_new_dispatch_is_not_covered_by_earlier_receipt(self):
        self.append(event="research", phase="aux_result", kind="conclusion", reference="r1", call_index=1, cost=.02)
        self.append(event="research", phase="aux_start", kind="conclusion", reference="r1", call_index=2)
        self.append(event="research", phase="aux_stopped", kind="conclusion", reference="r1", error_type="LLMError")
        self.append(event="run_end", reason="research_stopped", cost_total=.12)
        self.assertEqual(self.snapshot()["stats"]["cost_status"], "known_logged_lower_bound")

    def test_length_skip_and_known_response_error_keep_reported_cost(self):
        self.append(event="research", phase="aux_result", kind="conclusion", reference="r1", cost=.02, finish_reason="length")
        self.append(event="research", phase="aux_skipped", kind="conclusion", reference="r1",
                    reason="response_length", cost=.02, current_call_cost_unknown=False)
        self.append(event="research", phase="aux_stopped", kind="reflection", reference=3,
                    stage="response", error_type="LLMError", generation_returned=True,
                    cost=.03, current_call_cost_unknown=False)
        self.append(event="run_end", reason="research_stopped", cost_total=.15)
        self.assertEqual(self.snapshot()["stats"]["cost_status"], "reported")

    def test_stop_detail_is_sanitized_and_hidden_for_active_history(self):
        (self.root / "checkpoint.json").write_text(json.dumps(dict(research=dict(
            stopped_reason="research stopped: token=private sk-secretvalue"))))
        self.append(event="research", phase="aux_stopped", error_type="<script>provider text</script>")
        self.assertIsNone(self.snapshot()["run"]["stop_detail"])
        self.append(event="run_end", reason="research_stopped", cost_total=.1)
        detail = self.snapshot()["run"]["stop_detail"]
        self.assertNotIn("private", detail)
        self.assertNotIn("sk-secretvalue", detail)
        self.assertNotIn("<script>", detail)


if __name__ == "__main__":
    unittest.main()
