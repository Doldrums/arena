"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    a, sums = [1, 2, 5, 11], set()
    for i, x in enumerate(a):
        for y in a[i:]:
            sums.add(x + y)
    for x in range(12, 285):
        new = {x + y for y in a} | {2 * x}
        if len(new) == len(a) + 1 and not new & sums:
            a.append(x)
            sums |= new
    return a
# EVOLVE-BLOCK-END
