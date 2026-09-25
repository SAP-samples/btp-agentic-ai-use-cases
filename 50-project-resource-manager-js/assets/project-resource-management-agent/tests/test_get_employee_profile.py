"""Unit test for retrieving employee profile from SuccessFactors (REQ-04)."""
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


class TestGetEmployeeProfile:
    """Tests for REQ-04: Retrieve Employee Profile."""

    def test_employee_profile_server_in_mock(self):
        """Verify SF Employee Profile MCP server is in mcp-mock.json."""
        mock_path = Path(__file__).parent.parent / "mcp-mock.json"
        with open(mock_path) as f:
            mock_data = json.load(f)
        assert "sap-sf-employee-profile" in mock_data["servers"]
        server = mock_data["servers"]["sap-sf-employee-profile"]
        assert "list_eppublicprofile_for_sfodata" in server["tools"]
        assert "get_eppublicprofile_for_sfodata" in server["tools"]

    def test_public_profile_has_user_id_and_intro(self):
        """Verify employee public profile includes user ID and introduction."""
        response = _load_mock_tool_response(
            "sap-sf-employee-profile",
            "list_eppublicprofile_for_sfodata"
        )
        for profile in response["d"]["results"]:
            assert "userId" in profile
            assert "myNameText" in profile
            assert len(profile["myNameText"]) > 0

    def test_profile_introduction_is_relevant(self):
        """Verify introduction text describes professional background."""
        response = _load_mock_tool_response(
            "sap-sf-employee-profile",
            "get_eppublicprofile_for_sfodata"
        )
        profile = response["d"]
        assert "introduction" in profile
        assert len(profile["introduction"]) > 20, "Introduction should be meaningful"

    @pytest.mark.asyncio
    async def test_get_single_profile_by_user_id(self):
        """Test retrieving a single employee profile by user ID."""
        response = _load_mock_tool_response(
            "sap-sf-employee-profile",
            "get_eppublicprofile_for_sfodata"
        )
        tool = _make_mock_tool("get_eppublicprofile_for_sfodata", response)
        result = await tool.ainvoke({"userid": "EMP001"})
        result_data = json.loads(result)
        assert "d" in result_data
        assert result_data["d"]["userId"] == "EMP001"

    def test_certifications_in_profile_mock(self):
        """Verify certification data is available for employees."""
        mock_path = Path(__file__).parent.parent / "mcp-mock.json"
        with open(mock_path) as f:
            mock_data = json.load(f)
        server = mock_data["servers"]["sap-sf-employee-profile"]
        assert "list_background_certificates_for_sfodata" in server["tools"]
        certs_response = server["tools"]["list_background_certificates_for_sfodata"]["mock_response"]
        assert len(certs_response["d"]["results"]) > 0
        cert = certs_response["d"]["results"][0]
        assert "name" in cert
        assert "institution" in cert

    def test_education_background_available(self):
        """Verify education background data is available."""
        response = _load_mock_tool_response(
            "sap-sf-employee-profile",
            "list_background_education_for_sfodata"
        )
        assert len(response["d"]["results"]) > 0
        edu = response["d"]["results"][0]
        assert "school" in edu
        assert "degree" in edu
        assert "userId" in edu
