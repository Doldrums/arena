"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
from autoresearch_suite.science_materials_expansion import kmc_seed

def transport(lattice, occupancies, barrier_model, temperature, budget):
    return kmc_seed(lattice, occupancies, barrier_model, temperature, budget)
# EVOLVE-BLOCK-END
