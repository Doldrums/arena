"""Run-scoped Docker SDK capability for the pinned, prebuilt DGM experiment.

This service is deliberately separate from the canonical evaluator and SCiEL
brokers. It never builds/pulls images or mounts host paths into a container.
Native commands execute only inside approved, offline, resource-bound images.
"""

from .dgm_policy import (
    ALIAS,
    BOOTSTRAP,
    Config,
    HEX,
    LABEL,
    MAX_ENTRIES,
    MAX_EXPANDED,
    MAX_JSON,
    MAX_STREAM,
    MAX_TAR,
    NATIVE_NAME,
    PIN,
    REQUEST_TIMEOUT,
    admission,
    atomic_record,
    container_path,
    encoded,
    peer_run,
    result,
    root_file,
    route,
    sanitize_tar,
)
from .dgm_execution import (
    Proxy,
)
from .dgm_http import (
    Handler,
    RelayHandler,
    RelayServer,
    Server,
    main,
)
from .evaluator_policy import Denied, DockerConnection, RUN, _peer_identity, directory_fd, json_object, only_defaults, read_regular, require


if __name__ == "__main__":
    main()
