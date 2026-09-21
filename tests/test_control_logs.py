import os

import pytest

from arena import control, control_logs
from control_helpers import principal, service, submit


def test_logs_cursor_tail_and_native_secret_exclusion(service):
    user, _ = principal(service)
    run = submit(service, user)
    directory = service.runs_dir / run["id"]
    raw = directory / "artifacts" / ".arena"
    raw.mkdir(parents=True)
    (raw / "stdout.log").write_text("sk-this-is-a-native-model-secret\nprint('generated code')")
    first = service.logs(user, run["id"], limit=12)
    second = service.logs(user, run["id"], cursor=first["next_cursor"], limit=32)
    whole = service.logs(user, run["id"])
    assert (first["text"] + second["text"]) == whole["text"][:44]
    assert "sk-" not in whole["text"] and "generated code" not in whole["text"]
    tail = service.logs(user, run["id"], tail=True, limit=10)
    assert tail["text"] == whole["text"][-10:]
    assert tail["eof"] is True
    with pytest.raises(control.ControlError):
        service.logs(user, run["id"], stream="../snapshot.json")
    with pytest.raises(control.ControlError):
        service.logs(user, run["id"], limit=65537)


def test_log_symlink_hardlink_and_directory_traversal_rejected(service, tmp_path):
    user, _ = principal(service)
    run = submit(service, user)
    log = service.runs_dir / run["id"] / "stdout.log"
    outside = tmp_path / "secret"
    outside.write_text("secret")
    log.unlink()
    log.symlink_to(outside)
    with pytest.raises(OSError):
        service.logs(user, run["id"])
    log.unlink()
    os.link(outside, log)
    with pytest.raises(control.ControlError):
        service.logs(user, run["id"])
    with pytest.raises(control.ControlError):
        service.logs(user, "../secret")


def test_native_log_scope_redacts_worker_secrets_before_pagination(service, monkeypatch):
    user, _ = principal(service)
    run = submit(service, user)
    native, _ = principal(service, scopes=("read", "logs:native"))
    directory = service.runs_dir / run["id"]
    raw = directory / "artifacts" / ".arena"
    raw.mkdir(parents=True)
    secret = "fixture-gateway-credential-0123456789"
    monkeypatch.setenv("ARENA_PROVIDER_CLIENT_KEY", secret)
    payload = "diagnostic " + secret + "\n" + "Bearer abc123\n" + "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJyb290In0.signature\n"
    (raw / "stdout.log").write_text(payload)
    with pytest.raises(control.ControlError) as caught:
        service.logs(user, run["id"], stream="native_stdout")
    assert caught.value.status == 403
    assert service.logs(native, run["id"], stream="native_stdout")["pending"]
    control_logs._publish_native_logs(directory, control_logs._secret_values())
    # The HTTP process can now lack all worker credentials; it reads only the
    # already redacted snapshot and cannot fall back to the raw source file.
    monkeypatch.delenv("ARENA_PROVIDER_CLIENT_KEY")
    text = ""
    cursor = 0
    while True:
        page = service.logs(native, run["id"], stream="native_stdout", cursor=cursor, limit=7)
        text += page["text"]
        cursor = page["next_cursor"]
        if page["eof"]:
            break
    assert secret not in text and "abc123" not in text and "eyJ" not in text
    assert "diagnostic" in text and "REDACTED" in text
    assert (directory / "native_stdout.log").stat().st_mode & 0o077 == 0
    assert secret not in service.db_path.read_bytes().decode(errors="replace")


def test_growing_partial_native_credential_is_not_published(service):
    user, _ = principal(service, scopes=("admin",))
    run = submit(service, user)
    directory = service.runs_dir / run["id"]
    raw = directory / "artifacts" / ".arena"
    raw.mkdir(parents=True)
    secret = "private-value-abcdefghijklmnop"
    cache = {}
    for length in (3, 10, len(secret)):
        (raw / "stderr.log").write_text("message " + secret[:length])
        control_logs._publish_native_logs(directory, (secret,), cache=cache)
        result = service.logs(user, run["id"], stream="native_stderr")
        assert secret[:length] not in result["text"]
        assert "message [REDACTED]" in result["text"]


def test_native_log_redactor_never_follows_raw_symlinks(service, tmp_path):
    user, _ = principal(service, scopes=("admin",))
    run = submit(service, user)
    directory = service.runs_dir / run["id"]
    raw = directory / "artifacts" / ".arena"
    raw.mkdir(parents=True)
    target = tmp_path / "private-other-file"
    target.write_text("unrelated private data")
    (raw / "stdout.log").symlink_to(target)
    control_logs._publish_native_logs(directory, ())
    result = service.logs(user, run["id"], stream="native_stdout")
    assert result["pending"] is True and result["text"] == ""


def native_log_files(service):
    user, _ = principal(service)
    run = submit(service, user)
    directory = service.runs_dir / run["id"]
    raw = directory / "artifacts" / ".arena"
    raw.mkdir(parents=True)
    return directory, raw


def test_unchanged_native_logs_skip_content_reads_and_writes(service, monkeypatch):
    directory, raw = native_log_files(service)
    (raw / "stdout.log").write_text("ordinary stdout")
    (raw / "stderr.log").write_text("ordinary stderr")
    diagnostic = directory / "preparation.stderr"
    diagnostic.write_text("private preparation note")
    diagnostic.chmod(0o600)
    cache = {}
    control_logs._publish_native_logs(directory, (), cache=cache)

    def unexpected(*args, **kwargs):
        pytest.fail("Unchanged native logs must not be read or rewritten")

    monkeypatch.setattr(control_logs, "_read_regular", unexpected)
    monkeypatch.setattr(control_logs, "_replace_private_bytes", unexpected)
    control_logs._publish_native_logs(directory, (), cache=cache)
    assert len(cache) == 2


