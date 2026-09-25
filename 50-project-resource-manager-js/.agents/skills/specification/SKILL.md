---
name: specification
description: Generate actionable TODO-list specifications from a PRD, intent.md, or direct user prompt. Produces specification/ folder with per-asset checklists. Route here when the user explicitly asks for a specification or says "do specification directly" (even if they skip intent-analysis). To implement, just say "execute specification/specification.md".
metadata:
  version: 1.0.0
  author: sap-joule-studio
  
---

# Specification Skill

Generate actionable, TODO-list specifications from a Product Requirements Document (PRD), an intent document, or a direct user prompt. Output is a `specification/` folder containing one main spec and one per-asset spec — each a persisted checklist an AI coding agent can execute directly.

## Input Resolution

The skill uses the best available input, checked in this order:

1. **`product-requirements-document.md`** — full PRD with solution category, milestones, requirements. Preferred.
2. **`intent.md`** — lighter intent document from the `intent-analysis` skill. Used if no PRD exists.
3. **User prompt** — direct description of what to build. Used if neither file exists.

When working from intent or user prompt (no PRD), the skill must infer solution category, feature scope, and requirements from the available context. Ask clarifying questions if the input is too ambiguous to determine asset types or key features.

**To implement code:** just say `execute specification/specification.md`.

## Output Structure

```
specification/
  specification.md                            # Master spec — orchestrates all asset specs
  guidelines.md                               # Execution rules (copied from <type> skill, editable)
  guidelines-<type>.md                        # Type-specific constraints (copied once per used type, editable)
  <asset-name>/
    specification.md                          # Per-asset TODO list
    api-specs/                                # (optional) Downloaded API spec files (OData / REST)
    mcp-specs/                                # (optional) Existing MCP server tool schemas
```

Code is generated into `assets/<asset-name>/` when specifications are executed.

## Fast Track Mode

If user request contains "fast track":
- Skip all interactive questions, bypass confirmations
- Generate minimal specification TODO items
- Immediately proceed to execution after generation — do NOT ask the user; autonomously execute `specification/specification.md` by reading it and running all tasks
- Never skip: tests (for agents)

**Fast track = faster workflow, NOT incomplete implementation.**

## A - Writing Specifications

### Step 1: Determine Asset Type
Read the resolved input (PRD → intent → user prompt).
- If a PRD exists, find the `Solution Category` field, and get the relevant `Asset Type`.
- If working from intent or user prompt, infer the category from the description.

Split on commas if multiple. If missing/ambiguous, ask user.

Select a **feature name** prefix (e.g. `purchase-order-approval`).

**Asset name** = `<feature>-<asset-type>` (e.g. `purchase-order-approval-agent`). 

Exceptions:
- **n8n workflows**: use `assets/workflows/<workflow-name>` where `<workflow-name>` is kebab-case (e.g. `assets/workflows/invoice-approval-workflow`).
- **Data products**: the asset name is derived at metadata approval time (Step 1 of the `data-product` skill) as the kebab-case folder name (e.g. `sales-order-analytics-data-product`). Use a placeholder until then.

This naming allows multiple assets of the same type to coexist.

### Step 2: API Discovery (Conditional)

> **CONSTRAINT: APIs must NEVER be consumed directly. No direct HTTP clients (`requests`, `httpx`, OData clients, `fetch`, `axios`, etc.) for any SAP or external API. All API interactions MUST go through MCP tools.**

> **Note:** If the asset includes data products AND the `data-product` skill exists (check `skills/data-product/SKILL.md`), that skill's MCP tools (`dpca-mcp-server__ums_search_data_products` ,`fetch-and-prepare`, `generate-interop`, `fetch-ams-policy`, etc.) cover data product interactions. Still run the sub-steps below for any additional MCP servers or APIs identified in the Fit Gap Analysis. **If Fit Gap rows have a Data Product ORD ID and `—` for both API ORD ID and MCP Server ORD ID, skip Steps 2a and 2b entirely — DPQuery is the only runtime dependency.**

