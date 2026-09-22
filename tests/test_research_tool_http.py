"""Research API grants do not expose general Docker routes."""
import json

import pytest

from arena.evaluator_policy import Denied
from arena.research_tool_http import route
from arena.research_tool_server_config import Config

IMAGE = 'sha256:' + 'a' * 64
IDENT = 'b' * 64
NAME = 'sciel-method-' + 'c' * 32


@pytest.mark.parametrize('version', ['', '/v1.49'])
@pytest.mark.parametrize('method,path,action', [
    ('HEAD', '/_ping', 'ping'), ('GET', '/version', 'version'),
    ('GET', '/images/' + IMAGE + '/json', 'image'),
    ('GET', '/images/' + IMAGE.replace(':', '%3A') + '/json', 'image'),
    ('POST', '/containers/create?name=' + NAME, 'create'),
    ('GET', '/containers/' + IDENT + '/json', 'json'),
    ('POST', '/containers/' + IDENT + '/start', 'start'),
    ('POST', '/containers/' + IDENT + '/wait?condition=next-exit', 'wait'),
    ('POST', '/containers/' + IDENT + '/attach?stream=1&stdout=1&stderr=1', 'attach'),
    ('DELETE', '/containers/' + IDENT + '?force=1', 'delete'),
])
def test_native_endpoint_families(version, method, path, action):
    checked = route(method, version + path, IMAGE)
    assert checked[0] == version and checked[1] == action


@pytest.mark.parametrize('method,path', [
    ('GET', '/info'), ('GET', '/containers/json'), ('POST', '/build'),
    ('GET', '/images/other/json'), ('GET', '/images/' + IMAGE + '/json?x=1'),
    ('GET', '/images/sha256%253A' + 'a' * 64 + '/json'),
    ('POST', '/containers/create?name=' + NAME + '&name=' + NAME),
    ('POST', '/containers/create?name=arena-eval-' + 'c' * 32),
    ('POST', '/containers/' + IDENT + '/exec'),
    ('GET', '/containers/' + IDENT + '/archive'),
    ('POST', '/containers/' + IDENT + '/attach?stdin=1'),
    ('POST', '/containers/' + IDENT + '/start?extra=1'),
    ('DELETE', '/containers/' + IDENT + '?force=1&v=1'),
    ('DELETE', '/containers/' + IDENT),
    ('GET', 'http://localhost/containers/' + IDENT + '/json'),
    ('GET', '/containers/' + IDENT + '/json#fragment'),
])
def test_general_docker_capabilities_denied(method, path):
    with pytest.raises((Denied, ValueError)):
        route(method, path, IMAGE)


def configuration(tmp_path):
    return dict(docker_socket='/var/run/docker.sock', socket_path='/run/arena-research-tools/docker.sock',
        staging_root='/run/research-stage', receipts_root='/var/lib/arena/research-receipts',
        policy=dict(image_id=IMAGE, runtime_dir='/opt/arena/research-runtime',
            run_roots=['/srv/arena/control/runs'], engine_registry='/run/engine-registry',
            engine_staging_root='/run/engine-stage', runtime_sha256='d' * 64))


@pytest.mark.parametrize('change', ['unknown', 'uid', 'overlap', 'relative', 'same_socket', 'tag'])
def test_configuration_rejects_unreviewed_grants(tmp_path, change):
    data = configuration(tmp_path)
    if change == 'unknown': data['max_containers'] = 100
    if change == 'uid': data['policy']['worker_uid'] = 0
    if change == 'overlap': data['staging_root'] = data['policy']['engine_staging_root']
    if change == 'relative': data['receipts_root'] = 'relative'
    if change == 'same_socket': data['socket_path'] = data['docker_socket']
    if change == 'tag': data['policy']['image_id'] = 'python:latest'
    path = tmp_path / 'config.json'
    path.write_text(json.dumps(data))
    with pytest.raises(Denied):
        Config.read(path)


def test_explicit_separate_configuration(tmp_path):
    path = tmp_path / 'config.json'
    path.write_text(json.dumps(configuration(tmp_path)))
    config = Config.read(path)
    assert config.timeout_seconds == 30 and config.max_containers == 4
    assert config.policy.image_id == IMAGE
