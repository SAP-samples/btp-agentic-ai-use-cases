**This skill operates on the current working directory.** The caller is responsible for running it from the correct target directory (e.g. `assets/agent-extension/`).

## Schema References

All generated files MUST conform to the following JSON Schema definitions:

- **Extension Descriptor** (`extension.yaml`): [assets/extension.json](assets/extension.json)
- **Asset Descriptor**: From `setup-solution` skill
- **Agent Discovery Response** (response schema reference): [assets/agent-discovery-response.json](assets/agent-discovery-response.json)
  - Fetching all extensible agents returns the full response (`{ agents: [...], pageInfo: {...} }`)
  - Fetching a single extensible agent returns a single agent object (one item from the `agents` array, no `pageInfo`)

### Tool Result → YAML Field Mapping

Use this mapping to translate agent discovery response fields into the generated YAML files.

#### Agent → `extension.yaml`

| Tool Result Field | `extension.yaml` Field |
|---|---|
| `ordId` | `agent.ordId` |
| `systemInstance.globalTenantId` | `agent.identifier` |
| `extensions[].params.capabilityId` | `capabilityImplementations[].capabilityId` |
| `extensions[].params.instructionSupported` | Determines if `capabilityImplementations[].instruction` can be set |
| `extensions[].params.tools.additions.enabled` | Determines if `capabilityImplementations[].tools[]` can be populated |
| `extensions[].params.supportedHooks` | Determines which hooks can be defined in `capabilityImplementations[].hooks[]` |

#### Agent → `asset.yaml`

| Tool Result Field | `asset.yaml` Field |
|---|---|
| `ordId` | `requires[].ordId` (where `type: agent`) |
| `version` | `requires[].version` (where `type: agent`) |

## Step 0: Ensure Intent, PRD, and Spec exist (MANDATORY)

**Before generating any extension YAML, the solution MUST contain all three IBD documents: `intent.md`, `product-requirements-document.md`, and a `specification/` folder.** These are normally already present because this skill runs at the end of the orchestration chain (`intent-analysis` → `product-requirements-document` → `specification` → `create-agent-extension`).

**Check the current working directory and act accordingly:**

- **If `product-requirements-document.md` AND `specification/` already exist**, the upstream chain already ran — proceed directly to Step 1.
- **Otherwise (any of the three documents is missing — e.g. this skill was reached directly from an "Extend agent" request), you MUST run the full IBD chain first, in order, and only then continue:**
  1. Run the `intent-analysis` skill → writes `intent.md`.
  2. Then run the `product-requirements-document` skill → writes `product-requirements-document.md`.
  3. Then run the `specification` skill → writes the `specification/` folder.

  Do NOT generate any extension YAML, and do NOT jump ahead to Step 1, until **all three** documents exist. Generating `intent.md` alone is NOT sufficient — the PRD and specification MUST also be produced. This guarantees an agent extension solution is as complete and consistent as any other solution type, with or without fast track.

## Step 1: Fetch Agent Information

**IMPORTANT: Always fetch agent information first** to get the correct `ordId` and `version` for the agent to be extended.

#### When User Provides a Specific ordId

If the user provides a specific ordId and version (e.g., `sap.ai:agent:my-agent:v1` & version `1.0.0`), fetch that specific agent via the agent discovery API:

#### Default Query (No ordId Provided)

Fetch all extensible agents via the agent discovery API.

Note that the result can have a next page with a cursor that can be used to fetch more agents if needed. If multiple agents are returned, ask the user to select which agent they want to extend. Present the options clearly with their `ordId`, `version`, and a short description.

#### Handle Multiple Versions

If the query returns **multiple versions** of the same agent (e.g., `sap.ai:agent:my-agent:v1` and `sap.ai:agent:my-agent:v2`), you **MUST ask the user which version to use** before proceeding. Present the versions clearly:

- List each version with its `ordId`, `version`, `description`
- Highlight differences between versions if apparent (e.g., different extension capabilities)
- **Do NOT default to the latest version silently** — always let the user decide

#### Handle Agent Not Found

**CRITICAL — MANDATORY ABORT:** If no agent is found in the extensible agents registry (empty results, the specified `ordId` does not exist, or no matching agent returns):

