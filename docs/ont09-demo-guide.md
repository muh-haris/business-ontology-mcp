# ONT-09 — 5-minute demonstration guide

## Minute 0–1: Motivation

Explain the difference between raw business rows and ontology-defined concepts: Customer, Product, Order, Invoice. State that the model is not allowed to fabricate missing data.

## Minute 1–2: Ontology and validation

Open `ontology/business.yaml`, show the `PLACES`, `CONTAINS`, `HAS_INVOICE` relationships and `paid_invoice_amount` semantic definition. Show the validator rejecting a nonexistent source customer through `python check_validation.py --invalid` (this intentional test exits nonzero).

## Minute 2–3: Build and query the graph

Run `python build_graph.py`, then `python final_demo.py`. Show the three recorded Product P001 purchases. Explain why invoice totals are not product-specific revenue.

## Minute 3–4: Independent MCP interoperability

Run `python demo_mcp_client.py`, then `python scripts/inspector_setup.py` and `python -m scripts.inspector_smoke`. Explain that the independent CLI queries the MCP server over stdio. Optionally show MCP Inspector browser UI with `purchases_for_product` and `ontology://schema`.

## Minute 4–5: Evidence and limitations

Run `python quality_audit.py` and `python -m pytest -q`. Summarize that the NetworkX backend is validated while Omnigraph native import is not yet verified. Display GitHub PRs and discuss further work: native Omnigraph CLI integration, auth, persistence, and agent evaluation.

## Suggested instructor questions

**Why use an ontology?** It declares business concepts and permitted relations, making graph queries checkable rather than free-form guesses.

**How do you validate relationships?** Each edge must refer to existing typed entities and respect cardinality, which is checked before graph construction.

**Why MCP?** It exposes semantic lookup operations to compatible external clients via a standard interface.

**Is this an AI agent?** It is an agent-facing MCP server and semantic layer. The tests show a client invoking tools, but no autonomous LLM policy has been evaluated.

**Is it integrated with Omnigraph?** A `.pg` + JSONL exporter exists, but native CLI import and query compatibility still require validation.
