"""Unit test for checking employee time-off / leave data (REQ-03a)."""
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


class TestGetEmployeeTimeOff:
    """Tests for REQ-03a: Check Employee Time-Off / Leave Data."""

    def test_timeoff_server_in_mock(self):
        """Verify time-off MCP server is in mcp-mock.json."""
        mock_path = Path(__file__).parent.parent / "mcp-mock.json"
        with open(mock_path) as f:
            mock_data = json.load(f)
        assert "sap-sf-time-off" in mock_data["servers"]
        server = mock_data["servers"]["sap-sf-time-off"]
        assert "list_employeetime_for_sfodata" in server["tools"]

    def test_timeoff_record_has_required_fields(self):
        """Verify time-off records have all required fields for conflict detection."""
        response = _load_mock_tool_response(
            "sap-sf-time-off",
            "list_employeetime_for_sfodata"
        )
        for record in response["d"]["results"]:
            assert "userId" in record
            assert "timeType" in record
            assert "startDate" in record
            assert "endDate" in record
            assert "quantityInDays" in record
            assert "approvalStatus" in record

    def test_timeoff_records_have_approved_status(self):
        """Verify at least one time-off record has approved status."""
        response = _load_mock_tool_response(
            "sap-sf-time-off",
            "list_employeetime_for_sfodata"
        )
        approved = [r for r in response["d"]["results"] if r["approvalStatus"] == "APPROVED"]
        assert len(approved) >= 1, "Should have at least one approved time-off record"

    def test_timeoff_dates_are_valid(self):
        """Verify time-off records have valid date ranges (end >= start)."""
        response = _load_mock_tool_response(
            "sap-sf-time-off",
            "list_employeetime_for_sfodata"
        )
        for record in response["d"]["results"]:
            start = record["startDate"]
            end = record["endDate"]
            # Extract epoch milliseconds from /Date(...)/ format
            start_ms = int(start.replace("/Date(", "").replace(")/", ""))
            end_ms = int(end.replace("/Date(", "").replace(")/", ""))
            assert end_ms >= start_ms, f"End date must be >= start date for record {record['externalCode']}"

    def test_timeoff_quantity_is_positive(self):
        """Verify time-off duration in days is positive."""
        response = _load_mock_tool_response(
            "sap-sf-time-off",
            "list_employeetime_for_sfodata"
        )
        for record in response["d"]["results"]:
            assert record["quantityInDays"] > 0, "Time-off duration must be positive"

    def test_multiple_employees_have_timeoff(self):
        """Verify time-off data covers multiple employees."""
        response = _load_mock_tool_response(
            "sap-sf-time-off",
            "list_employeetime_for_sfodata"
        )
        user_ids = {r["userId"] for r in response["d"]["results"]}
        assert len(user_ids) >= 2, "Should have time-off data for at least 2 employees"

    def test_employee_with_timeoff_appears_in_availability(self):
        """Verify at least one employee with time-off also appears in availability data."""
        mock_path = Path(__file__).parent.parent / "mcp-mock.json"
        with open(mock_path) as f:
            mock_data = json.load(f)

        timeoff_records = mock_data["servers"]["sap-sf-time-off"]["tools"][
            "list_employeetime_for_sfodata"
        ]["mock_response"]["d"]["results"]
        timeoff_ids = {r["userId"] for r in timeoff_records}

        avail_records = mock_data["servers"]["sap-s4-workforce-daily-availability"]["tools"][
            "list_timeoverviewset_for_shcm_api_manage_wf_availability"
        ]["mock_response"]["d"]["results"]
        avail_ids = {r["Personworkagreementexternalid"] for r in avail_records}

        overlap = timeoff_ids & avail_ids
        assert len(overlap) >= 1, (
            "At least one employee with time-off must appear in availability data "
            "to test conflict detection"
        )

    @pytest.mark.asyncio
    async def test_filter_by_date_range_and_user(self):
        """Test querying time-off data filtered by date range and user ID."""
        response = _load_mock_tool_response(
            "sap-sf-time-off",
            "list_employeetime_for_sfodata"
        )
        tool = _make_mock_tool("list_employeetime_for_sfodata", response)
        result = await tool.ainvoke({
            "filter": "userId eq 'EMP003' and startDate ge datetime'2025-03-01T00:00:00' and approvalStatus eq 'APPROVED'"
        })
        result_data = json.loads(result)
        assert "d" in result_data

    def test_timeoff_type_is_meaningful(self):
        """Verify time-off types are recognizable leave categories."""
        response = _load_mock_tool_response(
            "sap-sf-time-off",
            "list_employeetime_for_sfodata"
        )
        valid_types = {"VACATION", "SICK_LEAVE", "PERSONAL", "MATERNITY", "PATERNITY",
                       "BEREAVEMENT", "JURY_DUTY", "UNPAID_LEAVE", "TRAINING"}
        for record in response["d"]["results"]:
            assert record["timeType"] in valid_types, (
                f"Unexpected time-off type: {record['timeType']}"
            )
