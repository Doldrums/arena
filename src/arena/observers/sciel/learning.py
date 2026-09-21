"""Small read-only learning projections from recorded, ancestry-filtered telemetry.

No defaults, engine imports, policy replay, or inferred probability distributions.
History totals describe the supplied journal; checkpoint windows are separate.
"""
from __future__ import annotations

import math
from collections import deque

HISTORY_LIMIT = 300
DECISION_LIMIT = 120
_BASE_ARMS = ("diff", "full_rewrite", "error_repair")


def _dict(value):
    return value if isinstance(value, dict) else {}


def _number(value):
    if type(value) not in (int, float):
        return None
    try:
        return value if math.isfinite(value) else None
    except OverflowError:
        return None


def _integer(value):
    return value if type(value) is int and value >= 0 else None


def _name(value):
    return value if isinstance(value, str) and 0 < len(value) <= 128 else None


def _bool(value):
    return value if type(value) is bool else None


def _numbers(value):
    return {key: _number(item) for key, item in list(_dict(value).items())[:32]
            if _name(key) and type(item) in (int, float)}


def _sum(total, value):
    return _number((total or 0) + value) if value is not None else total


def _normalization(value):
    """Project saved policy evidence; never renormalize historical rewards."""
    value = _dict(value)
    if (value.get("schema") != "sciel-reward-normalization/2" or
            value.get("policy") != "ulp8-positive-median-cap1/1"):
        return None
    return dict(schema=value["schema"], policy=value["policy"],
                learning_raw=_number(value.get("learning_raw")),
                scale=_number(value.get("scale")), scale_source=_name(value.get("scale_source")),
                cap_applied=_bool(value.get("cap_applied")),
                previous_sample_count=_integer(value.get("previous_sample_count")),
                channel_eligible={key: _bool(_dict(value.get("channel_eligible")).get(key))
                                  for key in ("population", "island")},
                ulp_thresholds={key: _number(_dict(value.get("ulp_thresholds")).get(key))
                                for key in ("population", "island")})


def _components(config, recorded, checkpoint, numeric_stats):
    policy = _dict(config.get("policy"))
    policy_known = isinstance(config.get("policy"), dict)
    mb = _dict(_dict(checkpoint.get("controller")).get("mode_bandit"))
    bandit_on = bool(policy.get("mode_bandit")) or bool(mb)
    mlp = policy.get("mode_source") == "mlp"
    enabled = _bool(policy.get("enabled"))
    fixed = _name(config.get("op_fixed"))
    operator_known = recorded and any(key in config for key in ("crossover", "op_temperature", "op_window"))
    operator_status = "static" if fixed else "online" if operator_known or numeric_stats else "unknown"
    operator_detail = ("Fixed operator selection; eligible records can still update its bandit window."
                       if fixed else "Adaptive operator sampling uses the maximum reward in each arm's record window."
                       if operator_status == "online" else "Operator selection configuration was not recorded.")
    preset = config.get("preset_selection") is True
    source = ("preset weights" if preset else "disabled" if enabled is False else "frozen MLP" if mlp else
              "mode bandit" if bandit_on else "static mixture + plateau rules"
              if policy_known else "unknown")
    mode_status = ("online" if preset and config.get("preset_adaptive") is True else
                   "static" if preset and config.get("preset_adaptive") is False else "unknown" if preset else
                   "disabled" if enabled is False else "frozen" if mlp else
                   "online" if bandit_on else "static" if policy_known else "unknown")
    bandit_detail = ("Checkpoint windows include zero-reward attempts; plateau attempts are excluded."
                     if bandit_on else "Disabled in the recorded policy configuration."
                     if policy_known else "Mode-bandit configuration was not recorded.")
    if bandit_on and (enabled is False or mlp):
        bandit_detail += " It can collect shadow updates while another source controls selection."
    selection = _name(config.get("selection_policy"))
    if _dict(config.get("container")).get("selection") == "centres":
        parent_status = "static"
        parent_detail = "Container-centre selection bypasses the configured parent kernel; kernel statistics may still be collected."
    elif selection == "novelty_chain":
        parent_status = "static"
        parent_detail = "Score and visit-count heuristic (novelty_chain); logged reward_sum is not used for sampling."
    elif selection in {"ucb1", "ucb_sw"}:
        parent_status = "online"
        parent_detail = "Recorded " + selection + " policy updates reward statistics; this is not neural gradient training."
    elif selection == "stock_70_20_10":
        parent_status, parent_detail = "static", "Fixed rank-based score mixture."
    else:
        parent_status, parent_detail = "unknown", "Parent policy: " + (selection or "not recorded") + "."
    three = _bool(config.get("three_head"))
    return [
        dict(id="operator_bandit", label="Operator bandit", status=operator_status, detail=operator_detail),
        dict(id="mode_controller", label="Mode controller", status=mode_status,
             detail="Recorded source: " + source + (". Preset adaptation uses binary population improvement, a separate reward from operator windows."
                    if preset else ". Observed distributions include any recorded plateau override.")),
        dict(id="mode_bandit", label="Mode bandit", status="online" if bandit_on else "disabled" if policy_known else "unknown", detail=bandit_detail),
        dict(id="parent_selection", label="Parent selection", status=parent_status, detail=parent_detail),
        dict(id="mode_mlp", label="Mode MLP", status="frozen" if mlp else "disabled" if policy_known else "unknown",
             detail="Offline weights; no in-run gradient updates." if mlp else "Not enabled in recorded policy." if policy_known else "Not recorded."),
        dict(id="three_head", label="Three-head model", status="frozen" if three else "disabled" if three is False else "unknown",
             detail="Offline model; no in-run gradient updates." if three else "Disabled in recorded configuration." if three is False else "Not recorded."),
    ], source


