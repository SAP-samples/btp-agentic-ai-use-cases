# Joule Studio runtime Agent Bootstrap

Creates a ready-to-deploy AI agent asset for Joule Studio runtime with A2A protocol, LangGraph, and SAP AI Core integration.

**This skill operates on the current working directory.** The caller is responsible for running it from the correct target directory (e.g. `assets/<asset-name>/`).

## Instructions

Follow these 3 phases in order:

### Phase 1: Collect User Input

Use `question` tool if available or a similar tool that can be used to ask questions to the user to gather exactly 2 values BEFORE any file operations:

```
Question 1: "Please enter your agent name (e.g., expense-tracker-agent):"
Question 2: "Please enter your agent description (e.g., 'An AI agent that tracks business expenses'):"
```

**Example interaction:**

- User wants: "Create an agent to help with travel expenses"
- Agent name: `travel-expense-agent`
- Agent description: `An AI agent that helps employees manage and submit travel expenses`

### Phase 2: Copy Templates (Deterministic)

Use the skill base directory injected at load time (available at the bottom of this skill as `Base directory for this skill`). Set `SKILL_PATH` to that value and run:

```bash
set -euo pipefail
SKILL_PATH="<base-directory-for-this-skill>"
cp -r "$SKILL_PATH/templates/." ./
```

This produces `app/mcp_tools.py` — the owned indirection layer for MCP tool loading (see Output Structure below).

### Phase 3: Replace Placeholders (Deterministic)

Use a Python script to replace all placeholders. Derive the <...> placeholder values from the 2 inputs collected in Phase 1. Refer to "Placeholder Derivation Rules" section for more information.

**macOS/Linux** — run inline with a heredoc:

```bash
python - << 'PYEOF'
r = {
    "{{AGENT_TITLE}}": "<Agent Title>",
    "{{AGENT_DESCRIPTION}}": "<agent-description>",
    "{{AGENT_ID}}": "<agent-name>",
    "{{AGENT_NAME}}": "<agent-name>",
    "{{AGENT_SKILL_DESCRIPTION}}": "<agent-description>",
    "{{AGENT_CARD_DESCRIPTION}}": "<agent-description>",
    "[\"{{AGENT_TAGS}}\"]": "<tags-list>",
    "[\"{{AGENT_EXAMPLES}}\"]": "<examples-list>",
    "{{SYSTEM_PROMPT}}": "<system-prompt>",
}
for p in ["README.md", "app/main.py", "app/agent.py"]:
    t = open(p).read()
    for k, v in r.items(): t = t.replace(k, v)
    open(p, "w").write(t)
    print(f"Processed: {p}")
PYEOF
```

**Windows** — heredocs are not supported; save the script above to `replace_placeholders.py` (with values filled in) and run:

```powershell
python replace_placeholders.py
```

## Placeholder Derivation Rules

Derive all 10 placeholders from the 2 user inputs:

| Placeholder                     | Derivation                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 | Example Value                                                                                                                                                                                                                                                          |
| ------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `{{AGENT_NAME}}`              | Direct from input                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | `travel-expense-agent`                                                                                                                                                                                                                                               |
| `{{AGENT_NAMESPACE}}`         | Same as AGENT_NAME                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         | `travel-expense-agent`                                                                                                                                                                                                                                               |
| `{{AGENT_ID}}`                | Same as AGENT_NAME                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         | `travel-expense-agent`                                                                                                                                                                                                                                               |
| `{{AGENT_TITLE}}`             | Title-case: replace`-` with space, capitalize                                                                                                                                                                                                                                                                                                                                                                                                                                                            | `Travel Expense Agent`                                                                                                                                                                                                                                               |
| `{{AGENT_TAGS}}`              | Split AGENT_NAME by`-` into Python list                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | `["travel", "expense", "agent"]`                                                                                                                                                                                                                                     |
| `{{AGENT_DESCRIPTION}}`       | Direct from input                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | `An AI agent that helps employees manage and submit travel expenses`                                                                                                                                                                                                 |
| `{{AGENT_SKILL_DESCRIPTION}}` | Same as AGENT_DESCRIPTION                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | `An AI agent that helps employees manage and submit travel expenses`                                                                                                                                                                                                 |
| `{{AGENT_CARD_DESCRIPTION}}`  | Same as AGENT_DESCRIPTION                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | `An AI agent that helps employees manage and submit travel expenses`                                                                                                                                                                                                 |
| `{{SYSTEM_PROMPT}}`           | Template:`You are {AGENT_DESCRIPTION}. Help users with their requests.\n\nIMPORTANT: You MUST use tools to retrieve live data. Never fabricate, guess, or invent data. Relay tool errors verbatim without adding suggestions.`<br /><br /> If a **Data Dependencies** section exists in this spec document with one or more Data Product ORD IDs, append **exactly** the following line — listing all ORD IDs as comma-separated values, using each ORD ID value exactly as written, do NOT add, infer, or substitute any other ORD IDs: `Use the DPQuery MCP to query the data products. You must always provide the ordids <ORD_ID_1>, <ORD_ID_2>.\n` (Do not use placeholders — use the actual ORD IDs from the Data Dependencies section) | `You are an AI agent that helps employees manage and submit travel expenses. Help users with their requests.\n\nIMPORTANT: You MUST use tools to retrieve live data. Never fabricate, guess, or invent data. Relay tool errors verbatim without adding suggestions.` |
| `{{AGENT_EXAMPLES}}`          | Generate 2 example prompts based on description                                                                                                                                                                                                                                                                                                                                                                                                                                                            | `["Help me submit a travel expense", "What are the expense policies?"]`                                                                                                                                                                                              |

