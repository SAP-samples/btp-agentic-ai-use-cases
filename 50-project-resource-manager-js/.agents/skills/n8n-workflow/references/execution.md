# n8n Workflow Skill

## Invocation Rule

**Before generating any workflow JSON, check what IBD documents already exist in the current working directory and act accordingly:**

- **If `intent.md`, `product-requirements-document.md`, AND a `specification/` folder already exist**, the upstream chain already ran — proceed directly to the Steps below.
- **Otherwise** (any of the three documents is missing — e.g. this skill was invoked directly from a "create a workflow" request, or as a hook workflow inside an agent extension solution), run the missing upstream steps first, in order:
  1. Run the `intent-analysis` skill → writes `intent.md`.
  2. Run the `product-requirements-document` skill → writes `product-requirements-document.md`.
  3. Run the `specification` skill → writes the `specification/` folder.

Do NOT generate any `.n8n.json` file until all three documents exist. Generating `intent.md` alone is NOT sufficient — the PRD and specification MUST also be produced before any workflow node is planned or written.

## ⛔ CRITICAL RULES — read first, always follow

1. **NEVER** use `$env.*` variables in workflow JSON → use placeholder URLs like `https://your-sap-system.com/api`
2. **Always use SAP Custom Nodes when one exists for the required capability. Never substitute it with a generic core node.** See the [Subskill Routing mapping table](#subskill-routing) for the full capability-to-node mapping. If no SAP Node exists for the requested capability, document that outcome and only then fall back to an appropriate generic node.
3. **Separate deterministic API calls from agent reasoning.** Use SAP MCP Client nodes for any deterministic SAP API call (fetch, create, update, post). Use SAP Agent nodes only for analysis, reasoning, or content generation. Do not embed data fetching logic inside agent definitions. Do not use Set nodes as the mechanism for executing SAP actions — a `n8n-nodes-base.set` node stores data in n8n memory only and does not contact SAP. Any step that must post, create, update, or notify via SAP must be a `CUSTOM.sapMcpClient` node.
4. **ALWAYS** use `.n8n.json` extension and write to `assets/workflows/<workflow-name>/`
5. **DO NOT explain credentials, deployment, or setup steps in your response.** The n8n platform automatically detects missing credentials when the workflow is imported and prompts users via its UI. Mentioning this in your response is redundant and creates noise. Keep your response focused on what was created — not what the user needs to do next.

   After stating where the workflow was created, you may optionally include a business-facing summary that describes:
    - The workflow's purpose and trigger
    - The business roles involved
    - Key decisions and outcomes
    - Any non-obvious design choice, explained as a business reason (e.g. "human review can take time, so the submitter receives the outcome whenever the decision arrives") — not the technical mechanism

   Keep this summary focused on the business process only. Do not include:
    - Credentials
    - Node names
    - Deployment steps
    - Webhook URLs
    - n8n UI instructions
    - Operational prerequisites
    - Communication protocols or interaction patterns between systems

   You may name external systems once (e.g. "S/4HANA", "SAP Task Center") without describing how the systems interact.

   When the workflow includes a human-in-the-loop step, describe it in business terms only. Example: "The workflow pauses for approval. The manager receives a task to review and, once they respond, the process continues automatically."
6. **ALL changes to a workflow file MUST be applied in a single `Write` call.** Never use multiple sequential `Edit` or `Write` calls on the same file — doing so leaves the file in an invalid or incomplete state between writes, which can corrupt the workflow.

Construct the entire final JSON in memory first, then apply each pre-write check defined in the rules below, in order:

- **Topology and execution**
   - every node must be reachable from a trigger,
   - every convergence point must have a Merge node (see rule 9 and rule 15 for the IF-branch exception),
   - every execution path must fulfill the caller contract,
   - every routing step is grounded — no invented thresholds or fabricated rules,

- **Code node conventions**
   - every user-provided configuration constant is named in ALL_CAPS and placed at the top of its Code node,
   - every Code node with a user-provided configuration constant has a sticky note directly above it,

- **Validation and metadata**
   - `pinData` has been fetched via `pin-data-schemas` for every node type used and reconciled with the current node set (kept, renamed, re-synthesized for new or changed nodes), then merged onto the workflow's top-level `pinData` field,
   - validate with `validate-n8n-workflow`.

   Then write once. This applies equally to new files and edits to existing ones.
7. **STOP. Before planning or writing any node, verify it exists in the catalog.** Only use nodes returned by `search-nodes-catalog`. Never generate a node from base n8n training knowledge — if the search tools did not return it, do not use it. This applies to both new workflows and edits to existing ones.
    - **New workflows:** If a planned node is not returned by the search tools, do not use it. Find a workaround using nodes you can use and rewrite the plan. 
    - **Editing existing workflows:** Check all nodes in the existing file — not just the ones being added or changed. If a node that was not returned by the search tools is already present, do not silently preserve it. Instead, remove it and Inform the user: "This workflow contained the [display name] node, which was not supported in the current version. It was removed." Then proceed with the requested edits using only catalog-confirmed nodes.

8. **Every node must be reachable from a trigger.** Every executable path in the workflow must be reachable from at least one trigger node.

   Treat a node as a trigger when it is a known trigger-type node. As a naming heuristic, its `type`, lowercased, usually:
   - ends with `trigger`, or
   - ends with `.webhook`

   Do **not** treat response or action nodes such as `n8n-nodes-base.respondToWebhook` as triggers, even if they are related to webhook flows.

   Examples:
   - `n8n-nodes-base.webhook` → trigger
   - `n8n-nodes-base.respondToWebhook` → not a trigger

   Before writing the final workflow JSON, traverse the `connections` graph from each trigger and confirm that every non-trigger node is visited. If any node is unreachable, re-derive its intended role in the execution graph from the user's original prompt and reconnect it before writing.

9. **Every convergence point must have a Merge node.** This rule applies only to caller-based workflows — those triggered by `n8n-nodes-base.webhook`.

   A convergence exists when:
   - two or more parallel branches fan out from a common point, and
   - those branches connect, directly or indirectly, to the same downstream node.

   Requirements:
   - Converging branches must pass through a common Merge node before reaching any shared downstream node.
   - The Merge node does not need to be the direct predecessor of the shared node; intermediate nodes are allowed.

   Why this matters:
   - Without a Merge, each branch can trigger the shared node independently.
   - For `respondToWebhook`, the first response succeeds and later responses fail.
   - For other shared downstream nodes, this can cause duplicate execution, race-like behavior, or missing data from one branch when the shared node runs.

   Exception:
   - Independent branches that terminate separately are not convergences and do not require a Merge node.

   **Note on downstream expressions:** After a Merge node, `$json` refers to the merged output, not to a specific upstream branch. To read data from a particular upstream node, use a node reference such as `$('Node Name').item.json.field`, but only when that node is guaranteed to have produced data on the current execution path. If a field is created after the Merge on the unified path, use `$json`.

10. **Every execution path must fulfill the caller contract.** This rule applies only to caller-based workflows (see rule 9). These trigger types imply a contract: the caller expects a result regardless of which execution path is taken. Every path reachable from the trigger must contain at least one node that fulfills this contract.

   The preferred fulfillment is an explicit response to the caller via `n8n-nodes-base.respondToWebhook`. Other durable side effects (sending a notification, writing to a datastore, calling an external service) may be acceptable when an explicit response is not possible or appropriate, but they should not be used as a substitute where a direct response is expected.

   Requirements:
   - A Switch node in rules mode must define a fallback output so unmatched items continue on a valid path — without it, unmatched items follow a path with no nodes at all, silently dropping the caller contract.

11. **Structure user-provided configuration as a named constant block.** When a Code node contains data that the user supplied directly in the prompt — such as routing tables, decision matrices, threshold sets, policy mappings, or reviewer assignments — structure it as a named constant block:

   Required:
   - Define a single ALL_CAPS constant for the configuration data (e.g. `ROUTING_TABLE`, `APPROVAL_THRESHOLDS`).
   - Place the constant at the top of the node, before any logic.
   - One entry per line so individual values are easy to locate and change.
   - Keep all data values inside the constant block. Do not scatter magic numbers or strings through the logic.
   - Add a sticky note directly above the Code node.

   Example (JavaScript mode):
   ```javascript
   const ROUTING_TABLE = {
     "CC1000": "approver.a@example.com",
     "CC2000": "approver.b@example.com",
   };
   ```

   For each Code node that contains a user-provided configuration block, add a `n8n-nodes-base.stickyNote` node directly above it. Position it so it does not overlap any other node: place it at the same x as the Code node, choose a width wide enough to display the text without clipping, choose a height tall enough to show the full content, and set y so there is a small gap between the bottom of the note and the top of the Code node.

   Use this sticky note content:

   > This configuration is hardcoded — the values in this node reflect what you provided. If this data is maintained in a connected system, replace this node with a live lookup when that integration is available. For now, update the values in this node directly when they change.

12. **Ground every routing step before generating.** This is both the pre-generation decision point (if reached from intent analysis) and a pre-write enforcement gate. Before generating any conditional or routing node, determine whether the decision is fully defined in the prompt:

   - If the condition can be expressed as a fixed rule from information already present in the prompt or conversation → use an IF node or Switch node.
   - If the input is free-text, unstructured, or requires contextual judgment that no fixed rule can capture → use an Agent node.
   - If neither applies — the rule is not defined and the input is structured or of a known, bounded type — choose a reasonable default, explicitly state the assumed value in your response, and continue generating so the user can review or correct the assumption before activation. Stop and ask only when no reasonable default exists and the routing structure would be materially wrong without it.
   - **User explicitly requests AI-based routing** → use an Agent node for the inference step and a Switch/IF node to route on its structured output. This combination is intentional — the Agent infers, the IF/Switch routes on the result.

   Fabricating routing logic — such as invented thresholds, keyword scoring, or any rule not grounded in the prompt — creates workflows with unapproved behavior and increases the risk of incorrect runtime decisions.

13. **Validate the workflow JSON BEFORE writing the file.** Use the `validate-n8n-workflow` MCP tool on the fully constructed JSON before any file write. Pass two arguments: `workflow` — the full workflow JSON serialized as a string — and `assetYaml` — the contents of the workflow's `asset.yaml` (at `assets/workflows/<workflow-name>/asset.yaml` under the solution root) read as a YAML string. Only proceed with the `Write` call after validation passes (or after understanding which errors are expected and acceptable, e.g. missing credential IDs).

14. **Webhook node wraps the POST body — always access data via `$json.body.*`, never `$json.*` directly.** The `n8n-nodes-base.webhook` node wraps the incoming request into an envelope with `headers`, `params`, `query`, `body`, `webhookUrl`, and `executionMode`. The actual POST body is at `$json.body`, not at `$json`.

   - A field `foo` sent in the POST body → `$json.body.foo`
   - An array `items` sent in the POST body → `$json.body.items`
   - To expand a body array into individual n8n items, use a **Split Out** node (`n8n-nodes-base.splitOut`) immediately after the Webhook node with `fieldToSplitOut: "body.<arrayField>"`. Do NOT use `splitInBatches` for this purpose — `splitInBatches` splits existing n8n items, it does not expand an array field.

   **Mandatory pattern for any webhook workflow that processes a list from the body:**
   ```
   Webhook → Split Out (fieldToSplitOut: "body.items") → [per-item processing nodes]
   ```

   Never reference `$json.name`, `$json.quantity`, or any top-level field from the POST body directly after a Webhook node — these will be `undefined`. Always prefix with `$json.body.`.

15. **IF-branch convergence to a shared Aggregate node does NOT require a Merge node.** Rule 9 (Merge at convergence) applies to parallel branches that produce independent results that must be combined before a single downstream execution. It does NOT apply when two branches of an IF node both feed the same Aggregate node — in that case the Aggregate collects items from whichever branch fires, naturally and correctly, without a Merge. Adding a Merge node in this pattern causes a deadlock: if all items go to one branch, the Merge waits forever for the empty branch.

   - **IF true-branch → Aggregate, IF false-branch → Aggregate** → correct, no Merge needed
   - **Two parallel execution branches → shared respondToWebhook** → Merge IS required (rule 9 applies)

17. **NEVER use HTTP Request nodes.** This rule overrides any conflicting examples or instructions elsewhere in the documentation because HTTP Request nodes are not available on the target system. Use **SAP MCP Client** nodes for any outbound calls.



16. **NEVER put outbound HTTP calls inside Code nodes.** The n8n-workflow-mgr upload pipeline runs a static analysis check and **rejects the upload with a 400 error** if any Code node (JavaScript or Python) contains a direct HTTP call. The following patterns are all blocked:
   JavaScript — blocked patterns:
   - `this.helpers.httpRequest(...)` / `this.helpers.request(...)`
   - `fetch(...)`
   - `require('https')` / `require('http')` / `require('axios')` / `require('node-fetch')` / `require('got')` / `require('superagent')` / `require('undici')`
   - `axios.get(...)`, `https.request(...)`, or any method call on a blocked module
   - `new XMLHttpRequest()`

   Python — blocked patterns:
   - `import requests` / `import httpx` / `import aiohttp`
   - `import urllib` / `import urllib.request` / `import urllib3`
   - `import http` / `import http.client`
   - All `from <module> import` variants of the above

   **What to do instead:** Use an SAP MCP Client node, or another integration node. All outbound HTTP must live in a node, not in a Code node script.


## Key Constraints

- **NEVER** answer with the n8n URL in the message
- Each workflow gets its own asset folder under `assets/workflows/<workflow-name>/`. The asset type is `n8nworkflow` declared inside `metadata.type`.
- Do not derive the type from naming conventions.

## References

- [workflow-hooks.md](./references/workflow-hooks.md): ONLY read this file when the user is creating a **pre-hook or post-hook** workflow for an **agent extension** scenario. It contains the A2A message protocol, hook-specific response patterns, and examples. Do NOT read it for regular (non-hook) workflows.

## External API Integration Rules

Choose the integration pattern in this order:

1. **Use a dedicated n8n node** when one exists for the target service.
   - Example: Use the Outlook node to send email.

2. **Use the `n8n-sap-mcp-client` skill** for SAP systems and SAP services.
   - Example: S/4HANA, SAP BTP services exposed through MCP.

3. **Use an MCP server wrapper plus the `n8n-sap-mcp-client` skill** for custom LOB systems or internal APIs.
   - Example: Legacy systems, internal databases, custom services.

**Do not use HTTP Request nodes as a fallback** for the scenarios above.

## SAP Node Detailed Rules

SAP Nodes are the default choice whenever they cover the requested capability. Use generic n8n nodes only when no SAP Node exists for that use case.

### Subskill Routing

Analyze the user prompt and invoke the relevant SAP subskills. The table below maps signals to subskills. When in doubt, prefer the SAP subskill first and let the catalog lookup confirm availability.

| Signal type | Examples | Action |
|-------------|----------|--------|
| Strong SAP-specific signals | `SAP Task Center`, `SAP AI Core`, `SAP Agent`, `SAP MCP Client`, `S/4HANA` | Invoke the matching subskill (`n8n-sap-task-center`, `n8n-sap-ai-core`, `n8n-sap-agent`, `n8n-sap-mcp-client`) |
| Contextual SAP workflow signals | `purchase requisition in S/4HANA`, `SAP sales order`, `SAP invoice extraction`, `approval in SAP Task Center`, `SAP agent orchestration`, `extract with SAP AI Core` | Invoke the matching subskill |
| Ambiguous terms that match a SAP capability | `AI`, `LLM`, `chat`, `analyze`, `agent`, `approval`, `invoice`, `purchase requisition`, `sales order`, `task` (without explicit non-SAP context) | Invoke the matching SAP subskill by default; the catalog lookup will confirm whether the node is available |

**Mapping table:**
- **SAP Task Center** → `n8n-sap-task-center` skill (mandatory Switch node pattern after Task Center)
- **SAP AI Core** → `n8n-sap-ai-core` skill (NEVER use OpenAI/Gemini, only SAP AI Core nodes)
- **SAP Agent** → `n8n-sap-agent` skill (SAP Agent node configuration and credentials)
- **SAP MCP Client / S/4HANA** → `n8n-sap-mcp-client` skill (NEVER use HTTP Request for SAP, use MCP Client)

> **Set nodes are NOT SAP actions.** `n8n-nodes-base.set` only stores data in n8n memory — it does not contact SAP. Any step that must post, create, update, or notify via SAP must be a `CUSTOM.sapMcpClient` node. See `n8n-sap-mcp-client` for the correct pattern.

**Example:** User prompt "Create workflow with SAP Agent for approval escalation"
→ Detected strong signals: "SAP Agent", contextual signal: "approval escalation"
→ MUST invoke: `n8n-sap-agent`, `n8n-sap-task-center`
→ Read and follow ALL rules from both skill files

## Steps

### **MANDATORY: Setup the Solution**
1. Identify any `CUSTOM.sapAgent` or `CUSTOM.sapMcpClient` nodes in the workflow.
2. Run the `setup-solution` skill (if not already done), passing the node types from step 1 — follow the **Example 1: Multi-Asset Solution (Agent + n8n Workflow + MCP Server)** in that skill.
3. If the workflow contains `CUSTOM.sapAgent` nodes and the solution already has agents, read each agent's `asset.yaml` to collect their `provides.apis[].ordId` values, then derive the agent ORD ID by replacing `apiResource` with `agent` (e.g. `customer.build:apiResource:...:v1` → `customer.build:agent:...:v1`). Populate the `agents` parameter on every SAP Agent node with the full list using these derived ORD IDs. Follow the `agents` and `agentName` parameter shapes defined in `n8n-sap-agent.md`.

### **Set up project folder**
If `assets/workflows/<workflow-name>/` already exists, use it. Otherwise create it:
   ```bash
   mkdir -p assets/workflows/<workflow-name>/
   ```

When part of a multi-asset solution, add the following entry to `solution.yaml`:
```yaml
  - ref: ./assets/workflows/<workflow-name>/asset.yaml
```

### **MANDATORY: Look up nodes from the catalog (MUST do this for EVERY node)**

Before writing ANY node in the workflow JSON, you MUST look up its exact `type` and `typeVersion` from the catalog.

Required verification checklist:
- Call `search-nodes-catalog` MCP tool once with all planned node keywords.
- Use the returned `name` as `type` and `version` as `typeVersion`.
- Never use a node that was not returned by the catalog.
- If a planned node was not searched for, stop and search for it before continuing.
- If the catalog does not return a node, choose an alternative approach or tell the user the requested solution is not available.
- Before generating the workflow JSON, confirm every planned node appears in the catalog results.
- Custom/SAP nodes (e.g. `CUSTOM.approvalTask`) include full `properties` in the output to help you configure them correctly.

### **MANDATORY: Create the file in the filesystem**
Write workflow files to `assets/workflows/<workflow-name>/` only. The file **MUST** use the `.n8n.json` extension (for example, `morning-email-workflow.n8n.json`). NEVER use MCP to create or update workflow files.

Every workflow JSON **MUST** include a `"description"` field at the top level that accurately summarises what the workflow does. When editing an existing workflow, update the `"description"` to reflect any changes made.

### **MANDATORY: Credential policy — never embed instance-specific credentials**
Generated workflow JSON must **never** contain instance-specific credential IDs or names. Credentials are instance-specific and are resolved automatically during solution deployment. No input from the user is required.

For every node that requires authentication, omit the `credentials` field entirely. Do not embed credential IDs, names, or placeholders.

If validation reports a missing credential error, that is expected and acceptable.

### **MANDATORY: Generate workflow ordId and API ORD IDs**
After the workflow JSON file is written, run the following script to generate the `workflow` block and `provides.apis[]` entries for `asset.yaml`:

```bash
node skills/n8n-workflow/scripts/generate-workflow-asset.js assets/workflows/<workflow-name>/<workflow-name>.n8n.json <workflow-name> <solution-name>
```

Example:
```bash
node skills/n8n-workflow/scripts/generate-workflow-asset.js assets/workflows/leave-request/leave-request.n8n.json leave-request-workflow my-solution
```

Example output:
```yaml
workflow:
  definitionFile: leave-request.n8n.json
  name: leave-request-workflow
  ordId: sap.btpn8n:apiResource:ManagedN8nMcpServer:v1

provides:
  apis:
    - name: leave_request_submitted
      path: /my-solution-3f8a1/leave-request-workflow/leave-request-submitted
      kind: rest
      description: <add description>
      ordId: sap.n8nwfrt:apiResource:my-solution-3f8a1_leave-request-workflow.leaveRequestSubmitted:v1
    - name: leave_request_submitted_mcp_server
      kind: mcp-server
      description: MCP server for leave request submitted operations
      ordId: sap.n8nwfrt:apiResource:my-solution-3f8a1_leave-request-workflow.leaveRequestSubmittedMcpServer:v1
```

Paste the output verbatim into `asset.yaml`. The only field to fill in is the `description` value for each `kind: rest` entry — write a one-sentence description of what each webhook does based on the workflow context. The script also rewrites each webhook node's `parameters.path` to the full path `<solution-name>/<workflow-name>/<operation>` (matching `provides.apis[].path` without the leading slash) so the runtime appends it to the tenant URL as-is — no webhook URL is generated at deploy time. Do not hand-edit either path.

If the workflow has **no** webhook nodes, the script outputs only the `workflow:` block — the `provides.apis[]` block is omitted from `asset.yaml`.

### **MANDATORY when applicable: Generate MCP server for in-solution agent consumption**

**Evaluate all three conditions below right now — before moving to the next section.** If all three hold, this step is **required**; skipping it leaves the solution incomplete and non-functional.

1. The solution contains at least one agent asset — check `solution.yaml` for a `ref:` entry pointing to an `asset.yaml` with `type: agent`.
2. The workflow is triggered by a webhook — it has an `n8n-nodes-base.webhook` node as its entry point (trigger). A webhook node used elsewhere in the workflow, not as the trigger, does not count. The script above will have produced a `provides.apis[]` block two entries: a `kind: rest` entry and a corresponding `kind: mcp-server` entry when this is the case.
3. The specification (intent.md, PRD, tasks.md, or the agent's own specification) indicates the agent should call, trigger, or invoke this workflow in any way. The MCP wrapping is an infrastructure detail added by IBD — the spec does not need to mention MCP explicitly.

If all three conditions hold, **complete Steps A–F before continuing**. If any condition is not met, skip this step entirely.

#### Step A — Generate the OpenAPI spec

Run the script and redirect its output to the folder that the `mcp-translation-file` skill expects:

```bash
mkdir -p specification/<workflow-name>-mcp-server/api-specs
node skills/n8n-workflow/scripts/generate-webhook-openapi.js \
  assets/workflows/<workflow-name>/<workflow-name>.n8n.json \
  <workflow-name> \
  > specification/<workflow-name>-mcp-server/api-specs/<workflow-name>-webhook-api.json
```

If the script outputs `{}` (no webhook nodes), abort Steps A–F — there is nothing to expose as an MCP server.

#### Step B — Prepare the `mcp-translation-file` skill prerequisites

The `mcp-translation-file` skill requires a `specification/<asset-name>/specification.md` whose content references an API integration. Create the file if it does not already exist:

File: `specification/<workflow-name>-mcp-server/specification.md`

```markdown
# <workflow-name>-mcp-server MCP Translation

## Tasks

- Generate MCP translation for webhook API integration with ORD ID `<rest-api-ordId>`.
```

Replace `<rest-api-ordId>` with the value from `provides.apis[].ordId` where `kind: rest` in `assets/workflows/<workflow-name>/asset.yaml` — the value that `generate-workflow-asset.js` produced in the previous step.

#### Step C — Run the `mcp-translation-file` skill

Invoke the `mcp-translation-file` skill with asset name `<workflow-name>-mcp-server`. The skill will:

- Locate the API spec at `specification/<workflow-name>-mcp-server/api-specs/<workflow-name>-webhook-api.json`
- Resolve the ORD ID from `specification/<workflow-name>-mcp-server/specification.md`
- Write output files to `specification/<workflow-name>-mcp-server/mcps/<workflow-name>-webhook-api/`

After the skill completes successfully, copy the generated files into the MCP server asset folder so they ship with the deployable asset:

```bash
mkdir -p assets/<workflow-name>-mcp-server/mcp-translation
cp specification/<workflow-name>-mcp-server/mcps/<workflow-name>-webhook-api/translation.json \
   assets/<workflow-name>-mcp-server/mcp-translation/translation.json
cp specification/<workflow-name>-mcp-server/mcps/<workflow-name>-webhook-api/api-spec.json \
   assets/<workflow-name>-mcp-server/mcp-translation/api-spec.json
```

#### Step D — Create the mcp-server `asset.yaml`

Write `assets/<workflow-name>-mcp-server/asset.yaml`. The MCP card ORD ID (`<mcp-card-ordId>`) must be derived from the REST ORD ID using the ADR-021 §8.1 convention:

1. From the workflow's `asset.yaml`, find the `provides.apis` entry where `kind: rest`. Use **only this entry** — do **not** use the `kind: mcp-server` entry that the workflow script also generates (it uses a different `McpServer` camelCase suffix and serves a different purpose).
2. Take that REST entry's `ordId` and append `_mcp` to the `apiName` segment (the part between the last `.` and `:v1`).

Example derivation:
- REST ORD ID (from workflow asset.yaml, `kind: rest`): `sap.n8nwfrt:apiResource:my-solution_leave-request-workflow.leaveRequestSubmitted:v1`
- MCP card ORD ID: `sap.n8nwfrt:apiResource:my-solution_leave-request-workflow.leaveRequestSubmitted_mcp:v1`
- **Wrong** (do not copy): `sap.n8nwfrt:apiResource:my-solution_leave-request-workflow.leaveRequestSubmittedMcpServer:v1` ← this is the workflow's own `kind: mcp-server` entry; ignore it here

```yaml
apiVersion: asset.sap/v1
kind: Asset
type: mcp-server

metadata:
  name: <workflow-name>-mcp-server
  version: "1.0.0"
  translation: mcp-translation/translation.json
  apiSpec: mcp-translation/api-spec.json

requires:
  - name: <webhook-snake-name>        # snake_case of the webhook node name
    kind: api
    ordId: <rest-api-ordId>           # provides.apis[].ordId where kind: rest

provides:
  apis:
    - name: <webhook-snake-name>-mcp-server
      kind: mcp-server
      description: MCP server for <workflow-name> webhook operations
      ordId: <mcp-card-ordId>         # REST ORD ID with _mcp appended to apiName segment (see derivation above)
```

If the workflow has **multiple** webhook nodes, add one `requires` entry and one `provides.apis` entry per webhook node, deriving each `<mcp-card-ordId>` from its corresponding `kind: rest` entry.

#### Step E — Update `solution.yaml`

Add the new mcp-server asset reference to `solution.yaml`:

```yaml
  - ref: ./assets/<workflow-name>-mcp-server/asset.yaml
```

#### Step F — Update every agent's `asset.yaml`

Find all agent assets in the solution:
1. Read `solution.yaml`.
2. For each `ref:` entry, read the target `asset.yaml`.
3. Collect every asset whose `type` field equals `agent`.

For each agent found, add a `requires` entry to its `asset.yaml` **only if** the specification (intent.md, PRD, tasks.md, or the agent's own specification) indicates that this agent should call, trigger, or invoke this workflow. Merge with any existing `requires` entries — do not overwrite them.

```yaml
requires:
  - name: <workflow-name>-mcp-server
    kind: mcp-server
    ordId: <mcp-card-ordId>           # same value as in Step D (REST ORD ID with _mcp appended to apiName)
```

Then update `app/agent.py` in the same agent directory to instruct the agent to use the MCP tool rather than calling the webhook URL directly. Append a sentence to the system prompt such as:

> To invoke the `<workflow-name>` workflow, use the `<tool-name>` MCP tool. Do not call workflow webhook URLs directly.

Derive `<tool-name>` from the MCP card ORD ID: take the `apiName` segment (e.g. `leaveRequestSubmitted_mcp`), then strip the `_mcp` suffix → `leaveRequestSubmitted`. The agent directory is the folder that contains the `asset.yaml` identified in step 2 above.

If no agent assets are found in `solution.yaml`, skip this step.

### **MANDATORY: Fetch pinData schemas and embed sample pinData**
Before validation, populate the workflow's top-level `pinData` object with sample data for every node whose schema can be served by the SAP pinData library. This must happen inside the same in-memory JSON that will be validated and written — never as a follow-up edit.

Required steps:
1. Build the input list from the catalog results already obtained in the "Look up nodes from the catalog" step:
   - Include **every** node type used in the workflow — both SAP (`CUSTOM.*`) and generic (`n8n-nodes-base.*`). Do not pre-filter; the tool moves non-SAP entries into `notFound` on its own.
   - Deduplicate by `type`, and use the exact `typeVersion` that `search-nodes-catalog` returned for each.
2. Call the `pin-data-schemas` MCP tool once with the full list:
   ```json
   { "nodes": [ { "type": "CUSTOM.sapMcpClient", "typeVersion": 1 }, { "type": "n8n-nodes-base.webhook", "typeVersion": 2 } ] }
   ```
3. For every entry in the returned `schemas` object, find each node in the workflow whose `type` matches. For each match, synthesize **one** sample item that conforms to the returned JSON Schema (respect `required`, `type`, `enum`, `format`; use plausible placeholder values) and add it under `pinData[<node.name>]` as a single-element array. If the same `type` appears on multiple nodes, generate a separate sample object for each node — never share a reference across nodes.
4. Entries in `notFound` are expected:
   - `reason: "non-sap"` → generic n8n nodes; skip silently.
   - `reason: "no-schema"` → SAP node not yet in the library; skip silently.
   - `reason: "duplicate-type"` → already handled from a prior `schemas` entry; skip silently.
   - `reason: "version-mismatch"` → keep the `typeVersion` from the catalog (it drives the node's real behavior); do **not** downgrade to `closestVersion`. Skip the pinData entry for this node.
5. Merge the resulting object into the workflow's top-level `pinData` field, replacing any `pinData: {}` placeholder. Only include entries for nodes actually present in the workflow.
6. If the workflow has zero nodes, skip the tool call.

**On edits to an existing workflow:** Still call `pin-data-schemas` — the fetch is unconditional so the model always has fresh schemas for every node type currently in the workflow. Then reconcile with the existing `pinData` before writing:
- Read the current top-level `pinData` from the in-memory workflow.
- Keep every existing `pinData[<name>]` entry whose node is still present and whose `type` and `typeVersion` are unchanged. Do not re-synthesize over user-provided or previously pinned sample data.
- If a node was renamed (its `name` changed but `type` and `typeVersion` are the same), move the existing `pinData` entry from the old key to the new `name` rather than dropping and re-synthesizing.
- Delete `pinData[<name>]` entries whose node was removed from the workflow.
- Only synthesize new sample data (using the schemas from the `pin-data-schemas` call above) for nodes that (a) are new to the workflow, (b) had their `type` or `typeVersion` changed, or (c) previously had no `pinData` entry.

Example — a workflow with an SAP MCP Client node named `Get Blocked Invoices (S/4HANA)`:
```json
"pinData": {
  "Get Blocked Invoices (S/4HANA)": [
    {
      "mcpServer": { "globalTenantId": null, "name": "S/4HANA Cloud", "ordId": "sap.s4:apiResource:supplier-invoice:v1" },
      "requestId": "req-test-001",
      "result": { "content": [{ "text": "Retrieved 2 blocked invoices", "type": "text" }], "isError": false, "structuredContent": { "invoices": [] } }
    }
  ]
}
```
### **Validate the workflow**
**Pre-validation gate:** Before running the validator, confirm that the MCP server step was handled. If the three conditions in the ["MANDATORY when applicable"](#mandatory-when-applicable-generate-mcp-server-for-in-solution-agent-consumption) section above all hold — verify that `assets/<workflow-name>-mcp-server/` exists with a valid `asset.yaml`. If it does not exist, **stop and complete Steps A–F now** before continuing.

Before writing the workflow file, validate the fully constructed workflow JSON with the `validate-n8n-workflow` MCP tool, following the rule above. Pass two arguments: `workflow` — the full workflow JSON serialized as a string — and `assetYaml` — the contents of the workflow's `asset.yaml` (at `assets/workflows/<workflow-name>/asset.yaml` under the solution root) read as a YAML string. If validation returns errors, fix the workflow before writing it. Some errors are expected and cannot be fixed by the agent — for example, credentials with `"id": "MISSING"`. In those cases, inform the user and leave the credential configuration to be done manually in the n8n UI.

### **Delete workflows**
Use the n8n MCP tool only for deletion from the remote n8n instance.

## CRITICAL: Node parameter rules

- **ONLY use parameters exactly as shown in the example below**. NEVER invent or add extra parameters.
- **NEVER use n8n environment variables** (e.g. `$env.MY_VAR`, `={{ $env.SOME_VALUE }}`) in any generated workflow.
- **NEVER include post-import setup instructions in your response** — do not mention configuring credentials, updating placeholders, deploying, or any setup step. The workflow file is the only deliverable.
- After stating where the workflow was created, you may optionally include a business-facing summary, as described in Rule 4.
- Forbidden phrases include: "Before deploying", "Configuration Required", "You'll need to configure", "Before activating", "Update the placeholders", "Credentials Required", or any similar guidance.

- **Webhook `path` is generated, not hand-authored** — the `generate-workflow-asset.js` script derives the operation segment from the webhook node's **name** (kebab-case) and rewrites the node's `parameters.path` to the full `<solution-name>/<workflow-name>/<operation>` path. Whatever `path` you set on the webhook node is overwritten, so it always matches the API `name` (snake_case) and ordId (camelCase) — all three come from the node name. Because node names are unique within a workflow, the paths are unique too. Never hand-edit the generated path.
- **Webhook `name` in the n8n node MUST be descriptive and business-meaningful** — the webhook node's display name is used to derive the `path`, the API `name`, and the `ordId` of the API entry in the workflow's `asset.yaml`, so it must clearly describe what the endpoint does. Use the workflow's business purpose (e.g. "Prime Number Calculator", "Array Sorter", "Leave Request Submitted", "Blocked Invoice Received"), NEVER generic technical terms like "Webhook", "API", or "Endpoint".
- **SAP Task Center recipients**: At least one recipient target must be configured (`recipients` or `recipientGroups`). For exact parameter shapes, defaults, and naming rules, follow the dedicated `n8n-sap-task-center` skill.

**For SAP Nodes:** All detailed rules (parameters, credentials, patterns) are in the dedicated SAP skills. Always invoke the appropriate skill (`n8n-sap-task-center`, `n8n-sap-ai-core`, `n8n-sap-agent`, `n8n-sap-mcp-client`) as indicated by the routing table above.

**When a new agent is added to the solution:** Read every existing `.n8n.json` workflow file in the solution and update the `agents` parameter on every `CUSTOM.sapAgent` node to include the new agent. Every SAP Agent node must always reflect the full list of solution agents. Follow the `agents` and `agentName` parameter shapes defined in `n8n-sap-agent.md`.
