"""Example domain query expressed as typed graph traversals."""

from src.graph_adapter import GraphReader


def purchases_for_product(graph: GraphReader, product_id: str) -> list[dict]:
    """List purchases of a product; preserve missing invoice/customer information."""
    graph.get_entity("Product", product_id)  # Explicitly reject unknown products.
    orders = graph.related("Product", product_id, "CONTAINS", "in")
    results = []

    for order_entry in orders:
        order = order_entry["entity"]
        order_id = order["id"]
        customers = graph.related("Order", order_id, "PLACES", "in")
        invoices = graph.related("Order", order_id, "HAS_INVOICE", "out")

        # Cardinality is checked before graph construction.
        customer = customers[0]["entity"] if customers else None
        invoice = invoices[0]["entity"] if invoices else None

        results.append({
            "product_id": product_id,
            "order_id": order_id,
            "customer_id": customer["id"] if customer else None,
            "customer_name": customer["properties"].get("name") if customer else None,
            "invoice_id": invoice["id"] if invoice else None,
            "invoice_amount": invoice["properties"].get("amount") if invoice else None,
            "invoice_currency": invoice["properties"].get("currency") if invoice else None,
            "invoice_status": invoice["properties"].get("status") if invoice else None,
        })

    return sorted(results, key=lambda row: str(row["order_id"]))
