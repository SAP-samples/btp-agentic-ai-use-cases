# Complete Instrumented Agent Example

A full example of an Joule Studio runtime agent with OpenTelemetry instrumentation.

---

## main.py

```python
"""
A2A Server with OpenTelemetry instrumentation.
"""

import logging
import os

import click
import uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from sap_cloud_sdk import bootstrap
from sap_cloud_sdk.aicore import set_aicore_config

from agent_executor import MyAgentExecutor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure AI Core
logger.info("Setting AICore configuration")
set_aicore_config()

HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "9000"))


@click.command()
@click.option("--host", default=HOST, help="Host to bind to")
@click.option("--port", default=PORT, help="Port to bind to")
def main(host: str, port: int):
    """Start the A2A agent server."""
    
    capabilities = AgentCapabilities(streaming=True, pushNotifications=False)
    
    skill = AgentSkill(
        id="my-agent",
        name="My Instrumented Agent",
        description="An agent with OpenTelemetry instrumentation",
        tags=["instrumented", "otel"],
        examples=["How can you help me?"],
    )
    
    agent_card = AgentCard(
        name="My Instrumented Agent",
        description="Agent with full observability",
        url=f"http://{host}:{port}/",
        version="1.0.0",
        defaultInputModes=["text", "text/plain"],
        defaultOutputModes=["text", "text/plain"],
        capabilities=capabilities,
        skills=[skill],
    )
    
    task_store = InMemoryTaskStore()
    request_handler = DefaultRequestHandler(
        agent_executor=MyAgentExecutor(),
        task_store=task_store,
    )
    
    server = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=request_handler,
    )
    
    app = server.build()
    bootstrap(app)

    logger.info(f"Starting A2A server at http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
```

---

## agent.py

```python
"""
Instrumented agent with OpenTelemetry tracing and metrics.
"""

import logging
import warnings
from dataclasses import dataclass
from typing import AsyncGenerator, Literal

from pydantic_ai import Agent
from pydantic_ai_litellm import LiteLLMModel
from sap_cloud_sdk.core.telemetry import (
    context_overlay,
    GenAIOperation,
    add_span_attribute,
)

warnings.filterwarnings("ignore", message="Pydantic serializer warnings")
logger = logging.getLogger(__name__)


@dataclass
class AgentResponse:
    """Response from the agent."""
    status: Literal["input_required", "completed", "error"]
    message: str


class InstrumentedAgent:
    """Agent with full OpenTelemetry instrumentation."""

    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]

    def __init__(self):
        """Initialize the agent with LiteLLM model."""
        self.model = LiteLLMModel('sap/anthropic--claude-4.5-sonnet')
        self.agent = Agent(
            model=self.model,
            system_prompt=self._get_system_prompt()
        )

    def _get_system_prompt(self) -> str:
        """Get the system prompt."""
        return """You are a helpful AI assistant.
        
Answer questions clearly and concisely.
If you don't know something, say so honestly."""

    def _log_token_usage(self, result) -> None:
        try:
            usage = result.usage()

            logger.info(
                f"Token Usage - Input: {usage.input_tokens}, "
                f"Output: {usage.output_tokens}, "
                f"Total: {usage.total_tokens}"
            )

            add_span_attribute("gen_ai.usage.input_tokens", usage.input_tokens)
            add_span_attribute("gen_ai.usage.output_tokens", usage.output_tokens)

        except AttributeError:
            logger.warning("Token usage information not available")
        except Exception as e:
            logger.warning(f"Failed to record token metrics: {e}")

    async def stream(
        self, query: str, context_id: str
    ) -> AsyncGenerator[dict, None]:
        """
        Stream responses with tracing.

        Args:
            query: The user's question
            context_id: Unique conversation context ID

        Yields:
            Status updates and final response
        """
        yield {
            "is_task_complete": False,
            "require_user_input": False,
            "content": "Processing your request...",
        }

        try:
            # Create custom span with business context
            # Auto-instrumentation traces the LiteLLM call inside
            with context_overlay(
                GenAIOperation.CHAT,
                attributes={
                    "context.id": context_id,
                    "query.length": len(query),
                    "agent.type": "instrumented_agent"
                }
            ):
                result = await self.agent.run(query)
                
                # Add custom attribute with response length
                add_span_attribute("response.length", len(result.output))

                # Log token usage for visibility and billing
                self._log_token_usage(result)

            yield {
                "is_task_complete": True,
                "require_user_input": False,
                "content": result.output,
            }

        except Exception as e:
            logger.exception("Error during agent execution")
            yield {
                "is_task_complete": True,
                "require_user_input": False,
                "content": f"Error processing request: {str(e)}",
            }

    def invoke(self, query: str, context_id: str) -> AgentResponse:
        """
        Synchronous invocation with tracing.

        Args:
            query: The user's question
            context_id: Unique conversation context ID

        Returns:
            AgentResponse with status and message
        """
        import asyncio

        async def _run():
            with context_overlay(
                GenAIOperation.CHAT,
                attributes={
                    "custom.context.id": context_id,
                    "query.length": len(query),
                    "agent.type": "instrumented_agent",
                }
            ):
                result = await self.agent.run(query)
                add_span_attribute("response.length", len(result.output))
                usage = result.usage()
                add_span_attribute("gen_ai.usage.input_tokens", usage.input_tokens)
                add_span_attribute("gen_ai.usage.output_tokens", usage.output_tokens)
                return result

        try:
            result = asyncio.run(_run())
            return AgentResponse(status="completed", message=result.output)
        except Exception as e:
            return AgentResponse(status="error", message=f"Error: {str(e)}")
```

