import argparse
from pathlib import Path
from src.schema import load_ontology
from src.validator import RecordValidationError, validate_dataset

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--invalid", action="store_true", help="Demonstrate a rejected reference")
    args = parser.parse_args()
    ontology = load_ontology(ROOT / "ontology" / "business.yaml")
    records = {
        "Customer": [{"customer_id": "C001", "name": "Amina"}],
        "Product": [{"product_id": "P001", "name": "Notebook", "unit_price": 12.5, "currency": "USD"}],
        "Order": [{"order_id": "O001", "order_date": "2026-11-23", "status": "placed"}],
        "Invoice": [{"invoice_id": "I001", "amount": 12.5, "currency": "USD", "status": "paid"}],
    }
    edges = [
        {"type": "PLACES", "source_id": "C001", "target_id": "O001"},
        {"type": "CONTAINS", "source_id": "O001", "target_id": "P001"},
        {"type": "HAS_INVOICE", "source_id": "O001", "target_id": "I001"},
    ]
    if args.invalid:
        edges[0]["source_id"] = "C999"
    try:
        report = validate_dataset(ontology, records, edges)
    except RecordValidationError as error:
        print(f"Validation rejected: {error}")
        raise SystemExit(1) from None
    print("Ontology:", ontology.name)
    print("Entity counts:", report.entity_counts)
    print("Relationship counts:", report.relationship_counts)
    print("Total entities:", report.total_entities)
    print("Total relationships:", report.total_relationships)
    print("Record validation: PASSED")

if __name__ == "__main__":
    main()
