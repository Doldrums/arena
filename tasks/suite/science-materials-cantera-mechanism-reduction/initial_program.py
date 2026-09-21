"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def reduce_mechanism(full_mechanism, training_conditions, tolerance):
    # Valid full-model baseline; optimization must remove mechanisms responsibly.
    return {'species': list(full_mechanism['species']),
            'reaction_indices': list(range(len(full_mechanism['reaction_equations'])))}
# EVOLVE-BLOCK-END
