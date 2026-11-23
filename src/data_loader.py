"""Load CSV business records into the dictionaries expected by validate_dataset."""

import csv
import re
from pathlib import Path

from src.schema import Ontology
from src.validator import RecordValidationError, validate_dataset

EDGE_COLUMNS = ("type", "source_id", "target_id")


def convert_value(value: str, property_type: str, context: str):
    """Parse CSV text to the Python type declared by the ontology."""
    text = value.strip()

    if property_type in ("string", "date", "datetime"):
        return text

    if property_type == "integer":
        if not re.fullmatch(r"[+-]?\d+", text):
            raise RecordValidationError(f"{context}: invalid integer {value!r}")
        return int(text)

    if property_type == "number":
        try:
            return float(text)
        except ValueError:
            raise RecordValidationError(
                f"{context}: invalid number {value!r}"
            ) from None

    if property_type == "boolean":
        if text.lower() not in ("true", "false"):
            raise RecordValidationError(f"{context}: expected true or false")
        return text.lower() == "true"

    raise RecordValidationError(f"{context}: unsupported type {property_type}")


def _read_table(path: Path, expected_columns: set[str], required_columns: set[str]):
    if not path.is_file():
        raise FileNotFoundError(f"Missing dataset file: {path}")

    with path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise RecordValidationError(f"{path.name}: empty CSV or missing header")

        actual = reader.fieldnames
        if any(not key for key in actual) or len(actual) != len(set(actual)):
            raise RecordValidationError(f"{path.name}: blank or duplicate CSV header")

        unknown = set(actual) - expected_columns
        missing = required_columns - set(actual)
        if unknown or missing:
            raise RecordValidationError(
                f"{path.name}: unknown columns {sorted(unknown)}; missing columns {sorted(missing)}"
            )

        rows = []
        for line, row in enumerate(reader, start=2):
            if None in row or any(value is None for value in row.values()):
                raise RecordValidationError(f"{path.name}:{line}: incorrect number of CSV fields")
            rows.append(row)
        return rows


def load_business_dataset(folder: str | Path, ontology: Ontology):
    """Return (records, edges) already validated against the ontology."""
    folder = Path(folder)
    records = {}

    for entity_name, spec in ontology.entities.items():
        path = folder / f"{entity_name.lower()}s.csv"
        required = {key for key, prop in spec.properties.items() if prop.required}
        source_rows = _read_table(path, set(spec.properties), required)
        parsed_rows = []

        for index, raw in enumerate(source_rows, start=2):
            record = {}
            for key, value in raw.items():
                prop = spec.properties[key]
                if not value.strip() and not prop.required:
                    continue
                record[key] = convert_value(
                    value, prop.type, f"{path.name}:{index} {key}"
                )
            parsed_rows.append(record)

        records[entity_name] = parsed_rows

    raw_edges = _read_table(
        folder / "relationships.csv", set(EDGE_COLUMNS), set(EDGE_COLUMNS)
    )
    edges = [
        {column: row[column].strip() for column in EDGE_COLUMNS}
        for row in raw_edges
    ]

    # ONT-03 owns data-type, uniqueness, referential and cardinality rules.
    validate_dataset(ontology, records, edges)
    return records, edges
