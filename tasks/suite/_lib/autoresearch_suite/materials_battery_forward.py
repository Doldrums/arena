"""Trusted GroupedSPMe forward model for C12, independently wrapped from the
Hallemans et al. 2025 model specification and author parameter/data release.

The separate interpreter keeps the paper's NumPy/PyBaMM requirements isolated.
No candidate file or code is loaded by the worker; inputs are JSON parameters
and a specified physical measurement protocol. Telemetry is disabled.
"""
from __future__ import annotations

from arena_task_paths import cache_path, data_root
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
DATA = data_root() / "materials-expansion/C12/raw"
ENVIRONMENT = cache_path("materials-battery-env", "bin", "python")


def forward(parameters, protocol):
    if not ENVIRONMENT.is_file():
        raise ValueError(f"requires_setup: install the isolated {ENVIRONMENT.parent.parent} PyBOP25.6/PyBaMM25.6 environment")
    env = dict(os.environ)
    env["PYBAMM_DISABLE_TELEMETRY"] = "true"
    env["MPLCONFIGDIR"] = str(cache_path("materials-battery-matplotlib"))
    result = subprocess.run([str(ENVIRONMENT), str(Path(__file__).resolve()), "--solve"],
                            input=json.dumps({"parameters": parameters, "protocol": protocol}),
                            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            timeout=120, env=env, check=False)
    if result.returncode:
        raise ValueError("GroupedSPMe forward solve failed: " + result.stderr[-1800:])
    return json.loads(result.stdout)


def solve(parameters, protocol):
    import numpy as np
    import pybamm
    import pybop
    from scipy.io import loadmat
    if not pybamm.__version__.startswith("25.6") or str(pybop.__version__) != "25.6":
        raise ValueError("The model protocol requires PyBaMM25.6 and PyBOP25.6")
    ocp = DATA / "OCP_LGM50LT.mat"
    if hashlib.sha256(ocp.read_bytes()).hexdigest() != "9fd8293724ae5da5ad101a142875e8b6ed2c68c0f916bd6d80c13652b33d1233":
        raise ValueError("Measured OCP source hash differs")
    table = loadmat(ocp)
    base = pybop.ParameterSet.pybamm("Chen2020")
    base["Electrolyte diffusivity [m2.s-1]"] = 1.769e-10
    for name in ["Electrolyte conductivity [S.m-1]", "Negative electrode conductivity [S.m-1]", "Positive electrode conductivity [S.m-1]"]:
        base[name] = 1e16
    grouped = pybop.lithium_ion.GroupedSPMe.apply_parameter_grouping(base)
    def positive_ocp(sto):
        return pybamm.Interpolant(table["x_pos"].ravel(), table["U_pos"].ravel(), sto, interpolator="cubic", extrapolate=True)
    def negative_ocp(sto):
        return pybamm.Interpolant(table["x_neg"].ravel(), table["U_neg"].ravel(), sto, interpolator="cubic", extrapolate=True)
    total = 55.6e-6 + 82.8e-6 + base["Separator thickness [m]"]
    grouped.update({"Measured cell capacity [A.s]": 3600 * 4.885,
                    "Positive electrode OCP [V]": positive_ocp,
                    "Negative electrode OCP [V]": negative_ocp,
                    "Positive electrode relative thickness": 55.6e-6 / total,
                    "Negative electrode relative thickness": 82.8e-6 / total}, check_already_exists=False)
    grouped.update(parameters)
    eis = protocol["kind"] == "impedance"
    # Preserve the author's physical mesh rather than fitting a surrogate.
    model = pybop.lithium_ion.GroupedSPMe(parameter_set=grouped, eis=eis,
                var_pts={"x_n": 100, "x_s": 20, "x_p": 100, "r_n": 100, "r_p": 100},
                options={"surface form": "differential", "contact resistance": "true"},
                solver=pybamm.CasadiSolver(dt_max=100))
    model.build(initial_state={"Initial SoC": float(protocol["soc"])})
    if eis:
        result = np.asarray(model.simulateEIS(inputs=None, f_eval=np.asarray(protocol["frequency_hz"], float))["Impedance"])
        return np.c_[result.real, result.imag].tolist()
    times = np.asarray(protocol["time_s"], float)
    current = np.asarray(protocol["current_a"], float)
    dataset = pybop.Dataset({"Time [s]": times, "Current function [A]": current})
    model.set_current_function(dataset=dataset)
    simulation = model.predict(t_eval=times)
    result = np.asarray(simulation["Voltage [V]"].data)
    if result.shape != times.shape or not np.isfinite(result).all():
        raise ValueError("SPMe failed before the final requested measurement")
    return result.tolist()


if __name__ == "__main__":
    payload = json.load(sys.stdin)
    print(json.dumps(solve(payload["parameters"], payload["protocol"]), allow_nan=False))
