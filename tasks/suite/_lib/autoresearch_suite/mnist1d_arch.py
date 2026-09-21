"""Neural architecture search on MNIST-1D (EvoPrompting, recreated protocol).

EvoPrompting evolves PyTorch model code and scores it by test error and model
size on MNIST-1D, a 40-sample-long procedurally generated 1-D version of MNIST
(Greydanus 2020) that trains in seconds on a CPU. The candidate exposes::

    build_model() -> torch.nn.Module   # maps (batch, 40) float inputs to (batch, 10) logits

The evaluator generates the dataset deterministically with the ``mnist1d``
package (4000 train / 1000 test), trains with Adam for a fixed number of steps
and reports ``test_error + size_penalty * parameters / 100000``; lower is
better. Models above ``max_parameters`` are rejected.
"""
from __future__ import annotations

import numpy as np

from .runtime import CandidateError, require


def dataset():
    try:
        from mnist1d.data import get_dataset_args, make_dataset
    except ImportError as error:
        raise CandidateError(f"mnist1d is required: {error}") from None
    args = get_dataset_args()
    data = make_dataset(args)
    return (np.asarray(data["x"], dtype=np.float32), np.asarray(data["y"], dtype=np.int64),
            np.asarray(data["x_test"], dtype=np.float32), np.asarray(data["y_test"], dtype=np.int64))


def mnist1d_score(build_model, steps=1500, batch_size=128, lr=1e-3, seed=0, max_parameters=250_000, size_penalty=0.05):
    try:
        import torch
    except ImportError as error:
        raise CandidateError(f"torch is required: {error}") from None
    torch.manual_seed(seed)
    x, y, x_test, y_test = dataset()
    try:
        model = build_model()
    except CandidateError:
        raise
    except Exception as error:  # noqa: BLE001
        raise CandidateError(f"build_model raised {type(error).__name__}: {error}") from None
    require(isinstance(model, torch.nn.Module), "build_model must return a torch.nn.Module")
    parameters = sum(p.numel() for p in model.parameters())
    require(0 < parameters <= max_parameters, f"model has {parameters} parameters; allowed 1..{max_parameters}")
    x_t, y_t = torch.from_numpy(x), torch.from_numpy(y)
    with torch.no_grad():
        probe = model(x_t[:4])
    require(tuple(probe.shape) == (4, 10), f"model must map (batch, 40) to (batch, 10) logits; got {tuple(probe.shape)}")
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    rng = np.random.default_rng(seed)
    model.train()
    for _ in range(steps):
        idx = torch.from_numpy(rng.integers(0, len(x), batch_size))
        optimizer.zero_grad()
        loss = torch.nn.functional.cross_entropy(model(x_t[idx]), y_t[idx])
        require(bool(torch.isfinite(loss)), "training loss became non-finite")
        loss.backward()
        optimizer.step()
    model.eval()
    with torch.no_grad():
        test_error = float((model(torch.from_numpy(x_test)).argmax(1) != torch.from_numpy(y_test)).float().mean())
        train_error = float((model(x_t).argmax(1) != y_t).float().mean())
    score = test_error + size_penalty * parameters / 100_000
    return score, {"test_error": test_error, "train_error": train_error, "parameters": parameters, "steps": steps}
