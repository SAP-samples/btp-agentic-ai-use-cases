# Specification: {{asset-name}}

> **Guidelines**: Read all applicable guidelines before executing ANY tasks below:
> - [guidelines.md](../guidelines.md) — Universal execution rules
> - [guidelines-agent.md](../guidelines-agent.md) — Universal agent patterns
> - [guidelines-agent-python.md](../guidelines-agent-python.md) — Python implementation details
> - [guidelines-agent-skills.md](../guidelines-agent-skills.md) — Runtime skills patterns
> - [guidelines-agent-mcp.md](../guidelines-agent-mcp.md) — MCP integration patterns

---

## Basic Setup

- [ ] Read the project input (`product-requirements-document.md`, `intent.md`, or the user prompt that triggered this specification)
- [ ] **If a Data Product ORD ID is recorded in the `Data Product ORD ID` column of the Fit Gap Analysis in `intent.md`**: copy it exactly into the **Data Dependencies** section of this spec document:
  ```
  ## Data Dependencies
  - Data Product ORD ID: <exact value from intent.md fit-gap table>
  ```
  Use this section as the authoritative source for ORD IDs during bootstrap — do NOT re-read `intent.md` for ORD IDs after this point.
- [ ] Bootstrap agent code in `assets/{{asset-name}}/` using instructions from the sap-agent-bootstrap section. (invoke from inside `assets/{{asset-name}}/`, use copy commands — do NOT create files manually)
- [ ] **If `## Data Dependencies` has Data Product ORD IDs**: open `assets/{{asset-name}}/app/agent.py`, find the `@prompt_section` body(get_system_prompt), and confirm it contains exactly: `Use the DPQuery MCP to query the data products. You must always provide the ordids <ORD_IDs>.` with the actual ORD IDs from this spec's `## Data Dependencies` section. If missing, add it.
- [ ] Install dependencies, validate the agent starts and responds at `/.well-known/agent.json`

---

## Runtime Skills

> **Before proceeding**, read [guidelines-agent-skills.md](../guidelines-agent-skills.md) and decide — based on the PRD/intent — whether the agent needs runtime skills.

**When to create runtime skills:**
- Complex multi-step workflows (approval processes, escalation paths)
- Domain-specific knowledge (compliance rules, validation constraints)
- Task-specific instructions that would bloat the system prompt
- Reference material needed (templates, lookup tables, examples)

**If runtime skills are needed:**

- [ ] For each identified skill domain, create `assets/{{asset-name}}/app/skills/<skill-name>/SKILL.md` with:
  - YAML frontmatter: `name`, `description`, optional `allowed-tools`
  - Body: Step-by-step instructions with decision criteria
  - Companion asset files as needed (`references/`, `examples/`, `templates/`)

> For the required SKILL.md frontmatter and body structure, see the template at `references/skill-template.md` in the agent skill.

---

## Project-Specific Tasks

{{project-specific-tasks}}

---

## Business Instrumentation

- [ ] Implement business step instrumentation for each milestone from the PRD: structured logging with pattern `[MILESTONE_ID].[achieved|missed]: [description]` and OpenTelemetry custom spans. See [guidelines-agent-python.md](../guidelines-agent-python.md) for Python-specific implementation (extract business logic from `stream()` into a plain async helper to avoid `GeneratorExit` context errors).
- [ ] Verify `bootstrap(app)` is called after `app = server.build()` in `main.py`

---

## MCP Tool Integration

> Read [guidelines-agent-mcp.md](../guidelines-agent-mcp.md) for complete MCP integration patterns.
> Tasks below are valid if any SAP API integration exists.

- [ ] **If Data Product ORD IDs are in `## Data Dependencies`**: add only DPQuery to `asset.yaml requires` — do NOT call `get_mcp_tool_details` for Data Product ORD IDs and do NOT create new MCP servers to access Data Products and do NOT add them to `requires` (they are data assets, not MCP servers):
  ```yaml 
  requires:
    - name: dpquery 
      kind: mcp-server 
      ordId: sap.bdc.dpq:apiResource:mcp-dpquery:v1 
  ```
  **If ALL `## Data Dependencies` rows are Data Product ORD IDs (no direct API ORD IDs), skip the next 5 tasks.**
