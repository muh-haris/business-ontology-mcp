"""Exercise the actual MCP stdio transport using a local Python subprocess."""

import asyncio
import json
import sys
from pathlib import Path

from mcp import Client, StdioServerParameters


ROOT = Path(__file__).resolve().parent


async def main() -> None:
    params = StdioServerParameters(
        command=sys.executable,
        args=[str(ROOT / "mcp_server.py")],
        cwd=str(ROOT),
    )
    async with Client(params) as client:
        listing = await client.list_tools()
        names = sorted(tool.name for tool in listing.tools)
        print("MCP tools:", names)

        expected = {
            "list_entity_types": {"graph_nodes": 34, "graph_edges": 40},
            "get_entity": {"id": "C001", "type": "Customer"},
            "purchases_for_product": {"product_id": "P001", "count": 3},
        }

        for name, arguments in [
            ("list_entity_types", {}),
            ("get_entity", {"entity_type": "Customer", "entity_id": "C001"}),
            ("purchases_for_product", {"product_id": "P001"}),
        ]:
            result = await client.call_tool(name, arguments)
            if result.is_error:
                raise RuntimeError(f"Tool {name} failed: {result.content}")
            data = result.structured_content
            if not isinstance(data, dict):
                raise RuntimeError(
                    f"{name} did not return structured data: {result.content!r}"
                )
            for key, value in expected[name].items():
                if data.get(key) != value:
                    raise AssertionError(f"{name}: expected {key}={value!r}, got {data.get(key)!r}")
            print(f"{name}: {json.dumps(data, ensure_ascii=False)}")

        resource = await client.read_resource("ontology://schema")
        assert resource.contents
        schema = json.loads(resource.contents[0].text)
        assert schema["name"] == "commerce_core"
        assert len(schema["entities"]) == 4
        print("Ontology resource: AVAILABLE")
        print("MCP stdio verification: PASSED")


if __name__ == "__main__":
    asyncio.run(main())
