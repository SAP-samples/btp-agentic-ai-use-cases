"""
Utility functions for MCP tool processing.

Provides helper functions for enhancing MCP tool descriptions and metadata.
"""
import asyncio
import hashlib
import json
import logging
import os
import re
from typing import Any

import httpx
from langchain_core.tools import ToolException

logger = logging.getLogger(__name__)

_MCP_RETRY_ATTEMPTS = 4
_MCP_RETRY_DELAY = 4.0  # seconds
# Per-attempt timeout for a single MCP tool invocation. A slow or hung MCP
# server would otherwise stall the request indefinitely and exhaust the worker
# pool. Applied to each attempt individually (not the whole retry loop).
MCP_CALL_TIMEOUT_SECONDS = float(os.environ.get("MCP_CALL_TIMEOUT_SECONDS", 30.0))
# Maximum response size to prevent OOM and bound per-turn context cost — responses
# larger than this are truncated. Kept modest by default because tool results are
# re-sent on every subsequent turn; raise MCP_MAX_RESPONSE_CHARS for agents that
# genuinely need large payloads.
MCP_MAX_RESPONSE_CHARS = int(os.environ.get("MCP_MAX_RESPONSE_CHARS", 30_000))


def minify_json(text: str) -> str:
    """Return a whitespace-stripped form of ``text`` if it is valid JSON.

    Pretty-printed JSON carries indentation and spacing that cost tokens on every
    turn the result stays in context. Re-serializing with compact separators is
    lossless and typically saves ~30%. Non-JSON input is returned
    unchanged.
    """
    try:
        parsed = json.loads(text)
    except (ValueError, TypeError):
        return text
    return json.dumps(parsed, separators=(",", ":"), ensure_ascii=False)


def truncate_response(text: str, max_chars: int = MCP_MAX_RESPONSE_CHARS) -> str:
    """Truncate ``text`` to ``max_chars``, cutting at a structural boundary.

    A raw character cut can leave the model with a half-written JSON object or a
    token split mid-word. When possible we back up to the last newline, comma, or
    whitespace before the limit so the truncated output ends cleanly. A marker is
    always appended so the model knows content was dropped.
    """
    if len(text) <= max_chars:
        return text
    window = text[:max_chars]
    # Back up to the last clean boundary within the final 10% of the window so we
    # never cut mid-token; fall back to the hard cut if none is found.
    floor = int(max_chars * 0.9)
    boundary = max(window.rfind("\n"), window.rfind(","), window.rfind(" "))
    if boundary >= floor:
        window = window[:boundary]
    return window + "\n...[truncated]"


def _is_retryable_error(exc: Exception) -> bool:
    """Return True for transient errors that are worth retrying.

    Excludes client errors (HTTP 4xx) because those indicate a bad request
    that will not succeed on retry.
    """
    if isinstance(exc, httpx.HTTPStatusError):
        # 4xx = client error — not retryable
        return exc.response.status_code < 400 or exc.response.status_code >= 500
    if isinstance(exc, (ExceptionGroup, BaseExceptionGroup)):
        # anyio task-group wraps transport/protocol errors — retryable
        return True
    if isinstance(exc, (asyncio.TimeoutError, TimeoutError)):
        # A hung server that timed out may respond on a fresh attempt — retryable
        return True
    # Network-level errors, timeouts, unexpected exceptions — retryable
    return True


def enhance_tool_description(mcp_tool: Any) -> str:
    """
    Enhance MCP tool description with server name prefix.

    Prefixes the description with server name to help LLM identify tool origin.
    Extracts server label from fragment_name or uses server_name as fallback.

    Args:
        mcp_tool: The MCP tool object from SDK

    Returns:
        Enhanced description string with server label prefix

    Example:
        Input: tool with server_name="sap_system", description="Get user data"
        Output: "[sap_system] Get user data"
    """
    if mcp_tool is None:
        logger.warning("enhance_tool_description called with None tool")
        return ""

    # Extract server label from fragment_name or use server_name as fallback
    server_label = getattr(mcp_tool, "fragment_name", mcp_tool.server_name)
    enhanced_description = f"[{server_label}] {mcp_tool.description or ''}".strip()

    return enhanced_description

