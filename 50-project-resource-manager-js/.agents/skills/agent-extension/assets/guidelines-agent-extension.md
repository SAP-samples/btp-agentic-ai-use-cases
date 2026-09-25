# Agent Extension Guidelines

Technical constraints and patterns for building an agent extension. Follow these throughout specification execution.

## Tech Stack

- Declarative YAML descriptors only (`extension.yaml`, `asset.yaml`) — no agent source code
- Generated via the `create-agent-extension` skill

## Key Constraints

- An extension **augments an already-deployed, extensible agent** — it MUST NOT modify the base agent's source code or make an agent extensible.
- Only declare capabilities the base agent actually supports (read the agent's extension capabilities: `instructionSupported`, `tools.additions.enabled`, `supportedHooks`). Never invent capabilities.
- The extension targets a specific base agent by `ordId` + `version`; `asset.yaml` `requires` MUST reference it.
- Tools are surfaced through MCP servers — the actual MCP tool discovery/wiring is handled at build time and is out of scope for this spec (do not consume APIs directly).
- Hooks are n8n workflows (`deploymentType: N8N`) that run BEFORE (pre-hook) or AFTER (post-hook) the agent. If a hook references an n8n workflow in the same solution, that workflow is a separate asset.

## Extension Structure

- One extension asset folder `assets/<asset-name>/` containing `extension.yaml` + `asset.yaml`
- `extension.yaml` `capabilityImplementations` may include `instruction`, `tools`, and/or `hooks` — only the sections the agent supports
- Validate both YAML files are well-formed after creation

## Integration with Other Assets

- If a hook uses an n8n workflow created in the same solution: create the n8n workflow asset first, then reference it by name in the hook config
- Keep the extension self-contained and independently deployable
