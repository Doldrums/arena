"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import numpy as np

def predict_shift(training_profiles, training_perturbations, perturbation_set, gene_context):
    mean = np.mean(training_profiles, axis=0)
    singles = {tuple(p)[0]: training_profiles[i] for i,p in enumerate(training_perturbations) if len(p) == 1}
    result=[]
    for perturbation in perturbation_set:
        effects = [singles[g] for g in perturbation if g in singles]
        result.append(np.sum(effects, axis=0) if effects else mean)
    return np.array(result)
# EVOLVE-BLOCK-END
