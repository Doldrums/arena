#!/usr/bin/env python3
"""Explicitly fetch registered public source pins; never install or execute them."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
from pathlib import Path
import re
import subprocess

def fetch(item, root):
    name, repo = item
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]*', name) or not re.fullmatch(r'https://github.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo['url']) or not re.fullmatch(r'[0-9a-f]{40}',repo['commit']):
        raise ValueError('Invalid pinned repository identity')
    path=root/name
    env={k:v for k,v in os.environ.items() if not k.startswith('GIT_')}
    env.update(GIT_CONFIG_GLOBAL=os.devnull,GIT_CONFIG_NOSYSTEM='1',GIT_TERMINAL_PROMPT='0')
    def git(*args):
        return subprocess.run(['git','--no-replace-objects','-c','core.hooksPath=/dev/null','-C',str(path),*args],env=env,capture_output=True,text=True,check=True,timeout=600).stdout.strip()
    try:
        if path.exists():
            if path.is_symlink() or git('status','--porcelain','--untracked-files=all'):
                raise ValueError('Existing checkout is not clean')
            if git('rev-parse','HEAD')!=repo['commit']:
                raise ValueError('Existing checkout is at a different pin')
        else:
            path.mkdir(parents=True)
            git('init','--quiet')
            git('remote','add','origin',repo['url'])
            git('fetch','--quiet','--depth=1','origin',repo['commit'])
            git('checkout','--quiet','--detach','FETCH_HEAD')
        return {'framework':name,'status':'source_verified','commit':git('rev-parse','HEAD')}
    except (subprocess.SubprocessError,OSError,ValueError):
        return {'framework':name,'status':'fetch_failed','commit':repo['commit']}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registry',type=Path,required=True)
    parser.add_argument('--sources',type=Path,required=True)
    parser.add_argument('--report',type=Path,required=True)
    parser.add_argument('--jobs',type=int,default=4,choices=range(1,9))
    args=parser.parse_args()
    repos={}
    for path in sorted((args.registry/'framework-recipes').glob('*.json')):
        for recipe in json.loads(path.read_text())['recipes']:
            if recipe['status']=='source_verified': repos[recipe['id']]=recipe['repository']
    for name in ('shinka','dgm'):
        repos[name]=json.loads((args.registry/'participants'/f'{name}.json').read_text())['repository']
    # SCiEL stays private and is transferred separately by the operator.
    args.sources.mkdir(parents=True,exist_ok=True)
    results=[]
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        for future in as_completed([pool.submit(fetch,item,args.sources) for item in repos.items()]):
            result=future.result();results.append(result);print(json.dumps(result),flush=True)
    args.report.write_text(json.dumps({'schema':'arena.deployment-sources/1','sources':sorted(results,key=lambda item:item['framework'])},indent=2)+'\n')
    args.report.chmod(0o600)
    return int(any(item['status']!='source_verified' for item in results))

if __name__=='__main__':
    raise SystemExit(main())
