## Important Notes

- agent.json includes agentCard, models, secrets, HPA, probes, resources, virtualService, etc.

### Examples

#### Example 1: Python Agent Asset

```yaml
apiVersion: asset.sap/v1
kind: Asset
metadata:
  name: ai-assistant-agent
type: agent
provides:
  apis:
    - name: ai-assistant-agent
      kind: a2a
      ordId: customer.build:apiResource:claims-automation-3f8a1.ai-assistant-agent:v1
container:
  buildPath: .
  port: 5000
requires:
  - name: CE_COSTCENTER_0001_MCP
    kind: mcp-server
    ordId: customer.build:apiResource:claims-automation-3f8a1.ce-costcenter-0001-mcp-server:v1
probes:
  startup:
    path: /.well-known/agent.json
    periodSeconds: 5
    timeoutSeconds: 3
    failureThreshold: 18
  liveness:
    path: /.well-known/agent.json
    initialDelaySeconds: 15
    periodSeconds: 10
    timeoutSeconds: 5
    failureThreshold: 3
  readiness:
    path: /.well-known/agent.json
    initialDelaySeconds: 5
    periodSeconds: 5
    timeoutSeconds: 3
    failureThreshold: 3
```

When an agent needs to consume an existing Data Product, add the DPQuery MCP's ORD ID to the agent's `asset.yaml` under `requires`:

```yaml
# In assets/agent/asset.yaml:
apiVersion: asset.sap/v1
kind: Asset
type: agent
metadata:
  name: my-agent
# ... other agent config ...
requires:
  - name: dpquery
    kind: mcp-server
    ordId: sap.bdc.dpq:apiResource:mcp-dpquery:v1
```

#### Example 2: Multi-Asset Solution (Agent + MCP Servers)

```yaml
apiVersion: solution.sap/v1
kind: Solution
metadata:
  name: full-stack-app-7c2e4
  version: "1.0.0"
  description: "Agent + MCP Server example"
assets:
  - ref: ./assets/agent/asset.yaml
  - ref: ./assets/s4-dispute-mcp-server/asset.yaml
```

When an agent needs access to tools defined in MCP Server translation files, add the MCP Server ORD IDs to the agent's `asset.yaml` under `requires`:

```yaml
# In assets/agent/asset.yaml:
apiVersion: asset.sap/v1
kind: Asset
type: agent
metadata:
  name: my-agent
# ... other agent config ...
requires:
  - name: S4_DISPUTE_MCP
    kind: mcp-server
    ordId: customer.build:apiResource:full-stack-app-7c2e4.s4-dispute-mcp-server:v1
```

For newly created MCP Server assets, the ORD IDs in the `requires` field of the agent's `asset.yaml` must match the ORD IDs of the MCP Server assets defined in their respective `asset.yaml` files.
For existing MCP Servers with known ORD IDs, the ORD IDs in the `requires` field of the agent's `asset.yaml` must match the known ORD IDs of the existing MCP Servers. Include the `version` field if it was returned by `get_mcp` and recorded in `intent.md`.

#### Example 3: Multi-Asset Solution (Agent + n8n Workflow)

When a solution includes both an AI agent and one or more n8n workflows, every asset **MUST** be referenced in `solution.yaml`.

```yaml
# solution.yaml
apiVersion: solution.sap/v1
kind: Solution
metadata:
  name: invoice-approval-3a9f2
  version: "1.0.0"
  description: "Invoice approval with AI agent and n8n workflow"
assets:
  - ref: ./assets/invoice-approval-agent/asset.yaml
  - ref: ./assets/workflows/invoice-approval-workflow/asset.yaml
```

```yaml
# assets/workflows/invoice-approval-workflow/asset.yaml
apiVersion: asset.sap/v1
kind: Asset

metadata:
  name: invoice-approval-workflow
  description: Invoice approval workflow
  version: "1.0.0"
  type: n8nworkflow

projectVersion: "1"
sourceRoot: "."

workflow:
  definitionFile: invoice-approval.n8n.json
  name: invoice-approval-workflow
  ordId: sap.btpn8n:apiResource:ManagedN8nMcpServer:v1
```

> `sourceRoot: "."` means `definitionFile` is resolved relative to `assets/workflows/invoice-approval-workflow/`. The workflow file is therefore at `assets/workflows/invoice-approval-workflow/invoice-approval.n8n.json`.

The folder structure for this solution:

```
./
├── solution.yaml
└── assets/
    ├── invoice-approval-agent/
    │   ├── asset.yaml
    │   └── ...
    └── workflows/
        └── invoice-approval-workflow/
            ├── asset.yaml
            └── invoice-approval.n8n.json
```
```

#### Example 4: Multi-Asset Solution (Agent + n8n Workflow + MCP server)

When an agent in the solution should **invoke** an n8n workflow via MCP, a third asset — the workflow's mcp-server translation card — is required alongside the agent and the workflow. All three must be listed in `solution.yaml`.

```yaml
# solution.yaml
apiVersion: solution.sap/v1
kind: Solution
metadata:
  name: leave-request-3a9f2
  version: "1.0.0"
  description: "Agent triggers leave-request workflow via MCP"
assets:
  - ref: ./assets/leave-request-agent/asset.yaml
  - ref: ./assets/workflows/leave-request-workflow/asset.yaml
  - ref: ./assets/leave-request-workflow-mcp-server/asset.yaml
```

The agent's `asset.yaml` uses a `requires` entry that references the mcp-server asset by **name** and the `_mcp`-suffixed ORD ID (ADR-021 §8.1 translation card convention):

```yaml
# assets/leave-request-agent/asset.yaml
apiVersion: asset.sap/v1
kind: Asset
type: agent
metadata:
  name: leave-request-agent
