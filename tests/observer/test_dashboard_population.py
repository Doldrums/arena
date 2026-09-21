"""Recorded population projection; no engine, NumPy, models or candidate execution."""

import copy
import json
import unittest
from unittest.mock import patch

from arena.observers.sciel.population import population_view


def population(iteration=2, seq=4):
    return dict(event="population", iteration_no=iteration, B_evals=iteration,
        segment_id="a", event_seq=seq, archive=[.7, .6],
        islands=[dict(idx=0, best=.7, n=2, cells=1,
            grid=[[5, 9, .7]], members=[["p1", .6, 0], ["p2", .7, 1]])])


def checkpoint(iteration=2, anchor=None):
    result = dict(iteration_no=iteration, B_evals=iteration,
        identity={"descriptor": {"kind": "pca2_v3@abc", "embed_sha": "abc"}},
        config={"grid_bins": 10, "container": {"kind": "legacy"}},
        db=dict(programs=[dict(id="p1", score=.6, gen=0),
                          dict(id="p2", score=.7, gen=1),
                          dict(id="p3", score=.65, gen=2)],
                archive=["p2", "p3"], islands=[dict(idx=0, best_id="p2",
                    members=["p1", "p2"], grid={"5,9": "p2"})]))
    if anchor is not None:
        result["provenance"] = {"journal_anchor": {"segment_id": "a", "event_seq": anchor}}
    return result


