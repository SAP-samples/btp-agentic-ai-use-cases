---
name: n8n-workflow
description: Intent-based development asset. Writes or edits n8n workflow JSON files (.n8n.json). Do NOT generate any workflow or invoke this skill until intent.md exists.
metadata:
  version: 1.0.0
  author: sap-joule-studio
---

## Reference Files

### IBD Flow

| File | When to read | What it covers |
|---|---|---|
| [intent-analysis](./references/intent-analysis.md) | Always, first | Determines solution category and asset type from user intent |
| [setup-solution](./references/setup-solution.md) | Always, before generating | Asset scaffold: `asset.yaml` structure, naming rules, `requires` declarations |
| [execution](./references/execution.md) | MUST read to execute specification list | All rules for generating workflow JSON: node catalog, SAP node routing, validation, single Write call |
| [workflows-hooks](./references/workflow-hooks.md) | When building a pre/post hook workflow for A2A agent extension | Hook-specific rules: A2A message protocol, webhook trigger/response shape, hook patterns |

### n8n Node References

| File | When to read | What it covers |
|---|---|---|
| [n8n-expressions](./references/n8n-expressions/n8n-expressions.md) | MUST read when writing any node parameter with `{{ }}` expressions, `$json`, `$('Node Name')` references, Luxon date math, data transformation, or when a webhook workflow accesses request body fields or constructs a JSON response | Expression syntax, reference-by-node-name rules, method chains, Luxon date math, anti-patterns |
| [n8n-code-nodes](./references/n8n-code-nodes/n8n-code-nodes.md) | MUST read when any Code node is being written, evaluated, or justified; when the user reaches for JavaScript or Python; or when "transform data" / "custom logic" / "loop" comes up and the right tool is unclear | Last-resort principle, decision tree summary, Crypto/XML node traps, anti-patterns |
| [n8n-code-nodes-decision-tree](./references/n8n-code-nodes/n8n-code-nodes-decision-tree.md) | Read when using decision trees in code nodes; Prerequisite: n8n-code-nodes | Full 3-stage decision logic: expression → Edit Fields → Code node, with examples by category |
| [n8n-code-nodes-arrow-functions](./references/n8n-code-nodes/n8n-code-nodes-arrow-functions.md) | Read when using arrow functions in code nodes; Prerequisite: n8n-code-nodes | IIFE pattern, cross-item aggregation with Execute Once, performance tradeoffs, common mistakes |
| [n8n-code-nodes-javascript-patterns](./references/n8n-code-nodes/n8n-code-nodes-javascript-patterns.md) | Read when using JavaScript patterns in code nodes; Prerequisite: n8n-code-nodes | Run modes, return shape, available libraries, binary handling, error patterns, testing |
| [n8n-loops](./references/n8n-loops/n8n-loops.md) | MUST read when any looping, iteration, batching, rate limiting, or paginated API call is involved | Covers Loop Over Items node, HTTP Request pagination modes, and stateful iteration patterns |
| [n8n-loops-loop-over-items](./references/n8n-loops/n8n-loops-loop-over-items.md) | Read when configuring the Loop Over Items node; Prerequisite: n8n-loops | Configuring the Loop Over Items node, batching, rate limiting, stateful iteration |
| [n8n-loops-http-pagination](./references/n8n-loops/n8n-loops-http-pagination.md) | Read when calling a paginated API; Prerequisite: n8n-loops | Calling a paginated API, configuring HTTP Request pagination modes |
| [n8n-sap-agent](./references/n8n-sap-agent/n8n-sap-agent.md) | MUST read when generating SAP Agent nodes | Agent invocation, mandatory parameters, `agents`/`agentName` key order, multi-agent orchestration |
| [n8n-sap-ai-core](./references/n8n-sap-ai-core/n8n-sap-ai-core.md) | MUST read when generating LLM operations (chat, extraction, summarization, OCR) | SAP AI Core node structure, parameter reference, model names, translation codes, LangChain connection pattern |
| [n8n-sap-mcp-client](./references/n8n-sap-mcp-client/n8n-sap-mcp-client.md) | MUST read when invoking any SAP system or S/4HANA action | Mandatory use for all SAP calls, tool selection modes, credential resolution, no-Set-node rule |
| [n8n-sap-task-center](./references/n8n-sap-task-center/n8n-sap-task-center.md) | MUST read when building approval or human-in-the-loop workflows | Mandatory Switch node pattern after Task Center, recipient rules, post-decision SAP MCP Client requirement |
| [n8n-trigger-nodes](./references/n8n-trigger-nodes/n8n-trigger-nodes-webhook.md) | MUST read when placing any Webhook trigger node | responseMode decision table, fire-and-forget vs synchronous vs responseNode patterns, common errors|
