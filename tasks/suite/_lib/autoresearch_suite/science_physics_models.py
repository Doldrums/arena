"""Reflectometry, XY Monte Carlo and tokamak equilibrium evaluation."""
from __future__ import annotations

from .science_physics_expansion import (
    CandidateError,
    array,
    crps,
    math,
    np,
    require,
)

def parratt(q,parameters,solvent_sld,q_fwhm=None):
    """Independent four-medium Parratt recursion; lengths A, SLD 1e-6/A^2."""
    oxide,film,dry,solvent_fraction,roughness,background=np.asarray(parameters,float)
    rho=np.array([2.07,3.47,dry+solvent_fraction*solvent_sld,solvent_sld])*1e-6
    q=np.asarray(q,float)
    if q_fwhm is not None:
        nodes,weights=np.polynomial.hermite.hermgauss(15)
        shifted=np.maximum(1e-8,q[:,None]+np.asarray(q_fwhm)[:,None]/math.sqrt(8*math.log(2))*math.sqrt(2)*nodes)
        return (parratt(shifted.ravel(),parameters,solvent_sld).reshape(len(q),-1)@weights)/math.sqrt(np.pi)
    kz=np.sqrt((q[:,None]/2)**2-4*np.pi*(rho[None,:]-rho[0])+0j)
    thickness=[0,oxide,film,0]; reflection=np.zeros(len(q),complex)
    for j in range(2,-1,-1):
        interface=(kz[:,j]-kz[:,j+1])/(kz[:,j]+kz[:,j+1]+1e-300)
        interface*=np.exp(-2*kz[:,j]*kz[:,j+1]*roughness**2)
        phase=np.exp(2j*kz[:,j+1]*thickness[j+1])
        reflection=(interface+reflection*phase)/(1+interface*reflection*phase)
    return np.abs(reflection)**2+background


def reflectometry(candidate,data,metadata):
    require(metadata.get('split_unit')=='complete_contrast','reflection observations must split complete contrasts, not neighboring q points')
    bounds=np.asarray(metadata['bounds']); losses=[]; details=[]
    for case in metadata['cases']:
        train=[]
        for identifier in case['train']:
            values=data[identifier]
            train.append({'q':values[:,0].copy(),'reflectivity':values[:,1].copy(),'errors':values[:,2].copy(),
                          'q_fwhm':values[:,3].copy(),'solvent_sld':metadata['contrasts'][identifier]})
        require(case['test'] not in case['train'],'training/test contrast overlap')
        samples=array(candidate.infer_profile(train,bounds.tolist(),{'sample_id':case['sample_id'],
            'parameter_names':['oxide_A','film_A','dry_SLD','solvent_fraction','roughness_A','background'],
            'solvent_sld_test':metadata['contrasts'][case['test']]}),name='SLD profile posterior')
        require(samples.ndim==2 and samples.shape[1]==6 and 32<=len(samples)<=4096,'return 32..4096 six-parameter posterior samples')
        require(np.all((samples>=bounds[:,0])&(samples<=bounds[:,1])),'profile posterior violates physical bounds')
        values=data[case['test']]; selection=samples[np.linspace(0,len(samples)-1,min(128,len(samples))).astype(int)]
        predictions=np.array([parratt(values[:,0],p,metadata['contrasts'][case['test']],values[:,3]) for p in selection])
        # Proper log posterior predictive density relative to noise normalization.
        from scipy.special import logsumexp
        residual=(predictions-values[:,1])/values[:,2]
        predictive_nll=float(np.mean(-logsumexp(-.5*residual**2,axis=0)+math.log(len(predictions))))
        truth_score=0.
        if 'truth_parameters' in case:
            truth=np.asarray(case['truth_parameters']); truth_score=float(np.mean([crps(samples[:,j],truth[j])/(bounds[j,1]-bounds[j,0]) for j in range(6)]))
        losses.append(predictive_nll+truth_score)
        details.append({'track':case['track'],'sample_id':case['sample_id'],'held_out_contrast':case['test'],
                        'predictive_nll_above_noise_constant':predictive_nll,'truth_normalized_crps':truth_score if 'truth_parameters' in case else None})
    return float(np.mean(losses)),{'metric':'held_out_contrast_posterior_predictive_nll_plus_simulated_truth_CRPS','cases':details,
        'experimental_samples':len({c['sample_id'] for c in metadata['cases'] if c['track']=='experimental'}),
        'limitation':'Measured curves are not exact profile truth. Single experimental sample, three contrasts; no cross-sample generalization claim.'}


