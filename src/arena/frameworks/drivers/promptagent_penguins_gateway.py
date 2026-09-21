"""Native PromptAgent MCTS on immutable bundled penguins, with frozen heldout."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import runpy
from pathlib import Path
import sys

from .promptagent_gateway_transport import (GatewayTransport, MODELS, PromptAgentStopped,
    REQUEST_LIMIT, install_transport, write_json)

COMMIT = '2edfc9e4462a6af97dc973442d074de9b3e876b2'
ENGINE = 'promptagent-penguins-gateway'
PROFILE = 'penguins-mcts-pilot'
DATA = 'datasets/penguins_in_a_table.json'
DATA_SHA256 = 'f743ab0bd8d500798fc0ab83fdd3547b924e9c1acb15ca11b65ac228c0ab557a'
PORT_FILES = {
    'src/prompt_optim_agent/language_model/openai_model.py': '8eea4a7c64b51e4672a52213f60c4f6d304c6c648131923ee189355dc909ac08',
    'src/prompt_optim_agent/language_model/__init__.py': 'a56dd35bd401368834967a72061436a33f8400ad665a7c3ea4e0fa840bdb3de2'}
CONFIG_SHA256 = 'f52594cf512d503003c821727fa767006761f5bdd05a2749350ae8105de8eaee'


def sha(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 32 * 1024**2:
        raise ValueError('PromptAgent evidence must be a bounded regular file')
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def ports(source):
    result = {}
    for name, digest in PORT_FILES.items():
        path = Path(source) / name
        if sha(path) != digest:
            raise ValueError('PromptAgent provider source differs from reviewed pin')
        text = path.read_text()
        if name.endswith('/openai_model.py'):
            text = text.replace('from openai import OpenAI',
                'from arena.frameworks.drivers.promptagent_gateway_transport import OpenAI', 1)
        else:
            lines = text.splitlines(keepends=True)
            disabled = {'palm':'palm_model', 'hf_text2text':'hf_text2text_model',
                        'hf_textgeneration':'hf_textgeneration_model', 'ct_model':'ct_model', 'vllm':'vllm'}
            text = ''.join(line for line in lines if not any(
                line.startswith('from .' + module + ' import') or line.lstrip().startswith('"' + name + '":')
                for name, module in disabled.items()))
        result[name] = text
    return result


def evidence(source):
    paths = [source / name for name in ('LICENSE', 'requirements.txt', 'example_config.yaml', DATA)]
    paths += sorted((source / 'src').rglob('*.py'))
    if any(path.is_symlink() for path in (source / 'src').rglob('*')):
        raise ValueError('PromptAgent source cannot contain symlinks')
    return {path.relative_to(source).as_posix(): sha(path) for path in paths}


def preparation(source, freeze):
    source = Path(source)
    if sha(source / DATA) != DATA_SHA256 or sha(source / 'example_config.yaml') != CONFIG_SHA256:
        raise ValueError('PromptAgent packaged benchmark/config differs from reviewed pin')
    return {'schema': 'arena.promptagent-preparation/1', 'source_commit': COMMIT,
        'source_files': evidence(source), 'dependency_freeze_sha256': sha(freeze),
        'provider_ports': {name: {'before': PORT_FILES[name], 'after': hashlib.sha256(text.encode()).hexdigest()}
                           for name, text in ports(source).items()}}


def native_config(source, model, output):
    if model not in MODELS:
        raise ValueError('Unknown model')
    import yaml
    config = yaml.safe_load((source / 'example_config.yaml').read_text())
    config.update(task_name='bigbench', search_algo='mcts', print_log=False, log_dir=str(output / 'native'))
    config['task_setting'].update(train_size=8, eval_size=4, test_size=4, seed=42,
                                  data_dir=str(source / DATA), post_instruction=False)
    for role in ('base', 'optim'):
        config[role + '_model_setting'].update(model_type='openai', model_name=model,
            api_key='environment:' + role, device='cpu', gpu_ids=None, model_path=None)
    config['search_setting'].update(iteration_num=2, expand_width=2, depth_limit=2, min_depth=1, w_exp=2.5)
    config['world_model_setting'].update(train_shuffle=True, train_batch_size=2,
        num_new_prompts=1, eval_batch_size=1, test_batch_size=1, print_log=False)
    return config


def split_manifest(task):
    splits = {name: [canonical_hash(row) for row in rows] for name, rows in task.dataset.items()}
    if {name: len(rows) for name, rows in splits.items()} != {'train': 8, 'eval': 4, 'test': 4}:
        raise ValueError('Unexpected native benchmark split sizes')
    sets = {name: set(rows) for name, rows in splits.items()}
    if any(len(sets[name]) != len(splits[name]) for name in splits) or any(sets[a] & sets[b] for a,b in [('train','eval'),('train','test'),('eval','test')]):
        raise ValueError('Native benchmark split overlaps or duplicate observations')
    # Forward prompts must also distinguish splits independently of their labels.
    questions = [row['question'] for rows in task.dataset.values() for row in rows]
    if len(set(questions)) != 16:
        raise ValueError('Native question overlap across prepared splits')
    return {'schema': 'arena.promptagent-native-splits/1', 'dataset_sha256': DATA_SHA256,
            'seed': 42, 'record_hashes': splits, 'disjoint': True}


def frozen_state(search):
    return [{**{key: value for key, value in node.to_dict().items() if key != 'test_metric'},
             'cum_rewards': list(node.cum_rewards)} for node in search.nodes]


def result_json(result):
    return {key: [[node.to_dict() for node in path] for path in value] if key == 'all_paths'
            else [node.to_dict() for node in value] for key, value in result.items()}


def run(source, model, output, manifest_path, freeze, *, client=None):
    source, output = Path(source).resolve(), Path(output).resolve()
    if output.exists():
        raise ValueError('PromptAgent output must be new')
    if any((path / '.env').exists() or (path / '.env').is_symlink() for path in (source, *source.parents)):
        raise ValueError('PromptAgent credentials must come from the worker environment')
    manifest = json.loads(Path(manifest_path).read_text())
    if manifest != preparation(source, freeze):
        raise ValueError('PromptAgent prepared source/data/environment provenance changed')
    output.mkdir(parents=True)
    config = native_config(source, model, output)
    write_json(output / 'native-config.json', config)
    receipt = {'schema':'arena.promptagent-pilot/1','framework':ENGINE,'model':model,'source_commit':COMMIT,
        'canonical_evaluation':False,'status':'preparing','preparation_sha256':sha(manifest_path),
        'config_sha256':sha(output/'native-config.json'),'ports':manifest['provider_ports'],
        'limits':{'mcts_iterations':2,'depth_limit':2,'expand_width':2,'train_batch_size':2,
                  'requested_prompts_per_expansion':1,'request_limit':REQUEST_LIMIT,
                  'evaluation_workers':1,'outer_timeout_seconds':2400},
        'limitations':['Small native benchmark subset, not paper reproduction or canonical task evaluation.',
            'Heldout metrics are native accuracy for frozen reward-selected paths; do not select again using test scores.',
            'Current gateway does not enforce native base/optimizer temperature0/1; no token or monetary budget claimed.',
            'A malformed optimizer response may produce no child prompts under the unchanged native parser.',
            'Extra model-emitted prompt blocks consume the same global request cap; incomplete search is not scored complete.']}
    write_json(output/'pilot-receipt.json',receipt)
    transport = GatewayTransport(model, output, client=client)
    install_transport(transport)
    for name, text in ports(source).items():
        (source/name).write_text(text)
    sys.path.insert(0,str(source/'src'))
    agent, before_test = None, None
    try:
        import torch
        torch.manual_seed(42)
        from prompt_optim_agent.agent import BaseAgent
        from prompt_optim_agent.search_algo.mcts import MCTSNode
        runpy.run_path(str(source/'src/main.py'))['validate_config'](config)
        receipt['native_config_validated'] = True
        MCTSNode.reset_id()
        agent = BaseAgent(**config)
        splits = split_manifest(agent.task)
        write_json(output/'native-splits.json',splits)
        def observe(phase):
            nonlocal before_test
            if phase == 'heldout' and before_test is None:
                before_test = frozen_state(agent.search_algo)
                write_json(output/'frozen-search-state.json',before_test)
            elif before_test is not None and phase != 'heldout':
                raise PromptAgentStopped('Native search attempted further optimization after heldout evaluation')
        transport.bind_task(agent.task, observe)
        states, result = agent.run()
        if before_test is None or before_test != frozen_state(agent.search_algo):
            raise ValueError('Native prompt/reward/search state changed during heldout evaluation')
        exported = result_json(result)
        write_json(output/'native-result.json',exported)
        selected = result['best_reward_path_selected_node'][0]
        receipt.update(status='completed', native_nodes=len(agent.search_algo.nodes),
            iterations_completed=len(states), selected_node={'id':selected.id,'reward':selected.reward,
                'heldout_accuracy':selected.test_metric}, heldout_frozen=True,
            splits_sha256=sha(output/'native-splits.json'), frozen_state_sha256=sha(output/'frozen-search-state.json'))
        return receipt
    except BaseException as error:
        receipt.update(status='stopped' if isinstance(error,PromptAgentStopped) else 'failed',error_type=type(error).__name__)
        if agent is not None:
            write_json(output/'native-partial-nodes.json',[node.to_dict() for node in agent.search_algo.nodes])
        raise
    finally:
        transport.save()
        write_json(output/'pilot-receipt.json',receipt)


def main():
    parser=argparse.ArgumentParser(description=__doc__,allow_abbrev=False)
    parser.add_argument('--model',choices=MODELS,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--preparation',type=Path,required=True)
    parser.add_argument('--dependencies',type=Path,required=True)
    args=parser.parse_args()
    try:
        run(Path.cwd(),args.model,args.output,args.preparation,args.dependencies)
    except PromptAgentStopped:
        parser.exit(1,'PromptAgent provider/budget stopped; inspect private receipt.\n')


if __name__ == '__main__':
    main()
