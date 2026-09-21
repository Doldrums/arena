from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from arena.frameworks.drivers import dgm_gateway as gateway


@pytest.mark.parametrize("model", gateway.MODELS)
def test_exact_model_is_preserved_at_client_boundary(monkeypatch, model):
    monkeypatch.setenv("ARENA_DGM_MODEL", model)
    monkeypatch.setenv("OPENAI_API_KEY", "inert-test-key")
    monkeypatch.setenv("ARENA_DGM_GATEWAY_URL", "http://172.30.88.1:8789/v1")
    created = []
    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=lambda **kwargs: created.append(kwargs)))
    client, selected = gateway.create_client(model)
    assert selected == model and client is None
    assert created == [{"api_key": "inert-test-key", "base_url": "http://172.30.88.1:8789/v1"}]


@pytest.mark.parametrize("model", [None, "gpt-4o", "o3-mini-2025-01-31", "gpt-5.6-sol ", ""])
def test_unknown_models_are_never_aliased(monkeypatch, model):
    monkeypatch.delenv("ARENA_DGM_MODEL", raising=False)
    if model is not None:
        monkeypatch.setenv("ARENA_DGM_MODEL", model)
    with pytest.raises(ValueError, match="exact reviewed"):
        gateway.selected_model()


def test_mismatched_role_model_fails_before_client_creation(monkeypatch):
    monkeypatch.setenv("ARENA_DGM_MODEL", gateway.MODELS[0])
    monkeypatch.setitem(sys.modules, "openai", None)
    with pytest.raises(ValueError, match="differs"):
        gateway.create_client(gateway.MODELS[1])


def test_missing_credential_is_not_substituted(monkeypatch):
    monkeypatch.setenv("ARENA_DGM_MODEL", gateway.MODELS[0])
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="scoped gateway"):
        gateway.create_client(gateway.MODELS[0])


@pytest.mark.parametrize("endpoint", ["https://api.openai.com/v1", "http://8.8.8.8:80/v1",
    "http://127.0.0.1:8789/v1?api_key=secret", "http://secret@127.0.0.1:8789/v1",
    "http://127.0.0.1:8789/v1#secret", "http://127.0.0.1:8789/other", "http://127.0.0.1/v1",
    "http://127.0.0.1:99999/v1", "unix:/run/docker.sock"])
def test_gateway_rejects_unreviewed_endpoint_forms(monkeypatch, endpoint):
    monkeypatch.setenv("ARENA_DGM_GATEWAY_URL", endpoint)
    with pytest.raises(ValueError, match="operator-pinned"):
        gateway.gateway_url()


def test_overlay_rejects_changed_native_source(tmp_path):
    (tmp_path / "llm.py").write_text("changed")
    with pytest.raises(ValueError, match="hash mismatch"):
        gateway.provider_overlays(tmp_path)


def test_overlay_refuses_symlink_before_reading_target(tmp_path):
    (tmp_path / "llm.py").symlink_to(tmp_path / "absent")
    with pytest.raises(ValueError, match="regular pinned"):
        gateway.provider_overlays(tmp_path)


def test_gateway_default_is_loopback(monkeypatch):
    monkeypatch.delenv("ARENA_DGM_GATEWAY_URL", raising=False)
    assert gateway.gateway_url() == "http://127.0.0.1:8789/v1"
