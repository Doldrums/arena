"""Declared dependency boundary for the prepared, network-free CPU image.

Eligibility is not runtime evidence. The exact pinned image must also evaluate
the task's seed successfully before campaign preparation accepts it.
"""
from __future__ import annotations

# Left side is the task catalog's import-name requirement; right side documents
# the distribution installed in the reviewed evaluation image. No implicit alias
# expansion admits a new environment, native executable, data mount or service.
CPU_DEPENDENCIES = {
    "py:numpy": "numpy",
    "py:scipy": "scipy",
    "py:sklearn": "scikit-learn",
    "py:cvxpy": "cvxpy",
    "py:sympy": "sympy",
    "py:shapely": "shapely",
    "py:bs4": "beautifulsoup4",
    "py:lxml": "lxml",
    "py:matplotlib": "matplotlib",
    "py:pykalman": "pykalman",
    "py:pywt": "PyWavelets",
    "py:gymnasium": "gymnasium",
    "py:networkx": "networkx",
    "py:pandas": "pandas",
}
CPU_REQUIREMENTS = frozenset(CPU_DEPENDENCIES)
BASE_CPU_REQUIREMENTS = frozenset({"py:numpy", "py:scipy"})
CPU_PROFILE = "sciel-catalog-cpu/1"
SCIENCE_PROFILE = "sciel-catalog-prepared-science/1"

# This environment contains only the reviewed source subsets listed below.
# New datasets, packages or image builds require a new reviewed profile pin.
SCIENCE_IMAGE_ID = "sha256:51c51296d55326219ea316c58115c5f843c680db2efce771f67eb28371739ed0"
SCIENCE_IMAGE_REFERENCE = ("127.0.0.1:5000/empira/canonical-science-cpu@sha256:"
                           "7f3715b194c745682d4235b6e8f7d22223f3f47d772138b63ca424fc0cc79cae")
SCIENCE_DATA_LOCK_SHA256 = "1bd32da2324b6a8a979101768ae03a9b731dfbbdaa123946f723fe82e2e22a0b"
SCIENCE_TASK_REQUIREMENTS = {
    "science-biology-beeline-regulatory-network": (
        "file:../../.cache/science-biology/B11.json", "file:../../.cache/science-biology/B11.manifest.json",
        "py:numpy", "py:scipy"),
    "science-biology-casanovo-peptide-decoding": (
        "file:../../.cache/science-biology/B12.json", "file:../../.cache/science-biology/B12.manifest.json",
        "py:numpy", "py:scipy"),
    "science-biology-petab-kinetic-inference": (
        "file:../../.cache/science-biology/B10.json", "file:../../.cache/science-biology/B10.manifest.json",
        "py:numpy", "py:scipy"),
    "science-biology-phylogenetic-likelihood": (
        "file:../../.cache/science-biology/B07.json", "file:../../.cache/science-biology/B07.manifest.json",
        "py:numpy", "py:scipy"),
    "science-earth-camels-runoff": (
        "file:../../.cache/science-earth-data/E01.json", "file:../../.cache/science-earth-data/E01.manifest.json",
        "py:numpy", "py:scipy"),
    "science-materials-cantera-mechanism-reduction": ("py:cantera", "py:numpy"),
    "science-materials-edbo-reaction-discovery": (
        "file:data/materials-expansion/C01/experiments_yield_and_cost.csv", "py:numpy"),
    "science-physics-refnx-contrast-inversion": (
        "file:data/physics-expansion/P13/benchmark.npz", "file:data/physics-expansion/P13/manifest.json",
        "py:numpy", "py:scipy"),
}


def supports_science_task(task_id, requirements):
    """Exact task/requirement matches, never general file or package admission."""
    return (type(task_id) is str and task_id in SCIENCE_TASK_REQUIREMENTS
            and type(requirements) is list
            and tuple(requirements) == SCIENCE_TASK_REQUIREMENTS[task_id])


def science_environment(image):
    """Immutable image identity includes the reviewed prepared-data closure."""
    if image not in (SCIENCE_IMAGE_ID, SCIENCE_IMAGE_REFERENCE):
        raise ValueError("Prepared science requires its exact reviewed image digest")
    return {"profile": SCIENCE_PROFILE, "image_id": SCIENCE_IMAGE_ID,
            "image_reference": SCIENCE_IMAGE_REFERENCE, "data_lock_sha256": SCIENCE_DATA_LOCK_SHA256}


def validate_task_profile(task, evaluation):
    """Bind extra environment data only for an explicitly reviewed cohort."""
    profile = evaluation.get("profile", CPU_PROFILE)
    from .sciel_catalog_jax import JAX_PROFILE, validate_jax_task
    from .sciel_catalog_torch import TORCH_PROFILE, validate_torch_task
    if profile == JAX_PROFILE:
        return validate_jax_task(task, evaluation)
    if profile == TORCH_PROFILE:
        return validate_torch_task(task, evaluation)
    if profile == SCIENCE_PROFILE:
        environment = science_environment(evaluation["execution"]["image"])
        if not supports_science_task(task["id"], task.get("requirements")):
            raise ValueError("Task and requirements are outside the exact prepared science cohort")
        return environment
    if profile != CPU_PROFILE:
        raise ValueError("Unknown catalog evaluation profile")
    if not supports_requirements(task.get("requirements")):
        raise ValueError("Catalog CPU profile supports only explicitly approved CPU dependencies")
    return None


def requirement_group(requirements):
    """Return the minimum reviewed CPU image group, or None when unsupported."""
    if not supports_requirements(requirements):
        return None
    return "base" if set(requirements) <= BASE_CPU_REQUIREMENTS else "extended"


def supports_requirements(requirements):
    """Match catalog aliases exactly; never infer support from package names."""
    return (type(requirements) is list
            and all(type(value) is str and value in CPU_REQUIREMENTS for value in requirements))
