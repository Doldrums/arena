"""Source-data physics tasks, with independent checks and explicit setup gates.

P12/P14 are fully specified mathematical simulation benchmarks. Other families
consume a checksum-pinned source-data pack; they never fall back to toy data.
The dataset schemas and adaptations are documented in PHYSICS_EXPANSION.md.
"""
from __future__ import annotations

from arena_task_paths import cache_path, data_root

import copy
import hashlib
import json
import math
import os
from pathlib import Path
import time

import numpy as np
from scipy.linalg import expm
from scipy.ndimage import gaussian_filter, uniform_filter
from scipy.stats import wasserstein_distance

from .runtime import CandidateError, require


def data_directory(proposal):
    root = os.environ.get('AUTORESEARCH_PHYSICS_DATA')
    if root:
        return Path(root) / proposal
    return data_root() / 'physics-expansion' / proposal


def array(value, shape=None, name='output', *, complex_ok=False):
    result = np.asarray(value)
    require(result.dtype.kind in ('iufc' if complex_ok else 'iuf'), f'{name} must be numeric')
    require(np.all(np.isfinite(result)), f'{name} must be finite')
    if shape is not None:
        require(result.shape == tuple(shape), f'{name} must have shape {tuple(shape)}; got {result.shape}')
    return result


def load_pack(proposal, directory=None):
    directory = Path(directory) if directory else data_directory(proposal)
    manifest_path = directory / 'manifest.json'
    if not manifest_path.is_file():
        raise FileNotFoundError(f'{proposal}: source-data pack missing at {directory}. Run scripts/prepare_physics_expansion.py; no synthetic fallback is allowed.')
    manifest = json.loads(manifest_path.read_text())
    require(manifest.get('proposal_id') == proposal, 'source pack belongs to another proposal')
    require(manifest.get('fixture_only') is False, 'fixtures cannot serve as benchmark data')
    require(manifest.get('source_kind') in {'experimental', 'source_simulation', 'source_model'}, 'source kind must be explicit')
    require(isinstance(manifest.get('sources'), list) and len(manifest['sources']) > 0, 'source provenance is missing')
    path = directory / 'benchmark.npz'
    require(path.is_file(), 'source data file is missing')
    require(hashlib.sha256(path.read_bytes()).hexdigest() == manifest.get('sha256'), 'source pack checksum mismatch')
    with np.load(path, allow_pickle=False) as opened:
        data = {key: opened[key] for key in opened.files}
    return data, manifest


def disjoint(train, test, label='groups'):
    require(len(set(np.asarray(train).tolist()) & set(np.asarray(test).tolist())) == 0,
            f'training and evaluation {label} overlap')


from .science_physics_observations import (
    calorimeter,
    collider,
    collider_metrics,
    crps,
    decoding_metrics,
    detection_metrics,
    exoplanets,
    gravitational_waves,
    interferometry,
    lens_forward,
    shear_bias,
    shower_features,
    strong_lensing,
    surface_code,
    tracking,
    trackml_score,
    visibility_forward,
    weak_lensing,
)


from .science_physics_turbulence import (
    closure_rollout,
    filter_velocity,
    project_solenoidal,
    turbulence,
    velocity_gradient,
)


from .science_physics_quantum_control import (
    channel_metrics,
    quantum_channel,
    quantum_control,
    quantum_model,
    quantum_seed,
)


from .science_physics_models import (
    anamak_equilibrium,
    coil_currents,
    coil_forward,
    coil_inverse,
    coil_seed,
    parratt,
    reflectometry,
    reflectometry_seed,
    tokamak,
    xy_chain,
    xy_kernel,
    xy_monte_carlo,
    xy_observables,
)


from .science_physics_seeds import (
    atmosphere_seed,
    closure_seed,
    collider_seed,
    distance_seed,
    gw_seed,
    imaging_seed,
    shear_seed,
    shower_seed,
    tracking_seed,
)


def evaluate(candidate,parameters):
    proposal=parameters['proposal_id']
    if proposal in ('P03','P07','P10') and not parameters.get('_physics_worker'):
        import sys
        environment=cache_path('physics-env')
        if Path(sys.prefix).resolve()!=environment.resolve():
            return isolated_physics_evaluate(candidate,parameters,environment)
    if proposal=='P12':return quantum_control(candidate)
    data,metadata=load_pack(proposal,parameters.get('data_directory'))
    evaluators={'P01':weak_lensing,'P02':gravitational_waves,'P03':surface_code,'P04':calorimeter,'P05':tracking,
        'P06':collider,'P07':strong_lensing,'P08':exoplanets,'P09':interferometry,'P10':tokamak,
        'P11':turbulence,'P13':reflectometry,'P14':xy_monte_carlo}
    require(proposal in evaluators,'unknown physics proposal')
    score,details=evaluators[proposal](candidate,data,metadata)
    if proposal in ('P03','P07','P10'):
        import importlib.metadata
        packages=['numpy','scipy']+({'P03':['stim','pymatching'],'P07':['lenstronomy','astropy'],'P10':['freegsnke','freegs4e']}[proposal])
        details['scientific_library_versions']={name:importlib.metadata.version(name) for name in packages}
    require(np.isfinite(score),'nonfinite scientific score')
    details['source_data_sha256']=metadata['sha256'];details['source_kind']=metadata['source_kind']
    return score,details


def isolated_physics_evaluate(candidate,parameters,environment):
    """Pinned optional solver environment, callable through the normal evaluator."""
    import subprocess
    python=Path(environment)/'bin'/'python'
    require(python.is_file(),f'Prepare {environment} using scripts/prepare_physics_expansion.py --setup-environment')
    candidate_path=getattr(candidate,'__file__',None)
    require(candidate_path is not None,'isolated physics evaluation needs a candidate program file')
    worker_parameters=dict(parameters,_physics_worker=True)
    script="from autoresearch_suite.runtime import load_program; from autoresearch_suite.science_physics_expansion import evaluate; import sys,json; score,details=evaluate(load_program(sys.argv[1]),json.loads(sys.argv[2])); print('_SCIEL_PHYSICS_RESULT_'+json.dumps([score,details],allow_nan=False))"
    environment_variables=dict(os.environ,PYTHONPATH=str(Path(__file__).resolve().parents[1]),MPLCONFIGDIR=str(Path(environment)/'matplotlib-cache'))
    result=subprocess.run([str(python),'-c',script,str(candidate_path),json.dumps(worker_parameters)],capture_output=True,text=True,timeout=850,env=environment_variables)
    require(result.returncode==0,'isolated physics evaluation failed: '+result.stderr[-1800:])
    lines=[line for line in result.stdout.splitlines() if line.startswith('_SCIEL_PHYSICS_RESULT_')]
    require(len(lines)==1,'isolated physics worker did not return exactly one result')
    score,details=json.loads(lines[0].removeprefix('_SCIEL_PHYSICS_RESULT_'))
    details['execution_environment']=str(environment);return float(score),details
