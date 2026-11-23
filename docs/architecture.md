# Business Ontology and MCP — Architecture Design

## 1. Objective

Build an open-source business ontology layer that defines business entities, their properties and relationships, converts validated business records into a knowledge graph, and exposes semantic information through MCP to compatible AI agents.

## 2. Reference Projects

**Omnigraph:** Typed property-graph engine supporting schema enforcement, relationships, queries and graph versioning.

Repository: https://github.com/ModernRelay/omnigraph

**NVIDIA Auto Ontology:** Framework for discovering enterprise metadata, managing business semantic definitions and exposing semantic capabilities to AI agents.

Repository: https://github.com/NVIDIA/auto-ontology

## 3. Proposed Architecture

1. YAML ontology definitions
2. Ontology parser and validator
3. Graph adapter interface
4. NetworkX and Omnigraph backends
5. Read-only MCP semantic server
6. Open-source MCP client or agent

## 4. Initial Business Domain

Entities:

- Customer: customer_id, name, email
- Product: product_id, name, unit_price, currency
- Order: order_id, order_date, status
- Invoice: invoice_id, amount, currency, status

Relationships:

- Customer places Order
- Order contains Product
- Order has Invoice

Every entity has a unique identifier. All relationships must reference existing entities and follow the ontology's declared source and target types.

## 5. Semantic Concepts

The ontology will distinguish raw data from business meaning.

For example, revenue is not automatically equal to an order's listed value. Any implemented revenue metric must have an explicit definition covering the source records, invoice/payment status, currency, time period and aggregation rules.

## 6. Graph Adapter

The graph adapter will expose a consistent interface for adding validated entities, adding relationships, retrieving records and traversing the graph.

The first implementation will use NetworkX. A separate Omnigraph adapter will translate the same semantic model to supported Omnigraph schemas and graph operations.

## 7. MCP Capabilities

Planned read-only tools:

- list_entity_types
- describe_entity
- get_entity
- find_related_entities
- query_business_graph

The server will return structured, validated results. Arbitrary code execution and unrestricted database queries will not be exposed.

## 8. Demonstration

Load synthetic customer, order, product and invoice records.

Demonstrate that a client can discover the ontology and correctly answer which customers purchased a given product by traversing actual graph relationships.

Test the difference between known records, unknown records and invalid queries.

## 9. Security and Reliability

- Use synthetic sample data.
- Reject invalid entity types and relationship references.
- Validate all incoming query arguments.
- Keep graph-query tools read-only initially.
- Return explicit errors for missing records.
- Do not expose secrets in code or logs.
- Do not claim that an agent response is grounded unless it uses graph-query results.

## 10. Development Plan

ONT-02: Ontology schema

ONT-03: Validation

ONT-04: Sample business data

ONT-05: Graph adapters

ONT-06: MCP server

ONT-07: Open-source client integration

ONT-08: Tests and documentation

ONT-09: Final demonstration and pull request

## 11. Deliverables

A public GitHub repository containing source code, ontology definitions, validated synthetic data, an operational knowledge graph backend, MCP server, tests, documentation and reproducible demonstrations.

## 12. Scope and Limitations

The first version will not automatically infer arbitrary enterprise ontologies, connect to production enterprise databases or train a language model.

NVIDIA Auto Ontology integration is optional and will be evaluated separately. The Omnigraph backend must be tested against actual Omnigraph tooling before being described as supported.
