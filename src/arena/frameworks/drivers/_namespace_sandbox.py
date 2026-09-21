"""Linux user/mount/PID/network namespace sandbox for native FunSearch scorers.

The native reconstructed program and scoring function are unchanged. Only the
caller-supplied Sandbox.run execution boundary is implemented here.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import resource
import re
import signal
import subprocess
import sys
import tempfile
from types import ModuleType


def child_main():
    payload = json.loads(Path('/work/input.json').read_text())
    try:
        # Decorators are native specification markers, not an imported engine.
        markers = ModuleType('funsearch')
        markers.run = markers.evolve = lambda function: function
        sys.modules['funsearch'] = markers
        namespace = {'funsearch': markers}
        exec(compile(Path('/work/program.py').read_text(), '/work/program.py', 'exec'), namespace)
        argument = payload['input']
        if payload['input_kind'] == 'tuple': argument = tuple(argument)
        value = namespace[payload['function']](argument)
        if hasattr(value, 'item'): value = value.item()
        result = {'output': value, 'runs_ok': True}
        encoded = json.dumps(result, allow_nan=True)
    except BaseException as exc:
        encoded = json.dumps({'output': None, 'runs_ok': False, 'error_type': type(exc).__name__})
    Path('/result/score.json').write_text(encoded)


def command(bubblewrap, directory, python=None, prefix=None, base_prefix=None):
    python = str(python or sys.executable)
    prefix, base_prefix = Path(prefix or sys.prefix), Path(base_prefix or sys.base_prefix)
    root = Path(directory)
    argv = [str(bubblewrap), '--unshare-all', '--die-with-parent', '--new-session', '--cap-drop', 'ALL',
            '--proc', '/proc', '--dev', '/dev', '--tmpfs', '/tmp', '--dir', '/work', '--dir', '/result']
    for path in ('/usr/lib', '/lib', '/lib64', '/etc/ld.so.cache'):
        if Path(path).exists(): argv += ['--ro-bind', path, path]
    for path in dict.fromkeys((str(base_prefix), str(prefix))):
        argv += ['--ro-bind', path, path]
    # uv-managed Python may expose a versionless directory alias in pyvenv.cfg.
    # Python resolves its stdlib relative to that home even in isolated mode.
    runtime_aliases = [base_prefix]
    configuration = prefix / 'pyvenv.cfg'
    if configuration.is_file():
        matches = re.findall(r'^home\s*=\s*(.+)$', configuration.read_text(), re.MULTILINE)
        if len(matches) == 1:
            alias = Path(matches[0].strip()).parent
            if alias.is_absolute() and alias != base_prefix and alias.resolve() == base_prefix.resolve():
                argv += ['--ro-bind', str(base_prefix), str(alias)]
                runtime_aliases.append(alias)
    # A venv created by another venv can point through that environment's
    # bin/python. Mount the actual binary at the intermediate target, without
    # exposing the other environment, host application, or configuration tree.
    executable = Path(python)
    target = executable
    seen = set()
    while target.is_symlink():
        if target in seen or len(seen) >= 16:
            raise ValueError('Interpreter symlink chain is cyclic or too deep')
        seen.add(target)
        link = Path(os.readlink(target))
        target = Path(os.path.normpath(link if link.is_absolute() else target.parent / link))
        if not target.is_relative_to(prefix) and not any(target.is_relative_to(p) for p in runtime_aliases):
            argv += ['--ro-bind', str(executable.resolve(strict=True)), str(target)]
            break
    argv += ['--ro-bind', str(Path(__file__).resolve()), '/work/runner.py',
             '--ro-bind', str(root / 'program.py'), '/work/program.py',
             '--ro-bind', str(root / 'input.json'), '/work/input.json',
             '--bind', str(root / 'result'), '/result', '--chdir', '/work',
             '--clearenv', '--setenv', 'HOME', '/tmp', '--setenv', 'TMPDIR', '/tmp',
             '--setenv', 'OMP_NUM_THREADS', '1', '--setenv', 'OPENBLAS_NUM_THREADS', '1',
             '--setenv', 'MKL_NUM_THREADS', '1', '--setenv', 'NUMEXPR_NUM_THREADS', '1',
             python, '-I', '/work/runner.py']
    return argv


class NamespaceSandbox:
    def __init__(self, bubblewrap, base_path, **kwargs):
        self.bubblewrap = Path(bubblewrap)
        if not self.bubblewrap.is_absolute() or not os.access(self.bubblewrap, os.X_OK):
            raise ValueError('An explicit executable bubblewrap is required')
        self.base_path = Path(base_path) / 'namespace-sandbox'
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.call_count = 0

    def run(self, program, function_to_run, test_input, timeout_seconds):
        if not isinstance(program, str) or len(program.encode()) > 1024*1024 or not function_to_run.isidentifier():
            raise ValueError('Native sandbox program/function is invalid or too large')
        timeout = min(max(float(timeout_seconds), 1), 60)
        def limits():
            resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
            resource.setrlimit(resource.RLIMIT_FSIZE, (4*1024*1024, 4*1024*1024))
            resource.setrlimit(resource.RLIMIT_AS, (2*1024**3, 2*1024**3))
            resource.setrlimit(resource.RLIMIT_CPU, (int(timeout)+1, int(timeout)+1))
        self.call_count += 1
        with tempfile.TemporaryDirectory(prefix='call-', dir=self.base_path) as temporary:
            root = Path(temporary); (root/'result').mkdir()
            (root/'program.py').write_text(program)
            (root/'input.json').write_text(json.dumps({'function': function_to_run, 'input': test_input,
                                                      'input_kind': 'tuple' if isinstance(test_input, tuple) else 'json'}))
            with (root/'stdout.log').open('wb') as stdout, (root/'stderr.log').open('wb') as stderr:
                process = subprocess.Popen(command(self.bubblewrap, root), stdin=subprocess.DEVNULL,
                                           stdout=stdout, stderr=stderr, env={'PATH':'/usr/bin:/bin'},
                                           start_new_session=True, preexec_fn=limits)
                try: process.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL); process.wait()
                    return None, False
            result = root/'result/score.json'
            if process.returncode != 0 or not result.is_file() or result.is_symlink() or result.stat().st_size > 4096:
                return None, False
            try: value = json.loads(result.read_text())
            except (ValueError, UnicodeError): return None, False
            if type(value) is not dict or type(value.get('runs_ok')) is not bool: return None, False
            return value.get('output'), value['runs_ok']


if __name__ == '__main__':
    child_main()
