"""Local, read-only web dashboard for the validated commerce knowledge graph.

Reuses the existing SemanticService / NetworkX graph; does not change MCP.
Run from repository root with ``python ui_server.py``.
"""

from collections import Counter
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.semantic_service import SemanticService

ROOT = Path(__file__).resolve().parents[1]
UI_DIR = ROOT / "frontend"


def _node_key(entity_type: str, entity_id: str) -> str:
    return f"{entity_type}:{entity_id}"


def build_graph_payload(service: SemanticService) -> dict:
    """Serialize actual validated NetworkX nodes and edges, stably ordered."""
    graph = service.graph.graph
    nodes = []
    for (entity_type, entity_id), attrs in graph.nodes(data=True):
        props = dict(attrs["properties"])
        title = props.get("name") or props.get("status") or str(entity_id)
        nodes.append({
            "id": _node_key(entity_type, str(entity_id)),
            "entity_type": entity_type,
            "entity_id": str(entity_id),
            "label": str(title),
            "properties": props,
        })
    nodes.sort(key=lambda n: (n["entity_type"], n["entity_id"]))

    edges = []
    for source, target, rel in graph.edges(keys=True):
        source_id = _node_key(str(source[0]), str(source[1]))
        target_id = _node_key(str(target[0]), str(target[1]))
        edges.append({
            "id": f"{source_id}/{rel}/{target_id}",
            "source": source_id,
            "target": target_id,
            "relationship": str(rel),
        })
    edges.sort(key=lambda e: (e["relationship"], e["source"], e["target"]))
    return {"nodes": nodes, "edges": edges, "node_count": len(nodes), "edge_count": len(edges)}


def build_overview(service: SemanticService, graph_payload: dict) -> dict:
    overview = service.list_entity_types()
    entity_counts = Counter(n["entity_type"] for n in graph_payload["nodes"])
    relationship_counts = Counter(e["relationship"] for e in graph_payload["edges"])
    invoice_status_counts = Counter(
        str(n["properties"].get("status", "unknown"))
        for n in graph_payload["nodes"] if n["entity_type"] == "Invoice"
    )
    product_purchase_counts = []
    for n in graph_payload["nodes"]:
        if n["entity_type"] == "Product":
            product_purchase_counts.append({
                "id": n["entity_id"],
                "name": n["label"],
                "orders": sum(e["target"] == n["id"] and e["relationship"] == "CONTAINS"
                              for e in graph_payload["edges"]),
            })
    product_purchase_counts.sort(key=lambda p: (-p["orders"], p["id"]))
    return {
        **overview,
        "entity_counts": dict(sorted(entity_counts.items())),
        "relationship_counts": dict(sorted(relationship_counts.items())),
        "invoice_status_counts": dict(sorted(invoice_status_counts.items())),
        "product_purchase_counts": product_purchase_counts,
        "mcp_tools": ["list_entity_types", "describe_entity", "get_entity",
                      "find_related_entities", "purchases_for_product"],
        "dataset": "synthetic",
        "backend": "NetworkX",
        "read_only": True,
    }


def create_app(service: SemanticService | None = None) -> FastAPI:
    """Application factory for both local use and isolation in unit tests."""
    service = service if service is not None else SemanticService.from_project(ROOT)
    snapshot = build_graph_payload(service)
    overview = build_overview(service, snapshot)

    app = FastAPI(
        title="Business Ontology Studio",
        description="Read-only visual interface over the existing commerce_core semantic graph.",
        version="1.0.0",
    )
    app.state.semantic_service = service

    @app.get("/api/health")
    def health():
        return {"status": "ok", "ontology": overview["ontology"],
                "graph_nodes": snapshot["node_count"], "graph_edges": snapshot["edge_count"]}

    @app.get("/api/overview")
    def overview_endpoint():
        return overview

    @app.get("/api/graph")
    def graph_endpoint():
        return snapshot

    @app.get("/api/ontology")
    def ontology_endpoint():
        return service.ontology_resource()

    @app.get("/api/entities")
    def list_entities(
        entity_type: str | None = Query(None, max_length=80),
        q: str = Query("", max_length=120),
        limit: int = Query(200, ge=1, le=1000),
    ):
        if entity_type and entity_type not in service.ontology.entities:
            raise HTTPException(status_code=400, detail=f"Unknown entity type: {entity_type}")
        term = q.strip().casefold()
        nodes = [n for n in snapshot["nodes"]
                 if not entity_type or n["entity_type"] == entity_type]
        if term:
            nodes = [n for n in nodes if term in (" ".join([
                n["entity_type"], n["entity_id"], n["label"],
                *(str(v) for v in n["properties"].values()),
            ])).casefold()]
        return {"count": len(nodes), "items": nodes[:limit]}

    def entity_details(entity_type: str, entity_id: str):
        try:
            entity = service.get_entity(entity_type, entity_id)
            neighbors = service.find_related_entities(entity_type, entity_id, direction="both")
        except KeyError:
            raise HTTPException(status_code=404, detail="Entity not found") from None
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from None
        return {"entity": entity, "related": neighbors}

    @app.get("/api/entities/{entity_type}/{entity_id}/related")
    def related_endpoint(
        entity_type: str, entity_id: str,
        relation: str | None = Query(None, max_length=80),
        direction: str = Query("both", max_length=8),
    ):
        try:
            return service.find_related_entities(entity_type, entity_id, relation, direction)
        except KeyError:
            raise HTTPException(status_code=404, detail="Entity not found") from None
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from None

    @app.get("/api/entities/{entity_type}/{entity_id}")
    def entity_endpoint(entity_type: str, entity_id: str):
        return entity_details(entity_type, entity_id)

    @app.get("/api/queries/product-purchases")
    def product_purchases(product_id: str = Query(..., min_length=1, max_length=80)):
        try:
            return service.purchases_for_product(product_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="Product not found") from None
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from None

    @app.get("/", include_in_schema=False)
    def dashboard():
        return FileResponse(UI_DIR / "index.html", media_type="text/html")

    app.mount("/assets", StaticFiles(directory=UI_DIR), name="assets")
    return app


app = create_app()
