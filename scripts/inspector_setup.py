"""Create a machine-local MCP Inspector configuration for this project."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / '.mcp-local' / 'inspector.json'
SERVER_NAME = 'business-ontology'


def build_config(root: Path, python_executable: str) -> dict:
    root = Path(root).resolve()
    return {
        'mcpServers': {
            SERVER_NAME: {
                'type': 'stdio',
                'command': str(Path(python_executable).resolve()),
                'args': [str(root / 'mcp_server.py')],
                'cwd': str(root),
            }
        }
    }


def main() -> None:
    if not (ROOT / 'mcp_server.py').is_file():
        raise FileNotFoundError('mcp_server.py is missing. Complete ONT-06 first.')
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(
        json.dumps(build_config(ROOT, sys.executable), indent=2) + '\n',
        encoding='utf-8',
    )
    print('Inspector config:', CONFIG_PATH)
    print('Python executable:', sys.executable)
    print('Server:', SERVER_NAME)
    print('Configuration created: PASSED')


if __name__ == '__main__':
    main()
