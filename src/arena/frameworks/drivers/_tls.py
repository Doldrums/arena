"""Explicit, provenance-hashed CA input for HTTPS-only native clients."""
import os
from pathlib import Path
import ssl


def configure_ca(path: Path | None):
    if path is None:
        return
    path = path.absolute()
    if path.is_symlink() or any(parent.is_symlink() for parent in path.parents) or not path.is_file():
        raise ValueError("TLS CA bundle must be a regular file without symlinks")
    if not 1 <= path.stat().st_size <= 4 * 1024 * 1024:
        raise ValueError("TLS CA bundle exceeds the file limit")
    # Validate the bundle before the native constructor can send a request.
    # The operator bundle includes system roots as well as the local relay CA.
    ssl.create_default_context(cafile=str(path))
    os.environ["SSL_CERT_FILE"] = str(path)
