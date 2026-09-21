"""Metadata identities for bundled task libraries and legacy Git collections."""
from __future__ import annotations


BUNDLE_FIELDS = (
    "kind", "root_path", "repository_url", "revision", "manifest_path", "manifest_sha256",
)


def source_url(source, path):
    """Link to the reviewed code location; its content digest travels separately."""
    if source.get("kind") == "bundled":
        return f"{source['repository_url']}/blob/{source['revision']}/{source['root_path']}/{path}"
    return f"{source['repository']['url']}/blob/{source['repository']['commit']}/{path}"


def _validate_bundle(value):
    from .registry import _require, _relative, _hash, _SHA256, _url
    _require(value["kind"] == "bundled", "unsupported task source kind")
    _relative(value["root_path"], "root_path")
    _relative(value["manifest_path"], "manifest_path")
    _require(value["root_path"] == "tasks", "bundled tasks must use the tasks directory")
    _require(value["manifest_path"] == "registry/task-library-manifest.json",
             "bundled tasks require the reviewed integrity manifest")
    _hash(value["manifest_sha256"], _SHA256, "manifest_sha256")
    _url(value["repository_url"], "repository_url", github=True)
    _require(value["repository_url"] == "https://github.com/Doldrums/arena"
             and value["revision"] == "main", "bundled code links must identify Arena")


def validate_source(source):
    from .registry import _object, _identifier, _repository, _relative, _hash, _SHA256
    if type(source) is not dict:
        return _object(source, (), "source")
    common = ("id", "catalog_path", "catalog_sha256", "index_path", "index_sha256")
    _object(source, common + (BUNDLE_FIELDS if source.get("kind") == "bundled" else ("repository",)), "source")
    _identifier(source["id"], "source.id")
    if source.get("kind") == "bundled":
        _validate_bundle(source)
    else:
        _repository(source["repository"])
    for key in ("catalog_path", "index_path"):
        _relative(source[key], key)
    for key in ("catalog_sha256", "index_sha256"):
        _hash(source[key], _SHA256, key)
    return source


def validate_registration(value):
    from .registry import _object, _identifier, _require, _repository, _relative, _text
    if type(value) is not dict:
        return _object(value, (), "registration")
    common = ("schema", "id", "kind", "admission", "refresh", "snapshot_source_id")
    if value.get("schema") == "arena.registration/2":
        fields = tuple(field for field in BUNDLE_FIELDS if field != "kind")
        _object(value, common + fields + ("storage", "catalog_path"), "registration")
        _require(value["storage"] == "bundled", "registration must use bundled task storage")
        _validate_bundle({**value, "kind": value["storage"]})
        _relative(value["catalog_path"], "catalog_path")
        _require(value["refresh"] == "reviewed_local_snapshot", "bundled tasks require a reviewed local snapshot")
    else:
        _object(value, common + ("repository", "manifest_path", "tracked_ref", "access"), "registration")
        _require(value["schema"] == "arena.registration/1", "unsupported registration schema")
        _repository(value["repository"])
        _relative(value["manifest_path"], "manifest_path")
        _text(value["tracked_ref"], "tracked_ref")
        _require(value["access"] in ("github_app_private", "github_app_public"), "invalid repository access mode")
        _require(value["refresh"] == "manual_pinned_snapshot", "remote refresh/build is not implemented")
    _identifier(value["id"], "registration.id")
    _require(value["kind"] == "task_collection", "unsupported registration kind")
    _require(value["admission"] == "team_registry_pr", "registration requires team registry PR")
    _identifier(value["snapshot_source_id"], "snapshot_source_id")
    return value


def registration_source(registration):
    """Return the source identity before source-file digests have been captured."""
    if registration.get("storage") == "bundled":
        return {
            "id": registration["snapshot_source_id"], "kind": "bundled",
            **{name: registration[name] for name in BUNDLE_FIELDS if name != "kind"},
            "catalog_path": registration["catalog_path"], "index_path": "suite/index.json",
        }
    return {"id": registration["snapshot_source_id"], "repository": registration["repository"],
            "catalog_path": registration["manifest_path"], "index_path": "suite/index.json"}
