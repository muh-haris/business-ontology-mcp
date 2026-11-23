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


def test_tool_listing_accepts_bare_result():
    validate_tool_listing({'tools': [{'name': name} for name in EXPECTED_TOOLS]})


def test_product_query_accepts_bare_result():
    validate_product_query(purchase_payload()['result'])


def test_resource_accepts_bare_result():
    validate_resource({'contents': [{'text': json.dumps({
        'name': 'commerce_core',
        'entities': {'Customer': {}, 'Order': {}, 'Product': {}, 'Invoice': {}},
    })}]})


def test_inspector_error_payload_is_rejected():
    with pytest.raises(ValueError, match='Inspector returned an error'):
        extract_result({'error': {'code': 'server_not_found', 'message': 'Missing server'}})


def test_unrecognized_response_has_diagnostic():
    with pytest.raises(ValueError, match='keys='):
        extract_result({'status': 'unexpected'})


def test_main_uses_windows_safe_inspector_tool_argument(monkeypatch, tmp_path):
    # Regression: JSON passed via npx.cmd can lose its embedded quotes on Windows.
    from scripts import inspector_smoke as smoke

    config = tmp_path / "inspector.json"
    config.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(smoke, "CONFIG_PATH", config)
    invocations = []

    def fake_call(*args):
        invocations.append(args)
        if "tools/list" in args:
            return {"tools": [{"name": name} for name in EXPECTED_TOOLS]}
        if "tools/call" in args:
            return purchase_payload()["result"]
        if "resources/read" in args:
            return {"contents": [{"text": json.dumps({
                "name": "commerce_core",
                "entities": {name: {} for name in ("Customer", "Order", "Product", "Invoice")},
            })}]}
        raise AssertionError("Unexpected Inspector method")

    monkeypatch.setattr(smoke, "call_inspector", fake_call)
    smoke.main()

    tool_call = next(args for args in invocations if "tools/call" in args)
    assert "--tool-arg" in tool_call
    assert tool_call[tool_call.index("--tool-arg") + 1] == "product_id=P001"
    assert "--tool-args-json" not in tool_call
