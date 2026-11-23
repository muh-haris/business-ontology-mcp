"""Deterministic, fail-closed audit of the synthetic ontology graph.

This checks an actual on-disk dataset against its schema and the graph API.
It does not claim to benchmark production throughput or the Omnigraph CLI.
"""

from pathlib import Path

from src.data_loader import load_business_dataset
from src.semantic_service import SemanticService
from src.schema import load_ontology


class AuditError(ValueError):
    """The synthetic dataset or semantic graph failed an expected invariant."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AuditError(message)


def audit_project(project_root: str | Path) -> dict:
    root = Path(project_root)
    ontology = load_ontology(root / "ontology" / "business.yaml")
    records, relationships = load_business_dataset(root / "sample_data", ontology)
    service = SemanticService.from_project(root)
    overview = service.list_entity_types()

    entity_counts = {kind: len(rows) for kind, rows in records.items()}
    relation_counts = {kind: sum(e["type"] == kind for e in relationships)
                       for kind in ontology.relationships}
    require(overview["graph_nodes"] == sum(entity_counts.values()), "Node count mismatch")
    require(overview["graph_edges"] == len(relationships), "Edge count mismatch")
    require(set(overview["entity_types"]) == set(ontology.entities), "Ontology entity types mismatch")
    require(set(overview["relationship_types"]) == set(ontology.relationships), "Ontology relationships mismatch")

    # Check that every source record survived graph construction unchanged.
    for kind, rows in records.items():
        id_key = ontology.entities[kind].key
        for row in rows:
            found = service.get_entity(kind, row[id_key])
            require(found["properties"] == row, f"Entity data mismatch: {kind}:{row[id_key]}")

    # Verify every declared edge in both traversal directions.
    for edge in relationships:
        kind = edge["type"]
        source_type = ontology.relationships[kind].source
        target_type = ontology.relationships[kind].target
        source_id, target_id = edge["source_id"], edge["target_id"]
        outbound = service.find_related_entities(source_type, source_id, kind, "out")["results"]
        inbound = service.find_related_entities(target_type, target_id, kind, "in")["results"]
        require(any(r["entity"]["type"] == target_type and r["entity"]["id"] == target_id
                    for r in outbound), f"Outgoing edge missing: {kind}:{source_id}->{target_id}")
        require(any(r["entity"]["type"] == source_type and r["entity"]["id"] == source_id
                    for r in inbound), f"Incoming edge missing: {kind}:{source_id}->{target_id}")

    # Independently compare every product's returned order IDs with CSV edges.
    for product in records["Product"]:
        product_id = product["product_id"]
        expected_orders = sorted(e["source_id"] for e in relationships
                                 if e["type"] == "CONTAINS" and e["target_id"] == product_id)
        answer = service.purchases_for_product(product_id)
        returned_orders = sorted(p["order_id"] for p in answer["purchases"])
        require(answer["count"] == len(expected_orders), f"Incorrect purchase count: {product_id}")
        require(returned_orders == expected_orders, f"Incorrect purchase orders: {product_id}")

    # Versioned golden case for this specific synthetic dataset, not a general commerce invariant.
    golden = service.purchases_for_product("P001")
    golden_rows = golden["purchases"]
    require([(p["order_id"], p["customer_name"], p["invoice_status"])
             for p in golden_rows] == [
                ("O001", "Amina Khan", "paid"),
                ("O003", "Sara Malik", "pending"),
                ("O006", "Noor Fatima", "paid"),
             ], "Golden P001 purchase data has changed")
    require([p["invoice_amount"] for p in golden_rows] == [20.5, 22.5, 47.5],
            "Golden invoice totals have changed")

    # Negative queries must raise errors; returning fabricated/default records is a failure.
    invalid_cases = [
        ("unknown customer", lambda: service.get_entity("Customer", "C999")),
        ("unknown product", lambda: service.purchases_for_product("P999")),
        ("unknown relationship", lambda: service.find_related_entities(
            "Customer", "C001", "DOES_NOT_EXIST")),
        ("invalid direction", lambda: service.find_related_entities(
            "Customer", "C001", "PLACES", "sideways")),
    ]
    for label, operation in invalid_cases:
        try:
            operation()
        except (KeyError, ValueError):
            continue
        raise AuditError(f"Invalid query was accepted: {label}")

    # Check response isolation: mutable outputs must not modify the graph.
    first = service.get_entity("Customer", "C001")
    first["properties"]["name"] = "CHANGED BY CLIENT"
    require(service.get_entity("Customer", "C001")["properties"]["name"] == "Amina Khan",
            "Returned entity objects leak mutable graph state")

    return {
        "status": "passed",
        "ontology": ontology.name,
        "node_count": overview["graph_nodes"],
        "edge_count": overview["graph_edges"],
        "entity_counts": entity_counts,
        "relationship_counts": relation_counts,
        "entity_lookups_checked": sum(entity_counts.values()),
        "bidirectional_edges_checked": len(relationships),
        "product_queries_checked": len(records["Product"]),
        "invalid_queries_rejected": len(invalid_cases),
        "golden_product": {"product_id": "P001", "order_ids": [p["order_id"] for p in golden_rows]},
        "scope": "Synthetic CSV -> validated NetworkX graph -> read-only semantic service",
        "limitations": [
            "MCP Inspector interoperability is verified separately in ONT-07.",
            "Omnigraph native import remains unverified unless separately run.",
            "Invoice amount is the whole invoice, not the contribution of a particular product.",
            "No production load, latency or security penetration benchmark is performed.",
        ],
    }
