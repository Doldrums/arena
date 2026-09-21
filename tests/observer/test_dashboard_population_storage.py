"""Storage view never substitutes map bins or niche IDs for actual vectors."""
from copy import deepcopy
import math

import pytest

from arena.observers.sciel.population import population_view
from arena.observers.sciel.population_storage import project_vectors


def checkpoint(kind='legacy', descriptor='code_length'):
    return dict(iteration_no=4,B_evals=3,config=dict(container={'kind':kind},grid_bins=10),
        identity={'descriptor':{'kind':descriptor}},db=dict(
        programs=[dict(id='p1',score=.4,gen=0),dict(id='p2',score=.7,gen=1),dict(id='old',score=.8,gen=1)],
        islands=[dict(idx=0,members=['p1','p2'],best_id='p2',grid={'2,4':'p1','5,7':'p2'})],archive=['old']))


def view(cp, rows=None):
    return population_view(cp,rows or [],{}, {})


def point(ident, vector):
    return dict(id=ident,kind='centroid',island_id=None,program_id=None,niche_id=ident,vector=vector)


def test_map_elites_has_two_recorded_axes_not_program_embeddings():
    cp=checkpoint();before=deepcopy(cp);result=view(cp);storage=result['storage']
    assert cp==before and storage['kind']=='map_elites'
    assert storage['native_dimensions']==2 and storage['input_dimensions'] is None
    assert storage['axes'][0]['label']=='Code length bin'
    assert storage['axes'][1]['label']=='Score bin' and storage['bins']=={'x':10,'y':10}
    assert [(a['program_id'],a['cell']) for a in storage['assignments']]==[('p1',[2,4]),('p2',[5,7])]
    assert storage['projection']['available'] is False
    assert result['archive']['members'][0]['id']=='old'
    cp['identity']['descriptor']={'kind':'pca2_v3@abc','component':1,'explained':.077}
    storage=view(cp)['storage']
    assert storage['axes'][0]['label']=='Recorded descriptor bin'
    assert storage['input_dimensions'] is None,'no dimension guessed from a model version'
    assert storage['projection']['explained_variance'] is None,'training variance is not snapshot PCA variance'


def test_global_vq_projects_real_centroids_once_and_links_only_explicit_elites():
    cp=checkpoint(descriptor='vq_niche')
    cp['db']['niche']={'centroids':[[1.,0.,0.,0.],[0.,1.,0.,0.],[-1.,0.,0.,0.]]}
    cp['db']['islands'][0]['grid']={'0,4':'p1'}
    cp['db']['islands'].append(dict(idx=1,members=['p2'],best_id='p2',grid={'2,7':'p2'}))
    result=view(cp)['storage'];projection=result['projection']
    assert result['label']=='VQ niches × score bins'
    assert result['native_dimensions']==2 and result['input_dimensions']==4
    assert result['axes'][0]['type']=='categorical' and result['bins']['x'] is None
    assert projection['scope']=='global_codebook' and projection['stale'] is False
    assert len(projection['points'])==3 and all(p['kind']=='centroid' and p['program_id'] is None and p['island_id'] is None for p in projection['points'])
    assert projection['projected_rank']==2 and all(p['position'][2]==0 for p in projection['points'])
    assert projection['assignments']==[
        dict(island_id=0,program_id='p1',cell=[0,4],niche_id=0,score=.4,binding='recorded_elite'),
        dict(island_id=1,program_id='p2',cell=[2,7],niche_id=2,score=.7,binding='recorded_elite')]
    assert all(p['program_id'] is None for p in projection['points']), 'non-elite members get no inferred embedding'


