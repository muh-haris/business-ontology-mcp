"""Real CSV -> ontology -> validated graph -> semantic-service integration tests."""

from pathlib import Path
from shutil import copytree

import pytest

from src.data_loader import load_business_dataset
from src.schema import load_ontology
from src.semantic_service import SemanticService
from src.validator import RecordValidationError

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def service():
    return SemanticService.from_project(ROOT)


def test_end_to_end_counts(service):
    overview = service.list_entity_types()
    assert overview["graph_nodes"] == 34
    assert overview["graph_edges"] == 40


def test_all_four_business_concepts_discoverable(service):
    assert set(service.list_entity_types()["entity_types"]) == {
        "Customer", "Product", "Order", "Invoice"
    }
    for kind in ("Customer", "Product", "Order", "Invoice"):
        described = service.describe_entity(kind)
        assert described["key"] in described["properties"]


def test_customer_to_order_and_reverse_traversal(service):
    outgoing = service.find_related_entities("Customer", "C001", "PLACES", "out")
    orders = {r["entity"]["id"] for r in outgoing["results"]}
    assert orders == {"O001", "O004"}
    incoming = service.find_related_entities("Order", "O001", "PLACES", "in")
    assert [r["entity"]["id"] for r in incoming["results"]] == ["C001"]


def test_product_purchase_query_matches_golden_records(service):
    response = service.purchases_for_product("P001")
    assert response["count"] == 3
    assert [(r["order_id"], r["customer_id"], r["invoice_id"]) for r in response["purchases"]] == [
        ("O001", "C001", "I001"), ("O003", "C003", "I003"), ("O006", "C005", "I006")
    ]


def test_pending_invoice_not_mislabeled_paid(service):
    rows = service.purchases_for_product("P001")["purchases"]
    pending = next(row for row in rows if row["order_id"] == "O003")
    assert pending["invoice_status"] == "pending"
    assert pending["invoice_amount"] == 22.5


def test_result_isolation(service):
    item = service.get_entity("Customer", "C001")
    item["properties"]["name"] = "TAMPERED"
    assert service.get_entity("Customer", "C001")["properties"]["name"] == "Amina Khan"


def test_unknown_customer_fails_closed(service):
    with pytest.raises((KeyError, ValueError)):
        service.get_entity("Customer", "C999")


def test_unknown_product_fails_closed(service):
    with pytest.raises((KeyError, ValueError)):
        service.purchases_for_product("P999")


def test_unsupported_relation_fails_closed(service):
    with pytest.raises(ValueError, match="Unknown relationship"):
        service.find_related_entities("Customer", "C001", "OWNS")


def test_invalid_direction_fails_closed(service):
    with pytest.raises(ValueError, match="direction"):
        service.find_related_entities("Customer", "C001", "PLACES", "sideways")


def test_tampered_csv_reference_prevents_graph_build(tmp_path):
    data_dir = tmp_path / "sample_data"
    copytree(ROOT / "sample_data", data_dir)
    file = data_dir / "relationships.csv"
    contents = file.read_text(encoding="utf-8")
    assert "PLACES,C001,O001" in contents
    file.write_text(contents.replace("PLACES,C001,O001", "PLACES,C999,O001"), encoding="utf-8")
    ontology = load_ontology(ROOT / "ontology" / "business.yaml")
    with pytest.raises(RecordValidationError, match="unknown source"):
        load_business_dataset(data_dir, ontology)
