"""Transport-only versioning tests; no native imports, network or candidate execution."""
from contextlib import contextmanager
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from arena.frameworks.drivers import funsearch_gateway as gateway
from arena.frameworks.drivers import funsearch_original as native_driver
from arena.frameworks.drivers import funsearch_original_timeout_v2 as v2
from arena.frameworks.recipes import load_recipes, validate_recipe

ROOT = Path(__file__).resolve().parents[2]


def test_original_and_reimplementation_recipe_hashes_are_unchanged():
    recipes = load_recipes()
    expected = {'funsearch-original': '6ac3ac45d3136e27c282bf31b61527a74a1be261ad2baefcf1ad9e48096b1c7a',
                'funsearch-re-implementation': 'bd70e0c9956ac88b235bc0f1bb634c54244f17a1ccf12d66982685e191d50a21'}
    for ident, digest in expected.items():
        assert hashlib.sha256(json.dumps(recipes[ident], sort_keys=True).encode()).hexdigest() == digest
    recipe = recipes['funsearch-original-timeout-v2']
    assert validate_recipe(recipe) is recipe
    assert recipe['repository'] == recipes['funsearch-original']['repository']
    assert recipe['participant_ids'] == []  # Do not attribute the later community paper.
    assert recipe['profiles'][0]['invocation']['target'].endswith('.funsearch_original_timeout_v2')


@pytest.mark.parametrize('selected,expected', [(None, 180), (330, 330)])
def test_default180_and_explicit330_delegate_identical_native_task(monkeypatch, tmp_path, selected, expected):
    clients = []; calls = []
    def client(**kwargs):
        clients.append(kwargs)
        def completion(**request):
            calls.append(request)
            return SimpleNamespace(id='inert-response', usage=None, choices=[SimpleNamespace(message=SimpleNamespace(content='  return 0.0\n'))])
        return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=completion)))
    monkeypatch.setitem(sys.modules, 'openai', SimpleNamespace(OpenAI=client))
    monkeypatch.setenv('OPENAI_API_KEY', 'inert-local-key')
    monkeypatch.chdir(tmp_path); (tmp_path / 'implementation').mkdir()
    (tmp_path / 'implementation/specification_nonsymmetric_admissible_set.txt').write_text('inert native specification')
    @contextmanager
    def namespace(path):
        assert path == tmp_path
        yield SimpleNamespace(config_lib=SimpleNamespace(Config=lambda **k: k, ProgramsDatabaseConfig=lambda **k: k))
    monkeypatch.setattr(native_driver, 'native_namespace', namespace)
    def run(native, spec, factory, config, output, maximum, trace):
        assert spec == 'inert native specification' and factory['inputs'] == [(9, 5)]
        assert config == {'programs_database': {'num_islands': 2}, 'num_samplers': 1, 'num_evaluators': 1, 'samples_per_prompt': 1}
        assert maximum == 6 and trace == 32 * 1024**2
        assert factory['draw_sample']('inert prompt') == '  return 0.0\n'
        return 0
    monkeypatch.setattr(native_driver, 'run_native', run)
    args = SimpleNamespace(model='gpt-5.6-sol', output=tmp_path, bubblewrap=Path('/usr/bin/bwrap'), max_samples=6)
    assert gateway.original(args, **({} if selected is None else {'request_timeout': selected})) == 0
    assert clients[0]['timeout'] == expected and clients[0]['max_retries'] == 0
    assert calls[0]['model'] == 'gpt-5.6-sol' and calls[0]['n'] == 1
    assert 'timeout' not in calls[0] and 'max_tokens' not in calls[0]


def test_v2_records_transport_before_preserving_native_failure(monkeypatch, tmp_path):
    monkeypatch.setenv('OPENAI_API_KEY', 'inert-local-key')
    def fail(args, *, request_timeout):
        assert request_timeout == 330 and args.max_samples == 6
        raise TimeoutError('inert timeout; no retry')
    monkeypatch.setattr(gateway, 'original', fail)
    output = tmp_path / 'result'
    with pytest.raises(TimeoutError):
        v2.main(['--model', 'gpt-5.6-sol', '--bubblewrap', '/usr/bin/bwrap', '--output', str(output)])
    proof = json.loads((output / 'provider-seam.json').read_text())
    assert proof['transport']['sdk_timeout_seconds'] == 330
    assert proof['transport']['sdk_max_retries'] == 0 and proof['transport']['template_outer_timeout_seconds'] == 2400
    assert proof['generated_sample_budget'] == 6 and not proof['canonical_evaluation']
    assert 'inert-local-key' not in (output / 'provider-seam.json').read_text()
    with pytest.raises(ValueError, match='empty'):
        v2.main(['--model', 'gpt-5.6-sol', '--bubblewrap', '/usr/bin/bwrap', '--output', str(output)])


@pytest.mark.parametrize('extra', [['--max-samples', '8'], ['--engine', 'reimplementation'], ['--request-timeout', '600']])
def test_v2_rejects_budget_or_engine_overrides_before_any_run(extra, tmp_path):
    with pytest.raises(SystemExit):
        v2.main(['--model', 'gpt-5.6-sol', '--bubblewrap', '/usr/bin/bwrap', '--output', str(tmp_path / 'out'), *extra])
    assert not (tmp_path / 'out').exists()


def test_seven_pure_templates_keep_source_interpreter_budget_and_outer_cap():
    path = ROOT / 'scripts/deployment/prepare_funsearch_timeout_v2.py'
    spec = importlib.util.spec_from_file_location('funsearch_v2_preparation_test', path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    items = module.templates(Path('/srv/arena'), Path('/usr/bin/bwrap'))
    assert len(items) == len({item['model'] for item in items}) == 7
    for item in items:
        assert item['framework'] == item['spec']['framework'] == 'funsearch-original-timeout-v2'
        assert item['spec']['timeout_seconds'] == 2400 and item['spec']['output_dir'] == '{output_dir}'
        assert item['spec']['source_dir'] == '/srv/arena/sources/funsearch-original'
        assert item['spec']['request']['python'] == '/srv/arena/envs/funsearch-original/bin/python'
        assert item['spec']['request']['arguments'] == ['--model', item['model'], '--max-samples', '6']
        assert item['spec']['environment_names'] == ['OPENAI_API_KEY']