def reflectometry_seed(training,bounds,metadata):
    from scipy.optimize import least_squares
    bounds=np.asarray(bounds); lo=bounds[:,0]; hi=bounds[:,1]; ranges=hi-lo
    def residual(unit):
        parameters=lo+ranges*unit
        return np.concatenate([(parratt(item['q'],parameters,item['solvent_sld'],item['q_fwhm'])-item['reflectivity'])/item['errors'] for item in training])
    starts=[np.array([10,210,.3,.03,3,1.5e-5]),np.array([12,110,.5,.06,5,2e-5]),np.array([8,320,.2,.02,4,1e-5])]
    fits=[least_squares(residual,np.clip((x-lo)/ranges,.001,.999),bounds=(np.zeros(6),np.ones(6)),max_nfev=250) for x in starts]
    best=min(fits,key=lambda r:np.sum(r.fun**2)); covariance=np.linalg.pinv(best.jac.T@best.jac,rcond=1e-8)
    draws=np.random.default_rng(4911).multivariate_normal(best.x,covariance,size=256,check_valid='ignore')
    return lo+ranges*np.clip(draws,0,1)


def xy_observables(theta):
    energy=-np.mean(np.cos(theta-np.roll(theta,1,0))+np.cos(theta-np.roll(theta,1,1)))
    magnetization=abs(np.mean(np.exp(1j*theta)))
    return np.array([energy,magnetization])


def xy_kernel(theta,temperature,kernel,rng):
    """Only evaluator-owned invariant kernels; never executes candidate transitions."""
    n=len(theta)
    if kernel=='wolff':
        axis=rng.uniform(-np.pi,np.pi); projection=np.cos(theta-axis)
        selected=np.zeros(theta.shape,bool); origin=(int(rng.integers(n)),int(rng.integers(n)))
        selected[origin]=True; queue=[origin]
        for i,j in queue:
            for a,b in [((i+1)%n,j),((i-1)%n,j),(i,(j+1)%n),(i,(j-1)%n)]:
                coupling=projection[i,j]*projection[a,b]
                if not selected[a,b] and coupling>0 and rng.random() < -math.expm1(-2*coupling/temperature):
                    selected[a,b]=True; queue.append((a,b))
        theta[selected]=(2*axis+np.pi-theta[selected]+np.pi)%(2*np.pi)-np.pi
    else:
        require(n%2==0,'checkerboard kernels require even lattice size')
        parity=np.indices(theta.shape).sum(axis=0)%2
        for color in (0,1):
            neighbors=sum(np.exp(1j*np.roll(theta,shift,axis)) for axis in (0,1) for shift in (-1,1))
            mask=parity==color
            if kernel=='overrelax':
                theta[mask]=2*np.angle(neighbors[mask])-theta[mask]
            elif kernel=='metropolis':
                proposed=theta+rng.uniform(-np.pi,np.pi,theta.shape)
                delta=-np.real(np.exp(-1j*proposed)*neighbors)+np.real(np.exp(-1j*theta)*neighbors)
                accept=mask&(np.log(rng.random(theta.shape)) < -delta/temperature)
                theta[accept]=proposed[accept]
            else:
                raise CandidateError('unknown trusted XY kernel')
    theta[:]=(theta+np.pi)%(2*np.pi)-np.pi


def xy_chain(temperature,size,kernels,sweeps,warmup,seed):
    rng=np.random.default_rng(seed); theta=rng.uniform(-np.pi,np.pi,(size,size)); values=[]
    for step in range(sweeps):
        xy_kernel(theta,temperature,kernels[step%len(kernels)],rng)
        if step>=warmup:
            values.append(xy_observables(theta))
    return np.asarray(values)


