"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import numpy as np

class LightResponse:
    def __init__(self,sites):
        weather=np.concatenate([s["meteorology"] for s in sites]);flux=np.concatenate([s["flux"] for s in sites]);good=np.concatenate([np.array(s["quality_flag"])==0 for s in sites])
        self.coeff=np.linalg.lstsq(self.features(weather[good]),flux[good],rcond=None)[0]
    def features(self,weather):
        x=np.asarray(weather);temperature=x[:,0];radiation=np.maximum(x[:,1],0)
        # Temperature-sensitive respiration minus saturating light uptake.
        return np.column_stack([np.ones(len(x)),np.exp(np.clip(.07*temperature,-10,10)),radiation/(radiation+200)])
    def predict_flux(self,meteorology,ecosystem_metadata,history):return self.features(meteorology)@self.coeff

def fit_flux(training_sites):return LightResponse(training_sites)
# EVOLVE-BLOCK-END
