"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import random


def solve(instance):
    # WalkSAT with a fixed flip budget.
    n, clauses = instance["n"], instance["clauses"]
    rng = random.Random(0)
    assignment = [rng.random() < 0.5 for _ in range(n)]
    def satisfied(clause):
        return any(assignment[abs(l) - 1] == (l > 0) for l in clause)
    for _ in range(20000):
        unsat = [c for c in clauses if not satisfied(c)]
        if not unsat:
            break
        clause = rng.choice(unsat)
        literal = rng.choice(clause)
        assignment[abs(literal) - 1] = not assignment[abs(literal) - 1]
    return assignment
# EVOLVE-BLOCK-END
