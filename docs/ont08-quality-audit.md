# ONT-08 — Integration Testing and Reliability Audit

## Objective
Verify that the business ontology, CSV loader, record validator, NetworkX graph adapter, and read-only semantic service agree on the same synthetic data. This stage does not alter the MCP server.

## Artifacts
- `src/quality_audit.py`: deterministic fail-closed quality checks
- `quality_audit.py`: CLI runner and JSON report writer
- `tests/test_e2e_integration.py`: 11 real-data integration tests
- `tests/test_quality_audit.py`: 5 audit contract tests

## Run on Windows 10
From the repository root with the existing `.venv` activated:

```powershell
python -m pytest -v tests/test_e2e_integration.py tests/test_quality_audit.py
python quality_audit.py
Get-Content reports/generated/ont08_audit.json
python -m pytest -v
```

Expected with the unchanged synthetic data: 34 nodes, 40 edges, 40 bidirectional edge checks, eight product queries, four rejected invalid queries. The audit exits nonzero on an invariant violation rather than printing success.

## Coverage
- Reads the actual YAML ontology and five CSV files
- Uses the existing loader and validator before graph construction
- Verifies node and edge counts, every graph entity and every edge in both directions
- Independently compares each product's order IDs to its source CSV edges
- Confirms the golden Product P001 example has orders O001, O003 and O006
- Checks that pending Invoice I003 remains pending
- Ensures invalid lookups and relationship requests raise errors
- Ensures callers cannot mutate the graph through returned entity dictionaries
- Generates a JSON-serializable, deterministic audit report

## Correct interpretation
The `invoice_amount` in `purchases_for_product` is the **total amount of the invoice for the entire order**, not the price attributable to the selected product. A payment status of `paid` does not establish accounting revenue recognition.

## Separate verifications and remaining limitations
- ONT-07 already demonstrated independent MCP Inspector CLI interoperability; the ONT-08 audit does not replace or rerun that Node.js integration.
- Omnigraph native CLI loading remains unverified unless separately executed.
- This is a deterministic correctness audit of synthetic data, not a production stress test, vulnerability scan, load test, or LLM agent evaluation.
- The current graph is in memory and reloaded from CSV at server startup; runtime persistence is not implemented.
- These golden checks are deliberately tied to the versioned demonstration dataset; changes to the dataset may require updating expected values and documenting why.

## Generated files
The CLI writes `reports/generated/ont08_audit.json`. Add `reports/generated/` to `.gitignore`; review and summarize the report in your tracked README or final evaluation document instead of committing machine-generated output automatically.
