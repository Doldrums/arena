"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    limit=10000
    squarefree=[True]*(limit+1)
    for d in range(2,int(limit**0.5)+1):
        for x in range(d*d,limit+1,d*d):squarefree[x]=False
    values=[x for x in range(1,limit+1) if squarefree[x]]
    return list(max(zip(values,values[1:]),key=lambda pair:pair[1]-pair[0]))
# EVOLVE-BLOCK-END
