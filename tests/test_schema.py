
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from src.schema import Ontology, load_ontology


FILE = (
    Path(__file__).resolve().parents[1]
    / "ontology"
    / "business.yaml"
)


def raw_ontology():
    return yaml.safe_load(
        FILE.read_text(encoding="utf-8")
    )


def test_business_ontology_loads():
    ontology = load_ontology(FILE)

    assert ontology.name == "commerce_core"
    assert len(ontology.entities) == 4
    assert len(ontology.relationships) == 3

    assert (
        ontology.metrics["paid_invoice_amount"].group_by
        == ["currency"]
    )


def test_unknown_relationship_target_rejected():
    data = raw_ontology()
    data["relationships"]["PLACES"]["target"] = "Employee"

    with pytest.raises(
        ValidationError, match="unknown target"
    ):
        Ontology.model_validate(data)


def test_missing_key_property_rejected():
    data = raw_ontology()

    del data["entities"]["Customer"]["properties"]["customer_id"]

    with pytest.raises(
        ValidationError, match="required property"
    ):
        Ontology.model_validate(data)


def test_invalid_property_type_rejected():
    data = raw_ontology()

    data["entities"]["Product"]["properties"]["unit_price"]["type"] = "money"

    with pytest.raises(ValidationError):
        Ontology.model_validate(data)


def test_unknown_metric_field_rejected():
    data = raw_ontology()
    data["metrics"]["paid_invoice_amount"]["field"] = "profit"

    with pytest.raises(
        ValidationError, match="unknown property"
    ):
        Ontology.model_validate(data)


def test_extra_schema_field_rejected():
    data = raw_ontology()
    data["entities"]["Customer"]["unexpected"] = "value"

    with pytest.raises(
        ValidationError, match="Extra inputs"
    ):
        Ontology.model_validate(data)


def test_non_mapping_yaml_rejected(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text(
        "- customer\n- product\n",
        encoding="utf-8"
    )

    with pytest.raises(
        ValueError, match="must contain a mapping"
    ):
        load_ontology(path)
