"""Produce local Omnigraph import files (does not require the CLI)."""

from pathlib import Path

from src.data_loader import load_business_dataset
from src.omnigraph_export import export_omnigraph
from src.schema import load_ontology

ROOT = Path(__file__).resolve().parent


def main():
    ontology = load_ontology(ROOT / "ontology" / "business.yaml")
    records, edges = load_business_dataset(ROOT / "sample_data", ontology)
    schema_file, data_file = export_omnigraph(
        ontology, records, edges, ROOT / "exports" / "omnigraph"
    )
    print("Schema:", schema_file)
    print("Load data:", data_file)
    print("JSONL rows:", len(records["Customer"]) + len(records["Product"]) + len(records["Order"]) + len(records["Invoice"]) + len(edges))
    print("Omnigraph export: CREATED (not yet verified by CLI)")


if __name__ == "__main__":
    main()
