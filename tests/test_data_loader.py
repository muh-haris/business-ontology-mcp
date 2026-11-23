"""Integration tests: ONT-04 CSV fixtures + ONT-03 validator."""

import csv
import shutil
from pathlib import Path

import pytest

from src.data_loader import convert_value, load_business_dataset
from src.schema import load_ontology
from src.validator import RecordValidationError, validate_dataset

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "sample_data"
ONTOLOGY = ROOT / "ontology" / "business.yaml"


@pytest.fixture
def ontology():
    return load_ontology(ONTOLOGY)


@pytest.fixture
def copy_data(tmp_path):
    dest = tmp_path / "sample_data"
    shutil.copytree(DATA_DIR, dest)
    return dest


def rewrite_csv(folder, name, transform):
    path = folder / name
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames
        rows = list(reader)
    header, rows = transform(header, rows)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)


def test_synthetic_dataset_counts(ontology):
    records, edges = load_business_dataset(DATA_DIR, ontology)
    report = validate_dataset(ontology, records, edges)
    assert report.entity_counts == {
        "Customer": 6, "Product": 8, "Order": 10, "Invoice": 10
    }
    assert report.relationship_counts == {
        "PLACES": 10, "CONTAINS": 20, "HAS_INVOICE": 10
    }
    assert report.total_entities == 34
    assert report.total_relationships == 40


def test_prices_are_numeric(ontology):
    records, _ = load_business_dataset(DATA_DIR, ontology)
    assert isinstance(records["Product"][0]["unit_price"], float)
    assert records["Product"][0]["unit_price"] == 12.5
    assert isinstance(records["Invoice"][0]["amount"], float)


def test_loading_is_deterministic(ontology):
    first = load_business_dataset(DATA_DIR, ontology)
    second = load_business_dataset(DATA_DIR, ontology)
    assert first == second


def test_products_can_appear_in_multiple_orders(ontology):
    _, edges = load_business_dataset(DATA_DIR, ontology)
    orders = {e["source_id"] for e in edges
              if e["type"] == "CONTAINS" and e["target_id"] == "P001"}
    assert orders == {"O001", "O003", "O006"}


def test_blank_optional_field_is_omitted(copy_data, ontology):
    rewrite_csv(copy_data, "customers.csv", lambda h, rows: (
        h, [{**row, "email": ""} if i == 0 else row for i, row in enumerate(rows)]
    ))
    records, _ = load_business_dataset(copy_data, ontology)
    assert "email" not in records["Customer"][0]


def test_bad_price_rejected(copy_data, ontology):
    rewrite_csv(copy_data, "products.csv", lambda h, rows: (
        h, [{**row, "unit_price": "twelve"} if i == 0 else row for i, row in enumerate(rows)]
    ))
    with pytest.raises(RecordValidationError, match="invalid number"):
        load_business_dataset(copy_data, ontology)


def test_duplicate_customer_id_rejected(copy_data, ontology):
    rewrite_csv(copy_data, "customers.csv", lambda h, rows: (
        h, rows + [{**rows[0], "name": "Other"}]
    ))
    with pytest.raises(RecordValidationError, match="duplicate ID"):
        load_business_dataset(copy_data, ontology)


def test_unknown_order_reference_rejected(copy_data, ontology):
    rewrite_csv(copy_data, "relationships.csv", lambda h, rows: (
        h, [{**row, "source_id": "C999"} if i == 0 else row for i, row in enumerate(rows)]
    ))
    with pytest.raises(RecordValidationError, match="unknown source"):
        load_business_dataset(copy_data, ontology)


def test_invoice_cardinality_violation_rejected(copy_data, ontology):
    rewrite_csv(copy_data, "relationships.csv", lambda h, rows: (
        h, [{**row, "target_id": "I001"}
            if row["type"] == "HAS_INVOICE" and row["source_id"] == "O002"
            else row for row in rows]
    ))
    with pytest.raises(RecordValidationError, match="target cardinality"):
        load_business_dataset(copy_data, ontology)


def test_invalid_order_date_rejected(copy_data, ontology):
    rewrite_csv(copy_data, "orders.csv", lambda h, rows: (
        h, [{**row, "order_date": "2026-02-30"} if i == 0 else row for i, row in enumerate(rows)]
    ))
    with pytest.raises(RecordValidationError, match="must be date"):
        load_business_dataset(copy_data, ontology)


def test_missing_csv_rejected(copy_data, ontology):
    (copy_data / "products.csv").unlink()
    with pytest.raises(FileNotFoundError, match="products.csv"):
        load_business_dataset(copy_data, ontology)


def test_missing_required_column_rejected(copy_data, ontology):
    rewrite_csv(copy_data, "customers.csv", lambda h, rows: (
        [field for field in h if field != "name"],
        [{k: v for k, v in row.items() if k != "name"} for row in rows]
    ))
    with pytest.raises(RecordValidationError, match="missing columns"):
        load_business_dataset(copy_data, ontology)


def test_extra_column_rejected(copy_data, ontology):
    rewrite_csv(copy_data, "customers.csv", lambda h, rows: (
        h + ["secret"], [{**row, "secret": "bad"} for row in rows]
    ))
    with pytest.raises(RecordValidationError, match="unknown columns"):
        load_business_dataset(copy_data, ontology)


def test_boolean_and_integer_csv_conversion():
    assert convert_value("true", "boolean", "flag") is True
    assert convert_value("FALSE", "boolean", "flag") is False
    assert convert_value("12", "integer", "quantity") == 12
    with pytest.raises(RecordValidationError):
        convert_value("12.5", "integer", "quantity")


def test_missing_relationship_field_rejected(copy_data, ontology):
    rewrite_csv(copy_data, "relationships.csv", lambda h, rows: (
        [field for field in h if field != "target_id"],
        [{k: v for k, v in row.items() if k != "target_id"} for row in rows]
    ))
    with pytest.raises(RecordValidationError, match="missing columns"):
        load_business_dataset(copy_data, ontology)


def test_sample_invoice_amounts_match_listed_products(ontology):
    """Fixture consistency check only; not a generic accounting rule."""
    records, edges = load_business_dataset(DATA_DIR, ontology)
    prices = {p["product_id"]: p["unit_price"] for p in records["Product"]}
    amounts = {i["invoice_id"]: i["amount"] for i in records["Invoice"]}
    order_totals = {order["order_id"]: 0.0 for order in records["Order"]}
    invoices = {}

    for edge in edges:
        if edge["type"] == "CONTAINS":
            order_totals[edge["source_id"]] += prices[edge["target_id"]]
        elif edge["type"] == "HAS_INVOICE":
            invoices[edge["source_id"]] = edge["target_id"]

    for order_id, total in order_totals.items():
        assert total == pytest.approx(amounts[invoices[order_id]])
