"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    representations={}
    for mask in range(1,1<<10):
        terms=[x for x in range(1,11) if mask>>(x-1)&1]
        residue=sum(pow(x,-1,101) for x in terms)%101
        representations.setdefault(residue,terms)
    return [representations[r] for r in range(101)]
# EVOLVE-BLOCK-END