def test_newer_journal_cannot_bind_its_cells_to_older_checkpoint_centroids():
    cp=checkpoint(descriptor='vq_niche');cp['db']['niche']={'centroids':[[1.,0.],[0.,1.]]}
    cp['db']['islands'][0]['grid']={'0,4':'p1'}
    row=dict(event='population',iteration_no=5,B_evals=4,islands=[dict(idx=0,n=3,cells=1,best=.9,
        members=[['p1',.4,0],['p2',.7,1],['new',.9,2]],grid=[[1,9,.9]])])
    result=view(cp,[row]);storage=result['storage']
    assert result['source']=='journal' and storage['assignments'][0]['program_id'] is None
    assert storage['assignments'][0]['binding']=='recorded_cell'
    assert storage['projection']['stale'] is True and storage['projection']['iteration']==4
    assert storage['projection']['assignments'][0]['program_id']=='p1'
    assert storage['projection']['assignments'][0]['niche_id']==0
    assert 'new' not in str(storage['projection'])


@pytest.mark.parametrize('kind',['cvt','vq','annealed'])
def test_explicit_geometry_overrides_legacy_vq_label_and_uses_only_active_saved_vectors(kind):
    cp=checkpoint(kind,descriptor='vq_niche');cp['db']['niche']={'centroids':[[999.]*4]}
    cp['db']['islands'][0]['grid']={'7,0':'p2'}
    cp['db']['container']=dict(schema=1,config={'kind':kind},vectors={'p1':[1.,0.,0.],'p2':[0.,1.,0.],'old':[9.,9.,9.]},
        geometries={'0':dict(centres=[[.5,.5,0.]],centre_ids=[7],config={'kind':kind,'dim':3})})
    result=view(cp)['storage'];projection=result['projection']
    assert result['kind']==kind and result['native_dimensions']==1
    assert result['axes'][0]['label']=='Centre ID within island'
    assert result['bins']=={'x':None,'y':None}
    assert projection['scope']=='checkpoint_active_members_and_centres'
    assert len(projection['points'])==3 and all(p['island_id']==0 for p in projection['points'])
    assert {p['program_id']:p['score'] for p in projection['points'] if p['kind']=='program'}=={'p1':.4,'p2':.7}
    assert projection['points'][0]['niche_id']==7 and projection['assignments'][0]['niche_id']==7
    assert 'old' not in str(projection) and '999' not in str(projection)


@pytest.mark.parametrize('kind',['pool','pool_novelty','grid'])
def test_explicit_nonlegacy_storage_wins_over_stale_descriptor_label(kind):
    cp=checkpoint(kind,descriptor='vq_niche');cp['db']['container']={'config':{'kind':kind}}
    cp['db']['niche']={'centroids':[[1.,0.]]}
    if kind!='grid':cp['db']['islands'][0]['grid']={}
    result=view(cp);storage=result['storage']
    assert storage['kind']==('map_elites' if kind=='grid' else 'pool')
    assert not storage['projection']['available']
    assert result['layout']['kind']!= 'vq'
    if kind=='grid':assert any('overrides' in note for note in storage['notes'])
    else:assert storage['native_dimensions']==0


def test_unknown_metadata_does_not_replace_it_with_current_defaults():
    result=population_view({},[],{}, {})['storage']
    assert result['kind']=='unknown' and result['native_dimensions'] is None
    assert result['axes']==[] and result['input_dimensions'] is None
    assert not result['projection']['available']
    future=checkpoint('future_storage',descriptor='vq_niche')
    assert view(future)['storage']['kind']=='unknown'
    sparse=population_view({},[],{'descriptor':{'kind':'future_custom'}},{})['storage']
    assert sparse['kind']=='unknown' and sparse['native_dimensions'] is None


