"""Read-only diagram semantics; fixtures are recorded configs, not engine defaults."""
import copy
import json
import unittest
import pytest

from arena.observers.sciel.architecture import architecture
from arena.observers.sciel.architecture_graph import architecture_graph


SLOTS = {"scheduler", "parent", "operator", "generation", "evaluation", "population",
         "mode_policy", "operator_bandit", "refine", "ideas", "descriptor",
         "memory", "conclusion", "reflection", "reward", "novelty"}


def baseline():
    return dict(engine_contract='espalier-3.2', config=dict(budget=None, schedule_horizon=80, num_islands=3, max_islands=6,
        schedule_policy="sh", portfolio_seed=True, dynamic_islands=True, warm_start=None,
        crossover=True, idea_island=True, selection_policy="novelty_chain",
        container={"kind": "legacy", "selection": "shared"}, op_window=50,
        refine_stall=8, three_head=False, preset_selection=False,
        policy={"enabled": True, "base_mix": {"base": .8, "exploit": .2}, "plateau_shift": True},
        research={"enabled": True, "inject_lessons": True, "reflection_interval": 10},
        llm={"models": ["google/gemini-2.5-flash"]}),
        descriptor={"kind": "pca2_v3@f49107ce", "embed_sha": "95b154a3d49e"},
        evaluator={"backend": "subprocess"})


def node(graph, ident):
    return next(item for item in graph["nodes"] if item["id"] == ident)


def links(graph, source, target):
    return [item for item in graph["edges"] if item["from"] == source and item["to"] == target]


