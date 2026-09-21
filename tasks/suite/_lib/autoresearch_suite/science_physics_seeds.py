"""Reference seed routines for source-data physics tasks."""
from __future__ import annotations

from .science_physics_expansion import (
    np,
    uniform_filter,
    visibility_forward,
)

def shear_seed(images,psf,metadata):
    def moments(image):
        yy,xx=np.indices(image.shape); weight=np.maximum(image,0); total=max(weight.sum(),1e-12)
        x=(weight*xx).sum()/total; y=(weight*yy).sum()/total
        return np.array([(weight*(xx-x)**2).sum(),(weight*(yy-y)**2).sum(),(weight*(xx-x)*(yy-y)).sum()])/total
    point=moments(psf); galaxies=np.array([moments(im)-point for im in images]); denom=galaxies[:,:2].sum(axis=1)
    useful=denom>1e-6; ellipticity=np.column_stack([galaxies[:,0]-galaxies[:,1],2*galaxies[:,2]])[useful]/denom[useful,None]
    return np.mean(np.clip(ellipticity,-1,1),axis=0)/2 if len(ellipticity) else np.zeros(2)


def gw_seed(h1,l1,metadata):
    from scipy.signal import welch,find_peaks
    sample_rate=metadata['sample_rate_hz']; energies=[]
    for strain in (h1,l1):
        f,p=welch(strain,fs=sample_rate,nperseg=int(sample_rate*2)); frequency=np.fft.rfftfreq(len(strain),1/sample_rate)
        white=np.fft.irfft(np.fft.rfft(strain)/np.sqrt(np.maximum(np.interp(frequency,f,p),1e-60)),n=len(strain))
        energies.append(uniform_filter(white**2,size=max(1,int(.1*sample_rate))))
    ranking=np.sqrt(energies[0]*energies[1]); peaks,_=find_peaks(ranking,distance=max(1,int(.5*sample_rate)))
    return np.column_stack([metadata['epoch']+peaks/sample_rate,ranking[peaks]])


def shower_seed(training):
    showers=training['showers']; energies=training['incident_energies']
    def sample(incident_energies,rng):
        output=[]
        for energy in incident_energies:
            indices=np.flatnonzero(energies==energy)
            if len(indices):output.append(showers[rng.choice(indices)])
            else:
                index=np.argmin(abs(np.log(energies/energy)));output.append(showers[index]*energy/energies[index])
        return np.asarray(output)
    return sample


def tracking_seed(hits,cells,metadata):
    from sklearn.cluster import DBSCAN
    xyz=hits[:,1:4]; radius=np.linalg.norm(xyz,axis=1); transverse=np.maximum(np.linalg.norm(xyz[:,:2],axis=1),1e-9)
    features=np.column_stack([xyz[:,0]/transverse,xyz[:,1]/transverse,xyz[:,2]/np.maximum(radius,1e-9)])
    labels=DBSCAN(eps=.018,min_samples=3,n_jobs=1).fit_predict(features); out=labels+1
    noise=np.flatnonzero(labels<0);out[noise]=np.arange(len(noise))+max(out)+1
    return out


def collider_seed(control):
    from sklearn.ensemble import IsolationForest
    center=np.median(control,axis=0); scale=np.maximum(np.std(control,axis=0),1e-10)
    model=IsolationForest(n_estimators=80,max_samples=min(1024,len(control)),random_state=219).fit((control-center)/scale)
    class Ranker:
        def score(self,events):return -model.score_samples((events-center)/scale)
    return Ranker()


def distance_seed(image,psf,time_delays,kinematics,metadata):
    from scipy.optimize import least_squares
    bounds=np.asarray(metadata['bounds']); low,high=bounds.T
    def residual(unit):
        result=metadata['forward'](low+unit*(high-low))
        return np.r_[((result['image']-image)/metadata['image_sigma']).ravel(),
            ((result['time_delays']-time_delays)/metadata['delay_sigma']).ravel(),
            (result['velocity_dispersion']-float(kinematics))/metadata['kinematics_sigma']]
    fit=least_squares(residual,np.full(len(bounds),.5),bounds=(np.zeros(len(bounds)),np.ones(len(bounds))),max_nfev=50)
    covariance=np.linalg.pinv(fit.jac.T@fit.jac,rcond=1e-8)
    samples=np.random.default_rng(2891).multivariate_normal(fit.x,covariance,size=128,check_valid='ignore')
    return low+np.clip(samples,0,1)*(high-low)


def atmosphere_seed(spectrum,uncertainty,metadata):
    spectra=np.asarray(metadata['forward_grid_spectra']); log_probability=-.5*np.sum(((spectra-spectrum)/uncertainty)**2,axis=1)
    probability=np.exp(log_probability-log_probability.max());probability/=probability.sum()
    return np.random.default_rng(127).choice(len(spectra),size=512,p=probability)


def imaging_seed(visibilities,metadata,noise):
    from scipy.optimize import minimize
    n=metadata['pixels']; initial=np.ones((n,n))*metadata['flux_jy']/(n*n); uv=visibilities['uv']
    def loss(flat):
        image=np.exp(flat-flat.max());image=image.reshape(n,n)*metadata['flux_jy']/image.sum()
        predicted=visibility_forward(image,uv,metadata['pixel_radians']); triangles=visibilities['closure_triangles'].astype(int)
        oriented=predicted[np.abs(triangles)-1]; oriented=np.where(triangles>0,oriented,oriented.conj())
        phase=np.angle(np.prod(oriented,axis=1)); delta=np.angle(np.exp(1j*(phase-visibilities['closure_phases'])))
        return np.mean(((np.abs(predicted)-visibilities['amplitudes'])/noise['amplitude_sigma'])**2)+np.mean((delta/noise['closure_sigma'])**2)+.001*np.mean(np.diff(image,axis=0)**2)
    fit=minimize(loss,np.log(initial.ravel()),method='L-BFGS-B',options={'maxiter':20,'maxfun':20000})
    values=np.exp(fit.x-fit.x.max()).reshape(n,n);return values*metadata['flux_jy']/values.sum()


def closure_seed(velocity,gradients,filter_width):
    strain=.5*(gradients+np.swapaxes(gradients,-1,-2)); magnitude=np.sqrt(2*np.sum(strain**2,axis=(-1,-2)))
    eddy_viscosity=(.17*filter_width)**2*magnitude
    # Deviatoric Smagorinsky plus nonnegative isotropic gradient-model energy.
    isotropic=filter_width**2*np.sum(gradients**2,axis=(-1,-2))/36
    return -2*eddy_viscosity[...,None,None]*strain+isotropic[...,None,None]*np.eye(3)
