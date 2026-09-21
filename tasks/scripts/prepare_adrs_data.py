#!/usr/bin/env python3
"""Fetch the original Cloudcast/LLM-SQL data at locked revision and SHA256.

Only files in the selected reviewed dataset lock are requested.
No evaluator, solver, API client or model is executed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "suite" / "_lib"))
from arena_task_paths import runtime_path


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        while block:=f.read(1024*1024):h.update(block)
    return h.hexdigest()


def contained(root,name):
    p=(root/name).resolve()
    if not p.is_relative_to(root.resolve()):raise ValueError('Unsafe data destination: '+name)
    return p


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--verify-only',action='store_true')
    parser.add_argument('--lock',choices=['adrs-data-lock.json','eplb-data-lock.json'],default='adrs-data-lock.json')
    parser.add_argument('--suite',action='store_true',help='also prepare cached ADRS data for the bundled suite evaluators')
    args=parser.parse_args();root=args.root.resolve()
    lock=json.loads((root/'catalog'/args.lock).read_text())
    cache=runtime_path(lock.get('cache_directory','.cache/datasets/adrs-data'))/lock['commit']
    verified=[]
    for row in lock['files']:
        source=contained(cache,row['path'])
        if not source.is_file() or digest(source)!=row['sha256']:
            if args.verify_only:raise ValueError('Missing or modified cached data: '+row['path'])
            source.parent.mkdir(parents=True,exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=source.parent,delete=False) as tmp:
                temp=Path(tmp.name)
                try:
                    with urllib.request.urlopen(row['url'],timeout=60) as response:
                        shutil.copyfileobj(response,tmp)
                    tmp.flush()
                    if temp.stat().st_size!=row['size_bytes'] or digest(temp)!=row['sha256']:
                        raise ValueError('Downloaded data hash/size mismatch: '+row['path'])
                    temp.replace(source)
                finally:
                    temp.unlink(missing_ok=True)
        destinations=list(row['destinations'])
        if args.suite:
            prefix='eplb/' if args.lock=='eplb-data-lock.json' and not row['path'].startswith('eplb/') else ''
            destinations.append('suite/_lib/vendor/adrs/'+prefix+row['path'])
        for name in destinations:
            target=runtime_path(name)
            if target.exists():
                if not target.is_file() or digest(target)!=row['sha256']:
                    raise ValueError('Existing dataset differs; retain it or move it before retrying: '+name)
            elif args.verify_only:raise ValueError('Missing evaluator data: '+name)
            else:
                target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(source,target)
        verified.append(row['path'])
    print(json.dumps({'status':'verified','dataset_commit':lock['commit'],'files':len(verified),'total_bytes':lock['total_bytes']}))


if __name__=='__main__':main()
