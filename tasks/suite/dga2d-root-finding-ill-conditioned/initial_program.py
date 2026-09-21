"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def find_root(f, x0):
    # Newton's method with a finite-difference derivative.
    x = float(x0)
    for _ in range(60):
        fx = f(x)
        if abs(fx) <= 1e-12:
            return x
        h = 1e-6 * max(1.0, abs(x))
        d = (f(x + h) - fx) / h
        if d == 0:
            break
        x = x - fx / d
    return x
# EVOLVE-BLOCK-END
