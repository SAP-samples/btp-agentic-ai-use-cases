# n8n SAP Agent Node Generation

## Overview

Ensures correct generation of **SAP Agent** nodes for orchestrating AI agents from n8n workflows. It covers agent invocation, parameter passing, response handling, and integration with other workflow nodes.

**Critical Mission:** Enable workflows to invoke SAP AI agents and process their responses, creating powerful agent-workflow orchestration patterns.

---

## CRITICAL RULES (Never Skip)

### 1. **ALWAYS use MCP to get node metadata**

**BEFORE generating an SAP Agent node:**
```javascript
// Call MCP tool
search-nodes-catalog("SAP Agent")
// If not found, fallback to:
search-nodes-catalog("AI Agent")
```

**Use the returned values:**
- `name` → use as `type` in workflow
- `version` → use as `typeVersion` in workflow
- `properties` → use to understand available parameters

**NEVER hardcode typeVersion** - always get it from MCP.

**NEVER include `globalTenantId`** anywhere in the workflow JSON. Do not add it to `agentName` or `agents`; Managed n8n resolves it at execution time through UMS (User Management Service).

**NEVER add extra fields** to `agentName`. Only use `{ ordId, name }`.

**ALWAYS put `ordId` before `name`** in every serialized object. The SAP Agent node parses the JSON by key order; if `name` comes first, the agent is not recognized. This applies to every entry in `agents` and to `agentName`. For `agents` entries the required key order is `ordId`, `name`, `description` (description is optional but must come last if included).

---

### 2. **SAP Agent Node Purpose**

The SAP Agent node allows workflows to:
- ✅ Invoke AI agents from n8n
- ✅ Pass context and parameters to agents
- ✅ Receive agent responses
- ✅ Process agent outputs in subsequent nodes
- ✅ Orchestrate multiple agents in sequence

---

### 3. **SAP Agent is for Reasoning Only — NOT for Fetching or Writing SAP Data**

The SAP Agent node invokes an AI agent to analyze, generate, or decide. It is **not** a mechanism for performing SAP API operations.

❌ **Do NOT:**
- Ask the agent to "fetch" or "look up" SAP data inside its prompt — the agent has no direct SAP connection
- End the agent branch with a Set node that logs the agent's decision (nothing reaches SAP)

✅ **DO:**
- Pre-fetch SAP data with a `CUSTOM.sapMcpClient` node **before** the agent runs
- Pass the fetched data into the agent's `input`
- After the agent responds, use another `CUSTOM.sapMcpClient` node to execute the SAP action

**Required separation pattern:**
```
SAP MCP Client (fetch data from SAP)
    ↓
SAP Agent (analyze / decide based on fetched data)
    ↓
SAP MCP Client (execute the SAP action)
```

---

### 4. **Mandatory Parameters**

**Always required:**
- `agents` (string, hidden) — JSON-serialized array of all agents in the solution. This powers the editor dropdown at design time and must be present even when only one agent exists. Each entry must use this exact key order: `ordId`, `name`, `description` (description is optional but must come last if included). Do not include any other fields. **Key order matters: `ordId` must come before `name` or the agent node will not recognize the entry.**
- `agentName` (string) — JSON-serialized object containing only `{ ordId, name }` for the agent to invoke, with `ordId` first. Do not include `globalTenantId`, `id`, or `description`. **Key order matters: `ordId` must come before `name`.**
- `input` — Prefer a string for prompt-style input. Use an expression that resolves to an object only when the MCP `properties` metadata explicitly supports structured input.
- `sessionId` (string, optional but recommended) - Preserves conversation continuity

> **When a new agent is added to the solution**: update the `agents` array on **every existing SAP Agent node** in the workflow to include the new agent. Every node must always reflect the full list of solution agents.
>
> **When an agent is removed from the solution**: update the `agents` array on **every existing SAP Agent node** to exclude the removed agent. Verify no `agentName` still targets its `ordId`.

**Guidance:**
- Use a string expression for prompt-style inputs
- Use an expression that resolves to an object only when confirmed by `properties` from MCP
- Note: expression syntax `={{ ... }}` is distinct from JSON shape — the expression is evaluated at runtime to produce the actual object

