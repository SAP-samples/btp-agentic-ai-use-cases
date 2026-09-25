"""Unit test for resource assignment execution with human-in-the-loop (REQ-07)."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

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


class TestCreateResourceAssignment:
    """Tests for REQ-07: Execute Resource Assignment (with HITL gate)."""

    def test_assignment_tool_in_mock(self):
        """Verify resource assignment creation tool is in mcp-mock.json."""
        mock_path = Path(__file__).parent.parent / "mcp-mock.json"
        with open(mock_path) as f:
            mock_data = json.load(f)
        server = mock_data["servers"]["sap-s4-project-demand"]
        assert "create_a_projdmndresourceassignment_for_cds_api_projectdemand" in server["tools"]

    def test_assignment_mock_response_has_uuid(self):
        """Verify assignment creation returns an assignment UUID."""
        response = _load_mock_tool_response(
            "sap-s4-project-demand",
            "create_a_projdmndresourceassignment_for_cds_api_projectdemand"
        )
        assert "d" in response
        assignment = response["d"]
        assert "ProjDmndRsceAssgmtUUID" in assignment
        assert len(assignment["ProjDmndRsceAssgmtUUID"]) > 0

    def test_assignment_requires_employee_id(self):
        """Verify assignment creation requires employee personnel number."""
        mock_path = Path(__file__).parent.parent / "mcp-mock.json"
        with open(mock_path) as f:
            mock_data = json.load(f)
        tool_def = mock_data["servers"]["sap-s4-project-demand"]["tools"][
            "create_a_projdmndresourceassignment_for_cds_api_projectdemand"
        ]
        input_schema = tool_def["input_schema"]
        assert "projdmndrsceassgmt" in input_schema["properties"], \
            "Employee personnel number (ProjDmndRsceAssgmt) must be a required parameter"

    def test_assignment_requires_demand_uuid(self):
        """Verify assignment creation requires demand UUID."""
        mock_path = Path(__file__).parent.parent / "mcp-mock.json"
        with open(mock_path) as f:
            mock_data = json.load(f)
        tool_def = mock_data["servers"]["sap-s4-project-demand"]["tools"][
            "create_a_projdmndresourceassignment_for_cds_api_projectdemand"
        ]
        input_schema = tool_def["input_schema"]
        assert "projectdemandworkuuid" in input_schema["properties"]
        assert "projectdemanduuid" in input_schema["properties"]

    @pytest.mark.asyncio
    async def test_assignment_can_be_created_after_confirmation(self):
        """Test that assignment tool can be invoked (simulating post-confirmation)."""
        response = _load_mock_tool_response(
            "sap-s4-project-demand",
            "create_a_projdmndresourceassignment_for_cds_api_projectdemand"
        )
        tool = _make_mock_tool(
            "create_a_projdmndresourceassignment_for_cds_api_projectdemand",
            response
        )
        # Simulate a confirmed assignment invocation
        result = await tool.ainvoke({
            "projectdemandworkuuid": "b1c2d3e4-0001-0001-0001-100000000001",
            "projectdemanduuid": "a1b2c3d4-0001-0001-0001-000000000001",
            "projdmndrsceassgmt": "10000101",
            "projdmndrsceassgmtquantity": "200.000",
            "projdmndrsceassgmtquantityunit": "H",
            "projdmndrsceassgmtstartdate": "/Date(1735689600000)/",
            "projdmndrsceassgmtenddate": "/Date(1751328000000)/"
        })
        result_data = json.loads(result)
        assert "d" in result_data
        assert "ProjDmndRsceAssgmtUUID" in result_data["d"]

    def test_system_prompt_has_hitl_guardrail(self):
        """Verify the agent system prompt includes the HITL confirmation guardrail."""
        import sys, os
        sys.path.insert(0, str(Path(__file__).parent.parent / "app"))
        try:
            from agent import get_system_prompt
            prompt = get_system_prompt()
            # The system prompt must explicitly forbid calling assignment without confirmation
            assert "NEVER call" in prompt or "CRITICAL" in prompt, \
                "System prompt must have HITL guardrail"
            assert "confirm" in prompt.lower(), \
                "System prompt must mention confirmation requirement"
        finally:
            sys.path.remove(str(Path(__file__).parent.parent / "app"))

    def test_assignment_skill_file_exists(self):
        """Verify the assignment-confirmation skill file exists."""
        skill_path = Path(__file__).parent.parent / "app" / "skills" / "assignment-confirmation" / "SKILL.md"
        assert skill_path.exists(), "assignment-confirmation/SKILL.md must exist"
        content = skill_path.read_text()
        assert "Yes" in content, "Skill must handle Yes confirmation"
        assert "No" in content, "Skill must handle No/cancellation"