## Customization

- **Tools**: Extend LangGraph in `agent.py`
- **A2A skills**: Add `AgentSkill` definitions in `main.py`
- **Runtime skills**: Place skill markdown files under `app/skills/` following this structure:

  ```
  app/skills/
  └── <skill-name>/
      ├── SKILL.md          ← required; must have YAML frontmatter with `name` and `description`
      └── <other assets>    ← optional supporting files accessible via the `load` tool
  ```

  The agent exposes a `load(path)` tool (implemented in `load_skill_resources.py`) that resolves paths relative to `app/skills/`. Use it to read skill files at runtime.

  For the required SKILL.md frontmatter and body structure, see the template at:
  `$SKILL_PATH/references/skill-template.md`

## Token efficiency

The generated agent has several pre-wired cost controls. These can all be overridden via the agent's configuration (the `@agent_config` / `@agent_model` keys in `agent.py`):

- **Prompt caching** — the static prefix (system prompt + tool schemas) is cached at 0.1× input token cost after the first turn. Requires a byte-stable system prompt; do not conditionally append text to it at runtime.
- **Summarization** — conversation history is summarized by a cheaper model (`sap/anthropic--claude-4.5-haiku`) once it exceeds 30k tokens, keeping only the last 4 messages in full. Tune `config.summarization.trigger_tokens` to trade context quality against cost.
- **MCP response trimming** — tool responses are JSON-minified and capped at 30k chars before entering context. Override with `MCP_MAX_RESPONSE_CHARS` env var.
- **Runtime skill descriptions** — the `load` tool exposes every skill under `app/skills/` by name and description on every turn. Keep skill `description` fields tight; a bloated description is a fixed per-turn cost.
- **Model** — the default `sap/anthropic--claude-4.5-sonnet` is suitable for general-purpose agents. For simpler/deterministic tasks, a smaller model costs less per verified outcome.

## Model fallback & resilience

The generated agent runs on a single primary model (`config.model`) by default; **model fallback is disabled**. To enable it, set `config.fallback_models` to a comma-separated, ordered list of models (first listed is tried first). Each fallback model must be available in the deployment's region, so leaving it empty is the safe default. This is the client-side complement to SAP AI Core orchestration's per-request fallback: orchestration switches models on transient failures within a single request, whereas the agent keeps cross-request memory of a failing model.

That memory is a per-model circuit breaker (`app/circuit_breaker.py`): once a model records `config.circuit_breaker.failure_threshold` consecutive transient failures it is skipped for `config.circuit_breaker.cooldown_seconds` instead of being re-tried (and re-timed-out) on every request, then probed once to test recovery. Set the failure threshold to 0 to disable the breaker. Only transient errors (timeout, rate limit, 5xx, connection) count toward fallback or the breaker; other errors propagate immediately.

## ⚠️ Important: Dependencies

**Note:** Dependencies listed in `requirements.txt` are NOT installed during the bootstrap process. They will be installed:

- **In the cluster**: Automatically during the deployment process via CI/CD pipeline

The bootstrap process only creates the project structure and configuration files. No local Python environment setup is performed at this stage.

## ⚠️ Known Deployment Gotchas

These issues have caused real deployment failures and are proven to break the agent on the platform:

1. **`set_aicore_config()` must be called first** — it must be called at the very top of `main.py`, before any AI framework imports (LangChain, LiteLLM, etc.). Call `bootstrap(app)` after the app is built to wire all telemetry and middleware in one step.
2. **MCP tool loading via `get_mcp_tools()` must be async and lazy** — `get_mcp_tools()` is async and makes real network calls to the Agent Gateway. It cannot be called from `__init__()` and cannot be made sync. The correct pattern is:

   ```python
   from mcp_tools import get_mcp_tools

   async def _load_tools():
       return await get_mcp_tools()

   async def _get_graph(self):
       if self._graph is None:
           tools = await _load_tools()
           self._graph = create_agent(self.llm, tools=tools, system_prompt=get_system_prompt())
       return self._graph
   ```

   If MCP tools are loaded in `__init__()`, the HTTP server cannot start before the startup probe fires, causing the container to be killed.
3. **All imports inside `app/` must use peer-level style** — use `from matching import ...`, `from tools import ...`, never `from app.xxx import ...`.

