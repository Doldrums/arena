"""Source-backed specialized recipes and execution-only native delegation."""
import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
RECIPES = json.loads((ROOT / 'registry/framework-recipes/specialized.json').read_text())['recipes']
BY_ID = {recipe['id']: recipe for recipe in RECIPES}
EXPECTED = set('gepa mipro evoprompt promptagent protegi sepo accelopt revolve text2reward eureka llamea-bo llamea-mobo llamea-hpo llm-flowrepair qdaif enpire eoh-s l-autoda llm-evolved-rl-algorithms lmx cocoevo autorise'.split())


def factory(tmp_path, monkeypatch, payload, module):
    monkeypatch.chdir(tmp_path)
    path = tmp_path / 'factory.py'
    path.write_text('raise RuntimeError("Factory import must happen only during explicit execution")')
    monkeypatch.setattr(module, 'load_factory', lambda reference: payload)
    return ['--factory', 'factory.py:build']


def test_every_requested_method_has_an_explicit_audit_outcome():
    assert EXPECTED == set(p for r in RECIPES for p in r['participant_ids'])
    assert len(BY_ID) == len(RECIPES)
    for recipe in RECIPES:
        assert recipe['status'] in {'source_verified', 'blocked', 'artifact_only'}
        if recipe['status'] == 'source_verified':
            assert recipe['profiles'] and not recipe['blocked_reason']
        else:
            assert recipe['blocked_reason'] or recipe['profiles']
        if recipe['repository']:
            assert re.fullmatch('[a-f0-9]{40}', recipe['repository']['commit'])
            assert recipe['evidence']
        for path, sha in recipe['evidence'].items():
            assert not Path(path).is_absolute() and '..' not in Path(path).parts
            assert re.fullmatch('[a-f0-9]{64}', sha)
        for profile in recipe['profiles']:
            assert profile['evaluation']['mode'] == 'native'
            assert set(profile['evaluation']['evidence']) <= recipe['evidence'].keys()
            assert set(profile['required_files']) <= recipe['evidence'].keys()
            assert set(profile['config_files']) <= recipe['evidence'].keys()
            if profile['invocation']['kind'] == 'script':
                assert profile['invocation']['target'] in recipe['evidence']


def test_artifacts_and_algorithm_versions_cannot_be_mislabelled():
    assert BY_ID['autorise']['status'] == 'artifact_only' and not BY_ID['autorise']['profiles']
    assert BY_ID['gepa-artifact']['status'] == 'artifact_only'
    assert BY_ID['qdaif-artifact']['status'] == 'artifact_only'
    assert BY_ID['mipro']['profiles'][0]['id'] == 'miprov2-native-api'
    assert 'MIPROv2' in BY_ID['mipro']['name']
    assert BY_ID['sepo']['status'] == 'blocked' and not BY_ID['sepo']['profiles']
    assert BY_ID['llm-flowrepair']['repository'] is None
    assert BY_ID['accelopt']['status'] == 'source_verified'
    assert BY_ID['accelopt']['profiles'][0]['id'] == 'nkibench-complete-loop'
    assert BY_ID['enpire']['status'] == 'artifact_only'
    assert 'two seeds' in BY_ID['llm-evolved-rl-algorithms']['profiles'][0]['evaluation']['description']


@pytest.mark.parametrize('recipe', [r for r in RECIPES if r['repository']], ids=lambda r: r['id'])
def test_optional_pinned_source_evidence(recipe, tmp_path):
    source_root = os.environ.get('ARENA_SPECIALIZED_SOURCE_ROOT')
    if not source_root:
        pytest.skip('Set ARENA_SPECIALIZED_SOURCE_ROOT for source-only conformance; no native code runs')
    slug = {'gepa': 'gepa-library', 'gepa-artifact': 'gepa'}.get(recipe['id'], recipe['id'])
    source = Path(source_root) / slug
    actual = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    assert actual == recipe['repository']['commit']
    if recipe['id'] == 'accelopt':
        from arena.frameworks.drivers.accelopt import TEMPLATE, corrected_template
        original = (source / TEMPLATE).read_bytes()
        patched = corrected_template(original)
        for position in range(10, 16):
            patched = patched.replace(f'${{{position}}}'.encode(), f'${position}'.encode())
        assert patched == original
    from arena.frameworks.recipes import RecipeAdapter
    for profile in recipe['profiles']:
        output = tmp_path / profile['id']
        command = RecipeAdapter(recipe).prepare(source, {'python': sys.executable, 'profile': profile['id']}, output)
        assert command['workspace_copy'] and not output.exists()
        assert command['profile'] == profile['id']
        assert str(output / 'workspace' / recipe['id']) in command['cwd']
    for filename, expected in recipe['evidence'].items():
        assert hashlib.sha256((source / filename).read_bytes()).hexdigest() == expected, filename


