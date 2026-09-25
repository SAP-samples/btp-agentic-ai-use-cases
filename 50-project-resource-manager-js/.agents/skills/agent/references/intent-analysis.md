### Solution Category

| Category   | What gets built                                                                                   | Asset Type |
|------------|---------------------------------------------------------------------------------------------------|------------|
| **AI Agent** | Pro-code Python agent (A2A protocol) with extensibility, OpenTelemetry instrumentation, and tests |`agent`|

### Decision Flow

- Is the primary deliverable an autonomous agent that reasons and decides its own next steps without a fixed workflow graph — no explicit orchestration layer driving the flow? → **AI Agent**
- Is there a clearly defined workflow AND at least one step requires open-ended reasoning, context retention, or dynamic tool use that a static node cannot reliably handle? → **n8n Workflow, AI Agent**

### Common Solution Patterns

| Business Need                                                                                               | Likely Solution                                              | Category               |
|-------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------|------------------------|
| Natural language queries over SAP data, trend analysis, or autonomous recommendations (no fixed steps)      | Pro-code Python agent (A2A) with MCP tool calls              | AI Agent               |
| Intelligent assistant embedded in a UI (e.g. onboarding Q&A, troubleshooting help, product search)          | Pro-code Python agent (A2A)                                  | AI Agent               |
| Scheduled/event-driven workflow + one step requires open-ended reasoning or personalised content generation | n8n workflow calling a pro-code agent as a sub-step          | n8n Workflow, AI Agent |
| Overdue receivables escalation chain + agent drafts personalised collection emails per customer             | n8n escalation flow + agent for context-aware email drafting | n8n Workflow, AI Agent |
| Supplier KPI alert workflow + agent analyses performance trends and recommends alternative vendors           | n8n threshold alert + agent for advisory reasoning           | n8n Workflow, AI Agent |

### Key Milestones — MANDATORY for AI Agents
- In `intent.md`, the `Key Milestones` section is **REQUIRED** for AI Agent solutions, do NOT skip it even in Fast Track Mode.
- Capture 3–5 essential business steps/milestones. These are required for business step instrumentation downstream (OpenTelemetry spans).

### Business Goals & Success Metrics - MANDATORY FOR AI Agents
-  In `intent.md`, the `Business Goals & Success Metrics` section is **REQUIRED** for AI Agent solutions, do NOT skip it even in Fast Track Mode.
- Although Fast Track Mode explicitly states 'no questions to the user', the Business Goals section is an **EXCEPTION**, so follow Step 2a in the Workflow.

### Fast Track Mode
**This rule applies whenever the recommended solution category is AI Agent.**
- In Fast Track Mode: all other sections may be minimal, but `Key Milestones` and `Business Goals & Success Metrics` must still be populated.
- The 50-line fast-track cap on `intent.md` is measured **excluding** the `Key Milestones` and `Business Goals & Success Metrics` section for AI Agent solutions.
