"""Test client for the Deep Research Agent A2A server.

Demonstrates fetching the Agent Card, sending a research request via
standard message and streaming, and printing the results.

Usage:
    # Start the server first:
    #   uvicorn app:app --port 10000
    #
    # Then run this client:
    #   python test_client.py

    # To test against a deployed CF instance set BASE_URL:
    #   BASE_URL=https://deep-research-agent.cfapps.sap.hana.ondemand.com python test_client.py
"""

import asyncio
import logging
import os
from typing import Any
from uuid import uuid4

import httpx
from a2a.client import A2ACardResolver, A2AClient
from a2a.types import (
    AgentCard,
    MessageSendParams,
    SendMessageRequest,
    SendStreamingMessageRequest,
)
from a2a.utils.constants import (
    AGENT_CARD_WELL_KNOWN_PATH,
    EXTENDED_AGENT_CARD_PATH,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = os.getenv("BASE_URL", "http://localhost:10000")

# Research question sent to the deep research agent
RESEARCH_QUESTION = (
    "Research different approaches to custom AI Agent development with "
    "Joule Studio Agent Builder, Joule Studio Code Editor and SAP Cloud SDK for AI"
)


async def resolve_agent_card(
    httpx_client: httpx.AsyncClient,
) -> AgentCard:
    """Fetch and return the best available agent card from the server.

    Tries to fetch the public card first, then upgrades to the authenticated
    extended card if the server supports it.

    Args:
        httpx_client: Shared async HTTP client.

    Returns:
        The most privileged `AgentCard` available.

    Raises:
        RuntimeError: If the public agent card cannot be fetched.
    """
    resolver = A2ACardResolver(
        httpx_client=httpx_client,
        base_url=BASE_URL,
    )

    try:
        logger.info(
            "Fetching public agent card from %s%s",
            BASE_URL,
            AGENT_CARD_WELL_KNOWN_PATH,
        )
        public_card = await resolver.get_agent_card()
        logger.info("Agent card fetched successfully:")
        logger.info(public_card.model_dump_json(indent=2, exclude_none=True))

        if public_card.supports_authenticated_extended_card:
            try:
                logger.info(
                    "Fetching authenticated extended card from %s%s",
                    BASE_URL,
                    EXTENDED_AGENT_CARD_PATH,
                )
                extended_card = await resolver.get_agent_card(
                    relative_card_path=EXTENDED_AGENT_CARD_PATH,
                    http_kwargs={"headers": {"Authorization": "Bearer dummy-token"}},
                )
                logger.info("Extended agent card fetched successfully.")
                return extended_card
            except Exception as exc:
                logger.warning(
                    "Could not fetch extended card (%s). Using public card.", exc
                )

        return public_card

    except Exception as exc:
        raise RuntimeError(
            f"Failed to fetch agent card from {BASE_URL}: {exc}"
        ) from exc


async def send_research_request(
    client: A2AClient,
    question: str,
    *,
    task_id: str | None = None,
    context_id: str | None = None,
) -> Any:
    """Send a synchronous research request and return the raw response.

    Args:
        client: Initialised A2A client.
        question: The research question to submit.
        task_id: Optional task ID for continuing an existing task.
        context_id: Optional context ID for multi-turn conversations.

    Returns:
        The raw A2A response object.
    """
    message: dict[str, Any] = {
        "role": "user",
        "parts": [{"kind": "text", "text": question}],
        "message_id": uuid4().hex,
    }
    if task_id:
        message["task_id"] = task_id
    if context_id:
        message["context_id"] = context_id

    request = SendMessageRequest(
        id=str(uuid4()),
        params=MessageSendParams(message=message),
    )
    return await client.send_message(request)


async def stream_research_request(
    client: A2AClient,
    question: str,
) -> None:
    """Send a streaming research request and print each chunk as it arrives.

    This is the recommended mode for the deep research agent because research
    tasks are long-running and the streaming endpoint emits intermediate status
    updates so the caller can show progress.

    Args:
        client: Initialised A2A client.
        question: The research question to investigate.
    """
    message: dict[str, Any] = {
        "role": "user",
        "parts": [{"kind": "text", "text": question}],
        "message_id": uuid4().hex,
    }
    request = SendStreamingMessageRequest(
        id=str(uuid4()),
        params=MessageSendParams(message=message),
    )

    print("\n" + "=" * 60)
    print("STREAMING DEEP RESEARCH REQUEST")
    print("=" * 60)
    print(f"Question: {question}")
    print("-" * 60)

    chunk_count = 0
    async for chunk in client.send_message_streaming(request):
        chunk_count += 1
        print(f"\n[Chunk {chunk_count}]")
        print(chunk.model_dump_json(indent=2, exclude_none=True))

    print("-" * 60)
    print(f"Stream complete — received {chunk_count} chunk(s).")


async def main() -> None:
    """Run the deep research agent test scenarios."""
    async with httpx.AsyncClient(timeout=httpx.Timeout(600.0)) as httpx_client:
        # ------------------------------------------------------------------
        # Step 1: Resolve the agent card
        # ------------------------------------------------------------------
        card = await resolve_agent_card(httpx_client)
        client = A2AClient(httpx_client=httpx_client, agent_card=card)
        logger.info("A2AClient initialised against %s", BASE_URL)

        # ------------------------------------------------------------------
        # Step 2: Synchronous request (may take several minutes)
        # ------------------------------------------------------------------
        print("\n" + "=" * 60)
        print("SYNCHRONOUS RESEARCH REQUEST")
        print("=" * 60)
        print(f"Question: {RESEARCH_QUESTION}")
        print("-" * 60)

        response = await send_research_request(client, RESEARCH_QUESTION)
        print(response.model_dump_json(indent=2, exclude_none=True))

        # ------------------------------------------------------------------
        # Step 3: Streaming request (preferred for deep research)
        # ------------------------------------------------------------------
        await stream_research_request(client, RESEARCH_QUESTION)

        # ------------------------------------------------------------------
        # Step 4: Multi-turn follow-up (continue the same research context)
        # ------------------------------------------------------------------
        # Extract task and context IDs from the synchronous response to
        # continue the conversation in the same thread.
        try:
            result = response.root.result
            task_id = result.id
            context_id = result.context_id

            print("\n" + "=" * 60)
            print("MULTI-TURN FOLLOW-UP REQUEST")
            print("=" * 60)
            follow_up = "Summarise the key differences between the three approaches in a comparison table."
            print(f"Follow-up: {follow_up}")
            print("-" * 60)

            follow_up_response = await send_research_request(
                client,
                follow_up,
                task_id=task_id,
                context_id=context_id,
            )
            print(follow_up_response.model_dump_json(indent=2, exclude_none=True))

        except (AttributeError, TypeError) as exc:
            logger.warning(
                "Could not extract task/context IDs for multi-turn test: %s", exc
            )


if __name__ == "__main__":
    asyncio.run(main())
