"""The learning panel projects recorded facts; it never replays policies."""
import copy
import json
import unittest

from arena.observers.sciel.learning import learning_view


def start(**overrides):
    config = dict(crossover=False, op_temperature=.5, selection_policy="novelty_chain",
                  policy=dict(enabled=True, base_mix={"base": .8, "exploit": .2}), three_head=False)
    config.update(overrides)
    return dict(event="run_start", segment_id="a", config=config)


def iteration(number=1, **overrides):
    row = dict(event="iteration", segment_id="a", island=0, iteration_no=number,
               op_used="diff", op_propensity=.5, op_stat={"diff": 0, "full_rewrite": 0},
               meta=dict(op_used="diff", escalated=False,
                         validation_trace={"attempts": [{"operator": "diff"}]}),
               child_score=.7, r_norm=.2, is_island_event=True, is_pop_event=True,
               d_pop=.1, d_isl=.1, effective_mode="base")
    row.update(overrides)
    return row


def controller(number=0, **overrides):
    row = dict(event="decision", policy="controller", action="exploit", segment_id="a", island=0,
               iteration_no=number, event_seq=11, mode_dist={"base": .8, "exploit": .2},
               propensity=.2, plateau=False, phase=0)
    row.update(overrides)
    return row


def arm(view, name):
    return next(item for item in view["operator"]["arms"] if item["name"] == name)


def component(view, name):
    return next(item for item in view["components"] if item["id"] == name)


