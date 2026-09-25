# Specification: {{asset-name}}

> **Guidelines**: Read [guidelines-n8n-workflow.md](../guidelines-n8n-workflow.md) before executing ANY tasks below. Follow all constraints described there throughout execution.

## Basic Setup

- [ ] Read the project input (`product-requirements-document.md`, `intent.md`, or the user prompt that triggered this specification)

{{project-specific-tasks}}

- [ ] Run the `setup-solution` skill first to create `solution.yaml` (if not already done)
- [ ] Write each workflow JSON file to its own `assets/workflows/<workflow-name>/` folder using the `n8n-workflow` skill
- [ ] Ensure `connections` in JSON reference nodes by `name`, not `id`
- [ ] Validate all workflow JSON files are well-formed
- [ ] **If the solution contains an agent that should invoke this workflow via MCP**: complete the MANDATORY-when-applicable section in `skills/n8n-workflow/references/execution.md` (Steps A–F) — create the mcp-server translation card, update `solution.yaml`, and add a `requires` entry plus system prompt instruction to every agent asset that should call this workflow. This task must be ticked regardless of which skill (agent or n8n) ran first.