**Example with string input (preferred for prompts):**
```json
{
  "type": "<from MCP>",
  "typeVersion": "<from MCP>",
  "name": "Invoke AP Invoice Agent",
  "parameters": {
    "agents": "<serialised JSON string — see shape below>",
    "agentName": "<serialised JSON string — see shape below>",
    "input": "={{ $json.invoiceText }}",
    "sessionId": "={{ $json.requestId }}"
  }
}
```

**Logical shape of `agents` and `agentName` (both must be serialised as JSON strings in the workflow):**

> ⚠️ **Key order is significant.** The SAP Agent node parses by key order. Required order is `ordId` → `name` → `description` (description optional, but must be last). Reversed order (`name` first) causes the agent to not be recognized.

```json
{
  "agents": [
    {
      "ordId": "customer.build:agent:finance:v1",
      "name": "Finance Agent",
      "description": "Handles finance queries"
    }
  ],
  "agentName": {
    "ordId": "customer.build:agent:finance:v1",
    "name": "Finance Agent"
  }
}
```

> Both `agents` and `agentName` are stored as JSON-serialised strings in the n8n workflow JSON. The logical shapes above show the object structure before serialisation.

**Example with object input (only if MCP properties confirm support):**
```json
{
  "type": "<from MCP>",
  "typeVersion": "<from MCP>",
  "name": "Invoke AP Invoice Agent",
  "parameters": {
    "agents": "<serialised JSON string — same shape as above>",
    "agentName": "<serialised JSON string — same shape as above>",
    "input": "={{ ({ invoiceData: $json.invoiceData, source: $json.source }) }}",
    "sessionId": "={{ $json.requestId }}"
  }
}
```

---

### 5. **Agent Orchestration Patterns**

#### Pattern 1: Single Agent Invocation
```
Webhook → SAP Agent → Process Response → Respond
```

#### Pattern 2: Sequential Multi-Agent
```
Trigger → Agent 1 (Analysis) → Agent 2 (Action) → Agent 3 (Verification) → Done
```

#### Pattern 3: Agent + HITL (Human-in-the-Loop)
```
Webhook → SAP Agent → Check Confidence → [Low: Task Center, High: Auto-process]
```

#### Pattern 4: Agent + Error Handling
```
Webhook → SAP Agent → Check Result → [Error: Task Center for manual review]
```

---

### 6. **Agent Response Handling**

Agent responses typically include:
```json
{
  "response": "...",      // Agent's text response
  "confidence": 0.95,     // Confidence score
  "actions": [],          // Actions taken by agent
  "metadata": {}          // Additional context
}
```

**Always check confidence/success before proceeding:**
```json
{
  "type": "n8n-nodes-base.if",
  "name": "Check Confidence",
  "parameters": {
    "conditions": {
      "conditions": [{
        "leftValue": "={{ $json.confidence }}",
        "rightValue": 0.8,
        "operator": { "type": "number", "operation": "gte" }
      }]
    }
  }
}
```

---

## Common Errors to Avoid

❌ **ERROR 1:** Not handling agent errors
```
Agent → Process Response → Done
// No error handling
```
✅ **FIX:** Add error/confidence check
```
Agent → Check Success → [Error: Notify/Escalate, Success: Continue]
```

---

❌ **ERROR 2:** Losing context in multi-agent flows
```json
"input": "={{ $json.data }}"  // Only has current node data
```
✅ **FIX:** Reference previous nodes
```json
"input": {
  "currentData": "={{ $json.data }}",
  "previousAnalysis": "={{ $('Agent 1').item.json.analysis }}"
}
```

---

❌ **ERROR 3:** Adding a new agent but not updating existing SAP Agent nodes
```json
// Node 1 — agents only lists the original agent, new agent is missing
"agents": "[{\"ordId\":\"...invoice-agent:v1\",\"name\":\"Invoice Agent\"}]"
```
✅ **FIX:** When a new agent is added to the solution, update `agents` on every existing SAP Agent node to include it
```json
"agents": "[{\"ordId\":\"...invoice-agent:v1\",\"name\":\"Invoice Agent\"},{\"ordId\":\"...approval-agent:v1\",\"name\":\"Approval Agent\"}]"
```

---