def _windows(checkpoint, latest_iteration):
    iteration = _integer(checkpoint.get("iteration_no"))
    stale = latest_iteration > iteration if iteration is not None and latest_iteration is not None else None
    state = _dict(checkpoint.get("op_bandit"))
    arms = []
    for name, values in list(_dict(state.get("events")).items())[:32]:
        if not _name(name):
            continue
        valid = isinstance(values, list) and all(_number(v) is not None for v in values)
        arms.append(dict(name=name, window_count=len(values) if isinstance(values, list) else None,
                         window_max=max(values, default=0) if valid else None))
    operator = dict(available=bool(state), iteration=iteration, stale=stale,
                    window=_integer(state.get("window")), temperature=_number(state.get("temperature")),
                    floor=_number(state.get("floor")), arms=arms)
    mode = _dict(_dict(checkpoint.get("controller")).get("mode_bandit"))
    phase_arms = []
    for key, values in list(_dict(mode.get("events")).items())[:128]:
        if not isinstance(key, str) or "|" not in key:
            continue
        phase, name = key.rsplit("|", 1)
        try:
            phase = int(phase)
        except ValueError:
            continue
        if not _name(name):
            continue
        valid = isinstance(values, list) and all(_number(v) is not None for v in values)
        mean = _number(sum(v / len(values) for v in values)) if valid and values else None
        phase_arms.append(dict(phase=phase, mode=name,
                               count=len(values) if isinstance(values, list) else None, mean_reward=mean))
    return operator, dict(available=bool(mode), iteration=iteration, stale=stale,
                          window=_integer(mode.get("window")), temperature=_number(mode.get("temp")),
                          phase_arms=phase_arms)


def _embedding(start, checkpoint):
    descriptor = (_dict(start.get("descriptor")) or
                  _dict(_dict(checkpoint.get("identity")).get("descriptor")))
    kind = _name(descriptor.get("kind"))
    learned = kind in {"legacy_random_raw", "vq_niche"} or bool(kind and kind.startswith("pca"))
    if learned:
        status, detail = "frozen", "Recorded descriptor " + kind + "; embedder weights are frozen during search."
        if kind == "vq_niche":
            detail += " VQ niche bookkeeping can adapt separately."
    elif kind in {"code_length", "repeat_ranked_pool"}:
        status, detail = "disabled", "Actual recorded descriptor: " + kind + "; no learned embedding axis."
    else:
        status, detail = "unknown", "Actual learned descriptor was not recorded; requested embedding flags are insufficient evidence."
    return dict(id="code_embedding", label="Code embedding", status=status, detail=detail)


def _preset_checkpoint(checkpoint, latest_iteration):
    """Observed saved weights only; do not replay binary rewards or synthesize a policy."""
    state = _dict(checkpoint.get("preset_weights"))
    iteration = _integer(checkpoint.get("iteration_no"))
    return dict(available=bool(state), iteration=iteration,
                stale=latest_iteration > iteration if iteration is not None and latest_iteration is not None else None,
                version=_integer(state.get("version")), updates=_integer(state.get("updates")),
                log_weights=_numbers(state.get("log_weights")), prior=_numbers(state.get("prior")),
                learning_rate=_number(state.get("learning_rate")),
                exploration=_number(state.get("exploration")),
                max_importance_reward=_number(state.get("max_importance_reward")))


