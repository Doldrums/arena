"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
N = 9

# EVOLVE-BLOCK-START
def construct():
    # Greedy snake: always extend with the lowest bit flip that keeps the path induced (104 edges in Q_9).
    path, used = [0], {0}
    while True:
        cur, nxt = path[-1], None
        for b in range(N):
            v = cur ^ (1 << b)
            if v in used or any((v ^ p).bit_count() == 1 for p in path[:-1]):
                continue
            nxt = v
            break
        if nxt is None:
            return path
        path.append(nxt)
        used.add(nxt)
# EVOLVE-BLOCK-END
