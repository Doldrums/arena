"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    from math import lcm
    selected = []
    for x in range(2, 257):
        if all(lcm(x,y) > 256 for y in selected):
            selected.append(x)
    return selected
# EVOLVE-BLOCK-END
