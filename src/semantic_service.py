"""Read-only business semantics backed by a validated graph."""

from copy import deepcopy
from pathlib import Path

from src.business_queries import purchases_for_product
from src.data_loader import load_business_dataset
from src.graph_adapter import NetworkXGraphAdapter
from src.schema import load_ontology


class SemanticService:
    """MCP-independent operations; safe to test without a transport."""

    def __init__(self, ontology, graph):
        self.ontology = ontology
        self.graph = graph

    @classmethod
    def from_project(cls, project_root: str | Path):
        root = Path(project_root)
        ontology = load_ontology(root / "ontology" / "business.yaml")
        records, edges = load_business_dataset(root / "sample_data", ontology)
        graph = NetworkXGraphAdapter.from_records(ontology, records, edges)
        return cls(ontology, graph)

    def list_entity_types(self) -> dict:
        return {
            "ontology": self.ontology.name,
            "entity_types": sorted(self.ontology.entities),
            "relationship_types": sorted(self.ontology.relationships),
            "graph_nodes": self.graph.node_count,
            "graph_edges": self.graph.edge_count,
        }

    def describe_entity(self, entity_type: str) -> dict:
        spec = self.ontology.entities.get(entity_type)
        if spec is None:
            raise ValueError(f"Unknown entity type: {entity_type}")
        return {
            "entity_type": entity_type,
            "description": spec.description,
            "key": spec.key,
            "properties": {name: item.model_dump(mode="json") for name, item in spec.properties.items()},
            "relationships": [
                {"type": name, "source": rel.source, "target": rel.target,
                 "cardinality": rel.cardinality}
                for name, rel in sorted(self.ontology.relationships.items())
                if entity_type in (rel.source, rel.target)
            ],
        }

    def get_entity(self, entity_type: str, entity_id: str) -> dict:
        return self.graph.get_entity(entity_type, entity_id)

    def find_related_entities(
        self, entity_type: str, entity_id: str,
        relation: str | None = None, direction: str = "out",
    ) -> dict:
        results = self.graph.related(entity_type, entity_id, relation, direction)
        return {
            "entity_type": entity_type, "entity_id": entity_id,
            "relation": relation, "direction": direction,
            "count": len(results), "results": results,
        }

    def purchases_for_product(self, product_id: str) -> dict:
        rows = purchases_for_product(self.graph, product_id)
        return {"product_id": product_id, "count": len(rows), "purchases": rows}

    def ontology_resource(self) -> dict:
        return deepcopy(self.ontology.model_dump(mode="json"))