1. **Do NOT create any extension files** — no `extension.yaml`, no agent-extension folder, no skeleton files
2. **Do NOT use placeholder values** — never write `<REPLACE: ...>`, `<from tool: ...>`, or similar placeholder text
3. **Do NOT invent or guess agent information** — never fabricate `ordId`, `version`, `identifier`, or extension capabilities
4. **Do NOT ask the user to provide the ordId manually** — if the agent is not in the registry, it cannot be extended
5. **SKIP the entire agent extension creation** and inform the user:
   > "The requested agent was not found in the extensible agents registry. Skipping agent extension creation. Only agents that are registered as extensible can be extended via this skill."
6. **Continue with other tasks** in the conversation if applicable (e.g., creating workflows, other assets that don't depend on the agent extension)

**This is a hard stop** — without valid agent data from the discovery API, no extension artifacts can be created. The skill requires real agent metadata; it cannot proceed with placeholders or user-provided values.

## Step 1b: Collect and Confirm Extension Requirements (MANDATORY)

**CRITICAL: This step MUST NOT be skipped under any circumstances.** Before generating any YAML files, collect all required information and obtain explicit user confirmation.

### Required Information Checklist

Gather the following information from the user, intent.md, product-requirements-document.md, and the agent discovery response:

**Extension Basics:**
- [ ] Extension name (kebab-case, descriptive)
- [ ] Extension purpose/description (what capabilities does this add?)
- [ ] Target base agent (confirmed from Step 1)
  - Agent name: `<agent-name>`
  - Agent ordId: `<ordId>`
  - Agent version: `<version>`

**Extension Capabilities (based on agent's supported extensions):**
- [ ] Will this extension add **instructions**? (if `instructionSupported: true`)
  - If yes, what additional instructions/guidance?
- [ ] Will this extension add **tools**? (if `tools.additions.enabled: true`)
  - If yes, which APIs/systems will be integrated?
  - Expected tool names/functions?
- [ ] Will this extension add **hooks**? (if `supportedHooks` is non-empty)
  - If yes, which hooks? (pre-execution, post-execution, etc.)
  - What should each hook do?

**Dependencies:**
- [ ] Are there MCP servers to be created? (list expected MCP servers)
- [ ] Are there n8n workflows involved? (list expected workflows)
- [ ] Any other asset dependencies?

**Business Context (from intent.md/PRD):**
- [ ] Business challenge being addressed
- [ ] Success criteria/metrics
- [ ] Key milestones (if applicable)

### Missing Information Handling

**If ANY required information is missing or unclear:**

1. **DO NOT proceed with file generation**
2. **Ask specific clarifying questions** to fill the gaps
3. **Wait for user response** before continuing

Example clarifying questions:
- "I see the base agent supports tools. Which specific APIs or systems should this extension integrate with?"
- "The agent supports pre-execution and post-execution hooks. Which hooks do you need for your use case?"
- "What additional instructions or guidance should the agent follow when using this extension?"

### Confirmation Summary

Once all information is collected, **present a summary to the user for confirmation:**

```
📋 Extension Requirements Summary

**Extension Details:**
- Name: `<extension-name>`
- Purpose: `<brief description>`

**Target Agent:**
- Agent: `<agent-name>` (ordId: `<ordId>`, version: `<version>`)
- Supported capabilities: [instructions: yes/no, tools: yes/no, hooks: yes/no]

**Planned Extension Features:**
- Instructions: `<yes/no - description if yes>`
- Tools: `<yes/no - list of tools if yes>`
- Hooks: `<yes/no - list of hooks if yes>`

**Dependencies:**
- MCP Servers: `<list or "none">`
- n8n Workflows: `<list or "none">`

**Business Goals:**
- Challenge: `<from intent.md>`
- Success Criteria: `<from intent.md>`

Is this information correct? Please confirm or provide corrections before I proceed with generating the extension files.
```

**Wait for explicit user confirmation** (e.g., "yes", "confirmed", "looks good", "proceed") before moving to Step 2.

**If user provides corrections:**
- Update the collected information
- Present the updated summary again
- Wait for confirmation again

**Only proceed to Step 2 after receiving explicit user confirmation.**

### Fast Track Mode Exception

**Even in fast-track mode, this confirmation step MUST be performed.** However, in fast-track mode:
- Use a condensed summary format (3-5 lines instead of full detail)
- Pre-fill supported capabilities based on the discovery response and ask the user to correct them if needed
- **Still require explicit confirmation** before proceeding to Step 2

Example fast-track confirmation:
```
📋 Quick Confirmation: Creating extension `<name>` for agent `<agent-name>` with [tools/hooks/instructions]. Integrating with [API names]. Reply "confirm" to proceed or provide corrections.
```

## Step 2: Generate `extension.yaml`

Create `assets/<agent-extension>/extension.yaml` conforming to the Extension Descriptor schema ([assets/extension.json](assets/extension.json)).

**Always generate this file immediately as an empty skeleton** — do NOT ask the user what to include first. The skeleton is populated based solely on the extension capabilities returned by the discovery response.

The `capabilityImplementations` structure depends on what the agent's extension capabilities support:

#### If tools AND hooks are supported

(`extensions[].params.tools.additions.enabled` is `true` AND `extensions[].params.supportedHooks` is non-empty)

```yaml
_schema-version: "0.1.0"
kind: Extension

metadata:
  name: "<agent-extension-name>"

agent:
  ordId: "<from tool: ordId>"
  identifier: "<from tool: systemInstance.globalTenantId>"

capabilityImplementations:
  - capabilityId: "<from tool: extensions[].params.capabilityId>"
    tools: []
    hooks: []
```

#### If only tools are supported

(`extensions[].params.tools.additions.enabled` is `true` AND `extensions[].params.supportedHooks` is empty or absent)

```yaml
_schema-version: "0.1.0"
kind: Extension

metadata:
  name: "<agent-extension-name>"

agent:
  ordId: "<from tool: ordId>"
  identifier: "<from tool: systemInstance.globalTenantId>"

capabilityImplementations:
  - capabilityId: "<from tool: extensions[].params.capabilityId>"
    tools: []
```

#### If only hooks are supported

(`extensions[].params.tools.additions.enabled` is `false` or absent AND `extensions[].params.supportedHooks` is non-empty)

```yaml
_schema-version: "0.1.0"
kind: Extension

metadata:
  name: "<agent-extension-name>"

agent:
  ordId: "<from tool: ordId>"
  identifier: "<from tool: systemInstance.globalTenantId>"

capabilityImplementations:
  - capabilityId: "<from tool: extensions[].params.capabilityId>"
    hooks: []
```

#### If neither tools nor hooks are supported

```yaml
_schema-version: "0.1.0"
kind: Extension

metadata:
  name: "<agent-extension-name>"

agent:
  ordId: "<from tool: ordId>"
  identifier: "<from tool: systemInstance.globalTenantId>"

capabilityImplementations:
  - capabilityId: "<from tool: extensions[].params.capabilityId>"
```

**Important rules for extension.yaml:**
- The `capabilityId` must match the `params.capabilityId` from the agent's extension capabilities
- Only include `tools` property if `extensions[].params.tools.additions.enabled` is `true`
- Only include `hooks` property if `extensions[].params.supportedHooks` is non-empty
- Only add `instruction` if `extensions[].params.instructionSupported` is `true`
- Do NOT include `tools` or `hooks` properties at all when the capability does not support them

## Step 3: Setup Solution and Dependencies

Before populating tools or dependencies:

1. Run `setup-solution` from the solution root (not from `assets/<ext>/`) — running it from inside the asset folder creates a misplaced `solution.yaml` inside the asset directory.
2. **CRITICAL — additive only:** If `solution.yaml` already exists, only add the agent-extension entry to the existing `assets:` list. Do NOT regenerate or overwrite the file — doing so drops the MCP server and n8n workflow registrations created by earlier spec steps.
3. Confirm the extension `asset.yaml` exists and contains the agent dependency `requires` entry. If missing, add it manually.
4. Confirm MCP server assets now exist under `assets/` before proceeding to Step 3b.

## Step 3b: Populate Tools and MCP Server Dependencies

**Run this step only after Step 3 (`setup-solution`) has completed**, because `setup-solution` creates the MCP server assets in `assets/` that this step reads.

### Populating Tools from Solution MCP Servers

Populate `capabilityImplementations[].tools[]` only when:
- at least one local `type: mcp-server` asset exists under `assets/`
- `extensions[].params.tools.additions.enabled` is `true`

If either condition is not met, omit `tools` entirely or leave it empty according to the capability rules above.

**CRITICAL — LOB MCP servers are strictly forbidden:**
- **NEVER include tools from LOB (Line of Business) MCP servers** — these are existing/UMS-registered MCP servers referenced by a known ORD ID but NOT created as part of this solution.
- ONLY populate tools from MCP servers **created within this same solution** — i.e., `type: mcp-server` assets present under `assets/` in the current solution directory.

**How to populate tools:**

For each `mcp-server` asset in the solution:
1. Read its `asset.yaml` → extract `provides.apis[].ordId` (the MCP server ORD ID)
2. Locate the tool list using the first readable file in this order:
   - `mcp-translation/.tool-list.json` — use the array of tool name strings directly
   - `mcp-translation/translation.json` — fallback; extract `tools[].name`

   Do not merge both files. Stop after the first readable file.
3. For each tool name found in those files, add one entry to `capabilityImplementations[].tools[]` — one entry per individual tool, all sharing the same `ordId`:

```yaml
tools:
  - ordId: "<from mcp-server asset.yaml: provides.apis[].ordId>"
    mcpToolName: "<first tool name read from file>"
  - ordId: "<from mcp-server asset.yaml: provides.apis[].ordId>"
    mcpToolName: "<second tool name read from file>"
```

**CRITICAL — never invent tool names:**
- Tool names MUST come exclusively from the file content read in step 2.
- If tool support is enabled but neither `.tool-list.json` nor `translation.json` is readable, set `tools: []` and warn the user: "Could not read tool list for `<asset-name>` — tools array left empty. Add tool names manually."
- If tool support is not enabled for the capability (`extensions[].params.tools.additions.enabled` is `false` or absent), omit the `tools` property entirely — do not write `tools: []`.
- **NEVER guess, infer, or generate tool names** from the entity name, API name, or any other context.

If the solution contains no `mcp-server` assets (only LOB/existing MCP servers are referenced), leave `tools: []` as generated by the skeleton — LOB MCP servers must never be listed here.

### Reflecting MCP servers in `asset.yaml`

For every `mcp-server` asset whose tools are mapped in `extension.yaml`, a corresponding `requires` entry **MUST** be added to the extension's `asset.yaml`. This is required for both platform dependency resolution and UI tool-count hydration.

The complete `requires` block must include the agent dependency and each MCP server dependency (n8n workflow dependencies are added later in Step 4.3 if applicable):

```yaml
requires:
  - name: "<agent-title-kebab-case>"
    type: agent
    version: "<from tool: version>"
    ordId: "<from tool: ordId>"
  - name: "<mcp-server asset metadata.name>"
    type: mcp-server
    version: "<mcp-server asset metadata.version>"
    ordId: "<from mcp-server asset.yaml: provides.apis[].ordId>"
```

**CRITICAL:** Use `type: mcp-server` — never `kind: mcp-server`. The platform filters by `type` and will silently ignore the entry if `kind` is used instead.

## Step 4: Configure Hooks for n8n Workflows from Same Solution

This step applies **only when a new n8n workflow was created in the same solution** and needs to be connected as a hook to the agent extension. Skip this step if the workflow comes from UMS (external fetch).

### Step 4.1: Gather Hook Configuration

**Enumerate REST APIs first.** Read the workflow's `asset.yaml` and collect **all** `provides.apis[]` entries where `kind: rest` — every one of them will become a hook entry. No user selection is needed; Step 1b already confirmed which workflows and hooks are in scope. The hook config values below (hookType, timeout, onFailure, canShortCircuit) are collected once and applied uniformly to all hooks generated from this workflow.

#### From Base Agent (do NOT ask user)

| Parameter | Source |
|---|---|
| `hookId` | Read from `extensions[].params.supportedHooks` in agent discovery response |

#### Required inputs from User (MANDATORY: Ask user before proceeding)

#### Fast Track Mode
**IMPORTANT:**

In Fast Track Mode, use the **default values** from the table above. Do NOT ask the user for hook configuration parameters.

#### Normal Mode (Non-Fast Track)

**CRITICAL: You MUST ask the user for the following values if they were not explicitly provided in the conversation. Do NOT guess or use default values — always ask the user first.**

**For pre-hooks (hookType = BEFORE) — ask ALL 4 parameters:**

| Parameter | Allowed Values | Description |
|---|---|---|
| `hookType` | `BEFORE` or `AFTER` | BEFORE = pre-hook, AFTER = post-hook |
| `timeout` | `5`, `10`, `30`, `60`, or `120` | Timeout in seconds for hook execution |
| `onFailure` | `FAIL` or `CONTINUE` | FAIL (stop on error) or CONTINUE (ignore errors) - block or continue agent execution on error during hook invocation |
| `canShortCircuit` | `true` or `false` | Whether this hook can stop agent execution |

**For post-hooks (hookType = AFTER) — ask only 2 parameters:**

| Parameter | Allowed Values | Description |
|---|---|---|
| `hookType` | `BEFORE` or `AFTER` | BEFORE = pre-hook, AFTER = post-hook |
| `timeout` | `5`, `10`, `30`, `60`, or `120` | Timeout in seconds for hook execution |

For post-hooks, do NOT ask for `onFailure` and `canShortCircuit`. Use default values: `onFailure: CONTINUE` and `canShortCircuit: true`.

**Example prompt for pre-hook (BEFORE):**
> To configure the hook for the workflow, I need the following information:
> 1. **Hook Type**: Should this hook run BEFORE (pre-hook) or AFTER (post-hook) the agent processing?
> 2. **Timeout**: What timeout in seconds? Options: 5, 10, 30, 60, 120
> 3. **On Failure**: If the hook fails, should the agent BLOCK (stop on error) or CONTINUE (ignore errors)?
> 4. **Can Short-Circuit**: Can this hook stop agent execution? (true/false)

**Example prompt for post-hook (AFTER):**
> To configure the hook for the workflow, I need the following information:
> 1. **Hook Type**: Should this hook run BEFORE (pre-hook) or AFTER (post-hook) the agent processing?
> 2. **Timeout**: What timeout in seconds? Options: 5, 10, 30, 60, 120

**Do NOT proceed to Step 4.2 until you have all required values from the user.**

### Step 4.2: Read Workflow Configuration

Fetch workflow asset files from the same solution. Then follow these steps:

1. **Get REST API ordIds**: Read the workflow's `asset.yaml` and extract **all** `provides.apis[]` entries where `kind: rest`. Each entry produces one hook — collect every `ordId` from these entries.

2. **Get HTTP method per REST API**: 
   - From the workflow's `asset.yaml`, get the file path from `workflow.definitionFile`
   - Read that workflow JSON file
   - For each REST API collected in step 1, find the webhook node whose `parameters.path` matches the API's `path` field (strip the leading `/` from the API path to compare — n8n stores the path without the leading slash)
   - Extract `parameters.httpMethod` from that matched node
   - Each REST API gets its own method from its own webhook node

3. **Generate hook entries in `extension.yaml`** — one entry per REST API collected in step 1, all sharing the same hookType, timeout, onFailure, canShortCircuit, and method:

**For pre-hooks (BEFORE):**
```yaml
hooks:
  # One entry per kind:rest API in provides.apis[] — repeat the block below for each
  - hookId: "<from base agent supportedHooks>"
    name: "<descriptive name>"
    hookType: BEFORE
    deploymentType: N8N
    onFailure: "<FAIL or CONTINUE - from user input>"
    timeout: <5|10|30|60|120 - from user input>
    canShortCircuit: <true|false - from user input>
    n8nWorkflowConfig:
      ordId: "<ordId of this REST API from provides.apis[]>"
      name: "<from workflow asset.yaml: workflow.name>"
      method: "<parameters.httpMethod of the webhook node whose path matches this API's path>"
```

**For post-hooks (AFTER):**
```yaml
hooks:
  # One entry per kind:rest API in provides.apis[] — repeat the block below for each
  - hookId: "<from base agent supportedHooks>"
    name: "<descriptive name>"
    hookType: AFTER
    deploymentType: N8N
    onFailure: CONTINUE
    timeout: <5|10|30|60|120 - from user input>
    canShortCircuit: true
    n8nWorkflowConfig:
      ordId: "<ordId of this REST API from provides.apis[]>"
      name: "<from workflow asset.yaml: workflow.name>"
      method: "<parameters.httpMethod of the webhook node whose path matches this API's path>"
```

### Step 4.3: Add Workflow Dependency to `asset.yaml`

Add a `requires` entry for the n8n workflow to the agent extension's `asset.yaml`. Do NOT replace existing entries — append to the existing `requires` block, preserving the agent and any MCP server entries already present.

**One requires entry per workflow, regardless of how many hooks it backs.** If the workflow exposes two REST APIs and produces two hooks, still add only a single `type: n8n-workflow` entry:

```yaml
requires:
  - name: "<agent-title-kebab-case>"
    type: agent
    version: "<from tool: version>"
    ordId: "<from tool: ordId>"
  - name: "<from workflow asset.yaml: workflow.name>"
    type: n8n-workflow
```

**Important**: The `name` in the requires entry MUST match the `name` from `workflow.name` in the workflow's `asset.yaml`, NOT the `metadata.name`.

### Hook Configuration Example

Given a workflow folder `assets/workflows/invoice-notification-workflow/` with:

**asset.yaml:**
```yaml
apiVersion: asset.sap/v1
kind: Asset

metadata:
  name: invoice-notification-workflow
  description: Invoice unmatched notification workflow
  version: 1.0.0
  type: n8nworkflow

projectVersion: "1"
sourceRoot: "."

workflow:
  definitionFile: invoice-unmatched.n8n.json
  name: invoice-unmatched-notification
  ordId: sap.btpn8n:apiResource:ManagedN8nMcpServer:v1  # DEPRECATED: use provides.apis[].ordId in hooks instead

provides:
  apis:
    - name: invoice_notification
      path: /invoice-notification
      kind: rest
      description: Triggers the invoice unmatched notification workflow
      ordId: customer.build:apiResource:invoice-notification.invoiceNotification:v1
    - name: invoice_reminder
      path: /invoice-reminder
      kind: rest
      description: Triggers the invoice reminder workflow
      ordId: customer.build:apiResource:invoice-notification.invoiceReminder:v1
    - name: invoice_notification_mcp_server
      kind: mcp-server
      description: MCP server for invoice notification operations
      ordId: customer.build:apiResource:invoice-notification.invoiceNotificationMcpServer:v1
```

**invoice-unmatched.n8n.json:**
```json
{
  "nodes": [
    {
      "parameters": {
        "httpMethod": "POST",
        "path": "invoice-notification"
      },
      "type": "n8n-nodes-base.webhook",
      "webhookId": "abc123-def456"
    },
    {
      "parameters": {
        "httpMethod": "POST",
        "path": "invoice-reminder"
      },
      "type": "n8n-nodes-base.webhook",
      "webhookId": "abc123-def789"
    }
  ]
}
```

The resulting `extension.yaml`:
```yaml
_schema-version: "0.1.0"
kind: Extension

metadata:
  name: invoice-workflow-extension
  extensionUrl: https://<jouleHost>/new/build/solutions/9dcb86f8-8eef-4d18-bc51-663525028d80

agent:
  ordId: sap.example:agent:my-agent:v1
  identifier: 6e4226f8-7b40-4fae-88b7-ae8e7ac33c3c

capabilityImplementations:
  - capabilityId: default
    tools: []
    hooks:
      - hookId: agent_pre_hook
        name: Invoice Notification
        hookType: BEFORE
        deploymentType: N8N
        onFailure: CONTINUE
        timeout: 30
        canShortCircuit: true
        n8nWorkflowConfig:
          ordId: customer.build:apiResource:invoice-notification.invoiceNotification:v1
          name: invoice-unmatched-notification
          method: POST
      - hookId: agent_pre_hook_2
        name: Invoice Reminder
        hookType: BEFORE
        deploymentType: N8N
        onFailure: CONTINUE
        timeout: 30
        canShortCircuit: true
        n8nWorkflowConfig:
          ordId: customer.build:apiResource:invoice-notification.invoiceReminder:v1
          name: invoice-unmatched-notification
          method: POST
```

And the `requires` entry in `asset.yaml` (one entry for the workflow, regardless of how many hooks it backs):
```yaml
requires:
  - name: base-agent
    type: agent
    version: "1.0.0"
    ordId: "sap.ai:agent:example:v1"
  - name: invoice-unmatched-notification
    type: n8n-workflow
```

## Step 5: Set `extensionUrl`

After the solution is set up, fetch the solution URL to retrieve the platform URL for the solution. Then **add only** the `extensionUrl` field to the existing `metadata` block in `extension.yaml` — do NOT overwrite or remove other metadata fields like `name`:

```yaml
metadata:
  name: "<keep existing>"
  extensionUrl: "<fetched solution URL>"
```

This step MUST be performed as the final step — the `extensionUrl` is the complete host URL for the solution.
