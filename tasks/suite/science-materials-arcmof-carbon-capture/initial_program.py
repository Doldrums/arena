"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def select_mofs(descriptors, operating_conditions, observations, budget):
    used = {o['index'] for o in observations}
    return [i for i in range(len(descriptors)) if i not in used][:budget]
# EVOLVE-BLOCK-END
