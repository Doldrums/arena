"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import numpy as np

def invert_seismograms(traces,source_receiver_geometry,forward_oracle,budget):
    shape=tuple(source_receiver_geometry["grid_shape"])
    # Smooth depth-gradient initial velocity in declared m/s; replace with FWI.
    low,high=source_receiver_geometry["velocity_bounds"]
    depth=np.linspace(low,high,shape[0])[:,None]
    return np.broadcast_to(depth,shape).copy()
# EVOLVE-BLOCK-END
