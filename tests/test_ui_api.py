"""Integration checks for the optional browser UI and read-only HTTP API."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.ui_app import create_app

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def client():
    with TestClient(create_app()) as app_client:
        yield app_client


def test_dashboard_serves_html(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Knowledge graph" in response.text
    assert "text/html" in response.headers["content-type"]


def test_styles_and_local_javascript_are_served(client):
    css = client.get("/assets/styles.css")
    js = client.get("/assets/app.js")
    assert css.status_code == 200 and "graph-node" in css.text
    assert js.status_code == 200 and "selectNode" in js.text


def test_health_is_grounded(client):
    data = client.get("/api/health").json()
    assert data == {"status": "ok", "ontology": "commerce_core", "graph_nodes": 34, "graph_edges": 40}


def test_overview_counts_and_read_only(client):
    data = client.get("/api/overview").json()
    assert data["entity_counts"] == {"Customer": 6, "Invoice": 10, "Order": 10, "Product": 8}
    assert data["relationship_counts"] == {"CONTAINS": 20, "HAS_INVOICE": 10, "PLACES": 10}
    assert data["read_only"] is True
    assert len(data["mcp_tools"]) == 5


def test_complete_graph_contains_34_nodes_and_40_valid_edges(client):
    graph = client.get("/api/graph").json()
    assert graph["node_count"] == len(graph["nodes"]) == 34
    assert graph["edge_count"] == len(graph["edges"]) == 40
    keys = {node["id"] for node in graph["nodes"]}
    assert len(keys) == 34
    for edge in graph["edges"]:
        assert edge["source"] in keys
        assert edge["target"] in keys
        assert edge["relationship"] in {"PLACES", "CONTAINS", "HAS_INVOICE"}


def test_graph_snapshot_is_deterministic(client):
    assert client.get("/api/graph").json() == client.get("/api/graph").json()


def test_entity_directory_filters_by_type(client):
    data = client.get("/api/entities", params={"entity_type": "Customer"}).json()
    assert data["count"] == 6
    assert {n["entity_type"] for n in data["items"]} == {"Customer"}


def test_entity_directory_search_matches_properties(client):
    data = client.get("/api/entities", params={"q": "amina@example.org"}).json()
    assert data["count"] == 1
    assert data["items"][0]["entity_id"] == "C001"


def test_directory_invalid_entity_type(client):
    response = client.get("/api/entities", params={"entity_type": "Employee"})
    assert response.status_code == 400


def test_entity_inspection_includes_related_records(client):
    data = client.get("/api/entities/Customer/C001").json()
    assert data["entity"]["properties"]["name"] == "Amina Khan"
    related = data["related"]["results"]
    assert {r["entity"]["id"] for r in related if r["relationship"] == "PLACES"} == {"O001", "O004"}


def test_missing_entity_fails_closed(client):
    assert client.get("/api/entities/Customer/C999").status_code == 404
    assert client.get("/api/entities/Employee/E01").status_code == 400


def test_relationship_traversal(client):
    data = client.get("/api/entities/Product/P001/related", params={"relation": "CONTAINS", "direction": "in"}).json()
    assert data["count"] == 3
    assert {x["entity"]["id"] for x in data["results"]} == {"O001", "O003", "O006"}


def test_invalid_relation_or_direction_rejected(client):
    assert client.get("/api/entities/Customer/C001/related", params={"direction": "sideways"}).status_code == 400
    assert client.get("/api/entities/Customer/C001/related", params={"relation": "MAGIC"}).status_code == 400


def test_product_purchase_query_preserves_pending_status(client):
    data = client.get("/api/queries/product-purchases", params={"product_id": "P001"}).json()
    assert data["count"] == 3
    assert [r["order_id"] for r in data["purchases"]] == ["O001", "O003", "O006"]
    assert [r["invoice_status"] for r in data["purchases"]] == ["paid", "pending", "paid"]


def test_missing_product_returns_404(client):
    assert client.get("/api/queries/product-purchases", params={"product_id": "P999"}).status_code == 404


def test_schema_is_available(client):
    data = client.get("/api/ontology").json()
    assert set(data["entities"]) == {"Customer", "Product", "Order", "Invoice"}


def test_read_only_api_rejects_mutation(client):
    assert client.post("/api/graph", json={"nodes": []}).status_code == 405
    assert client.put("/api/entities/Customer/C001", json={"name": "changed"}).status_code == 405
    assert client.get("/api/entities/Customer/C001").json()["entity"]["properties"]["name"] == "Amina Khan"


def test_api_docs_are_available(client):
    assert client.get("/openapi.json").status_code == 200
    assert client.get("/docs").status_code == 200
