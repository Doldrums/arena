"""Environment-only gateway setup, followed by the unchanged native CLI.

This module contains no optimizer or evaluator implementation. CoEvo's native
embedding model is prepared offline and checked against an operator manifest.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import runpy
import sys
from types import SimpleNamespace

from arena.frameworks.drivers._tls import configure_ca

GPT2_REVISION = "607a30d783dfa663caf39e06633721c8d4cfcd7e"


def discard_tracking_metadata(body: bytes) -> bytes:
    """Remove only the native SDK's unused user tracking field, never its value."""
    data = json.loads(body)
    if not isinstance(data, dict):
        raise ValueError("Native provider request must be a JSON object")
    if "user" in data:
        if not isinstance(data["user"], str) or len(data["user"]) > 256:
            raise ValueError("Native user metadata must be a string of at most 256 characters")
        del data["user"]
    return json.dumps(data, separators=(",", ":")).encode()


def configure_codeevolve_transport():
    """Extend only the native provider's HTTP client; native generate is untouched.

    Linux Python 3.13 uses fork, so island workers inherit this client binding.
    Reject other start methods rather than silently losing the compatibility fix.
    """
    import multiprocessing
    import httpx
    import codeevolve.lm.openai as provider
    if multiprocessing.get_start_method() != "fork":
        raise ValueError("This CodeEvolve gateway profile requires the reviewed Linux fork process backend")

    class MetadataTransport(httpx.AsyncBaseTransport):
        def __init__(self, verify):
            self.transport = httpx.AsyncHTTPTransport(verify=verify)

        async def handle_async_request(self, request):
            body = discard_tracking_metadata(await request.aread())
            headers = [(k, v) for k, v in request.headers.raw if k.lower() != b"content-length"]
            forwarded = httpx.Request(request.method, request.url, headers=headers, content=body,
                                      extensions=request.extensions)
            return await self.transport.handle_async_request(forwarded)

        async def aclose(self):
            await self.transport.aclose()

    def native_client(*, verify):
        return httpx.AsyncClient(transport=MetadataTransport(verify))

    provider.httpx = SimpleNamespace(AsyncClient=native_client)


def verify_embedding_cache(cache: Path, manifest: Path) -> dict:
    if not cache.is_absolute() or not cache.is_dir() or cache.is_symlink():
        raise ValueError("Prepared HF cache must be an absolute existing directory")
    if manifest.is_symlink() or not manifest.is_file() or manifest.stat().st_size > 65536:
        raise ValueError("Missing or invalid embedding-cache manifest")
    data = json.loads(manifest.read_text())
    if (data.get("schema") != "arena.model-cache/1" or data.get("model") != "openai-community/gpt2"
            or data.get("revision") != GPT2_REVISION or not isinstance(data.get("files"), dict)):
        raise ValueError("Embedding-cache manifest does not identify the reviewed GPT-2 revision")
    required = {"config.json", "generation_config.json", "tokenizer_config.json", "tokenizer.json",
                "vocab.json", "merges.txt", "model.safetensors"}
    if not required <= data["files"].keys() or len(data["files"]) > 12:
        raise ValueError("Incomplete embedding-cache manifest")
    root = cache.resolve()
    repo = root / "hub/models--openai-community--gpt2"
    ref = repo / "refs/main"
    if not ref.resolve().is_relative_to(root) or ref.read_text().strip() != GPT2_REVISION:
        raise ValueError("Offline HF main reference does not match the pinned revision")
    snapshot = repo / "snapshots" / GPT2_REVISION
    for name, digest in data["files"].items():
        if (not isinstance(name, str) or Path(name).name != name or name in {".", ".."}
                or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest)):
            raise ValueError("Invalid embedding-cache file record")
        path = snapshot / name
        resolved = path.resolve()
        if not resolved.is_relative_to(root) or not resolved.is_file() or resolved.stat().st_size > 600_000_000:
            raise ValueError("Embedding-cache file is missing or outside the prepared cache")
        hasher = hashlib.sha256()
        with resolved.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                hasher.update(chunk)
        if hasher.hexdigest() != digest:
            raise ValueError("Embedding-cache file hash mismatch: " + name)
    return data


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--engine", choices=("codeevolve", "coevo"), required=True)
    parser.add_argument("--model")
    parser.add_argument("--tls-ca", type=Path)
    parser.add_argument("--hf-cache", type=Path)
    parser.add_argument("--hf-manifest", type=Path)
    args, native_args = parser.parse_known_args(argv)
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise ValueError("OPENAI_API_KEY must contain the scoped local gateway credential")
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        os.environ[name] = "1"
    os.environ["API_KEY"] = key
    if args.engine == "codeevolve":
        if any((args.model, args.tls_ca, args.hf_cache, args.hf_manifest)):
            parser.error("CodeEvolve selects its model through native YAML")
        os.environ["API_BASE"] = "http://127.0.0.1:8789/v1"
        configure_codeevolve_transport()
        Path("arena-provider-seam.json").write_text(json.dumps({
            "schema": "arena.native-provider-seam/1", "framework": "codeevolve",
            "native_loop_modified": False, "discarded_metadata": ["user"],
            "endpoint": "http://127.0.0.1:8789/v1", "canonical_evaluation": False,
        }, indent=2) + "\n")
        sys.argv = ["codeevolve", *native_args]
        runpy.run_module("codeevolve.cli", run_name="__main__")
    else:
        if not args.model or not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,79}", args.model):
            parser.error("CoEvo requires an exact gateway model alias")
        if args.tls_ca is None or args.hf_cache is None or args.hf_manifest is None:
            parser.error("CoEvo requires its public TLS CA and prepared embedding cache")
        if Path("model_config.json").exists() or Path("model_config.json").is_symlink():
            raise ValueError("The native credential template must be removed from the isolated workspace")
        configure_ca(args.tls_ca)
        verify_embedding_cache(args.hf_cache, args.hf_manifest)
        os.environ.update(API_URL="https://127.0.0.1:8790/v1/chat/completions", MODEL=args.model,
                          API_TIMEOUT="120", HF_HOME=str(args.hf_cache), HF_HUB_OFFLINE="1",
                          TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1", CUDA_VISIBLE_DEVICES="")
        entrypoint = Path.cwd() / "main_run.py"
        sys.argv = [str(entrypoint), *native_args]
        runpy.run_path(str(entrypoint), run_name="__main__")


if __name__ == "__main__":
    main()
