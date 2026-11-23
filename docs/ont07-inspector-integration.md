# ONT-07 — Independent MCP Inspector Client Integration

## Objective

Verify the `business-ontology-mcp` server using the **official open-source MCP Inspector** (browser and CLI). Unlike the ONT-06 Python demo, this is an independent Node.js MCP client that starts the Python stdio server and checks the actual protocol results.

## Requirements

- ONT-06 running and its 76 tests passing
- Project-specific Python virtual environment active
- Node.js version supported by the installed MCP Inspector (consult current Inspector README)
- `node`, `npm`, and `npx` available on the PATH
- Windows 10 PowerShell (the guide also works on other OSes with `npx`)

## Setup

```powershell
node --version
npm --version
npx.cmd --version
python scripts/inspector_setup.py
Get-Content .mcp-local/inspector.json
```

The generator uses the active Python interpreter and project root. It writes `.mcp-local/inspector.json`, which contains absolute machine-local paths and must be excluded from Git. **Do not use a hard-coded path from another computer.**

## External-client CLI smoke test

```powershell
python scripts/inspector_smoke.py
```

The script launches the official Inspector CLI through `npx.cmd` on Windows, and checks three distinct protocol requests:

1. `tools/list`: all five tools must appear.
2. `tools/call` with `purchases_for_product` and `P001`: structured output must show three specific purchase records.
3. `resources/read` with `ontology://schema`: schema must identify `commerce_core` and four entity definitions.

A failure in any step exits with a nonzero status; the script cannot claim success just because a connection was established.

## Manual Inspector web demonstration

```powershell
npx.cmd -y @modelcontextprotocol/inspector --config .mcp-local/inspector.json
```

Open the locally displayed Inspector URL. Use **business-ontology** in the server selection and **Connect** if it is not already connected. Labels may differ between Inspector versions. Test these tool calls using their input arguments:

| MCP tool | Inputs | Verify |
| --- | --- | --- |
| `list_entity_types` | `{}` | 34 graph nodes, 40 graph edges |
| `describe_entity` | `{"entity_type":"Customer"}` | Customer fields and relationships |
| `get_entity` | `{"entity_type":"Customer","entity_id":"C001"}` | Amina Khan |
| `find_related_entities` | `{"entity_type":"Customer","entity_id":"C001","relation":"PLACES","direction":"out"}` | Customer order relationship |
| `purchases_for_product` | `{"product_id":"P001"}` | Three purchased-order records |

Read `ontology://schema` from **Resources**, and verify the four entity definitions. Make sure invalid lookup of customer `C999` produces an error, not a fictitious result. Capture screenshots of the actual connected Inspector and selected tool/resource responses for the instructor.

Inspector is a **developer testing client**, not an LLM-powered conversational agent. The ONT-07 deliverable demonstrates MCP interoperability. The next task can connect a separate AI client if required by the assignment.

## Verification and submission

```powershell
python -m pytest -v
python scripts/inspector_smoke.py
git status
```

Update README with ONT-07 instructions. Include the new Python scripts, tests and this guide in Git, but do not commit `.mcp-local/`, `.venv/` or runtime credentials.

## Troubleshooting

- `npx.cmd` not recognized: install a current supported Node.js release and open a new PowerShell terminal.
- PowerShell blocks `npx.ps1`: use `npx.cmd` (not `npx`) on Windows.
- Inspector says Python cannot be started: activate `.venv` and rerun the config generator, then check the configured executable path.
- Server unavailable or timeout: ensure `mcp_server.py` works with `python demo_mcp_client.py`, and do not print extra messages to stdout inside the stdio server.
- `structuredContent` is missing: use the fixed ONT-06 implementation with `@mcp.tool(structured_output=True)`.
- The Inspector UI cannot connect: try the CLI smoke test first and inspect its error diagnostics.

## References

- https://github.com/modelcontextprotocol/inspector
- https://github.com/modelcontextprotocol/inspector/blob/main/clients/cli/README.md
- https://github.com/modelcontextprotocol/inspector/blob/main/docs/mcp-server-configuration.md
