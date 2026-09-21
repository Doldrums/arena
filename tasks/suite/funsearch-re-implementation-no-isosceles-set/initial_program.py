"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
N = 64

# EVOLVE-BLOCK-START
def construct():
    # Points on a line at Sidon-like positions (all pairwise distances distinct).
    xs, used = [], set()
    x = 0
    while x < N:
        diffs = {abs(x - y) for y in xs}
        if not (diffs & used):
            used |= diffs
            xs.append(x)
        x += 1
    return [(x, 0) for x in xs]
# EVOLVE-BLOCK-END
