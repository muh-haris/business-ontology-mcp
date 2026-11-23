import math
import re
from dataclasses import dataclass
from datetime import date, datetime

from src.schema import Ontology


class RecordValidationError(ValueError):
    """A record or graph relationship violates the ontology."""


@dataclass(frozen=True)
class ValidationReport:
    entity_counts: dict[str, int]
    relationship_counts: dict[str, int]

    @property
    def total_entities(self):
        return sum(self.entity_counts.values())

    @property
    def total_relationships(self):
        return sum(self.relationship_counts.values())


def matches_type(value, declared_type):
    if declared_type == "string":
        return isinstance(value, str)
    if declared_type == "integer":
        return type(value) is int
    if declared_type == "number":
        return type(value) in (int, float) and math.isfinite(value)
    if declared_type == "boolean":
        return type(value) is bool
    if declared_type == "date":
        if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            return False
        try:
            date.fromisoformat(value)
        except ValueError:
            return False
        return True
    if declared_type == "datetime":
        if not isinstance(value, str) or not re.fullmatch(
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?",
            value,
        ):
            return False
        try:
            datetime.fromisoformat(value)
        except ValueError:
            return False
        return True
    return False


def validate_dataset(ontology: Ontology, records: dict, relationships: list) -> ValidationReport:
    """Validate records and typed edges without changing either input."""
    if not isinstance(records, dict):
        raise RecordValidationError("Records must be a dictionary of entity lists")
    if not isinstance(relationships, list):
        raise RecordValidationError("Relationships must be a list")

    entity_counts = {name: 0 for name in ontology.entities}
    relationship_counts = {name: 0 for name in ontology.relationships}
    entity_index = set()

    for entity_type, rows in records.items():
        if entity_type not in ontology.entities:
            raise RecordValidationError(f"Unknown entity type: {entity_type}")
        if not isinstance(rows, list):
            raise RecordValidationError(f"{entity_type}: records must be a list")

        spec = ontology.entities[entity_type]
        for row_number, row in enumerate(rows, 1):
            context = f"{entity_type} row {row_number}"
            if not isinstance(row, dict):
                raise RecordValidationError(f"{context}: record must be an object")

            unknown = set(row) - set(spec.properties)
            if unknown:
                raise RecordValidationError(f"{context}: unknown properties {sorted(unknown)}")

            for property_name, property_spec in spec.properties.items():
                if property_name not in row:
                    if property_spec.required:
                        raise RecordValidationError(f"{context}: missing required {property_name}")
                    continue

                value = row[property_name]
                if not matches_type(value, property_spec.type):
                    raise RecordValidationError(
                        f"{context}: {property_name} must be {property_spec.type}"
                    )
                if property_spec.required and isinstance(value, str) and not value.strip():
                    raise RecordValidationError(f"{context}: {property_name} cannot be blank")

            identifier = row[spec.key]
            identity = (entity_type, identifier)
            if identity in entity_index:
                raise RecordValidationError(f"{context}: duplicate ID {identifier!r}")
            entity_index.add(identity)
            entity_counts[entity_type] += 1

    seen_edges = set()
    sources = {}
    targets = {}
    for number, edge in enumerate(relationships, 1):
        context = f"Relationship row {number}"
        if not isinstance(edge, dict):
            raise RecordValidationError(f"{context}: relationship must be an object")
        required = {"type", "source_id", "target_id"}
        if set(edge) != required:
            raise RecordValidationError(f"{context}: expected fields {sorted(required)}")

        rel_type = edge["type"]
        if not isinstance(rel_type, str) or rel_type not in ontology.relationships:
            raise RecordValidationError(f"{context}: unknown relationship type {rel_type!r}")

        spec = ontology.relationships[rel_type]
        source_id = edge["source_id"]
        target_id = edge["target_id"]

        source_key = ontology.entities[spec.source].properties[ontology.entities[spec.source].key]
        target_key = ontology.entities[spec.target].properties[ontology.entities[spec.target].key]
        if not matches_type(source_id, source_key.type) or not matches_type(target_id, target_key.type):
            raise RecordValidationError(f"{context}: endpoint ID types do not match ontology keys")
        if (spec.source, source_id) not in entity_index:
            raise RecordValidationError(f"{context}: unknown source {spec.source}:{source_id}")
        if (spec.target, target_id) not in entity_index:
            raise RecordValidationError(f"{context}: unknown target {spec.target}:{target_id}")

        triple = (rel_type, source_id, target_id)
        if triple in seen_edges:
            raise RecordValidationError(f"{context}: duplicate relationship")

        source_slot = (rel_type, source_id)
        target_slot = (rel_type, target_id)
        if spec.cardinality in ("one_to_one", "many_to_one") and source_slot in sources:
            raise RecordValidationError(f"{context}: source cardinality violated for {rel_type}")
        if spec.cardinality in ("one_to_one", "one_to_many") and target_slot in targets:
            raise RecordValidationError(f"{context}: target cardinality violated for {rel_type}")

        seen_edges.add(triple)
        sources[source_slot] = target_id
        targets[target_slot] = source_id
        relationship_counts[rel_type] += 1

    return ValidationReport(entity_counts, relationship_counts)
