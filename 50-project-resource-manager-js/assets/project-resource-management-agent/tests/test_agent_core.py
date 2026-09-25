"""Unit tests for the core agent module — covers decorators, instrumentation, and AgentResponse."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

APP_PATH = str(Path(__file__).parent.parent / "app")
if APP_PATH not in sys.path:
    sys.path.insert(0, APP_PATH)


class TestAgentDecorators:
    """Tests that the 9 expected decorated functions exist in agent.py."""

    def test_exactly_nine_decorated_functions(self):
        """Verify agent.py has exactly 9 decorated functions (@agent_model, @agent_config, @prompt_section)."""
        agent_path = Path(__file__).parent.parent / "app" / "agent.py"
        content = agent_path.read_text()
        count = sum(1 for line in content.splitlines()
                    if line.startswith("@agent_model") or 
                       line.startswith("@agent_config") or 
                       line.startswith("@prompt_section"))
        assert count == 9, f"Expected 9 decorated functions, found {count}"

    def test_get_model_name_returns_string(self):
        """Verify get_model_name returns a non-empty string."""
        from agent import get_model_name
        result = get_model_name()
        assert isinstance(result, str)
        assert len(result) > 0
        assert "claude" in result.lower() or "gpt" in result.lower() or "sap" in result.lower()

    def test_get_temperature_returns_float(self):
        """Verify temperature is a valid float between 0 and 1."""
        from agent import get_temperature
        result = get_temperature()
        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0

    def test_thread_ttl_is_positive(self):
        """Verify thread TTL is positive."""
        from agent import thread_ttl_seconds
        result = thread_ttl_seconds()
        assert isinstance(result, int)
        assert result > 0

    def test_summarization_trigger_is_large(self):
        """Verify summarization trigger is a reasonable token count."""
        from agent import summarization_trigger_tokens
        result = summarization_trigger_tokens()
        assert isinstance(result, int)
        assert result >= 10_000

    def test_circuit_breaker_threshold_is_non_negative(self):
        """Verify circuit breaker threshold is non-negative."""
        from agent import get_circuit_breaker_failure_threshold
        result = get_circuit_breaker_failure_threshold()
        assert isinstance(result, int)
        assert result >= 0

    def test_fallback_model_names_is_string(self):
        """Verify fallback model names returns a string (can be empty)."""
        from agent import get_fallback_model_names
        result = get_fallback_model_names()
        assert isinstance(result, str)

    def test_summarization_model_is_string(self):
        """Verify summarization model name is a non-empty string."""
        from agent import get_summarization_model_name
        result = get_summarization_model_name()
        assert isinstance(result, str)
        assert len(result) > 0


class TestAgentResponse:
    """Tests for the AgentResponse dataclass."""

    def test_agent_response_completed(self):
        """Verify AgentResponse can be created with completed status."""
        from agent import AgentResponse
        response = AgentResponse(status="completed", message="Task done")
        assert response.status == "completed"
        assert response.message == "Task done"

    def test_agent_response_input_required(self):
        """Verify AgentResponse can be created with input_required status."""
        from agent import AgentResponse
        response = AgentResponse(status="input_required", message="Need confirmation")
        assert response.status == "input_required"
        assert "confirmation" in response.message.lower()

    def test_agent_response_error(self):
        """Verify AgentResponse can be created with error status."""
        from agent import AgentResponse
        response = AgentResponse(status="error", message="Something went wrong")
        assert response.status == "error"


class TestSystemPrompt:
    """Tests for the system prompt content."""

    def test_system_prompt_is_non_empty(self):
        """Verify system prompt returns meaningful content."""
        from agent import get_system_prompt
        prompt = get_system_prompt()
        assert isinstance(prompt, str)
        assert len(prompt) > 200

    def test_system_prompt_mentions_s4hana(self):
        """Verify system prompt mentions SAP S/4HANA."""
        from agent import get_system_prompt
        prompt = get_system_prompt()
        assert "S/4HANA" in prompt or "s4hana" in prompt.lower() or "SAP" in prompt

    def test_system_prompt_mentions_successfactors(self):
        """Verify system prompt mentions SAP SuccessFactors."""
        from agent import get_system_prompt
        prompt = get_system_prompt()
        assert "SuccessFactors" in prompt or "successfactors" in prompt.lower()

    def test_system_prompt_has_assignment_guardrail(self):
        """Verify system prompt has the assignment confirmation guardrail."""
        from agent import get_system_prompt
        prompt = get_system_prompt()
        assert "confirm" in prompt.lower() or "NEVER" in prompt or "CRITICAL" in prompt

    def test_system_prompt_has_data_integrity_instruction(self):
        """Verify system prompt instructs agent not to fabricate data."""
        from agent import get_system_prompt
        prompt = get_system_prompt()
        assert "fabricate" in prompt.lower() or "invent" in prompt.lower() or "Never" in prompt

    def test_system_prompt_has_page_size_instruction(self):
        """Verify system prompt instructs agent to limit pagination."""
        from agent import get_system_prompt
        prompt = get_system_prompt()
        assert "100" in prompt or "pagination" in prompt.lower() or "PAGE SIZE" in prompt

    def test_security_suffix_appended(self):
        """Verify the defensive prompt suffix is appended."""
        from agent import get_system_prompt
        prompt = get_system_prompt()
        assert "Tool Results" in prompt or "Security" in prompt or "external data" in prompt.lower()


class TestMilestoneInstrumentation:
    """Tests for business milestone logging functions."""

    def test_log_milestone_outcomes_m1(self):
        """Verify M1 milestone is logged for project-related queries."""
        from agent import _log_milestone_outcomes
        import logging

        with patch("agent.logger") as mock_logger:
            _log_milestone_outcomes("show me active projects", "Here are 3 projects from S/4HANA Cloud")
            mock_logger.info.assert_called()
            call_args = str(mock_logger.info.call_args_list)
            assert "M1" in call_args

    def test_log_milestone_outcomes_m2(self):
        """Verify M2 milestone is logged for demand-related queries."""
        from agent import _log_milestone_outcomes

        with patch("agent.logger") as mock_logger:
            _log_milestone_outcomes("show resource demands", "Found 2 open demands for project")
            mock_logger.info.assert_called()

    def test_log_milestone_outcomes_m5_achieved(self):
        """Verify M5 achieved milestone is logged after successful assignment."""
        from agent import _log_milestone_outcomes

        with patch("agent.logger") as mock_logger:
            _log_milestone_outcomes(
                "assign and confirm",
                "Assignment successfully created. Assignment ID: d1e2f3a4-0001"
            )
            mock_logger.info.assert_called()
            call_args_str = str(mock_logger.info.call_args_list)
            assert "M5" in call_args_str

    def test_log_milestone_outcomes_m5_missed(self):
        """Verify M5 missed milestone is logged when assignment fails."""
        from agent import _log_milestone_outcomes

        with patch("agent.logger") as mock_logger:
            _log_milestone_outcomes(
                "assign and confirm",
                "Assignment failed. API Error: 400 Bad Request"
            )
            mock_logger.info.assert_called()

    def test_run_agent_instrumentation_is_defined(self):
        """Verify the instrumentation helper function exists."""
        from agent import _run_agent_with_instrumentation
        assert callable(_run_agent_with_instrumentation)


class TestSampleAgent:
    """Tests for the SampleAgent class initialization."""

    def test_sample_agent_can_be_instantiated(self):
        """Verify SampleAgent can be created (no network calls in __init__)."""
        from agent import SampleAgent
        with patch("agent.create_checkpointer"), patch("agent.ChatLiteLLM"):
            agent = SampleAgent()
            assert agent is not None
            assert hasattr(agent, "stream")
            assert hasattr(agent, "invoke")

    def test_sample_agent_has_expected_attributes(self):
        """Verify SampleAgent has all required attributes."""
        from agent import SampleAgent
        with patch("agent.create_checkpointer"), patch("agent.ChatLiteLLM"):
            agent = SampleAgent()
            assert hasattr(agent, "_primary_model")
            assert hasattr(agent, "_temperature")
            assert hasattr(agent, "_model_chain")
            assert hasattr(agent, "llm")
            assert hasattr(agent, "_checkpointer")

    def test_sample_agent_supported_content_types(self):
        """Verify SampleAgent declares supported content types."""
        from agent import SampleAgent
        assert hasattr(SampleAgent, "SUPPORTED_CONTENT_TYPES")
        assert "text" in SampleAgent.SUPPORTED_CONTENT_TYPES

    @pytest.mark.asyncio
    async def test_stream_returns_processing_first(self):
        """Verify stream() yields a 'Processing...' message as first chunk."""
        from agent import SampleAgent

        with patch("agent.create_checkpointer"), patch("agent.ChatLiteLLM"):
            agent = SampleAgent()

        # Mock the invoke_with_fallback to return a canned response
        mock_result = {"messages": [MagicMock(content="Here are your active projects.")]}
        with patch.object(agent, "_invoke_with_fallback", new=AsyncMock(return_value=mock_result)):
            chunks = []
            async for chunk in agent.stream("show me active projects", "test-session-1"):
                chunks.append(chunk)

        assert len(chunks) >= 2
        assert chunks[0]["is_task_complete"] is False
        assert chunks[0]["content"] == "Processing..."

    @pytest.mark.asyncio
    async def test_stream_completes_with_is_task_complete_true(self):
        """Verify stream() final chunk has is_task_complete=True."""
        from agent import SampleAgent

        with patch("agent.create_checkpointer"), patch("agent.ChatLiteLLM"):
            agent = SampleAgent()

        mock_result = {"messages": [MagicMock(content="Here are 2 active projects in S/4HANA Cloud.")]}
        with patch.object(agent, "_invoke_with_fallback", new=AsyncMock(return_value=mock_result)):
            chunks = []
            async for chunk in agent.stream("show me active projects", "test-session-2", tools=[]):
                chunks.append(chunk)

        last = chunks[-1]
        assert last["is_task_complete"] is True
        assert "project" in last["content"].lower() or len(last["content"]) > 0

    @pytest.mark.asyncio
    async def test_stream_handles_exception_gracefully(self):
        """Verify stream() returns error message when agent fails."""
        from agent import SampleAgent

        with patch("agent.create_checkpointer"), patch("agent.ChatLiteLLM"):
            agent = SampleAgent()

        with patch.object(agent, "_invoke_with_fallback", new=AsyncMock(side_effect=RuntimeError("Test error"))):
            chunks = []
            async for chunk in agent.stream("test query", "test-session-3", tools=[]):
                chunks.append(chunk)

        last = chunks[-1]
        assert last["is_task_complete"] is True
        assert "error" in last["content"].lower()

    @pytest.mark.asyncio
    async def test_invoke_returns_agent_response(self):
        """Verify invoke() returns an AgentResponse object."""
        from agent import SampleAgent, AgentResponse

        with patch("agent.create_checkpointer"), patch("agent.ChatLiteLLM"):
            agent = SampleAgent()

        mock_result = {"messages": [MagicMock(content="Found 2 open resource demands.")]}
        with patch.object(agent, "_invoke_with_fallback", new=AsyncMock(return_value=mock_result)):
            response = await agent.invoke("show demands for project", "test-session-4", tools=[])

        assert isinstance(response, AgentResponse)
        assert response.status == "completed"
        assert "demand" in response.message.lower()
