"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    from random import Random
    def instance(size, seed, limit=10000):
        rng = Random(seed)
        values = set()
        while len(values) < size:
            x = rng.randint(-limit, limit)
            if x:
                values.add(x)
        return sorted(values)
    # Odd numbers are sum-free: the sum of two odd numbers is even.
    return [[x for x in instance(size, seed) if x % 2] for size, seed in ((60, 801), (120, 802), (240, 803))]
# EVOLVE-BLOCK-END
