"""Behavior checks for typed graph construction and traversal."""

from copy import deepcopy
from pathlib import Path

import pytest

from src.business_queries import purchases_for_product
from src.data_loader import load_business_dataset
from src.graph_adapter import NetworkXGraphAdapter
from src.schema import load_ontology
from src.validator import RecordValidationError

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def example():
    ontology = load_ontology(ROOT / "ontology" / "business.yaml")
    records, edges = load_business_dataset(ROOT / "sample_data", ontology)
    return ontology, records, edges


@pytest.fixture
def graph(example):
    return NetworkXGraphAdapter.from_records(*example)


def test_counts(graph):
    assert graph.node_count == 34
    assert graph.edge_count == 40


def test_lookup_entity(graph):
    product = graph.get_entity("Product", "P001")
    assert product["type"] == "Product"
    assert product["properties"]["name"] == "Notebook"


def test_unknown_entity_rejected(graph):
    with pytest.raises(KeyError, match="Unknown entity"):
        graph.get_entity("Customer", "C999")


def test_unknown_type_rejected(graph):
    with pytest.raises(ValueError, match="Unknown entity type"):
        graph.get_entity("Employee", "E001")


def test_outgoing_orders(graph):
    related = graph.related("Customer", "C001", "PLACES", "out")
    assert [r["entity"]["id"] for r in related] == ["O001", "O004"]


def test_incoming_customer(graph):
    related = graph.related("Order", "O001", "PLACES", "in")
    assert len(related) == 1
    assert related[0]["entity"]["id"] == "C001"


def test_multiple_edge_kinds(graph):
    rows = graph.related("Order", "O001", direction="both")
    assert {r["relationship"] for r in rows} == {"PLACES", "CONTAINS", "HAS_INVOICE"}


def test_unknown_relationship_and_direction_rejected(graph):
    with pytest.raises(ValueError, match="Unknown relationship type"):
        graph.related("Order", "O001", "IS_A")
    with pytest.raises(ValueError, match="direction"):
        graph.related("Order", "O001", direction="sideways")


def test_results_are_copies(graph):
    entity = graph.get_entity("Product", "P001")
    entity["properties"]["name"] = "Changed"
    assert graph.get_entity("Product", "P001")["properties"]["name"] == "Notebook"


def test_shared_product(graph):
    orders = graph.related("Product", "P001", "CONTAINS", "in")
    assert [r["entity"]["id"] for r in orders] == ["O001", "O003", "O006"]


def test_purchases_are_grounded(graph):
    purchases = purchases_for_product(graph, "P001")
    assert [p["order_id"] for p in purchases] == ["O001", "O003", "O006"]
    assert all(p["invoice_id"] and p["customer_id"] for p in purchases)
    assert purchases[0]["customer_name"] == "Amina Khan"


def test_nonexistent_product_rejected(graph):
    with pytest.raises(KeyError, match="Unknown entity"):
        purchases_for_product(graph, "P999")


def test_invalid_data_rejected_before_graph_build(example):
    ontology, records, edges = example
    invalid = deepcopy(edges)
    invalid[0]["source_id"] = "C999"
    with pytest.raises(RecordValidationError, match="unknown source"):
        NetworkXGraphAdapter.from_records(ontology, records, invalid)


def test_same_raw_id_in_different_types(example):
    ontology, _, _ = example
    records = {
        "Customer": [{"customer_id": "X1", "name": "Same ID"}],
        "Product": [{"product_id": "X1", "name": "Other type", "unit_price": 2.0, "currency": "USD"}],
    }
    graph = NetworkXGraphAdapter.from_records(ontology, records, [])
    assert graph.node_count == 2
    assert graph.get_entity("Customer", "X1")["type"] == "Customer"
    assert graph.get_entity("Product", "X1")["type"] == "Product"
