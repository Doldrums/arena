"""Offline, reduced particle-physics method benchmarks with independent metrics.

These generators are deliberately small surrogates, not detector simulation,
TrackML/LHC Olympics data, or a statistical test of new physics. Evaluation
seeds are public and fixed; held-out means fresh samples relative to the
candidate's background reference, not a secret benchmark split.
"""
from __future__ import annotations

import math

import numpy as np

from .runtime import CandidateError, require


def _real_vector(value, size, name):
    try:
        array = np.asarray(value)
    except (TypeError, ValueError) as exc:
        raise CandidateError(f"{name} must be a numeric vector") from exc
    require(array.shape == (size,), f"{name} must have shape ({size},)")
    require(array.dtype.kind in "iuf", f"{name} must contain real numbers")
    require(bool(np.all(np.isfinite(array))), f"{name} must be finite")
    return array


def track_event(seed, tracks=40, layers=8, noise_fraction=0.15, missing=0.12):
    """Return shuffled (x, y, z, layer) rows and independent truth (-1=noise).

    Dimensionless radii range from 0.12 to 1.0. Ideal transverse tracks are
    circles through the beam axis: phi(r)=phi0+asin(kappa*r/2). The longitudinal
    displacement follows transverse arc length. Measurement noise, a displaced
    z origin, missing hits, both curvature signs, and unrelated hits are added.
    """
    require(tracks >= 2 and layers >= 4, "need at least two tracks and four layers")
    require(0 <= missing < 1 and 0 <= noise_fraction <= 1, "invalid noise rate")
    rng = np.random.default_rng(seed)
    radii = np.linspace(0.12, 1.0, layers)
    rows, truth = [], []
    for track in range(tracks):
        phi0 = rng.uniform(-np.pi, np.pi)
        curvature = rng.choice([-1.0, 1.0]) * rng.uniform(0.15, 0.85)
        slope = rng.uniform(-1.3, 1.3)
        z0 = rng.normal(0, 0.006)
        retained = rng.random(layers) >= missing
        if retained.sum() < 4:
            retained[rng.choice(layers, 4, replace=False)] = True
        for layer, radius in enumerate(radii):
            if not retained[layer]:
                continue
            bend = np.arcsin(curvature * radius / 2)
            phi = phi0 + bend
            z = z0 + slope * 2 * bend / curvature
            xyz = np.array([radius * np.cos(phi), radius * np.sin(phi), z])
            xyz += rng.normal(0, [0.0007, 0.0007, 0.0015])
            rows.append([*xyz, layer])
            truth.append(track)
    for _ in range(round(len(rows) * noise_fraction)):
        layer = int(rng.integers(layers))
        radius = radii[layer]
        phi = rng.uniform(-np.pi, np.pi)
        rows.append([radius * np.cos(phi), radius * np.sin(phi), rng.uniform(-1.4, 1.4), layer])
        truth.append(-1)
    order = rng.permutation(len(rows))
    return np.asarray(rows, dtype=float)[order], np.asarray(truth, dtype=np.int64)[order]


def track_pair_metrics(truth, predicted):
    """Pairwise precision/recall/F1; every noise-containing pair is false.

    Labels are arbitrary IDs, never compared numerically against truth IDs.
    -1 abstains on a hit. Singleton and abstained signal hits still contribute
    missed true pairs. Noise hits do not form one giant true noise cluster.
    """
    truth = np.asarray(truth, dtype=np.int64)
    predicted = _real_vector(predicted, len(truth), "track labels")
    require(bool(np.all(predicted == np.floor(predicted))), "track labels must be integers")
    require(bool(np.all((predicted >= -1) & (predicted <= 2**31 - 1))),
            "track labels must lie between -1 and 2147483647")
    predicted = predicted.astype(np.int64)
    i, j = np.triu_indices(len(truth), k=1)
    actual = (truth[i] >= 0) & (truth[i] == truth[j])
    proposed = (predicted[i] >= 0) & (predicted[i] == predicted[j])
    tp = int(np.count_nonzero(actual & proposed))
    n_actual, n_proposed = int(actual.sum()), int(proposed.sum())
    precision = tp / n_proposed if n_proposed else 0.0
    recall = tp / n_actual if n_actual else 0.0
    f1 = 2 * tp / (n_actual + n_proposed) if n_actual + n_proposed else 0.0
    return {"f1": f1, "precision": precision, "recall": recall,
            "true_pairs": n_actual, "predicted_pairs": n_proposed, "correct_pairs": tp}


def tracking_score(reconstruct, seeds=(3101, 3109, 3121, 3137), tracks=40):
    require(len(seeds) > 0, "at least one evaluation seed is required")
    results = []
    for case, seed in enumerate(seeds):
        hits, truth = track_event(seed, tracks=tracks + 8 * case,
                                  noise_fraction=0.10 + 0.04 * case,
                                  missing=0.08 + 0.025 * case)
        # Never expose truth or let an in-place edit change the verifier input.
        labels = reconstruct(hits.copy())
        results.append({"seed": int(seed), "hits": len(hits),
                        **track_pair_metrics(truth, labels)})
    return float(np.mean([row["f1"] for row in results])), {
        "metric": "mean_signal_hit_pair_f1", "events": results,
        "adaptation": "reduced_synthetic_trackml_inspired", "evaluation_seeds_public": True}


