"""Versioned one-CPU timing policy for the recreated CPU kernel cohort.

Historical host-wide thread timings are a different protocol. The requested
thread count never comes from host CPU inventory or candidate environment.
"""
from typing import Protocol, TypeVar

from .runtime import CandidateError, require


POLICY = "arena.kernel-cpu.single-thread/1"


class ThreadRuntime(Protocol):
    def get_num_threads(self) -> int: ...
    def get_num_interop_threads(self) -> int: ...
    def set_num_threads(self, count: int) -> None: ...
    def set_num_interop_threads(self, count: int) -> None: ...


Runtime = TypeVar("Runtime", bound=ThreadRuntime)


def require_policy(torch: ThreadRuntime) -> None:
    """Reject thread-policy drift rather than describing it as a one-CPU run."""
    require(torch.get_num_threads() == 1 and torch.get_num_interop_threads() == 1,
            "CPU kernel timing policy requires one intra-op and one inter-op thread")


def configure(torch: Runtime) -> Runtime:
    """Idempotent even after PyTorch's one-shot inter-op setter was used."""
    try:
        if torch.get_num_threads() != 1:
            torch.set_num_threads(1)
        if torch.get_num_interop_threads() != 1:
            torch.set_num_interop_threads(1)
    except RuntimeError:
        raise CandidateError("Cannot establish the one-CPU kernel timing policy; "
                             "evaluate in a fresh process before parallel work") from None
    require_policy(torch)
    return torch


def details(torch: ThreadRuntime) -> dict[str, str | int]:
    require_policy(torch)
    return {"thread_policy": POLICY, "threads": torch.get_num_threads(),
            "interop_threads": torch.get_num_interop_threads()}
