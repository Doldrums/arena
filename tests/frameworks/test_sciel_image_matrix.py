"""Pure private-image model-matrix transformations, with no execution."""
import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("prepare_sciel_image_matrix", ROOT / "scripts/deployment/prepare_sciel_image_matrix.py")
matrix = importlib.util.module_from_spec(spec)
spec.loader.exec_module(matrix)


def baseline():
    return {"budget": 4, "max_iterations": 6, "research": {"max_aux_calls": 1, "enabled": True},
            "llm": {"models": ["gpt-5.6-sol"], "model_capabilities": {"gpt-5.6-sol": {"temperature": False}},
                    "api_base": "http://127.0.0.1:8789/v1", "weights": [1.0]},
            "parallel_search": {"workers": 1, "host_evaluator_slots": 1, "provider_slots": 2}}


def test_six_models_only_change_identity_and_keep_baseline_unmodified():
    original = baseline(); before = copy.deepcopy(original)
    configurations = [matrix.model_configuration(original, m) for m in matrix.MODELS[1:]]
    assert len(configurations) == 6 and original == before
    for model, config in zip(matrix.MODELS[1:], configurations):
        assert config['llm']['models'] == [model]
        assert config['llm']['model_capabilities'] == {model: {'temperature': False}}
        config['llm']['models'] = before['llm']['models']
        config['llm']['model_capabilities'] = before['llm']['model_capabilities']
        assert config == before
    assert original == before


@pytest.mark.parametrize('model', ['gpt-5.6-sol', 'gpt-4o', 'local/gpt-6-astra'])
def test_no_duplicate_first_model_or_alias_substitution(model):
    with pytest.raises(ValueError, match='six remaining'):
        matrix.model_configuration(baseline(), model)


@pytest.mark.parametrize('key,value', [('budget', 12), ('max_iterations', 24), ('research', {'max_aux_calls': 4})])
def test_wrong_baseline_cannot_silently_expand_pilot_budget(key, value):
    config = baseline(); config[key] = value
    with pytest.raises(ValueError, match='reviewed successful'):
        matrix.model_configuration(config, 'gpt-6-astra')


def test_task_copy_is_data_only_and_rejects_links_and_unreviewed_files(tmp_path):
    task = tmp_path / 'arena/reference-sat'; task.mkdir(parents=True)
    for name in matrix.TASK_FILES:
        (task / name).write_text('raise RuntimeError("never import task inputs")')
    (task / 'evaluation.json').write_text(json.dumps({'task_id':'reference-sat','profile':'sciel-unit-interval/1',
        'execution':{'require_control_cgroup':True}}))
    snapshot = matrix.task_snapshot(tmp_path)
    assert len(snapshot) == 5
    (task / 'unreviewed.py').write_text('inert')
    with pytest.raises(ValueError, match='five reviewed'):
        matrix.task_snapshot(tmp_path)
    (task / 'unreviewed.py').unlink()
    (task / 'evaluator.py').unlink(); (task / 'evaluator.py').symlink_to(task / 'initial_program.py')
    with pytest.raises(ValueError, match='without symlinks'):
        matrix.task_snapshot(tmp_path)
