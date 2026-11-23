from pathlib import Path

import pytest

from src.semantic_service import SemanticService


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def service():
    return SemanticService.from_project(ROOT)


def test_graph_size_and_types(service):
    result = service.list_entity_types()
    assert result["graph_nodes"] == 34
    assert result["graph_edges"] == 40
    assert result["entity_types"] == ["Customer", "Invoice", "Order", "Product"]


def test_entity_description(service):
    result = service.describe_entity("Customer")
    assert result["key"] == "customer_id"
    assert result["properties"]["name"]["required"] is True


def test_unknown_type_rejected(service):
    with pytest.raises(ValueError, match="Unknown entity type"):
        service.describe_entity("Employee")


def test_get_known_customer(service):
    customer = service.get_entity("Customer", "C001")
    assert customer["id"] == "C001"
    assert customer["type"] == "Customer"
    assert customer["properties"]["name"] == "Amina Khan"


def test_unknown_customer_rejected(service):
    with pytest.raises(KeyError, match="Unknown entity"):
        service.get_entity("Customer", "C999")


def test_related_orders(service):
    result = service.find_related_entities("Customer", "C001", "PLACES", "out")
    assert result["count"] >= 1
    assert all(row["entity"]["type"] == "Order" for row in result["results"])


def test_reverse_traversal(service):
    result = service.find_related_entities("Product", "P001", "CONTAINS", "in")
    assert {row["entity"]["id"] for row in result["results"]} == {"O001", "O003", "O006"}


def test_invalid_direction_rejected(service):
    with pytest.raises(ValueError, match="direction"):
        service.find_related_entities("Product", "P001", direction="sideways")


def test_unknown_relationship_rejected(service):
    with pytest.raises(ValueError, match="Unknown relationship"):
        service.find_related_entities("Product", "P001", relation="SELLS")


def test_product_purchase_results(service):
    result = service.purchases_for_product("P001")
    assert result["count"] == 3
    assert [row["order_id"] for row in result["purchases"]] == ["O001", "O003", "O006"]


def test_unknown_product_rejected(service):
    with pytest.raises(KeyError, match="Unknown entity"):
        service.purchases_for_product("P999")


def test_ontology_resource_is_defensive_copy(service):
    resource = service.ontology_resource()
    resource["entities"].clear()
    assert len(service.ontology.entities) == 4
