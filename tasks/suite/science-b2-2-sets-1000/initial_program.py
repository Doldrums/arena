"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    chosen, counts = [], {}
    for x in range(1, 1001):
        new = [x + y for y in chosen] + [2 * x]
        trial = dict(counts)
        for s in new:
            trial[s] = trial.get(s, 0) + 1
        if max(trial[s] for s in new) <= 2:
            chosen.append(x)
            counts = trial
    return chosen
# EVOLVE-BLOCK-END
