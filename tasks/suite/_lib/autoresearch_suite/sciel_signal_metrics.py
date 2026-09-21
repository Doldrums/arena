"""SCiEL signal tracking metrics. Original Apache-2.0 scoring and penalties."""

import numpy as np

def calculate_slope_changes(signal_data):
    """
    Calculate slope change penalty S(θ) - counts directional reversals

    Args:
        signal_data: 1D array of signal values

    Returns:
        Number of slope changes (directional reversals)
    """
    if len(signal_data) < 3:
        return 0

    # Calculate differences
    diffs = np.diff(signal_data)

    # Count sign changes in consecutive differences
    sign_changes = 0
    for i in range(1, len(diffs)):
        if np.sign(diffs[i]) != np.sign(diffs[i - 1]) and diffs[i - 1] != 0:
            sign_changes += 1

    return sign_changes


def calculate_lag_error(filtered_signal, original_signal, window_size):
    """
    Calculate instantaneous lag error L_recent(θ) = |y[n] - x[n]|

    Args:
        filtered_signal: Output of the filter
        original_signal: Original input signal
        window_size: Size of the processing window

    Returns:
        Instantaneous lag error at the most recent sample
    """
    if len(filtered_signal) == 0:
        return 1.0  # Maximum penalty

    # Account for processing delay
    delay = window_size - 1
    if len(original_signal) <= delay:
        return 1.0

    # Compare the last filtered sample with the corresponding original sample
    recent_filtered = filtered_signal[-1]
    recent_original = original_signal[delay + len(filtered_signal) - 1]

    return abs(recent_filtered - recent_original)


def calculate_average_tracking_error(filtered_signal, original_signal, window_size):
    """
    Calculate average tracking error L_avg(θ) over the window

    Args:
        filtered_signal: Output of the filter
        original_signal: Original input signal
        window_size: Size of the processing window

    Returns:
        Average absolute error over the processed samples
    """
    if len(filtered_signal) == 0:
        return 1.0  # Maximum penalty

    # Account for processing delay
    delay = window_size - 1
    if len(original_signal) <= delay:
        return 1.0

    # Align signals
    aligned_original = original_signal[delay : delay + len(filtered_signal)]

    # Ensure same length
    min_length = min(len(filtered_signal), len(aligned_original))
    if min_length == 0:
        return 1.0

    filtered_aligned = filtered_signal[:min_length]
    original_aligned = aligned_original[:min_length]

    # Calculate mean absolute error
    return np.mean(np.abs(filtered_aligned - original_aligned))


def calculate_false_reversal_penalty(filtered_signal, clean_signal, window_size):
    """
    Calculate false reversal penalty R(θ) - mismatched trend changes

    Args:
        filtered_signal: Output of the filter
        clean_signal: Ground truth clean signal
        window_size: Size of the processing window

    Returns:
        Penalty for trend changes that don't match the clean signal
    """
    if len(filtered_signal) < 3 or len(clean_signal) < 3:
        return 0

    # Account for processing delay
    delay = window_size - 1
    if len(clean_signal) <= delay:
        return 1.0

    # Align signals
    aligned_clean = clean_signal[delay : delay + len(filtered_signal)]
    min_length = min(len(filtered_signal), len(aligned_clean))

    if min_length < 3:
        return 0

    filtered_aligned = filtered_signal[:min_length]
    clean_aligned = aligned_clean[:min_length]

    # Calculate trend changes for both signals
    filtered_diffs = np.diff(filtered_aligned)
    clean_diffs = np.diff(clean_aligned)

    # Count mismatched trend changes
    false_reversals = 0
    for i in range(1, len(filtered_diffs)):
        # Check if there's a trend change in filtered signal
        filtered_change = (
            np.sign(filtered_diffs[i]) != np.sign(filtered_diffs[i - 1])
            and filtered_diffs[i - 1] != 0
        )

        # Check if there's a corresponding trend change in clean signal
        clean_change = (
            np.sign(clean_diffs[i]) != np.sign(clean_diffs[i - 1]) and clean_diffs[i - 1] != 0
        )

        # Count as false reversal if filtered has change but clean doesn't
        if filtered_change and not clean_change:
            false_reversals += 1

    return false_reversals


def calculate_composite_score(S, L_recent, L_avg, R, alpha=[0.3, 0.2, 0.2, 0.3]):
    """
    Calculate the composite metric J(θ) = α₁·S(θ) + α₂·L_recent(θ) + α₃·L_avg(θ) + α₄·R(θ)

    All metrics are normalized and converted to penalties (higher = worse)
    The final score is converted to a maximization problem (higher = better)
    """
    # Normalize slope changes (typical range 0-100)
    S_norm = min(S / 50.0, 2.0)

    # Lag errors are already in reasonable range (0-10 typically)
    L_recent_norm = min(L_recent, 2.0)
    L_avg_norm = min(L_avg, 2.0)

    # Normalize false reversals (typical range 0-50)
    R_norm = min(R / 25.0, 2.0)

    # Calculate weighted penalty
    penalty = (
        alpha[0] * S_norm + alpha[1] * L_recent_norm + alpha[2] * L_avg_norm + alpha[3] * R_norm
    )

    # Convert to maximization score (higher is better)
    score = 1.0 / (1.0 + penalty)

    return score
