"""Restricted, Linux-only Docker socket for canonical Arena evaluations.

This is a privileged boundary, not a general Docker proxy. Requests are rebuilt
from a fixed evaluator profile. No caller-provided Docker configuration is
forwarded, and mutable candidate/output paths are never passed to the daemon.
"""

from .evaluator_policy import (
    Config,
    Denied,
    DockerConnection,
    IMAGE,
    MAX_BODY,
    MAX_RESPONSE,
    MAX_STREAM,
    RUN,
    _peer_identity,
    canonical_config,
    directory_fd,
    engine_binding,
    json_object,
    only_defaults,
    peer_run,
    read_regular,
    require,
    route,
)
from .evaluator_execution import (
    Proxy,
)
from .evaluator_http import (
    Handler,
    Server,
    main,
)


if __name__ == "__main__":
    main()