def anomaly_sample(seed, mode=0, n_reference=1024, n_background=640, n_signal=32):
    """Return reference background, shuffled unlabeled events, and private labels.

    Five dimensionless features consist of a mass-like coordinate and four
    correlated shape coordinates. The synthetic background includes nonlinear
    mass dependence, a two-component mixture and moderate heavy tails. Injected
    compact overdensities vary in location and correlation across six modes.
    Features are illustrative; they are not physical jet observables.
    """
    require(min(n_reference, n_background, n_signal) > 0, "sample counts must be positive")
    require(0 <= mode < 6, "mode must be in 0..5")
    rng = np.random.default_rng(seed)

    def background(n):
        mass = rng.beta(2, 3, n)
        latent = rng.standard_t(9, size=(n, 4)) / np.sqrt(9 / 7)
        component = rng.choice([-1.0, 1.0], n, p=[0.6, 0.4])
        x1 = 1.5 * mass + 0.65 * latent[:, 0] + 0.4 * component
        x2 = 0.85 * x1 + 0.25 * latent[:, 1] + 0.35 * np.sin(5 * mass)
        x3 = -0.5 * x1 + 0.35 * latent[:, 2] + mass**2
        x4 = 0.4 * x2 + 0.35 * latent[:, 3] - 0.4 * mass
        return np.column_stack((mass, x1, x2, x3, x4))

    reference = background(n_reference)
    held_out = background(n_background)
    signal = background(n_signal)
    mass_centers = (0.32, 0.48, 0.62, 0.40, 0.57, 0.72)
    # Localized, overlapping clusters make density-ratio approaches meaningful;
    # correlations, not merely marginal feature extrema, carry information.
    signal[:, 0] = rng.normal(mass_centers[mode], 0.025 + 0.005 * (mode % 3), n_signal)
    residual_shift = np.array([
        [0.0, 0.95, 0.0, 0.0], [0.0, 0.0, 0.95, 0.0],
        [0.0, 0.0, 0.0, 0.95], [0.3, -0.7, 0.7, 0.0],
        [-0.3, 0.7, 0.0, -0.65], [0.5, -0.35, 0.55, 0.5],
    ])[mode]
    center = np.median(reference[:, 1:], axis=0) + residual_shift
    signal[:, 1:] = center + 0.85 * (signal[:, 1:] - np.median(signal[:, 1:], axis=0))
    events = np.concatenate((held_out, signal), axis=0)
    truth = np.concatenate((np.zeros(n_background, dtype=np.int64), np.ones(n_signal, dtype=np.int64)))
    order = rng.permutation(len(truth))
    return reference, events[order], truth[order]


def anomaly_metrics(truth, scores, background_acceptance=0.05):
    """Tie-aware AUROC and conservative signal efficiency at a background cut.

    The threshold is an evaluator diagnostic chosen using held-out background
    labels. It is not a deployable candidate threshold or a discovery p-value.
    Strict comparison at the order statistic prevents tied scores from passing
    the entire background sample. Constant scores yield AUROC .5 and TPR 0.
    """
    truth = np.asarray(truth)
    scores = _real_vector(scores, len(truth), "anomaly scores")
    require(bool(np.all((truth == 0) | (truth == 1))), "truth must be binary")
    background, signal = scores[truth == 0], scores[truth == 1]
    require(len(background) > 0 and len(signal) > 0, "both classes are required")
    require(0 < background_acceptance < 1, "background acceptance must be in (0, 1)")
    # Direct comparisons avoid overflow from score subtraction at extreme values.
    auc = float(np.mean((signal[:, None] > background).astype(float)
                        + 0.5 * (signal[:, None] == background)))
    allowed = math.floor(background_acceptance * len(background))
    threshold = np.sort(background)[len(background) - allowed - 1]
    fpr = float(np.mean(background > threshold))
    efficiency = float(np.mean(signal > threshold))
    return {"auc": auc, "signal_efficiency": efficiency, "background_efficiency": fpr,
            "background_acceptance_target": background_acceptance,
            "score": 0.5 * (auc + efficiency)}


def anomaly_score(rank_anomalies, seeds=(4103, 4111, 4127, 4133, 4153, 4157), n_reference=1024):
    require(0 < len(seeds) <= 6, "one to six evaluation seeds are required")
    results = []
    for mode, seed in enumerate(seeds):
        reference, events, truth = anomaly_sample(seed, mode=mode, n_reference=n_reference)
        scores = rank_anomalies(reference.copy(), events.copy())
        results.append({"seed": int(seed), "mode": mode, **anomaly_metrics(truth, scores)})
    return float(np.mean([row["score"] for row in results])), {
        "metric": "mean_half_auc_plus_half_tpr_at_5pct_background", "cases": results,
        "adaptation": "reduced_synthetic_lhco_inspired", "evaluation_seeds_public": True}
