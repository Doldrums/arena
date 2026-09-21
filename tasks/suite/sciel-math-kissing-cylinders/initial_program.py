# EVOLVE-BLOCK-START
import numpy as np


def kissing_cylinders7() -> np.ndarray:
    """
    Arrange n mutually tangent infinite unit-radius cylinders in R^3 (the "kissing
    cylinders" problem). Each cylinder is described by its axis line: a point P on the
    axis and a unit direction vector v. Two unit cylinders are tangent (kiss) when the
    shortest distance between their axis lines equals 2 (the sum of the two radii). The
    objective is to make every pair of cylinders mutually tangent. Here n = 7.

    Returns:
        cylinders: np.ndarray of shape (7, 2, 3). For cylinder i, cylinders[i, 0] is the
            point P on its axis (taken closest to the origin, i.e. P . v = 0) and
            cylinders[i, 1] is the unit direction vector v of its axis.
    """
    # Known good construction of 7 mutually tangent unit cylinders (from the upstream
    # notebook's stored configuration). Translated to a pure-numpy literal.
    cylinders = np.array(
        [
            [[-0.895079798222949, -0.218667037637932, -2.698674434206914],
             [0.455691112272712, -0.886598452747669, -0.079301915368401]],
            [[2.312489793725001, 3.147856283569415, 0.748107205326668],
             [-0.664105297845157, 0.595346549216158, -0.452246215805514]],
            [[3.170115696452898, -1.572941214905496, 0.275241501569553],
             [0.101170430028976, 0.365792590480751, 0.925181238913292]],
            [[1.406156005670123, -0.503509206206139, -1.138840951658002],
             [0.278750862076112, 0.957110225796107, -0.078980836715941]],
            [[3.310296433116253, -4.04403876669603, 1.793851653115256],
             [0.391295737183334, 0.621396411266488, 0.678788734531799]],
            [[0.571615889126358, 0.70496184855727, 0.536647055898052],
             [0.303154750428934, -0.720544668653402, 0.623628557530466]],
            [[0.91063644953714, 1.170580327427548, -3.796585078946353],
             [0.071052005884345, 0.948268376505215, 0.30941670701495]],
        ],
        dtype=np.float64,
    )
    return cylinders


# EVOLVE-BLOCK-END