def enhance_tool_name(mcp_tool: Any) -> str:
    """Get enhanced and namespaced tool name, sanitized to match ^[a-zA-Z0-9-_]+$ and at most 64 chars.

    The server_name is parsed to extract meaningful segments:
    - If server_name has format like "org:type:resource:version" (e.g., "sap.mcpbuilder:apiResource:cost-center:v1"),
      the first two segments (org + type) are dropped, keeping only "resource:version" portions.
    - The remaining segments are joined with underscores and combined with tool_name as: {remaining}__{tool_name}
    - If server_name has 2 or fewer segments, the entire name is used.

    The result is sanitized to match ^[a-zA-Z0-9-_]+$ and truncated if needed.
    If the sanitized name exceeds 64 chars, it is truncated to 55 chars and an
    8-char sha256 suffix is appended (total 64), guaranteeing uniqueness.

    Args:
        mcp_tool: The MCP tool object from SDK (must have server_name and name attributes)

    Returns:
        Sanitized and namespaced tool name (max 64 chars)

    Examples:
        >>> tool = MockTool(server_name="sap.mcpbuilder:apiResource:cost-center:v1", name="list_a_costcenter")
        >>> enhance_tool_name(tool)
        'cost-center_v1__list_a_costcenter'
        >>> tool = MockTool(server_name="simple-server", name="my_tool")
        >>> enhance_tool_name(tool)
        'simple-server__my_tool'
    """
    if mcp_tool is None:
        logger.warning("enhance_tool_name called with None tool")
        return ""

    server_name = mcp_tool.server_name
    tool_name = mcp_tool.name

    # Step 1: Split server_name by ':'
    segments = server_name.split(":")

    # Step 2: If more than 2 segments, drop the first two (org + type), keep the rest
    if len(segments) > 2:
        remaining = segments[2:]
    else:
        remaining = segments

    # Step 3: Build {remaining}__{tool_name}, joining remaining segments with underscores
    server_part = "_".join(remaining)
    raw = f"{server_part}__{tool_name}"

    # Step 4: Sanitize (replace invalid chars with _)
    sanitized = re.sub(r"[^a-zA-Z0-9\-_]", "_", raw)

    # Step 5: If > 64 chars, truncate to 55 + _ + 8-char hash
    if len(sanitized) <= 64:
        return sanitized
    suffix = hashlib.sha256(sanitized.encode()).hexdigest()[:8]
    return f"{sanitized[:55]}_{suffix}"