class PopulationTests(unittest.TestCase):
    def test_journal_does_not_invent_elite_or_archive_ids(self):
        rows = [dict(event="research", phase="outcome", experiment_id="r2",
                     evidence=dict(id="r2", child_id="p2")), population()]
        start = {"descriptor": {"kind": "pca2_v3@xyz", "embed_sha": "xyz"},
                 "config": {"grid_bins": 10}}
        result = population_view(checkpoint(1), rows, start, {"r2": {"code": "x=1"}})
        self.assertEqual(result["source"], "journal")
        self.assertEqual(result["descriptor"]["embed_sha"], "xyz")
        self.assertEqual(result["iteration"], 2)
        self.assertFalse(result["stale"])
        island = result["islands"][0]
        self.assertIsNone(island["best_candidate_id"])
        self.assertEqual(island["grid"], [dict(x=5, y=9, score=.7, candidate_id=None)])
        self.assertIsNone(island["members"][1]["grid_elite"])
        self.assertIsNone(island["members"][1]["archive_member"])
        self.assertTrue(island["members"][1]["code_available"])
        self.assertEqual(result["archive"]["source"], "journal_scores")
        self.assertTrue(all(member["id"] is None for member in result["archive"]["members"]))

    def test_checkpoint_keeps_members_elites_and_archive_distinct(self):
        cp, rows = checkpoint(3), [population(2)]
        sources = {"p2": {"code": "def run(): return 1"}}
        original = copy.deepcopy((cp, rows, sources))
        result = population_view(cp, rows, {}, sources)
        self.assertEqual((cp, rows, sources), original)
        self.assertEqual(result["source"], "checkpoint")
        island = result["islands"][0]
        self.assertEqual(island["best_candidate_id"], "p2")
        self.assertEqual(island["grid"][0]["candidate_id"], "p2")
        self.assertEqual(island["member_count"], 2)
        self.assertEqual([p["id"] for p in island["members"]], ["p1", "p2"])
        self.assertEqual([p["id"] for p in result["archive"]["members"]], ["p2", "p3"])
        self.assertFalse(island["members"][0]["grid_elite"])
        self.assertTrue(island["members"][1]["grid_elite"])
        self.assertEqual(island["members"][1]["grid_cell"], [5, 9])

    def test_same_iteration_snapshot_order_uses_checkpoint_anchor(self):
        rows = [population(seq=4), {"event": "research", "segment_id": "a", "event_seq": 5}]
        result = population_view(checkpoint(anchor=5), rows, {}, {})
        self.assertEqual(result["source"], "checkpoint")
        result = population_view(checkpoint(anchor=4), rows, {}, {})
        self.assertEqual(result["source"], "checkpoint")
        result = population_view(checkpoint(), rows, {}, {})
        self.assertEqual(result["source"], "journal")

    def test_journal_after_checkpoint_wins_even_at_same_iteration(self):
        rows = [{"event": "research", "segment_id": "a", "event_seq": 3}, population()]
        result = population_view(checkpoint(anchor=3), rows, {}, {})
        self.assertEqual(result["source"], "journal")
        self.assertIsNone(result["islands"][0]["grid"][0]["candidate_id"])

    def test_freshness_detects_newer_iteration_or_same_iteration_admission(self):
        for later in [dict(event="iteration", iteration_no=3),
                      dict(event="research", phase="outcome", evidence={"child_id": "p4"})]:
            result = population_view({}, [population(), later], {}, {})
            self.assertTrue(result["stale"])
        # A new hypothesis is not a population admission.
        result = population_view({}, [population(), dict(event="research", phase="attempt",
            evidence={"iteration": 3})], {}, {})
        self.assertFalse(result["stale"])

    def test_missing_snapshot_and_actual_descriptor_remain_unknown(self):
        result = population_view({}, [], {"config": {"embed_grid": True}}, {})
        self.assertFalse(result["available"])
        self.assertEqual(result["descriptor"], {})
        self.assertEqual(result["islands"], [])
        self.assertIsNone(result["iteration"])
        self.assertIsNone(result["stale"])
        self.assertEqual(result["layout"]["kind"], "unknown")
        self.assertEqual(result["layout"]["coordinates"], "unavailable")
        self.assertEqual(result["archive"]["source"], "unavailable")

    def test_recorded_descriptor_fallback_and_vq_labels(self):
        for kind, layout, label in [("code_length", "map_elites", "Code length bin"),
                                    ("vq_niche", "vq", "Recorded VQ niche ID")]:
            result = population_view({}, [population()], {"descriptor": {"kind": kind},
                "config": {"embed_grid": True}}, {})
            self.assertEqual(result["layout"]["kind"], layout)
            self.assertEqual(result["layout"]["x_label"], label)
            self.assertIsNone(result["layout"]["grid_bins"])
            self.assertEqual(result["layout"]["embedding_coordinates"], "unavailable")

    def test_missing_legacy_members_are_not_empty_storage(self):
        row = population()
        del row["islands"][0]["members"]
        del row["islands"][0]["grid"]
        result = population_view({}, [row], {}, {})
        island = result["islands"][0]
        self.assertEqual(island["member_count"], 2)
        self.assertFalse(island["members_available"])
        self.assertFalse(island["grid_available"])

    def test_bounded_payload_preserves_recorded_counts(self):
        row = population()
        row["islands"][0].update(n=7, cells=7,
            members=[[f"p{i}", i / 10, i] for i in range(7)],
            grid=[[i, 1, i / 10] for i in range(7)])
        row["archive"] = list(range(7))
        with patch("arena.observers.sciel.population.MAX_MEMBERS", 2), patch("arena.observers.sciel.population.MAX_CELLS", 3), \
                patch("arena.observers.sciel.population.MAX_ARCHIVE", 4):
            result = population_view({}, [row], {}, {})
        island = result["islands"][0]
        self.assertEqual(island["member_count"], 7)
        self.assertEqual(len(island["members"]), 2)
        self.assertEqual(len(island["grid"]), 3)
        self.assertTrue(island["members_truncated"])
        self.assertTrue(island["grid_truncated"])
        self.assertEqual(result["archive"]["count"], 7)
        self.assertEqual(len(result["archive"]["members"]), 4)
        self.assertTrue(result["archive"]["truncated"])

    def test_malformed_optional_values_produce_finite_json(self):
        row = population()
        row["archive"] = [float("nan"), True]
        row["islands"][0].update(best=float("inf"),
            members=[["p1", float("nan"), True], None],
            grid=[[0, 1, float("inf")], [True, 1, .2]])
        start = {"descriptor": {"kind": [], "bad": float("nan")},
                 "config": {"container": {"kind": []}}}
        result = population_view({}, [row], start, {})
        json.dumps(result, allow_nan=False)
        self.assertIsNone(result["islands"][0]["best_score"])
        self.assertIsNone(result["islands"][0]["members"][0]["score"])
        self.assertIsNone(result["islands"][0]["members"][0]["generation"])

    def test_retention_uses_recorded_soft_target_without_changing_membership(self):
        cp = checkpoint()
        cp["config"].update(pop_cap=1)
        original = copy.deepcopy(cp)
        result = population_view(cp, [], {}, {})
        self.assertEqual(result["retention"], dict(target_members_per_island=1, limit_kind="soft"))
        # Protected elites can exceed a soft target; placeholders are not an
        # instruction to hide real members or invent new stored candidates.
        self.assertEqual(result["islands"][0]["member_count"], 2)
        self.assertEqual([member["id"] for member in result["islands"][0]["members"]], ["p1", "p2"])
        self.assertEqual(cp, original)

    def test_retention_recognizes_explicit_hard_container_kinds(self):
        for kind in ("grid", "pool", "pool_novelty", "cvt", "vq", "annealed"):
            with self.subTest(kind=kind):
                result = population_view({}, [], {"config": {"pop_cap": 50, "container": {"kind": kind}}}, {})
                self.assertEqual(result["retention"], dict(target_members_per_island=50, limit_kind="hard"))

    def test_retention_unknown_archives_do_not_inherit_current_defaults(self):
        for config in ({}, {"embed_grid": True}, {"container": {"kind": []}}, {"container": {"kind": "future"}}):
            with self.subTest(config=config):
                result = population_view({}, [], {"config": config}, {})
                self.assertEqual(result["retention"], dict(target_members_per_island=None, limit_kind="unknown"))
        result = population_view({}, [], {"config": {"container": {"kind": "legacy"}}}, {})
        self.assertEqual(result["retention"], dict(target_members_per_island=None, limit_kind="soft"))

    def test_retention_rejects_nonpositive_or_nonfinite_targets(self):
        for target in (0, -1, float("nan"), float("inf"), True, "50", []):
            with self.subTest(target=target):
                result = population_view({}, [], {"config": {"pop_cap": target}}, {})
                self.assertIsNone(result["retention"]["target_members_per_island"])
                json.dumps(result, allow_nan=False)

    def test_retention_uses_same_config_precedence_as_population(self):
        cp = checkpoint()
        cp["config"].update(pop_cap=50)
        start = {"config": {"pop_cap": 80, "container": {"kind": "pool"}}}
        result = population_view(cp, [], start, {})
        self.assertEqual(result["retention"], dict(target_members_per_island=80, limit_kind="hard"))
        # A partial run_start config does not borrow an unrecorded value from
        # another source; the chosen configuration remains coherent.
        result = population_view(cp, [], {"config": {"grid_bins": 10}}, {})
        self.assertEqual(result["retention"], dict(target_members_per_island=None, limit_kind="unknown"))


if __name__ == "__main__":
    unittest.main()
