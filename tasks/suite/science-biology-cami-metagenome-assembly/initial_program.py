"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def assemble(reads, library_metadata):
    # Deterministic greedy overlap seed; production-quality graph methods can replace it.
    contigs=list(dict.fromkeys(reads))
    minimum=int(library_metadata.get("minimum_overlap",31))
    changed=True
    while changed:
        changed=False
        for i in range(len(contigs)):
            if changed: break
            for j in range(i+1,len(contigs)):
                a,b=contigs[i],contigs[j]
                if b in a: merged=a
                elif a in b: merged=b
                else:
                    merged=None
                    for k in range(min(len(a),len(b))-1,minimum-1,-1):
                        if a[-k:]==b[:k]: merged=a+b[k:];break
                        if b[-k:]==a[:k]: merged=b+a[k:];break
                if merged is not None:
                    contigs[i]=merged;contigs.pop(j);changed=True;break
    return contigs
# EVOLVE-BLOCK-END
