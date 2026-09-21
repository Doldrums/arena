"""Supply SCiEL's undeclared AlgoTune dependency without changing its protocol.

The original evaluator discovers three machine-specific paths. This adapter
loads a byte-verified, vendored subset of the official AlgoTune repository and
sets the evaluator's registry explicitly. Its scoring, timings, configuration,
candidate and validity interpretation remain those of the SCiEL source.
"""

import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent
TASKS = {
    "affine_transform_2d", "convolve2d_full_fill", "eigenvectors_complex",
    "fft_cmplx_scipy_fftpack", "fft_convolution", "lu_factorization",
    "polynomial_real", "psd_cone_projection",
}


def verify_vendor():
    """Verify every distributed source byte before importing this dependency."""
    provenance = json.loads((ROOT / "sources.json").read_text())
    vendor = (ROOT / "vendor").resolve()
    for relative, expected in provenance["files"].items():
        path = (vendor / relative).resolve()
        if not path.is_relative_to(vendor) or not path.is_file():
            raise ValueError(f"Missing pinned AlgoTune asset: {relative}")
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f"Pinned AlgoTune asset has changed: {relative}")
    return vendor, provenance


def evaluate(candidate_path, *, checkout, task):
    if task not in TASKS:
        raise ValueError(f"Unknown recovered SCiEL AlgoTune task: {task}")
    vendor, provenance = verify_vendor()
    sys.path[:0] = [str(Path(checkout).resolve() / "engine"), str(Path(checkout).resolve())]
    sys.path.insert(0, str(vendor))
    importlib.import_module(f"AlgoTuneTasks.{task}.{task}")
    from AlgoTuneTasks.base import TASK_REGISTRY

    # Do not accept a previously imported, unrelated copy of these modules.
    for name, module in tuple(sys.modules.items()):
        location = getattr(module, "__file__", None)
        if name.startswith(("AlgoTuneTasks", "AlgoTuner")) and location:
            if not Path(location).resolve().is_relative_to(vendor):
                raise ValueError(f"AlgoTune module was loaded outside the pinned dependency: {name}")

    source = Path(checkout).resolve() / "examples" / "algotune" / task / "evaluator.py"
    spec = importlib.util.spec_from_file_location("sciel_original_algotune_evaluator", source)
    original = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(original)
    original.TASK_REGISTRY = TASK_REGISTRY
    # Leave config=None: the unmodified evaluator reads its original YAML.
    result = original.evaluate(str(Path(candidate_path).resolve()))
    result["dependency_provenance"] = {
        "repository": provenance["repository"],
        "commit": provenance["commit"],
        "adapter_change": "Explicit registry discovery; original evaluator and YAML unchanged",
    }
    return result
