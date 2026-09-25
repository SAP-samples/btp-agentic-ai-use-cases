### Solution Category

| Category   | What gets built                                                                                   | Asset Type|
|------------|---------------------------------------------------------------------------------------------------|-----------|
| **n8n Workflow**           | n8n workflow written as a `.n8n.json` file                                        |`n8n-workflow`|

### Decision Flow

- Is there a clearly defined workflow (steps and routing known upfront), all AI involvement can be handled by a static LLM node, or the user explicitly calls out n8n as the orchestrator? → **n8n Workflow**
- Is there a clearly defined workflow AND at least one step requires open-ended reasoning, context retention, or dynamic tool use that a static node cannot reliably handle? → **n8n Workflow, AI Agent**

### Clarifying Questions

1. Call `list-supported-nodes` in parallel with landscape investigation; not all general n8n nodes are supported — use returned nodes as the **exclusive** option set for any trigger, delivery, or node selection question.
2. Scan for all unresolved items from the prompt (vague thresholds e.g. "needs attention", missing scheduling details e.g. "every evening", missing context, unknown dependencies, data structure e.g. "structured response", approval owners).
3. **If ANY required information is missing or unclear:** ask one by one before proceeding — do not assume or default.

### Node Selection Rules for SAP System Interactions

**Use SAP MCP Client node for:**
- Any deterministic API call to SAP systems (fetch, create, update, post)
- Operations with known endpoint and parameters
- Before generating, verify the required MCP translation card exists. If missing, flag it for generation.

**Use SAP Agent node for:**
- Analysis based on thresholds, patterns, or business rules
- Content generation requiring context (emails, summaries, recommendations)
- Decision-making with open-ended reasoning
- Multi-step problem solving where dynamic tool selection is needed

**IBD flow requirements:**
- Separate deterministic API calls (MCP Client nodes) from reasoning (SAP Agent nodes) into distinct workflow nodes
- Do not embed data fetching logic inside agent definitions
- Pattern: `MCP Client (fetch) → SAP Agent (analyze) → MCP Client (action)`
- When the user's intent requires creating, updating, posting, notifying, or otherwise causing a durable side effect in SAP, execute that step with an SAP MCP Client node.
- For read-only analysis workflows, a terminal formatting or response-shaping node is acceptable if no SAP write-back is requested.

### Iteration over a Collection with a Human Approval Step

When a prompt describes both collection processing and human approval, decide in this order:

1. **What is being approved?**
   - **Each item individually** → continue to the next question.
   - **The full collection as one result** → use **Bulk approval**. Stop here.

2. **How are items delivered to the workflow?**
   - **One item per invocation** → use **Per-item approval, submitted sequentially by the caller**.
   - **A full collection in one invocation** → if items are independent (no ordering dependency, approval coupling, or rate-limit constraint between items), use **Parallel per-item processing with individual approvals**.

| Pattern | Invocation shape | Approval scope | Iteration owner | Best fit |
|---|---|---|---|---|
| Per-item approval, submitted sequentially by the caller | One item per invocation | Per item | Caller | Event-driven item intake, caller-controlled sequencing |
| Bulk approval | Full collection in one invocation | Full collection | Workflow | One approval decision for the aggregated result |
| Parallel per-item processing with individual approvals | Full collection in one invocation | Per item | Workflow | Batch trigger with independent items |

**Per-item approval, submitted sequentially by the caller:** the human reviews each item separately, and the caller controls when to submit each item.
- The iteration belongs to the caller. The workflow handles a single item: it receives one item, processes it through analysis and human approval, and returns the result.
- Choose this pattern when the prompt implies items arrive one at a time (for example, "when an invoice is submitted" or "for each incoming request") or when the caller must control sequencing because of ordering dependencies, rate limits, or partial processing.
- **If the prompt implies a batch trigger** (for example, "process all blocked invoices," "run for the backlog," or "handle the collection"), **do not use this pattern; use the parallel pattern instead.**
- Reason: sequential submission avoids embedding human wait time inside a long-running workflow. Each invocation handles one item, and the caller decides when to submit the next item.

