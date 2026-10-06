"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    # Greedy: moduli in increasing order, each takes the class covering most uncovered residues.
    base = 51975
    covered = bytearray(base)
    classes = []
    for m in [d for d in range(3, base + 1, 2) if base % d == 0]:
        best = max(range(m), key=lambda r: covered[r::m].count(0))
        classes.append([m, best])
        covered[best::m] = b'\x01' * len(range(best, base, m))
    return classes
# EVOLVE-BLOCK-END
