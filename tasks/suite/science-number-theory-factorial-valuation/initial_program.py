"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    from math import factorial
    def valuation(n):
        v = 0
        while n % 2 == 0:
            n //= 2
            v += 1
        return v
    values, total = [2], 2
    for i in range(3, 33):
        if valuation(total + factorial(i)) > valuation(total):
            values.append(i)
            total += factorial(i)
    return values
# EVOLVE-BLOCK-END
