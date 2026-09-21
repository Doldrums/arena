"""Fetch and inspect immutable ZIP source archives; never executes their contents.

archive_spec: {url: HTTPS URL, sha256: 64 lower-case hexadecimal characters,
               strip_prefix: optional single wrapper directory, license: optional}
Cache checkouts are identified by archive digest and the extraction prefix.
A provenance marker records each original file hash. Modified source is reported,
not silently reset. The marker is evidence, not protection from a malicious user
who can alter both the checkout and the marker.
"""

from arena_task_paths import cache_path
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import stat
import tempfile
import unicodedata
from urllib.parse import urlsplit
from urllib.request import Request, HTTPRedirectHandler, build_opener
import zipfile

MARKER = '.autoresearch-archive.json'
MAX_DOWNLOAD_BYTES = 2 * 1024**3
MAX_UNPACKED_BYTES = 4 * 1024**3
MAX_MEMBER_BYTES = 1024**3
MAX_MEMBERS = 100_000


def _validated_spec(spec):
    if not isinstance(spec, dict):
        raise ValueError('Archive specification must be an object')
    url = spec.get('url')
    digest = spec.get('sha256')
    if not isinstance(url, str):
        raise ValueError('Archive URL is required')
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
        raise ValueError('Archive URL must be HTTPS without credentials or fragment')
    if not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{64}', digest):
        raise ValueError('Archive SHA256 must be 64 lower-case hexadecimal characters')
    prefix = spec.get('strip_prefix') or ''
    if not isinstance(prefix, str):
        raise ValueError('strip_prefix must be a directory name or null')
    if prefix.startswith('/'):
        raise ValueError('strip_prefix must be relative')
    prefix = prefix.removesuffix('/')
    if prefix and (prefix in {'.', '..'} or any(c in prefix for c in '/\\:\x00')):
        raise ValueError('strip_prefix must name one relative wrapper directory')
    return {'url': url, 'sha256': digest, 'strip_prefix': prefix, 'license': spec.get('license')}


def archive_path(root, archive_spec):
    """Return the checkout path; does not fetch or create anything."""
    spec = _validated_spec(archive_spec)
    suffix = ('-' + hashlib.sha256(spec['strip_prefix'].encode()).hexdigest()[:12]) if spec['strip_prefix'] else ''
    return cache_path('upstreams', 'archives') / (spec['sha256'] + suffix)


def _file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _json_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def _member_path(info, prefix):
    name = info.filename
    original = getattr(info, 'orig_filename', name)
    if not name or '\x00' in original or '\\' in name or PurePosixPath(name).is_absolute() or PureWindowsPath(name).drive:
        raise ValueError(f'Unsafe ZIP member path: {name!r}')
    parts = name.removesuffix('/').split('/')
    if any(p in {'', '.', '..'} or ':' in p for p in parts):
        raise ValueError(f'Unsafe ZIP member path: {name!r}')
    mode = info.external_attr >> 16
    file_type = stat.S_IFMT(mode)
    if file_type not in {0, stat.S_IFREG, stat.S_IFDIR}:
        raise ValueError(f'ZIP symlinks and special files are forbidden: {name!r}')
    is_dir = info.is_dir()
    if file_type == stat.S_IFDIR and not is_dir:
        raise ValueError(f'Inconsistent ZIP directory member: {name!r}')
    if prefix:
        if parts[0] != prefix:
            raise ValueError(f'ZIP member is outside strip_prefix: {name!r}')
        parts = parts[1:]
        if not parts:
            if not is_dir:
                raise ValueError('strip_prefix names a file, not a wrapper directory')
            return None
    if not parts:
        return None
    relative = PurePosixPath(*parts)
    if relative.parts[0].casefold() == MARKER.casefold():
        raise ValueError('ZIP member collides with the reserved source marker')
    return relative


