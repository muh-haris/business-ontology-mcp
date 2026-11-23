"""Check export structure; a real CLI integration test is still needed."""

import json
from pathlib import Path

import pytest

from src.data_loader import load_business_dataset
from src.omnigraph_export import export_omnigraph, render_schema
from src.schema import load_ontology
from src.validator import RecordValidationError

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def example():
    ontology = load_ontology(ROOT / "ontology" / "business.yaml")
    records, edges = load_business_dataset(ROOT / "sample_data", ontology)
    return ontology, records, edges


def test_schema_contains_key_and_types(example):
    schema = render_schema(example[0])
    assert "node Customer {" in schema
    assert "customer_id: String @key" in schema
    assert "unit_price: F64" in schema
    assert "order_date: Date" in schema
    assert "edge PLACES: Customer -> Order" in schema
    assert "@unique(@dst)" in schema


def test_schema_mapping_for_source_cardinality(example):
    schema = render_schema(example[0])
    assert "edge HAS_INVOICE: Order -> Invoice @card(0..1)" in schema


def test_export_rows_and_content(tmp_path, example):
    schema_file, jsonl = export_omnigraph(*example, tmp_path)
    assert schema_file.exists()
    rows = [json.loads(line) for line in jsonl.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 74
    assert sum("type" in row for row in rows) == 34
    assert sum("edge" in row for row in rows) == 40
    assert {row["type"] for row in rows if "type" in row} == {
        "Customer", "Product", "Order", "Invoice"
    }
    assert any(row == {"edge": "PLACES", "from": "C001", "to": "O001"} for row in rows)


def test_export_rejects_bad_record(tmp_path, example):
    ontology, records, edges = example
    records["Customer"][0]["customer_id"] = ""
    with pytest.raises(RecordValidationError):
        export_omnigraph(ontology, records, edges, tmp_path)
