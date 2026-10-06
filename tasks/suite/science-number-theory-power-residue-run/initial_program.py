"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    roots = {}
    for x in range(1, 1009):
        roots.setdefault(x*x % 1009, x)
    # Descending search provides a feasible late run; earlier runs improve it.
    for s in range(1004, 0, -1):
        if all(s+i in roots for i in range(5)):
            return {'start':s, 'roots':[roots[s+i] for i in range(5)]}
    raise RuntimeError('No baseline run found')
# EVOLVE-BLOCK-END