def test_driver_imports_do_not_import_native_libraries_or_run_factories(tmp_path):
    code = '''import importlib,sys
for name in ('gepa','mipro_v2','eoh_s','llamea_bo','llamea_hpo','protegi','evoprompt','promptagent','lmx','accelopt'):
 importlib.import_module('arena.frameworks.drivers.'+name)
assert not any(name in sys.modules for name in ('gepa','dspy','llm4ad','llamea','llm_client','run_es_search'))
'''
    subprocess.run([sys.executable, '-c', code], cwd=tmp_path, env=os.environ | {'PYTHONPATH': str(ROOT / 'src')}, check=True)


def test_gepa_delegates_whole_optimizer_and_keeps_native_result(tmp_path, monkeypatch):
    from arena.frameworks.drivers import gepa
    payload = {'seed_candidate': {'prompt': 'initial'}, 'trainset': [1], 'adapter': object(), 'max_metric_calls': 999}
    args = factory(tmp_path, monkeypatch, payload, gepa)
    calls = []
    def optimize(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(to_dict=lambda: {'candidates': [{'prompt': 'evolved'}], 'val_aggregate_scores': [0.75]})
    monkeypatch.setitem(sys.modules, 'gepa', SimpleNamespace(optimize=optimize))
    output = tmp_path.parent / (tmp_path.name + '-results')
    assert gepa.main(args + ['--max-metric-calls', '7', '--output', str(output)]) == 0
    assert len(calls) == 1 and calls[0]['max_metric_calls'] == 7
    assert calls[0]['adapter'] is payload['adapter'] and calls[0]['run_dir'] == str(output)
    assert calls[0]['use_cloudpickle'] is False and calls[0]['use_wandb'] is False
    assert json.loads((output / 'gepa-result.json').read_text())['val_aggregate_scores'] == [0.75]


def test_mipro_calls_native_compile_with_explicit_budget(tmp_path, monkeypatch):
    from arena.frameworks.drivers import mipro_v2
    payload = {'optimizer': {'metric': object()}, 'compile': {'student': object(), 'trainset': [1], 'valset': [2]}}
    args = factory(tmp_path, monkeypatch, payload, mipro_v2)
    calls = {}
    class Optimizer:
        def __init__(self, **kwargs): calls['optimizer'] = kwargs
        def compile(self, **kwargs):
            calls['compile'] = kwargs
            return SimpleNamespace(save=lambda path, **options: calls.update(save=(path, options)))
    monkeypatch.setitem(sys.modules, 'dspy', SimpleNamespace(MIPROv2=Optimizer))
    mipro_v2.main(args + ['--trials', '8', '--candidates', '4', '--output', str(tmp_path / 'results')])
    assert calls['optimizer']['auto'] is None and calls['optimizer']['num_candidates'] == 4
    assert calls['compile']['student'] is payload['compile']['student']
    assert calls['compile']['num_trials'] == 8 and calls['compile']['valset'] == [2]
    assert calls['save'][1] == {'save_program': False}


def test_eoh_s_preserves_set_evaluator_and_native_loop(tmp_path, monkeypatch):
    from arena.frameworks.drivers import eoh_s
    payload = {'llm': object(), 'evaluation': object()}
    args = factory(tmp_path, monkeypatch, payload, eoh_s)
    calls = {}
    class Method:
        def __init__(self, **kwargs): calls.update(kwargs)
        def run(self): calls['ran'] = True
    monkeypatch.setitem(sys.modules, 'llm4ad.method.eohs', SimpleNamespace(EoHS=Method, EoHSProfiler=lambda **kwargs: kwargs))
    eoh_s.main(args + ['--max-samples', '20', '--generations', '3', '--population', '5', '--output', str(tmp_path / 'results')])
    assert calls['ran'] and calls['evaluation'] is payload['evaluation']
    assert calls['max_sample_nums'] == 20 and calls['max_generations'] == 3
    assert calls['profiler']['log_style'] == 'simple'


def test_llamea_hpo_preserves_native_hpo_callback_and_loop(tmp_path, monkeypatch):
    from arena.frameworks.drivers import llamea_hpo
    payload = {'f': object(), 'llm': object(), 'budget': 100, 'HPO': False}
    args = factory(tmp_path, monkeypatch, payload, llamea_hpo)
    calls = {}
    class Method:
        def __init__(self, **kwargs): calls.update(kwargs)
        def run(self): calls['ran'] = True
    monkeypatch.setitem(sys.modules, 'llamea', SimpleNamespace(LLaMEA=Method))
    llamea_hpo.main(args + ['--generations', '3'])
    assert calls['ran'] and calls['HPO'] is True and calls['budget'] == 3
    assert calls['f'] is payload['f']


def test_llamea_bo_key_is_only_passed_to_native_function(monkeypatch, capsys):
    from arena.frameworks.drivers import llamea_bo
    calls = []
    monkeypatch.setenv('GEMINI_API_KEY', 'fixture-not-a-real-key')
    monkeypatch.setitem(sys.modules, 'run_es_search', SimpleNamespace(run_exp=lambda *args, **kwargs: calls.append((args, kwargs))))
    llamea_bo.main(['--parents', '2', '--offspring', '3', '--populations', '4', '--elitist'])
    assert calls == [((2, 3, True, 'fixture-not-a-real-key'), {'n_population': 4})]
    assert 'fixture-not-a-real-key' not in capsys.readouterr().out


def test_protegi_bridges_key_in_memory_without_writing_config(tmp_path, monkeypatch):
    from arena.frameworks.drivers import protegi
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('OPENAI_API_KEY', 'fixture-key')
    monkeypatch.setitem(sys.modules, 'config', SimpleNamespace())
    monkeypatch.setattr(sys, 'argv', ['driver'])
    observed = {}
    def native(path, run_name):
        observed.update(key=sys.modules['config'].OPENAI_KEY, argv=sys.argv[:], run_name=run_name)
    monkeypatch.setattr(protegi.runpy, 'run_path', native)
    protegi.main(['--rounds', '2'])
    assert observed['key'] == 'fixture-key' and observed['argv'][1:] == ['--rounds', '2']
    assert observed['run_name'] == '__main__' and not (tmp_path / 'config.py').exists()


def test_evoprompt_does_not_persist_environment_credentials(tmp_path, monkeypatch):
    from arena.frameworks.drivers import evoprompt
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('OPENAI_API_KEY', 'fixture-key')
    monkeypatch.setattr(sys, 'argv', ['driver'])
    original = {'turbo': {'default': {'api_key': 'placeholder', 'model': 'gpt-3.5-turbo'}}}
    reader = lambda path: original
    client = SimpleNamespace(read_yaml_file=reader)
    monkeypatch.setitem(sys.modules, 'llm_client', client)
    observed = {}
    monkeypatch.setattr(evoprompt.runpy, 'run_path', lambda *args, **kwargs: observed.update(client.read_yaml_file('auth.yaml')))
    evoprompt.main(['--budget', '2'])
    assert observed['turbo']['default']['api_key'] == 'fixture-key'
    assert original['turbo']['default']['api_key'] == 'placeholder'
    assert client.read_yaml_file is reader and not list(tmp_path.iterdir())


def test_promptagent_preserves_search_but_redacts_only_credential_logging(tmp_path, monkeypatch):
    from arena.frameworks.drivers import promptagent
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('OPENAI_API_KEY', 'fixture-key')
    config = {'base_model_setting': {'model_type': 'openai', 'api_key': None},
              'optim_model_setting': {'model_type': 'openai', 'api_key': None}, 'log_dir': 'ignored'}
    (tmp_path / 'config.json').write_text(json.dumps(config))
    monkeypatch.setitem(sys.modules, 'yaml', SimpleNamespace(safe_load=json.loads))
    messages, calls = [], {}
    class Agent:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
            self.logger = SimpleNamespace(info=messages.append)
            self.log_vars()
            calls.update(kwargs)
        def run(self): calls['ran'] = True
    monkeypatch.setattr(promptagent.runpy, 'run_path', lambda path: {'BaseAgent': Agent, 'validate_config': lambda config: None})
    promptagent.main(['--config', 'config.json', '--output', str(tmp_path / 'results')])
    assert calls['ran'] and calls['base_model_setting']['api_key'] == 'fixture-key'
    assert 'fixture-key' not in '\n'.join(messages) and '<environment>' in '\n'.join(messages)
    assert 'fixture-key' not in (tmp_path / 'config.json').read_text()


def test_lmx_creates_native_output_directory_then_runs_original_loop(tmp_path, monkeypatch):
    from arena.frameworks.drivers import lmx
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, 'argv', ['driver'])
    observed = []
    monkeypatch.setattr(lmx.runpy, 'run_path', lambda path, run_name: observed.append((path, run_name, sys.argv[1:])))
    lmx.main(['--max_generations', '2', '--exp_id', 'fixture'])
    assert (tmp_path / 'results').is_dir()
    assert observed == [(str(tmp_path / 'scripts/symbolic_regression.py'), '__main__', ['--max_generations', '2', '--exp_id', 'fixture'])]