class ArchitectureGraphTests(unittest.TestCase):
    def test_baseline_has_static_modes_frozen_pca_and_gcr(self):
        graph = architecture_graph(baseline(), {}, [])
        self.assertEqual(node(graph, "mode_policy")["kind"], "rule")
        self.assertIn("plateau", node(graph, "mode_policy")["subtitle"])
        self.assertFalse(links(graph, "reward", "mode_policy"))
        self.assertEqual(node(graph, "descriptor")["kind"], "frozen")
        self.assertEqual(node(graph, "operator_bandit")["kind"], "online")
        self.assertIn("Non-escalated island records", links(graph, "reward", "operator_bandit")[0]["label"])
        self.assertEqual(node(graph, "ideas")["label"], "Idea island")
        self.assertIn("Portfolio starts", node(graph, "scheduler")["features"])
        self.assertIn("Dynamic islands", node(graph, "scheduler")["features"])
        self.assertTrue(links(graph, "memory", "generation"))
        self.assertTrue(links(graph, "reflection", "memory"))
        self.assertEqual(links(graph, "evaluation", "memory")[0]["label"], "Recorded outcomes / evidence")
        self.assertIn("conclusions were rejected", node(graph, "reflection")["detail"])
        self.assertEqual(node(graph, "population")["label"], "MAP-Elites + archive")
        self.assertIn("Parent delta", links(graph, "evaluation", "conclusion")[0]["label"])
        self.assertIn("nonnegative record reward", node(graph, "conclusion")["detail"])

    def test_contextual_rl_adds_correct_credit_and_two_stage_ideas(self):
        first = baseline()
        first["config"]["policy"].update(mode_bandit=True, plateau_shift=False, plateau_shadow=True)
        first["config"]["idea_two_stage"] = {"enabled": True}
        first["config"]["research"]["lesson_selection"] = {"mode": "source_diverse_guarded"}
        graph = architecture_graph(first, {}, [])
        self.assertEqual(node(graph, "mode_policy")["kind"], "online")
        self.assertEqual(node(graph, "mode_policy")["label"], "Contextual mode bandit")
        self.assertEqual(links(graph, "reward", "mode_policy")[0]["label"], "All on-policy attempts · failures = 0")
        self.assertEqual(node(graph, "ideas")["label"], "Two-stage ideas")
        self.assertIn("Guarded source diversity", node(graph, "memory")["features"])
        self.assertTrue(any(item["status"] == "shadow" and "Plateau" in item["label"] for item in graph["inactive"]))

    def test_adaptive_presets_and_actual_vq_replace_mode_bandit_and_pca(self):
        first = baseline()
        first["config"].update(preset_selection=True, preset_adaptive=True, embed_grid=False,
                               embed_axis_path="inherited-pca.npz", embed_niche=True,
                               policy={"enabled": False, "mode_bandit": False})
        first["descriptor"] = {"kind": "vq_niche", "embed_sha": "95b154a3d49e"}
        graph = architecture_graph(first, {}, [])
        self.assertEqual(node(graph, "mode_policy")["label"], "Preset-weight bandit")
        self.assertEqual(node(graph, "mode_policy")["kind"], "online")
        self.assertEqual(links(graph, "reward", "mode_policy")[0]["label"], "Binary population record · after C/R")
        self.assertEqual(node(graph, "descriptor")["label"], "VQ niches")
        self.assertEqual(node(graph, "population")["label"], "MAP-Elites + archive")
        self.assertIn("niche × score", node(graph, "population")["subtitle"])
        self.assertIn("embedder weights remain frozen", node(graph, "descriptor")["detail"])
        self.assertNotIn("inherited-pca.npz", json.dumps(graph))
        self.assertIn("Mode source: Adaptive preset weights", graph["summary"])

    def test_frozen_mlp_and_three_head_never_claim_effective_online_learning(self):
        for three in (False, True):
            first = baseline()
            first["config"]["policy"].update(mode_bandit=True, mode_source="mlp")
            first["config"]["three_head"] = three
            graph = architecture_graph(first, {}, [])
            self.assertEqual(node(graph, "mode_policy")["kind"], "frozen")
            self.assertFalse(links(graph, "reward", "mode_policy"))
            self.assertTrue(any(item["status"] == "shadow" and "bandit" in item["label"].lower()
                                for item in graph["inactive"]))
            if three:
                self.assertIn("If the head supplies no tilt", node(graph, "mode_policy")["detail"])

    def test_disabled_modes_reflection_and_injection_have_no_effective_edges(self):
        first = baseline()
        first["config"]["policy"] = {"enabled": False, "mode_bandit": True}
        first["config"]["research"].update(reflection_interval=0, inject_lessons=False)
        first["config"].update(op_fixed="full_rewrite", idea_island=False)
        graph = architecture_graph(first, {}, [])
        ids = {item["id"] for item in graph["nodes"]}
        self.assertFalse(ids & {"mode_policy", "reflection", "operator_bandit", "refine", "ideas"})
        self.assertIn("memory", ids)
        self.assertFalse(links(graph, "memory", "generation"))

    def test_requested_embeddings_and_partial_policy_are_not_evidence_of_activation(self):
        first = {"config": {"embed_grid": True, "embed_niche": True,
                            "policy": {"mode_bandit": True}}}
        graph = architecture_graph(first, {}, [])
        self.assertEqual(node(graph, "descriptor")["status"], "unknown")
        self.assertEqual(node(graph, "mode_policy")["status"], "unknown")
        self.assertFalse(links(graph, "reward", "mode_policy"))
        first["descriptor"] = {"kind": "code_length"}
        self.assertNotIn("descriptor", {item["id"] for item in architecture_graph(first, {}, [])["nodes"]})

    def test_checkpoint_fallback_and_start_descriptor_precedence(self):
        first = baseline()
        cp = {"config": first["config"], "identity": {"descriptor": first["descriptor"]}}
        graph = architecture_graph({}, cp, [])
        self.assertEqual(node(graph, "descriptor")["kind"], "frozen")
        override = architecture_graph({"config": {}, "descriptor": {"kind": "code_length"}}, cp, [])
        self.assertNotIn("descriptor", {item["id"] for item in override["nodes"]})
        self.assertEqual(node(override, "mode_policy")["status"], "unknown")

    def test_missing_archival_config_stays_unknown_and_contract_is_bounded(self):
        graph = architecture_graph({}, {}, [])
        self.assertEqual(node(graph, "scheduler")["status"], "unknown")
        self.assertEqual(node(graph, "operator_bandit")["status"], "unknown")
        self.assertTrue(any("defaults are not substituted" in note for note in graph["notes"]))
        ids = {item["id"] for item in graph["nodes"]}
        self.assertEqual(len(ids), len(graph["nodes"]))
        self.assertLessEqual(ids, SLOTS)
        for item in graph["edges"]:
            self.assertIn(item["from"], ids)
            self.assertIn(item["to"], ids)
            self.assertIn(item["kind"], {"flow", "control", "reward", "knowledge"})
        json.dumps(graph, allow_nan=False)

    def test_existing_architecture_contract_preserved_and_inputs_unchanged(self):
        first, cp, rows = baseline(), {}, []
        original = copy.deepcopy((first, cp, rows))
        view = architecture(first, cp, rows)
        self.assertEqual(view["schema"], "sciel-architecture/1")
        self.assertEqual(len(view["stages"]), 7)
        self.assertTrue(view["sections"] and view["edges"])
        self.assertIn("graph", view)
        self.assertIn("Fresh start", node(view["graph"], "scheduler")["features"])
        self.assertEqual(node(view["graph"], "generation")["phase"], "generating")
        self.assertEqual(node(view["graph"], "conclusion")["phase"], "research")
        self.assertEqual(node(view["graph"], "reflection")["phase"], "research")
        self.assertEqual((first, cp, rows), original)

    def test_novelty_is_recorded_between_generation_and_evaluation_only_when_enabled(self):
        first = baseline()
        self.assertNotIn('novelty', {n['id'] for n in architecture_graph(first, {}, [])['nodes']})
        first['config']['candidate_novelty'] = {'enabled': True, 'max_resamples': 2, 'neighbors': 3}
        graph = architecture_graph(first, {}, [])
        self.assertEqual(node(graph, 'novelty')['subtitle'], 'SHA256 → AST → code embedding')
        self.assertIn('whole-run history', node(graph, 'novelty')['detail'])
        self.assertIn('similarity is advisory', node(graph, 'novelty')['detail'])
        self.assertTrue(links(graph, 'generation', 'novelty'))
        self.assertTrue(links(graph, 'novelty', 'evaluation'))
        self.assertTrue(links(graph, 'novelty', 'generation'))
        self.assertFalse(links(graph, 'generation', 'evaluation'))
        self.assertLessEqual(len(graph['nodes']), 16)
        first['config']['candidate_novelty']['enabled'] = False
        graph = architecture_graph(first, {}, [])
        self.assertNotIn('novelty', {n['id'] for n in graph['nodes']})
        self.assertTrue(links(graph, 'generation', 'evaluation'))

    def test_preset_credit_timing_uses_recorded_engine_contract(self):
        first = baseline()
        first['config'].update(preset_selection=True, preset_adaptive=True)
        for contract, timing in [('espalier-3.2', 'after C/R'), ('espalier-3.3', 'before C/R'),
                                 ('espalier-3.4', 'before C/R'), ('espalier-3.5', 'before C/R'), ('espalier-3.6', 'before C/R'),
                                 ('espalier-3.7', 'before C/R'), ('espalier-3.8', 'before C/R'), ('espalier-3.9', 'before C/R'), ('espalier-3.10', 'before C/R'), ('espalier-3.11', 'before C/R'), ('espalier-3.12', 'before C/R'), ('espalier-3.13', 'before C/R'), ('espalier-3.14', 'before C/R'), ('espalier-3.15', 'before C/R'), ('espalier-3.16', 'before C/R'), ('espalier-3.17', 'before C/R'), ('espalier-3.18', 'before C/R'), ('espalier-3.19', 'before C/R'), ('espalier-3.20', 'before C/R'), ('espalier-3.21', 'before C/R'), ('espalier-3.22', 'before C/R'), ('espalier-3.23', 'before C/R'), (None, 'timing not recorded'),
                                 ('espalier-3.24', 'before C/R'), ('espalier-3.25', 'before C/R'), ('espalier-3.26', 'before C/R'), ('espalier-3.27', 'before C/R'), ('espalier-3.28', 'before C/R'), ('unknown', 'timing not recorded')]:
            with self.subTest(contract=contract):
                first['engine_contract'] = contract
                graph = architecture_graph(first, {}, [])
                self.assertEqual(links(graph, 'reward', 'mode_policy')[0]['label'],
                                 'Binary population record · ' + timing)
                if timing == 'before C/R':
                    self.assertIn('After the search result, before conclusion/reflection.',
                                  node(graph, 'mode_policy')['detail'])
        first.pop('engine_contract')
        graph = architecture_graph(first, {'identity': {'engine_contract': 'espalier-3.4'}}, [])
        self.assertIn('before C/R', links(graph, 'reward', 'mode_policy')[0]['label'])

    def test_proactive_research_cadence_requires_enabled_recorded_setting(self):
        first = baseline()
        first['engine_contract'] = 'espalier-3.21'
        tools = {'enabled': True, 'trigger_sources': ['population_stall', 'search_attempt_stall']}
        first['config']['research_tools'] = tools
        historical = architecture_graph(first, {}, [])
        tools['proactive_every_attempts'] = None
        self.assertEqual(architecture_graph(first, {}, []), historical)
        self.assertEqual(node(historical, 'research_cells')['subtitle'], 'Durable questions and method history')
        self.assertNotIn('Proactive', json.dumps(historical))

        tools['proactive_every_attempts'] = 8
        original = copy.deepcopy(first)
        graph = architecture_graph(first, {}, [])
        cell = node(graph, 'research_cells')
        self.assertIn('Proactive every 8 attempts', cell['subtitle'])
        self.assertIn('Proactive every 8 attempts', cell['features'])
        self.assertIn('Triggered by recorded search signals', cell['features'])
        self.assertIn('first ordinary attempt after bootstrap', cell['detail'])
        self.assertIn('every 8 globally committed ordinary attempts', cell['detail'])
        self.assertIn('independent of new records', cell['detail'])
        self.assertIn('can defer execution', cell['detail'])
        self.assertIn('Recorded stagnation / enabled plateau signals',
                      links(graph, 'scheduler', 'research_cells')[0]['label'])
        self.assertFalse(links(graph, 'research_cells', 'reward'))
        self.assertEqual(first, original)

        tools['enabled'] = False
        disabled = architecture_graph(first, {}, [])
        self.assertNotIn('research_cells', {item['id'] for item in disabled['nodes']})
        self.assertNotIn('Proactive', json.dumps(disabled))

    def test_memory_and_format_corrections_require_explicit_recorded_flags(self):
        first = baseline()
        first['config']['idea_two_stage'] = {'enabled': True, 'card_repair_attempts': 1}
        first['config']['research'].update(compact_lesson_memory=True, conclusion_source_refs=True,
                                          conclusion_repair_attempts=1)
        view = architecture(first, {}, [])
        graph = view['graph']
        self.assertIn('Compact lesson memory', node(graph, 'memory')['features'])
        self.assertIn('full stored evidence is retained separately', node(graph, 'memory')['detail'])
        self.assertIn('Host-bound source references', node(graph, 'conclusion')['features'])
        self.assertIn('Up to 1 format correction', node(graph, 'conclusion')['features'])
        self.assertIn('auxiliary-call budget', node(graph, 'conclusion')['detail'])
        self.assertIn('Up to 1 card correction', node(graph, 'ideas')['features'])
        fields = {field['key']:field for section in view['sections'] for field in section['fields']}
        self.assertIs(fields['research.compact_lesson_memory']['value'], True)
        self.assertEqual(fields['idea_two_stage.card_repair_attempts']['value'], 1)
        for research in ({}, {'compact_lesson_memory':False, 'conclusion_source_refs':False,
                             'conclusion_repair_attempts':0}):
            first['config']['research'] = dict(enabled=True, **research)
            first['config']['idea_two_stage'] = {'enabled':True}
            old = architecture(first, {}, [])
            self.assertNotIn('Compact lesson memory', node(old['graph'], 'memory')['features'])
            self.assertNotIn('Host-bound source references', node(old['graph'], 'conclusion')['features'])
            self.assertNotIn('Up to 1 format correction', node(old['graph'], 'conclusion')['features'])
            self.assertNotIn('Up to 1 card correction', node(old['graph'], 'ideas')['features'])


if __name__ == "__main__":
    unittest.main()


@pytest.mark.parametrize('contract', ['espalier-3.32', 'espalier-3.33', 'espalier-3.34', 'espalier-3.35'])
def test_recorded_independent_research_has_shared_wave_barrier_and_cross_island_observations(contract):
    start=baseline();start['engine_contract']=contract
    start['config']['research_tools']={'enabled':True,'independent_research':True,'shared_observations':True,
        'trigger_sources':['plateau'],'yield_after_success':True,'max_scientific_steps':3}
    graph=architecture_graph(start,{},[])
    assert any('Independent continuation queue' in row['label'] for row in links(graph,'scheduler','research_cells'))
    assert links(graph,'research_checks','research_cells')
    assert any('shared wave commit barrier' in note for note in graph['notes'])
    assert any('negative and unpublished' in note for note in graph['notes'])
    start['engine_contract']='espalier-3.31'
    old=architecture_graph(start,{},[])
    assert not any('Independent continuation queue' in row['label'] for row in links(old,'scheduler','research_cells'))
