"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def pack(boxes, container):
    # Shelf heuristic: rows along x, shelves along y, layers along z, new bin when the layer is full.
    W, H, D = container
    placements, b, x, y, z, row_h, layer_d = [], 0, 0, 0, 0, 0, 0
    for w, h, d in boxes:
        if x + w > W:
            x, y, row_h = 0, y + row_h, 0
        if y + h > H:
            y, z, layer_d = 0, z + layer_d, 0
            x, row_h = 0, 0
        if z + d > D:
            b, x, y, z, row_h, layer_d = b + 1, 0, 0, 0, 0, 0
        placements.append((b, x, y, z, w, h, d))
        x, row_h, layer_d = x + w, max(row_h, h), max(layer_d, d)
    return placements
# EVOLVE-BLOCK-END