def test_factory_load_is_explicit_and_rejects_escape(tmp_path, monkeypatch):
    from arena.frameworks.drivers._specialized import load_factory, bounded_positive
    monkeypatch.chdir(tmp_path)
    staged = tmp_path / 'factory.py'
    staged.write_text('def build():\n return {"native": "contract"}\n')
    assert load_factory('factory.py:build') == {'native': 'contract'}
    for reference in ('../outside.py:build', str(staged)+':build', 'factory.py:bad-name'):
        with pytest.raises(ValueError): load_factory(reference)
    for budget in ('0', '-1', '1000001'):
        with pytest.raises(ValueError): bounded_positive(budget)


def test_factory_modules_support_postponed_dataclasses_and_keep_distinct_identity(tmp_path, monkeypatch):
    import pickle
    from arena.frameworks.drivers._specialized import load_factory
    monkeypatch.chdir(tmp_path)
    source = '''from __future__ import annotations
from dataclasses import dataclass
@dataclass
class Config:
    value: int = 7
def build():
    return {"config": Config()}
'''
    (tmp_path / "first.py").write_text(source)
    (tmp_path / "second.py").write_text(source.replace("= 7", "= 9"))
    first = load_factory("first.py:build")["config"]
    second = load_factory("second.py:build")["config"]
    assert (first.value, second.value) == (7, 9)
    assert type(first).__module__ != type(second).__module__
    assert pickle.loads(pickle.dumps(first)) == first
    assert sys.modules[type(first).__module__].Config is type(first)


