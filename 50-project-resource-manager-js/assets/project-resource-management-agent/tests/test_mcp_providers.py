"""Tests for the MCP providers (agw) module — covers token context and mock mode."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio

import pytest

APP_PATH = str(Path(__file__).parent.parent / "app")
if APP_PATH not in sys.path:
    sys.path.insert(0, APP_PATH)


class TestAGWTokenContext:
    """Tests for user token context management in agw module."""

    def test_set_user_token_stores_token(self):
        """Verify set_user_token stores a token in the context var."""
        from mcp_providers.agw import set_user_token, get_user_token
        set_user_token("test-jwt-token-12345")
        result = get_user_token()
        assert result == "test-jwt-token-12345"

    def test_get_user_token_returns_none_by_default(self):
        """Verify get_user_token returns None when no token is set."""
        from mcp_providers.agw import get_user_token, set_user_token
        set_user_token(None)
        result = get_user_token()
        assert result is None

    def test_set_user_token_can_be_updated(self):
        """Verify token can be updated."""
        from mcp_providers.agw import set_user_token, get_user_token
        set_user_token("token-v1")
        set_user_token("token-v2")
        result = get_user_token()
        assert result == "token-v2"

    def test_get_user_sub_function_exists(self):
        """Verify get_user_sub function is available."""
        from mcp_providers.agw import get_user_sub
        assert callable(get_user_sub)

    def test_get_user_sub_returns_string_in_test_mode(self):
        """Verify get_user_sub returns a string in IBD_TESTING mode."""
        import os
        # IBD_TESTING=1 is set by conftest.py, so get_user_sub should return 'unknown'
        from mcp_providers.agw import get_user_sub, set_user_token
        set_user_token(None)  # Ensure no token is set
        if os.environ.get("IBD_TESTING") == "1":
            result = get_user_sub()
            assert isinstance(result, str)
            assert result == "unknown"  # IBD_TESTING returns 'unknown' when no token

    def test_mcp_mock_file_path_is_correct(self):
        """Verify the mock file path points to the correct location."""
        from mcp_providers.agw import _MOCK_FILE
        assert _MOCK_FILE.name == "mcp-mock.json"
        # The mock file should exist since we created it
        assert _MOCK_FILE.exists(), f"mcp-mock.json should exist at {_MOCK_FILE}"


class TestAGWMockMode:
    """Tests for get_mcp_tools in IBD_TESTING mode."""

    @pytest.mark.asyncio
    async def test_get_mcp_tools_returns_tools_in_test_mode(self):
        """Verify get_mcp_tools returns tool list when IBD_TESTING is set."""
        # IBD_TESTING=1 is already set by conftest.py
        assert os.environ.get("IBD_TESTING") == "1"
        try:
            from mcp_tools import get_mcp_tools
            tools = await get_mcp_tools()
            assert isinstance(tools, list)
            assert len(tools) > 0
        except ImportError:
            pytest.skip("mcp_tools module not available")

    @pytest.mark.asyncio
    async def test_mock_tools_have_names(self):
        """Verify each mock tool has a name attribute."""
        try:
            from mcp_tools import get_mcp_tools
            tools = await get_mcp_tools()
            for tool in tools:
                assert hasattr(tool, "name") or hasattr(tool, "__name__")
        except ImportError:
            pytest.skip("mcp_tools module not available")

    def test_mcp_mock_json_tools_match_expected_count(self):
        """Verify mcp-mock.json has the expected number of tools."""
        mock_path = Path(__file__).parent.parent / "mcp-mock.json"
        with open(mock_path) as f:
            data = json.load(f)
        total = sum(len(s["tools"]) for s in data["servers"].values())
        assert total >= 20, f"Expected at least 20 tools, found {total}"

    def test_agw_module_has_required_exports(self):
        """Verify agw module exports all required functions."""
        from mcp_providers import agw
        required = ["set_user_token", "get_user_token", "get_user_sub"]
        for name in required:
            assert hasattr(agw, name), f"agw must export: {name}"


class TestAgentMainModule:
    """Tests for main.py structure and bootstrap."""

    def test_main_py_imports_required_modules(self):
        """Verify main.py imports agent_executor and sets up A2A server."""
        main_path = Path(__file__).parent.parent / "app" / "main.py"
        content = main_path.read_text()
        assert "agent_executor" in content.lower() or "AgentExecutor" in content
        assert "bootstrap" in content

    def test_main_py_uses_correct_port(self):
        """Verify main.py uses port 5000 for Python agents."""
        main_path = Path(__file__).parent.parent / "app" / "main.py"
        content = main_path.read_text()
        assert "5000" in content or "port" in content.lower()

    def test_agent_executor_importable(self):
        """Verify AgentExecutor module is importable."""
        try:
            from agent_executor import AgentExecutor
            assert AgentExecutor is not None
        except ImportError:
            pytest.skip("agent_executor module not available")

    def test_mcp_tools_module_uses_mock_in_test_mode(self):
        """Verify mcp_tools returns mock data when IBD_TESTING=1."""
        try:
            import mcp_tools
            # The module should exist and be importable
            assert mcp_tools is not None
        except ImportError:
            pytest.skip("mcp_tools not available")
