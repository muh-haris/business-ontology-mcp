"""Check and summarize the synthetic commerce CSV dataset."""

from pathlib import Path

from src.data_loader import load_business_dataset
from src.schema import load_ontology
from src.validator import RecordValidationError, validate_dataset

ROOT = Path(__file__).resolve().parent


def main():
    ontology = load_ontology(ROOT / "ontology" / "business.yaml")
    records, edges = load_business_dataset(ROOT / "sample_data", ontology)
    report = validate_dataset(ontology, records, edges)

    print(f"Ontology: {ontology.name}")
    print("Entities:", report.entity_counts)
    print("Relationships:", report.relationship_counts)
    print("Total entities:", report.total_entities)
    print("Total relationships:", report.total_relationships)
    print("Business dataset validation: PASSED")


if __name__ == "__main__":
    try:
        main()
    except (RecordValidationError, FileNotFoundError, ValueError) as exc:
        print("Business dataset validation: FAILED")
        print(exc)
        raise SystemExit(1) from None
