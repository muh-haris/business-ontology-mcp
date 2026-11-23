
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PropertySpec(StrictModel):
    type: Literal[
        "string", "integer", "number",
        "boolean", "date", "datetime"
    ]
    description: str = Field(min_length=1)
    required: bool = False


class EntitySpec(StrictModel):
    description: str = Field(min_length=1)
    key: str = Field(min_length=1)
    properties: dict[str, PropertySpec] = Field(min_length=1)


class RelationshipSpec(StrictModel):
    description: str = Field(min_length=1)
    source: str = Field(min_length=1)
    target: str = Field(min_length=1)
    cardinality: Literal[
        "one_to_one", "one_to_many",
        "many_to_one", "many_to_many"
    ]


class MetricSpec(StrictModel):
    description: str = Field(min_length=1)
    source: str = Field(min_length=1)
    field: str = Field(min_length=1)
    aggregate: Literal["sum", "count", "average"]
    filters: dict[str, str] = Field(default_factory=dict)
    group_by: list[str] = Field(default_factory=list)


class Ontology(StrictModel):
    version: str = Field(min_length=1)
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    entities: dict[str, EntitySpec] = Field(min_length=1)
    relationships: dict[str, RelationshipSpec] = Field(default_factory=dict)
    metrics: dict[str, MetricSpec] = Field(default_factory=dict)

    @model_validator(mode="after")
    def check_references(self):
        for name, entity in self.entities.items():
            key = entity.properties.get(entity.key)

            if key is None or not key.required:
                raise ValueError(
                    f"{name}: key must be a required property"
                )

        for name, rel in self.relationships.items():
            if rel.source not in self.entities:
                raise ValueError(
                    f"{name}: unknown source entity {rel.source}"
                )

            if rel.target not in self.entities:
                raise ValueError(
                    f"{name}: unknown target entity {rel.target}"
                )

        for name, metric in self.metrics.items():
            entity = self.entities.get(metric.source)

            if entity is None:
                raise ValueError(
                    f"{name}: unknown metric source {metric.source}"
                )

            for field in [
                metric.field, *metric.filters, *metric.group_by
            ]:
                if field not in entity.properties:
                    raise ValueError(
                        f"{name}: unknown property {field}"
                    )

        return self


def load_ontology(path: str | Path) -> Ontology:
    with Path(path).open(encoding="utf-8") as file:
        data = yaml.safe_load(file)

    if not isinstance(data, dict):
        raise ValueError(
            "Ontology YAML must contain a mapping"
        )

    return Ontology.model_validate(data)


if __name__ == "__main__":
    path = (
        Path(__file__).resolve().parents[1]
        / "ontology"
        / "business.yaml"
    )

    ontology = load_ontology(path)

    print(
        f"Ontology: {ontology.name} "
        f"(v{ontology.version})"
    )
    print(
        f"Entities ({len(ontology.entities)}): "
        f"{', '.join(ontology.entities)}"
    )
    print(
        f"Relationships ({len(ontology.relationships)}): "
        f"{', '.join(ontology.relationships)}"
    )
    print(
        f"Metrics ({len(ontology.metrics)}): "
        f"{', '.join(ontology.metrics)}"
    )