@pytest.mark.parametrize("change", ["append", "truncate", "replace", "rewrite_same_size"])
def test_native_log_cache_tracks_source_mutations(service, change):
    directory, raw = native_log_files(service)
    source = raw / "stdout.log"
    source.write_text("first")
    original = source.stat()
    cache = {}
    control_logs._publish_native_logs(directory, (), cache=cache)
    if change == "append":
        with source.open("a") as stream:
            stream.write(" appended")
        expected = "first appended"
    elif change == "truncate":
        source.write_text("")
        expected = ""
    elif change == "replace":
        replacement = raw / "replacement"
        replacement.write_text("replacement")
        replacement.replace(source)
        expected = "replacement"
    else:
        source.write_text("other")
        os.utime(source, ns=(original.st_atime_ns, original.st_mtime_ns))
        expected = "other"
    control_logs._publish_native_logs(directory, (), cache=cache)
    assert (directory / "native_stdout.log").read_text() == expected


def test_native_log_cache_binds_current_redaction_policy(service):
    directory, raw = native_log_files(service)
    secret = "fixture-private-new-credential"
    (raw / "stdout.log").write_text("value " + secret)
    cache = {}
    control_logs._publish_native_logs(directory, (), cache=cache)
    assert secret in (directory / "native_stdout.log").read_text()
    control_logs._publish_native_logs(directory, (secret,), cache=cache)
    assert (directory / "native_stdout.log").read_text() == "value [REDACTED]"
    assert secret not in repr(cache)


def test_native_log_cache_tracks_preparation_diagnostic_lifecycle(service):
    directory, raw = native_log_files(service)
    (raw / "stderr.log").write_text("native stderr")
    diagnostic = directory / "preparation.stderr"
    cache = {}
    control_logs._publish_native_logs(directory, (), cache=cache)
    diagnostic.write_text("first diagnostic")
    diagnostic.chmod(0o600)
    control_logs._publish_native_logs(directory, (), cache=cache)
    assert (directory / "native_stderr.log").read_text() == "first diagnostic\nnative stderr"
    diagnostic.write_text("second diagnostic")
    control_logs._publish_native_logs(directory, (), cache=cache)
    assert (directory / "native_stderr.log").read_text() == "second diagnostic\nnative stderr"
    diagnostic.unlink()
    control_logs._publish_native_logs(directory, (), cache=cache)
    assert (directory / "native_stderr.log").read_text() == "native stderr"


@pytest.mark.parametrize("change", ["delete", "replace", "symlink", "hardlink", "permissions"])
def test_native_log_cache_revalidates_published_output(service, tmp_path, change):
    directory, raw = native_log_files(service)
    (raw / "stdout.log").write_text("expected output")
    published = directory / "native_stdout.log"
    unrelated = tmp_path / "unrelated"
    unrelated.write_text("unrelated must remain unchanged")
    cache = {}
    control_logs._publish_native_logs(directory, (), cache=cache)
    if change == "permissions":
        published.chmod(0o644)
    else:
        published.unlink()
        if change == "replace":
            published.write_text("tampered output")
        elif change == "symlink":
            published.symlink_to(unrelated)
        elif change == "hardlink":
            os.link(unrelated, published)
    control_logs._publish_native_logs(directory, (), cache=cache)
    assert published.read_text() == "expected output"
    assert not published.is_symlink()
    assert published.stat().st_mode & 0o077 == 0
    assert unrelated.read_text() == "unrelated must remain unchanged"


@pytest.mark.parametrize("change", ["symlink", "oversized"])
def test_native_log_cache_never_reads_an_invalid_replacement(service, tmp_path, change):
    directory, raw = native_log_files(service)
    source = raw / "stdout.log"
    source.write_text("original safe output")
    cache = {}
    control_logs._publish_native_logs(directory, (), cache=cache)
    source.unlink()
    if change == "symlink":
        unrelated = tmp_path / "private-unrelated"
        unrelated.write_text("never expose this content")
        source.symlink_to(unrelated)
    else:
        with source.open("wb") as stream:
            stream.truncate(control_logs.MAX_NATIVE_LOG + 1)
    control_logs._publish_native_logs(directory, (), cache=cache)
    assert (directory / "native_stdout.log").read_text() == "original safe output"
    assert (str(directory), "stdout") not in cache
    source.unlink()
    source.write_text("new safe output")
    control_logs._publish_native_logs(directory, (), cache=cache)
    assert (directory / "native_stdout.log").read_text() == "new safe output"


def test_native_log_cache_retries_a_source_changed_during_read(service, monkeypatch):
    directory, raw = native_log_files(service)
    source = raw / "stdout.log"
    source.write_text("old")
    read = control_logs._read_regular
    changed = False

    def read_then_append(path, *args, **kwargs):
        nonlocal changed
        value = read(path, *args, **kwargs)
        if path == source and not changed:
            source.write_text("new complete output")
            changed = True
        return value

    monkeypatch.setattr(control_logs, "_read_regular", read_then_append)
    cache = {}
    control_logs._publish_native_logs(directory, (), cache=cache)
    assert (directory / "native_stdout.log").read_text() == "old"
    assert (str(directory), "stdout") not in cache
    control_logs._publish_native_logs(directory, (), cache=cache)
    assert (directory / "native_stdout.log").read_text() == "new complete output"
