"""Build the local business graph and demonstrate a grounded product query."""

from pathlib import Path

from src.business_queries import purchases_for_product
from src.data_loader import load_business_dataset
from src.graph_adapter import NetworkXGraphAdapter
from src.schema import load_ontology

ROOT = Path(__file__).resolve().parent


def main():
    ontology = load_ontology(ROOT / "ontology" / "business.yaml")
    records, edges = load_business_dataset(ROOT / "sample_data", ontology)
    graph = NetworkXGraphAdapter.from_records(ontology, records, edges)

    print("Ontology:", ontology.name)
    print("Graph nodes:", graph.node_count)
    print("Graph edges:", graph.edge_count)
    print("Product P001:", graph.get_entity("Product", "P001")["properties"]["name"])
    print("Purchases for P001:")
    for row in purchases_for_product(graph, "P001"):
        print(
            f"  {row['order_id']}: {row['customer_name']} "
            f"| {row['invoice_currency']} {row['invoice_amount']} "
            f"| {row['invoice_status']}"
        )
    print("Graph build: PASSED")


if __name__ == "__main__":
    main()
