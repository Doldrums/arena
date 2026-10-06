"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    # The Golay-Rudin-Shapiro recursion P -> (P, Q), Q -> (P, -Q), truncated to 24 coefficients.
    p, q = [1], [1]
    while len(p) < 24:
        p, q = p + q, p + [-c for c in q]
    return p[:24]
# EVOLVE-BLOCK-END
