"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import numpy as np

def integrate(counts, batch_labels):
    totals = np.maximum(counts.sum(axis=1, keepdims=True), 1)
    x = np.log1p(counts / totals * 10000)
    global_mean = x.mean(axis=0)
    for batch in np.unique(batch_labels):
        mask = batch_labels == batch
        x[mask] -= x[mask].mean(axis=0) - global_mean
    x -= x.mean(axis=0)
    u,s,_ = np.linalg.svd(x, full_matrices=False)
    return u[:, :min(20,len(s))] * s[:min(20,len(s))]
# EVOLVE-BLOCK-END
