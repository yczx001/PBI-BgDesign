import json
import pytest
from pathlib import Path

from pbi_bgdesign.ai.mcp_client import MCPClientManager, load_mcp_config


@pytest.fixture
def mcp_config(tmp_path: Path) -> Path:
    config = {
        "mcpServers": {
            "test-server": {
                "command": "echo",
                "args": ["test"]
            },
            "remote-server": {
                "url": "http://localhost:3001/sse"
            }
        }
    }
    path = tmp_path / "mcp_config.json"
    path.write_text(json.dumps(config))
    return path


def test_load_mcp_config_reads_dict_format(mcp_config):
    config = load_mcp_config(str(mcp_config))
    assert "test-server" in config["mcpServers"]
    assert "remote-server" in config["mcpServers"]


def test_load_mcp_config_missing_file(tmp_path):
    config = load_mcp_config(str(tmp_path / "nonexistent.json"))
    assert config == {"mcpServers": {}}


def test_mcp_client_manager_init():
    manager = MCPClientManager()
    assert len(manager.connected_servers) == 0


def test_mcp_client_manager_infer_transport():
    manager = MCPClientManager()
    assert manager._infer_transport({"command": "npx", "args": []}) == "stdio"
    assert manager._infer_transport({"url": "http://localhost:3001"}) == "sse"
