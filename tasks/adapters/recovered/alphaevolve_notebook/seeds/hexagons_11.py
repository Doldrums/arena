# Independently written trivial seed for the AlphaEvolve notebook task; a valid but weak
# construction. It is not the published construction and not a reproduction of the paper.
# Contract: construct() -> (inner_hex_data [[x, y, angle_degrees] x 11], outer_hex_center (x, y), outer_hex_side_length, outer_hex_angle_degrees)
def construct():
    inner = [[4.0 * k, 0.0, 0.0] for k in range(-5, 6)]
    return inner, (0.0, 0.0), 40.0, 0.0
