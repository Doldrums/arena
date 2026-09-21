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


def requirement_group(requirements):
    """Return the minimum reviewed CPU image group, or None when unsupported."""
    if not supports_requirements(requirements):
        return None
    return "base" if set(requirements) <= BASE_CPU_REQUIREMENTS else "extended"


def supports_requirements(requirements):
    """Match catalog aliases exactly; never infer support from package names."""
    return (type(requirements) is list
            and all(type(value) is str and value in CPU_REQUIREMENTS for value in requirements))
