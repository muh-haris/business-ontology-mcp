"""Contract tests for reproducible audit reports and failure detection."""

import json
from pathlib import Path
from shutil import copytree

import pytest

from src.quality_audit import AuditError, audit_project, require

ROOT = Path(__file__).resolve().parents[1]


def test_audit_passes_for_reference_dataset():
    report = audit_project(ROOT)
    assert report["status"] == "passed"
    assert (report["node_count"], report["edge_count"]) == (34, 40)


def test_every_entity_edge_and_product_is_audited():
    report = audit_project(ROOT)
    assert report["entity_lookups_checked"] == 34
    assert report["bidirectional_edges_checked"] == 40
    assert report["product_queries_checked"] == 8
    assert report["invalid_queries_rejected"] == 4


def test_audit_report_is_deterministic_and_json_safe():
    first = json.dumps(audit_project(ROOT), sort_keys=True)
    second = json.dumps(audit_project(ROOT), sort_keys=True)
    assert first == second


def test_audit_includes_limitations_and_not_recognized_revenue():
    report = audit_project(ROOT)
    assert "limitations" in report
    assert any("whole invoice" in text for text in report["limitations"])
    assert "recognized_revenue" not in report


def test_require_raises_on_failed_invariant():
    with pytest.raises(AuditError, match="forced failure"):
        require(False, "forced failure")
