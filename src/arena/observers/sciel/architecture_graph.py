"""Diagram of recorded search wiring; no engine imports or default application."""
from __future__ import annotations

import math
from .research_tools import EVENT_SCHEMA


def _dict(value):
    return value if isinstance(value, dict) else {}


def _text(value):
    return value[:200] if isinstance(value, str) and value.strip() else None


def _number(value):
    if type(value) not in (int, float):
        return None
    try:
        return value if math.isfinite(value) else None
    except OverflowError:
        return None


def architecture_graph(start, checkpoint, rows, *, protocol=None):
    """Show configured/evidenced mechanisms, distinguishing frozen and online state."""
    start, checkpoint, protocol = _dict(start), _dict(checkpoint), _dict(protocol)
    config = start.get("config")
    if not isinstance(config, dict):
        config = _dict(checkpoint.get("config"))
    policy, research = _dict(config.get("policy")), _dict(config.get("research"))
    container = _dict(config.get("container"))
    novelty = _dict(config.get("candidate_novelty"))
    parallel = _dict(config.get('parallel_search'))
    contract = _text(start.get("engine_contract")) or _text(_dict(checkpoint.get("identity")).get("engine_contract"))
    preset_timing = ("before" if contract in {"espalier-3.3", "espalier-3.4", "espalier-3.5", "espalier-3.6", "espalier-3.7", "espalier-3.8", "espalier-3.9", "espalier-3.10", "espalier-3.11", "espalier-3.12", "espalier-3.13", "espalier-3.14", "espalier-3.15", "espalier-3.16", "espalier-3.17", "espalier-3.18", "espalier-3.19", "espalier-3.20", "espalier-3.21", "espalier-3.22", "espalier-3.23", "espalier-3.24", "espalier-3.25", "espalier-3.26", "espalier-3.27", "espalier-3.28", "espalier-3.29", "espalier-3.30", "espalier-3.31", "espalier-3.32"} else
                     "after" if contract in {"espalier-3", "espalier-3.1", "espalier-3.2"} else "unknown")
    descriptor = (_dict(start.get("descriptor")) or
                  _dict(_dict(checkpoint.get("identity")).get("descriptor")))
    observed_policies, observed_ops, observed_research = set(), set(), False
    for row in rows:
        if not isinstance(row, dict):
            continue
        if row.get("event") == "decision" and _text(row.get("policy")):
            observed_policies.add(row["policy"])
        if row.get("event") == "iteration" and _text(row.get("op_used")):
            observed_ops.add(row["op_used"])
        if row.get("event") == "research":
            observed_research = True
    nodes, edges, inactive, notes = [], [], [], []
    core_status = "enabled" if config or observed_ops else "unknown"

    def node(ident, label, subtitle, kind="core", status="enabled", detail="", features=(), phase=None):
        item = dict(id=ident, label=label, subtitle=subtitle, kind=kind, status=status,
                    detail=detail, features=list(features))
        if phase is not None:
            item["phase"] = phase
        nodes.append(item)

    def edge(source, target, label, kind="flow"):
        edges.append({"from": source, "to": target, "label": label, "kind": kind})

    def off(label, detail, status="disabled"):
        inactive.append(dict(label=label, detail=detail, status=status))

    fixed = _text(config.get("op_fixed"))
    repeated = _dict(config.get("repeat_population")).get("enabled") is True
    scheduler_features = []
    if parallel.get('enabled') is True:
        scheduler_features.append('Parallel waves')
    if protocol.get("kind") in ("fresh", "warm_start"):
        scheduler_features.append(_text(protocol.get("label")) or "Recorded initialization")
    if config.get("portfolio_seed") is True:
        scheduler_features.append("Portfolio starts")
    if config.get("dynamic_islands") is True:
        scheduler_features.append("Dynamic islands")
    if config.get("budget", "missing") is None:
        scheduler_features.append("Unlimited search")
    scheduler_detail = "Recorded scheduler: " + (_text(config.get("schedule_policy")) or "unknown") + "."
    if config.get("portfolio_seed") is True:
        scheduler_detail += " Initialization requests constructive, local-optimizer and global-stochastic programs; these are instructions, not guaranteed diversity."
    if config.get("dynamic_islands") is True:
        scheduler_detail += " Stalled search can spawn another island, up to the recorded maximum " + str(config.get("max_islands", "unknown")) + "."
    if config.get("budget", "missing") is None:
        scheduler_detail += " The scheduling horizon controls milestones, not termination."
    node("scheduler", "Island scheduler", _text(config.get("schedule_policy")) or "Scheduler not recorded",
         status=core_status, detail=scheduler_detail, features=scheduler_features)

    selection = _text(config.get("selection_policy"))
    parent_kind, parent_status = "rule", "enabled" if selection else "unknown"
    if container.get("selection") == "centres":
        parent_label, parent_detail = "Centre parent selection", "Select a centre, then a quality-weighted parent; bypasses the configured parent kernel."
    elif selection == "novelty_chain":
        parent_label, parent_detail = "Parent selection", "Score and visit-count sampling, with any effective mode tilt. Recorded reward sums do not drive this kernel."
    elif selection in {"ucb1", "ucb_sw"}:
        parent_kind = "online"
        parent_label, parent_detail = "Parent selection", "Reward-updated UCB indices are sampled through a distribution; this is not an argmax or neural training."
    else:
        parent_label, parent_detail = "Parent selection", "Uses the recorded selection policy; missing configuration remains unknown."
    node("parent", parent_label, "Centre sampling" if container.get("selection") == "centres" else selection or "Policy not recorded",
         kind=parent_kind, status=parent_status, detail=parent_detail)
    operator_features = []
    if config.get("crossover") is True:
        operator_features.append("Crossover available" if not fixed else "Crossover configured; fixed operator wins")
    node("operator", "Generation operator", "Fixed: " + fixed if fixed else "Choose an edit strategy",
         status=core_status, detail="Operator selection precedes generation. Retry escalation may execute a different operator; idea-island routing can force idea generation.", features=operator_features)
    research_on = research.get("enabled") is True or ("enabled" not in research and observed_research)
    models = [_text(value) for value in _dict(config.get("llm")).get("models", [])
              if _text(value)] if isinstance(_dict(config.get("llm")).get("models"), list) else []
    node("generation", "G · Generate" if research_on else "Generate program", ", ".join(models[:3]) or "Model not recorded",
         status=core_status, detail="Generate a candidate program and preserve its required entry points." +
         (" Full research also requests a pre-evaluation hypothesis and forecast." if research_on else ""), phase="generating")
    output_repeats = _dict(config.get("candidate_novelty")).get("output_repeats") is True
    evaluator = _dict(start.get("evaluator"))
    node("evaluation", "Evaluate candidate", _text(evaluator.get("backend")) or "Task evaluator",
         status=core_status, detail="Run task validity and scoring stages; failed evaluations are distinct from measured zero scores. Limits and isolation follow the recorded evaluator." +
         (" Exact recorded-output repeats return to generation before population admission, sharing at most two extra requests with source novelty. Equal scores alone do not trigger rejection." if output_repeats else ""),
         features=["Exact output repeat retries"] if output_repeats else [], phase="evaluating")
    storage = _text(container.get("kind"))
    population_label = {"legacy": "MAP-Elites + archive", "grid": "MAP-Elites population",
                        "pool": "Program pool", "pool_novelty": "Novelty-gated pool",
                        "cvt": "CVT population", "vq": "VQ population",
                        "annealed": "Annealed population"}.get(storage, "Population")
    population_subtitle = ("Islands · niche × score cells" if descriptor.get("kind") == "vq_niche"
                           else "Islands · descriptor × score cells") if storage == "legacy" else storage or "Container not recorded"
    population_detail = "Admit evaluated programs under recorded retention and diversity rules. Population/island best scores supply the next decision's baseline."
    if storage == "legacy":
        population_detail += " MAP-Elites protects cell elites and keeps a score-ranked archive. VQ, when active, replaces the niche axis; it does not remove MAP-Elites or the archive."
    node("population", population_label, population_subtitle,
         status=core_status, detail=population_detail,
         features=(["Repeat-ranked pool"] if repeated else []) +
         ([str(config["num_islands"]) + " initial islands"] if type(config.get("num_islands")) is int else []))
    for a, b, label in [("scheduler", "parent", "Island"), ("parent", "operator", "Parent"),
                        ("operator", "generation", "Strategy"),
                        ("evaluation", "population", "Valid score"), ("population", "parent", "Retained programs")]:
        edge(a, b, label)
    if novelty.get("enabled") is True:
        retries = novelty.get("max_resamples")
        limit = str(retries) if type(retries) is int and 0 <= retries <= 2 else "unrecorded"
        node("novelty", "Candidate novelty", "SHA256 → AST → code embedding", kind="rule",
             detail="After repair and entry-point grafting, compare the final source against whole-run history, including evicted islands. Exact-source and structural-AST duplicates are rejected; embedding similarity is advisory and does not prove equivalent behavior. Failed prior evaluations may be remeasured, separately from new mutations. At most " + limit + " replacement code requests; each paid attempt is retained.",
             features=["Whole-run checkpointed history", "Up to " + limit + " resamples", "Similarity is advisory"])
        edge("generation", "novelty", "Repaired / grafted candidate")
        edge("novelty", "evaluation", "New source or eligible remeasurement")
        edge("novelty", "generation", "Rejected duplicate · bounded code resample", "control")
    else:
        edge("generation", "evaluation", "Candidate")
        if novelty.get("enabled") is False:
            off("Candidate novelty", "Whole-run source registry is disabled in this recorded configuration.")

    preset = config.get("preset_selection") is True or "preset_weights" in observed_policies
    adaptive = config.get("preset_adaptive")
    bandit = policy.get("mode_bandit") is True
    mlp = policy.get("mode_source") == "mlp"
    three = config.get("three_head") is True
    mode_source, mode_feedback = None, None
    if three:
        mode_source = "Frozen promise override"
        node("mode_policy", "Three-head override", "Frozen population model", kind="frozen",
             detail="A returned promise tilt overrides the prior mode and marks it exploit. If the head supplies no tilt, the underlying recorded controller remains in use. No head is trained during this run.",
             features=["Conditional parent override"])
        if bandit:
            off("Underlying mode bandit", "It may accumulate shadow updates; its chosen tilt is replaced whenever the promise head supplies one.", "shadow")
    elif preset:
        mode_source = "Adaptive preset weights" if adaptive is True else "Static preset weights" if adaptive is False else "Preset adaptation not recorded"
        mode_feedback = "preset" if adaptive is True else None
        node("mode_policy", "Preset-weight bandit" if adaptive is True else "Preset weights", "Base / elite / uniform parents",
             kind="online" if adaptive is True else "rule", status="unknown" if type(adaptive) is not bool else "enabled",
             detail="Sample a parent-selection preset. Adaptive weights use binary population improvement divided by the chosen propensity, with clipped credit and explicit exploration. " +
             ("After the search result, before conclusion/reflection." if preset_timing == "before" else
              "This recorded engine updates only after research completes." if preset_timing == "after" else
              "Update timing relative to conclusion/reflection is not established by the recorded engine contract."),
             features=["Binary population-record reward"] if adaptive is True else [])
        if bandit or mlp:
            off("Nominal mode controller", "Preset sampling replaces its mode and tilt.", "shadow")
    elif policy.get("enabled") is False:
        off("Mode controller", "Disabled in this run's recorded configuration.")
        if bandit:
            off("Mode bandit", "Configured estimator is not choosing modes while the controller is disabled.", "shadow")
    elif policy.get("enabled") is not True:
        node("mode_policy", "Mode policy", "Activation not recorded", kind="rule", status="unknown",
             detail="A configured policy name or saved estimator alone does not establish that it controlled selection.")
    elif mlp:
        mode_source = "Frozen return-conditioned MLP"
        node("mode_policy", "Mode MLP", "Offline weights · frozen inference", kind="frozen",
             detail="Return-conditioned inference blends into the base mode mixture. No in-run gradient updates; any enabled plateau rule takes precedence.")
        if bandit:
            off("Mode bandit", "The MLP takes precedence; the estimator can collect shadow updates.", "shadow")
    elif bandit:
        mode_source, mode_feedback = "Online mode bandit", "mode"
        node("mode_policy", "Contextual mode bandit", "Per scheduling phase · mean reward", kind="online",
             detail="Learns from all on-policy attempts, including zero for failed/no-child attempts. Mean normalized reward and a prior determine the mode distribution. Warmup can turn exploit into effective base.",
             features=["Base / exploit / explore"] + (["Plateau override"] if policy.get("plateau_shift") is True else []))
    elif policy.get("enabled") is True and isinstance(policy.get("base_mix"), dict):
        mode_source = "Static mode mixture"
        node("mode_policy", "Static mode controller", "Recorded mixture" + (" + plateau rules" if policy.get("plateau_shift") is True else ""), kind="rule",
             detail="Samples the recorded base mixture; configured plateau rules may temporarily substitute another mixture. This is not online policy learning.",
             features=["Elite/uniform parent tilt"])
    else:
        node("mode_policy", "Mode policy", "Source not recorded", kind="rule", status="unknown",
             detail="No effective mode source can be established from the available configuration.")
    if any(item["id"] == "mode_policy" for item in nodes):
        edge("mode_policy", "parent", "Parent-distribution tilt", "control")

    op_known = bool(_dict(checkpoint.get("op_bandit"))) or any(key in config for key in ("op_temperature", "op_window"))
    if fixed or repeated:
        off("Operator-bandit sampling", "Bypassed by the fixed/specialized operator path; stored windows alone do not prove it chose an operator.", "shadow")
    else:
        node("operator_bandit", "Operator bandit", "Window maximum · sampled arms", kind="online",
             status="enabled" if op_known else "unknown",
             detail="Samples diff, full rewrite, optional crossover and repair after a fresh failure. Only qualifying non-escalated island records update the arm's reward window.",
             features=(["Crossover arm"] if config.get("crossover") is True else []))
        edge("operator_bandit", "operator", "Operator probabilities", "control")
    refine = _number(config.get("refine_stall"))
    if refine is not None and not fixed and not repeated:
        node("refine", "Refine on stall", "Rule-based intensification", kind="rule",
             detail="For a stalled competitive parent, boost diff and request deeper refinement. Skipped on forced operators and the idea island.",
             features=["Stall threshold: " + str(refine)])
        edge("refine", "operator", "Bias diff", "control")
        edge("refine", "generation", "Refinement directive", "control")
    elif fixed:
        off("Refinement bias", "Forced operators bypass refinement.")
    if config.get("plateau_shadow") is True or policy.get("plateau_shadow") is True:
        off("Plateau diagnostics", "Shadow monitoring records signals; only an enabled plateau_shift changes the mode distribution.", "shadow")

    idea_on = fixed == "idea" or (not fixed and config.get("idea_island") is True) or "idea" in observed_ops
    if idea_on:
        idea_config = _dict(config.get("idea_two_stage"))
        two_stage = idea_config.get("enabled") is True
        card_repair = two_stage and type(idea_config.get("card_repair_attempts")) is int and idea_config["card_repair_attempts"] == 1
        node("ideas", "Two-stage ideas" if two_stage else "Idea island", "Strategy card → program" if two_stage else "Forced idea operator", kind="rule",
             detail="The idea route overrides ordinary operator sampling on its assigned island." +
             (" A separate model call proposes a structured card; a second implements that fixed card." if two_stage else " One generation request explores a strategy-level change.") +
             (" An invalid returned card may receive one paid format correction; only a valid card proceeds to code. This is not a retry of an unknown provider request." if card_repair else ""),
             features=(["Extra card-generation call"] if two_stage else []) +
                      (["Up to 1 card correction"] if card_repair else []))
        edge("ideas", "operator", "Force idea route", "control")
        edge("ideas", "generation", "Card then code" if two_stage else "Idea prompt", "control")
    elif config.get("idea_island") is False:
        off("Idea island", "Disabled in the recorded configuration.")

    kind = _text(descriptor.get("kind"))
    if storage in {"cvt", "vq", "annealed"} and kind:
        node("descriptor", "Embedding geometry", str(container["kind"]), kind="frozen",
             detail="The container receives frozen embedding vectors directly. A recorded fitted PCA axis is not the cell assignment in this geometric-container path.",
             features=["Frozen vectors", "Container geometry"])
        edge("descriptor", "population", "Geometry inputs", "control")
    elif kind == "vq_niche":
        node("descriptor", "VQ niches", "Frozen embedder · adaptive codebook", kind="online",
             detail="Actual recorded VQ niche assignment replaces the fitted PCA axis. The codebook adapts during search; embedder weights remain frozen.",
             features=["Recorded VQ representation", "Frozen embedder " + (_text(descriptor.get("embed_sha")) or "hash unrecorded")])
        edge("descriptor", "population", "Niche assignment", "control")
    elif kind and (kind.startswith("pca") or kind == "legacy_random_raw"):
        node("descriptor", "Learned descriptor", kind, kind="frozen",
             detail="The actual recorded frozen embedding and behavior axis determine population cells. No in-run model training.", features=["Frozen representation"])
        edge("descriptor", "population", "Diversity cells", "control")
    elif kind in {"code_length", "repeat_ranked_pool"}:
        off("Learned descriptor", "Actual representation is " + kind + "; requested embedding paths do not establish an active model.")
    else:
        node("descriptor", "Diversity descriptor", "Actual representation not recorded", kind="rule", status="unknown",
             detail="Requested embedding flags and paths are insufficient evidence that a model was loaded.")
        edge("descriptor", "population", "Representation unknown", "control")

    node("reward", "Search feedback", "Measured outcomes → search updates", kind="rule", status="unknown" if repeated else core_status,
         detail="Ordinary reward combines nonnegative weighted gains over pre-step population/island best and divides by the prior positive-jump median. Presets use a separate binary population-record reward. Improving a weak parent can yield no record reward; none is an LLM training loss.")
    edge("evaluation", "reward", "Measured outcome", "reward")
    if any(item["id"] == "operator_bandit" for item in nodes):
        edge("reward", "operator_bandit", "Non-escalated island records only", "reward")
    if mode_feedback == "mode":
        edge("reward", "mode_policy", "All on-policy attempts · failures = 0", "reward")
        notes.append("Plateau overrides use a separate mode mixture. Recorded effective modes can differ after warmup gating; the diagram does not verify individual credit assignments.")
    elif mode_feedback == "preset":
        timing = "before C/R" if preset_timing == "before" else "after C/R" if preset_timing == "after" else "timing not recorded"
        edge("reward", "mode_policy", "Binary population record · " + timing, "reward")
        notes.append("Preset credit is committed after the search result and before conclusion/reflection." if preset_timing == "before" else
                     "This historical engine waits for research completion; a stopped conclusion can leave an observed iteration without a preset update." if preset_timing == "after" else
                     "Preset-update timing is not inferred from the installed engine; the recorded contract is missing or unrecognized.")
    if parent_kind == "online":
        edge("reward", "parent", "Parent reward statistics", "reward")

    if research_on:
        selection_mode = _text(_dict(research.get("lesson_selection")).get("mode"))
        compact = research.get("compact_lesson_memory") is True
        source_refs = research.get("conclusion_source_refs") is True
        conclusion_repair = type(research.get("conclusion_repair_attempts")) is int and research["conclusion_repair_attempts"] == 1
        node("memory", "Research memory", "Compact evidence cards" if compact else selection_mode or "Recorded lesson retrieval", kind="knowledge",
             detail="Stores recorded experiment evidence independently of conclusion acceptance, plus admitted lessons and fragments. Retrieved knowledge supplements generation prompts; it does not update LLM weights." +
             (" Compact decision cards bound shown source observations and advice exposures, with explicit omissions and hash-bound evidence references; full stored evidence is retained separately. Recorded admission still determines actual prompt delivery." if compact else ""),
             features=(["Guarded source diversity"] if selection_mode == "source_diverse_guarded" else []) +
             (["Lesson injection"] if research.get("inject_lessons") is True else []) +
             (["Compact lesson memory"] if compact else []))
        node("conclusion", "C · Conclusion", "Reference-bound mechanism review" if source_refs else "Evidence and mechanism review", kind="knowledge", phase="research",
             detail="Compare signed child-minus-measured-parent delta with the forecast, then review the mechanism. This parent delta differs from the nonnegative record reward used by search bandits. Structural and evidence checks gate lessons; model text never replaces measured fitness." +
             (" The model selects host-prepared claim and source references; the host resolves exact text and checks binding. This does not prove causal effects or complete edit coverage." if source_refs else "") +
             (" A complete invalid response may receive at most one paid format correction within the auxiliary-call budget; scheduling a correction does not establish that a call occurred." if conclusion_repair else ""),
             features=(["Host-bound source references"] if source_refs else []) +
                      (["Up to 1 format correction"] if conclusion_repair else []))
        edge("evaluation", "conclusion", "Parent delta / forecast verdict", "knowledge")
        edge("evaluation", "memory", "Recorded outcomes / evidence", "knowledge")
        edge("conclusion", "memory", "Accepted lessons", "knowledge")
        if research.get("inject_lessons") is True:
            edge("memory", "generation", "Retrieved lessons / evidence", "knowledge")
        else:
            off("Lesson injection", "Disabled or not recorded; memory storage alone does not establish prompt delivery.",
                "disabled" if research.get("inject_lessons") is False else "unknown")
        interval = _number(research.get("reflection_interval"))
        if interval != 0:
            node("reflection", "R · Reflection", "Every " + str(interval) + " outcomes" if interval is not None else "Cadence not recorded",
                 kind="knowledge", status="enabled" if interval is not None else "unknown", phase="research",
                 detail="Review accumulated experiment evidence, including experiments whose conclusions were rejected, and revise admitted knowledge under validation. Reflection does not require every conclusion to succeed; no gradient training.")
            edge("memory", "reflection", "History + lessons", "knowledge")
            edge("reflection", "memory", "Validated revisions", "knowledge")
        else:
            off("Reflection", "Recorded reflection interval is zero.")
    elif research.get("enabled") is False:
        off("G / C / R research", "Full research is disabled; no full-research conclusion or reflection path is shown.")
    else:
        notes.append("Full-research configuration is missing; conclusion, reflection and lesson-delivery modules are not inferred.")
    if not config:
        notes.append("No resolved configuration is available. Current engine defaults are not substituted.")
    tools = _dict(config.get('research_tools'))
    independent = contract == 'espalier-3.32' and tools.get('independent_research') is True
    proactive_every = tools.get('proactive_every_attempts')
    proactive = (tools.get('enabled') is True and type(proactive_every) is int
                 and proactive_every > 0)
    tool_events = [row for row in rows if row.get('event') == 'research_tool' and row.get('schema') == EVENT_SCHEMA]
    if tools.get('enabled') is True or tool_events:
        published = {row.get('tool_id') for row in tool_events if row.get('phase') == 'published'}
        executed = {row.get('invocation_id') for row in tool_events if row.get('phase') == 'invocation_result' and row.get('dispatch_status') == 'invoked'}
        node('tool_library', 'Island tool library' if tools.get('share_between_islands') is False else 'Shared tool library', 'Immutable executable versions', kind='knowledge',
             detail=('Cross-island sharing is explicitly disabled. ' if tools.get('share_between_islands') is False else '') + 'Islands can author executable tools and publish versions after a successful contract trial. Published tools become visible at the next wave within their recorded scope. Availability does not establish use by another island. This library supplements the existing population; native Programs, hypotheses and lessons retain their own records.',
             features=[str(len(published)) + ' published versions recorded'])
        node('tool_execution', 'Isolated tool calls', 'Saved experiment receipts' if independent else 'Receipts before candidate generation', kind='rule',
             detail='Actual invocations retain exact inputs, output, dispatch status and resource receipts. Tool results can be prepared in the generation Snapshot; context_prepared alone is not proof of prompt delivery. Child receipt links identify consumed executions, not causal utility or reward credit. These are tool trials, not native task evaluations.',
             features=[str(len(executed)) + ' executions recorded'])
        if not independent:
            edge('generation', 'tool_library', 'Author / revise a tool before candidate generation', 'control')
        edge('tool_library', 'tool_execution', 'Explicit version invocation', 'flow')
        edge('tool_execution', 'generation', 'Prepared Snapshot context · delivery separately recorded', 'knowledge')
        if independent or proactive or isinstance(tools.get('trigger_sources'),list) or any(row.get('phase')=='cell_created' for row in tool_events):
            cadence = (f'Proactive research is due at the first ordinary attempt after bootstrap, then every {proactive_every} globally committed ordinary attempts, independent of new records. Capacity and planning gates can defer execution. ' if proactive else '')
            yields_after_trial = (contract in {'espalier-3.30', 'espalier-3.31','espalier-3.32'}
                and tools.get('yield_after_success') is True
                and type(tools.get('max_scientific_steps')) is int
                and tools['max_scientific_steps'] > 1)
            continuation = (' After a successful foreground tool, ordinary generation receives its observations. '
                'The question stays open for a later scheduled research opportunity. The first planner call, '
                'foreground tool and independent method pipeline can still block; this is not a background planner.'
                if yields_after_trial and not independent else '')
            node('research_cells','Research cells',
                f'Proactive every {proactive_every} attempts + search signals' if proactive else 'Durable questions and method history',kind='knowledge',
                detail=cadence + 'Recorded population stagnation and enabled plateau signals can open a research question. A cell retains immutable revisions, roles, tool versions and evidence independently of candidate generations or island population slots. Local trials, independent replay, recipient adoption trials and later use are distinct transitions. Adoption does not establish task benefit.' + continuation,
                features=([f'Proactive every {proactive_every} attempts'] if proactive else []) + ['Triggered by recorded search signals','Independent cell and program lineages'] + (['Yield after a successful tool'] if yields_after_trial else []))
            if independent:
                notes.append('Research continuations have a checkpoint-owned queue and may dispatch alongside ordinary evolutionary jobs. A shared wave commit barrier remains; this is not independent asynchronous publication. Queue status does not establish running CPU.')
                edge('scheduler','research_cells','Independent continuation queue · shared wave commit','control')
                if tools.get('shared_observations') is True:
                    edge('research_checks','research_cells','Receipt-bound observations across islands · prompt delivery recorded','knowledge')
                    notes.append('Shared observations may include negative and unpublished checks. Delivery to a model does not imply tool adoption, actual use or causal benefit.')
            node('research_checks','Research check results','Compact evidence for G',kind='knowledge',
                detail='Bounded research-check cards carry the question, exact source/receipt references, observations and limitations into prepared generation context. The next program still passes ordinary candidate novelty and task evaluation. A prepared Snapshot alone is not proof of actual prompt delivery, causal utility or a policy reward.')
            edge('scheduler','research_cells',('Proactive cadence; ' if proactive else '') + 'Recorded stagnation / enabled plateau signals','control')
            edge('research_cells','tool_library','Propose or reuse immutable methods','knowledge')
            edge('tool_execution','research_checks','Bounded observations and receipt references','knowledge')
            edge('research_checks','generation','Prepared research cards · ordinary G / evaluation follows','knowledge')
            if contract in {'espalier-3.25','espalier-3.26','espalier-3.27','espalier-3.28','espalier-3.29','espalier-3.30','espalier-3.31','espalier-3.32'}:
                edge('population','research_cells','Saved sources, outputs and observed search limits','knowledge')
                edge('tool_execution','research_cells','Inspect saved measurements; choose the next test','knowledge')
                edge('research_cells','tool_execution','Revise, continue saved state, or close the question','control')
                edge('tool_execution','novelty' if any(n['id']=='novelty' for n in nodes) else 'evaluation',
                     'Exact saved candidate → ordinary validation / evaluation','flow')
                notes.append('Research cells keep a sequential decision history and immutable stage inputs. '
                    'Tool CPU and model charges are recorded separately; candidate evaluation and a later method trial on another source do not by themselves establish causal benefit.')
    elif tools.get('enabled') is False:
        off('Shared executable tools', 'Disabled in this recorded Engine configuration.')
    if parallel.get('enabled') is True:
        notes.append('Parallel jobs use frozen parent and knowledge snapshots. Conclusions follow the generation wave in commit order; reflection finishes before the next wave. Configured slots do not establish actual simultaneous execution.')
    if repeated:
        notes.append("A specialized repeat-population route is recorded; ordinary reward/control paths must not be treated as its complete protocol.")
    for key, label in (("three_head", "Three-head override"), ("preset_selection", "Preset weights")):
        if config.get(key) is False:
            off(label, "Explicitly disabled in the recorded configuration.")
    notes.append("This is recorded architecture, not proof that a stochastic model followed every directive or that an enabled feature improved quality.")
    mode_summary = mode_source or ("disabled" if policy.get("enabled") is False else "unknown")
    return dict(nodes=nodes, edges=edges, inactive=inactive,
                execution=dict(status='enabled' if parallel.get('enabled') is True else 'disabled' if parallel.get('enabled') is False else 'unknown',
                               workers=parallel.get('workers') if type(parallel.get('workers')) is int else None,
                               feedback='C/R at wave boundaries' if research.get('enabled') is True else 'Research disabled' if research.get('enabled') is False else 'Research status unknown'),
                summary=["Mode source: " + mode_summary,
                         "Representation: " + (kind or "unknown"),
                         "LLM and embedding weights are not updated by these search rewards."], notes=notes)
