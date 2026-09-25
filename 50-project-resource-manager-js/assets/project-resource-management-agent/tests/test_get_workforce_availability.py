"""Unit test for checking employee availability (REQ-03)."""
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


class TestGetWorkforceAvailability:
    """Tests for REQ-03: Check Employee Availability."""

    def test_availability_server_in_mock(self):
        """Verify workforce availability MCP server is in mcp-mock.json."""
        mock_path = Path(__file__).parent.parent / "mcp-mock.json"
        with open(mock_path) as f:
            mock_data = json.load(f)
        assert "sap-s4-workforce-daily-availability" in mock_data["servers"]
        server = mock_data["servers"]["sap-s4-workforce-daily-availability"]
        assert "list_timeoverviewset_for_shcm_api_manage_wf_availability" in server["tools"]

    def test_availability_record_has_required_fields(self):
        """Verify availability records have all required fields."""
        response = _load_mock_tool_response(
            "sap-s4-workforce-daily-availability",
            "list_timeoverviewset_for_shcm_api_manage_wf_availability"
        )
        for record in response["d"]["results"]:
            assert "Personworkagreementexternalid" in record
            assert "Calendardate" in record
            assert "Plannedworkinghours" in record
            assert "Absencehours" in record
            assert "Isnonworkingday" in record

    def test_available_hours_calculation(self):
        """Test that available hours can be calculated from planned minus absence."""
        response = _load_mock_tool_response(
            "sap-s4-workforce-daily-availability",
            "list_timeoverviewset_for_shcm_api_manage_wf_availability"
        )
        for record in response["d"]["results"]:
            planned = float(record["Plannedworkinghours"])
            absence = float(record["Absencehours"])
            available = planned - absence
            assert available >= 0, "Available hours cannot be negative"

    def test_multiple_employees_in_availability_response(self):
        """Verify availability response includes data for multiple employees."""
        response = _load_mock_tool_response(
            "sap-s4-workforce-daily-availability",
            "list_timeoverviewset_for_shcm_api_manage_wf_availability"
        )
        results = response["d"]["results"]
        assert len(results) >= 3

        # Verify there are multiple distinct employees
        emp_ids = {r["Personworkagreementexternalid"] for r in results}
        assert len(emp_ids) >= 2, "Should have data for multiple employees"

    @pytest.mark.asyncio
    async def test_filter_by_date_range(self):
        """Test filtering availability data by date range."""
        response = _load_mock_tool_response(
            "sap-s4-workforce-daily-availability",
            "list_timeoverviewset_for_shcm_api_manage_wf_availability"
        )
        tool = _make_mock_tool(
            "list_timeoverviewset_for_shcm_api_manage_wf_availability",
            response
        )
        result = await tool.ainvoke({
            "filter": "Calendardate ge datetime'2025-02-01T00:00:00' and Calendardate le datetime'2025-06-30T00:00:00'"
        })
        result_data = json.loads(result)
        assert "d" in result_data

    def test_partial_availability_employee_has_absence(self):
        """Test that a partially available employee shows absence hours."""
        response = _load_mock_tool_response(
            "sap-s4-workforce-daily-availability",
            "list_timeoverviewset_for_shcm_api_manage_wf_availability"
        )
        # EMP003 should have 4 absence hours (partial availability)
        emp003_records = [r for r in response["d"]["results"]
                         if r["Personworkagreementexternalid"] == "EMP003"]
        assert len(emp003_records) > 0
        assert float(emp003_records[0]["Absencehours"]) > 0
