"""Root-owned broker for an operator-approved private SCiEL image.

Only explicit admitted runs reach Docker. Clients supply an existing run ID and
deployment digest, never an image, mount, command, credential, or Docker option.
"""

from .engine_policy import (
    Config,
    MAX_ARTIFACTS,
    MAX_JSON,
    MAX_LOG,
    admission,
    checked_native_config,
    input_file,
    replace_private,
    root_file,
    stage_tree,
    write_private,
)
from .engine_execution import (
    Broker,
)
from .engine_http import (
    Handler,
    Server,
    main,
)
from .evaluator_policy import Denied, DockerConnection, RUN, directory_fd, json_object, peer_run, read_regular, require


if __name__ == "__main__":
    main()
