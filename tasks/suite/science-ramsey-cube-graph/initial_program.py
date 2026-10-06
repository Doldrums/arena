"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    # 3x3 rook graph (same row or column) against its complement, on 9 vertices.
    return {'n': 9, 'colors': [0 if i // 3 == j // 3 or i % 3 == j % 3 else 1 for i in range(9) for j in range(i + 1, 9)]}
# EVOLVE-BLOCK-END
