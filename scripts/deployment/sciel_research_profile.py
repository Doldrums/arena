"""Compatibility imports for deployment preparation; runtime lives in arena."""
from arena.sciel_research_profile import (
    CHECKS,
    ENGINE_COMMIT,
    LIMITS,
    PARALLEL,
    PROFILE,
    RUNTIME_SOURCES,
    apply_research_profile,
    canonical,
    profile_identity,
    require_conformance,
    research_config,
    tools_config,
)

__all__ = [
    "CHECKS", "ENGINE_COMMIT", "LIMITS", "PARALLEL", "PROFILE", "RUNTIME_SOURCES",
    "apply_research_profile", "canonical", "profile_identity", "require_conformance",
    "research_config", "tools_config",
]
