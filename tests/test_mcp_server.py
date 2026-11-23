"""MCP SDK v2 protocol tests; require pip install 'mcp>=2,<3'."""

import asyncio
from pathlib import Path

from mcp import Client

from src.mcp_server import create_server
from src.semantic_service import SemanticService


ROOT = Path(__file__).resolve().parents[1]


def test_mcp_lists_tools():
    async def run():
        async with Client(create_server(SemanticService.from_project(ROOT))) as client:
            tools = (await client.list_tools()).tools
            names = {tool.name for tool in tools}
            assert names == {
                "list_entity_types", "describe_entity", "get_entity",
                "find_related_entities", "purchases_for_product"
            }
            assert all(tool.output_schema is not None for tool in tools)
    asyncio.run(run())


def test_mcp_product_query():
    async def run():
        async with Client(create_server(SemanticService.from_project(ROOT))) as client:
            response = await client.call_tool("purchases_for_product", {"product_id": "P001"})
            assert not response.is_error
            assert isinstance(response.structured_content, dict), (
                f"Expected structured data, got: {response.content!r}"
            )
            assert response.structured_content["count"] == 3
            assert [row["order_id"] for row in response.structured_content["purchases"]] == [
                "O001", "O003", "O006"
            ]
    asyncio.run(run())


def test_mcp_rejects_unknown_entity():
    async def run():
        async with Client(create_server(SemanticService.from_project(ROOT))) as client:
            response = await client.call_tool(
                "get_entity", {"entity_type": "Customer", "entity_id": "C999"}
            )
            assert response.is_error
    asyncio.run(run())


def test_mcp_resource():
    async def run():
        async with Client(create_server(SemanticService.from_project(ROOT))) as client:
            resources = await client.list_resources()
            assert any(str(r.uri) == "ontology://schema" for r in resources.resources)
            contents = await client.read_resource("ontology://schema")
            assert '"commerce_core"' in contents.contents[0].text
    asyncio.run(run())
