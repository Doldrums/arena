"""Known native artifact schemas, with no participant imports or code execution."""
import hashlib
import json

import pytest

from arena.results import Evidence
from arena.results_native import project_native


class MemoryEvidence:
    def __init__(self, files):
        self.files, self.reads, self.issues = files, [], set()

    def raw(self, path, limit):
        self.reads.append(path)
        data = self.files[path]
        if len(data) > limit:
            raise ValueError('bounded evidence')
        return data


def fixture(framework, values):
    files = {path: value if isinstance(value, bytes) else json.dumps(value).encode()
             for path, value in values.items()}
    native = {'schema': 'arena.native-result/1', 'framework': framework,
              'canonical_evaluation': False, 'status': 'recorded',
              'artifacts': [{'path': path, 'sha256': hashlib.sha256(data).hexdigest()}
                            for path, data in files.items()]}
    return MemoryEvidence(files), native


def circle(score, validity=1):
    return {'validity': validity, 'sum_radii': score * 2.6,
            'target_ratio': score, 'combined_score': score}


@pytest.mark.parametrize('framework,prefix', [('adaevolve','results'), ('evox','results'), ('openevolve','native')])
def test_circle_native_best_seed_iterations_and_distinct_stored_ids(framework, prefix):
    seed = {'id':'aaaa', 'parent_id':None, 'metrics':circle(.8), 'code':'private code'}
    child = {'id':'bbbb', 'parent_id':'aaaa', 'metrics':circle(.95)}
    evidence, native = fixture(framework, {
        f'{prefix}/best/best_program_info.json': {'iteration':1, 'metrics':circle(.95)},
        f'{prefix}/checkpoints/checkpoint_1/metadata.json': {'last_iteration':1},
        f'{prefix}/checkpoints/checkpoint_4/metadata.json': {'last_iteration':4},
        f'{prefix}/checkpoints/checkpoint_1/programs/aaaa.json': seed,
        f'{prefix}/checkpoints/checkpoint_4/programs/aaaa.json': seed,
        f'{prefix}/checkpoints/checkpoint_4/programs/bbbb.json': child,
    })
    result = project_native(evidence, framework, native)
    assert (result['best_score'],result['seed_score'],result['iterations'],result['candidates']) == (.95,.8,4,2)
    assert result['evaluations'] is None
    assert result['status'] == 'recorded' and not evidence.issues
    assert 'private code' not in json.dumps(result)
    assert len(result['evidence_hashes']) == 5


@pytest.mark.parametrize('invalid', [True, False, 0, None, '1'])
def test_circle_requires_native_numeric_validity(invalid):
    evidence, native = fixture('evox', {'results/best/best_program_info.json': {'metrics':circle(.9,invalid)}})
    assert project_native(evidence,'evox',native)['best_score'] is None


def test_base_does_not_confuse_bandit_rounds_with_evaluations():
    evidence, native = fixture('base', {'results/base-result.json': {
        'schema_version':'base_online_v1', 'task':'cp', 'final_best_fitness':.99,
        'init_best':.4, 'selections':[0,1,1,1], 'llm_calls':4,
        'arm_results':[{'final_metrics':circle(.4)},{'final_metrics':circle(.99)}]}})
    result = project_native(evidence,'base',native)
    assert result['best_score'] == .99 and result['seed_score'] == .4
    assert result['iterations'] == 4 and result['evaluations'] is None
    assert result['candidates'] is None


def test_eoh_minimizes_finite_objectives_and_deduplicates_source():
    evidence, native = fixture('eoh', {
        'results/results/samples/samples_best.json': {'objective':.04},
        'results/results/samples/samples_1~8.json': [
            {'objective':.05,'code':'a'}, {'objective':.04,'code':'b'},
            {'objective':None,'code':'c'}, {'objective':float('nan'),'code':'c'}],
        'results/results/pops/population_generation_2.json': [{'objective':.04}],
    })
    result = project_native(evidence,'eoh',native)
    assert result['best_score'] == .04 and result['direction'] == 'minimize'
    assert result['candidates'] == 3 and result['iterations'] == 2
    assert result['seed_score'] is None and result['evaluations'] is None


