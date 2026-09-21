"""Fluid gradients and turbulence closure rollouts."""
from __future__ import annotations

from .science_physics_expansion import (
    array,
    disjoint,
    np,
    require,
    uniform_filter,
)

def velocity_gradient(velocity,spacing):
    return np.stack([(np.roll(velocity,-1,axis=i)-np.roll(velocity,1,axis=i))/(2*spacing) for i in range(3)],axis=-1)


def filter_velocity(fine,width,stride):
    # Full periodic DNS boxes only: no false periodic wrapping on arbitrary cutouts.
    velocity=np.stack([uniform_filter(fine[...,i],size=width,mode='wrap') for i in range(3)],axis=-1)
    product=np.empty(fine.shape[:-1]+(3,3))
    for i in range(3):
        for j in range(3):
            product[...,i,j]=uniform_filter(fine[...,i]*fine[...,j],size=width,mode='wrap')-velocity[...,i]*velocity[...,j]
    return velocity[::stride,::stride,::stride],product[::stride,::stride,::stride]


def project_solenoidal(field,spacing):
    n=field.shape[0]; k=2*np.pi*np.fft.fftfreq(n,d=spacing); grid=np.stack(np.meshgrid(k,k,k,indexing='ij'),axis=-1)
    spectrum=np.fft.fftn(field,axes=(0,1,2)); norm=np.sum(grid*grid,axis=-1); norm[0,0,0]=1
    spectrum-=grid*np.sum(grid*spectrum,axis=-1)[...,None]/norm[...,None]
    return np.fft.ifftn(spectrum,axes=(0,1,2)).real


def closure_rollout(candidate,initial,spacing,width,viscosity,dt,steps):
    velocity=initial.copy(); max_energy=np.mean(velocity**2)*4
    def rhs(u):
        grad=velocity_gradient(u,spacing)
        stress=array(candidate.closure(u.copy(),grad.copy(),width),u.shape[:-1]+(3,3),'subgrid stress')
        divergence=sum((np.roll(stress[..., :,j],-1,axis=j)-np.roll(stress[..., :,j],1,axis=j))/(2*spacing) for j in range(3))
        lap=sum((np.roll(u,-1,axis=j)+np.roll(u,1,axis=j)-2*u)/spacing**2 for j in range(3))
        return project_solenoidal(-np.einsum('...j,...ij->...i',u,grad)-divergence+viscosity*lap,spacing)
    for _ in range(steps):
        k1=rhs(velocity); velocity=project_solenoidal(velocity+dt*rhs(velocity+.5*dt*k1),spacing)
        require(np.all(np.isfinite(velocity)) and np.mean(velocity**2)<=max_energy,'unstable coarse-flow rollout')
    return velocity


def turbulence(candidate,data,metadata):
    disjoint(data['development_block_ids'],data['block_ids'],'DNS space-time blocks')
    require(metadata.get('full_periodic_boxes') is True,'periodic filter requires complete periodic source boxes, not arbitrary cutouts')
    errors=[]; diagnostics=[]
    for i,config in enumerate(metadata['cases']):
        fine=array(data[f'fine_{i}'],name='fine DNS velocity'); stride=config['stride']; width=config['filter_cells']
        require(fine.ndim==4 and fine.shape[-1]==3 and len(set(fine.shape[:3]))==1,'cubic 3D DNS velocity required')
        velocity,truth=filter_velocity(fine,width,stride); spacing=config['fine_spacing']*stride; delta=config['fine_spacing']*width
        grad=velocity_gradient(velocity,spacing)
        prediction=array(candidate.closure(velocity.copy(),grad.copy(),delta),truth.shape,'subgrid stress')
        require(np.allclose(prediction,np.swapaxes(prediction,-1,-2),rtol=1e-5,atol=1e-8),'stress must be symmetric')
        moved=array(candidate.closure(velocity+np.array([.83,-.21,.54]),grad.copy(),delta),truth.shape)
        require(np.allclose(moved,prediction,rtol=1e-3,atol=1e-6),'closure violates Galilean invariance')
        # Cyclic permutation is a proper rotation of both space and vector axes.
        rotated=np.transpose(velocity,(1,2,0,3))[...,[1,2,0]]; rotated_grad=velocity_gradient(rotated,spacing)
        result=array(candidate.closure(rotated,rotated_grad,delta),truth.shape)
        expected=np.transpose(prediction,(1,2,0,3,4))[...,[1,2,0],:][...,:,[1,2,0]]
        require(np.allclose(result,expected,rtol=2e-3,atol=1e-6),'closure violates cyclic rotational consistency')
        scale=max(np.sqrt(np.mean(truth**2)),1e-12); stress_error=float(np.sqrt(np.mean((prediction-truth)**2))/scale)
        transfer_true=-np.einsum('...ij,...ij->...',truth,grad); transfer_pred=-np.einsum('...ij,...ij->...',prediction,grad)
        transfer_error=float(np.sqrt(np.mean((transfer_true-transfer_pred)**2))/max(np.sqrt(np.mean(transfer_true**2)),1e-12))
        final=closure_rollout(candidate,velocity,spacing,delta,config['viscosity'],config['dt'],config['steps'])
        reference,_=filter_velocity(data[f'fine_future_{i}'],width,stride)
        spectrum=np.abs(np.fft.fftn(final,axes=(0,1,2)))**2; expected_spectrum=np.abs(np.fft.fftn(reference,axes=(0,1,2)))**2
        spectrum_error=float(np.sum(np.abs(spectrum-expected_spectrum))/np.sum(expected_spectrum))
        errors.append(stress_error+transfer_error+spectrum_error)
        diagnostics.append({'stress_nrmse':stress_error,'energy_transfer_nrmse':transfer_error,'rollout_spectral_relative_L1':spectrum_error})
    return float(np.mean(errors)),{'metric':'stress_energy_transfer_and_rollout_spectrum_error','blocks':diagnostics}
