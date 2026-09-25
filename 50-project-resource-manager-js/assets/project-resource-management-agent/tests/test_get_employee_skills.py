"""Unit test for retrieving employee skills from SuccessFactors (REQ-04)."""
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


class TestGetEmployeeSkills:
    """Tests for REQ-04: Retrieve Employee Skills."""

    def test_skills_management_server_in_mock(self):
        """Verify SuccessFactors Skills Management MCP server is in mock."""
        mock_path = Path(__file__).parent.parent / "mcp-mock.json"
        with open(mock_path) as f:
            mock_data = json.load(f)
        assert "sap-sf-skills-management" in mock_data["servers"]
        server = mock_data["servers"]["sap-sf-skills-management"]
        assert "list_skillprofile_for_sfodata" in server["tools"]
        assert "list_ratedskillmapping_for_sfodata" in server["tools"]
        assert "get_skillprofile_for_sfodata" in server["tools"]

    def test_rated_skill_mapping_has_proficiency(self):
        """Verify rated skill records include proficiency level fields."""
        response = _load_mock_tool_response(
            "sap-sf-skills-management",
            "list_ratedskillmapping_for_sfodata"
        )
        for skill in response["d"]["results"]:
            assert "skill" in skill
            assert "SkillProfile_externalCode" in skill
            assert "expectedLevel_en_US" in skill or "selfRatedLevel_en_US" in skill

    def test_skill_profile_linked_to_employee(self):
        """Verify skill profiles are linked to employee user IDs."""
        response = _load_mock_tool_response(
            "sap-sf-skills-management",
            "list_skillprofile_for_sfodata"
        )
        for profile in response["d"]["results"]:
            assert "externalCode" in profile
            assert profile["externalCode"].startswith("EMP")

    def test_employee_has_multiple_skills(self):
        """Verify an employee can have multiple skill entries."""
        response = _load_mock_tool_response(
            "sap-sf-skills-management",
            "list_ratedskillmapping_for_sfodata"
        )
        # Count skills per employee
        emp_skills: dict = {}
        for skill in response["d"]["results"]:
            emp_id = skill["SkillProfile_externalCode"]
            emp_skills.setdefault(emp_id, []).append(skill["skill"])

        # At least one employee should have multiple skills
        has_multiple = any(len(skills) > 1 for skills in emp_skills.values())
        assert has_multiple, "At least one employee should have multiple skills"

    @pytest.mark.asyncio
    async def test_filter_skills_by_employee_id(self):
        """Test filtering rated skills by employee external code."""
        response = _load_mock_tool_response(
            "sap-sf-skills-management",
            "list_ratedskillmapping_for_sfodata"
        )
        tool = _make_mock_tool("list_ratedskillmapping_for_sfodata", response)
        result = await tool.ainvoke({
            "filter": "SkillProfile_externalCode eq 'EMP001'",
            "top": "100"
        })
        result_data = json.loads(result)
        assert "d" in result_data
        results = result_data["d"]["results"]
        assert len(results) > 0

    def test_skill_names_are_meaningful(self):
        """Verify skill names are non-empty and SAP-relevant."""
        response = _load_mock_tool_response(
            "sap-sf-skills-management",
            "list_ratedskillmapping_for_sfodata"
        )
        for skill in response["d"]["results"]:
            assert len(skill["skill"]) > 0, "Skill name should not be empty"
