# Advanced Agent Instrumentation with OpenTelemetry

Provides in-depth guidance on instrumenting an Joule Studio runtime agent with OpenTelemetry. Use this for advanced scenarios beyond the basic `bootstrap(app)` call included in the agent bootstrap.

> **Note**: Basic instrumentation is already included in agents created with the `sap-agent-bootstrap`. Use this  when you need custom spans, manual token tracking, or more advanced observability.

## Overview

The SAP Cloud SDK provides automatic observability through OpenTelemetry-compliant tracing. This enables:

- **Automatic LLM call tracing** - Traces LiteLLM, LangChain, Anthropic, and OpenAI calls
- **Token usage tracking** - Records input/output tokens in OpenTelemetry spans
- **Custom spans** - Add business context to operations
- **Span attributes** - Record token usage and custom metadata on OpenTelemetry spans

## Quick Start

### Step 1: Initialize Instrumentation via Bootstrap

Call `bootstrap(app)` after the app is built — it wires all OpenTelemetry instrumentation and Starlette middleware in one call:

```python
# main.py
from sap_cloud_sdk import bootstrap
from sap_cloud_sdk.aicore import set_aicore_config

set_aicore_config()

# ... imports, app setup ...

app = server.build()
bootstrap(app)
```

This automatically traces:
- LiteLLM calls
- LangChain operations
- Anthropic API calls
- OpenAI API calls

### Step 2: Import Telemetry Functions

```python
from sap_cloud_sdk.core.telemetry import (
    context_overlay,
    GenAIOperation,
    add_span_attribute,
    chat_span,
    execute_tool_span,
    invoke_agent_span,
)
```

### Step 3: Record Token Usage

`add_span_attribute` only records when called inside an active span (e.g. within `context_overlay` or `chat_span`). Call `_log_token_usage` from within that span scope:

```python
def _log_token_usage(self, result) -> None:
    try:
        usage = result.usage()

        logger.info(
            f"Token Usage - Input: {usage.input_tokens}, "
            f"Output: {usage.output_tokens}, "
            f"Total: {usage.total_tokens}"
        )

        # Must be called inside an active span context
        add_span_attribute("gen_ai.usage.input_tokens", usage.input_tokens)
        add_span_attribute("gen_ai.usage.output_tokens", usage.output_tokens)

    except AttributeError:
        logger.warning("Token usage information not available")
    except Exception as e:
        logger.warning(f"Failed to record token metrics: {e}")

# Call within an active span:
with context_overlay(GenAIOperation.CHAT, attributes={"context.id": context_id}):
    result = await self.agent.run(query)
    self._log_token_usage(result)  # span is active here
```

### Step 4: Add Custom Spans with Context

Wrap LLM operations with custom spans for business context:

```python
async def process_query(self, query: str, context_id: str):
    """Process a query with tracing."""
    
    with context_overlay(
        GenAIOperation.CHAT,
        attributes={
            "context.id": context_id,
            "query.length": len(query),
            "agent.type": "my_agent"
        }
    ):
        result = await self.agent.run(query)
        
        add_span_attribute("response.length", len(result.output))
        
        usage = result.usage()
        add_span_attribute("gen_ai.usage.input_tokens", usage.input_tokens)
        add_span_attribute("gen_ai.usage.output_tokens", usage.output_tokens)
        
        return result
```

## Telemetry Middleware

`bootstrap(app)` automatically registers IAS JWT claim extraction middleware — no separate setup needed. It reads `Authorization: Bearer <token>`, parses the IAS JWT, and sets:
- `sap.tenancy.tenant_id` — from the `sap_gtid` claim
- `user.id` — from the `user_uuid` claim
- `sap.trigger_type` — from the `x-sap-origin` request header

Call `bootstrap(app)` **after** `app = server.build()` — the app must exist before middleware can register on it:

```python
from sap_cloud_sdk import bootstrap

# ... agent card setup ...

app = server.build()
bootstrap(app)
uvicorn.run(app, host=host, port=port)
```

## Available GenAI Operations

Use these operation types for context overlays:

| Operation | Use Case |
|-----------|----------|
| `GenAIOperation.CHAT` | Chat/conversation operations |
| `GenAIOperation.TEXT_COMPLETION` | Text completion tasks |
| `GenAIOperation.EMBEDDINGS` | Embedding generation |
| `GenAIOperation.GENERATE_CONTENT` | Multimodal content generation |
| `GenAIOperation.RETRIEVAL` | RAG retrieval operations |
| `GenAIOperation.EXECUTE_TOOL` | Tool/function execution |
| `GenAIOperation.CREATE_AGENT` | Agent creation |
| `GenAIOperation.INVOKE_AGENT` | Agent invocation |

## Specialized Span Helpers

For common agentic patterns, use these purpose-built span context managers instead of a generic `context_overlay`. They set the required OpenTelemetry GenAI semantic convention attributes automatically.

**`chat_span`** — wraps a direct LLM call; yields the span so you can set token usage attributes:

```python
with chat_span(model="anthropic--claude-4.5-sonnet", provider="sap-aicore", conversation_id=context_id) as span:
    response = client.chat.completions.create(...)
    span.set_attribute("gen_ai.usage.input_tokens", response.usage.prompt_tokens)
    span.set_attribute("gen_ai.usage.output_tokens", response.usage.completion_tokens)
```

**`execute_tool_span`** — wraps a tool call inside an agent loop:

```python
with execute_tool_span(tool_name="get_weather", tool_type="function") as tool_span:
    result = get_weather(city=args["city"])
    tool_span.set_attribute("gen_ai.tool.call.result", result)
```

**`invoke_agent_span`** — wraps an outbound agent invocation (remote or in-process):

```python
with invoke_agent_span(provider="sap-aicore", agent_name="SupportBot", conversation_id=context_id):
    response = remote_agent.run(query)
```

## Complete Example

See [Complete Agent Example](references/instrumented-agent-example.md) for a full working implementation.

## Configuration

### Production Environment

In Container Hosting, the OTEL exporter endpoint is automatically injected:

```bash
# Auto-configured by Container Hosting
OTEL_EXPORTER_OTLP_ENDPOINT=https://...
```

### Local Development

For local testing, set the endpoint manually:

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4317"
```

Or use a local collector like Jaeger:

```bash
# Start Jaeger with OTLP support
docker run -d --name jaeger \
  -p 16686:16686 \
  -p 4317:4317 \
  jaegertracing/all-in-one:latest

# Set endpoint
export OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4317"
```

## OpenTelemetry Span Attributes

Auto-instrumentation adds these attributes to spans:

| Attribute | Description |
|-----------|-------------|
| `gen_ai.usage.input_tokens` | Number of input tokens |
| `gen_ai.usage.output_tokens` | Number of output tokens |
| `gen_ai.usage.total_tokens` | Total tokens used |
| `gen_ai.request.model` | Model name |
| `gen_ai.system` | AI provider (e.g., "litellm") |

Custom attributes you add:

| Attribute | Description |
|-----------|-------------|
| `context.id` | Conversation/session ID |
| `query.length` | Input query length |
| `response.length` | Response length |
| `agent.type` | Your agent type identifier |

## Best Practices

1. **Use bootstrap**: Call `bootstrap(app)` after `app = server.build()` — it wires all instrumentation and middleware in one call
2. **Use Context Overlays**: Wrap operations for business context
3. **Track Token Usage**: Set `gen_ai.usage.input_tokens` / `gen_ai.usage.output_tokens` span attributes after each LLM interaction
4. **Add Meaningful Attributes**: Include IDs and metadata for debugging
5. **Handle Errors**: Wrap telemetry calls in try/except to avoid breaking business logic

## Troubleshooting

| Issue | Solution |
|-------|----------|
| No traces appearing | Ensure `bootstrap(app)` is called after `app = server.build()` |
| Token attributes missing from spans | Call `add_span_attribute` inside an active span context; check `result.usage()` returns data |
| Missing spans | Verify `OTEL_EXPORTER_OTLP_ENDPOINT` is set |
| Local traces not visible | Ensure Jaeger/collector is running |
