"""Fast, offline tests for Inspector setup and response assertions."""

import json
from pathlib import Path

import pytest

from scripts.inspector_setup import SERVER_NAME, build_config
from scripts.inspector_smoke import (
    EXPECTED_TOOLS, extract_result, validate_product_query,
    validate_resource, validate_tool_listing,
)


def test_config_resolves_server_command(tmp_path):
    data = build_config(tmp_path, str(tmp_path / 'python.exe'))
    server = data['mcpServers'][SERVER_NAME]
    assert server['type'] == 'stdio'
    assert Path(server['args'][0]) == tmp_path / 'mcp_server.py'
    assert server['cwd'] == str(tmp_path)


def test_config_does_not_require_secrets(tmp_path):
    server = build_config(tmp_path, str(tmp_path / 'python.exe'))['mcpServers'][SERVER_NAME]
    assert 'env' not in server
    assert 'API_KEY' not in json.dumps(server)


def test_inspector_result_is_required():
    with pytest.raises(ValueError, match='no result'):
        extract_result({'result': None})


def test_tool_errors_are_not_accepted():
    with pytest.raises(ValueError, match='tool error'):
        extract_result({'result': {'isError': True}})


def test_tool_listing_accepts_five_tools():
    validate_tool_listing({'result': {'tools': [{'name': x} for x in EXPECTED_TOOLS]}})


def test_tool_listing_rejects_missing_tool():
    with pytest.raises(ValueError, match='Missing MCP tools'):
        validate_tool_listing({'result': {'tools': [{'name': 'get_entity'}]}})


def purchase_payload():
    return {'result': {'structuredContent': {
        'product_id': 'P001', 'count': 3,
        'purchases': [
            {'order_id': 'O001', 'customer_name': 'Amina Khan'},
            {'order_id': 'O003', 'customer_name': 'Sara Malik'},
            {'order_id': 'O006', 'customer_name': 'Noor Fatima'},
        ],
    }}}


def test_grounded_purchase_query_is_accepted():
    validate_product_query(purchase_payload())


def test_missing_structured_output_is_rejected():
    with pytest.raises(ValueError, match='structuredContent'):
        validate_product_query({'result': {'content': []}})


def test_resource_contains_expected_ontology():
    envelope = {'result': {'contents': [{'text': json.dumps({
        'name': 'commerce_core', 'entities': {'Customer': {}, 'Order': {}, 'Product': {}, 'Invoice': {}}
    })}]}}
    validate_resource(envelope)


def test_resource_missing_schema_rejected():
    with pytest.raises(ValueError, match='contents'):
        validate_resource({'result': {'contents': []}})
