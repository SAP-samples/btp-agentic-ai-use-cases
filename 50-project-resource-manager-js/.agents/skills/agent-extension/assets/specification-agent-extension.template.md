# Specification: {{asset-name}}

> **Guidelines**: Read [guidelines.md](../guidelines.md) and [guidelines-agent-extension.md](../guidelines-agent-extension.md) before executing ANY tasks below. Follow all constraints described there throughout execution.

## Basic Setup

- [ ] Read the project input (`product-requirements-document.md`, `intent.md`, or the user prompt that triggered this specification)
- [ ] Confirm the base agent to extend (ordId + version) from the intent's Fit Gap Analysis / PRD

{{project-specific-tasks}}

- [ ] If `specification/{{asset-name}}/mcp-specs/` exists but `specification/{{asset-name}}/api-specs/` does not, create the missing API specs:
  - Read each Fit Gap Analysis row in `intent.md` that contains an MCP Server ORD ID
  - Extract the corresponding API ORD ID from the same row
  - Call `sap_knowledge_graph_api_discovery` to get the download link
  - Save each API spec to `specification/{{asset-name}}/api-specs/`
- [ ] If `specification/{{asset-name}}/api-specs/` exists, invoke `mcp-translation-file`
- [ ] Then invoke `setup-solution` to create and register MCP server assets in `assets/`
- [ ] Skip the previous two steps if `mcp-translation-file` is not available in this environment
- [ ] **Prerequisite check**: if the solution includes an n8n workflow, confirm `assets/workflows/<workflow-name>/<workflow-name>.n8n.json` and `assets/workflows/<workflow-name>/asset.yaml` exist before proceeding — `create-agent-extension` Step 4 reads them to wire hooks
- [ ] Invoke the `create-agent-extension` skill from `assets/{{asset-name}}/` to generate `extension.yaml` and `asset.yaml`, and populate tools from any MCP server assets already present in `assets/`
- [ ] Ensure `extension.yaml` only declares capabilities the base agent supports (instructions, tools, hooks — per the agent's extension capabilities)
- [ ] Validate `extension.yaml` and `asset.yaml` are well-formed and `asset.yaml` `requires` references the base agent (ordId + version)

## Final Validation

Confirm all files are present and correctly cross-referenced before marking this spec complete:

**MCP Server** (if API integration exists):
- [ ] `assets/<mcp-server>/asset.yaml` — `provides.apis[].ordId` matches entries in `extension.yaml` `tools[].ordId` and `asset.yaml` `requires`
- [ ] `assets/<mcp-server>/mcp-translation/translation.json` exists
- [ ] `assets/<mcp-server>/mcp-translation/.tool-list.json` exists
- [ ] `solution.yaml` `assets:` list includes `./assets/<mcp-server>/asset.yaml`

**n8n Workflow** (if hooks exist):
- [ ] `assets/workflows/<workflow-name>/<workflow-name>.n8n.json` exists and contains a node with `webhookId`
- [ ] For hooks with `deploymentType: N8N`, every `extension.yaml` `hooks[].n8nWorkflowConfig.ordId` matches a `provides.apis[]` entry with `kind: rest` in the referenced workflow's `asset.yaml`
- [ ] `assets/workflows/<workflow-name>/asset.yaml` `workflow.name` matches `asset.yaml` `requires` entry `name` with `type: n8n-workflow`
- [ ] `solution.yaml` `assets:` list includes `./assets/workflows/<workflow-name>/asset.yaml`

**Agent Extension**:
- [ ] `assets/{{asset-name}}/extension.yaml` — `tools[]` populated (non-empty if MCP assets exist), `hooks[]` populated (non-empty if n8n workflow exists)
- [ ] `assets/{{asset-name}}/asset.yaml` — `requires` has entries for: agent (`type: agent`), each MCP server (`type: mcp-server`), n8n workflow (`type: n8n-workflow`)
- [ ] `solution.yaml` `assets:` list includes `./assets/{{asset-name}}/asset.yaml`
