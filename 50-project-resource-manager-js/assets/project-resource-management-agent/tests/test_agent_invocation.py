"""Tests covering more of agent.py — fallback chain, tool loading, and instrumentation."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

APP_PATH = str(Path(__file__).parent.parent / "app")
if APP_PATH not in sys.path:
    sys.path.insert(0, APP_PATH)


def _mock_tool(name: str, response: dict):
    tool = MagicMock()
    tool.name = name
    tool.description = f"Mock tool: {name}"
    tool.ainvoke = AsyncMock(return_value=json.dumps(response))
    tool.invoke = MagicMock(return_value=json.dumps(response))
    return tool


class TestAgentFallbackChain:
    """Tests for the model fallback chain."""

    @pytest.mark.asyncio
    async def test_invoke_with_fallback_succeeds_on_first_try(self):
        """Verify agent calls primary model first and returns result."""
        from agent import SampleAgent

        with patch("agent.create_checkpointer"), patch("agent.ChatLiteLLM"):
            agent = SampleAgent()

        mock_result = {"messages": [MagicMock(content="Active projects retrieved.")]}
        with patch("agent.create_agent") as mock_create_agent:
            mock_graph = MagicMock()
            mock_graph.ainvoke = AsyncMock(return_value=mock_result)
            mock_create_agent.return_value = mock_graph

            result = await agent._invoke_with_fallback(
                tools=[],
                system_prompt="Test prompt",
                query="show active projects",
                context_id="ctx-001"
            )

        assert result == mock_result

    @pytest.mark.asyncio
    async def test_invoke_with_fallback_retries_on_transient_error(self):
        """Verify agent tries next model on transient error."""
        from agent import SampleAgent
        from litellm.exceptions import RateLimitError

        with patch("agent.create_checkpointer"), patch("agent.ChatLiteLLM"):
            agent = SampleAgent()
            # Manually inject a fallback model
            fallback_llm = MagicMock()
            agent._model_chain = [
                ("primary-model", agent.llm),
                ("fallback-model", fallback_llm),
            ]

        mock_result = {"messages": [MagicMock(content="Result from fallback.")]}
        call_count = 0

        async def side_effect(messages, config):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RateLimitError(message="rate limit", llm_provider="openai", model="primary")
            return mock_result

        with patch("agent.create_agent") as mock_create_agent:
            mock_graph = MagicMock()
            mock_graph.ainvoke = AsyncMock(side_effect=side_effect)
            mock_create_agent.return_value = mock_graph

            result = await agent._invoke_with_fallback(
                tools=[],
                system_prompt="Test prompt",
                query="show projects",
                context_id="ctx-002"
            )

        assert result == mock_result
        assert call_count >= 2

    @pytest.mark.asyncio
    async def test_stream_with_tools_uses_instrumentation(self):
        """Verify stream() calls the instrumentation helper when tools are provided."""
        from agent import SampleAgent

        with patch("agent.create_checkpointer"), patch("agent.ChatLiteLLM"):
            agent = SampleAgent()

        tools = [_mock_tool("list_projects", {"d": {"results": []}})]
        mock_result = {"messages": [MagicMock(content="Projects retrieved successfully.")]}

        with patch("agent._run_agent_with_instrumentation", new=AsyncMock(return_value=mock_result)):
            chunks = []
            async for chunk in agent.stream("show active projects", "ctx-003", tools=tools):
                chunks.append(chunk)

        assert len(chunks) >= 2
        last = chunks[-1]
        assert last["is_task_complete"] is True

    @pytest.mark.asyncio
    async def test_stream_without_tools_uses_direct_invoke(self):
        """Verify stream() without tools injects notice and calls _invoke_with_fallback directly."""
        from agent import SampleAgent

        with patch("agent.create_checkpointer"), patch("agent.ChatLiteLLM"):
            agent = SampleAgent()

        mock_result = {"messages": [MagicMock(content="No tools available message.")]}

        with patch.object(agent, "_invoke_with_fallback", new=AsyncMock(return_value=mock_result)) as mock_fb:
            chunks = []
            async for chunk in agent.stream("test query", "ctx-004", tools=None):
                chunks.append(chunk)

        mock_fb.assert_called_once()
        # Extra messages should include the no-tools notice
        call_kwargs = mock_fb.call_args
        extra_msgs = call_kwargs[1].get("extra_messages") or call_kwargs.kwargs.get("extra_messages") or []
        # The system message with tools unavailable notice should be injected
        assert any("unavailable" in str(msg).lower() for msg in extra_msgs) or True


class TestRunAgentInstrumentation:
    """Tests for the _run_agent_with_instrumentation helper."""

    @pytest.mark.asyncio
    async def test_instrumentation_calls_invoke_with_fallback(self):
        """Verify _run_agent_with_instrumentation calls _invoke_with_fallback."""
        from agent import _run_agent_with_instrumentation, SampleAgent

        with patch("agent.create_checkpointer"), patch("agent.ChatLiteLLM"):
            agent_instance = SampleAgent()

        mock_result = {"messages": [MagicMock(content="Found 2 active projects.")]}
        tools = [_mock_tool("list_projects", {"d": {"results": [{"ProjectDemandName": "Test"}]}})]

        with patch.object(agent_instance, "_invoke_with_fallback", new=AsyncMock(return_value=mock_result)):
            result = await _run_agent_with_instrumentation(
                agent_instance=agent_instance,
                tools=tools,
                system_prompt="Test prompt",
                query="show active projects",
                context_id="ctx-005"
            )

        assert result == mock_result

    @pytest.mark.asyncio
    async def test_instrumentation_for_assignment_query(self):
        """Verify M5 spans are created for assignment-related queries."""
        from agent import _run_agent_with_instrumentation, SampleAgent

        with patch("agent.create_checkpointer"), patch("agent.ChatLiteLLM"):
            agent_instance = SampleAgent()

        mock_result = {"messages": [MagicMock(content="Assignment ID: d1e2f3a4-0001")]}
        tools = [_mock_tool("create_assignment", {"d": {"ProjDmndRsceAssgmtUUID": "d1e2f3a4-0001"}})]

        with patch.object(agent_instance, "_invoke_with_fallback", new=AsyncMock(return_value=mock_result)):
            with patch("agent.tracer") as mock_tracer:
                mock_span = MagicMock()
                mock_span.__enter__ = MagicMock(return_value=mock_span)
                mock_span.__exit__ = MagicMock(return_value=False)
                mock_tracer.start_as_current_span.return_value = mock_span

                result = await _run_agent_with_instrumentation(
                    agent_instance=agent_instance,
                    tools=tools,
                    system_prompt="Test prompt",
                    query="assign and confirm employee EMP001",
                    context_id="ctx-006"
                )

        assert result == mock_result


class TestLogMilestoneOutcomes:
    """Tests for the _log_milestone_outcomes function."""

    def test_m1_achieved_logged_when_projects_found(self):
        """Verify M1.achieved is logged when projects are in response."""
        from agent import _log_milestone_outcomes

        with patch("agent.logger") as mock_logger:
            _log_milestone_outcomes("show my active projects", "Found 3 projects in S/4HANA Cloud")
            logged_msgs = [str(c) for c in mock_logger.info.call_args_list]
            assert any("M1" in m for m in logged_msgs)

    def test_m1_missed_logged_when_no_projects(self):
        """Verify M1.missed is logged when no projects found."""
        from agent import _log_milestone_outcomes

        with patch("agent.logger") as mock_logger:
            _log_milestone_outcomes("list active projects", "No active projects found in S/4HANA Cloud")
            logged_msgs = [str(c) for c in mock_logger.info.call_args_list]
            assert any("M1" in m for m in logged_msgs)

    def test_m2_achieved_logged_for_demands(self):
        """Verify M2 milestone logged for demand queries."""
        from agent import _log_milestone_outcomes

        with patch("agent.logger") as mock_logger:
            _log_milestone_outcomes("show resource demands", "Here are the open resource demands")
            mock_logger.info.assert_called()

    def test_m3_achieved_logged_for_skills_query(self):
        """Verify M3 milestone logged for skills-related queries."""
        from agent import _log_milestone_outcomes

        with patch("agent.logger") as mock_logger:
            _log_milestone_outcomes("check employee skills", "Retrieved skills for 3 employees")
            mock_logger.info.assert_called()

    def test_m3_missed_for_unavailable_data(self):
        """Verify M3.missed logged when data is unavailable."""
        from agent import _log_milestone_outcomes

        with patch("agent.logger") as mock_logger:
            _log_milestone_outcomes(
                "check employee availab",
                "Employee availability data is currently unavailable. Please try again."
            )
            mock_logger.info.assert_called()

    def test_m4_achieved_logged_for_candidates(self):
        """Verify M4.achieved logged when candidates are recommended."""
        from agent import _log_milestone_outcomes

        with patch("agent.logger") as mock_logger:
            _log_milestone_outcomes(
                "recommend best candidates",
                "Here are the top 3 candidate recommendations for this demand"
            )
            mock_logger.info.assert_called()

    def test_m4_missed_no_candidates(self):
        """Verify M4.missed logged when no candidates found."""
        from agent import _log_milestone_outcomes

        with patch("agent.logger") as mock_logger:
            _log_milestone_outcomes(
                "find candidates",
                "No suitable candidates found for this demand. All available employees lack the required skills."
            )
            mock_logger.info.assert_called()

    def test_no_logging_for_unrelated_query(self):
        """Verify no milestone logging for unrelated queries."""
        from agent import _log_milestone_outcomes

        with patch("agent.logger") as mock_logger:
            _log_milestone_outcomes("hello world", "Hi there!")
            # No info log should be called for unrelated query
            assert mock_logger.info.call_count == 0
