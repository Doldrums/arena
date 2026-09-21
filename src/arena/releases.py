"""Immutable private release bindings and a minimal public release reference.

Registration and resolution never fetch code, inspect credentials, start an
image or execute a participant. Only the private worker resolver sees pointers.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import stat
import tempfile
from urllib.parse import urlsplit


SYSTEM_PATTERN = r"[a-z0-9][a-z0-9-]{0,63}"
VERSION_PATTERN = r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)(?:-(?:0|[1-9][0-9]*|[0-9]*[A-Za-z-][0-9A-Za-z-]*)(?:\.(?:0|[1-9][0-9]*|[0-9]*[A-Za-z-][0-9A-Za-z-]*))*)?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
IMAGE_PATTERN = r"(?:[a-z0-9][a-z0-9.-]*(?::[0-9]{1,5})?/)?(?:[a-z0-9]+(?:[._-][a-z0-9]+)*/)*[a-z0-9]+(?:[._-][a-z0-9]+)*@sha256:[0-9a-f]{64}"
MAX_RECORD_BYTES = 64 * 1024


class ReleaseError(ValueError):
    """A release record violates the private/public boundary or binding."""


class ReleaseNotFound(ReleaseError):
    """The worker has no private registration for the public reference."""


def _record_bytes(value):
    payload = (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()
    if len(payload) > MAX_RECORD_BYTES:
        raise ReleaseError("Private release record exceeds the size limit")
    return payload


def _identity(value):
    if (not isinstance(value.get("system"), str)
            or re.fullmatch(SYSTEM_PATTERN, value["system"]) is None):
        raise ReleaseError("Release system must be a lowercase identifier")
    if (not isinstance(value.get("version"), str) or len(value["version"]) > 128
            or re.fullmatch(VERSION_PATTERN, value["version"]) is None):
        raise ReleaseError("Release version must be an explicit semantic version")


def validate_public_release(value: dict) -> dict:
    if type(value) is not dict or set(value) != {"schema", "system", "version"}:
        raise ReleaseError("Public release permits only schema, system and version")
    if value["schema"] != "arena.release/1":
        raise ReleaseError("Expected arena.release/1")
    _identity(value)
    return dict(value)


def validate_private_release(value: dict) -> dict:
    if type(value) is not dict or set(value) != {"schema", "system", "version", "repository", "image"}:
        raise ReleaseError("Private release requires exactly identity, repository pin and image digest")
    if value["schema"] != "arena.private-release/1":
        raise ReleaseError("Expected arena.private-release/1")
    _identity(value)
    repository = value["repository"]
    if type(repository) is not dict or set(repository) != {"url", "commit"}:
        raise ReleaseError("Repository requires only a URL and exact commit")
    url = repository["url"]
    if not isinstance(url, str) or len(url) > 2048 or any(c.isspace() or ord(c) < 32 for c in url):
        raise ReleaseError("Repository URL must be credential-free HTTPS")
    try:
        parsed = urlsplit(url)
        parsed.port  # Validate the optional port without exposing the URL.
        valid_url = (parsed.scheme == "https" and parsed.hostname and parsed.path.strip("/")
                     and parsed.username is None and parsed.password is None and not parsed.query and not parsed.fragment)
    except ValueError:
        valid_url = False
    if not valid_url:
        raise ReleaseError("Repository URL must be credential-free HTTPS without query or fragment")
    if not isinstance(repository["commit"], str) or not re.fullmatch(r"[0-9a-f]{40}", repository["commit"]):
        raise ReleaseError("Repository must use a full immutable Git commit")
    if (not isinstance(value["image"], str) or len(value["image"]) > MAX_RECORD_BYTES
            or re.fullmatch(IMAGE_PATTERN, value["image"]) is None):
        raise ReleaseError("Worker image must use a credential-free repository@sha256 digest")
    checked = {"schema": value["schema"], "system": value["system"], "version": value["version"],
               "repository": dict(repository), "image": value["image"]}
    _record_bytes(checked)
    return checked


def public_release(value: dict) -> dict:
    """Project only public identity; private pointers never enter the result."""
    checked = validate_private_release(value)
    return {"schema": "arena.release/1", "system": checked["system"], "version": checked["version"]}


def _decode_record(data):
    def unique_fields(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ReleaseError("Release record contains duplicate fields")
            result[key] = value
        return result
    return json.loads(data, object_pairs_hook=unique_fields)


def _private_directory(path, *, create=False):
    if path.is_symlink():
        raise ReleaseError("Private store directories must not be symlinks")
    if create:
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if not path.exists():
        raise ReleaseNotFound("Private release store is not available")
    info = path.stat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ReleaseError("Private store directories must be owned by this worker and accessible only to it")


def _store_path(store_dir, *, create=False, public_roots=()):
    original = Path(store_dir)
    if not original.is_absolute() or original.is_symlink():
        raise ReleaseError("Private release store must be an absolute non-symlink directory")
    path = original.resolve()
    # A source checkout, installed package tree and explicitly declared web
    # roots are never private stores, including any parent that contains them.
    forbidden = [Path(__file__).resolve().parents[2], *map(Path, public_roots)]
    for root in forbidden:
        root = root.resolve()
        if path.is_relative_to(root) or root.is_relative_to(path):
            raise ReleaseError("Private release store must be outside public/source roots")
    _private_directory(path, create=create)
    return path


def _read_record(path):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError as exc:
        raise ReleaseNotFound("No private release binding exists for this system/version") from exc
    except OSError as exc:
        raise ReleaseError("Private release record cannot be opened safely") from exc
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or info.st_mode & 0o077 or info.st_size > MAX_RECORD_BYTES):
            raise ReleaseError("Private release record is not a bounded, worker-private regular file")
        data = stream.read(MAX_RECORD_BYTES + 1)
    if len(data) > MAX_RECORD_BYTES:
        raise ReleaseError("Private release record exceeds the size limit")
    try:
        return validate_private_release(_decode_record(data))
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise ReleaseError("Private release record is invalid") from exc


def register_release(store_dir: Path, value: dict, *, public_roots=()) -> dict:
    """Bind a version once; identical registration is an idempotent no-op."""
    checked = validate_private_release(value)
    payload = _record_bytes(checked)
    root = _store_path(store_dir, create=True, public_roots=public_roots)
    directory = root / checked["system"]
    _private_directory(directory, create=True)
    path = directory / (checked["version"] + ".json")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=directory, prefix=".pending-", delete=False) as stream:
            temporary = Path(stream.name)
            os.fchmod(stream.fileno(), 0o600)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            # Atomic create-only publication: readers never see partial JSON,
            # and concurrent registration cannot replace an existing binding.
            os.link(temporary, path, follow_symlinks=False)
        except FileExistsError:
            if _read_record(path) != checked:
                raise ReleaseError("This system/version already has an immutable private binding")
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return public_release(checked)


def resolve_release(store_dir: Path, reference: dict, *, public_roots=()) -> dict:
    """Worker-only lookup; absence or malformed records fail closed."""
    checked = validate_public_release(reference)
    root = _store_path(store_dir, public_roots=public_roots)
    directory = root / checked["system"]
    _private_directory(directory)
    record = _read_record(directory / (checked["version"] + ".json"))
    if public_release(record) != checked:
        raise ReleaseError("Private binding identity does not match the requested release")
    return record


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("register", "resolve"):
        command = commands.add_parser(name)
        command.add_argument("record", type=Path)
        command.add_argument("--store", type=Path, required=True)
        command.add_argument("--public-root", type=Path, action="append", default=[])
    args = parser.parse_args(argv)
    try:
        with args.record.open("rb") as stream:
            data = stream.read(MAX_RECORD_BYTES + 1)
        if len(data) > MAX_RECORD_BYTES:
            raise ReleaseError("Release input exceeds the size limit")
        value = _decode_record(data)
        function = register_release if args.command == "register" else resolve_release
        result = function(args.store, value, public_roots=args.public_root)
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0
    except (OSError, ValueError, UnicodeError, RecursionError):
        # Inputs may be private: don't echo record contents, URLs or paths.
        parser.exit(2, "Release registration/resolution failed; no release was selected.\n")


if __name__ == "__main__":
    raise SystemExit(main())
