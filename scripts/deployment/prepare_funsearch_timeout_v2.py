#!/usr/bin/env python3
"""Prepare seven original-author FunSearch timeout-v2 templates; never admit/run."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from arena.frameworks.drivers.base_gateway import MODELS

IDENTITY = 'funsearch-original-timeout-v2'


def templates(root, bubblewrap):
    items = []
    for model in MODELS:
        slug = model.replace('.', '-')
        spec = {'schema': 'arena.native-run/1', 'framework': IDENTITY,
                'source_dir': str(root / 'sources/funsearch-original'), 'output_dir': '{output_dir}',
                'timeout_seconds': 2400, 'environment_names': ['OPENAI_API_KEY'],
                'request': {'python': str(root / 'envs/funsearch-original/bin/python'),
                            'profile': 'gateway-cpu-pilot', 'arguments': ['--model', model, '--max-samples', '6'],
                            'executables': {'bubblewrap': str(bubblewrap)}}}
        items.append({'id': 'cpu-funsearch-original-timeout-v2-' + slug,
                      'name': 'FunSearch original · timeout v2 · ' + model,
                      'framework': IDENTITY, 'profile': 'gateway-cpu-pilot', 'model': model,
                      'status': 'ready', 'blocked_reason': None,
                      'resources': {'cpus': 4, 'memory_mb': 8192, 'evaluation_slots': 1, 'pids': 512},
                      'containment': 'cgroup-v2', 'evaluation_concurrency_verified': True, 'spec': spec})
    return items


def prepare(root, destination, bubblewrap):
    from arena.control import validate_config
    from arena.frameworks.runtime import prepare_plan
    if not root.is_absolute() or not destination.is_absolute() or destination.exists():
        raise ValueError('Use absolute paths and a new destination')
    items = templates(root, bubblewrap)
    plans = [prepare_plan({**item['spec'], 'output_dir': str(root / 'runs' / (item['id'] + '-plan-only'))}) for item in items]
    validate_config({'schema': 'arena.control/1', 'state_dir': str(root / 'control'),
                     'cgroup_root': '/sys/fs/cgroup/arena-workers',
                     'limits': {'cpus': 96, 'memory_mb': 307200, 'evaluation_slots': 32, 'max_active': 4,
                                'max_queued': 2048, 'max_runs_per_key': 2048, 'max_reserved_seconds_per_key': 6048000},
                     'templates': items})
    destination.mkdir(parents=True, mode=0o750)
    for item, plan in zip(items, plans):
        (destination / (item['model'] + '.plan.json')).write_text(json.dumps(plan, indent=2) + '\n')
    (destination / 'templates.json').write_text(json.dumps(items, indent=2) + '\n')
    proof = {'schema': 'arena.funsearch-timeout-v2-preparation/1', 'framework': IDENTITY,
             'model_calls': 0, 'research_executed': False, 'admitted': False,
             'canonical_evaluation': False, 'sdk_timeout_seconds': 330, 'sdk_max_retries': 0,
             'expected_gateway_timeout_seconds': 300, 'outer_timeout_seconds': 2400, 'max_samples': 6,
             'task': {'kind': 'constant-weight admissible set', 'input': [9, 5]},
             'plans': [{'model': item['model'], 'plan_sha256': plan['sha256'], 'source': plan['source']} for item, plan in zip(items, plans)],
             'helper_hashes': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in [
                 'src/arena/frameworks/drivers/funsearch_gateway.py',
                 'src/arena/frameworks/drivers/funsearch_original_timeout_v2.py',
                 'src/arena/frameworks/drivers/funsearch_original.py',
                 'src/arena/frameworks/drivers/_namespace_sandbox.py']}}
    (destination / 'preparation.json').write_text(json.dumps(proof, indent=2) + '\n')
    return proof


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--root', type=Path, default=Path('/srv/arena'))
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--bubblewrap', type=Path, default=Path('/usr/bin/bwrap'))
    args = parser.parse_args()
    proof = prepare(args.root, args.destination, args.bubblewrap)
    print(json.dumps({'templates': len(proof['plans']), 'destination': str(args.destination), 'model_calls': 0, 'admitted': False}))


if __name__ == '__main__': main()
