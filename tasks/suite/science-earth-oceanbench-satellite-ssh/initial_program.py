"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import numpy as np
from scipy.spatial import cKDTree

def reconstruct_ssh(observations,times,coordinates,grid):
    locations=np.array(coordinates);query=np.array(grid["coordinates"]);querytime=np.array(grid["times"])
    lat=float(np.mean(locations[:,0]));scale=np.array([111.,111.*np.cos(np.deg2rad(lat))])
    # Retrospective space-time inverse-distance interpolation, meters in/out.
    points=np.column_stack([locations*scale,np.array(times)*10.])
    targets=np.column_stack([query*scale,querytime*10.])
    distance,index=cKDTree(points).query(targets,k=min(16,len(points)))
    if distance.ndim==1:distance=distance[:,None];index=index[:,None]
    weights=1/np.maximum(distance,.01)**2
    return np.sum(np.asarray(observations)[index]*weights,axis=1)/weights.sum(axis=1)
# EVOLVE-BLOCK-END
