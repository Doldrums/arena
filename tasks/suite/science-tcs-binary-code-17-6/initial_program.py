"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    # First-order Reed-Muller code on 16 coordinates, extended by two zero bits.
    # Every affine Boolean function on F_2^4 is a word: 32 words, distance 8.
    words = []
    for slope in range(16):
        for intercept in range(2):
            word = 0
            for point in range(16):
                bit = ((slope & point).bit_count() + intercept) % 2
                word |= bit << point
            words.append(word)
    return words
# EVOLVE-BLOCK-END