This step covers two sub-cases. Run ones that apply.

#### 2a — MCP server tool discovery

**When to run:** `intent.md` Fit Gap Analysis table has one or more rows with a value in the **MCP Server ORD ID** column.

For each MCP server ORD ID carried over from intent analysis:

1. Call `get_mcp_tools` with the MCP server ORD ID (and the optional `version` if recorded in `intent.md`) to list all available tools (returns name, title, description — no schemas).
2. For each **relevant** tool (relevant to the business challenge / asset being specified), call `get_mcp_tool_details` with the MCP server ORD ID (and the optional `version` if recorded in `intent.md`) and tool name to retrieve the full input/output JSON schema.
3. Save each tool's full schema as a separate file: `specification/<asset-name>/mcp-specs/mcp-spec-<server-name>-<tool-name>.json`. Create directory if needed.
4. The MCP server ORD IDs, versions (if available), tool names, and paths to schema files **must** be included in the per-asset spec TODO items.

#### 2b — OData / REST API discovery

**When to run:** `intent.md` Fit Gap Analysis table has rows with an **API ORD ID** but no corresponding **MCP Server ORD ID** (i.e., a plain REST/OData API with no MCP server).

**Skip** if the agent has zero SAP API touchpoints (pure AI-to-AI, no SAP backend), OR if every required API interaction is already covered by an available MCP server.

For each relevant asset:

1. Call `sap_knowledge_graph_api_discovery` with a concise use-case description as `query`; save the output to `api-discovery-results.md`.
2. For each relevant API in the results:
   - Call `sap_knowledge_graph_api_schema_download` via the `jl` CLI:
     ```bash
     jl mcp call ibd-mcp-server sap_knowledge_graph_api_schema_download ordId=<apiOrdId> type=<apiType> fileType=<fileType>
     ```
   - Use this method **only**; do not invoke the MCP tool directly.
   - Prefer `EDMX` over `OpenAPI JSON` when both are available.
   - Save the **raw content as-is** to `specification/<asset-name>/api-specs/`(e.g. `specification/<asset-name>/api-specs/supplier-invoices.edmx`).
   - Create the directory if needed and preserve the original file extension.
3. If discovery returns no relevant results, ask the user to retry with a different query.

The discovered API names, ORD IDs, and paths to downloaded spec files **must** be included in the PRD-specific tasks in the generated specification. Do **NOT** include raw endpoints, entity sets, key fields, or response schemas — those are consumed exclusively by the `mcp-translation-file` skill, not by agent implementation tasks.

#### 2c — n8n workflow webhook API discovery

**When to run:** Another asset in the current solution (e.g. an agent) needs to invoke an already-deployed n8n workflow via its webhook endpoint. The webhook ORD ID comes from the `intent.md` Fit Gap Analysis **Webhook API ORD ID** column.

**Skip** if no other asset in the solution invokes an n8n workflow, or if the n8n workflow is being built as part of this solution (not pre-existing).

For each webhook to be invoked:

1. Call `get_webhook_api_spec` with the webhook API resource ORD ID from the Fit Gap Analysis. The ORD ID has the form `sap.n8nwfrt:apiResource:<tenant>_<workflow-name>_<path>:v1`.
2. Save the returned spec content to `specification/<asset-name>/api-specs/<workflow-name>.json`. Create the directory if needed.
3. After saving, invoke the `mcp-translation-file` skill so it can generate a translation card from the saved spec file.

The webhook ORD ID and path to the downloaded spec file **must** be included in the per-asset spec TODO items.

### Step 3: Generate Specification Files

**Before writing any files**, copy the guidelines from the skill into the `specification/` folder so they live next to the specs and can be customized per project:

- Copy `<skill:specification>/assets/guidelines.md` → `specification/guidelines.md` (skip if already exists)
- For each distinct asset type used, copy `<skill:<asset-type>>/assets/guidelines-<asset-type>.md` → `specification/guidelines-<asset-type>.md` (once per asset-typetype; skip if already exists)

