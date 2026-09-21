"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
from autoresearch_suite.science_materials_expansion import phase_seed

def evolve_composition(initial_field, parameters, times):
    return phase_seed(initial_field, parameters, times)
# EVOLVE-BLOCK-END
