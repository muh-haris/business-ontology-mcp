# ONT-09 — Final Technical Report

## Objective

Develop an open-source business ontology and semantic layer that allows MCP clients to discover business concepts and query a validated knowledge graph. The reference projects were ModernRelay Omnigraph and NVIDIA Auto Ontology.

## Implemented architecture

1. YAML ontology with `Customer`, `Product`, `Order`, and `Invoice` types.
2. Pydantic schema validation and typed CSV parsing.
3. Referential-integrity, uniqueness, type, and relationship-cardinality validation.
4. NetworkX typed directed knowledge graph with 34 nodes and 40 edges.
5. Read-only semantic service and MCP server with five tools and the `ontology://schema` resource.
6. Export bridge for Omnigraph `.pg` schema and JSONL data.
7. MCP Inspector CLI interoperability test and deterministic quality audit.

## Verified outputs

| Check | Observed result |
| --- | --- |
| Sample records | 6 customers, 8 products, 10 orders, 10 invoices |
| Graph size | 34 nodes, 40 relationships |
| Omnigraph export | 74 JSONL records generated, native import unverified |
| MCP tools | 5 discovered and invoked via independent MCP Inspector CLI |
| ONT-08 audit | PASS: 34 entity lookups, 40 bidirectional relations, 8 product queries, 4 invalid queries rejected |
| Python suite through ONT-08 | 108 passed (user-provided local log) |
| ONT-09 tests | Run `python -m pytest -v` and enter actual final count here |

## Grounded query demonstration

**Prompt:** Who purchased Product P001 and what are the associated invoice totals?

The query returns three orders:

| Order | Customer | Invoice total | Payment status |
| --- | --- | --- | --- |
| O001 | Amina Khan | USD 20.50 | paid |
| O003 | Sara Malik | USD 22.50 | pending |
| O006 | Noor Fatima | USD 47.50 | paid |

Amounts refer to **entire invoices** rather than per-product amounts or recognized revenue. The names and records are synthetic.

## Repeatable verification

From an activated Python virtual environment:

```powershell
python -m pip install -r requirements.txt
python -m pytest -v
python load_sample_data.py
python build_graph.py
python quality_audit.py
python final_demo.py
python demo_mcp_client.py
python scripts/inspector_setup.py
python -m scripts.inspector_smoke
```

The final two commands also require a supported Node.js installation and the MCP Inspector CLI available through `npx`.

## Limitations and accurate claims

- The working graph backend is NetworkX. Export files for Omnigraph have been generated, but no successful native Omnigraph CLI import is evidenced.
- The MCP Inspector is an **independent protocol client**, not an autonomous LLM agent. This task demonstrates protocol interoperability and grounded tool results, not natural-language planning by an LLM.
- The quality audit validates a small synthetic dataset, not production throughput, secure multi-tenancy, or performance under load.
- There is no data-governance system, authentication system, or production-grade authorization layer.
- A paid invoice sum is not automatically accounting revenue; no recognized-revenue metric was evaluated.

## Submission evidence checklist

- [ ] GitHub repository with clear README and installation instructions
- [ ] MIT or another compatible open-source license with an appropriate copyright owner
- [ ] ONT-01 through ONT-09 pull requests linked and reviewed
- [ ] Final test output pasted with actual number of passing tests
- [ ] Output of `python final_demo.py` saved
- [ ] Independent MCP Inspector CLI output saved
- [ ] Screenshots of tools list, P001 tool result, and ontology resource
- [ ] Native Omnigraph import status clearly stated
- [ ] Final PR merged into `main` after review

## References

- [ModernRelay Omnigraph](https://github.com/ModernRelay/omnigraph)
- [NVIDIA Auto Ontology](https://github.com/NVIDIA/auto-ontology)
- [MCP Inspector](https://github.com/modelcontextprotocol/inspector)
