---
name: intent-analysis
description: Analyzes user's intent, produces intent.md. MUST use first when user wants to create intent-based development asset, also in fast-track mode. EXCEPTION — if the user explicitly asks for a spec / specification spec (e.g. "create a spec / specification for …"), use the `specification` skill directly — it accepts user prompts as input and does not require intent.md.
metadata:
  version: 1.0.0
  author: sap-joule-studio
---

# Analyzing User's Intent
- This skill captures the user's intent in `intent.md`, which is the foundation for all downstream artifacts.
- **CRITICAL: Writing `intent.md` is MANDATORY and MUST NOT be skipped under any circumstances.**

**At startup, check if `intent.md` already exists in the current folder:**
- If `intent.md` exists, enter **Refinement Mode** (see the Refinement Mode section below).
- If `intent.md` does not exist, proceed with the steps in the Workflow below.
- Ask Clarifying Questions and write the file `intent.md` in the current directory.
- If and only if the user's request explicitly contains "fast track", operate in fast track mode (see the Fast Track Mode section for instructions).

## Output
The `intent.md` file should follow the format as mentioned below, replace `<...>` with actual contents
````markdown
# <Title of intent>

<overall project or idea title>

## Business challenge

<user's original business challenge statement>

## Business Goals & Success Criteria [skip for fast track mode, EXCEPT for AI Agent solutions]
<User-confirmed measurable business goals. Rendered as a markdown table:>

| Metric | Baseline | Target | Timeline | Process / Capability | Source |
|--------|----------|--------|----------|----------------------|--------|
| <metric name> | <baseline or —> | <target value> | <timeline or —> | <governed process/capability> | <user \| agent-derived> |

## Key Milestones [skip for fast track mode, EXCEPT for AI Agent solutions]

**Check asset-specific rules**: Some asset types require Key Milestones even in fast-track mode. See asset-specific info loaded at the start of the Workflow.

**For other solutions**: Can be skipped in fast-track mode.

<Checkpoints that mark meaningful progress or completion in the solution's process, as described by the user. For each: a short name and the condition under which it is reached.>

## Business Architecture (RBA)

### End-to-End Process

[E2E process, e.g. "Source to Pay (E2E-216)"]

### Process Hierarchy

```
<E2E Process (Level 1)>
└── <Phase (Level 2)>
    └── <Sub-Process>
        └── <Business Activity>
        └── <Business Activity>
    └── <Sub-Process>
        └── <Business Activity>
```

### Summary

