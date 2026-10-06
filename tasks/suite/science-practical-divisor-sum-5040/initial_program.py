"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    remainder=4979;chosen=[]
    for d in range(5040,0,-1):
        if 5040%d==0 and d<=remainder:
            chosen.append(d);remainder-=d
    assert remainder==0
    return chosen
# EVOLVE-BLOCK-END
