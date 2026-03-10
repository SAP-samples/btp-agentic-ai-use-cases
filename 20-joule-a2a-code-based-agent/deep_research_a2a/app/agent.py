"""Deep Research Agent for Joule integration with A2A.

Wraps the deepagents deep research orchestrator with an async streaming
interface compatible with the A2A SDK, using SAP Generative AI Hub for
model access.
"""

import asyncio
import logging
import os
from collections.abc import AsyncIterable
from datetime import datetime
from typing import Any

from deepagents import create_deep_agent
from gen_ai_hub.proxy.langchain import init_llm
from langchain_core.messages import AIMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver
from research_agent.prompts import (
    RESEARCH_WORKFLOW_INSTRUCTIONS,
    RESEARCHER_INSTRUCTIONS,
    SUBAGENT_DELEGATION_INSTRUCTIONS,
)
from research_agent.tools import tavily_search, think_tool

logger = logging.getLogger(__name__)

# Orchestrator limits
_MAX_CONCURRENT_RESEARCH_UNITS = int(os.getenv("MAX_CONCURRENT_RESEARCH_UNITS", 3))
_MAX_RESEARCHER_ITERATIONS = int(os.getenv("MAX_RESEARCHER_ITERATIONS", 3))

# LLM model in your SAP Generative AI Hub (configurable via environment variable), default as gpt-4o-mini
_MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")

# Additional instruction for A2A deployments: the agent must include
# the report body in its final assistant message so the A2A executor
# can surface it as an artifact without needing filesystem access.
_A2A_RESPONSE_INSTRUCTION = """
## A2A Response Format

After writing the final report to /final_report.md, copy the complete report
content verbatim into your final response message. This is required so the
A2A interface can return the research results directly to the caller.
"""

# Human-readable status labels for common tool names
_TOOL_STATUS: dict[str, str] = {
    "write_todos": "Planning research tasks...",
    "write_file": "Saving research content...",
    "read_file": "Reviewing research content...",
    "task": "Delegating to research sub-agent...",
    "tavily_search": "Searching the web...",
    "think_tool": "Analysing research findings...",
    "ls": "Checking available content...",
    "glob": "Locating research files...",
    "grep": "Searching through content...",
    "edit_file": "Editing research content...",
    "execute": "Executing research step...",
}


