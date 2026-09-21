"""Discovery caching and upstream inventory shape failures."""
import pytest

from arena.provider_service import ProviderBridge
from arena.providers import ProviderError


class InventoryTransport:
    def __init__(self, inventory):
        self.inventory = inventory
        self.calls = 0

    def models(self):
        self.calls += 1
        return self.inventory


@pytest.mark.parametrize("inventory,allowlist", [
    ({"models": []}, None),
    ({"models": [{"slug": "test-model", "supported_in_api": True}]}, []),
])
def test_empty_discovery_is_cached_until_ttl(monkeypatch, inventory, allowlist):
    clock = [0.0]
    monkeypatch.setattr("arena.provider_service.time.monotonic", lambda: clock[0])
    transport = InventoryTransport(inventory)
    bridge = ProviderBridge(transport, allowed_models=allowlist)
    assert bridge.models()["data"] == []
    clock[0] = 299.0
    assert bridge.models()["data"] == []
    assert transport.calls == 1
    clock[0] = 300.0
    assert bridge.models()["data"] == []
    assert transport.calls == 2


@pytest.mark.parametrize("item", [None, "bad entry", {
    "slug": "test-model", "supported_in_api": True, "supported_reasoning_levels": None,
}])
def test_malformed_inventory_is_not_cached(item):
    transport = InventoryTransport({"models": [item]})
    bridge = ProviderBridge(transport)
    with pytest.raises(ProviderError) as error:
        bridge.models()
    assert (error.value.status, error.value.code) == (502, "invalid_model_inventory")
    transport.inventory = {"models": []}
    assert bridge.models()["data"] == []
    assert transport.calls == 2
