"""Tests for agent server startup and A2A endpoints."""

import json
import urllib.error
import urllib.request

import pytest


@pytest.mark.server
class TestServerStartup:
    """Test that the agent server starts correctly."""

    def test_server_starts(self, start_agent):
        """Test that the server starts without errors."""
        # If we get here, the running_server fixture successfully started the server
        assert start_agent["process"].poll() is None, "Server process should be running"
        assert start_agent["port"] > 0, "Server should have a valid port"


@pytest.mark.server
class TestA2AEndpoints:
    """Test A2A protocol endpoints."""

    def test_agent_card_endpoint(self, start_agent):
        """Test that the agent card endpoint is accessible and returns valid JSON."""
        port = start_agent["port"]
        url = f"http://localhost:{port}/.well-known/agent-card.json"

        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                raw = resp.read().decode()
                status = resp.status
        except urllib.error.URLError as e:
            pytest.fail(f"Could not connect to server on port {port}: {e}")

        # Check status code
        assert status == 200, f"Agent card endpoint returned status {status}"

        # Parse and validate JSON
        try:
            card_data = json.loads(raw)
        except ValueError as e:
            pytest.fail(
                f"Agent card endpoint returned invalid JSON: {e}\nResponse text: {raw[:200]}"
            )

        # Validate it's a proper agent card with required fields
        assert "name" in card_data or "agentName" in card_data, (
            "Agent card should have a 'name' or 'agentName' field"
        )

        name = card_data.get("name") or card_data.get("agentName", "unknown")
        description = card_data.get("description", "")
        skills = card_data.get("skills") or []
        skill_names = [s.get("name", s.get("id", "?")) for s in skills]
        print(
            "\n--- Agent card ---\nname: {}\ndescription: {}\nskills: {}\n------------------".format(
                name, description, ", ".join(skill_names) if skill_names else "(none)"
            )
        )
