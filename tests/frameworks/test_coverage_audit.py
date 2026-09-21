"""Coverage is an explicit identity join, never a guess from paper titles."""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("framework_coverage_audit", ROOT / "scripts/audit_framework_coverage.py")
coverage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(coverage)


def fixture_root(tmp_path):
    registry = tmp_path / "registry"
    (registry / "framework-recipes").mkdir(parents=True)
    adapters = tmp_path / "src/arena/frameworks"
    adapters.mkdir(parents=True)
    records = []
    for identity in ("sciel", "shinka", "dgm", "paper-only"):
        records.append({"id": identity, "name": identity, "papers": [], "repository": None})
        if identity != "paper-only":
            (adapters / (identity + ".py")).write_text("raise RuntimeError('must not import adapter')\n")
    (registry / "participants.json").write_text(json.dumps({"participants": records}))
    return registry


def test_inventory_accounts_all_real_records_without_counting_recipes_as_papers():
    report = coverage.audit()
    assert report["summary"]["participants"] == 99
    assert report["summary"]["paper_ids"] == 98
    assert not report["summary"]["participant_status_counts"].get("unaccounted")
    assert sum(report["summary"]["participant_status_counts"].values()) == 99
    assert len({p["id"] for p in report["participants"]}) == 99


def test_paper_without_interface_is_reported_as_unaccounted(tmp_path):
    fixture_root(tmp_path)
    report = coverage.audit(tmp_path)
    assert report["summary"]["participant_status_counts"] == {"native_interface": 3, "unaccounted": 1}


def test_unknown_recipe_identity_is_rejected_instead_of_fuzzy_matched(tmp_path):
    registry = fixture_root(tmp_path)
    recipe = {"id": "unknown", "name": "Unknown", "participant_ids": ["invented-paper"],
              "repository": None, "status": "blocked", "license": None, "setup": [],
              "blocked_reason": "No verified release", "evidence": {}, "profiles": []}
    (registry / "framework-recipes/test.json").write_text(json.dumps({"schema": "arena.framework-recipes/1", "recipes": [recipe]}))
    with pytest.raises(ValueError, match="Unknown recipe participant"):
        coverage.audit(tmp_path)


def test_changed_catalog_binding_changes_offline_report(tmp_path):
    registry = fixture_root(tmp_path)
    before = coverage.render(coverage.audit(tmp_path))
    path = registry / "participants.json"
    document = json.loads(path.read_text())
    document["participants"][-1]["name"] = "Updated research record"
    path.write_text(json.dumps(document))
    after = coverage.render(coverage.audit(tmp_path))
    assert before != after
