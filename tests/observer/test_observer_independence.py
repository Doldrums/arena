"""The extracted observer must work without SCiEL or a model-client dependency."""
from pathlib import Path
import subprocess
import sys


def test_all_observer_modules_import_with_framework_and_model_clients_forbidden():
    source = Path(__file__).resolve().parents[2] / 'src'
    script = '''
import importlib
import importlib.abc
import pkgutil
import sys
sys.path.insert(0, sys.argv[1])
class RejectFrameworkImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'sciel', 'openai'}:
            raise AssertionError('Observer attempted a framework dependency: ' + fullname)
sys.meta_path.insert(0, RejectFrameworkImports())
import arena.observers.sciel
for item in pkgutil.walk_packages(arena.observers.sciel.__path__, 'arena.observers.sciel.'):
    importlib.import_module(item.name)
from arena.observers.sciel.data import RunStore
assert RunStore([]).discover() == []
assert not any(name == 'sciel' or name.startswith('sciel.') for name in sys.modules)
'''
    result = subprocess.run([sys.executable, '-I', '-c', script, str(source)],
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr


def test_timing_cache_uses_user_cache_even_when_started_inside_a_run(tmp_path, monkeypatch):
    from arena.server import default_timing_cache_dir
    run = tmp_path / 'run'
    run.mkdir()
    monkeypatch.chdir(run)
    monkeypatch.setenv('XDG_CACHE_HOME', str(tmp_path / 'user-cache'))
    assert default_timing_cache_dir([run]) == tmp_path / 'user-cache/arena/timing'
    assert list(run.iterdir()) == []


def test_timing_cache_persistence_is_disabled_for_overlapping_roots_and_symlinks(tmp_path, monkeypatch):
    from arena.server import DashboardServer, default_timing_cache_dir, observer_cache_dir
    root = tmp_path / 'watched'
    root.mkdir()
    cache = root / 'arena/timing'
    monkeypatch.setenv('XDG_CACHE_HOME', str(root))
    assert default_timing_cache_dir([root]) is None
    alias = tmp_path / 'alias'
    alias.symlink_to(root, target_is_directory=True)
    assert observer_cache_dir([alias], cache) is None
    assert observer_cache_dir([cache / 'nested-run'], cache) is None
    server = DashboardServer(('127.0.0.1', 0), [root], timing_cache_dir=cache)
    try:
        assert server.store.timing_monitor.cache_dir is None
        server.store.timing_monitor._save('fixture-run', {'hypotheses': []})
        assert list(root.iterdir()) == []
    finally:
        server.server_close()
