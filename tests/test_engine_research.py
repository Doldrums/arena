"""Full research capabilities are opt-in and bound to the effective engine protocol."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from arena.engine_research import ResearchGrant, admit
from arena.evaluator_policy import Denied
from arena.sciel_research_profile import ENGINE_COMMIT, apply_research_profile


def configuration():
    baseline = dict(task='arena/fixture', budget=16, max_iterations=32, confirm_records=True,
        random_seed=0, llm=dict(models=['gpt-5.5'], weights=[1.0]), parallel_search={}, candidate_novelty={})
    return apply_research_profile(baseline, image_id='sha256:' + 'a' * 64, model='gpt-5.5')


def granted():
    native = configuration()
    raw = json.dumps(native).encode()
    grant = ResearchGrant(Path('/run/research/docker.sock'), Path('/opt/arena/docker'),
        'b' * 64, native['research_tools']['image_id'], (hashlib.sha256(raw).hexdigest(),))
    return SimpleNamespace(research_tools=grant, worker_uid=998, worker_gid=998), raw


@pytest.mark.parametrize('overrides', [{'budget': 17}, {'seed': 1}, {'budget': True}, {'seed': False}])
def test_cli_cannot_override_approved_science_protocol(overrides):
    config, raw = granted()
    with pytest.raises(Denied, match='CLI overrides'):
        admit(config, raw, request=overrides, engine_commit=ENGINE_COMMIT)


def test_same_values_or_no_overrides_preserve_identity():
    config, raw = granted()
    first = admit(config, raw, request={}, engine_commit=ENGINE_COMMIT)
    assert first == admit(config, raw, request={'seed': 0, 'budget': 16}, engine_commit=ENGINE_COMMIT)


def test_other_engine_source_cannot_self_declare_pinned_profile():
    config, raw = granted()
    with pytest.raises(Denied, match='exact reviewed native engine'):
        admit(config, raw, request={}, engine_commit='f' * 40)


def test_config_changes_image_substitution_and_missing_capability_fail_closed():
    config, raw = granted()
    for changed, body in ((SimpleNamespace(research_tools=None), raw),
                          (config, raw + b' '),
                          (SimpleNamespace(research_tools=replace(config.research_tools, image_id='sha256:' + 'f' * 64), worker_uid=998, worker_gid=998), raw)):
        with pytest.raises(Denied):
            admit(changed, body, request={}, engine_commit=ENGINE_COMMIT)


def test_legacy_tools_off_does_not_gain_capability():
    assert admit(SimpleNamespace(research_tools=None), b'{"research_tools":{"enabled":false}}',
                 request={}, engine_commit='legacy') is None
