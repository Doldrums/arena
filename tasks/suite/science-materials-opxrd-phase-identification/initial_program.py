"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def identify_phases(two_theta, intensity, wavelength, candidate_library):
    from autoresearch_suite.science_opxrd import identify_phases as structural_search
    return structural_search(two_theta, intensity, wavelength, candidate_library)
# EVOLVE-BLOCK-END
