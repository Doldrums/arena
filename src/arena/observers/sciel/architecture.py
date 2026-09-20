"""Recorded run architecture, without importing or applying engine defaults.

This describes the selected run, not the configuration of the installed engine.
Missing historical fields remain unknown, even where today's default is known.
"""
from __future__ import annotations


def _dict(value):
    return value if isinstance(value, dict) else {}


def start_protocol(start, checkpoint, rows):
    """Describe recorded initialization without substituting current defaults."""
    config = start.get("config")
    if not isinstance(config, dict):
        config = checkpoint.get("config")
    recorded = isinstance(config, dict)
    config = _dict(config)
    warm = config.get("warm_start")
    event = next((row for row in rows if row.get("event") == "decision"
        and row.get("policy") == "initialization" and row.get("action") == "warm_start"
        and row.get("schema") == "sciel-warm-start/1"), None)
    warm_config = isinstance(warm, dict) and warm.get("schema") == "sciel-warm-start/1"
    parent = _dict(event.get("parent")) if event else _dict(_dict(warm).get("parent"))
    measured_initialization = any(row.get("event") == "decision"
        and row.get("policy") == "initialization" and row.get("action") == "seed_program"
        and row.get("schema") == "sciel-initialization/1" for row in rows)
    if event or warm_config:
        kind, label = "warm_start", "Warm start"
    elif recorded and warm is None and ("warm_start" in config or measured_initialization):
        kind, label = "fresh", "Fresh start"
    else:
        kind, label = "unknown", "Start protocol not recorded"
    def identifier(value):
        return value[:256] if isinstance(value, str) and value.strip() else None
    return dict(kind=kind, label=label,
        source_run=identifier(parent.get("run_id")) if kind == "warm_start" else None,
        source_candidate=identifier(parent.get("program_id")) if kind == "warm_start" else None,
        portfolio_seed=config.get("portfolio_seed") if type(config.get("portfolio_seed")) is bool else None)


