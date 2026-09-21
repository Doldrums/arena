"""A deliberately approximate structural search seed, never a data generator.

Candidate-side kinematic Bragg templates use source lattices/atomic coordinates,
constant atomic-number scattering amplitudes, and fixed instrumental broadening.
They are fitted to real source intensities. They do not replace observations.
"""
from functools import lru_cache
import json
import numpy as np
from scipy.ndimage import gaussian_filter1d, minimum_filter1d
from scipy.optimize import nnls

ELEMENTS = 'H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge As Se Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi Po At Rn Fr Ra Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm Md No Lr'.split()
ATOMIC_NUMBER = {symbol: i+1 for i, symbol in enumerate(ELEMENTS)}


def bragg_peaks(structure, wavelength, maximum_angle=100.):
    a, b, c, alpha, beta, gamma = structure['lattice_parameters_angstrom_degrees']
    alpha, beta, gamma = np.deg2rad([alpha, beta, gamma])
    cx = c*np.cos(beta)
    cy = c*(np.cos(alpha)-np.cos(beta)*np.cos(gamma))/np.sin(gamma)
    direct = np.array([[a, 0, 0], [b*np.cos(gamma), b*np.sin(gamma), 0],
                       [cx, cy, np.sqrt(max(c*c-cx*cx-cy*cy, 0))]])
    reciprocal = np.linalg.inv(direct).T
    qmax = 2*np.sin(np.deg2rad(maximum_angle/2))/wavelength
    limits = np.ceil(np.array([a, b, c])*qmax).astype(int)
    mesh = np.meshgrid(*(np.arange(-n, n+1) for n in limits), indexing='ij')
    hkl = np.stack([v.ravel() for v in mesh], axis=1)
    # Retain one representative of each Friedel pair. Common factor2 cancels.
    keep = (hkl[:, 0] > 0) | ((hkl[:, 0] == 0) & (hkl[:, 1] > 0)) | ((hkl[:, :2] == 0).all(axis=1) & (hkl[:, 2] > 0))
    hkl = hkl[keep]
    length = np.linalg.norm(hkl @ reciprocal, axis=1)
    keep = (length > 0) & (length <= qmax)
    hkl, length = hkl[keep], length[keep]
    angles = 2*np.rad2deg(np.arcsin(np.clip(length*wavelength/2, 0, 1)))
    coordinates = np.array([site['fractional_coordinates'] for site in structure['sites']])
    amplitudes = np.array([site['occupancy']*ATOMIC_NUMBER[site['element']] for site in structure['sites']])
    intensities = np.empty(len(hkl))
    for start in range(0, len(hkl), 256):
        phase = hkl[start:start+256] @ coordinates.T
        intensities[start:start+256] = np.abs(np.exp(2j*np.pi*phase) @ amplitudes)**2
    theta = np.deg2rad(angles/2)
    intensities *= (1+np.cos(2*theta)**2)/(np.sin(theta)**2*np.cos(theta))
    keep = intensities > max(float(intensities.max()), 1)*1e-9
    order = np.argsort(angles[keep])
    return angles[keep][order], intensities[keep][order]


@lru_cache(maxsize=64)
def _template(serialized_structure, wavelength):
    peaks, strength = bragg_peaks(json.loads(serialized_structure), wavelength)
    grid = np.arange(0, 100.05, .05)
    profile = np.zeros(len(grid))
    np.add.at(profile, np.minimum(np.rint(peaks/.05).astype(int), len(grid)-1), strength)
    return grid, gaussian_filter1d(profile, .10/.05)


def identify_phases(two_theta, intensity, wavelength, candidate_library):
    angles, measured = np.asarray(two_theta, float), np.asarray(intensity, float)
    step = max(float(np.median(np.diff(angles))), .001)
    window = max(3, 2*int(.6/step)+1)
    signal = np.maximum(measured-minimum_filter1d(measured, window), 0)
    signal /= max(float(np.linalg.norm(signal)), 1e-12)
    references = []
    for item in candidate_library:
        grid, profile = _template(json.dumps(item['structure'], sort_keys=True), float(wavelength))
        reference = np.interp(angles, grid, profile, left=0, right=0)
        references.append(reference/max(float(np.linalg.norm(reference)), 1e-12))
    weights, _ = nnls(np.array(references).T, signal, maxiter=500)
    selected = np.flatnonzero(weights >= max(float(weights.max())*.20, 1e-6))
    if not len(selected):
        selected = np.array([int(np.argmax(weights))])
    selected = sorted(selected, key=lambda i: weights[i], reverse=True)[:4]
    return [candidate_library[i]['id'] for i in selected]