def test_failed_factory_load_removes_partial_module(tmp_path, monkeypatch):
    from arena.frameworks.drivers._specialized import load_factory
    monkeypatch.chdir(tmp_path)
    (tmp_path / "factory.py").write_text('raise RuntimeError("inert fixture failure")\n')
    before = {name for name in sys.modules if name.startswith("arena_native_factory_")}
    with pytest.raises(RuntimeError, match="fixture failure"):
        load_factory("factory.py:build")
    assert {name for name in sys.modules if name.startswith("arena_native_factory_")} == before


def accelopt_fixture(tmp_path, monkeypatch):
    from arena.frameworks.drivers import accelopt
    monkeypatch.chdir(tmp_path)
    # Controlled source fixture; the optional source conformance test separately
    # verifies the production template SHA against the exact upstream checkout.
    template = b'''EXP_BASE_DIR=$1
TOPK_CANDIDATES=$10
NUM_SAMPLES=$11
MAX_THRESHOLD=$12
MIN_THRESHOLD=$13
TOPK=$14
EXP_N=$15
printf '%s|%s|%s|%s|%s|%s' "$TOPK_CANDIDATES" "$NUM_SAMPLES" "$MAX_THRESHOLD" "$MIN_THRESHOLD" "$TOPK" "$EXP_N"
'''
    path = tmp_path / accelopt.TEMPLATE
    path.parent.mkdir(parents=True); path.write_bytes(template)
    monkeypatch.setattr(accelopt, 'TEMPLATE_SHA256', hashlib.sha256(template).hexdigest())
    prepared = tmp_path / 'inputs/accelopt'
    (prepared / 'configs').mkdir(parents=True)
    for name in accelopt.CONFIG_NAMES:
        (prepared / 'configs' / name).write_text(json.dumps({'url':'http://127.0.0.1:3000/v1','model':'fixture-model','api_key':'None'}))
    (prepared / 'task.py').write_text('# controlled task fixture, never imported\n')
    (prepared / 'kernel.py').write_text('# controlled kernel fixture, never imported\n')
    (prepared / 'profile_results.csv').write_text('service_name,task,kernel,profile,problem,values,case_name\nfixture,inputs/accelopt/task.py,inputs/accelopt/kernel.py,{},fixture,1,fixture\n')
    return accelopt, path, prepared