def xy_monte_carlo(candidate,data,metadata):
    scores=[]; records=[]
    for i,case in enumerate(metadata['cases']):
        size=case['size']; temperature=case['temperature']; sweeps=case['sweeps']; warmup=case['warmup']
        schedule=candidate.schedule(temperature,size,{'site_units':sweeps*size*size,'warmup_site_units':warmup*size*size,
            'kernel_cost_site_units':size*size,'allowed':['metropolis','overrelax','wolff']})
        require(isinstance(schedule,(list,tuple)) and 1<=len(schedule)<=64,'schedule must list 1..64 trusted kernels')
        require(all(isinstance(x,str) and x in ('metropolis','overrelax','wolff') for x in schedule),'unrecognized kernel')
        require(any(x in ('metropolis','wolff') for x in schedule),'pure overrelaxation is not an ergodic sampler')
        reference=data['reference_means'][i]; reference_se=data['reference_standard_errors'][i]; scales=data['observable_scales'][i]
        require(np.all(reference_se/scales < .08),'reference uncertainty too large for scoring')
        estimates=[]; lag=[]
        for chain in range(case['chains']):
            values=xy_chain(temperature,size,schedule,sweeps,warmup,99173+1000*i+chain)
            estimates.append(values.mean(axis=0)); lag.append([float(np.corrcoef(values[:-1,j],values[1:,j])[0,1]) if np.std(values[:,j])>1e-12 else 1. for j in range(2)])
        estimates=np.asarray(estimates); mse=np.mean(((estimates-reference)/scales)**2)
        scores.append(float(mse)); records.append({'temperature':temperature,'size':size,'mean_observables':estimates.mean(axis=0).tolist(),
            'independent_chain_standard_errors':(estimates.std(axis=0,ddof=1)/math.sqrt(len(estimates))).tolist(),
            'reference_means':reference.tolist(),'reference_standard_errors':reference_se.tolist(),'lag1_autocorrelation':np.mean(lag,axis=0).tolist(),
            'charged_site_units_per_chain':sweeps*size*size,'normalized_MSE':float(mse)})
    return float(np.mean(scores)),{'metric':'independent_chain_equilibrium_observable_normalized_MSE_at_fixed_work','cases':records,
        'reference':'long independent mixed-kernel chains, numerical reference with explicit uncertainty; not exact equilibrium truth'}


def anamak_equilibrium(profile,grid=33):
    from freegsnke import build_machine,equilibrium_update,GSstaticsolver
    from freegsnke.jtor_update import Lao85
    theta=np.linspace(0,2*np.pi,8,endpoint=False)
    active={i:{'R':[float(1+.7*np.cos(t))],'Z':[float(.7*np.sin(t))],'dR':.05,'dZ':.05,
               'resistivity':1.55e-8,'polarity':1,'multiplier':1} for i,t in enumerate(theta)}
    passive=[{'R':float(1+.5*np.cos(t)),'Z':float(.5*np.sin(t)),'dR':.02,'dZ':.02,'resistivity':5.5e-7}
             for t in np.linspace(0,2*np.pi,50,endpoint=False)]
    limiter=[{'R':float(1+.45*np.cos(t)),'Z':float(.45*np.sin(t))} for t in np.linspace(0,2*np.pi,101,endpoint=False)]
    machine=build_machine.tokamak(active_coils_data=active,passive_coils_data=passive,limiter_data=limiter,wall_data=limiter)
    eq=equilibrium_update.Equilibrium(machine,Rmin=.1,Rmax=1.9,Zmin=-.8,Zmax=.8,nx=grid,ny=2*grid-1)
    profiles=Lao85(eq,Ip=profile['Ip'],fvac=.5,alpha=[profile['alpha']],beta=[profile['beta']])
    return eq,profiles,GSstaticsolver.NKGSsolver(eq)


def coil_inverse(profile,target,grid=33):
    from freegsnke.inverse import Inverse_optimizer
    eq,profiles,solver=anamak_equilibrium(profile,grid)
    rx,zx,rout=target['x_radius'],target['x_height'],target['outer_radius']
    constrain=Inverse_optimizer(null_points=[[rx,rx],[zx,-zx]],isoflux_set=np.array([[[rx,rx,rout],[zx,-zx,0.]]]),
                                weight_isoflux=1.,weight_nulls=.8)
    solver.inverse_solve(eq=eq,profiles=profiles,constrain=constrain,target_relative_tolerance=1e-5,
        target_relative_psit_update=1e-3,verbose=False,l2_reg=np.array([1e-12]*8),force_up_down_symmetric=True)
    return eq,profiles,solver


