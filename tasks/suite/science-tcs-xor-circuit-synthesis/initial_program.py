"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def synthesize(matrix, depth_limit):
    from autoresearch_suite.science_tcs_expansion import xor_baseline
    return xor_baseline(matrix, depth_limit)
# EVOLVE-BLOCK-END
