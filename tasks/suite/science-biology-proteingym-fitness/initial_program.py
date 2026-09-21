"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import numpy as np

class AdditiveModel:
    def __init__(self, reference, variants, effects):
        self.mean = float(np.mean(effects))
        values = {}
        for variant, effect in zip(variants, effects):
            for mutation in variant.split(":"):
                values.setdefault(mutation, []).append(float(effect))
        self.effects = {key: float(np.mean(x))-self.mean for key,x in values.items()}
    def score(self, variants):
        return [self.mean + sum(self.effects.get(m, 0.0) for m in v.split(":")) for v in variants]

def fit(reference, support_variants, effects):
    return AdditiveModel(reference, support_variants, effects)
# EVOLVE-BLOCK-END
