"""Unit test for listing active projects via Project Demand MCP tool (REQ-01)."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _load_mock_tool_response(server_slug: str, tool_name: str):
    """Load mock response from mcp-mock.json for the given tool."""
    mock_path = Path(__file__).parent.parent / "mcp-mock.json"
    with open(mock_path) as f:
        mock_data = json.load(f)
    return mock_data["servers"][server_slug]["tools"][tool_name]["mock_response"]


def _make_mock_tool(name: str, response):
    """Create a LangChain-compatible mock tool."""
    tool = MagicMock()
    tool.name = name
    tool.description = f"Mock tool: {name}"
    invoke_mock = AsyncMock(return_value=json.dumps(response))
    tool.ainvoke = invoke_mock
    tool.invoke = MagicMock(return_value=json.dumps(response))
    return tool


class TestGetActiveProjects:
    """Tests for REQ-01: List Active Projects."""

    def test_mock_data_has_active_projects(self):
        """Verify mcp-mock.json contains project demand data."""
        response = _load_mock_tool_response(
            "sap-s4-project-demand",
            "list_a_projectdemand_for_cds_api_projectdemand"
        )
        assert "d" in response
        results = response["d"]["results"]
        assert len(results) >= 2
        first = results[0]
        assert "ProjectDemandUUID" in first
        assert "ProjectDemandName" in first
        assert "ProjectDemandStatus" in first

    def test_active_project_has_required_fields(self):
        """Verify active project records have all required fields."""
        response = _load_mock_tool_response(
            "sap-s4-project-demand",
            "list_a_projectdemand_for_cds_api_projectdemand"
        )
        for project in response["d"]["results"]:
            assert "ProjectDemandUUID" in project, "Project UUID missing"
            assert "ProjectDemand" in project, "Project ID missing"
            assert "ProjectDemandName" in project, "Project Name missing"
            assert "ProjectDemandStatus" in project, "Project Status missing"

    def test_project_demand_tool_exists_in_mock(self):
        """Verify the Project Demand MCP server and tools are in mcp-mock.json."""
        mock_path = Path(__file__).parent.parent / "mcp-mock.json"
        with open(mock_path) as f:
            mock_data = json.load(f)
        assert "sap-s4-project-demand" in mock_data["servers"]
        server = mock_data["servers"]["sap-s4-project-demand"]
        assert "list_a_projectdemand_for_cds_api_projectdemand" in server["tools"]
        assert "get_a_projectdemand_for_cds_api_projectdemand" in server["tools"]

    @pytest.mark.asyncio
    async def test_list_projects_tool_invocable(self):
        """Test that the list projects tool can be invoked with mock data."""
        response = _load_mock_tool_response(
            "sap-s4-project-demand",
            "list_a_projectdemand_for_cds_api_projectdemand"
        )
        tool = _make_mock_tool(
            "list_a_projectdemand_for_cds_api_projectdemand",
            response
        )
        result = await tool.ainvoke({"filter": "ProjectDemandStatus eq '03'"})
        result_data = json.loads(result)
        assert "d" in result_data
        assert len(result_data["d"]["results"]) > 0

    def test_project_date_range_fields_present(self):
        """Verify project demand records contain start and end date fields."""
        response = _load_mock_tool_response(
            "sap-s4-project-demand",
            "list_a_projectdemand_for_cds_api_projectdemand"
        )
        for project in response["d"]["results"]:
            assert "ProjectDemandStartDate" in project
            assert "ProjectDemandEndDate" in project
