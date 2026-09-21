"""Inert adapter tests; real namespace checks are separate worker conformance."""
import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from arena.frameworks.drivers.funsearch_gateway import SampleBudget
from arena.frameworks.drivers import _namespace_sandbox as sandbox


def test_sample_cap_never_fabricates_an_extra_response_and_drains_native_loop():
    async def scenario():
        budget=SampleBudget(3); calls=[]; retained=[]; cleanup=[]
        async def complete(value):calls.append(value);return value
        async def native():
            try:
                for value in range(10):retained.append(await budget.complete(complete,value))
            except asyncio.CancelledError:
                cleanup.append('native evaluator queue drained')
                return 'native returned'
        assert await asyncio.wait_for(budget.run(native()),1)=='native returned'
        assert calls==retained==[0,1,2]
        assert cleanup==['native evaluator queue drained']
        assert budget.started==3 and budget.reached.is_set()
    asyncio.run(scenario())


def test_native_failure_is_not_relabelled_as_budget_success():
    async def scenario():
        budget=SampleBudget(3)
        async def native():raise RuntimeError('native failure')
        with pytest.raises(RuntimeError,match='native failure'):await budget.run(native())
        assert not budget.reached.is_set() and budget.started==0
    asyncio.run(scenario())


def test_namespace_mounts_only_runtime_and_own_input_and_clears_credentials(tmp_path):
    argv=sandbox.command('/usr/bin/bwrap',tmp_path,python='/venv/bin/python',prefix='/venv',base_prefix='/runtime')
    assert '--unshare-all' in argv and '--clearenv' in argv
    binds=[argv[i+1:i+3] for i,value in enumerate(argv) if value in ('--ro-bind','--bind')]
    assert ['/', '/'] not in binds
    assert ['/venv','/venv'] in binds and ['/runtime','/runtime'] in binds
    assert [str(tmp_path/'program.py'),'/work/program.py'] in binds
    assert [str(tmp_path/'result'),'/result'] in binds
    assert not any('/etc/arena' in value or 'OPENAI_API_KEY' in value for value in argv)
    assert argv[-3:]==['/venv/bin/python','-I','/work/runner.py']


def test_sandbox_returns_actual_child_score_without_executing_program_in_parent(monkeypatch,tmp_path):
    monkeypatch.setattr(sandbox.os,'access',lambda *args:True)
    marker=tmp_path/'must-not-exist'
    program=f'raise RuntimeError("inert fixture {marker}")'
    def popen(argv,**kwargs):
        assert kwargs['env']=={'PATH':'/usr/bin:/bin'}
        program_path=Path(argv[argv.index('/work/program.py')-1])
        assert program_path.read_text()==program
        result_dir=Path(argv[argv.index('--bind')+1])
        (result_dir/'score.json').write_text(json.dumps({'output':23,'runs_ok':True}))
        return SimpleNamespace(returncode=0,wait=lambda timeout=None:0)
    monkeypatch.setattr(sandbox.subprocess,'Popen',popen)
    scorer=sandbox.NamespaceSandbox('/usr/bin/bwrap',tmp_path)
    assert scorer.run(program,'evaluate',(6,3),30)==(23,True)
    assert scorer.call_count==1 and not marker.exists()


def test_venv_symlink_chain_mounts_only_intermediate_interpreter_not_parent_environment(tmp_path):
    prefix=tmp_path/'native-env';base=tmp_path/'base-runtime';other=tmp_path/'operator-env'
    for path in (prefix,base,other):(path/'bin').mkdir(parents=True)
    binary=base/'bin/python3.11';binary.write_bytes(b'inert interpreter fixture')
    (other/'bin/python3.11').symlink_to(binary)
    (prefix/'bin/python3.11').symlink_to(other/'bin/python3.11')
    (prefix/'bin/python').symlink_to('python3.11')
    argv=sandbox.command('/usr/bin/bwrap',tmp_path,python=prefix/'bin/python',prefix=prefix,base_prefix=base)
    binds=[argv[i+1:i+3] for i,value in enumerate(argv) if value=='--ro-bind']
    assert [str(binary),str(other/'bin/python3.11')] in binds
    assert [str(other),str(other)] not in binds


def test_uv_versionless_runtime_home_is_mounted_as_same_readonly_runtime(tmp_path):
    prefix=tmp_path/'native-env';base=tmp_path/'cpython-3.11.16';alias=tmp_path/'cpython-3.11'
    (prefix/'bin').mkdir(parents=True);(base/'bin').mkdir(parents=True)
    (base/'bin/python3.11').write_bytes(b'inert fixture')
    alias.symlink_to(base,target_is_directory=True)
    (prefix/'bin/python').symlink_to(alias/'bin/python3.11')
    (prefix/'pyvenv.cfg').write_text('home = '+str(alias/'bin')+'\n')
    argv=sandbox.command('/usr/bin/bwrap',tmp_path,python=prefix/'bin/python',prefix=prefix,base_prefix=base)
    binds=[argv[i+1:i+3] for i,value in enumerate(argv) if value=='--ro-bind']
    assert [str(base),str(alias)] in binds
    assert [str(tmp_path),str(tmp_path)] not in binds