---

## agent_executor.py

```python
"""
A2A Agent Executor with instrumented agent.
"""

import logging

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import (
    InternalError,
    InvalidParamsError,
    Part,
    TaskState,
    TextPart,
    UnsupportedOperationError,
)
from a2a.utils import new_agent_text_message, new_task
from a2a.utils.errors import ServerError

from agent import InstrumentedAgent

logger = logging.getLogger(__name__)


class MyAgentExecutor(AgentExecutor):
    """A2A executor bridging A2A protocol with InstrumentedAgent."""

    def __init__(self):
        """Initialize with the instrumented agent."""
        self.agent = InstrumentedAgent()

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Execute the agent and stream results via A2A protocol."""
        query = context.get_user_input()
        task = context.current_task

        if not task:
            task = new_task(context.message)
            await event_queue.enqueue_event(task)

        updater = TaskUpdater(event_queue, task.id, task.context_id)

        try:
            async for item in self.agent.stream(query, task.context_id):
                is_task_complete = item['is_task_complete']
                require_user_input = item.get('require_user_input', False)
                content = item.get('content', '')

                if not is_task_complete and not require_user_input:
                    await updater.update_status(
                        TaskState.working,
                        new_agent_text_message(content, task.context_id, task.id)
                    )
                elif require_user_input:
                    await updater.update_status(
                        TaskState.input_required,
                        new_agent_text_message(content, task.context_id, task.id),
                        final=True
                    )
                    break
                else:
                    await updater.add_artifact(
                        [Part(root=TextPart(text=content))],
                        name='agent_result'
                    )
                    await updater.complete()
                    break

        except Exception as e:
            logger.exception("Error executing agent")
            raise ServerError(error=InternalError()) from e

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Cancel a running task."""
        raise ServerError(error=UnsupportedOperationError())
```

---

## requirements.txt

```
pydantic-ai>=0.1.0
pydantic-ai-litellm>=0.1.0
a2a-sdk>=0.1.0
sap-cloud-sdk>=0.2.0
uvicorn>=0.30.0
click>=8.0.0
```

---

## Key Points

1. **Bootstrap wires instrumentation**: `bootstrap(app)` wires OpenTelemetry and Starlette middleware automatically
2. **Context Overlays**: Wrap LLM calls for business context tracking
3. **Token Recording**: Call `add_span_attribute()` to set token counts (`gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`) on the active span
4. **Custom Attributes**: Use `add_span_attribute()` for additional context
5. **Error Handling**: Telemetry code should never break business logic
