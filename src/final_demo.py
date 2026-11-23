"""Final read-only business ontology demonstration and verifiable summary.

The returned object is deterministic and uses only validated synthetic records.
It is not an LLM evaluation, Omnigraph CLI proof, or performance benchmark.
"""

from pathlib import Path

from src.quality_audit import audit_project
from src.semantic_service import SemanticService


def build_final_demo(project_root: str | Path) -> dict:
    """Run real graph lookups and return evidence suitable for JSON export."""
    root = Path(project_root)
    audit = audit_project(root)  # Fail closed if graph or golden references are wrong.
    service = SemanticService.from_project(root)

    overview = service.list_entity_types()
    customer = service.get_entity("Customer", "C001")
    outgoing = service.find_related_entities("Customer", "C001", "PLACES", "out")
    incoming = service.find_related_entities("Order", "O001", "PLACES", "in")
    product = service.get_entity("Product", "P001")
    purchases = service.purchases_for_product("P001")

    order_ids = sorted(item["entity"]["id"] for item in outgoing["results"])
    source_ids = sorted(item["entity"]["id"] for item in incoming["results"])
    if order_ids != ["O001", "O004"] or source_ids != ["C001"]:
        raise AssertionError("Bidirectional Customer C001 order traversal mismatch")

    if purchases["count"] != 3 or [p["order_id"] for p in purchases["purchases"]] != [
        "O001", "O003", "O006"
    ]:
        raise AssertionError("Product P001 purchase traversal mismatch")

    if any(p["invoice_currency"] != "USD" for p in purchases["purchases"]):
        raise AssertionError("Unexpected currency for reference product P001")

    expected_statuses = ["paid", "pending", "paid"]
    if [p["invoice_status"] for p in purchases["purchases"]] != expected_statuses:
        raise AssertionError("Invoice payment statuses no longer match the sample")

    try:
        service.get_entity("Customer", "C999")
    except (KeyError, ValueError):
        rejected = True
    else:
        rejected = False
    if not rejected:
        raise AssertionError("Unknown customer was not rejected")

    if audit["status"] != "passed":
        raise AssertionError("ONT-08 audit did not pass")

    return {
        "status": "passed",
        "ontology": overview["ontology"],
        "graph": {"nodes": overview["graph_nodes"], "edges": overview["graph_edges"]},
        "entity_types": overview["entity_types"],
        "relationship_types": overview["relationship_types"],
        "customer_demo": {
            "id": customer["id"],
            "name": customer["properties"]["name"],
            "orders": order_ids,
            "reverse_lookup_of_O001": source_ids,
        },
        "product_demo": {
            "id": product["id"],
            "name": product["properties"]["name"],
            "count": purchases["count"],
            "purchases": purchases["purchases"],
        },
        "unknown_customer_rejected": rejected,
        "audit": {
            "entity_lookups_checked": audit["entity_lookups_checked"],
            "bidirectional_edges_checked": audit["bidirectional_edges_checked"],
            "product_queries_checked": audit["product_queries_checked"],
            "invalid_queries_rejected": audit["invalid_queries_rejected"],
        },
        "verification_scope": (
            "Local synthetic CSV -> ontology validation -> NetworkX graph -> "
            "read-only semantic service. Independent MCP Inspector CLI was "
            "verified separately in ONT-07."
        ),
        "limitations": [
            "Omnigraph export has not been verified through a live native CLI import.",
            "MCP Inspector is a protocol client, not an autonomous LLM agent evaluation.",
            "Invoice amounts are whole-invoice totals, not product-specific revenue.",
            "This is a synthetic functional demo, not a performance or penetration test.",
        ],
    }
