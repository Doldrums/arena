"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import numpy as np

def infer_tree(alignment, substitution_model, budget):
    names=list(alignment)
    seq=np.array([list(alignment[n]) for n in names])
    distances={}
    for i in range(len(names)):
        for j in range(i):
            valid=np.isin(seq[i], list("ACGT")) & np.isin(seq[j], list("ACGT"))
            mismatch=np.mean(seq[i,valid]!=seq[j,valid]) if valid.any() else .5
            distances[i,j]=distances[j,i]=-.75*np.log(max(1-4*min(mismatch,.749)/3,1e-5))
    clusters={i:([i],names[i],0.) for i in range(len(names))}
    while len(clusters)>1:
        ids=list(clusters)
        a,b=min(((a,b) for i,a in enumerate(ids) for b in ids[:i]), key=lambda ab:np.mean([distances[x,y] for x in clusters[ab[0]][0] for y in clusters[ab[1]][0]]))
        aa,bb=clusters.pop(a),clusters.pop(b)
        height=float(np.mean([distances[x,y] for x in aa[0] for y in bb[0]]))/2
        tree=f"({aa[1]}:{max(height-aa[2],1e-6):.8f},{bb[1]}:{max(height-bb[2],1e-6):.8f})"
        clusters[max(ids)+1]=(aa[0]+bb[0],tree,height)
    return next(iter(clusters.values()))[1]+";"
# EVOLVE-BLOCK-END