def architecture(start, checkpoint, rows):
    """Project saved configuration and runtime observations into UI sections."""
    if isinstance(start.get("config"), dict):
        config, source = start["config"], "run_start.config"
    elif isinstance(checkpoint.get("config"), dict):
        config, source = checkpoint["config"], "checkpoint.config"
    else:
        config, source = {}, "unavailable"

    def field(key, label, *, note=None, mapping=None, origin=None):
        current = config if mapping is None else mapping
        recorded = True
        for part in key.split("."):
            if not isinstance(current, dict) or part not in current:
                recorded, current = False, None
                break
            current = current[part]
        return dict(key=key, label=label, value=current, status="recorded" if recorded else "unknown",
                    source=(origin or source) + "." + key if recorded else None, note=note)

    def cfg_fields(specs):
        return [field(key, label) for key, label in specs]

    def recorded(key, label, value, origin, note=None):
        return dict(key=key, label=label, value=value, status="recorded", source=origin, note=note)

    llm = _dict(config.get("llm"))
    model_pool = field("llm.models", "Generation model pool")
    if isinstance(llm.get("models"), list):
        weights = llm.get("weights")
        model_pool = recorded("generation_models", "Generation model pool", [
            dict(model=model, weight=weights[index] if isinstance(weights, list) and index < len(weights) else None)
            for index, model in enumerate(llm["models"])], source + ".llm",
            "Weights are recorded routing weights; zero-weight models remain visible. Missing weights are unknown.")
    model_fields = [model_pool, field("research.model", "Dedicated conclusion / reflection model"),
                    field("models", "Models reported by engine", mapping=start, origin="run_start")]
    for kind, phases in (("generation", {"hypothesis"}), ("auxiliary", {"aux_start", "aux_result"})):
        observed = []
        for row in rows:
            if row.get("event") == "research" and row.get("phase") in phases:
                value = row.get("model") or _dict(row.get("evidence")).get("model")
                if isinstance(value, str) and value not in observed:
                    observed.append(value)
            if kind == "generation" and row.get("event") == "iteration":
                value = row.get("model_used")
                if isinstance(value, str) and value not in observed:
                    observed.append(value)
        model_fields.append(recorded("observed_" + kind, "Observed " + kind + " models", observed,
                                     "journal", "Only explicit model IDs in available journal records."))
    model_fields += cfg_fields([("llm.mock", "Mock provider"), ("llm.max_tokens", "Generation token limit"),
        ("llm.temperature", "LLM temperature"), ("llm.timeout", "Provider timeout (seconds)"),
        ("llm.max_retries", "Provider request attempts"), ("llm.cost_reporting", "Cost reporting method")])

    descriptor = field("descriptor", "Actual descriptor", mapping=start, origin="run_start")
    if descriptor["status"] == "unknown":
        descriptor = field("descriptor", "Actual descriptor", mapping=_dict(checkpoint.get("identity")),
                           origin="checkpoint.identity")
    descriptor["note"] = "Actual recorded descriptor takes precedence over requested embedding settings; fallback is not inferred."
    descriptor_fields = [descriptor] + cfg_fields([
        ("embed_grid", "Requested embedding grid"), ("embed_grid_path", "Requested embedding model"),
        ("embed_axis_path", "Requested behavior axis"), ("embed_niche", "Requested learned niches"),
        ("embed_niche_path", "Requested niche model"), ("grid_bins", "Grid bins")])

    search_fields = cfg_fields([
        ("selection_policy", "Parent selection policy"), ("selection_floor", "Selection probability floor"),
        ("selection_temperature", "Selection temperature"), ("selection_cap", "Selection visit cap"),
        ("op_fixed", "Fixed generation operator"), ("op_temperature", "Operator sampling temperature"),
        ("op_floor", "Operator probability floor"), ("op_window", "Operator reward window"),
        ("container", "Population container"), ("policy", "Adaptive search policy"),
        ("crossover", "Crossover"), ("three_head", "Three-head selection"),
        ("preset_selection", "Preset selection"), ("preset_adaptive", "Adaptive presets")])
    search_fields += [field("candidate_novelty.enabled", "Whole-run candidate novelty"),
        field("candidate_novelty.max_resamples", "Maximum replacement code requests"),
        field("candidate_novelty.neighbors", "Recorded nearest code neighbors",
              note="SHA256 → AST → code embedding after repair/graft; embedding similarity is advisory, not behavioral equivalence.")]
    population_fields = cfg_fields([
        ("num_islands", "Initial islands"), ("pop_cap", "Population capacity"),
        ("archive_size", "Archive capacity"), ("schedule_policy", "Island scheduler"),
        ("milestone_fracs", "Successive-halving milestones"), ("sh_min_fair_evals", "SH minimum fair evaluations"),
        ("dynamic_islands", "Dynamic island creation"), ("max_islands", "Maximum islands"),
        ("spawn_stall", "Spawn after stalled evaluations"), ("portfolio_seed", "Portfolio seeding"),
        ("idea_island", "Idea island"), ("refine_stall", "Refine after stalled evaluations"),
        ("refine_elite_frac", "Refine elite threshold"), ("op_intensify_boost", "Refine operator boost")])
    research_fields = cfg_fields([
        ("research.enabled", "G / C / R research loop"), ("research.inject_lessons", "Inject lessons into generation"),
        ("research.reflection_interval", "Reflect every completed experiments"),
        ("research.max_aux_calls", "Conclusion / reflection call budget"),
        ("research.retrieve_k", "Retrieved lessons per generation"), ("research.max_lessons", "Lesson capacity"),
        ("research.max_experiments", "Experiment history capacity"), ("research.max_fragments", "Code fragment capacity"),
        ("research.lesson_selection", "Lesson retrieval policy"),
        ("research.structured_auxiliary", "Structured conclusion / reflection output"),
        ("research.compact_lesson_memory", "Compact lesson decision cards"),
        ("research.conclusion_source_refs", "Conclusion claim / source references"),
        ("research.conclusion_repair_attempts", "Maximum conclusion format corrections"),
        ("research.comparison_reviews", "Comparison reviews"),
        ("research.comparison_review_version", "Comparison review version"),
        ("research.comparison_review_text", "Inject comparison-review text"),
        ("research.restart_predictions", "Restart-scale predictions"),
        ("research.batch_only_lessons", "Lessons restricted to repeat batches")])
    evaluation_fields = cfg_fields([
        ("budget", "Search evaluation budget"), ("max_iterations", "Iteration cap"),
        ("checkpoint_interval", "Checkpoint every iterations"),
        ("inflight_cap", "Maximum in-flight work"), ("dup_cap", "Duplicate-attempt cap"),
        ("backstop_k", "Failure backstop"), ("confirm_records", "Confirm record candidates"),
        ("repeat_promotion", "Output-only repeat promotion"), ("repeat_population", "Repeat-based population selection")])
    evaluation_fields.insert(2, field("schedule_horizon", "Scheduling horizon (evaluations)",
        note="Finite horizon for successive-halving milestones and schedule progress only; this does not stop the run."))
    evaluation_fields += [field(key, label, mapping=start, origin="run_start") for key, label in
        [("tiers", "Recorded evaluation tiers"), ("known_best", "Task reference score"),
         ("evaluator", "Recorded evaluator limits and sandbox")]]
    execution_fields = cfg_fields([
        ('parallel_search.enabled', 'Parallel waves enabled'),
        ('parallel_search.workers', 'Concurrent jobs per run'),
        ('parallel_search.host_llm_slots', 'Shared host LLM slots'),
        ('parallel_search.provider_slots', 'Shared provider slots'),
        ('parallel_search.host_evaluator_slots', 'Shared host evaluator slots'),
        ('parallel_search.max_inflight_per_island', 'Maximum in-flight jobs per island'),
        ('parallel_search.max_inflight_per_parent', 'Maximum in-flight jobs per parent')])
    if _dict(config.get('parallel_search')).get('enabled') is True:
        execution_fields.append(recorded('feedback_timing', 'Research feedback timing',
            'When enabled: C after the generation wave; ordered admission; due R before the next wave.',
            source + '.parallel_search.enabled',
            'Delayed wave feedback is a distinct execution mode. Slot counts are limits, not measured utilization.'))
    optional_fields = cfg_fields([
        ('research_tools.enabled', 'Executable research tools'),
        ('research_tools.share_between_islands', 'Share published tools between islands'),
        ('research_tools.interval', 'Tool episode cadence per island opportunity'),
        ('research_tools.max_requests', 'Model request / repair limit'),
        ('research_tools.max_scientific_steps', 'Maximum scientific steps per research opportunity'),
        ('research_tools.trigger_sources', 'Recorded research-cell trigger signals'),
        ('research_tools.max_active_cells', 'Concurrent research-cell limit (not lifetime count)'),
        ('research_tools.limits', 'Isolated tool resource limits'),
        ("idea_two_stage", "Two-stage idea generation"), ("idea_card_selection", "Idea-card selection"),
        ("idea_two_stage.card_repair_attempts", "Maximum idea-card format corrections"),
        ("circle_generation", "Circle generation protocol"), ("circle_intervention", "Circle intervention protocol"),
        ("bet_enabled", "Legacy bets"), ("c2_event_bets", "Legacy C2 event bets"),
        ("kb_free", "Legacy free knowledge"), ("plateau_shadow", "Plateau shadow monitoring")])
    protocol = start_protocol(start, checkpoint, rows)
    initialization_fields = [dict(key="start_protocol", label="Start protocol", value=protocol["label"],
        status="unknown" if protocol["kind"] == "unknown" else "recorded",
        source="recorded_initialization" if protocol["kind"] != "unknown" else None,
        note="Warm start transfers a prior candidate source for a fresh evaluation; it does not inherit its score or knowledge.")]
    initialization_fields += [dict(key=key, label=label, value=protocol[key],
        status="recorded" if protocol[key] is not None else "unknown",
        source="warm_start.parent" if protocol[key] is not None else None, note=None)
        for key, label in [("source_run", "Source run"), ("source_candidate", "Source candidate")]]
    initialization_fields.append(field("portfolio_seed", "Portfolio seeding"))

    research = _dict(config.get("research"))
    research_state = "enabled" if research.get("enabled") is True else "disabled" if research.get("enabled") is False else "unknown"
    retrieval_state = research_state
    if research_state == "enabled":
        retrieval_state = "enabled" if research.get("inject_lessons") is True else "disabled" if research.get("inject_lessons") is False else "unknown"
    core_state = "enabled" if source != "unavailable" else "unknown"
    stages = [dict(id=ident, label=label, status=status, description=description) for ident, label, status, description in [
        ("selection", "Select parent", core_state, "Select a population member and generation operator."),
        ("retrieval", "Retrieve lessons", retrieval_state, "Retrieve admitted research knowledge when lesson injection is enabled."),
        ("generation", "G · Generate", core_state, "Generate a candidate; structured hypotheses belong to the research loop when enabled."),
        ("evaluation", "Evaluate", core_state, "Run the recorded task evaluation stages and persist the outcome."),
        ("admission", "Update population", core_state, "Apply the configured population admission and diversity rules."),
        ("conclusion", "C · Conclude", research_state, "Interpret the completed experiment and admit accepted lessons."),
        ("reflection", "R · Reflect", research_state, "Revisit accumulated experiments at the recorded reflection cadence.")]]
    edges = [dict(from_=a, to=b, label=label) for a, b, label in [
        ("selection", "generation", "parent"), ("retrieval", "generation", "knowledge"),
        ("generation", "evaluation", "candidate"), ("evaluation", "admission", "measured outcome"),
        ("admission", "selection", "population"), ("evaluation", "conclusion", "experiment evidence"),
        ("conclusion", "reflection", "experiment history"), ("conclusion", "retrieval", "accepted lessons"),
        ("reflection", "retrieval", "revised knowledge")]]
    for edge in edges:
        edge["from"] = edge.pop("from_")
    warnings = []
    if source == "unavailable":
        warnings.append("No resolved configuration was recorded; current engine defaults are not substituted.")
    if descriptor["status"] == "unknown":
        warnings.append("The actual descriptor is not recorded; requested embedding options do not establish what ran.")
    if "evaluator" not in start:
        warnings.append("Ordinary evaluator limits and sandbox are not recorded in this run_start.")
    from .architecture_graph import architecture_graph
    return dict(schema="sciel-architecture/1", source=source, recorded=source != "unavailable",
        summary="Architecture of this recorded run. Unknown fields are not reconstructed from today's defaults.",
        stages=stages, edges=edges, sections=[dict(id=ident, title=title, fields=fields) for ident, title, fields in [
            ("initialization", "Initialization and provenance", initialization_fields),
            ("models", "Models and request budgets", model_fields), ("search", "Selection, operators and container", search_fields),
            ('execution', 'Execution and shared resource limits', execution_fields),
            ("population", "Islands and adaptation", population_fields), ("research", "Research and knowledge", research_fields),
            ("evaluation", "Evaluation and repeat budgets", evaluation_fields), ("descriptor", "Diversity descriptor", descriptor_fields),
            ("optional", "Optional modules", optional_fields)]], warnings=warnings,
        graph=architecture_graph(start, checkpoint, rows, protocol=protocol))
