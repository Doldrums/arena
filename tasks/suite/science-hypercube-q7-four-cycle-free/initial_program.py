"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    # Greedy: scan edges in order and keep one unless it completes a four-cycle.
    d, chosen, out = 7, set(), []
    for x in range(2 ** d):
        for i in range(d):
            y = x ^ (1 << i)
            if x < y:
                ok = True
                for j in range(d):
                    if j != i:
                        c, e = x ^ (1 << j), y ^ (1 << j)
                        if all(p in chosen for p in ((min(x, c), max(x, c)), (min(y, e), max(y, e)), (min(c, e), max(c, e)))):
                            ok = False
                            break
                if ok:
                    chosen.add((x, y))
                    out.append([x, y])
    return out
# EVOLVE-BLOCK-END