def test_meoh_preserves_pairs_without_manufacturing_scalar_best():
    evidence, native = fixture('meoh', {'results/20260921_133220/population/pop_1.json': [
        {'function':'private', 'score':[-2091.8,-.14]},
        {'function':'private2', 'score':[-2093.0,-.13]}]})
    result = project_native(evidence,'meoh',native)
    assert result['best_score'] is None and result['direction'] is None
    assert result['population_objectives'] == [
        {'negative_mean_bins':-2091.8,'negative_mean_evaluation_seconds':-.14},
        {'negative_mean_bins':-2093.0,'negative_mean_evaluation_seconds':-.13}]
    assert result['population_size'] == 2 and result['iterations'] == 1
    assert 'private' not in json.dumps(result)


@pytest.mark.parametrize('framework', ['reevo','hsevo'])
def test_selected_program_heldout_validation_is_not_training_best(framework):
    value = (2025.4 - 2012.4) / 2012.4 * 100
    stdout = ('[*] Running ...\nweibull_5k_val.pickle\n'
              '\t Average number of bins: 2025.4\n\t Lower bound on optimum: 2012.4\n'
              f'\t Excess: 0.65%\n[*] Average:\n{value}\n').encode()
    evidence,native = fixture(framework, {f'workspace/{framework}/outputs/run/2026-09-21/best_code_overall_val_stdout.txt': stdout})
    result = project_native(evidence,framework,native)
    assert result['best_score'] == value and result['metric'] == 'validation_excess_percent'
    assert 'Held-out' in result['score_kind'] and result['evaluations'] is None


def test_loongflow_excludes_execution_failure_zero_and_uses_completed_iterations():
    evidence,native = fixture('loongflow', {
        'workspace/loongflow/results/aaaa/1/executor/best_evaluation.json':
            {'status':'success','score':.99,'metrics':{'validity':1,'target_ratio':.99}},
        'workspace/loongflow/results/aaaa/2/executor/best_evaluation.json':
            {'status':'execution_failed','score':0,'metrics':{}},
        'workspace/loongflow/results/aaaa/3/executor/best_evaluation.json':
            {'status':'success','score':100,'metrics':{'validity':0,'target_ratio':100}},
    })
    result = project_native(evidence,'loongflow',native)
    assert result['best_score'] == .99 and result['iterations'] == 3
    assert result['evaluations'] is None


def test_codeevolve_requires_positive_agreeing_native_metrics_not_cpu_count():
    evidence,native = fixture('codeevolve', {'results/run_metadata.json': {
        '1': {'cpu_count':122,'best_sol':{'fitness':0,'eval_metrics':{'radii_sum':0,'benchmark_ratio':0}}},
        '4': {'cpu_count':122,'best_sol':{'fitness':.95,'eval_metrics':{'radii_sum':2.5,'benchmark_ratio':.95}}}}})
    result = project_native(evidence,'codeevolve',native)
    assert result['best_score'] == .95 and result['iterations'] == 4
    assert 'cpu_count' not in result and result['seed_score'] is None


def test_codeevolve_zero_penalty_is_not_a_valid_zero():
    evidence,native = fixture('codeevolve', {'results/run_metadata.json': {
        '1': {'best_sol':{'fitness':0,'eval_metrics':{'radii_sum':0,'benchmark_ratio':0}}}}})
    assert project_native(evidence,'codeevolve',native)['best_score'] is None


@pytest.mark.parametrize('framework', ['coevo','coevo-observed-v2'])
def test_coevo_only_explicit_validity_no_fabricated_overwritten_generation_count(framework):
    evidence,native = fixture(framework, {f'workspace/{framework}/results/oscillation_1_coevo/history/gen_0.json': {
        'generation':0,'solutions':[
            {'sol_string':'a','evaluation_res':{'valid':True,'score':-1e-6}},
            {'sol_string':'b','evaluation_res':{'valid':False,'score':0}},
            {'sol_string':'a','evaluation_res':{'valid':True,'score':-2e-6}}]}})
    result = project_native(evidence,framework,native)
    assert result['best_score'] == -1e-6 and result['metric'] == 'negative_mse'
    assert result['candidates'] == 2 and result['native_generation'] == 0
    assert result['iterations'] is None and result['evaluations'] is None


@pytest.mark.parametrize('tamper', ['hash','unlisted','duplicate','absolute','traversal'])
def test_artifact_integrity_is_required_and_bad_paths_are_never_read(tamper):
    path = 'results/best/best_program_info.json'
    evidence,native = fixture('evox',{path:{'metrics':circle(.9)}})
    if tamper == 'hash': native['artifacts'][0]['sha256'] = '0'*64
    if tamper == 'unlisted': native['artifacts'] = []
    if tamper == 'duplicate': native['artifacts'] *= 2
    if tamper == 'absolute': native['artifacts'][0]['path'] = '/private/key'
    if tamper == 'traversal': native['artifacts'][0]['path'] = '../key'
    result = project_native(evidence,'evox',native)
    assert result['best_score'] is None and result['status'] == 'partial'
    assert evidence.issues
    if tamper != 'hash': assert not evidence.reads