class DeepResearchAgent:
    """Deep research agent backed by SAP Generative AI Hub and LangChain deepagents.

    Uses `create_deep_agent` to build a multi-agent research pipeline with:
    - An orchestrator that plans, delegates, synthesises, and writes reports.
    - A research sub-agent that performs web searches via Tavily.

    The `stream` method is compatible with the A2A `AgentExecutor` pattern.
    """

    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]

    def __init__(self) -> None:
        current_date = datetime.now().strftime("%Y-%m-%d")

        # Initialise model from SAP Generative AI Hub
        model = init_llm(_MODEL_NAME, max_tokens=8096)
        self.checkpointer = MemorySaver()

        # Build orchestrator system prompt
        instructions = (
            RESEARCH_WORKFLOW_INSTRUCTIONS
            + "\n\n"
            + _A2A_RESPONSE_INSTRUCTION
            + "\n\n"
            + "=" * 80
            + "\n\n"
            + SUBAGENT_DELEGATION_INSTRUCTIONS.format(
                max_concurrent_research_units=_MAX_CONCURRENT_RESEARCH_UNITS,
                max_researcher_iterations=_MAX_RESEARCHER_ITERATIONS,
            )
        )

        # Research sub-agent
        research_sub_agent: dict[str, Any] = {
            "name": "research-agent",
            "description": (
                "Delegate research to the sub-agent researcher. "
                "Only give this researcher one topic at a time."
            ),
            "system_prompt": RESEARCHER_INSTRUCTIONS.format(date=current_date),
            "tools": [tavily_search, think_tool],
        }

        self.graph = create_deep_agent(
            model=model,
            tools=[tavily_search, think_tool],
            system_prompt=instructions,
            subagents=[research_sub_agent],
            checkpointer=self.checkpointer,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _tool_status(self, tool_calls: list[dict]) -> str:
        """Return a human-readable status for the current tool calls.

        Args:
            tool_calls: List of tool call dicts each containing a 'name' key.

        Returns:
            Status string describing the operation in progress.
        """
        if not tool_calls:
            return "Processing..."
        name = tool_calls[0].get("name", "")
        msg = _TOOL_STATUS.get(name, f"Running {name}...")
        if len(tool_calls) > 1:
            msg = f"{msg} (and {len(tool_calls) - 1} more)"
        return msg

    def _extract_report_from_tool_calls(self, messages: list) -> str | None:
        """Scan messages for a write_file call that wrote /final_report.md.

        Args:
            messages: All messages from the completed agent state.

        Returns:
            Report content string if found, None otherwise.
        """
        for message in reversed(messages):
            if not (isinstance(message, AIMessage) and message.tool_calls):
                continue
            for tc in message.tool_calls:
                if tc.get("name") != "write_file":
                    continue
                args = tc.get("args", {})
                # Tolerate varying argument names
                path = args.get("path", args.get("filename", args.get("file_path", "")))
                if "/final_report.md" in str(path):
                    return args.get("content", args.get("text", args.get("data", "")))
        return None

    def _get_final_content(self, config: dict) -> str:
        """Retrieve the completed research report from agent state.

        Tries extracting from the write_file tool call that produced
        /final_report.md, then falls back to the last substantial AIMessage.

        Args:
            config: LangGraph run configuration containing the thread_id.

        Returns:
            Research report content as a plain string.
        """
        try:
            state = self.graph.get_state(config)
            messages = state.values.get("messages", [])

            # Primary: content written to /final_report.md
            report = self._extract_report_from_tool_calls(messages)
            if report:
                return report

            # Fallback: last non-trivial AIMessage
            for message in reversed(messages):
                if not isinstance(message, AIMessage):
                    continue
                content = message.content
                if isinstance(content, list):
                    content = "\n".join(
                        block.get("text", "")
                        for block in content
                        if isinstance(block, dict) and block.get("type") == "text"
                    )
                if isinstance(content, str) and len(content.strip()) > 100:
                    return content.strip()

        except Exception:
            logger.exception("Error retrieving final research report")

        return "Research completed. The report has been written to /final_report.md."

    # ------------------------------------------------------------------
    # Public streaming interface
    # ------------------------------------------------------------------

    async def stream(
        self, query: str, context_id: str
    ) -> AsyncIterable[dict[str, Any]]:
        """Stream research progress updates followed by the final report.

        Runs the deep research graph synchronously inside the async event loop,
        yielding lightweight status dicts compatible with the A2A task protocol
        after each graph step, then yields a final completion dict containing
        the full research report.

        Args:
            query: The research question or topic to investigate.
            context_id: Conversation thread ID for state persistence.

        Yields:
            Dicts with keys:
            - `is_task_complete` (bool): True only on the final yield.
            - `require_user_input` (bool): True when user clarification is needed.
            - `content` (str): Status message or final report text.
        """
        inputs = {"messages": [("user", query)]}
        config = {"configurable": {"thread_id": context_id}}

        try:
            for item in self.graph.stream(inputs, config, stream_mode="values"):
                message = item["messages"][-1]

                if isinstance(message, AIMessage) and message.tool_calls:
                    status = self._tool_status(message.tool_calls)
                    logger.info("Research agent: %s", status)
                    yield {
                        "is_task_complete": False,
                        "require_user_input": False,
                        "content": status,
                    }
                elif isinstance(message, ToolMessage):
                    yield {
                        "is_task_complete": False,
                        "require_user_input": False,
                        "content": "Processing results...",
                    }

                # Yield control so the event loop can flush SSE events
                await asyncio.sleep(0)

        except Exception as e:
            logger.exception("Research agent execution failed")
            yield {
                "is_task_complete": False,
                "require_user_input": True,
                "content": f"Research failed: {e!s}",
            }
            return

        final_content = self._get_final_content(config)
        yield {
            "is_task_complete": True,
            "require_user_input": False,
            "content": final_content,
        }
