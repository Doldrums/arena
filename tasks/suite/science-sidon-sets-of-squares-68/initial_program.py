"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    chosen, sums = [], set()
    for x in range(1, 69):
        new = {x * x + y * y for y in chosen} | {2 * x * x}
        if len(new) == len(chosen) + 1 and not new & sums:
            chosen.append(x)
            sums |= new
    return chosen
# EVOLVE-BLOCK-END