def test_corrupt_required_checkpoint_clears_previously_read_best():
    evidence,native = fixture('evox',{
        'results/best/best_program_info.json':{'metrics':circle(.9)},
        'results/checkpoints/checkpoint_4/metadata.json':b'{"last_iteration":4,"last_iteration":99}'})
    result = project_native(evidence,'evox',native)
    assert result['best_score'] is None and result['iterations'] is None


@pytest.mark.parametrize('score', [float('nan'),float('inf'),10**1000,True,'sk-private-value'])
def test_nonfinite_huge_boolean_and_secret_shaped_scores_never_escape(score):
    evidence,native = fixture('eoh',{'results/results/samples/samples_best.json':{'objective':score}})
    result = project_native(evidence,'eoh',native)
    assert result['best_score'] is None
    assert 'sk-private' not in json.dumps(result,allow_nan=False)


def test_unrecognized_framework_does_not_guess_any_score_key():
    evidence,native = fixture('unknown',{'score.json':{'score':100,'task':'Bearer private'}})
    result = project_native(evidence,'unknown',native)
    assert result['status'] == 'unsupported' and result['best_score'] is None
    assert not evidence.reads


def test_real_evidence_refuses_parent_symlink_even_with_matching_artifact_hash(tmp_path):
    outside = tmp_path/'outside'
    outside.mkdir()
    raw = json.dumps({'metrics':circle(.9)}).encode()
    (outside/'best_program_info.json').write_bytes(raw)
    root = tmp_path/'artifacts'
    (root/'results').mkdir(parents=True)
    (root/'results'/'best').symlink_to(outside,target_is_directory=True)
    _,native = fixture('evox',{'results/best/best_program_info.json':raw})
    result = project_native(Evidence(root),'evox',native)
    assert result['best_score'] is None and result['status'] == 'partial'


def test_native_record_identity_cannot_be_relabelled():
    evidence,native = fixture('evox',{'results/best/best_program_info.json':{'metrics':circle(.9)}})
    native['canonical_evaluation'] = True
    assert project_native(evidence,'evox',native)['best_score'] is None
    assert not evidence.reads


def darwinian_fixture(valid_marker=True):
    def organism(identity, score, parent):
        return {'organism':{'id':identity,'parent_id':parent,'code_block':'PRIVATE'},
                'evaluation_result':{'score':score,'is_viable':True,'trainable_failure_cases':[
                    {'error_message':'Valid but suboptimal configuration.' if valid_marker else 'Execution failed',
                     'sum_of_radii':score}]}}
    seed, child = organism('aaaa',2.1,None), organism('bbbb',2.5,'aaaa')
    rows = [{'iteration':0,'population':{'organisms':[seed]}},
            {'iteration':1,'population':{'organisms':[seed,child]}}]
    return fixture('darwinian-evolver-gateway', {
        'native/provider-seam.json':{'schema':'arena.native-provider-seam/1',
            'recipe':'darwinian-evolver-gateway','source_commit':'7f12365d2059c47e29068a5a6f498a293148d2a9',
            'native_argv':['circle_packing','--num_iterations','1'],'native_evaluator_modified':False},
        'native/results.jsonl':('\n'.join(json.dumps(row) for row in rows)+'\n').encode(),
        'native/snapshots/iteration_1.pkl': b'opaque, must never be opened',
    })


def test_darwinian_uses_native_validation_marker_never_pickle():
    evidence,native = darwinian_fixture()
    result = project_native(evidence,'darwinian-evolver-gateway',native)
    assert result['best_score'] == 2.5 and result['seed_score'] == 2.1
    assert result['metric'] == 'sum_radii' and result['iterations'] == 1
    assert result['candidates'] == 2 and result['evaluations'] is None
    assert not any(path.endswith('.pkl') for path in evidence.reads)
    assert 'PRIVATE' not in json.dumps(result)


def test_darwinian_is_viable_does_not_mean_packing_is_valid():
    evidence,native = darwinian_fixture(valid_marker=False)
    assert project_native(evidence,'darwinian-evolver-gateway',native)['best_score'] is None
