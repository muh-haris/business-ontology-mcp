# ONT-04 — Synthetic business records

This directory contains fictional, reproducible commerce fixtures in CSV format.
All names and emails are synthetic (`example.org`) and do not represent real customers.

## Files

| CSV | Rows | Purpose |
|---|---:|---|
| `customers.csv` | 6 | Customers |
| `products.csv` | 8 | Product catalog, prices in USD |
| `orders.csv` | 10 | Orders with ISO date strings |
| `invoices.csv` | 10 | Seven paid and three pending invoices |
| `relationships.csv` | 40 | 10 PLACES, 20 CONTAINS and 10 HAS_INVOICE edges |

All ten orders have exactly two distinct products, one customer and one invoice. Some
products are shared across orders. One-to-one and one-to-many restrictions are verified
using the existing ONT-03 validator.

Run `python load_sample_data.py`, then `python -m pytest -v`.

The loader uses the ONT-02 ontology to select and convert CSV properties, and calls
`validate_dataset` from ONT-03 before returning the records and edges. No graph database
or MCP server is involved yet; those are planned for ONT-05 and ONT-06.

**Limitations:** Product quantities, line-item discounts, taxes and returns have not been
modeled. Invoice amounts are deliberately chosen to equal the sum of the two listed
product prices for each order. This fixture does not prove financial reconciliation or
recognized revenue. The declared `paid_invoice_amount` metric is not executed here.

## Expected output

```text
Ontology: commerce_core
Entities: {'Customer': 6, 'Product': 8, 'Order': 10, 'Invoice': 10}
Relationships: {'PLACES': 10, 'CONTAINS': 20, 'HAS_INVOICE': 10}
Total entities: 34
Total relationships: 40
Business dataset validation: PASSED
```