**Bulk approval:** the human reviews and decides on the full collection in one step.
- The automated processing runs over the collection, results are consolidated, and a single human approval step covers the whole batch.
- Reason: because the wait occurs once regardless of collection size, the workflow correctly owns both the iteration and the single approval gate.

**Parallel per-item processing with individual approvals:** the workflow receives the full collection in a single invocation, processes items concurrently, and sends each item for approval independently.
- The iteration stays inside the workflow. Automated analysis runs in parallel across all items, and each approval request is issued independently.
- Choose this pattern when the prompt implies a batch trigger (for example, "process all blocked invoices," "run nightly for the backlog," or "handle the collection on schedule"), items are independent, and no ordering dependency, approval coupling, or rate-limit constraint is mentioned.
- If external systems impose strict concurrency limits, use the **Per-item approval, submitted sequentially by the caller** pattern instead.
- Reason: concurrent processing and approval dispatch make total elapsed time depend on the slowest approval response rather than the sum of all approval times.

### Choose routing nodes: deterministic vs. Agent

Routing node type must be decided here — Rule 10 in `execution.md` enforces this decision during generation.

- **Fixed rule from the prompt** → IF node or Switch node.
- **Free-text or judgment-based input** → Agent node.
- **Neither** → use a reasonable default, **explicitly state the assumed value in your response**, and continue generating. The user can correct the assumption before activating the workflow. Only stop and ask — deferring file generation — if no reasonable default exists and the routing structure would be materially wrong without one.
- **User explicitly requests AI-based routing** → Agent node for inference, Switch/IF node to route on its structured output. This combination is intentional — the Agent infers, the IF/Switch routes on the result.

Never fabricate routing logic.

### Eliciting routing rules and configuration data

When to ask:
- Ask when the prompt describes routing that maps a known set of values to different actions or recipients — for example when terms such as "rules", "matrix", "policy", "routing", "lookup", "conditions", "thresholds", "assignments", "tiers", or "mappings" appear, or when the prompt describes a lookup table (e.g. company code → reviewer, amount → approval tier).

Ask once, concisely:

> "It looks like your workflow uses a routing policy or lookup table. To generate this correctly, I need: the field being evaluated, the possible values or ranges, and the action for each. You can paste a table, a list, or a short description."

Proceed only if:
- The user provides the data, or
- The user explicitly confirms they want placeholder values generated and will replace them after generation.

Fast-track exception:
- If the user's request contains "fast track" or "fast-track" (case-insensitive), skip the question.
- Translate any data already present in the prompt into a complete named constant block as far as possible.
- Use clearly marked placeholders (e.g. `"YOUR_VALUE_HERE": "YOUR_ACTION_HERE"`) only for values genuinely absent from the prompt.
- The sticky note rule defined in execution.md ("Structure user-provided configuration as a named constant block") still applies.

### Common Solution Patterns

| Business Need                                                                                               | Likely Solution                                              | Category               |
|-------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------|------------------------|
| Event-driven trigger → multi-step automated process (e.g. PO budget breach → notify → route for approval)   | n8n workflow with trigger, condition, and action nodes       | n8n Workflow           |
| Scheduled monitoring with threshold alerts (e.g. supplier on-time delivery < 85%, overdue receivables)      | n8n workflow with scheduled trigger and conditional routing  | n8n Workflow           |
| Scheduled/event-driven workflow + one step requires open-ended reasoning or personalised content generation | n8n workflow calling a pro-code agent as a sub-step          | n8n Workflow, AI Agent |
| Overdue receivables escalation chain + agent drafts personalised collection emails per customer             | n8n escalation flow + agent for context-aware email drafting | n8n Workflow, AI Agent |
| Supplier KPI alert workflow + agent analyses performance trends and recommends alternative vendors           | n8n threshold alert + agent for advisory reasoning           | n8n Workflow, AI Agent |