def test_accelopt_positional_correction_is_narrow_hash_checked_and_works_in_bash(tmp_path, monkeypatch):
    module, source, _ = accelopt_fixture(tmp_path, monkeypatch)
    raw = source.read_bytes()
    patched = module.corrected_template(raw)
    assert patched.replace(b'${10}',b'$10').replace(b'${11}',b'$11').replace(b'${12}',b'$12').replace(b'${13}',b'$13').replace(b'${14}',b'$14').replace(b'${15}',b'$15') == raw
    script = tmp_path / 'fixture.sh'; script.write_bytes(patched)
    result = subprocess.check_output(['bash', str(script), *[str(i) for i in range(1,16)]],text=True)
    assert result == '10|11|12|13|14|15'
    with pytest.raises(ValueError, match='pinned source'):
        module.corrected_template(raw + b'# changed\n')
    assert source.read_bytes() == raw


def test_accelopt_delegates_complete_template_and_records_patch_provenance(tmp_path, monkeypatch):
    module, source, prepared = accelopt_fixture(tmp_path, monkeypatch)
    original = source.read_bytes()
    monkeypatch.setattr(module.shutil, 'which', lambda binary: '/prepared/bin/' + binary)
    calls=[]
    output = tmp_path / 'native-results'
    def native(argv, **kwargs):
        calls.append((argv,kwargs))
        names=['arena-initial','arena-09-21-12-00','arena-09-21-12-01']
        (output / 'log.txt').write_text('\n'.join(names)+'\n')
        for name in names:
            directory=output/name;directory.mkdir(exist_ok=True)
            (directory/'executor_results.json').write_text('[]')
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(module.subprocess,'run',native)
    code=module.main(['--prepared-dir','inputs/accelopt','--project','fixture-project','--organization','fixture-org','--iterations','2','--output',str(output)])
    assert code == 0 and len(calls) == 1
    argv, options=calls[0]
    assert argv[:2] == ['bash',str(output/'arena-native-loop.sh')]
    assert argv[2:9] == [str(output),'arena-initial','arena','0','fixture-project','2e-05','fixture-org']
    assert argv[9:] == ['2','12','6','2','1.04','1.15','8','16']
    assert options['env']['ACCELOPT_BASE_DIR'] == str(tmp_path.resolve())
    manifest=json.loads((output/'arena-patch.json').read_text())
    assert manifest['native_initial_passes'] == 1 and manifest['native_feedback_iterations'] == 2
    assert manifest['source_sha256'] == hashlib.sha256(original).hexdigest()
    assert manifest['execution_copy_sha256'] == digest_bytes(output/'arena-native-loop.sh')
    assert len(manifest['changes']) == 6 and source.read_bytes() == original
    assert str(prepared/'kernel.py') in (output/'arena-initial/candidates/profile_results.csv').read_text()


def digest_bytes(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_accelopt_refuses_literal_config_credentials_before_launch(tmp_path, monkeypatch):
    module, _, prepared = accelopt_fixture(tmp_path, monkeypatch)
    config=prepared/'configs/planner_config.json'
    config.write_text(json.dumps({'url':'http://localhost:3000/v1','model':'fixture','api_key':'fixture-secret'}))
    with pytest.raises(ValueError,match='nonsecret placeholder'):
        module.main(['--prepared-dir','inputs/accelopt','--project','fixture','--organization','fixture','--iterations','1','--output',str(tmp_path/'output')])
    assert not (tmp_path/'output').exists()


def test_accelopt_exit_zero_without_complete_native_outputs_is_not_success(tmp_path, monkeypatch):
    module, _, _ = accelopt_fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(module.shutil,'which',lambda binary:'/prepared/'+binary)
    monkeypatch.setattr(module.subprocess,'run',lambda *args,**kwargs:SimpleNamespace(returncode=0))
    with pytest.raises(ValueError,match='every expected execution stage'):
        module.main(['--prepared-dir','inputs/accelopt','--project','fixture','--organization','fixture','--iterations','1','--output',str(tmp_path/'output')])
