"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import numpy as np

def make_runoff(recession,evaporation):
    def runoff(forcing_history,basin_attributes,state):
        # Conservative snow/soil reservoirs; only current-day forcing is read.
        p,t=map(float,forcing_history[-1,:2]);snow=float(state.get("snow_mm",0.));soil=float(state.get("soil_mm",0.))
        if t<0:snow+=p;rain=0.
        else:rain=p
        melt=min(snow,max(t,0.)*2.);snow-=melt;soil+=rain+melt
        evap=min(soil,max(t,0.)*evaporation);soil-=evap
        discharge=recession*soil;soil-=discharge
        return {"discharge_mm":discharge,"evapotranspiration_mm":evap,"state":{"storage_mm":snow+soil,"snow_mm":snow,"soil_mm":soil}}
    return runoff

def fit_runoff(training_basins):
    best=(-float("inf"),.06,.08)
    for recession in [.02,.06,.12,.25]:
        for evaporation in [.02,.08,.2,.4]:
            model=make_runoff(recession,evaporation);skills=[]
            for basin in training_basins:
                x=np.array(basin["forcing"]);truth=np.array(basin["discharge"]);state={"storage_mm":0.};predictions=[]
                for row in x:
                    output=model(row[None,:],basin["attributes"],state);state=output["state"];predictions.append(output["discharge_mm"])
                mask=np.array(basin.get("quality_mask",[True]*len(x)),bool);mask[:min(365,len(x)//2)]=False
                variance=np.sum((truth[mask]-truth[mask].mean())**2)
                if variance>0:skills.append(1-np.sum((np.array(predictions)[mask]-truth[mask])**2)/variance)
            skill=float(np.mean(skills)) if skills else -1e30
            if skill>best[0]:best=(skill,recession,evaporation)
    return make_runoff(best[1],best[2])
# EVOLVE-BLOCK-END