class LearningTests(unittest.TestCase):
    def test_normalization_evidence_does_not_rewrite_rewards_or_record_flags(self):
        metadata = dict(schema="sciel-reward-normalization/2", policy="ulp8-positive-median-cap1/1",
                        channel_eligible=dict(population=False, island=False),
                        ulp_thresholds=dict(population=1e-15, island=1e-15),
                        learning_raw=0.0, scale=1.0, scale_source="cold_start_unit",
                        cap_applied=False, previous_sample_count=0)
        rows = [iteration(r_norm=0.0, r_raw=2e-16, d_pop=0.0, d_isl=2e-16,
                          is_pop_event=False, reward_normalization=metadata),
                iteration(2, r_norm=1.0, r_raw=.3, reward_normalization=dict(
                    metadata, learning_raw=.3, scale=.1, cap_applied=True,
                    channel_eligible=dict(population=True, island=True),
                    scale_source="prior_positive_median", previous_sample_count=1)),
                iteration(3, r_norm=33475588777075.5)]
        original = copy.deepcopy(rows)
        view = learning_view(start(), {}, rows)
        self.assertEqual(rows, original)
        self.assertEqual(view["rewards"][0]["raw_reward"], 2e-16)
        self.assertEqual(view["rewards"][0]["reward"], 0.0)
        self.assertEqual(view["rewards"][0]["normalization"], metadata)
        self.assertEqual(view["rewards"][2]["reward"], 33475588777075.5)
        self.assertIsNone(view["rewards"][2]["normalization"])
        self.assertEqual(view["summary"]["island_record_events"], 3)
        self.assertEqual(view["reward_normalization"]["recorded_events"], 2)
        self.assertEqual(view["reward_normalization"]["capped_events"], 1)
        self.assertEqual(view["reward_normalization"]["precision_filtered_channels"], 1)

    def test_normalization_policy_requires_saved_evidence(self):
        view = learning_view(start(), {}, [iteration()])
        self.assertIn("not recorded", view["reward_normalization"]["detail"])
        cp = dict(reward=dict(schema="sciel-reward-state/2",
                             normalization_policy="ulp8-positive-median-cap1/1"))
        view = learning_view(start(), cp, [])
        self.assertIn("8 ULPs", view["reward_normalization"]["detail"])
        self.assertEqual(view["reward_normalization"]["recorded_events"], 0)

    def test_static_controller_active_operator_and_no_online_neural_training(self):
        first = start()
        view = learning_view(first, {}, [first, iteration()])
        self.assertEqual(component(view, "operator_bandit")["status"], "online")
        self.assertEqual(component(view, "mode_controller")["status"], "static")
        self.assertEqual(component(view, "mode_bandit")["status"], "disabled")
        self.assertEqual(component(view, "mode_mlp")["status"], "disabled")
        self.assertEqual(component(view, "three_head")["status"], "disabled")
        self.assertIn("not used", component(view, "parent_selection")["detail"])
        self.assertEqual(view["summary"]["credited_operator_updates"], 1)
        self.assertEqual(view["summary"]["cumulative_reward"], .2)

    def test_escalation_attributes_sample_execution_reward_and_credit_separately(self):
        row = iteration(op_used="full_rewrite", meta=dict(op_used="full_rewrite", escalated=True,
                        validation_trace={"attempts": [{"operator": "diff"}, {"operator": "full_rewrite"}]}))
        view = learning_view(start(), {}, [row])
        self.assertEqual(arm(view, "diff")["choices"], 1)
        self.assertEqual(arm(view, "diff")["executions"], 0)
        executed = arm(view, "full_rewrite")
        self.assertEqual(executed["executions"], 1)
        self.assertEqual(executed["evaluated_count"], 1)
        self.assertEqual(executed["record_count"], 1)
        self.assertEqual(executed["credited_updates"], 0)
        self.assertEqual(executed["cumulative_reward"], .2)
        history = view["operator"]["history"][0]
        self.assertEqual(history["selected_operator"], "diff")
        self.assertEqual(history["operator"], "full_rewrite")
        self.assertEqual(history["selected_probability"], .5)

    def test_legacy_forced_fixed_can_credit_but_idea_and_unconfigured_cross_cannot(self):
        fixed = iteration(op_stat={"fixed": "diff"}, meta={"op_used": "diff", "escalated": False})
        idea = iteration(2, op_used="idea", op_stat={"idea_island": True},
                         meta={"op_used": "idea", "escalated": False})
        cross = iteration(3, op_used="cross", op_stat={"fixed": "cross"},
                          meta={"op_used": "cross", "escalated": False})
        view = learning_view(start(op_fixed="diff"), {}, [fixed, idea, cross])
        self.assertEqual(component(view, "operator_bandit")["status"], "static")
        self.assertEqual(arm(view, "diff")["credited_updates"], 1)
        self.assertEqual(arm(view, "idea")["credited_updates"], 0)
        self.assertEqual(arm(view, "cross")["credited_updates"], 0)
        self.assertTrue(all(row["forced"] for row in view["operator"]["history"]))
        cp = {"op_bandit": {"events": {"cross": []}}}
        self.assertEqual(arm(learning_view(start(), cp, [cross]), "cross")["credited_updates"], 1)

    def test_recorded_off_policy_fallback_never_credits_operator_bandit(self):
        row = iteration(op_used="full_rewrite", op_propensity=None, op_stat={"fixed": "cross"},
                        meta=dict(op_used="full_rewrite", escalated=False, op_requested="cross",
                                  op_initial="full_rewrite", op_on_policy=False,
                                  op_fallback_reason="no_distinct_donor",
                                  validation_trace={"attempts": [{"operator": "full_rewrite"}]}))
        view = learning_view(start(crossover=True), {}, [row])
        self.assertEqual(arm(view, "cross")["choices"], 1)
        self.assertEqual(arm(view, "full_rewrite")["credited_updates"], 0)
        history = view["operator"]["history"][0]
        self.assertEqual(history["selected_operator"], "cross")
        self.assertEqual(history["initial_operator"], "full_rewrite")
        self.assertEqual(history["fallback_reason"], "no_distinct_donor")
        self.assertIsNone(history["selected_probability"])
        self.assertFalse(history["on_policy"])
        self.assertEqual(view["summary"]["cumulative_reward"], .2)

    def test_failures_are_not_synthesized_as_zero_rewards(self):
        failed = iteration(reason="eval_failed", child_score=None, r_norm=None,
                           is_island_event=None, is_pop_event=None, effective_mode=None)
        nochild = iteration(2, reason="parse", child_score=None, r_norm=None,
                            is_island_event=None, is_pop_event=None, effective_mode=None)
        view = learning_view(start(), {}, [failed, nochild])
        self.assertEqual(arm(view, "diff")["executions"], 2)
        self.assertEqual(arm(view, "diff")["evaluated_count"], 1)
        self.assertEqual(arm(view, "diff")["credited_updates"], 0)
        self.assertIsNone(view["summary"]["cumulative_reward"])
        self.assertEqual(view["summary"]["missing_reward_events"], 2)
        self.assertTrue(all(point["reward"] is None for point in view["rewards"]))

    def test_missing_escalation_does_not_credit_or_infer_selected_operator(self):
        row = iteration(meta={"op_used": "diff"})
        view = learning_view(start(), {}, [row])
        self.assertIsNone(view["operator"]["history"][0]["selected_operator"])
        self.assertIsNone(arm(view, "diff")["credited_updates"])
        self.assertIsNone(view["summary"]["credited_operator_updates"])
        self.assertEqual(view["summary"]["known_credited_operator_updates"], 0)
        self.assertEqual(view["summary"]["unknown_credit_events"], 1)

    def test_population_and_island_records_are_distinct(self):
        view = learning_view(start(), {}, [iteration(is_pop_event=False)])
        self.assertEqual(view["summary"]["record_events"], 0)
        self.assertEqual(view["summary"]["island_record_events"], 1)
        self.assertEqual(arm(view, "diff")["record_count"], 0)
        self.assertEqual(arm(view, "diff")["credited_updates"], 1)

    def test_controller_joins_event_order_and_segment_not_counter_arithmetic(self):
        rows = [controller(50), iteration(900), controller(901, island=1),
                iteration(902, island=0), iteration(903, island=1),
                controller(904), dict(event="run_start", segment_id="b"),
                iteration(905, segment_id="b"), controller(905, segment_id="b")]
        history = learning_view(start(), {}, rows)["controller"]["history"]
        self.assertEqual(history[0]["iteration"], 900)
        self.assertEqual(history[0]["iteration_before"], 50)
        self.assertEqual(history[0]["effective_mode"], "base")
        self.assertEqual(history[1]["iteration"], 903)
        self.assertIsNone(history[2]["iteration"])
        self.assertIsNone(history[2]["effective_mode"])
        self.assertIsNone(history[3]["iteration"])
        self.assertEqual(history[0]["distribution"], {"base": .8, "exploit": .2})
        self.assertEqual(history[0]["propensity"], .2)

    def test_failed_iteration_does_not_infer_effective_mode(self):
        row = iteration(reason="eval_failed", effective_mode=None, child_score=None, r_norm=None)
        history = learning_view(start(), {}, [controller(), row])["controller"]["history"]
        self.assertEqual(history[0]["mode"], "exploit")
        self.assertIsNone(history[0]["effective_mode"])

    def test_refine_is_recorded_without_reconstructing_probability(self):
        first = start()
        rows = [first, dict(event="decision", policy="refine", action="intensify", segment_id="a", island=0),
                iteration(op_stat={"diff": 0, "full_rewrite": 0}, op_propensity=.72), iteration(2)]
        history = learning_view(first, {}, rows)["operator"]["history"]
        self.assertTrue(history[0]["refine"])
        self.assertFalse(history[1]["refine"])
        self.assertEqual(history[0]["stats"]["diff"], 0)
        self.assertEqual(history[0]["selected_probability"], .72)
        self.assertNotIn("distribution", history[0])
        self.assertIsNone(learning_view(first, {}, [iteration()])["operator"]["history"][0]["refine"])

    def test_checkpoint_windows_exact_and_separate_from_lifetime_counts(self):
        cp = dict(iteration_no=10, op_bandit=dict(window=2, temperature=.5, floor=.05,
                    events={"diff": [.4, .1], "full_rewrite": []}),
                  controller=dict(mode_bandit=dict(window=3, temp=.3,
                    events={"0|base": [0, .6, 0], "1|exploit": []})))
        view = learning_view(start(), cp, [iteration(11)])
        saved = view["operator"]["checkpoint"]
        self.assertTrue(saved["stale"])
        self.assertEqual(saved["iteration"], 10)
        self.assertEqual(saved["arms"][0], dict(name="diff", window_count=2, window_max=.4))
        self.assertEqual(saved["arms"][1]["window_max"], 0)
        self.assertEqual(arm(view, "diff")["credited_updates"], 1)
        mode = view["controller"]["mode_bandit"]
        self.assertEqual(mode["phase_arms"][0]["count"], 3)
        self.assertAlmostEqual(mode["phase_arms"][0]["mean_reward"], .2)
        self.assertIsNone(mode["phase_arms"][1]["mean_reward"])

    def test_mlp_precedence_and_shadow_mode_bandit(self):
        for enabled in (True, False):
            view = learning_view(start(policy=dict(enabled=enabled, mode_source="mlp", mode_bandit=True), three_head=True), {}, [])
            self.assertEqual(component(view, "mode_controller")["status"], "frozen" if enabled else "disabled")
            self.assertEqual(component(view, "mode_bandit")["status"], "online")
            self.assertIn("shadow", component(view, "mode_bandit")["detail"])
            self.assertEqual(component(view, "mode_mlp")["status"], "frozen")
            self.assertEqual(component(view, "three_head")["status"], "frozen")

    def test_centre_selection_and_presets_override_nominal_policies(self):
        view = learning_view(start(selection_policy="ucb1", container={"selection": "centres"},
                                   preset_selection=True, preset_adaptive=True, policy={"enabled": False}), {}, [])
        self.assertEqual(component(view, "parent_selection")["status"], "static")
        self.assertIn("bypasses", component(view, "parent_selection")["detail"])
        self.assertEqual(component(view, "mode_controller")["status"], "online")
        self.assertEqual(view["controller"]["source"], "preset weights")

    def test_preset_decisions_use_recorded_distribution_and_checkpoint_weights(self):
        first = start(preset_selection=True, preset_adaptive=True, policy={"enabled": False})
        preset = controller(7, policy="preset_weights", action="explore", adaptive=True,
                            distribution={"base": .7, "exploit": .2, "explore": .1},
                            propensity=.1, plateau=None, phase=None)
        pending = {**preset, "iteration_no": 8, "event_seq": 14}
        cp = dict(iteration_no=7, preset_weights=dict(version=1, updates=6,
                  log_weights={"base": 0., "exploit": -1.5, "explore": -2.},
                  prior={"base": .8, "exploit": .15, "explore": .05},
                  learning_rate=.1, exploration=.1, max_importance_reward=10.))
        rows = [first, preset, iteration(8, effective_mode="explore"), pending]
        original = copy.deepcopy((cp, rows))
        view = learning_view(first, cp, rows)
        completed, unfinished = view["controller"]["history"]
        self.assertEqual(completed["source"], "preset_weights")
        self.assertTrue(completed["adaptive"])
        self.assertEqual(completed["distribution"], preset["distribution"])
        self.assertEqual(completed["propensity"], .1)
        self.assertEqual(completed["iteration_before"], 7)
        self.assertEqual(completed["iteration"], 8)
        self.assertEqual(completed["effective_mode"], "explore")
        self.assertIsNone(unfinished["iteration"])
        self.assertIsNone(unfinished["effective_mode"])
        saved = view["controller"]["preset_weights"]
        self.assertTrue(saved["available"] and saved["stale"])
        self.assertEqual(saved["iteration"], 7)
        self.assertEqual(saved["updates"], 6)
        self.assertEqual(saved["log_weights"], cp["preset_weights"]["log_weights"])
        self.assertNotIn("probabilities", saved)
        self.assertNotIn("reward", completed)
        self.assertEqual(view["retention"]["controller_total"], 2)
        self.assertEqual((cp, rows), original)
        self.assertTrue(any("binary rewards" in note for note in view["notes"]))

    def test_preset_history_is_bounded_and_never_crosses_resume_segment(self):
        first = start(preset_selection=True, preset_adaptive=False, policy={"enabled": False})
        rows = [first]
        for index in range(125):
            rows.extend([controller(index, policy="preset_weights", action="base",
                                    distribution={"base": .75, "exploit": .17, "explore": .08},
                                    adaptive=False), iteration(index + 1)])
        rows.extend([controller(125, policy="preset_weights", distribution={"base": .75}),
                     {"event": "run_start", "segment_id": "b"}, iteration(126, segment_id="b")])
        view = learning_view(first, {}, rows)
        self.assertEqual(len(view["controller"]["history"]), 120)
        self.assertEqual(view["retention"]["controller_total"], 126)
        self.assertIsNone(view["controller"]["history"][-1]["iteration"])
        self.assertFalse(view["controller"]["preset_weights"]["available"])
        self.assertFalse(view["controller"]["history"][0]["adaptive"])

    def test_preset_checkpoint_malformed_fields_remain_unknown(self):
        cp = {"preset_weights": {"version": 1, "updates": True,
              "log_weights": {"base": float("nan"), "exploit": -2., "bad": True},
              "learning_rate": float("inf")}}
        saved = learning_view(start(), cp, [])["controller"]["preset_weights"]
        self.assertIsNone(saved["iteration"])
        self.assertIsNone(saved["stale"])
        self.assertIsNone(saved["updates"])
        self.assertIsNone(saved["learning_rate"])
        self.assertEqual(saved["log_weights"], {"base": None, "exploit": -2.})
        json.dumps(saved, allow_nan=False)

    def test_missing_config_is_unknown_and_checkpoint_config_is_fallback_only(self):
        view = learning_view({}, {}, [])
        self.assertTrue(all(item["status"] == "unknown" for item in view["components"]))
        self.assertIsNone(view["config_source"])
        self.assertFalse(view["operator"]["checkpoint"]["available"])
        self.assertIsNone(view["summary"]["cumulative_reward"])
        self.assertEqual(learning_view({}, {"config": start()["config"]}, [])["config_source"], "checkpoint")
        empty = learning_view({"config": {}}, {"config": start()["config"]}, [])
        self.assertEqual(empty["config_source"], "run_start")
        self.assertEqual(component(empty, "operator_bandit")["status"], "unknown")

    def test_embedding_uses_actual_descriptor_and_never_requested_flag_alone(self):
        first = start(embed_grid=True)
        self.assertEqual(component(learning_view(first, {}, []), "code_embedding")["status"], "unknown")
        first["descriptor"] = {"kind": "code_length"}
        cp = {"identity": {"descriptor": {"kind": "pca2_v3@abc", "embed_sha": "abc"}}}
        self.assertEqual(component(learning_view(first, cp, []), "code_embedding")["status"], "disabled")
        del first["descriptor"]
        self.assertEqual(component(learning_view(first, cp, []), "code_embedding")["status"], "frozen")
        first["descriptor"] = {"kind": "vq_niche", "embed_sha": "abc"}
        self.assertIn("bookkeeping", component(learning_view(first, {}, []), "code_embedding")["detail"])

    def test_history_is_bounded_but_totals_cover_all_rows_and_inputs_unchanged(self):
        first = start()
        rows = [first]
        for index in range(401):
            rows.extend([controller(index), iteration(index + 1, r_norm=1)])
        original = copy.deepcopy(rows)
        view = learning_view(first, {}, rows)
        self.assertEqual(rows, original)
        self.assertEqual(len(view["operator"]["history"]), 300)
        self.assertEqual(len(view["controller"]["history"]), 120)
        self.assertEqual(len(view["rewards"]), 300)
        self.assertEqual(view["rewards"][0]["iteration"], 102)
        self.assertEqual(view["summary"]["iterations"], 401)
        self.assertEqual(view["summary"]["cumulative_reward"], 401)
        self.assertEqual(view["retention"]["strategy"], "latest")
        self.assertTrue(any("extrema" in note for note in view["notes"]))

    def test_malformed_numbers_stay_json_finite(self):
        cp = dict(iteration_no=1, op_bandit={"events": {"diff": [float("nan")]}, "temperature": float("inf")})
        view = learning_view(start(), cp, [controller(mode_dist={"base": float("inf")}),
                 iteration(r_norm=float("nan"), op_propensity=float("inf"), op_stat={"diff": float("nan"), "bad": True})])
        json.dumps(view, allow_nan=False)
        self.assertIsNone(view["operator"]["checkpoint"]["arms"][0]["window_max"])
        self.assertIsNone(view["operator"]["history"][0]["selected_probability"])
        self.assertNotIn("bad", view["operator"]["history"][0]["stats"])


if __name__ == "__main__":
    unittest.main()
