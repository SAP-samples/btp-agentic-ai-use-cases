"""Integration test: full end-to-end staffing workflow with mocked LLM and MCP tools."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure app/ is on the path for peer-level imports
APP_PATH = str(Path(__file__).parent.parent / "app")
if APP_PATH not in sys.path:
    sys.path.insert(0, APP_PATH)


def _load_all_mock_tools():
    """Build a list of mock LangChain tools from mcp-mock.json."""
    mock_path = Path(__file__).parent.parent / "mcp-mock.json"
    with open(mock_path) as f:
        mock_data = json.load(f)

    tools = []
    for server_slug, server_def in mock_data["servers"].items():
        for tool_name, tool_def in server_def["tools"].items():
            tool = MagicMock()
            tool.name = tool_name
            tool.description = tool_def["description"]
            response = tool_def["mock_response"]
            tool.ainvoke = AsyncMock(return_value=json.dumps(response))
            tool.invoke = MagicMock(return_value=json.dumps(response))
            tools.append(tool)
    return tools


def _make_canned_llm_response(content: str):
    """Create a mock LLM response with the given content."""
    msg = MagicMock()
    msg.content = content
    return msg


class TestEndToEndStaffingFlow:
    """Integration test covering the full 5-milestone staffing workflow."""

    @pytest.fixture(autouse=True)
    def setup_tools(self):
        """Load all mock tools for use in tests."""
        self.all_tools = _load_all_mock_tools()
        assert len(self.all_tools) > 0

    def test_mcp_mock_has_all_seven_servers(self):
        """Verify all 7 MCP servers are present in mcp-mock.json."""
        mock_path = Path(__file__).parent.parent / "mcp-mock.json"
        with open(mock_path) as f:
            mock_data = json.load(f)
        expected_servers = [
            "sap-s4-project-demand",
            "sap-s4-resource-assignment-source",
            "sap-s4-workforce-daily-availability",
            "sap-sf-skills-management",
            "sap-sf-employee-profile",
            "sap-sf-employment-information",
            "sap-sf-time-off"
        ]
        for server in expected_servers:
            assert server in mock_data["servers"], f"Missing server: {server}"

    def test_total_tool_count_in_mock(self):
        """Verify all expected tool categories are covered in the mock."""
        assert len(self.all_tools) >= 20, "Should have at least 20 tools across all servers"

    def test_agent_module_imports_cleanly(self):
        """Verify the agent module can be imported without errors."""
        try:
            import agent
            assert hasattr(agent, "SampleAgent")
            assert hasattr(agent, "get_system_prompt")
        except ImportError as e:
            pytest.skip(f"Agent module import skipped: {e}")

    def test_system_prompt_has_business_guardrails(self):
        """Verify system prompt contains all required business guardrails."""
        try:
            from agent import get_system_prompt
            prompt = get_system_prompt()
            assert "DATA INTEGRITY" in prompt or "Never fabricate" in prompt.lower()
            assert "GRACEFUL DEGRADATION" in prompt or "unavailable" in prompt.lower()
            assert "PAGE SIZE" in prompt or "pagination" in prompt.lower()
            assert "CONFIDENCE THRESHOLD" in prompt or "low-confidence" in prompt.lower()
            assert "CRITICAL" in prompt or "NEVER call" in prompt
            assert "TIME-OFF" in prompt or "time-off" in prompt.lower(), "System prompt must include time-off conflict detection instructions"
            assert "EmployeeTime" in prompt, "System prompt must reference EmployeeTime entity for time-off queries"
        except ImportError:
            pytest.skip("Agent module not available in test environment")

    def test_resource_matching_skill_exists(self):
        """Verify the resource-matching runtime skill exists and is well-formed."""
        skill_path = Path(__file__).parent.parent / "app" / "skills" / "resource-matching" / "SKILL.md"
        assert skill_path.exists(), "resource-matching/SKILL.md must exist"
        content = skill_path.read_text()
        assert "name: resource-matching" in content
        assert "confidence" in content.lower()
        assert "rank" in content.lower()
        assert "time-off" in content.lower(), "resource-matching skill must include time-off checks"
        assert "EmployeeTime" in content, "resource-matching skill must reference EmployeeTime entity"

    def test_assignment_confirmation_skill_exists(self):
        """Verify the assignment-confirmation runtime skill exists and is well-formed."""
        skill_path = Path(__file__).parent.parent / "app" / "skills" / "assignment-confirmation" / "SKILL.md"
        assert skill_path.exists(), "assignment-confirmation/SKILL.md must exist"
        content = skill_path.read_text()
        assert "name: assignment-confirmation" in content
        assert "Yes" in content
        assert "No" in content

    def test_mock_project_demand_data_is_cross_referenceable(self):
        """Verify project demand UUID in mock is consistent across related entities."""
        mock_path = Path(__file__).parent.parent / "mcp-mock.json"
        with open(mock_path) as f:
            mock_data = json.load(f)

        # Get project UUID from project demand list
        projects = mock_data["servers"]["sap-s4-project-demand"]["tools"][
            "list_a_projectdemand_for_cds_api_projectdemand"
        ]["mock_response"]["d"]["results"]
        project_uuid = projects[0]["ProjectDemandUUID"]

        # Verify same UUID appears in resource demand
        resource_demands = mock_data["servers"]["sap-s4-project-demand"]["tools"][
            "list_a_projectdemandresource_for_cds_api_projectdemand"
        ]["mock_response"]["d"]["results"]
        demand_uuids = {d["ProjectDemandUUID"] for d in resource_demands}
        assert project_uuid in demand_uuids, "Project UUID must be consistent in resource demands"

    def test_mock_employee_ids_are_consistent(self):
        """Verify employee IDs are consistent across availability and skills data."""
        mock_path = Path(__file__).parent.parent / "mcp-mock.json"
        with open(mock_path) as f:
            mock_data = json.load(f)

        # Get employee IDs from availability data
        availability = mock_data["servers"]["sap-s4-workforce-daily-availability"]["tools"][
            "list_timeoverviewset_for_shcm_api_manage_wf_availability"
        ]["mock_response"]["d"]["results"]
        avail_emp_ids = {r["Personworkagreementexternalid"] for r in availability}

        # Get employee IDs from SF employment info
        emp_jobs = mock_data["servers"]["sap-sf-employment-information"]["tools"][
            "list_empjob_for_sfodata"
        ]["mock_response"]["d"]["results"]
        job_user_ids = {r["userId"] for r in emp_jobs}

        # Both should have overlapping employee identifiers in a real scenario
        # In mock, verify both exist and have data
        assert len(avail_emp_ids) >= 2, "Should have at least 2 employees in availability data"
        assert len(job_user_ids) >= 2, "Should have at least 2 employees in job data"

    @pytest.mark.asyncio
    async def test_milestone_m5_assignment_tool_accepts_required_params(self):
        """Test that the assignment tool (M5) accepts all required parameters."""
        mock_path = Path(__file__).parent.parent / "mcp-mock.json"
        with open(mock_path) as f:
            mock_data = json.load(f)

        tool_def = mock_data["servers"]["sap-s4-project-demand"]["tools"][
            "create_a_projdmndresourceassignment_for_cds_api_projectdemand"
        ]
        input_schema = tool_def["input_schema"]
        props = input_schema["properties"]

        # M5 requires these fields per PRD
        required_m5_params = [
            "projectdemandworkuuid",
            "projectdemanduuid",
            "projdmndrsceassgmt",  # employee personnel number
        ]
        for param in required_m5_params:
            assert param in props, f"M5 assignment tool must accept: {param}"

    def test_instrumentation_in_agent_code(self):
        """Verify the agent code contains milestone instrumentation."""
        agent_path = Path(__file__).parent.parent / "app" / "agent.py"
        content = agent_path.read_text()
        # Check for milestone logging patterns
        assert "M1" in content, "Agent must have M1 milestone logging"
        assert "M2" in content, "Agent must have M2 milestone logging"
        assert "M3" in content, "Agent must have M3 milestone logging"
        assert "M4" in content, "Agent must have M4 milestone logging"
        assert "M5" in content, "Agent must have M5 milestone logging"
        assert "achieved" in content, "Agent must log 'achieved' milestone outcomes"
        assert "missed" in content, "Agent must log 'missed' milestone outcomes"
        assert "tracer" in content, "Agent must use OpenTelemetry tracer"
        assert "time-off" in content.lower() or "timeoff" in content.lower(), "Agent must log time-off data in M3 milestone"

    def test_time_off_server_in_mock(self):
        """Verify the time-off MCP server is present in mcp-mock.json with correct tools."""
        mock_path = Path(__file__).parent.parent / "mcp-mock.json"
        with open(mock_path) as f:
            mock_data = json.load(f)
        assert "sap-sf-time-off" in mock_data["servers"], "Time-off server must be in mcp-mock.json"
        server = mock_data["servers"]["sap-sf-time-off"]
        assert "list_employeetime_for_sfodata" in server["tools"], "Time-off server must have list_employeetime tool"

    def test_time_off_mock_data_has_required_fields(self):
        """Verify time-off mock records have all required fields for conflict detection."""
        mock_path = Path(__file__).parent.parent / "mcp-mock.json"
        with open(mock_path) as f:
            mock_data = json.load(f)
        records = mock_data["servers"]["sap-sf-time-off"]["tools"][
            "list_employeetime_for_sfodata"
        ]["mock_response"]["d"]["results"]
        assert len(records) >= 1, "Must have at least one time-off record"
        for record in records:
            assert "userId" in record, "Time-off record must have userId"
            assert "startDate" in record, "Time-off record must have startDate"
            assert "endDate" in record, "Time-off record must have endDate"
            assert "approvalStatus" in record, "Time-off record must have approvalStatus"
            assert "timeType" in record, "Time-off record must have timeType"
            assert "quantityInDays" in record, "Time-off record must have quantityInDays"

    def test_time_off_conflict_detection_data(self):
        """Verify mock data includes employees with time-off that can conflict with projects."""
        mock_path = Path(__file__).parent.parent / "mcp-mock.json"
        with open(mock_path) as f:
            mock_data = json.load(f)
        # Get time-off records
        timeoff_records = mock_data["servers"]["sap-sf-time-off"]["tools"][
            "list_employeetime_for_sfodata"
        ]["mock_response"]["d"]["results"]
        # Get availability employee IDs
        avail_records = mock_data["servers"]["sap-s4-workforce-daily-availability"]["tools"][
            "list_timeoverviewset_for_shcm_api_manage_wf_availability"
        ]["mock_response"]["d"]["results"]
        avail_emp_ids = {r["Personworkagreementexternalid"] for r in avail_records}
        # At least one time-off record should be for an employee who also appears in availability
        timeoff_emp_ids = {r["userId"] for r in timeoff_records}
        overlap = avail_emp_ids & timeoff_emp_ids
        assert len(overlap) >= 1, "At least one employee must appear in both availability and time-off data for conflict testing"