def test_literal_vectors_are_validated_and_partial_bounds_are_explicit(monkeypatch):
    cp=checkpoint(descriptor='vq_niche');cp['db']['niche']={'centroids':[[1.,0.],[0.,1.],[True,0.],['0',0.]]}
    result=view(cp)['storage']['projection']
    assert result['available'] and result['recorded_count']==4 and result['projected_count']==2
    assert result['invalid_or_missing_vectors']==2 and result['limited']
    cp['db']['niche']['centroids']=[[1.,0.],[0.,1.,0.]]
    assert not view(cp)['storage']['projection']['available']
    cp['db']['niche']['centroids']=[[float('inf'),0.]]
    result=view(cp)['storage']['projection']
    assert not result['available'] and result['invalid_or_missing_vectors']==1
    cp['db']['niche']['centroids']=[[1.,0.],[0.,1.],[-1.,0.]]
    monkeypatch.setattr('arena.observers.sciel.population_storage.MAX_CENTRES',2)
    result=view(cp)['storage']['projection']
    assert result['limited'] and result['recorded_count']==3 and result['projected_count']==2


def test_pca_is_deterministic_finite_and_preserves_low_rank_geometry_without_jitter():
    points=[point(str(i),v) for i,v in enumerate([[2.,0.,0.,0.],[-2.,0.,0.,0.],[0.,1.,0.,0.],[0.,-1.,0.,0.]])]
    original=deepcopy(points);a=project_vectors(points);b=project_vectors(points)
    assert a==b and points==original
    assert a['input_dimensions']==4 and a['output_dimensions']==3 and a['projected_rank']==2
    assert a['explained_variance']==pytest.approx([.8,.2,0])
    assert a['converged'] and all(p['position'][2]==0 for p in a['points'])
    for i in range(len(points)):
        for j in range(i):
            assert math.dist(points[i]['vector'],points[j]['vector'])==pytest.approx(math.dist(a['points'][i]['position'],a['points'][j]['position']),abs=1e-8)
    one=project_vectors([point('single',[1.,2.,3.])])
    assert one['projected_rank']==0 and one['points'][0]['position']==[0.,0.,0.]
    assert one['explained_variance']==[0.,0.,0.]


def test_projection_fit_sampling_is_explicit_and_does_not_silently_drop_points(monkeypatch):
    monkeypatch.setattr('arena.observers.sciel.population_storage.MAX_FIT_POINTS',3)
    result=project_vectors([point(str(i),[float(i),float(i*i)]) for i in range(10)])
    assert result['fit_count']==3 and result['fit_population_count']==10 and result['fit_sampled']
    assert len(result['points'])==10


def test_geometry_points_keep_island_specific_centre_ids_without_cross_island_membership():
    cp=checkpoint('cvt');cp['db']['islands'].append(dict(idx=1,members=['p3'],grid={'7,0':'p3'}))
    cp['db']['islands'][0]['grid']={'7,0':'p2'}
    cp['db']['container']=dict(config={'kind':'cvt'},vectors={'p1':[1.,0.],'p2':[2.,0.],'p3':[10.,0.]},geometries={
        '0':{'centres':[[1.5,0.]],'centre_ids':[7]},'1':{'centres':[[10.,0.]],'centre_ids':[7]}})
    projection=view(cp)['storage']['projection']
    centres=[p for p in projection['points'] if p['kind']=='centroid']
    assert [p['id'] for p in centres]==['centre:0:7','centre:1:7']
    assert {(a['island_id'],a['program_id']) for a in projection['assignments']}=={(0,'p2'),(1,'p3')}


def test_pca_selects_global_leading_eigenspace_not_only_largest_diagonal_pivots():
    from itertools import product
    points=[point(str(i),[a*math.sqrt(5),b*math.sqrt(4.9),c*math.sqrt(4.8),2*d,2*d,2*d])
            for i,(a,b,c,d) in enumerate(product((-1.,1.), repeat=4))]
    result=project_vectors(points)
    assert result['converged'] and result['projected_rank']==3
    assert result['explained_variance']==pytest.approx([12/26.7,5/26.7,4.9/26.7],abs=1e-10)
    assert sum(result['explained_variance'])==pytest.approx(21.9/26.7)
    positions={p['id']:p['position'] for p in result['points']}
    assert math.dist(positions['0'],positions['1'])==pytest.approx(4*math.sqrt(3)), 'dominant correlated direction is represented'