def extract_archive(zip_path, target, archive_spec):
    """Safely extract a verified ZIP into a new or empty target; return file hashes.

    This helper also checks the archive digest, so using it directly does not skip
    verification. Callers should use a temporary staging directory.
    """
    spec = _validated_spec(archive_spec)
    if Path(zip_path).is_symlink() or _file_hash(zip_path) != spec['sha256']:
        raise ValueError('Archive SHA256 mismatch')
    target = Path(target)
    if target.is_symlink() or (target.exists() and (not target.is_dir() or any(target.iterdir()))):
        raise ValueError('Extraction target must be a new or empty regular directory')
    with zipfile.ZipFile(zip_path) as archive:
        members = archive.infolist()
        if len(members) > MAX_MEMBERS:
            raise ValueError('Archive has too many members')
        if sum(m.file_size for m in members) > MAX_UNPACKED_BYTES:
            raise ValueError('Archive exceeds uncompressed size limit')
        plan = []
        names = {}
        spelling = {}
        for info in members:
            if info.flag_bits & 1:
                raise ValueError('Encrypted source archives are unsupported')
            if info.file_size > MAX_MEMBER_BYTES:
                raise ValueError('Archive member exceeds size limit')
            relative = _member_path(info, spec['strip_prefix'])
            if relative is None:
                continue
            key = unicodedata.normalize('NFC', relative.as_posix()).casefold()
            if key in names:
                raise ValueError(f'Duplicate or case-colliding ZIP member: {relative}')
            for part in [relative, *relative.parents]:
                text = part.as_posix()
                if text == '.':
                    continue
                normalized = unicodedata.normalize('NFC', text).casefold()
                if normalized in spelling and spelling[normalized] != text:
                    raise ValueError('ZIP paths differ only by case or Unicode normalization')
                spelling[normalized] = text
            names[key] = info.is_dir()
            plan.append((info, relative))
        for key in names:
            for ancestor in PurePosixPath(key).parents:
                a = ancestor.as_posix()
                if a in names and not names[a]:
                    raise ValueError('ZIP file is also used as a parent directory')
        target.mkdir(parents=True, exist_ok=True)
        files = {}
        for info, relative in plan:
            destination = target.joinpath(*relative.parts)
            if info.is_dir():
                destination.mkdir(parents=True, exist_ok=True)
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            digest = hashlib.sha256()
            count = 0
            with archive.open(info) as source, destination.open('xb') as output:
                for chunk in iter(lambda: source.read(1024 * 1024), b''):
                    count += len(chunk)
                    if count > info.file_size or count > MAX_MEMBER_BYTES:
                        raise ValueError('ZIP member expands beyond its declared size')
                    digest.update(chunk)
                    output.write(chunk)
            if count != info.file_size:
                raise ValueError('ZIP member size mismatch')
            files[relative.as_posix()] = digest.hexdigest()
    return files


def _snapshot(target):
    files = {}
    for directory, dirs, names in os.walk(target, followlinks=False):
        base = Path(directory)
        for name in list(dirs):
            p = base / name
            if p.is_symlink():
                files[p.relative_to(target).as_posix()] = 'symlink:' + os.readlink(p)
                dirs.remove(name)
        for name in names:
            p = base / name
            relative = p.relative_to(target).as_posix()
            if relative == MARKER:
                continue
            if p.is_symlink():
                files[relative] = 'symlink:' + os.readlink(p)
            elif p.is_file():
                files[relative] = _file_hash(p)
            else:
                files[relative] = 'special-file'
    return files