## asset.yaml Gotchas

`asset.yaml` and `solution.yaml` creation are NOT part of this skill, and are the responsibility of the`setup-solution` skill.

## Next Steps

After bootstrapping completes, return control to the calling skill to continue implementation. Do not prompt the user with interactive options — this skill is only invoked as part of the automated `specification` skill.

## Multi-Asset: Update existing n8n workflows

If the solution already contains one or more n8n workflow files (`.n8n.json`) with `CUSTOM.sapAgent` nodes, update the `agents` parameter on every such node to include the newly bootstrapped agent. Every SAP Agent node must always reflect the full list of solution agents — including agents that were added after the workflow was first created.

The `agents` value is a JSON-serialized string. Add the new agent to the existing array:
```json
"agents": "[{\"ordId\":\"<existing-agent-ordId>\",\"name\":\"<existing-agent-name>\"},{\"ordId\":\"<new-agent-ordId>\",\"name\":\"<new-agent-name>\"}]"
```

The agent's ORD ID for `agents` / `agentName` uses the `agent` resource type, **not** `apiResource`. Derive it by taking the `provides.apis[].ordId` from the agent's `asset.yaml` and replacing `apiResource` with `agent`:

```
customer.build:apiResource:<solution>.<asset>:v1  →  customer.build:agent:<solution>.<asset>:v1
```

## Multi-Asset: Wire up workflow MCP servers

After bootstrapping completes, scan the solution for workflows that this agent should call. Two sub-cases apply.

> **Scope**: these sub-cases run once, at bootstrap time, as a best-effort check based on whatever assets already exist in the solution. They are not re-executed later. The primary enforcement of MCP wiring — covering any ordering (agent-first or n8n-first) — is through the dedicated checklist items in the active `specification.md` for both the agent and the n8n workflow skills. If you find wiring is missing after both assets exist, address it through those spec tasks, not by re-running bootstrap.

### Sub-case 1 — MCP server already exists

A workflow MCP server asset exists when there is a folder under `assets/` whose name ends with `-mcp-server` and whose `asset.yaml` has a top-level `type: mcp-server` and a `provides.apis[]` entry with `kind: mcp-server`:

```yaml
apiVersion: asset.sap/v1
kind: Asset
type: mcp-server

metadata:
  name: leave-request-workflow-mcp-server

provides:
  apis:
    - name: leave-request-submitted-mcp-server
      kind: mcp-server
      ordId: sap.n8nwfrt:apiResource:my-solution_leave-request-workflow.leaveRequestSubmitted_mcp:v1
```

For each such mcp-server asset found, add a `requires` entry to the newly created agent's `asset.yaml` **only if** the agent's specification (intent.md, PRD, tasks.md, or the agent description collected in Phase 1) indicates that this agent should call, trigger, or invoke that workflow. A workflow MCP server being present in the solution does not automatically mean this agent depends on it — only add the `requires` entry when there is a clear intent for the agent to invoke the workflow.

```yaml
requires:
  - name: <workflow-name>-mcp-server
    kind: mcp-server
    ordId: <mcp-card-ordId>   # from the mcp-server's asset.yaml provides.apis[].ordId
                               # (REST ORD ID with _mcp appended to apiName segment — ADR-021 §8.1)
```

### Sub-case 2 — Workflow exists with webhook trigger but no MCP server yet

A workflow may have been generated without an MCP server (for example, because no agent existed at the time). Detect this case by checking every workflow `asset.yaml` under `assets/workflows/`: if it contains a `provides.apis[]` entry with `kind: rest` (indicating a webhook trigger) and there is **no** corresponding `*-mcp-server` folder under `assets/`, the MCP server was never generated.

For each such workflow **only if** the agent's specification indicates this agent should call it, generate the MCP server now by completing Steps A–E from the **"MANDATORY when applicable: Generate MCP server for in-solution agent consumption"** section of `skills/n8n-workflow/references/execution.md`. After those steps complete, add the `requires` entry to this agent's `asset.yaml` using the same `<mcp-card-ordId>` as shown in Sub-case 1 above.

This covers the case where the n8n workflow (and its MCP server) was generated **before** the agent was bootstrapped. The n8n-workflow skill's MANDATORY-when-applicable step handles the reverse ordering — when the agent already exists at the time the workflow is generated, it updates the agent's `asset.yaml` directly (Step F of that section).

### After wiring — update the agent's system prompt

After adding the `requires` entry (Sub-case 1 or 2), update `app/agent.py` in this agent's directory to instruct the agent to use the MCP tool rather than calling the webhook URL directly. Append a sentence to the system prompt such as:

> To invoke the `<workflow-name>` workflow, use the `<tool-name>` MCP tool. Do not call workflow webhook URLs directly.

Derive `<tool-name>` from the MCP card ORD ID: take the `apiName` segment (e.g. `leaveRequestSubmitted_mcp`), then strip the `_mcp` suffix → `leaveRequestSubmitted`.
