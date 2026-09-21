"""Inert configuration/provider tests, never native research or model calls."""
import ast
import importlib.util
import json
from pathlib import Path
import pickle
import subprocess
import sys
from types import SimpleNamespace

import pytest

from arena.frameworks.drivers import llamea_bbob_gateway as llamea
from arena.frameworks.drivers import eohs_gateway as eohs

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path('/tmp/arena-framework-sources/llamea-hpo')


def test_imports_do_not_load_native_frameworks_or_sdk():
    code = '''import sys
from arena.frameworks.drivers import llamea_bbob_gateway, eohs_gateway
assert not any(x in sys.modules for x in ('llamea','llm4ad','smac','ioh','openai'))
'''
    subprocess.run([sys.executable, '-c', code], check=True)


@pytest.mark.skipif(not SOURCE.exists(), reason='Optional pinned source inspection; no upstream evaluator execution')
@pytest.mark.parametrize('hpo', [False, True])
def test_extraction_retains_real_evaluator_without_running_script_or_random_fitness(hpo):
    code, proof = llamea.extract_example(SOURCE, hpo)
    tree = ast.parse(code)
    assert not any(isinstance(n, (ast.For, ast.If)) for n in tree.body)
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)]
    assert not any(ast.unparse(n.func) in {'LLaMEA', 'Gemini_LLM', 'OpenAI_LLM'} for n in calls)
    assert 'correct_aoc(problem, l2, budget)' in code
    assert 'range(3)' in code and 'np.arange(1, 25)' in code
    assert 'np.random.rand()' not in code
    if hpo:
        assert 'solution.configspace is None' in code and 'solution.keys()' not in code
        assert 'n_trials=8' in code and 'instances=[str(arg) for arg in args]' in code
        assert 'smac.optimize()' in code and 'budget = 200 * dim' in code
        assert len(proof['adjustments']) == 3
    else:
        assert not proof['adjustments'] and 'smac.optimize()' not in code


def test_source_drift_fails_before_import_or_execution(tmp_path):
    p = tmp_path / llamea.EXAMPLES[True][0]
    p.parent.mkdir(); p.write_text('raise AssertionError("must stay inert")')
    with pytest.raises(ValueError, match='hash mismatch'):
        llamea.extract_example(tmp_path, True)


def test_evaluator_archive_retains_verified_code_not_runtime_namespace():
    obj = llamea.ExampleEvaluator('inert source', {'function': 'evaluate'})
    obj._function = lambda *args: 'runtime namespace with sensitive state'
    restored = pickle.loads(pickle.dumps(obj))
    assert restored.code == 'inert source' and restored._function is None


def test_provider_preserves_exact_native_model_and_removes_credentials_from_archive(monkeypatch):
    calls = []
    class Client:
        def __init__(self, **kwargs): calls.append(kwargs)
        def close(self): pass
    class Native:
        def __init__(self, api_key, model):
            self.api_key, self.model, self.client = api_key, model, Client(api_key=api_key)
        def __getstate__(self): return {k:v for k,v in self.__dict__.items() if k != 'client'}
    monkeypatch.setenv('OPENAI_API_KEY', 'inert-local-fixture')
    monkeypatch.setenv('OPENAI_BASE_URL', 'https://wrong.invalid')
    monkeypatch.setitem(sys.modules, 'llamea', SimpleNamespace(OpenAI_LLM=Native))
    monkeypatch.setitem(sys.modules, 'openai', SimpleNamespace(OpenAI=Client))
    for model in llamea.MODELS:
        llm = llamea.provider(model)
        assert llm.model == model
        assert 'inert-local-fixture' not in repr(llm.__getstate__())
        assert calls[-1] == {'base_url': llamea.ENDPOINT, 'timeout': 180, 'max_retries': 0}
    with pytest.raises(ValueError, match='exact reviewed'):
        llamea.provider('gpt-4o')


def test_eohs_uses_native_set_evaluation_and_hides_provider_key(monkeypatch, tmp_path):
    class Native:
        def __init__(self, **kwargs):
            for k,v in kwargs.items():setattr(self, '_'+k, v)
    def evaluator(**kwargs):return SimpleNamespace(kind='native-set', **kwargs)
    monkeypatch.setenv('OPENAI_API_KEY', 'inert-local-fixture')
    monkeypatch.setitem(sys.modules, 'llm4ad.task.optimization.online_bin_packing_set', SimpleNamespace(OBPSEvaluation=evaluator))
    monkeypatch.setitem(sys.modules, 'llm4ad.tools.llm.llm_api_https', SimpleNamespace(HttpsApi=Native))
    monkeypatch.setitem(sys.modules, 'llm4ad.method.eohs', SimpleNamespace(EoHSProfiler=lambda **kw:kw))
    for model in llamea.MODELS:
        result = eohs.configuration(model, tmp_path, tmp_path/'trusted-native.pkl')
        assert result['evaluation'].return_list is True
        assert result['evaluation'].dataset == str(tmp_path/'trusted-native.pkl')
        assert result['llm']._model == model and result['llm']._host == '127.0.0.1:8790'
        assert result['llm']._key == 'inert-local-fixture'
        assert 'inert-local-fixture' not in repr(vars(result['llm']))
        assert result['num_samplers'] == result['num_evaluators'] == 1
        assert result['pop_size'] == 2 and result['max_sample_nums'] == 8


def test_templates_cover_three_profiles_with_distinct_native_identity_and_no_inline_keys():
    spec = importlib.util.spec_from_file_location('llamea_pilot_generator', ROOT/'scripts/deployment/prepare_llamea_eohs_pilots.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    values = [module.template(Path('/srv/arena'), *profile, model, Path('/public-ca.pem'))
              for profile in module.PROFILES for model in module.MODELS]
    assert len(values) == len({v['id'] for v in values}) == 21
    assert {v['framework'] for v in values} == {'llamea-hpo', 'eoh-s'}
    for item in values:
        assert item['spec']['environment_names'] == ['OPENAI_API_KEY']
        assert item['spec']['timeout_seconds'] == 2400
        assert item['resources']['evaluation_slots'] == 1
        assert item['model'] in item['spec']['request']['arguments']
    assert {v['profile'] for v in values} == {p[1] for p in module.PROFILES}
