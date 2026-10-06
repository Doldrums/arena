"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    limit=10000
    values=sorted({x*x+y*y for x in range(101) for y in range(101) if 1<=x*x+y*y<=limit})
    return list(max(zip(values,values[1:]),key=lambda pair:pair[1]-pair[0]))
# EVOLVE-BLOCK-END
