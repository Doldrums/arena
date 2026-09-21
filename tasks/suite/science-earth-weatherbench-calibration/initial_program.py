"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import numpy as np

def calibrate(forecast,lead_time,location,training_history):
    history=np.array(training_history["forecast"]);truth=np.array(training_history["truth"])
    bias=float(np.mean(truth-history.mean(axis=1)))
    return np.asarray(forecast)+bias
# EVOLVE-BLOCK-END
