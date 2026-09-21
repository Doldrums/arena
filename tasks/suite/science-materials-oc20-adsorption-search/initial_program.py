"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def choose_configuration(surface, adsorbate, configurations, observations):
    used = {o['index'] for o in observations}
    return next(i for i in range(len(configurations)) if i not in used)
# EVOLVE-BLOCK-END
