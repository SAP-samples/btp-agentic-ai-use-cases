"""Unit test for retrieving open resource requirements (REQ-02)."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest


def _load_mock_tool_response(server_slug: str, tool_name: str):
    mock_path = Path(__file__).parent.parent / "mcp-mock.json"
    with open(mock_path) as f:
        mock_data = json.load(f)
    return mock_data["servers"][server_slug]["tools"][tool_name]["mock_response"]


def _make_mock_tool(name: str, response):
    tool = MagicMock()
    tool.name = name
    tool.description = f"Mock tool: {name}"
    tool.ainvoke = AsyncMock(return_value=json.dumps(response))
    tool.invoke = MagicMock(return_value=json.dumps(response))
    return tool


class TestGetResourceDemands:
    """Tests for REQ-02: Retrieve Open Resource Requirements."""

    def test_resource_demand_tool_in_mock(self):
        """Verify resource demand tools are present in mcp-mock.json."""
        mock_path = Path(__file__).parent.parent / "mcp-mock.json"
        with open(mock_path) as f:
            mock_data = json.load(f)
        server = mock_data["servers"]["sap-s4-project-demand"]
        assert "list_a_projectdemandresource_for_cds_api_projectdemand" in server["tools"]
        assert "list_a_projectdemandresourcerequest_for_cds_api_projectdemand" in server["tools"]

    def test_resource_demand_has_required_fields(self):
        """Verify resource demand records have required fields."""
        response = _load_mock_tool_response(
            "sap-s4-project-demand",
            "list_a_projectdemandresource_for_cds_api_projectdemand"
        )
        for demand in response["d"]["results"]:
            assert "ProjectDemandWorkUUID" in demand
            assert "ProjectDemandUUID" in demand
            assert "ProjDmndAssgmtStatus" in demand

    def test_resource_request_has_date_fields(self):
        """Verify resource request has start and end date for staffing window."""
        response = _load_mock_tool_response(
            "sap-s4-project-demand",
            "list_a_projectdemandresourcerequest_for_cds_api_projectdemand"
        )
        for req in response["d"]["results"]:
            assert "ProjDmndRsceReqStartDate" in req
            assert "ProjDmndRsceReqEndDate" in req

    def test_resource_request_has_staffing_instruction(self):
        """Verify resource request includes staffing instruction text."""
        response = _load_mock_tool_response(
            "sap-s4-project-demand",
            "list_a_projectdemandresourcerequest_for_cds_api_projectdemand"
        )
        assert len(response["d"]["results"]) > 0
        req = response["d"]["results"][0]
        assert "ProjDmndStfngInstructionText" in req
        assert len(req["ProjDmndStfngInstructionText"]) > 0

    @pytest.mark.asyncio
    async def test_filter_demand_by_project_uuid(self):
        """Test filtering resource demands by project UUID."""
        response = _load_mock_tool_response(
            "sap-s4-project-demand",
            "list_a_projectdemandresource_for_cds_api_projectdemand"
        )
        tool = _make_mock_tool(
            "list_a_projectdemandresource_for_cds_api_projectdemand",
            response
        )
        result = await tool.ainvoke({
            "filter": "ProjectDemandUUID eq guid'a1b2c3d4-0001-0001-0001-000000000001'"
        })
        result_data = json.loads(result)
        assert "d" in result_data
        assert len(result_data["d"]["results"]) > 0

    def test_open_demand_status_value(self):
        """Verify that open demand has correct status indicator."""
        response = _load_mock_tool_response(
            "sap-s4-project-demand",
            "list_a_projectdemandresource_for_cds_api_projectdemand"
        )
        # ProjDmndAssgmtStatus = '1' means open/unassigned
        for demand in response["d"]["results"]:
            assert demand["ProjDmndAssgmtStatus"] == "1", "Expected open status '1'"