def coil_currents(eq):
    return np.array([float(eq.tokamak.coils[i][1].current) for i in range(8)])


def coil_forward(currents,profile,grid,initial_psi=None):
    eq,profiles,solver=anamak_equilibrium(profile,grid)
    all_currents=np.zeros(58); all_currents[:8]=currents
    eq.tokamak.set_all_coil_currents(all_currents)
    if initial_psi is not None:
        eq.plasma_psi=np.array(initial_psi,copy=True)
    solver.solve(eq,profiles,constrain=None,target_relative_tolerance=1e-8,verbose=False)
    residual=solver.F_function(eq.plasma_psi.ravel(),eq.tokamak_psi.ravel(),profiles)
    relative=solver.relative_norm_residual(residual,eq.plasma_psi.ravel())
    require(np.isfinite(relative) and relative<2e-6,'Grad-Shafranov solve did not converge')
    require(getattr(profiles,'opt',None) is not None and len(profiles.opt)>0 and getattr(profiles,'xpt',None) is not None and len(profiles.xpt)>0,'missing closed plasma O-point/X-point topology')
    require(not bool(profiles.flag_limiter),'target requires diverted plasma, not limiter contact')
    return eq,profiles,solver,float(relative)


def tokamak(candidate,data,metadata):
    require(metadata.get('freegsnke_version')=='3.1.0','source solver version must be pinned')
    import importlib.metadata
    require(importlib.metadata.version('freegsnke')=='3.1.0','install freegsnke==3.1.0')
    scores=[]; results=[]
    for i,case in enumerate(metadata['cases']):
        machine={'name':'Anamak','coil_radii':(1+.7*np.cos(np.arange(8)*np.pi/4)).tolist(),
            'coil_heights':(.7*np.sin(np.arange(8)*np.pi/4)).tolist(),'current_bounds_A':[-8e5,8e5],
            'coarse_grid':case['coarse_grid']}
        target=dict(case['target'],boundary=data[f'boundary_{i}'].copy(),magnetic_axis=data[f'axis_{i}'].copy())
        currents=array(candidate.design_coils(machine,target,dict(case['profile'])),(8,),'active-coil currents')
        require(np.max(np.abs(currents))<=8e5,'coil current bound exceeded')
        errors=[]; residuals=[]; axes=[]
        for label in ('coarse','fine'):
            grid=case[label+'_grid']; initial=data[f'{label}_initial_psi_{i}']
            eq,profiles,solver,residual=coil_forward(currents,case['profile'],grid,initial)
            boundary=data[f'boundary_{i}']; flux=eq.psiRZ(boundary[:,0],boundary[:,1]); axis=np.asarray(eq.magneticAxis())[:2]
            require(.55<axis[0]<1.45 and abs(axis[1])<.45,'magnetic axis outside limiter interior')
            # Boundary is a target flux surface; normalize by axis-boundary span.
            axis_flux=float(eq.psiRZ(*axis)); span=max(abs(axis_flux-float(np.mean(flux))),1e-8)
            error=float(np.std(flux)/span + np.linalg.norm(axis-data[f'axis_{i}'])/.45)
            errors.append(error); residuals.append(residual); axes.append(axis)
        require(np.linalg.norm(axes[0]-axes[1])<.05,'equilibrium axis not converged under mesh refinement')
        scores.append(max(errors)); results.append({'currents_A':currents.tolist(),'coarse_error':errors[0],
            'refined_error':errors[1],'relative_GS_residuals':residuals,'axis_refinement_shift_m':float(np.linalg.norm(axes[0]-axes[1]))})
    return float(np.mean(scores)),{'metric':'worst_resolution_boundary_flux_and_magnetic_axis_error','cases':results,
        'model':'Published idealized Anamak geometry, static free-boundary Lao85 equilibria; not experimental operation'}


def coil_seed(machine,target,profile):
    eq,_,_=coil_inverse(profile,target,machine['coarse_grid'])
    return coil_currents(eq)