[1-2 sentences on how the user's challenge maps to the RBA hierarchy]

## Fit Gap Analysis

| Requirement (business) | Standard asset(s) found | API ORD ID | MCP Server ORD ID | MCP Server Version | Webhook API ORD ID | Data Product ORD ID | Gap? | Notes / assumptions |
| ---------------------- | ----------------------- | ---------- | ----------------- | ------------------ | ------------------ | ------------------- | ---- | ------------------- |
| <requirement>          | <asset(s)>              | `<api-ord-id>` or — | `<mcp-ord-id>` ✓ or — | `<version>` or — | `<webhook-ord-id>` or — | `<dp-ord-id>` or — | Yes/No/Maybe | <notes> |

### Key findings
<3–6 concise bullets covering reuse choices, key design decisions, and any critical assumptions>

## Recommendations

### <Title of recommendation>

#### Executive Summary

<brief summary of recommended approach, limited to 60-80 characters>

#### Recommended Solution

<full description of recommended solution, specifying relevant SAP products or required custom developments>

#### Problem Statement [skip for fast track mode]

<description of core problem being solved>

#### Affected User Roles [skip for fast track mode]

<brief list of user roles or job titles affected by this challenge — no detailed persona descriptions>

#### Important factors [skip for fast track mode]

##### <title of factor, e.g. Reduces manual effort through automation>

<description of factor>

#### Potential risks [skip for fast track mode]

##### <title of risk, e.g. Integration complexity with legacy systems>

<description of risk>

#### Recommended solution category

<solution category — use the categories from the asset-specific info loaded at Workflow start, or describe the most fitting category; list multiple if the solution combines several components>

#### Intent fit
<how well the recommended solution fits the user's original intent and requirements, including any trade-offs or limitations, represented just in percentage terms (e.g. "90%"). Write just the percentage number without description>
````

## Fast Track Mode
- A minimal intent.md is generated and all phases are completed automatically, no Clarifying Questions asked at any phase.
- Only essential sections are populated; all standard Q&A and explorations are skipped.
- **Business Goals & Success Criteria section**: Check asset-specific info (loaded at Workflow start) — some asset types mandate Business Goals & Success Criteria even in fast-track mode. For other solution types, milestones can be skipped.
- **Key Milestones section**: Check asset-specific info (loaded at Workflow start) — some asset types mandate Key Milestones even in fast-track mode. For other solution types, milestones can be skipped.
- You must still perform the fit-gap analysis. You **MUST** call the `sap_knowledge_graph_fit_gap` tool with the BP URIs from the `sap_knowledge_graph_bp_mapping` result.
- The produced document should not exceed 50 lines (excluding any sections that asset-specific info marks as mandatory).
- No confirmation for proceeding to the next skill is asked - just proceed immediately to the PRD generation using the `product-requirements-document` skill.
- If "fast track" is NOT in the user request:
  - Ask clarifying questions before writing `intent.md`
  - After writing `intent.md`, STOP and ask the user if they want to proceed to PRD
  - Do NOT pre-queue downstream skills (PRD) in your todo list

## Refinement Mode (existing intent.md)
When `intent.md` already exists:

1. **Load the existing document**: Read `intent.md` into your context.
2. **Ask what they want to refine**: Use the `question` tool to ask the user what they would like to change, add, or remove. Offer concrete options such as:
   - Adjust the business challenge or scope
   - Update affected user roles or pain points
   - Revise the Business Goals & Success Criteria
   - Revise the fit-gap analysis
   - Change the recommendation or solution category
   - Fix factual or structural issues
   - Other (open-ended)
3. **Gather the necessary information**: Ask only the questions required to implement the requested changes. Reuse context already in `intent.md` — do not repeat discovery already done.
4. **Apply the changes**: Overwrite `intent.md` with the updated content. **Do not reproduce or summarise the updated file content in the chat** — briefly note (one line) what was changed and confirm the file was saved.
5. **Confirm and iterate**: Ask the user whether they want to make further refinements or are satisfied with the result. Repeat steps 2-5 until the user is done.
6. **Suggest next step**: Once the user is satisfied, suggest re-running the `product-requirements-document` skill to reflect the updated intent.

Refinement Mode is iterative — the user can request multiple rounds of changes before moving on.

For the following phases, use a todo list if available.

## Workflow

### Step 1 (Load and Read first)
- Load all IBD asset skills relevant to the user's request; i.e. skills with `Intent-Based Development asset` in their description. Important: **Do not use apparent relevance or priority to decide which skills to load — if the user's request touches multiple asset types, load all of them with equal weightage. Do not deprioritise or skip a skill just because it appears secondary in the request.**
- Read ONLY the `intent-analysis` section from those skills.
- Only proceed to Step 2 after reading all the file instructions as they are crucial to the execution of the skill.

### Step 2
Understand their business challenge, including:
  - The specific user roles facing this challenge and when they encounter it
  - What are the pain points they experience
  - Success criteria: what must happen for the customer to consider the challenge resolved
  - Key milestones: what checkpoints mark meaningful progress or completion within the solution's process.
  - What constraints and requirements does the customer have relative to this business challenge

Before asking the user any Clarifying Questions, **investigate** the customer's current enterprise landscape as it relates to their business challenge. This way, you can mitigate asking questions about information that already might be available to you. For investigation:

1. **You MUST call the `sap_knowledge_graph_bp_mapping` tool** with the user's business challenge as the `query` (from the `ibd-mcp` server). This maps the challenge to the BP hierarchy in SAP's Reference Business Architecture (RBA) using an agentic search + SPARQL pipeline. The tool returns two parts:
   - A **structured JSON block** (fenced as ` ```json bp-mapping-result `) containing the primary E2E process, hierarchy with URIs, industry variants, and a summary. Extract the hierarchy and E2E process name for the **Business Architecture (RBA)** section of `intent.md`.
   - A **natural language analysis** explaining how the challenge maps to the RBA. Use this context for your investigation and to formulate better clarifying questions.

   The structured JSON includes Business Activity and Process URIs — retain these in your context as they will be needed for the Fit Gap Analysis step.

   If `sap_knowledge_graph_bp_mapping` returns empty output or an error, inform the user and proceed with the SAP LeanIX investigation and clarifying questions.

2. **Use LeanIX tools only if the tool is available, otherwise skip this step.** Use the following sap_leanix tools in the following manner:
  - Call `sap_leanix_call_leanix_agent`, with the business challenge as *user_message*, use returned `thread_id` to requery the agent until the result is ready. This will return a list of relevant Business Capabilities, Applications, and Initiatives from the customer's landscape.

3. Discover available APIs and MCP servers relevant to the business challenge:
   - Call `sap_knowledge_graph_api_discovery` with the business challenge as `query` to find relevant API ORD IDs, ideally OData services which have corresponding MCP servers
   - For each API ORD ID returned, call `get_mcp` with `ordId=<api-ord-id>` to check whether a corresponding MCP server exists in the customer's landscape.
   - If an MCP server is found → record it as type **MCP Server** (store the MCP server ORD ID and, if returned, the version).
   - If no MCP server is found → record it as type **API** (store the API ORD ID). **The MCP Server ORD ID column for this row MUST be `—`. Do NOT invent, infer, or guess an MCP ORD ID. Only populate MCP Server ORD ID from an actual `get_mcp` response.**
   - Carry all found ORD IDs in context — populate the **API ORD ID**, **MCP Server ORD ID**, and **MCP Server Version** columns of the Fit Gap Analysis table in `intent.md` for each relevant requirement row. The MCP Server ORD ID column must only contain values returned by `get_mcp`; use `—` for any row where `get_mcp` returned empty.

4. Discover deployed n8n workflow webhooks that other assets in the solution may need to invoke:
   - This applies when one asset (e.g. an agent) must trigger an already-deployed n8n workflow via its webhook endpoint.
   - The webhook API ORD ID is **not discoverable** via any tool — it must be provided by the user. If the user's challenge involves invoking an existing n8n workflow but they have not provided an ORD ID, ask them explicitly: "To invoke the n8n workflow, I need its webhook API ORD ID (format: `sap.n8nwfrt:apiResource:<tenant>_<workflow-name>_<path>:v1`). Can you provide it?"
   - Once you have the ORD ID, call `get_webhook_api_spec` with it to verify it resolves successfully before recording it.
   - Record any webhook API ORD IDs in the **Webhook API ORD ID** column of the Fit Gap Analysis table. Use `—` if no webhook invocation is needed.

5. Retain the information from your investigation in your context to formulate meaningful Clarifying Questions, and not generic questions, as tool responses in most cases already have that information.

6. Ask the user Clarifying Questions using `question` tool or similar tool that can be used to ask the user.

7. Use the results to populate the landscape context you will carry into the Fit Gap Analysis.

### Step 2a — Business Goals & Success Criteria (MANDATORY)

Using the `question` tool, elicit from the user at least:

- **Business outcome** the solution must deliver.
- **One or more measurable success metrics**, each with a **target value** (e.g. "reduce AP exception rate to 2%").
- **Process or capability** each metric governs (e.g. "Invoice to Pay").
- **Baseline and timeline** if known.

Phrase the question naturally. **Never generate or estimate metric values with the LLM** — they come only from the user.

**Confirmation gate:** render the collected answers as a markdown table with columns `Metric | Baseline | Target | Timeline | Process / Capability | Source` (fill `Source` = `user` or `agent-derived`; use `—` for unknown baseline/timeline) and present it to the user via the `question` tool with options **Confirm**, **Edit an entry**, **Add entry**, **Remove entry**. Apply any edits and re-present until the user selects **Confirm**. Carry the confirmed table into your conversation context; Step 3 will write it into the `## Business Goals & Success Criteria` section when `intent.md` is saved. Do NOT proceed to Step 3 before confirmation.

### Step 3
Perform a fit-gap analysis evaluating how well the customer's existing capabilities align with their business requirements.

1. **You MUST call the `sap_knowledge_graph_fit_gap` tool** (from the `ibd-mcp` server) with the BP sub-process URIs from the `sap_knowledge_graph_bp_mapping` structured result (available in your context from Step 1). Pass all sub-process URIs found in the `primary_e2e.phases[*].sub_processes[*].uri` fields of the `bp-mapping-result` JSON block as `bp_ids`. Also pass the user's business challenge as `business_challenge` for context.
2. The tool returns a structured JSON object with `sub_processes`; each sub-process contains `products`, and each product contains `capabilities` annotated with `mandatory`/`optional` coverage. The response also includes `total_products` and `total_capabilities`.
3. Use these results to map each business requirement to available standard SAP products and capabilities. Filter out products that are not relevant to the specific business challenge (e.g., SAP Fieldglass VMS is not relevant for a non-workforce scenario).
4. Identify gaps where requirements remain unmet based on the evidence returned.

When you're done, incorporate the results into the `Fit Gap Analysis` section of `intent.md` (see template). Keep all findings in your conversation context and proceed to the next step.

### Step 4
Investigate how to best tackle the gaps identified in the previous phase and determine the best solution approach. Use Solution Category Reference and Common Solution Patterns to guide your investigation:
1. Investigate whether any standard SAP products could meet the existing gaps
2. Investigate whether any custom development options could meet the existing gaps
3. Investigate what SAP best practices apply to this challenge
4. Determine which approach has the best balance between ease of implementation and fulfillment of the user's requirements.

For more information on different tools available to you, refer to the `Tools` section.

### Step 5: Collect and Confirm All Information (MANDATORY)

**CRITICAL: This step MUST NOT be skipped under any circumstances.** Before writing `intent.md`, present a comprehensive summary of all collected information and obtain explicit user confirmation.

#### Summary Presentation

Present a structured summary of all collected information to the user and request confirmation:

```
📋 Intent Analysis Summary

**Business Challenge:**
<User's original business challenge statement>

**Affected User Roles:**
<Roles identified from Step 2>

**Business Goals & Success Criteria:**
<Display the confirmed table from Step 2a>

**Key Milestones:**
<Milestones collected, or "Skipped (fast-track mode)" if applicable>

**Business Architecture (RBA):**
- End-to-End Process: <E2E process from bp_mapping>
- Mapped Business Activities: <key activities from hierarchy>

**Fit Gap Analysis - Key Findings:**
- Standard Assets Found: <count and brief list>
- APIs Available: <count>
- MCP Servers Available: <count>
- Webhook APIs (n8n): <count, or "None">
- Identified Gaps: <summary of gaps>

**Recommended Solution:**
- Solution Category: <recommended category/categories>
- Approach: <brief description>
- Intent Fit: <percentage>

**Missing or Unclear Information:**
<List any information that is still uncertain or missing, or "None - all required information collected">

Please review this summary. Type "confirm" to proceed with writing intent.md, or provide corrections/additions.
```

#### Handling User Response

**If user confirms** ("confirm", "yes", "looks good", "proceed"):
- Proceed immediately to writing `intent.md`

**If user provides corrections or additions:**
- Update the affected information
- Re-run relevant investigation steps if needed
- Present the updated summary again
- Wait for confirmation again

**If user identifies missing information:**
- Ask specific clarifying questions to fill the gaps
- Update the summary with new information
- Present the updated summary for confirmation

**Do NOT write `intent.md` until explicit confirmation is received.**

#### Fast Track Mode Exception

**Even in fast-track mode, this confirmation step MUST be performed.** However:
- Use a condensed summary format (8-10 lines maximum)
- Omit sections marked as "skipped" in fast-track mode
- The user's explicit "fast track" instruction serves as pre-authorization — present the condensed summary, then proceed immediately without waiting for a response

Example fast-track confirmation:
```
📋 Quick Confirmation:
Challenge: <brief statement>
Goals: <1-2 key metrics>
Solution: <category> - <one-line approach>
Fit Gap: <X> standard assets found, <Y> gaps identified
Confirm to proceed with intent.md generation, or provide corrections.
```

### Step 6: Write intent.md

After receiving explicit confirmation from Step 5, write the file `intent.md` in the current directory using the template defined at the top of this skill. Replace all `<...>` placeholders with the actual content gathered across all phases. You MUST include the recommended solution categories based on your investigation — use the Solution Category Reference as a guide.

**After writing `intent.md`, do NOT reproduce, paraphrase, or summarise its content in the chat.** Simply confirm the file has been saved. This avoids generating the same tokens twice.

## Tools

- **`sap_leanix_` tools. Use only if available**: The following four SAP LeanIX tools are available. They allow you to query the user's enterprise landscape and gather information about applications, interfaces, and technologies via fact sheets. Each fact sheet can contain links to other fact sheets, which can also be used to find related information.
  - **To get full information** → `sap_leanix_call_leanix_agent` with the business challenge as *user_message*, use returned `thread_id` to requery the agent until the result is ready.

- **`sap_knowledge_graph_bp_mapping` tool**: Maps a business challenge to the BP hierarchy in SAP's Reference Business Architecture (RBA). Returns structured JSON (primary E2E process, hierarchy with URIs, industry variants) plus a natural language analysis. Use this for the Business Architecture (RBA) section in Step 1. The structured output includes URIs that can be used for downstream SPARQL queries.

- **`sap_knowledge_graph_fit_gap` tool**: Queries the SAP Build Knowledge Graph to find products and solution capabilities that cover the identified sub-processes. Takes BP URIs from the `sap_knowledge_graph_bp_mapping` result (`primary_e2e.phases[*].sub_processes[*].uri`) and returns structured JSON with products whose capabilities are annotated with mandatory/optional coverage — no LLM intermediary, ~5s execution. Use this for the Fit Gap Analysis section in Step 2.

- **`sap_knowledge_graph_api_discovery` tool**: Discovers API ORD IDs relevant to a business challenge. Use in Step 1 as the entry point before calling `get_mcp`.

- **`get_mcp` tool**: Checks whether an MCP server exists for a given API ORD ID.
  - **To check if an API has an MCP server** → call with `ordId=<API_ORD_ID>`; returns MCP server ORD ID and version (if available) if one exists, empty otherwise.
  - Tool enumeration and schema retrieval happen later in the `specification` skill, not here.



## References
Asset-specific rules are loaded from `skills/*/references/intent-analysis.md` — merge them into this flow when making a recommendation.

### Solution Category Reference

The `Recommended solution category` field in `intent.md` flows directly into `product-requirements-document.md` and controls what gets built by the `specification` skill. **Choose carefully — this is a build decision, not just a label.**

**Multiple values are supported** — list them comma-separated (e.g. When multiple categories are specified):
- One spec is generated per category in parallel, each isolated in its own `specs/<type>/` directory.
- A cross-spec compatibility check runs after spec generation to verify the components can communicate correctly at runtime.
- Implementation runs in parallel, one sub-agent per component.


### Decision Flow


1. Does a standard SAP product cover the requirement without custom development? → **SAP Product**
2. *(See asset-specific info loaded at Workflow start for rules contributed by each IBD asset skill.)*


### Common Solution Patterns


## Enterprise Domains

Four domains structure all enterprises:

| Domain                  | Purpose               | Business Areas                                             |
| ----------------------- | --------------------- | ---------------------------------------------------------- |
| **Products & Services** | Develop offerings     | R&D, Engineering, Product Management                       |
| **Supply**              | Fulfill demand        | Procurement, Manufacturing, Supply Chain, Service Delivery |
| **Customer**            | Generate demand       | Sales, Marketing, Customer Service, Commerce               |
| **Corporate**           | Manage the enterprise | HR, Finance, Asset Management, IT, GRC                     |

## Core Business Processes

Eight end-to-end processes define the enterprise value chain:

| Process                     | Domain    | Flow                                                              |
| --------------------------- | --------- | ----------------------------------------------------------------- |
| **Lead to Cash**            | Customer  | Market → Lead → Quote → Order → Fulfill → Invoice → Cash          |
| **Source to Pay**           | Supply    | Source → Contract → Requisition → Order → Receipt → Invoice → Pay |
| **Plan to Fulfill**         | Supply    | Plan → Procure → Make → Inspect → Deliver                         |
| **Idea to Market**          | Products  | Idea → Requirement → Design → Release → Manage                    |
| **Recruit to Retire**       | Corporate | Plan → Recruit → Onboard → Develop → Reward → Offboard            |
| **Acquire to Decommission** | Corporate | Plan → Acquire → Operate → Maintain → Decommission                |
| **Finance**                 | Corporate | Plan → Record → Report → Treasury → Close                         |
| **Governance**              | Corporate | Portfolio → Project → Sustainability → GRC → IT Management        |

## Business Capability Hierarchy

```
Enterprise Domain (Products & Services, Supply, Customer, Corporate)
└── Business Domain (L1 grouping by function)
    └── Business Area (L2 grouping)
        └── Business Capability (what the business does)
```

A **Business Capability** describes an organization's ability to achieve a specific outcome. Capabilities are realized through:

- **Processes** (how work flows)
- **People** (roles, skills)
- **Technology** (applications, infrastructure)

## Solution Architecture Hierarchy

```
Solution Capability (implements Business Capability)
└── Solution Component (SAP product or service)
    └── Solution Process (implements business process)
        └── Solution Activity (specific action in a component)
```

## Architecture Principles

Apply these principles when formulating recommendations and solution designs:

- **Business before Technology**: Derive solutions from business requirements, not technology preferences
- **Cloud First**: Prefer SaaS for new capabilities; on-premise only when required
- **Run Simple**: Choose the simplest architecture that meets requirements
- **Extensibility**: Use standard features first; build custom only for differentiation
- **Data as Asset**: Treat data quality as competitive advantage; single source of truth
- **Composability**: Shrink monolithic core; surround with modular services
- **Control Technical Debt**: Use maintained, supported technology stacks

## SAP Product Portfolio (Key Products by Domain)

**Customer:**
- **SAP Sales Cloud** - Sales force automation
- **SAP Service Cloud** - Customer service management
- **SAP Commerce Cloud** - E-commerce platform
- **SAP Emarsys** - Marketing automation

**Supply:**
- **SAP S/4HANA** - Core ERP (MM, PP, SD, WM)
- **SAP Ariba** - Procurement network
- **SAP IBP** - Integrated business planning
- **SAP TM** - Transportation management

**Products & Services:**
- **SAP S/4HANA PLM** - Product lifecycle management
- **SAP Engineering Control Center** - CAD integration

**Corporate:**
- **SAP SuccessFactors** - Human capital management
- **SAP Concur** - Travel and expense
- **SAP S/4HANA Finance** - Financial management
- **SAP Analytics Cloud** - Business intelligence

**Platform:**
- **SAP Integration Suite** - Integration middleware
- **SAP Build** - Low-code development
- **SAP AI Core** - AI/ML runtime

## Guardrails
### Communication Guidelines
- Be direct and concise; avoid filler phrases, unnecessary apologies, excessive enthusiasm, or encouragement.
- Use the `question` tool (or a similar tool you have available) to pose questions to the user.
- Do not ask vague clarifying questions (e.g., "What platform do you use to host your application?") if the information is already available from your investigation. Instead, ask specific questions grounded in the user's landscape (e.g., "I see system X and Y in your environment. Do you intend to keep using them for the current challenge?").
- Do not propose something as an option in the clarifying questions if it can not be part of the actual solution in the end.
- If the user greets you, engages in casual conversation, or has not yet described a business challenge:
  - Respond warmly and ask what business challenge or requirement they'd like to work on.
  - Do not enter the understanding phase or start asking detailed questions.
  - Wait for them to describe their business intent before starting the Workflow.
- Keep communication professional and text-based (no emoji).
- Before and after each step, inform the user about what you're doing.
- The goal is to understand the "what" and "why", and only then the "how".

### Scope Guidelines
- Only start with the Workflow AFTER the user has provided their business intent or challenge. Go through the steps sequentially.
- Go through each step of the Workflow, until you have written `intent.md`.
- If the user provides new information at any point, evaluate whether it impacts your previous findings. If it does, make the necessary adjustments.
- If the user provides information that contradicts your previous findings, clarify with the user which information is correct and update your findings accordingly.
- If the user wants to discuss certain topics outside their usual phase, that's perfectly fine. Capture whatever information they share and adjust your approach accordingly.
- Users are in control - they can skip questions.
- Be thorough in your analysis and research in each phase to ensure that your recommendation is well-founded.


### Investigation Guidelines
- Start by identifying all aspects of the question that need investigation.
- Query each relevant dimension systematically (applications, capabilities, integrations, etc.)
- If a query returns information that raises new questions, investigate those too
- Synthesize the findings cohesively to be used in the relevant sections of 'intent.md'

## Gotchas
- **Never reproduce, paraphrase, or summarise the content of a file you have just written.** After saving a file, confirm it was written (one line) and move on. Summarising written content generates the same tokens twice and must be avoided.
- Avoid skipping tool calls under the assumption that you have enough information. Use this checklist to make sure you make the appropriate calls: ([] sap_knowledge_graph_bp_mapping, [] sap_knowledge_graph_fit_gap, [] sap_leanix, [] sap_knowledge_graph_api_discovery → get_mcp per ORD ID, [] get_webhook_api_spec if n8n webhook invocation is involved).
- **Critical constraint:** Business Case and Business Metrics content must never be generated by the LLM. Only include this information from if the user has uploaded some artifacts, or ask a question regarding this with a `question` tool or a similar tool you use to converse with the user.

## Next Steps
After completing the intent analysis and writing the intent.md, the next skill MUST always be `product-requirements-document`. Before automatically proceeding with this skill, ask the user if they want to proceed, as they may want to modify the `intent.md` file, or have some other questions.
