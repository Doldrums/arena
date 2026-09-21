"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import numpy as np

def acquire(unlabeled_geometries, observations, budget):
    used = {o['index'] for o in observations}
    return [i for i in range(len(unlabeled_geometries)) if i not in used][:budget]

class ConstantPotential:
    def __init__(self, mean): self.mean = mean
    def potential(self, atomic_numbers, coordinates):
        return self.mean * len(atomic_numbers), np.zeros_like(coordinates, dtype=float)

def fit(observations):
    return ConstantPotential(float(np.mean([o['energy_ev']/len(o['atomic_numbers']) for o in observations])))
# EVOLVE-BLOCK-END
