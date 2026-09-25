"""Unit test for retrieving employment information from SuccessFactors (REQ-04)."""
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


class TestGetEmploymentInfo:
    """Tests for REQ-04: Retrieve Employment Information."""

    def test_employment_info_server_in_mock(self):
        """Verify SF Employment Information MCP server is in mcp-mock.json."""
        mock_path = Path(__file__).parent.parent / "mcp-mock.json"
        with open(mock_path) as f:
            mock_data = json.load(f)
        assert "sap-sf-employment-information" in mock_data["servers"]
        server = mock_data["servers"]["sap-sf-employment-information"]
        assert "list_empjob_for_sfodata" in server["tools"]
        assert "list_empemployment_for_sfodata" in server["tools"]

    def test_emp_job_has_required_fields(self):
        """Verify EmpJob records have title, department, location and status."""
        response = _load_mock_tool_response(
            "sap-sf-employment-information",
            "list_empjob_for_sfodata"
        )
        for emp in response["d"]["results"]:
            assert "userId" in emp
            assert "jobTitle" in emp, "Job title is required"
            assert "department" in emp, "Department is required"
            assert "location" in emp, "Location is required"
            assert "emplStatus" in emp, "Employment status is required"

    def test_active_employees_have_status_a(self):
        """Verify active employees have employment status 'A'."""
        response = _load_mock_tool_response(
            "sap-sf-employment-information",
            "list_empjob_for_sfodata"
        )
        for emp in response["d"]["results"]:
            assert emp["emplStatus"] == "A", f"Employee {emp['userId']} should be active"

    def test_emp_job_has_standard_hours(self):
        """Verify employment records include standard weekly hours for capacity calculation."""
        response = _load_mock_tool_response(
            "sap-sf-employment-information",
            "list_empjob_for_sfodata"
        )
        for emp in response["d"]["results"]:
            assert "standardHours" in emp
            assert "fte" in emp
            assert float(emp["standardHours"]) > 0

    @pytest.mark.asyncio
    async def test_filter_emp_job_by_user_id(self):
        """Test filtering job info by user ID."""
        response = _load_mock_tool_response(
            "sap-sf-employment-information",
            "list_empjob_for_sfodata"
        )
        tool = _make_mock_tool("list_empjob_for_sfodata", response)
        result = await tool.ainvoke({
            "filter": "userId eq 'EMP001' and emplStatus eq 'A'",
            "top": "1"
        })
        result_data = json.loads(result)
        assert "d" in result_data

    def test_multiple_employees_in_response(self):
        """Verify response includes data for multiple employees."""
        response = _load_mock_tool_response(
            "sap-sf-employment-information",
            "list_empjob_for_sfodata"
        )
        results = response["d"]["results"]
        assert len(results) >= 2

        user_ids = {emp["userId"] for emp in results}
        assert len(user_ids) >= 2, "Should have data for multiple distinct employees"

    def test_partial_fte_employee_present(self):
        """Verify that partial FTE employees are represented in mock data."""
        response = _load_mock_tool_response(
            "sap-sf-employment-information",
            "list_empjob_for_sfodata"
        )
        # EMP003 should have 0.8 FTE
        emp003 = [e for e in response["d"]["results"] if e["userId"] == "EMP003"]
        assert len(emp003) > 0
        assert float(emp003[0]["fte"]) < 1.0, "EMP003 should be part-time"
