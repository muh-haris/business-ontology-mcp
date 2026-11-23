"""MCP 2.x adapter: five read-only tools plus one ontology resource."""

import json
from pathlib import Path
from typing import Any

from mcp.server import MCPServer

from src.semantic_service import SemanticService


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def create_server(service: SemanticService) -> MCPServer:
    mcp = MCPServer(
        "business-ontology",
        version="0.6.0",
        instructions=(
            "Use these read-only tools for synthetic commerce data. "
            "Do not invent missing entities or interpret paid invoice amounts as recognized revenue."
        ),
    )

    @mcp.tool(structured_output=True)
    def list_entity_types() -> dict[str, Any]:
        """List available business concepts, relationships and graph size."""
        return service.list_entity_types()

    @mcp.tool(structured_output=True)
    def describe_entity(entity_type: str) -> dict[str, Any]:
        """Describe a business entity's key, properties and relationship types."""
        return service.describe_entity(entity_type)

    @mcp.tool(structured_output=True)
    def get_entity(entity_type: str, entity_id: str) -> dict[str, Any]:
        """Retrieve one existing business entity by its declared type and identifier."""
        return service.get_entity(entity_type, entity_id)

    @mcp.tool(structured_output=True)
    def find_related_entities(
        entity_type: str,
        entity_id: str,
        relation: str | None = None,
        direction: str = "out",
    ) -> dict[str, Any]:
        """Traverse valid typed graph edges; direction is in, out or both."""
        return service.find_related_entities(entity_type, entity_id, relation, direction)

    @mcp.tool(structured_output=True)
    def purchases_for_product(product_id: str) -> dict[str, Any]:
        """Find recorded customers, orders and invoice details for a product."""
        return service.purchases_for_product(product_id)

    @mcp.resource("ontology://schema")
    def ontology_schema() -> str:
        """Validated business ontology schema as JSON."""
        return json.dumps(service.ontology_resource(), sort_keys=True)

    return mcp


def main() -> None:
    # Do not print anything to stdout: it is reserved for MCP stdio messages.
    service = SemanticService.from_project(PROJECT_ROOT)
    create_server(service).run(transport="stdio")


if __name__ == "__main__":
    main()
