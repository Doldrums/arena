"""Quantum-channel control evaluation and seed controls."""
from __future__ import annotations

from .science_physics_expansion import (
    array,
    copy,
    expm,
    math,
    np,
    require,
    time,
)

def quantum_model():
    return {'duration_ns':40.,'steps':80,'anharmonicity_rad_ns':-2*np.pi*.25,'amplitude_bound_rad_ns':.4,
        'slew_bound_rad_ns_per_ns':.12,'detuning_bounds_rad_ns':[-2*np.pi*.002,2*np.pi*.002],
        'drive_scale_bounds':[.97,1.03],'T1_ns':25000.,'Tphi_ns':40000.}


def quantum_channel(pulses,model,detuning,drive_scale,*,method='expm'):
    a=np.diag(np.sqrt([1.,2.]),1).astype(complex); number=a.conj().T@a; ident=np.eye(3)
    collapse=[a/math.sqrt(model['T1_ns']),number*math.sqrt(2/model['Tphi_ns'])]
    drift=detuning*number+.5*model['anharmonicity_rad_ns']*number@(number-ident)
    dissipator=np.zeros((9,9),complex)
    for c in collapse:
        cc=c.conj().T@c
        dissipator+=np.kron(c.conj(),c)-.5*(np.kron(ident,cc)+np.kron(cc.T,ident))
    channel=np.eye(9,dtype=complex); dt=model['duration_ns']/len(pulses)
    for x,y in pulses:
        h=drift+.5*drive_scale*(x*(a+a.conj().T)+1j*y*(a-a.conj().T))
        generator=-1j*(np.kron(ident,h)-np.kron(h.T,ident))+dissipator
        if method=='expm':
            channel=expm(dt*generator)@channel
        else:
            from scipy.integrate import solve_ivp
            solved=solve_ivp(lambda t,v:(generator@v.reshape(9,9)).ravel(),[0,dt],channel.ravel(),method='DOP853',rtol=2e-10,atol=2e-12)
            require(solved.success,'independent quantum integration failed')
            channel=solved.y[:,-1].reshape(9,9)
    return channel


def channel_metrics(channel):
    zero=np.array([1,0,0],complex); one=np.array([0,1,0],complex)
    states=[zero,one,(zero+one)/np.sqrt(2),(zero-one)/np.sqrt(2),(zero+1j*one)/np.sqrt(2),(zero-1j*one)/np.sqrt(2)]
    gate=np.array([[0,1,0],[1,0,0],[0,0,1]],complex); fidelity=[]; leakage=[]
    for state in states:
        rho=np.outer(state,state.conj()); output=(channel@rho.ravel(order='F')).reshape(3,3,order='F')
        require(abs(np.trace(output)-1)<1e-7 and np.linalg.eigvalsh(output).min()>-1e-7,'nonphysical channel')
        target=gate@state; fidelity.append(float(np.real(target.conj()@output@target))); leakage.append(float(output[2,2].real))
    return 1-float(np.mean(fidelity)),float(np.mean(leakage))


def quantum_control(candidate):
    model=quantum_model(); start=time.perf_counter()
    pulses=array(candidate.pulse('X_pi',copy.deepcopy(model)),(model['steps'],2),'IQ pulse')
    dt=model['duration_ns']/model['steps']
    require(np.max(np.linalg.norm(pulses,axis=1))<=model['amplitude_bound_rad_ns']+1e-12,'pulse amplitude bound exceeded')
    require(np.max(np.linalg.norm(np.diff(np.vstack([np.zeros((1,2)),pulses,np.zeros((1,2))]),axis=0),axis=1))/dt<=model['slew_bound_rad_ns_per_ns']+1e-12,'pulse slew/boundary bound exceeded')
    errors=[]; leak=[]
    # A fixed 3x3 grid of imperfections is withheld from the pulse API as cases.
    for detuning in np.linspace(*model['detuning_bounds_rad_ns'],3):
        for scale in np.linspace(*model['drive_scale_bounds'],3):
            infidelity,leakage=channel_metrics(quantum_channel(pulses,model,detuning,scale)); errors.append(infidelity); leak.append(leakage)
    coarse=quantum_channel(pulses,model,0,1)
    independent=quantum_channel(np.repeat(pulses,2,axis=0),model,0,1,method='DOP853')
    integration_error=float(np.max(np.abs(coarse-independent)))
    require(integration_error<2e-7,'independent refined integration disagrees')
    return float(np.mean(errors)+max(errors)),{'metric':'mean_plus_worst_robust_average_gate_infidelity','mean_infidelity':float(np.mean(errors)),
        'worst_infidelity':max(errors),'mean_leakage':float(np.mean(leak)),'independent_integration_max_error':integration_error,
        'seconds':time.perf_counter()-start,'physical_model':'three-level Duffing transmon with Lindblad relaxation/dephasing; no hardware claim'}


def quantum_seed(target,model):
    t=(np.arange(model['steps'])+.5)*model['duration_ns']/model['steps']; width=model['duration_ns']/6
    envelope=np.exp(-.5*((t-model['duration_ns']/2)/width)**2)
    envelope-=np.exp(-.5*(model['duration_ns']/2/width)**2)
    envelope*=np.pi/(np.sum(envelope)*model['duration_ns']/model['steps'])
    derivative=np.gradient(envelope,model['duration_ns']/model['steps'])
    return np.column_stack([envelope,-derivative/model['anharmonicity_rad_ns']])
