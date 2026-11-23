"""ONT-09 real end-to-end acceptance tests over synthetic business records."""

import json
from pathlib import Path

import pytest

from src.final_demo import build_final_demo
from final_demo import main

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def report():
    return build_final_demo(ROOT)


def test_final_demo_reports_verified_graph_counts(report):
    assert report["status"] == "passed"
    assert report["ontology"] == "commerce_core"
    assert report["graph"] == {"nodes": 34, "edges": 40}


def test_four_entity_types_are_present(report):
    assert set(report["entity_types"]) == {"Customer", "Product", "Order", "Invoice"}


def test_three_relationship_types_are_present(report):
    assert set(report["relationship_types"]) == {"PLACES", "CONTAINS", "HAS_INVOICE"}


def test_customer_bidirectional_traversal(report):
    customer = report["customer_demo"]
    assert customer["name"] == "Amina Khan"
    assert customer["orders"] == ["O001", "O004"]
    assert customer["reverse_lookup_of_O001"] == ["C001"]


def test_product_purchases_are_grounded(report):
    product = report["product_demo"]
    assert product["id"] == "P001"
    assert product["name"] == "Notebook"
    assert product["count"] == 3
    assert [(p["order_id"], p["customer_name"]) for p in product["purchases"]] == [
        ("O001", "Amina Khan"),
        ("O003", "Sara Malik"),
        ("O006", "Noor Fatima"),
    ]


def test_invoice_payment_states_preserved(report):
    statuses = [p["invoice_status"] for p in report["product_demo"]["purchases"]]
    assert statuses == ["paid", "pending", "paid"]


def test_invalid_query_fails_closed_and_audit_is_complete(report):
    assert report["unknown_customer_rejected"] is True
    assert report["audit"] == {
        "entity_lookups_checked": 34,
        "bidirectional_edges_checked": 40,
        "product_queries_checked": 8,
        "invalid_queries_rejected": 4,
    }


def test_report_is_deterministic_json_and_documents_limitations(report, tmp_path):
    assert build_final_demo(ROOT) == report
    path = tmp_path / "demo.json"
    target = main(["--output", str(path)])
    assert target == path
    assert json.loads(path.read_text(encoding="utf-8")) == report
    assert any("Omnigraph" in item for item in report["limitations"])
    assert any("MCP Inspector" in item for item in report["limitations"])
