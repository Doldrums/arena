# Independently written trivial seed for the AlphaEvolve notebook task; a valid but weak
# construction. It is not the published construction and not a reproduction of the paper.
# Contract: construct() -> list of 12 positive double-root locations for the Laguerre combination with m=12, n=1
def construct():
    return [4.0 * (i + 1) for i in range(12)]
