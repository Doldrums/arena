"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def infer_parameters(training_protocols, forward_model, bounds, budget):
    return {name: (limits[0] + limits[1])/2 for name, limits in bounds.items()}
# EVOLVE-BLOCK-END
