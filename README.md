# business-ontology-mcp

Open-source business ontology semantic layer with knowledge graph adapters and MCP integration for AI agents.

# Business Ontology MCP

An open-source Python semantic layer for defining
business concepts, building knowledge graphs, and
exposing graph queries to AI agents through MCP.

## Planned Components

- YAML ontology definitions
- Pydantic schema validation
- NetworkX graph prototype
- Omnigraph graph adapter
- MCP tools and resources
- Automated tests

## Architecture

See [Architecture Design](docs/architecture.md).

## References

- https://github.com/ModernRelay/omnigraph
- https://github.com/NVIDIA/auto-ontology

## Status

ONT-01: Architecture and reference analysis.
Implementation begins in ONT-02.

# ONT-02

## Business Ontology Schema

The initial ontology is defined in
`ontology/business.yaml`.

It contains four entity types:

- Customer
- Product
- Order
- Invoice

Relationships:

- Customer PLACES Order
- Order CONTAINS Product
- Order HAS_INVOICE Invoice

It also declares a paid-invoice amount metric
grouped by currency.

### Installation

Create and activate a Python virtual environment,
then run:

    python -m pip install -r requirements.txt

### Load the ontology

    python -m src.schema

### Run tests

    python -m pytest -v

### Current scope

ONT-02 provides typed ontology definitions,
YAML loading, structural validation and
basic reference checking.

Full business-record validation and graph
construction are implemented in later tasks.

# ONT-03

## Business Record Validation

The ontology validator checks business records
and relationships against the declared schema.

Supported checks:

- Required and unknown properties
- Property data types
- Unique entity identifiers
- Referential integrity
- Relationship cardinality
- Duplicate relationships

### Run demonstration

python check_validation.py

### Test invalid data

python check_validation.py --invalid

### Run automated tests

python -m pytest -v

For implementation details, see:
docs/ont03-record-validation.md
