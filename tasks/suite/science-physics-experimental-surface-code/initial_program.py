"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def decode(detector_events, metadata):
    import pymatching, stim
    dem=stim.DetectorErrorModel(metadata['detector_error_model'])
    return pymatching.Matching.from_detector_error_model(dem).decode_batch(detector_events).reshape(len(detector_events),metadata['num_observables'])
# EVOLVE-BLOCK-END
