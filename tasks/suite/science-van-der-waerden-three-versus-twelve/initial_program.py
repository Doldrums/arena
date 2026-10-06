"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    # Colour 12 and 13 red; blue runs have length at most 11 and the only blue
    # candidate with difference 2 (the odd numbers 1..23) meets 13.
    return [0 if i in (12, 13) else 1 for i in range(1, 24)]
# EVOLVE-BLOCK-END
