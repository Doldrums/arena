"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def suggest(observations, candidate_conditions, batch_size):
    used = {o['index'] for o in observations}
    return [i for i in range(len(candidate_conditions)) if i not in used][:batch_size]
# EVOLVE-BLOCK-END