These are **pure file copies** (`cp`) — do not modify, resolve references, or rewrite content. Copy the file bytes as-is.

For each asset:

1. Read the template: `<skill:<asset-type>>/assets/specification-<asset-type>.template.md`
2. Read the PRD thoroughly to derive feature-specific tasks
3. Replace placeholders:
   - `{​{asset-name}}` → actual asset name (e.g. `purchase-order-approval-agent`)
   - `{​{feature}}` → feature name (e.g. `purchase-order-approval`)
   - Any remaining `<skill:specification>` references: replace with the relative path from the file being written to the skill directory. **Must be a relative `../`-based path — never an absolute path (e.g. never `/Users/...` or `/home/...`).**
4. Replace `{{project-specific-tasks}}` with concrete TODO items derived from the input (PRD, intent, or user prompt). Use `##` markdown headers to group related TODOs:
   - Each functional requirement → one or more `- [ ]` items
   - Each business rule → specific TODO
   - When working from intent/prompt (no PRD): derive tasks from the described goals; be explicit about assumptions made
   - **If `## Data Dependencies` has only Data Product ORD IDs (no direct API ORD IDs): do NOT generate MCP server creation or `mcp-translation-file` tasks — DPQuery is the only runtime dependency.**
5. Write to `specification/<asset-name>/specification.md`

**CRITICAL: Complete the spec generation loop for ALL assets before doing anything else.**
Finish every per-asset spec file first, then generate the main spec at `specification/specification.md`:

```markdown
# Specification

> **Guidelines**: Read [guidelines.md](./guidelines.md) before executing ANY tasks below.

Check off items as completed.

## Solution Setup

- [ ] Create asset directories: `mkdir -p assets/<asset-name-1>/ assets/<asset-name-2>/`
- [ ] Invoke `setup-solution` skill to create `solution.yaml` and `asset.yaml` files for every asset
- [ ] Validate all `asset.yaml` and `solution.yaml` files exist and are well-formed

## Asset Implementation

- [ ] Execute specification/<asset-name-1>/specification.md (all items)
- [ ] Execute specification/<asset-name-2>/specification.md (all items)
- [ ] Cross-implementation compatibility check (only if multiple assets — verify interfaces, data shapes, auth, env vars align across assets; fix any mismatches before proceeding)
```

Adjust the list based on actual assets. Single-asset solutions omit the compatibility check.

### Step 4: Review (not in fast-track mode)

Only run this step after ALL per-asset specs and the main `specification/specification.md` is fully written.

Present the full set of generated specifications to the user. Summarize:
- Number of assets and their types
- Key features per asset
- API integrations discovered (if any)

User can edit specification files before execution.

**In fast-track mode:** skip review — do NOT output a summary, do NOT ask the user; autonomously proceed to execution by reading `specification/specification.md` and running all tasks.

## B - Executing Specifications

When user says **"execute specification/specification.md"** (or similar):

Read `specification/specification.md` and execute tasks.

## Templates

Templates live in `<skill:<asset-type>/assets/specification-<asset-type>.template.md`.

## Guidelines

Guidelines are **copied from the skill into the `specification/` folder** during spec generation, so they live next to the specs and can be customized per project.

| Source (skill asset)         | Copied to                              | Referenced as (main spec) | Referenced as (per-asset spec) 
| `guidelines.md`              | `specification/guidelines.md`          | `./guidelines.md`         | `../guidelines.md`          |     

This applies to asset specific guidelines as well. Source (skill asset) is copied from `<skill:asset-type>/asset/guidelines-<asset-type>.md` to `specification/guidelines-<asset-type>.md` and referenced per-asset spec as `../guidelines-<asset-type>.md` 

Only the guidelines files for asset types actually used in the solution are copied. If a guideline file does not exist, skip it silently and continue.

## What This Skill Does NOT Do

- Implement code (specifications are executed separately)
- Git operations, deployment, authentication
- Create PRDs (use `product-requirements-document` skill)
