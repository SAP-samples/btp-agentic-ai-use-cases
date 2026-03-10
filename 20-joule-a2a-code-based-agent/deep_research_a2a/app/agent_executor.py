"""A2A AgentExecutor for the Deep Research Agent.

Wraps `DeepResearchAgent` with the A2A `AgentExecutor` interface so the
agent can be served via the A2A Starlette application and consumed by
Joule and other A2A-compatible clients.
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
from agent import DeepResearchAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DeepResearchAgentExecutor(AgentExecutor):
    """A2A executor for the deep research agent.

    Handles the full A2A task lifecycle: task creation, streaming status
    updates while the agent is working, and artifact publication on
    completion.
    """

    def __init__(self) -> None:
        self.agent = DeepResearchAgent()

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Execute a research request received via the A2A protocol.

        Args:
            context: Incoming request context containing the user's message.
            event_queue: Queue for publishing task state events and artifacts.

        Raises:
            ServerError: On invalid request parameters or unexpected failures.
        """
        if self._validate_request(context):
            raise ServerError(error=InvalidParamsError())

        query = context.get_user_input()
        task = context.current_task

        if not task:
            task = new_task(context.message)  # type: ignore[arg-type]
            await event_queue.enqueue_event(task)

        updater = TaskUpdater(event_queue, task.id, task.context_id)

        logger.info("Starting deep research for context_id=%s", task.context_id)

        try:
            async for item in self.agent.stream(query, task.context_id):
                is_complete = item["is_task_complete"]
                needs_input = item["require_user_input"]

                if not is_complete and not needs_input:
                    # Intermediate progress update
                    await updater.update_status(
                        TaskState.working,
                        new_agent_text_message(
                            item["content"],
                            task.context_id,
                            task.id,
                        ),
                    )

                elif needs_input:
                    # Agent requires clarification from the user
                    await updater.update_status(
                        TaskState.input_required,
                        new_agent_text_message(
                            item["content"],
                            task.context_id,
                            task.id,
                        ),
                        final=True,
                    )
                    break

                else:
                    # Research complete - publish report as artifact
                    await updater.add_artifact(
                        [Part(root=TextPart(text=item["content"]))],
                        name="research_report",
                    )
                    await updater.complete()
                    logger.info("Research completed for context_id=%s", task.context_id)
                    break

        except Exception as e:
            logger.exception("Unexpected error during research execution: %s", e)
            raise ServerError(error=InternalError()) from e

    def _validate_request(self, context: RequestContext) -> bool:
        """Validate the incoming request context.

        Args:
            context: The A2A request context to validate.

        Returns:
            True if the request is invalid and should be rejected, False otherwise.
        """
        return False

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Cancel a running research task (not supported).

        Args:
            context: The request context for the task to cancel.
            event_queue: Event queue for the task.

        Raises:
            ServerError: Always, as cancellation is not supported.
        """
        raise ServerError(error=UnsupportedOperationError())
