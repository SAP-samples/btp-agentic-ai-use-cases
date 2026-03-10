"""A2A Starlette application for the Deep Research Agent.

Exposes the deep research agent as an A2A-compatible HTTP service that can be
registered as a custom agent skill in SAP Joule.
"""

import logging
import os

import httpx
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import (
    BasePushNotificationSender,
    InMemoryPushNotificationConfigStore,
    InMemoryTaskStore,
)
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)
from agent import DeepResearchAgent
from agent_executor import DeepResearchAgentExecutor

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 10000))

# Public URL used by Joule to register this agent - set via environment
# variable or update with your actual Cloud Foundry application URL.
AGENT_PUBLIC_URL = os.getenv("AGENT_PUBLIC_URL", f"http://{HOST}:{PORT}")

# ------------------------------------------------------------------
# Agent Card - describes this agent to Joule and other A2A clients
# ------------------------------------------------------------------

capabilities = AgentCapabilities(streaming=True, push_notifications=True)

skill = AgentSkill(
    id="deep_research",
    name="Deep Research",
    description=(
        "Conducts comprehensive web research on any topic using a "
        "multi-agent pipeline. Searches the web, analyses sources, "
        "synthesises findings, and returns a structured Markdown report "
        "with inline citations."
    ),
    tags=[
        "research",
        "web search",
        "analysis",
        "report generation",
        "AI agents",
    ],
    examples=[
        "Research different approaches to custom AI agents with Joule Studio Agent Builder",
        "Compare the latest large language models from OpenAI, Anthropic, and Google",
        "Summarise the current state of quantum computing research",
        "Research best practices for SAP BTP application development",
    ],
)

agent_card = AgentCard(
    name="Deep Research Agent",
    description=(
        "An AI research assistant powered by SAP Generative AI Hub. "
        "Given a research question or topic, it autonomously plans, "
        "delegates web searches to specialised sub-agents, and produces "
        "a comprehensive, cited Markdown research report."
    ),
    url=AGENT_PUBLIC_URL,
    version="1.0.0",
    default_input_modes=DeepResearchAgent.SUPPORTED_CONTENT_TYPES,
    default_output_modes=DeepResearchAgent.SUPPORTED_CONTENT_TYPES,
    capabilities=capabilities,
    skills=[skill],
)

# ------------------------------------------------------------------
# Server setup
# ------------------------------------------------------------------

httpx_client = httpx.AsyncClient()
push_config_store = InMemoryPushNotificationConfigStore()
push_sender = BasePushNotificationSender(
    httpx_client=httpx_client,
    config_store=push_config_store,
)
request_handler = DefaultRequestHandler(
    agent_executor=DeepResearchAgentExecutor(),
    task_store=InMemoryTaskStore(),
    push_config_store=push_config_store,
    push_sender=push_sender,
)
server = A2AStarletteApplication(
    agent_card=agent_card,
    http_handler=request_handler,
)

# ASGI app exported for uvicorn
app = server.build()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=HOST, port=PORT)