❌ **ERROR 4:** Using the `apiResource` ORD ID (from the agent's `provides` section) instead of the `agent` ORD ID — applies only to **same-solution agents**
```json
// WRONG — ordId copied directly from provides.apis[].ordId in asset.yaml
"agents": "[{\"ordId\":\"customer.build:apiResource:my-solution-3f8a1.invoice-agent:v1\",\"name\":\"Invoice Agent\"}]"
"agentName": "{\"ordId\":\"customer.build:apiResource:my-solution-3f8a1.invoice-agent:v1\",\"name\":\"Invoice Agent\"}"
```
✅ **FIX:** For same-solution agents, derive the ORD ID by taking `provides.apis[].ordId` from the agent's `asset.yaml` and replacing `apiResource` with `agent`:
```json
"agents": "[{\"ordId\":\"customer.build:agent:my-solution-3f8a1.invoice-agent:v1\",\"name\":\"Invoice Agent\"}]"
"agentName": "{\"ordId\":\"customer.build:agent:my-solution-3f8a1.invoice-agent:v1\",\"name\":\"Invoice Agent\"}"
```
The agent's `asset.yaml` `provides.apis[].ordId` uses `apiResource` — that is the ORD ID the agent *exposes*. When a workflow *references* the agent, it must use the `agent` resource type instead.

> **Pre-deployed agents (registered in UMS, not part of this solution):** their ORD ID is already in the correct `customer.build:agent:...` format and is selected by the user from the n8n editor dropdown — no derivation needed.

---

❌ **ERROR 5:** Removing an agent but leaving it in the `agents` array
```json
// Node still lists the deleted agent in agents
"agents": "[{\"ordId\":\"...invoice-agent:v1\",\"name\":\"Invoice Agent\"},{\"ordId\":\"...deleted-agent:v1\",\"name\":\"Deleted Agent\"}]"
```
✅ **FIX:** When an agent is removed from the solution, update `agents` on every existing SAP Agent node to exclude it. Also verify no `agentName` still targets the removed agent's `ordId`.

---

❌ **ERROR 6:** Logging the agent's decision with a Set node instead of posting it to SAP
```
SAP Agent → Set Node { "status": "approved" }   // WRONG — nothing reached SAP
```
✅ **FIX:** Use an SAP MCP Client node to execute the action in SAP after the agent decides:
```
SAP Agent → SAP MCP Client (post_approval_decision, { decision: "={{ $json.response }}" })
```

---

❌ **ERROR 7:** Embedding SAP data fetching inside the agent prompt without a preceding MCP Client node
```json
"input": "Fetch purchase order PO-12345 from S/4HANA and tell me if the budget is exceeded"
// WRONG — the agent has no direct SAP connection; nothing will be fetched
```
✅ **FIX:** Fetch the data with a dedicated SAP MCP Client node first, then pass the result to the agent:
```
SAP MCP Client (get_purchase_order, { poId: "PO-12345" })
    ↓
SAP Agent (input: "={{ $json.result }} — Is this PO over budget?")
```

---

## Testing Checklist

Before considering an Agent workflow complete:

- [ ] Used MCP `search-nodes-catalog` to get `typeVersion`
- [ ] `agents` parameter is present on every SAP Agent node, covering all solution agents
- [ ] `agents` and `agentName` use `customer.build:agent:...` ORD IDs derived from `asset.yaml` (`apiResource` → `agent`)
- [ ] `agentName` matches an existing solution agent, and every entry in `agents` keeps `ordId` before `name`
- [ ] Every entry in `agents` has `ordId` before `name`
- [ ] No `globalTenantId` appears anywhere in node parameters
- [ ] Input parameters are properly formatted
- [ ] No `credentials` block included in the workflow JSON — credentials are resolved automatically during deployment
- [ ] Response processing logic is in place
- [ ] Error handling implemented
- [ ] Agent node receives pre-fetched SAP data from an upstream MCP Client node — it does not fetch SAP data itself
- [ ] Any SAP action after the agent decision is executed by a downstream SAP MCP Client node, not a Set node
- [ ] Workflow validates with `validate-n8n-workflow` MCP
- [ ] If an agent was removed: `agents` array on every SAP Agent node no longer contains the removed agent's `ordId`
- [ ] If an agent was removed: no `agentName` still references the removed agent's `ordId`

---

## Integration with Other Node Generation Types

**Agent + Task Center:**
```
Agent → Check Confidence → [Low: Task Center HITL, High: Auto-process]
```
See: `../n8n-sap-task-center/n8n-sap-task-center.md`

**Agent + AI Core:**
```
AI Core (Analysis) → Agent (Action) → AI Core (Verification)
```
See: `../n8n-sap-ai-core/n8n-sap-ai-core.md`