def verify_archive_checkout(target, archive_spec):
    """Validate the source marker and report changes against its original hashes."""
    spec = _validated_spec(archive_spec)
    target = Path(target)
    marker_path = target / MARKER
    if target.is_symlink() or not target.is_dir() or marker_path.is_symlink() or not marker_path.is_file():
        raise ValueError('Archive checkout has no valid source marker')
    try:
        marker = json.loads(marker_path.read_text())
    except (ValueError, UnicodeError) as error:
        raise ValueError('Archive source marker is invalid JSON') from error
    if not isinstance(marker, dict) or marker.get('schema_version') != '1.0':
        raise ValueError('Archive source marker has an unsupported schema')
    if any(marker.get(key) != spec[key] for key in ('url', 'sha256', 'strip_prefix')):
        raise ValueError('Archive source marker does not match the pinned specification')
    original = marker.get('files')
    if not isinstance(original, dict) or not original:
        raise ValueError('Archive source marker has no file snapshot')
    for name, digest in original.items():
        if not isinstance(name, str) or not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{64}', digest):
            raise ValueError('Archive source marker contains an invalid file hash')
        if PurePosixPath(name).is_absolute() or any(p in {'', '.', '..'} for p in name.split('/')) or '\\' in name:
            raise ValueError('Archive source marker contains an unsafe path')
    if marker.get('snapshot_sha256') != _json_hash(original):
        raise ValueError('Archive source marker snapshot checksum is inconsistent')
    current = _snapshot(target)
    modified = sorted(name for name in original.keys() & current.keys() if original[name] != current[name])
    added = sorted(current.keys() - original.keys())
    deleted = sorted(original.keys() - current.keys())
    return {'source_type': 'archive', 'archive_sha256': spec['sha256'],
            'source_manifest_sha256': _file_hash(marker_path),
            'source_snapshot_sha256': marker['snapshot_sha256'],
            'current_snapshot_sha256': _json_hash(current),
            'working_tree_modified': bool(modified or added or deleted),
            'modified_files': modified, 'added_files': added, 'deleted_files': deleted}


def source_status(target, archive_spec):
    """Alias for consumers asking for archive provenance/status."""
    return verify_archive_checkout(target, archive_spec)


class _HTTPSRedirects(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        if urlsplit(newurl).scheme != 'https':
            raise ValueError('Archive download redirected away from HTTPS')
        return super().redirect_request(request, fp, code, msg, headers, newurl)


def _download(url, destination):
    request = Request(url, headers={'User-Agent': 'autoresearch-tasks/1.0'})
    with build_opener(_HTTPSRedirects()).open(request, timeout=60) as response, Path(destination).open('wb') as output:
        if urlsplit(response.geturl()).scheme != 'https':
            raise ValueError('Archive download redirected away from HTTPS')
        size = 0
        for chunk in iter(lambda: response.read(1024 * 1024), b''):
            size += len(chunk)
            if size > MAX_DOWNLOAD_BYTES:
                raise ValueError('Archive exceeds download size limit')
            output.write(chunk)


def setup_archive(root, archive_spec):
    """Fetch, verify, extract and snapshot a pinned archive, without installing it."""
    spec = _validated_spec(archive_spec)
    target = archive_path(root, spec)
    if target.exists() or target.is_symlink():
        status = verify_archive_checkout(target, spec)
        return {'status': 'ready', 'checkout': str(target), 'dependencies_installed': False, **status}
    target.parent.mkdir(parents=True, exist_ok=True)
    downloads = cache_path('downloads')
    downloads.mkdir(parents=True, exist_ok=True)
    download = downloads / (spec['sha256'] + '.zip')
    if download.exists() or download.is_symlink():
        if download.is_symlink() or not download.is_file() or _file_hash(download) != spec['sha256']:
            raise ValueError('Cached archive SHA256 mismatch')
    else:
        with tempfile.TemporaryDirectory(dir=downloads, prefix='fetch-') as temporary:
            pending = Path(temporary) / 'source.zip'
            _download(spec['url'], pending)
            if _file_hash(pending) != spec['sha256']:
                raise ValueError('Downloaded archive SHA256 mismatch')
            # The checksum address makes concurrent publication of identical bytes safe.
            os.replace(pending, download)
    with tempfile.TemporaryDirectory(dir=target.parent, prefix='extract-') as temporary:
        staging = Path(temporary) / 'checkout'
        files = extract_archive(download, staging, spec)
        if not files:
            raise ValueError('Source archive contains no files')
        marker = {'schema_version': '1.0', **spec, 'files': files,
                  'snapshot_sha256': _json_hash(files),
                  'created_at': datetime.now(timezone.utc).isoformat()}
        (staging / MARKER).write_text(json.dumps(marker, sort_keys=True, indent=2) + '\n')
        try:
            staging.rename(target)
        except FileExistsError:
            # Another process completed the same checkout; validate its marker below.
            pass
    status = verify_archive_checkout(target, spec)
    return {'status': 'source_fetched', 'checkout': str(target), 'dependencies_installed': False, **status}
