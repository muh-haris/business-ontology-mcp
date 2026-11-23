"""Validated, typed property graph backed by NetworkX."""

from copy import deepcopy
from typing import Protocol

import networkx as nx

from src.schema import Ontology
from src.validator import validate_dataset


class GraphReader(Protocol):
    """Read-only operations the future MCP server can rely on."""

    def get_entity(self, entity_type: str, entity_id: str) -> dict: ...

    def related(
        self,
        entity_type: str,
        entity_id: str,
        relation: str | None = None,
        direction: str = "out",
    ) -> list[dict]: ...


class NetworkXGraphAdapter:
    def __init__(self, ontology: Ontology):
        self.ontology = ontology
        self.graph = nx.MultiDiGraph()

    @classmethod
    def from_records(cls, ontology: Ontology, records: dict, edges: list):
        """Build a graph only after the complete dataset passes validation."""
        validate_dataset(ontology, records, edges)
        adapter = cls(ontology)

        for entity_type, spec in ontology.entities.items():
            for row in records.get(entity_type, []):
                entity_id = row[spec.key]
                adapter.graph.add_node(
                    (entity_type, entity_id),
                    properties=deepcopy(row),
                )

        for edge in edges:
            rel_type = edge["type"]
            spec = ontology.relationships[rel_type]
            source = (spec.source, edge["source_id"])
            target = (spec.target, edge["target_id"])
            adapter.graph.add_edge(source, target, key=rel_type, type=rel_type)

        return adapter

    @property
    def node_count(self) -> int:
        return self.graph.number_of_nodes()

    @property
    def edge_count(self) -> int:
        return self.graph.number_of_edges()

    def _key(self, entity_type: str, entity_id: str):
        if entity_type not in self.ontology.entities:
            raise ValueError(f"Unknown entity type: {entity_type}")
        key = (entity_type, entity_id)
        if key not in self.graph:
            raise KeyError(f"Unknown entity: {entity_type}:{entity_id}")
        return key

    def _entity(self, key):
        return {
            "type": key[0],
            "id": key[1],
            "properties": deepcopy(self.graph.nodes[key]["properties"]),
        }

    def get_entity(self, entity_type: str, entity_id: str) -> dict:
        return self._entity(self._key(entity_type, entity_id))

    def related(
        self,
        entity_type: str,
        entity_id: str,
        relation: str | None = None,
        direction: str = "out",
    ) -> list[dict]:
        if direction not in {"in", "out", "both"}:
            raise ValueError("direction must be 'in', 'out', or 'both'")
        if relation is not None and relation not in self.ontology.relationships:
            raise ValueError(f"Unknown relationship type: {relation}")

        source = self._key(entity_type, entity_id)
        results = []

        if direction in ("out", "both"):
            for _, target, edge_type in self.graph.out_edges(source, keys=True):
                if relation is None or relation == edge_type:
                    results.append({
                        "relationship": edge_type,
                        "direction": "out",
                        "entity": self._entity(target),
                    })

        if direction in ("in", "both"):
            for origin, _, edge_type in self.graph.in_edges(source, keys=True):
                if relation is None or relation == edge_type:
                    results.append({
                        "relationship": edge_type,
                        "direction": "in",
                        "entity": self._entity(origin),
                    })

        return sorted(
            results,
            key=lambda item: (
                item["relationship"],
                item["direction"],
                item["entity"]["type"],
                str(item["entity"]["id"]),
            ),
        )