- [ ] During API discovery, if Step 2b was pursued, verify `api-discovery-results.md` exists at workspace root with ORD IDs for all required APIs
- [ ] If `specification/{{asset-name}}/api-specs/` exists, invoke `mcp-translation-file` skill, then invoke `setup-solution` to create/register MCP assets — skip both if `mcp-translation-file` is not available in this environment
- [ ] Wire MCP tool loading in `agent.py` using `get_mcp_tools()` from the `mcp_tools` module (the bootstrap-generated indirection layer) — see [guidelines-agent-python.md](../guidelines-agent-python.md) for canonical pattern. NEVER import directly from `sap_cloud_sdk.agentgateway`. NEVER create direct HTTP clients for SAP APIs. NEVER implement custom tool files for SAP API access.
- [ ] Add MCP server dependencies to `asset.yaml` under `requires` — one entry per MCP server, using exact ORD IDs from generated assets (Path A) or API discovery (Path B). See [guidelines-agent-mcp.md](../guidelines-agent-mcp.md) for format. **EXCLUDE `dpca-mcp-server` — it is a build-time tool used during data product discovery, not a runtime dependency for the agent.**
- [ ] Lastly, after `mcp-specs` were generated and/or `mcp-translation-file` completed generating the new MCP assets, generate `mcp-mock.json` using the `mcp-mock-config` skill (required before tests can run). If `mcp-translation-file` was skipped (unavailable) and no `mcp-specs/` exist either, skip mock generation.
- [ ] **Path C — In-solution n8n workflow via MCP**: if the intent (PRD, `intent.md`, tasks.md) indicates this agent should invoke an n8n workflow in the same solution:
  - Check `solution.yaml` for a `<workflow-name>-mcp-server` asset. If it does not exist yet, the n8n workflow skill must complete Steps A–F first — do not proceed with wiring until that asset is present.
  - If the asset exists: add a `requires` entry to `asset.yaml` with the `_mcp` ORD ID from that mcp-server's `provides.apis[]`. Derive `<tool-name>` by taking the `apiName` segment of the `_mcp` ORD ID and stripping the `_mcp` suffix.
  - Append a system prompt instruction to `app/agent.py` telling the agent to use the MCP tool (not the webhook URL directly).
  - See `guidelines-agent-mcp.md` Path C section for the full format.

---

## Testing

> See [guidelines-agent-python.md](../guidelines-agent-python.md) for Python testing setup and patterns.

- [ ] `conftest.py` only sets `IBD_TESTING=true` — this causes the agent to run with mock MCP tool results during tests
- [ ] Write unit tests in `assets/{{asset-name}}/tests/` — exactly one per tool, run each immediately after writing
- [ ] Write one integration test executing end-to-end agent flow by calling the agent's `invoke` function with mocked LLM responses and mocked external systems (tests must run offline)
- [ ] Run `pytest` from `assets/{{asset-name}}/` (no args, no extra flags — `pytest.ini` configures everything) — if coverage < 70%, add tests until threshold met
- [ ] Verify `assets/{{asset-name}}/app/agent.py` has exactly 9 decorated functions from the bootstrap template (`@agent_model` for primary model, `@agent_model` for the fallback model chain, `@agent_model` for the summarization model, `@agent_config` for temperature, `@agent_config` for agent memory TTL, `@agent_config` for the summarization trigger, `@agent_config` for the circuit breaker failure threshold, `@agent_config` for the circuit breaker cooldown, `@prompt_section`) — run `grep -c "^@agent_model\|^@agent_config\|^@prompt_section" assets/{{asset-name}}/app/agent.py` and confirm it returns 9. If it returns more than 9, remove the extra decorators and replace them with plain Python constants
- [ ] Run `pytest` again from `assets/{{asset-name}}/` (no args) to generate final `test_report.json`
- [ ] Verify `test_report.json` exists in `assets/{{asset-name}}/` — if not, run pytest again until it does. The test report is automatically generated according to the `pytest.ini` and `conftest.py` when all tests are executed by running `pytest` with no extra args.
