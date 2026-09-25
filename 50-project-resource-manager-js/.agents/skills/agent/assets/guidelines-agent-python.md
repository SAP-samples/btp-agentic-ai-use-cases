# Python Agent Implementation Guidelines

Python-specific constraints and patterns for implementing Pro-Code AI Agents. Follow these throughout specification execution.

For universal agent patterns, see [guidelines-agent.md](./guidelines-agent.md).

## Tech Stack

- Python 3.13
- Agent framework defined in the `sap-agent-bootstrap` skill
- LangChain 1.0+ / LangGraph
- Agent2Agent (A2A) protocol
- Local execution only (in-memory storage, no deployment)

## Project Structure

- Asset root: `assets/<asset-name>/`
- Required structure: `asset.yaml`, `app/`
- Full layout from project root: `solution.yaml`, `assets/<asset-name>/asset.yaml`, `assets/<asset-name>/app/`
- `asset.yaml` must use `buildPath: .` and `/.well-known/agent.json` for all health probes
- Follow the `sap-agent-bootstrap` skill for project scaffolding — invoke directly from `assets/<asset-name>/`, use copy commands

## Key Constraints

- When working with LangChain or LangGraph, you MUST NEVER use the `create_react_agent` function (`from langgraph.prebuilt import create_react_agent`) as it has been deprecated in LangChain 1.0. Instead, you should use the `from langchain.agents import create_agent` function.
- Only use public APIs; mock any private systems (like S/4HANA) with minimal mock data
- AI Core is available at **runtime** via LiteLLM (environment variables provided at deployment) but is **NOT available during tests** — all LLM calls must be mocked
- No Git operations, no authentication, no documentation/READMEs
- Update `requirements.txt` for any new dependencies
- Never modify `sys.path`
- Map SAP Joule Studio/Skills concepts to standard agent tools
- No `.env` files (environment variables supplied at runtime)

## Code Quality

- All Python code must compile with valid imports
- No `src.` import patterns
- All function parameters must be used in function body

## Agent Decorators

- The bootstrap template already includes decorator scaffolding — no separate skill invocation needed
- **NEVER add new decorated functions to `app/agent.py`** — the five from the bootstrap template (`@agent_model` for primary model, `@agent_model` for fallback model, `@agent_config` for temperature, `@agent_config` for agent memory TTL, `@prompt_section`) are the complete and final set. `@agent_config` is not a general-purpose decorator; it exposes parameters to the SAP platform UI and is intentionally limited to temperature and agent memory TTL. All other values (thresholds, limits, counts, etc.) must be plain Python constants.
- Never mark decorator tasks complete until `sap_cloud_sdk.agent_decorators` imports exist in `app/agent.py`

## Agent Instrumentation (Python Implementation)

- ALL business logic steps MUST be instrumented with proper logging and OpenTelemetry spans
- Use milestones from the PRD's "Milestones" section (if available) or derive from the project input for business step instrumentation
- Each milestone must emit structured log statements on achievement and miss
- Log pattern: `[MILESTONE_ID].[achieved|missed]: [description]`
- Add OpenTelemetry custom spans for each business step using `tracer.start_as_current_span` — use the **decorator form** (`@tracer.start_as_current_span("name")`) on regular async methods, or the **context manager form** (`with tracer.start_as_current_span("name"):`) inside non-generator async functions
- **NEVER use `with tracer.start_as_current_span(...)` as a context manager inside an async generator** (i.e. any method containing `yield`). Doing so causes `ValueError: Token was created in a different Context` when the generator is closed via `GeneratorExit`. For `stream()`, extract all business logic into a plain async helper method (e.g. `_run_agent()`) and instrument that method instead, then call it from `stream()` and yield the result outside any span context.
- Ensure `bootstrap(app)` is called after `app = server.build()` in `main.py`

## MCP Tool Loading (Python Implementation)

For universal MCP patterns, see [guidelines-agent-mcp.md](./guidelines-agent-mcp.md).

**If your spec's `## Data Dependencies` has only Data Product ORD IDs:** skip this section (MCP Tool Loading).

### Canonical Pattern

```python
from mcp_tools import get_mcp_tools

async def _load_tools() -> list:
    return await get_mcp_tools()
```

`mcp_tools.py` is the owned indirection layer produced by the bootstrap — import from there, never directly from `sap_cloud_sdk.agentgateway`. This is the target the test fixture patches.

Call `_load_tools()` lazily (not in `__init__`) — it makes network calls. Wire the result into the agent graph:

```python
class MyAgent:
    def __init__(self):
        self._tools = None

    async def _get_tools(self) -> list:
        if self._tools is None:
            self._tools = await _load_tools()
        return self._tools

    async def stream(self, query, context_id, ext_impl=None):
        tools = await self._get_tools()
        graph = self._build_graph(tools, system_prompt=get_system_prompt())
        ...
```