def learning_view(start, checkpoint, rows):
    """Project supplied records without executing policies or changing inputs.

    Caller must remove abandoned journal branches before invoking this function.
    Counts cover available iteration records, not unlogged attempts or prior runs.
    """
    start, checkpoint = _dict(start), _dict(checkpoint)
    if isinstance(start.get("config"), dict):
        config, config_source = start["config"], "run_start"
    elif isinstance(checkpoint.get("config"), dict):
        config, config_source = checkpoint["config"], "checkpoint"
    else:
        config, config_source = {}, None
    state = _dict(checkpoint.get("op_bandit"))
    events = state.get("events")
    if isinstance(events, dict):
        configured = {name for name in events if _name(name)}
        arms_known = True
    elif config_source is not None and "crossover" in config:
        configured = set(_BASE_ARMS) | ({"cross"} if config.get("crossover") is True else set())
        arms_known = True
    else:
        configured, arms_known = set(), False
    arms = {}

    def arm(name):
        if not name:
            return None
        if name not in arms:
            if len(arms) >= 32:
                return None
            arms[name] = dict(name=name, choices=0, executions=0, evaluated_count=0,
                             record_count=0, island_record_count=0, credited_updates=0,
                             known_credited_updates=0, unknown_credit_events=0,
                             cumulative_reward=None)
        return arms[name]

    for name in sorted(configured)[:32]:
        arm(name)
    history, rewards, decisions = deque(maxlen=HISTORY_LIMIT), deque(maxlen=HISTORY_LIMIT), deque(maxlen=DECISION_LIMIT)
    pending_controller, pending_refine = {}, set()
    complete_interval = False
    count = records = island_records = credited = unknown_credit = missing_rewards = decision_count = 0
    cumulative = latest_iteration = None
    numeric_stats = False
    normalization_events = capped_events = precision_filtered_channels = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        event = row.get("event")
        key = (_name(row.get("segment_id")), _integer(row.get("island")))
        if event == "run_start":
            pending_controller.clear()
            pending_refine.clear()
            complete_interval = True
        if event == "decision" and row.get("policy") in ("controller", "preset_weights"):
            decision_count += 1
            preset = row.get("policy") == "preset_weights"
            item = dict(iteration=None, iteration_before=_integer(row.get("iteration_no")),
                        event_seq=_integer(row.get("event_seq")), island=key[1],
                        source=row["policy"], adaptive=_bool(row.get("adaptive")) if preset else None,
                        mode=_name(row.get("action")), effective_mode=None,
                        plateau=_bool(row.get("plateau")),
                        distribution=_numbers(row.get("distribution" if preset else "mode_dist")),
                        propensity=_number(row.get("propensity")), phase=_integer(row.get("phase")))
            decisions.append(item)
            pending_controller[key] = item
        elif event == "decision" and row.get("policy") == "refine" and row.get("action") == "intensify":
            pending_refine.add(key)
        if event != "iteration":
            continue
        count += 1
        iteration = _integer(row.get("iteration_no"))
        if iteration is not None:
            latest_iteration = max(latest_iteration or 0, iteration)
        decision = pending_controller.pop(key, None)
        if decision is not None:
            decision["iteration"] = iteration
            decision["effective_mode"] = _name(row.get("effective_mode"))
        meta, raw_stats = _dict(row.get("meta")), _dict(row.get("op_stat"))
        executed = _name(row.get("op_used")) or _name(meta.get("op_used"))
        escalated = _bool(meta.get("escalated"))
        stats = _numbers(raw_stats)
        numeric_stats = numeric_stats or bool(stats)
        fixed = _name(raw_stats.get("fixed"))
        forced = True if fixed or raw_stats.get("idea_island") is True else False if stats else None
        trace = _dict(meta.get("validation_trace")).get("attempts")
        selected = _name(_dict(trace[0]).get("operator")) if isinstance(trace, list) and trace else None
        selected = _name(meta.get("op_requested")) or selected or fixed or ("idea" if raw_stats.get("idea_island") is True else None)
        if selected is None and escalated is False:
            selected = executed
        selected_arm, executed_arm = arm(selected), arm(executed)
        if selected_arm is not None:
            selected_arm["choices"] += 1
        evaluated = _number(row.get("child_score")) is not None or row.get("reason") == "eval_failed"
        reward = _number(row.get("r_norm"))
        normalization = _normalization(row.get("reward_normalization"))
        if normalization is not None:
            normalization_events += 1
            capped_events += normalization["cap_applied"] is True
            for channel, field in (("population", "d_pop"), ("island", "d_isl")):
                gain = _number(row.get(field))
                precision_filtered_channels += (gain is not None and gain > 0 and
                                                 normalization["channel_eligible"][channel] is False)
        missing_rewards += reward is None
        cumulative = _sum(cumulative, reward)
        pop_record, island_record = row.get("is_pop_event") is True, row.get("is_island_event") is True
        records += pop_record
        island_records += island_record
        # Recorded stats establish eligibility of that particular arm even when
        # old runs have no config. Excluded arms require a known full arm set.
        membership = executed in configured if arms_known else True if executed in stats else False if executed == "idea" else None
        credit = (False if meta.get("op_on_policy") is False or row.get("is_island_event") is False or row.get("reason") or escalated is True or membership is False
                  else True if island_record and escalated is False and membership is True and executed else None)
        credited += credit is True
        unknown_credit += credit is None
        if executed_arm is not None:
            executed_arm["executions"] += 1
            executed_arm["evaluated_count"] += evaluated
            executed_arm["record_count"] += pop_record
            executed_arm["island_record_count"] += island_record
            executed_arm["known_credited_updates"] += credit is True
            executed_arm["unknown_credit_events"] += credit is None
            executed_arm["credited_updates"] = (None if executed_arm["unknown_credit_events"]
                                                  else executed_arm["known_credited_updates"])
            executed_arm["cumulative_reward"] = _sum(executed_arm["cumulative_reward"], reward)
        refined = True if key in pending_refine else False if complete_interval else None
        pending_refine.discard(key)
        history.append(dict(iteration=iteration, island=key[1], operator=executed, selected_operator=selected,
                            selected_probability=_number(row.get("op_propensity")), reward=reward,
                            escalated=escalated, forced=forced, refine=refined, stats=stats,
                            credited=credit, on_policy=_bool(meta.get("op_on_policy")),
                            initial_operator=_name(meta.get("op_initial")),
                            fallback_reason=_name(meta.get("op_fallback_reason"))))
        rewards.append(dict(iteration=iteration, reward=reward, cumulative_reward=cumulative,
                            raw_reward=_number(row.get("r_raw")), normalization=normalization,
                            pop_gain=_number(row.get("d_pop")), island_gain=_number(row.get("d_isl")), operator=executed))
    components, source = _components(config, config_source is not None, checkpoint, numeric_stats)
    components.append(_embedding(start, checkpoint))
    operator_checkpoint, mode_bandit = _windows(checkpoint, latest_iteration)
    notes = [
        "Totals use available journal iterations. A population record and an island record are different events.",
        "Operator credit requires a non-escalated successful island record and a configured arm; forced idea is not an arm.",
        "Operator windows retain qualifying record rewards, not all attempts. Their value is the window maximum.",
        "Operator statistics are recorded before selection. Refine can bias diff without changing these raw statistics; no full probability distribution is reconstructed.",
        "Controller decisions are joined by event order, segment and island. Effective mode is shown only when explicitly recorded; overrides can separate a recorded mode from its original propensity.",
        "Mode-bandit windows come only from the checkpoint; failure rows do not contain enough information to replay exact mode credit.",
        "Observed normalized rewards are search signals, not training losses. No gradient-training telemetry is recorded here.",
    ]
    if count > HISTORY_LIMIT or decision_count > DECISION_LIMIT:
        notes.append("Charts retain the latest records only; earlier extrema can be omitted. Summary totals still include all supplied iterations.")
    if missing_rewards:
        notes.append("Missing rewards remain unknown; reward sums include only recorded finite observations.")
    if config.get("preset_selection") is True:
        notes.append("Preset distributions and propensities come from recorded selections. Saved log weights and update counts come only from the checkpoint; binary rewards and later weights are not reconstructed.")
    reward_state = _dict(checkpoint.get("reward"))
    current_normalization = (reward_state.get("schema") == "sciel-reward-state/2" and
                             reward_state.get("normalization_policy") == "ulp8-positive-median-cap1/1")
    normalization_detail = (
        "Recorded policy: each learning gain must exceed 8 ULPs of its score/baseline. "
        "Eligible gains use the previous positive median (cold-start scale 1), with reward capped at 1. "
        "Raw scores, gains and strict record flags are unchanged. This precision rule is not evidence of scientific equivalence."
        if current_normalization or normalization_events else
        "Normalization policy is not recorded here. Historical rewards are displayed exactly as saved.")
    return dict(schema="sciel-learning/1", config_source=config_source, components=components,
                reward_normalization=dict(detail=normalization_detail, recorded_events=normalization_events,
                                          capped_events=capped_events,
                                          precision_filtered_channels=precision_filtered_channels),
                summary=dict(iterations=count, record_events=records, island_record_events=island_records,
                             credited_operator_updates=None if unknown_credit else credited,
                             known_credited_operator_updates=credited, unknown_credit_events=unknown_credit,
                             cumulative_reward=cumulative, missing_reward_events=missing_rewards),
                operator=dict(arms=list(arms.values()), history=list(history), checkpoint=operator_checkpoint),
                controller=dict(source=source, history=list(decisions), mode_bandit=mode_bandit,
                                preset_weights=_preset_checkpoint(checkpoint, latest_iteration)),
                rewards=list(rewards), notes=notes, history_limit=HISTORY_LIMIT,
                retention=dict(strategy="latest", operator_total=count, operator_retained=len(history),
                               controller_total=decision_count, controller_retained=len(decisions), controller_limit=DECISION_LIMIT))
