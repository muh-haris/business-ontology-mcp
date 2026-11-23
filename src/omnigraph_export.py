"""Translate validated business ontologies into Omnigraph .pg and JSONL files.

This is a file-format export bridge, not a live Omnigraph client.
"""

import json
import re
from pathlib import Path

from src.schema import Ontology
from src.validator import validate_dataset


TYPE_MAP = {
    "string": "String",
    "integer": "I64",
    "number": "F64",
    "boolean": "Bool",
    "date": "Date",
    "datetime": "DateTime",
}
IDENTIFIER = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


def _name(value: str) -> str:
    if not IDENTIFIER.fullmatch(value):
        raise ValueError(f"Invalid Omnigraph identifier: {value!r}")
    return value


def render_schema(ontology: Ontology) -> str:
    """Generate a basic typed .pg schema using the documented syntax."""
    lines = ["// Generated from business ontology; verify with omnigraph CLI."]

    for entity_type, spec in ontology.entities.items():
        lines.append(f"node {_name(entity_type)} {{")
        for property_name, prop in spec.properties.items():
            type_name = TYPE_MAP[prop.type]
            if not prop.required:
                type_name += "?"
            key_annotation = " @key" if property_name == spec.key else ""
            lines.append(f"  {_name(property_name)}: {type_name}{key_annotation}")
        lines.append("}\n")

    for rel_name, rel in ontology.relationships.items():
        base = (
            f"edge {_name(rel_name)}: {_name(rel.source)} -> {_name(rel.target)}"
        )
        if rel.cardinality in ("one_to_one", "many_to_one"):
            base += " @card(0..1)"
        if rel.cardinality in ("one_to_one", "one_to_many"):
            lines.extend([base + " {", "  @unique(@dst)", "}\n"])
        else:
            lines.append(base + "\n")

    return "\n".join(lines).rstrip() + "\n"


def render_jsonl(ontology: Ontology, records: dict, edges: list) -> str:
    """Emit the documented node/edge load envelopes, one object per line."""
    validate_dataset(ontology, records, edges)
    rows = []
    for entity_type in ontology.entities:
        for entity in records.get(entity_type, []):
            rows.append({"type": entity_type, "data": entity})
    for edge in edges:
        rows.append({
            "edge": edge["type"],
            "from": edge["source_id"],
            "to": edge["target_id"],
        })
    return "".join(
        json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n"
        for row in rows
    )


def export_omnigraph(
    ontology: Ontology, records: dict, edges: list, directory: str | Path
) -> tuple[Path, Path]:
    validate_dataset(ontology, records, edges)
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    schema_file = directory / "schema.pg"
    data_file = directory / "data.jsonl"
    schema_file.write_text(render_schema(ontology), encoding="utf-8")
    data_file.write_text(render_jsonl(ontology, records, edges), encoding="utf-8")
    return schema_file, data_file