### Local Testing (IBD_TESTING)

**If your spec's `## Data Dependencies` has only Data Product ORD IDs:** skip this subsection entirely (Local Testing / IBD_TESTING).

**Do NOT branch on `IBD_TESTING` in application code.** The `conftest.py` monkey-patches `mcp_tools.get_mcp_tools` before any agent code runs. Agent code stays identical in production and tests.

The patch returns `StructuredTool` instances built from `mcp-mock.json`. Generate `mcp-mock.json` with the `mcp-mock-config` skill before running tests.

## Testing

Working directory for all test operations: `assets/<asset-name>/` (asset root).

### Setup

1. Install test dependencies: `pip install -r requirements-test.txt`

### Boilerplate Files

- `conftest.py` — shared fixtures, custom markers, writes `test_report.json` on full runs
- `pytest.ini` — configures test discovery (`prebuilt_tests/`, `tests/`), default flags, markers
- `requirements-test.txt` — test dependencies
- `prebuilt_tests/` — pre-built structure and server tests; NEVER modify these

### Writing Tests

- All generated tests go in `assets/<asset-name>/tests/` (NOT inside `app/`)
- Unit tests: exactly one per tool; run each immediately after writing
- Integration test: one end-to-end test exercising the full agent graph
- **AI Core / LLM calls MUST be mocked in all tests.** AI Core credentials are NOT available in the test environment. Patch the LLM (e.g. `ChatLiteLLM`) to return canned responses. Never make real network calls to AI Core during tests.
- Mock all external systems (S/4HANA, MCP servers, AI Core) — tests must run offline

### Running Tests

- ALWAYS invoke as just `pytest` from asset root — no paths, no `--cov`, no `--json-report`, no extra flags
- `pytest.ini` configures everything; extra CLI flags conflict with ini settings
- Only exception: targeting a single test: `pytest path/to/test_file.py::test_name`
- Coverage must be ≥ 70%; if below, add targeted tests until threshold met
- Final `pytest` run (no args) MUST produce `test_report.json` — this only happens on full runs without arguments

## Validation Checklist

Run these verifications before marking implementation complete:

```bash
# Instrumentation
grep -r "M[0-9]\.achieved" assets/<asset-name>/app/     # must return results

# Decorators
grep -r "sap_cloud_sdk.agent_decorators" assets/<asset-name>/app/  # must return results
grep -c "^@agent_model\|^@agent_config\|^@prompt_section" assets/<asset-name>/app/agent.py  # must return 5 (two @agent_model for primary and fallback, two @agent_config for temperature and TTL, one @prompt_section)

# Test report
ls assets/<asset-name>/test_report.json                  # must exist
```

## Agent Evaluation (Post-Implementation)

Run after all tests pass and the agent is working locally.

### Prerequisite: `mcp-mock.json`

The `agent-evaluation` skill reads the agent's tools from `mcp-mock.json` at the asset root —
the same file `conftest.py` uses for local testing. Generate it with the `mcp-mock-config`
skill first if it does not exist.

Its deterministic `mock_response` values are what let the generated tests assert real
expected amounts and identifiers instead of placeholders, so generating it first materially
improves the suite.

### Generate the evaluation

Invoke the `agent-evaluation` skill and ask it to generate eval scenarios, passing the source
document path (e.g. `product-requirements-document.md` at the solution root, or
`specification/<asset-name>/specification.md`).

It resolves its own output location and always writes into the agent's asset folder,
regardless of where the source document sits or which directory you invoke it from. One flow
writes all three artifacts:

- `assets/<asset-name>/aeval/eval.yaml` — the evaluation criteria
- `assets/<asset-name>/aeval/testcases/<id>.yaml` — one dynamic conversation test case per scenario
- `assets/<asset-name>/aeval/config.yaml` — run parameters for scoring live sessions

The location matters: the business-outcome scorers read `assets/*/aeval/eval.yaml`, so an
`aeval/` folder written beside `assets/` scores zero however good its contents are.

Each test traces back to a criterion, and each criterion to the PRD. The skill reports
coverage as counts — source requirements covered by a criterion, criteria covered by a test,
and user journeys covered by a happy path — plus a dimension gap report naming behaviour
worth testing that the PRD never asked for.

Test cases are `dynamic_conversation` steps driven by a simulated user, with the concrete
identifiers and amounts in `user_agent.task_summary` and the expected values asserted in the
validation blocks. Review them before running evaluations, and check the report for any tool
lacking a `mock_response` — those tests assert parameters but not output.
