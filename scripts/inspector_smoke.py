"""Validate this project's MCP server through the independent Inspector CLI.

Requires Node.js and @modelcontextprotocol/inspector installed through npx.
"""

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from scripts.inspector_setup import CONFIG_PATH, ROOT, SERVER_NAME

EXPECTED_TOOLS = {
    'list_entity_types', 'describe_entity', 'get_entity',
    'find_related_entities', 'purchases_for_product',
}


def extract_result(envelope: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(envelope, dict):
        raise ValueError('Inspector output is not an object')
    result = envelope.get('result')
    if not isinstance(result, dict):
        raise ValueError('Inspector response has no result object')
    if result.get('isError') is True:
        raise ValueError('Inspector reported MCP tool error')
    return result


def validate_tool_listing(envelope: dict[str, Any]) -> None:
    result = extract_result(envelope)
    tools = result.get('tools')
    if not isinstance(tools, list):
        raise ValueError('Tools listing is missing')
    names = {item.get('name') for item in tools if isinstance(item, dict)}
    missing = EXPECTED_TOOLS - names
    if missing:
        raise ValueError(f'Missing MCP tools: {sorted(missing)}')


def validate_product_query(envelope: dict[str, Any]) -> None:
    result = extract_result(envelope)
    payload = result.get('structuredContent')
    if not isinstance(payload, dict):
        raise ValueError('Product query returned no structuredContent')
    if payload.get('product_id') != 'P001' or payload.get('count') != 3:
        raise ValueError(f'Incorrect P001 summary: {payload!r}')
    purchases = payload.get('purchases')
    if not isinstance(purchases, list) or len(purchases) != 3:
        raise ValueError('Expected three actual purchase rows')
    if {entry.get('order_id') for entry in purchases} != {'O001', 'O003', 'O006'}:
        raise ValueError('Purchase records do not match the sample graph')
    if {entry.get('customer_name') for entry in purchases} != {
        'Amina Khan', 'Sara Malik', 'Noor Fatima',
    }:
        raise ValueError('Purchase customers do not match the sample graph')


def validate_resource(envelope: dict[str, Any]) -> None:
    result = extract_result(envelope)
    contents = result.get('contents')
    if not isinstance(contents, list) or not contents:
        raise ValueError('Ontology resource is missing its contents')
    raw = contents[0].get('text')
    if not isinstance(raw, str):
        raise ValueError('Ontology resource was not returned as text')
    ontology = json.loads(raw)
    if ontology.get('name') != 'commerce_core' or len(ontology.get('entities', {})) != 4:
        raise ValueError('Ontology resource content is incorrect')


def call_inspector(*args: str) -> dict[str, Any]:
    executable = 'npx.cmd' if os.name == 'nt' else 'npx'
    if shutil.which(executable) is None:
        raise RuntimeError('npx not found. Install supported Node.js, then retry.')
    command = [
        executable, '-y', '@modelcontextprotocol/inspector',
        '--cli', '--config', str(CONFIG_PATH), '--server', SERVER_NAME,
        '--format', 'json', *args,
    ]
    try:
        completed = subprocess.run(
            command, cwd=ROOT, capture_output=True, text=True,
            encoding='utf-8', errors='replace', timeout=120,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError('Inspector command timed out') from exc
    if completed.returncode:
        raise RuntimeError(
            f'Inspector exited {completed.returncode}: '
            f'{completed.stderr.strip()[-1200:]}'
        )
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            'Inspector did not produce valid JSON; stdout: '
            + completed.stdout[-1200:]
        ) from exc


def main() -> None:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            'Missing local Inspector config. Run: python scripts/inspector_setup.py'
        )
    validate_tool_listing(call_inspector('--method', 'tools/list'))
    print('Five MCP tools: VERIFIED')
    validate_product_query(call_inspector(
        '--method', 'tools/call',
        '--tool-name', 'purchases_for_product',
        '--tool-args-json', json.dumps({'product_id': 'P001'}),
    ))
    print('P001 query: three grounded purchases VERIFIED')
    validate_resource(call_inspector(
        '--method', 'resources/read', '--uri', 'ontology://schema',
    ))
    print('ontology://schema resource: VERIFIED')
    print('Independent MCP Inspector CLI test: PASSED')


if __name__ == '__main__':
    main()
