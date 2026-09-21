"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct_auction(distribution_spec, support, constraints):
    from autoresearch_suite.science_economics_expansion import auction_baseline
    return auction_baseline(distribution_spec, support, constraints)
# EVOLVE-BLOCK-END