async def call_mcp_tool_with_retry(agw_client: Any, mcp_tool: Any, user_token: str | None = None, **kwargs: Any) -> str:
    """
    Call an MCP tool with retry logic and error handling.

    Args:
        agw_client: Agent Gateway client instance
        mcp_tool: The tool to call (MCPTool object from SDK)
        user_token: User authentication token to pass to MCP server for tool execution
        **kwargs: Tool arguments

    Returns:
        Tool result as string (truncated if exceeds MCP_MAX_RESPONSE_CHARS)

    Raises:
        ValueError: If tool is None
        RuntimeError: If SDK returns None or empty result
        Exception: If tool call fails after all retry attempts
    """
    if mcp_tool is None:
        raise ValueError("Tool parameter cannot be None")

    last_exc: Exception | None = None
    for attempt in range(1 + _MCP_RETRY_ATTEMPTS):
        try:
            # Log tool name but sanitize arguments to avoid exposing sensitive data
            arg_keys = list(kwargs.keys()) if kwargs else []
            logger.info(
                f"Calling MCP tool '{mcp_tool.name}' via Agent Gateway with {len(arg_keys)} argument(s)"
            )
            logger.debug(
                f"call_mcp_tool_with_retry: Initiating SDK call to Agent Gateway for {mcp_tool.name}"
            )

            # Capture result outside potential ExceptionGroup handling
            _call_result = None
            try:
                # Build call parameters
                call_params = {"tool": mcp_tool, **kwargs}

                if user_token is not None:
                    call_params["user_token"] = user_token

                _call_result = await asyncio.wait_for(
                    agw_client.call_mcp_tool(**call_params),
                    timeout=MCP_CALL_TIMEOUT_SECONDS,
                )
                logger.debug(
                    f"call_mcp_tool_with_retry: SDK call completed for {mcp_tool.name}"
                )
            except (asyncio.TimeoutError, TimeoutError):
                # A slow or hung MCP server exceeded the per-attempt timeout.
                # asyncio.wait_for has already cancelled the underlying call, so
                # the worker is freed. Re-raise to trigger the retry logic below.
                logger.warning(
                    f"call_mcp_tool_with_retry: Tool {mcp_tool.name} timed out after "
                    f"{MCP_CALL_TIMEOUT_SECONDS}s"
                )
                raise
            except (ExceptionGroup, BaseExceptionGroup) as eg:
                # The MCP server may close the connection after sending the response;
                # anyio wraps that teardown race in an ExceptionGroup.
                # If we already captured a result, the call succeeded — suppress teardown noise.
                if _call_result is None:
                    logger.warning(
                        f"call_mcp_tool_with_retry: ExceptionGroup raised and no result captured for {mcp_tool.name}: {eg}"
                    )
                    raise
                logger.debug(
                    f"call_mcp_tool_with_retry: Ignoring ExceptionGroup on teardown for {mcp_tool.name} "
                    f"(result already captured): {eg}"
                )

            # Validate result
            if _call_result is None:
                raise RuntimeError(
                    f"call_mcp_tool_with_retry: SDK call_mcp_tool returned None for {mcp_tool.name} — "
                    "the server may be unavailable or returned an empty response"
                )

            # Convert result to string
            result = str(_call_result) if _call_result else ""

            if not result:
                logger.warning(
                    f"call_mcp_tool_with_retry: Tool {mcp_tool.name} returned empty result"
                )
                result = ""

            # Minify JSON payloads before they enter context — lossless, and the
            # result is re-sent on every subsequent turn. Non-JSON is
            # returned unchanged.
            result = minify_json(result)

            # Truncate large responses to prevent OOM and bound per-turn context
            # cost, cutting at a structural boundary rather than mid-token.
            if len(result) > MCP_MAX_RESPONSE_CHARS:
                logger.warning(
                    f"call_mcp_tool_with_retry: Response from {mcp_tool.name} truncated from "
                    f"{len(result)} to ~{MCP_MAX_RESPONSE_CHARS} chars to prevent OOM"
                )
                result = truncate_response(result, MCP_MAX_RESPONSE_CHARS)

            logger.info(
                f"MCP tool '{mcp_tool.name}' returned successfully (response length: {len(result)} chars)"
            )
            return result

        except Exception as e:
            if not _is_retryable_error(e):
                logger.exception(
                    f"call_mcp_tool_with_retry: Non-retryable error calling {mcp_tool.name}"
                )
                raise
            last_exc = e
            if attempt < _MCP_RETRY_ATTEMPTS:
                logger.warning(
                    f"call_mcp_tool_with_retry: Error calling {mcp_tool.name} "
                    f"(attempt {attempt + 1}/{1 + _MCP_RETRY_ATTEMPTS}), retrying in {_MCP_RETRY_DELAY}s: {e}"
                )
                await asyncio.sleep(_MCP_RETRY_DELAY)

    logger.exception(
        f"call_mcp_tool_with_retry: Failed to call {mcp_tool.name} after {1 + _MCP_RETRY_ATTEMPTS} attempts",
        exc_info=last_exc,
        )
    # Raise ToolException so that LangChain's handle_tool_error=True can catch
    # it and forward the message to the LLM as a ToolMessage error string.
    # This prevents the LLM from hallucinating a result after the real call
    # fails all retry attempts.
    raise ToolException(
        f"Tool '{mcp_tool.name}' failed after {1 + _MCP_RETRY_ATTEMPTS} attempts: {last_exc}"
    ) from last_exc
