"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    # Paley graph on 37 vertices: i ~ j when j - i is a nonzero quadratic residue mod 37 (a (5,5)-free graph).
    q = 37
    residues = {(x * x) % q for x in range(1, q)}
    return q, [(i, j) for i in range(q) for j in range(i + 1, q) if (j - i) % q in residues]
# EVOLVE-BLOCK-END
