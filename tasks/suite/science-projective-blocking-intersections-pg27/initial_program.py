"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    points = [(1,x,y) for x in range(7) for y in range(7)] + [(0,1,x) for x in range(7)] + [(0,0,1)]
    return [i for i,p in enumerate(points) if p[2] == 0]
# EVOLVE-BLOCK-END
