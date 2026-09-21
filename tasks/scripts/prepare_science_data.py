#!/usr/bin/env python3
"""Fetch the real-measurement datasets used by the science supplement into suite/_lib/data (git-ignored).

* Pantheon+SH0ES supernova Hubble diagram and its STAT+SYS covariance from the
  public data release (github.com/PantheonPlusSH0ES/DataRelease), pinned to a
  commit and SHA-256; the covariance text file is converted to a NumPy array.

    python3 scripts/prepare_science_data.py
"""
from __future__ import annotations

import sys as _task_sys
from pathlib import Path as _TaskPath
_task_sys.path.insert(0, str(_TaskPath(__file__).resolve().parents[1] / "suite" / "_lib"))
from arena_task_paths import data_root

import hashlib
import urllib.request
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = data_root() / "pantheon-plus"
COMMIT = "c447f0fea703fcd0fff57de5000947b5ca81286b"
BASE = f"https://raw.githubusercontent.com/PantheonPlusSH0ES/DataRelease/{COMMIT}/Pantheon+_Data/4_DISTANCES_AND_COVAR/"
FILES = {"Pantheon+SH0ES.dat": "1cb0fc379ef066afdc2ffd1857681cc478024570d8a3eba284fb645775198cf8",
         "Pantheon+SH0ES_STAT+SYS.cov": "abf806d966485e64afdb359c87bffc0ecc00d05eff0a31ced66f247385df0fdc"}


def fetch(name, digest):
    path = DATA / name
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        with urllib.request.urlopen(BASE + name.replace("+", "%2B"), timeout=120) as response:
            raw = response.read()
        if hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError(f"{name}: SHA-256 differs from the pinned value")
        path.write_bytes(raw)
    return path


def main():
    DATA.mkdir(parents=True, exist_ok=True)
    for name, digest in FILES.items():
        fetch(name, digest)
    cov_npy = DATA / "Pantheon+SH0ES_STAT+SYS.npy"
    if not cov_npy.is_file():
        values = np.loadtxt(DATA / "Pantheon+SH0ES_STAT+SYS.cov")
        n = int(values[0])
        matrix = values[1:].reshape(n, n)
        if not np.allclose(matrix, matrix.T, atol=1e-6):
            raise ValueError("covariance is not symmetric")
        np.save(cov_npy, 0.5 * (matrix + matrix.T))  # text rounding leaves 3e-8 asymmetry; symmetrise for Cholesky
    print(f"pantheon-plus: {len(FILES)} files, covariance {np.load(cov_npy).shape}")


if __name__ == "__main__":
    main()