provides:
  apis:
    - name: leave-request-agent
      kind: a2a
      ordId: customer.build:apiResource:leave-request-3a9f2.leave-request-agent:v1
requires:
  - name: leave-request-workflow-mcp-server   # matches metadata.name in the mcp-server asset
    kind: mcp-server
    ordId: sap.n8nwfrt:apiResource:leave-request-3a9f2_leave-request-workflow.leaveRequestSubmitted_mcp:v1
probes:
  startup:
    path: /.well-known/agent.json
    periodSeconds: 5
    timeoutSeconds: 3
    failureThreshold: 18
  liveness:
    path: /.well-known/agent.json
    initialDelaySeconds: 15
    periodSeconds: 10
    timeoutSeconds: 5
    failureThreshold: 3
  readiness:
    path: /.well-known/agent.json
    initialDelaySeconds: 5
    periodSeconds: 5
    timeoutSeconds: 3
    failureThreshold: 3
```

The mcp-server asset uses a top-level `type: mcp-server` field (never `metadata.type`) and mirrors the `_mcp` ORD ID in its `provides.apis[]`:

```yaml
# assets/leave-request-workflow-mcp-server/asset.yaml
apiVersion: asset.sap/v1
kind: Asset
type: mcp-server

metadata:
  name: leave-request-workflow-mcp-server
  version: "1.0.0"
  translation: mcp-translation/translation.json
  apiSpec: mcp-translation/api-spec.json

requires:
  - name: leave_request_submitted
    kind: api
    ordId: sap.n8nwfrt:apiResource:leave-request-3a9f2_leave-request-workflow.leaveRequestSubmitted:v1

provides:
  apis:
    - name: leave-request-submitted-mcp-server
      kind: mcp-server
      description: MCP server for leave request webhook operations
      ordId: sap.n8nwfrt:apiResource:leave-request-3a9f2_leave-request-workflow.leaveRequestSubmitted_mcp:v1
```

> The `_mcp` ORD ID is derived from the workflow's `kind: rest` ORD ID by appending `_mcp` to the `apiName` segment (e.g. `leaveRequestSubmitted` → `leaveRequestSubmitted_mcp`). Do **not** copy the `kind: mcp-server` entry that the workflow script also generates — it uses a `McpServer` camelCase suffix and serves a different purpose.

The folder structure:

```
solution.yaml
assets/
├── leave-request-agent/
│   ├── asset.yaml
│   └── app/
│       └── agent.py   ← system prompt includes: "use the leaveRequestSubmitted MCP tool"
├── workflows/
│   └── leave-request-workflow/
│       ├── asset.yaml
│       └── leave-request-workflow.n8n.json
└── leave-request-workflow-mcp-server/
    ├── asset.yaml
    └── mcp-translation/
        ├── translation.json
        └── api-spec.json
```

#### Removing an agent from a multi-asset solution

When an agent is deleted from the solution:

1. **Remove from `solution.yaml`** — delete the agent's `asset.yaml` reference from the `assets` list.

2. **Update n8n workflows** — if the solution contains `.n8n.json` files with `CUSTOM.sapAgent` nodes, remove the deleted agent's entry from the `agents` JSON-serialized string on **every** such node:

   ```json
   // Before (agent being deleted: ordId "customer.build:agent:approval:v1")
   "agents": "[{\"ordId\":\"customer.build:agent:invoice:v1\",\"name\":\"Invoice Agent\"},{\"ordId\":\"customer.build:agent:approval:v1\",\"name\":\"Approval Agent\"}]"

   // After
   "agents": "[{\"ordId\":\"customer.build:agent:invoice:v1\",\"name\":\"Invoice Agent\"}]"
   ```

3. **Check `agentName` references** — if any SAP Agent node has `agentName` pointing to the deleted agent (same `ordId`), that node must be removed or re-targeted. Do not leave a dangling `agentName` reference.

The agent's ORD ID for `agents` / `agentName` uses the `agent` resource type, **not** `apiResource`. Derive it by taking the `provides.apis[].ordId` from the agent's `asset.yaml` and replacing `apiResource` with `agent`:

```
customer.build:apiResource:<solution>.<asset>:v1  →  customer.build:agent:<solution>.<asset>:v1
```

### Best Practices

 **Required folder structure** — always use this layout:

1. **Do NOT add `container.env` to agent assets** - it causes schema validation errors on the platform. Set environment variables via `ENV` instructions in the Dockerfile instead. The `env` block is only valid for `base-ui` / `service` component definitions.
2. **Keep agent `asset.yaml` minimal** - omit `resources` and `hpa` blocks unless you have a specific reason to override platform defaults. Extra fields have caused schema validation failures on the platform.
3. **Include health probes** (use `/.well-known/agent.json` for A2A agents):

   ```yaml
   probes:
     startup:
       path: /.well-known/agent.json
       periodSeconds: 5
       timeoutSeconds: 3
       failureThreshold: 18
     liveness:
       path: /.well-known/agent.json
       initialDelaySeconds: 15
       periodSeconds: 10
       timeoutSeconds: 5
       failureThreshold: 3
     readiness:
       path: /.well-known/agent.json
       initialDelaySeconds: 5
       periodSeconds: 5
       timeoutSeconds: 3
       failureThreshold: 3
   ```
4. **Standard ports**:

- Python agents: 5000

## Important Notes

- For A2A agents, always use `/.well-known/agent.json` as the probe path (startup + liveness + readiness)