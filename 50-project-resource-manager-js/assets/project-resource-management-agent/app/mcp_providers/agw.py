"""MCP tool provider — uses the Agent Gateway module for tool discovery and invocation.

Exposes `async def get_mcp_tools() -> list[BaseTool]` which discovers MCP tools
via the Agent Gateway module and converts them to LangChain tools.

Behaviour is controlled by the IBD_TESTING environment variable:

  Production (IBD_TESTING not set):
      Uses the Agent Gateway SDK client. The user token is read from a per-request
      context variable set by JWTContextMiddleware in main.py.
      Tools are fetched per-request (may vary per user).

  Local / test mode (IBD_TESTING=1):
      Reads mcp-mock.json from the directory containing this file's grandparent
      (i.e. <asset-root>/mcp-mock.json) and returns LangChain StructuredTool
      instances built from the mock data — no network calls.
"""

import json
import logging
import os
import base64
from contextvars import ContextVar, Token
from pathlib import Path
from typing import Any

from langchain_core.tools import BaseTool, StructuredTool
from pydantic import Field, create_model
from sap_cloud_sdk.agentgateway import create_client
from sap_cloud_sdk.agentgateway.converters import mcp_tool_to_langchain

from util import call_mcp_tool_with_retry

logger = logging.getLogger(__name__)

# Per-request user token, set by JWTContextMiddleware via set_user_token()
_user_token_context: ContextVar[str | None] = ContextVar("user_token", default=None)

# mcp-mock.json lives at the asset root (two levels above mcp_providers/)
_MOCK_FILE = Path(__file__).parent.parent.parent / "mcp-mock.json"


def set_user_token(token: str | None) -> Token:
    """Set the user token for the current async context (called by JWTContextMiddleware)."""
    return _user_token_context.set(token)


def get_user_token() -> str | None:
    """Get the user token for the current async context."""
    return _user_token_context.get()


def _get_user_token() -> str:
    token = _user_token_context.get()
    assert token is not None, "User token not set in current context"
    return token


def _build_mock_tools() -> list[BaseTool]:
    """Build LangChain StructuredTool instances from mcp-mock.json.

    Returns an empty list (without error) when mcp-mock.json is absent or
    cannot be parsed — add/fix the file to enable tool mocking.
    """
    if not _MOCK_FILE.exists():
        return []

    try:
        mock_data = json.loads(_MOCK_FILE.read_text())
    except Exception:
        logger.warning(
            "Failed to parse mcp-mock.json at %s — returning empty tool list",
            _MOCK_FILE,
            exc_info=True,
        )
        return []

    tools: list[BaseTool] = []

    for _server_slug, server in mock_data.get("servers", {}).items():
        for tool_name, tool_def in server.get("tools", {}).items():
            description = tool_def.get("description", "")
            mock_response = tool_def.get("mock_response", {})
            input_schema = tool_def.get("input_schema", {})

            props = input_schema.get("properties", {})
            required_fields = set(input_schema.get("required", []))
            field_definitions: dict[str, Any] = {}
            for field_name, field_info in props.items():
                json_type = field_info.get("type", "string")
                if json_type == "integer":
                    python_type: type = int
                elif json_type == "number":
                    python_type = float
                elif json_type == "boolean":
                    python_type = bool
                else:
                    python_type = str

                if field_name in required_fields:
                    field_definitions[field_name] = (
                        python_type,
                        Field(description=field_info.get("description", "")),
                    )
                else:
                    field_definitions[field_name] = (
                        python_type,
                        Field(default=None, description=field_info.get("description", "")),
                    )

            args_schema = (
                create_model(f"{tool_name}_args", **field_definitions)
                if field_definitions
                else create_model(f"{tool_name}_args")
            )
            _response = json.dumps(mock_response)

            async def _coroutine(_resp: str = _response, **kwargs: Any) -> str:
                return _resp

            tools.append(
                StructuredTool(
                    name=tool_name,
                    description=description,
                    args_schema=args_schema,
                    coroutine=_coroutine,
                    handle_tool_error=True,
                )
            )

    logger.info("Loaded %d mock MCP tool(s) from %s", len(tools), _MOCK_FILE)
    return tools


async def get_mcp_tools() -> list[BaseTool]:
    """Return LangChain-compatible MCP tools.

    In local/test mode (IBD_TESTING=1): returns mock tools from mcp-mock.json.
    In production: uses Agent Gateway SDK to discover and connect to MCP tools.

    The user token is read from the per-request context var set by JWTContextMiddleware.
    Tools are fetched per-request since tool listings may vary per user.
    """
    if os.environ.get("IBD_TESTING") == "1":
        return _build_mock_tools()

    agw_client = create_client()
    mcp_tools = await agw_client.list_mcp_tools(user_token=_get_user_token)

    if not mcp_tools:
        logger.warning("Agent Gateway returned 0 tools — MCP servers may not be available")
        return []

    def _make_caller(t: Any):
        async def call(_tool: Any = None, *, user_token: Any = None, **kwargs: Any) -> str:
            return await call_mcp_tool_with_retry(
                agw_client, t, user_token=_get_user_token(), **kwargs
            )
        return call

    tools = [
        mcp_tool_to_langchain(t, _make_caller(t), _get_user_token)
        for t in mcp_tools
    ]

    logger.info("Loaded %d MCP tool(s) from Agent Gateway", len(tools))
    # Sort deterministically so tool order is stable across requests (cache-stability).
    return sorted(tools, key=lambda t: t.name)

def get_user_sub() -> str:
    """Extract the JWT subject claim from the current request's token.

    Decodes the JWT payload (middle segment) without verifying the signature —
    The platform has already verified it before the request reaches this code.

    Returns:
        The 'sub' claim from the token.

    Raises:
        ValueError: If the token is missing or the sub claim cannot be extracted,
                    unless IBD_TESTING=1, in which case returns 'unknown'.
    """
    token = _user_token_context.get()
    if not token:
        if os.environ.get("IBD_TESTING") == "1":
            return "unknown"
        raise ValueError("No user token in context — cannot extract sub claim")

    try:
        payload_segment = token.split(".")[1]
        # Add padding if needed
        padding = 4 - len(payload_segment) % 4
        if padding != 4:
            payload_segment += "=" * padding
        payload = json.loads(base64.urlsafe_b64decode(payload_segment))
        sub = payload.get("sub")
        if not sub:
            raise ValueError("JWT payload contains no 'sub' claim")
        return sub
    except (IndexError, ValueError):
        raise
    except Exception as e:
        raise ValueError(f"Failed to decode JWT payload: {e}") from e

def reset_user_token(token: Token) -> None:
    """Restore the user token context to its previous value.

    Args:
        token: The Token returned by a prior set_user_token() call. Passing it to
            ContextVar.reset() unwinds the context stack to the value that was in
            effect before that set_user_token() call, rather than leaving a stale
            or None value behind.
    """
    _user_token_context.reset(token)
    logger.debug("User token context reset to previous value")