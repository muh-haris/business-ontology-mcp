# ONT-03 — Business Record and Relationship Validation

## Scope

`src/validator.py` validates in-memory business records and typed relationships against `ontology/business.yaml` loaded with `src/schema.py`.

- Required and unknown fields
- Property types (string, integer, finite number, boolean, ISO date, ISO datetime)
- Unique identifiers per entity type
- Existing source and target records
- Declared relationship types
- Duplicate relationship detection
- One-to-one, one-to-many, many-to-one and many-to-many *upper-bound* cardinalities

Input contract:

```python
records = {
    "Customer": [{"customer_id": "C001", "name": "Amina"}],
    "Order": [{"order_id": "O001", "order_date": "2026-11-23", "status": "placed"}],
}
relationships = [
    {"type": "PLACES", "source_id": "C001", "target_id": "O001"},
]
```

Relationship source and target entity **types** are resolved through the ontology definition, so the edge only carries type and endpoint IDs. Records with colliding IDs in different entity types remain distinct.

## Run

```powershell
python check_validation.py
python check_validation.py --invalid
python -m pytest -v tests/test_validator.py
python -m pytest -v
```

The second command intentionally fails with exit code 1, demonstrating rejection of a missing customer.

## Boundaries

Cardinality constraints enforce **maximum** participation. They do not require every order to have an invoice. Business invariants such as non-negative prices, valid ISO currency identifiers, payment-state enumerations, accounting metrics and input-file ingestion are separate work. The next task (ONT-04) will create a larger synthetic dataset and file-loading workflow.
