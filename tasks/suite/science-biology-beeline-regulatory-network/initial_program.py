"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import numpy as np

def infer_network(expression, genes, allowed_regulators, optional_ordering):
    correlation=np.corrcoef(expression, rowvar=False)
    correlation=np.nan_to_num(correlation)
    return [(r,t,abs(float(correlation[genes.index(r),i]))) for r in allowed_regulators for i,t in enumerate(genes) if r!=t]
# EVOLVE-BLOCK-END
