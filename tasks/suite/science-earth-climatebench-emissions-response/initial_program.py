"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import numpy as np

class EmissionsResponse:
    def __init__(self,scenarios):
        features=np.concatenate([self.features(s["forcing"]) for s in scenarios])
        self.scale=np.maximum(features.std(axis=0),1e-12);self.scale[0]=1
        design=features/self.scale
        self.coefficients={};self.shapes={}
        for variable in scenarios[0]["fields"]:
            fields=np.concatenate([s["fields"][variable] for s in scenarios]);self.shapes[variable]=fields.shape[1:]
            self.coefficients[variable]=np.linalg.lstsq(design,fields.reshape(len(fields),-1),rcond=1e-8)[0]
    def features(self,forcing):
        x=np.asarray(forcing["values"],float)
        # CumulativeCO2 plus methane and aerosol forcing proxies;30-year lag basis.
        lag=x.copy()
        for i in range(1,len(x)):lag[i]=lag[i-1]+(x[i]-lag[i-1])/30.
        return np.column_stack([np.ones(len(x)),x,lag[:,1:]])
    def project_climate(self,forcing):
        design=self.features(forcing)/self.scale
        return {v:(design@c).reshape((len(design),)+self.shapes[v]) for v,c in self.coefficients.items()}

def fit_climate(training_scenarios,grid):return EmissionsResponse(training_scenarios)
# EVOLVE-BLOCK-END
