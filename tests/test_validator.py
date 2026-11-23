from copy import deepcopy
from pathlib import Path

import pytest

from src.schema import load_ontology
from src.validator import RecordValidationError, validate_dataset

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def sample():
    ontology = load_ontology(ROOT / "ontology" / "business.yaml")
    records = {
        "Customer": [{"customer_id": "C1", "name": "Amina"}],
        "Product": [{"product_id": "P1", "name": "Notebook", "unit_price": 10.0, "currency": "USD"}],
        "Order": [{"order_id": "O1", "order_date": "2026-11-23", "status": "placed"}],
        "Invoice": [{"invoice_id": "I1", "amount": 10, "currency": "USD", "status": "paid"}],
    }
    edges = [
        {"type": "PLACES", "source_id": "C1", "target_id": "O1"},
        {"type": "CONTAINS", "source_id": "O1", "target_id": "P1"},
        {"type": "HAS_INVOICE", "source_id": "O1", "target_id": "I1"},
    ]
    return ontology, records, edges


def test_valid_dataset(sample):
    ontology, records, edges = sample
    before = deepcopy(records)
    report = validate_dataset(ontology, records, edges)
    assert report.total_entities == 4
    assert report.total_relationships == 3
    assert report.entity_counts["Order"] == 1
    assert report.relationship_counts["CONTAINS"] == 1
    assert records == before


def test_missing_required_field(sample):
    ontology, records, edges = sample
    del records["Customer"][0]["name"]
    with pytest.raises(RecordValidationError, match="missing required name"):
        validate_dataset(ontology, records, edges)


def test_unknown_property(sample):
    ontology, records, edges = sample
    records["Customer"][0]["region"] = "Lahore"
    with pytest.raises(RecordValidationError, match="unknown properties"):
        validate_dataset(ontology, records, edges)


def test_wrong_type(sample):
    ontology, records, edges = sample
    records["Product"][0]["unit_price"] = "10.0"
    with pytest.raises(RecordValidationError, match="unit_price must be number"):
        validate_dataset(ontology, records, edges)


def test_bool_is_not_number(sample):
    ontology, records, edges = sample
    records["Invoice"][0]["amount"] = True
    with pytest.raises(RecordValidationError, match="amount must be number"):
        validate_dataset(ontology, records, edges)


def test_nonfinite_number_rejected(sample):
    ontology, records, edges = sample
    records["Invoice"][0]["amount"] = float("nan")
    with pytest.raises(RecordValidationError, match="amount must be number"):
        validate_dataset(ontology, records, edges)


def test_invalid_date(sample):
    ontology, records, edges = sample
    records["Order"][0]["order_date"] = "2026-02-30"
    with pytest.raises(RecordValidationError, match="order_date must be date"):
        validate_dataset(ontology, records, edges)


def test_duplicate_id(sample):
    ontology, records, edges = sample
    records["Customer"].append({"customer_id": "C1", "name": "Other"})
    with pytest.raises(RecordValidationError, match="duplicate ID"):
        validate_dataset(ontology, records, edges)


def test_unknown_entity_type(sample):
    ontology, records, edges = sample
    records["Supplier"] = []
    with pytest.raises(RecordValidationError, match="Unknown entity type"):
        validate_dataset(ontology, records, edges)


def test_unknown_source_reference(sample):
    ontology, records, edges = sample
    edges[0]["source_id"] = "C999"
    with pytest.raises(RecordValidationError, match="unknown source"):
        validate_dataset(ontology, records, edges)


def test_unknown_target_reference(sample):
    ontology, records, edges = sample
    edges[2]["target_id"] = "I999"
    with pytest.raises(RecordValidationError, match="unknown target"):
        validate_dataset(ontology, records, edges)


def test_unknown_relationship_type(sample):
    ontology, records, edges = sample
    edges[0]["type"] = "OWNS"
    with pytest.raises(RecordValidationError, match="unknown relationship type"):
        validate_dataset(ontology, records, edges)


def test_duplicate_edge(sample):
    ontology, records, edges = sample
    edges.append(dict(edges[0]))
    with pytest.raises(RecordValidationError, match="duplicate relationship"):
        validate_dataset(ontology, records, edges)


def test_one_to_many_target_has_one_source(sample):
    ontology, records, edges = sample
    records["Customer"].append({"customer_id": "C2", "name": "Bilal"})
    edges.append({"type": "PLACES", "source_id": "C2", "target_id": "O1"})
    with pytest.raises(RecordValidationError, match="target cardinality"):
        validate_dataset(ontology, records, edges)


def test_one_to_one_source_cannot_have_two_targets(sample):
    ontology, records, edges = sample
    records["Invoice"].append({"invoice_id": "I2", "amount": 20, "currency": "USD", "status": "paid"})
    edges.append({"type": "HAS_INVOICE", "source_id": "O1", "target_id": "I2"})
    with pytest.raises(RecordValidationError, match="source cardinality"):
        validate_dataset(ontology, records, edges)


def test_one_to_one_target_cannot_have_two_sources(sample):
    ontology, records, edges = sample
    records["Order"].append({"order_id": "O2", "order_date": "2026-11-22", "status": "placed"})
    edges.append({"type": "HAS_INVOICE", "source_id": "O2", "target_id": "I1"})
    with pytest.raises(RecordValidationError, match="target cardinality"):
        validate_dataset(ontology, records, edges)


def test_many_to_many_allows_shared_product(sample):
    ontology, records, edges = sample
    records["Order"].append({"order_id": "O2", "order_date": "2026-11-22", "status": "placed"})
    edges.append({"type": "CONTAINS", "source_id": "O2", "target_id": "P1"})
    report = validate_dataset(ontology, records, edges)
    assert report.relationship_counts["CONTAINS"] == 2


def test_blank_key_rejected(sample):
    ontology, records, edges = sample
    records["Customer"][0]["customer_id"] = " "
    with pytest.raises(RecordValidationError, match="cannot be blank"):
        validate_dataset(ontology, records, edges)


def test_malformed_edges_rejected(sample):
    ontology, records, edges = sample
    edges[0]["source_type"] = "Customer"
    with pytest.raises(RecordValidationError, match="expected fields"):
        validate_dataset(ontology, records, edges)
