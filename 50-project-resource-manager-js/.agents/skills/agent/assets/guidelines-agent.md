# Agent Guidelines

Universal patterns and constraints for building Pro-Code AI Agents. Follow these throughout specification execution.

## Specialized Guidelines

This document provides universal agent patterns. For detailed guidance on specific topics, see:

For detailed guidance on specific topics, guidelines are split into specialized files for better maintainability:

| Source (Guidelines Files)         | Copied to                              | Purpose |
|------------------------------|----------------------------------------|---------|
| `./guidelines-agent-python.md`          | `specification/guidelines-agent-python.md`                | Python implementation details(Tech stack, project structure, decorators, testing, validation) |
| `./guidelines-agent-skills.md`          | `specification/guidelines-agent-skills.md`                | Runtime skills patterns(When and how to create task-specific skills) |
| `./guidelines-agent-mcp.md`             | `specification/guidelines-agent-mcp.md`                   | MCP integration patterns(MCP tool patterns, API discovery paths, mock configuration) | 

## Core Architecture

### Agent2Agent (A2A) Protocol

All agents implement the A2A protocol for inter-agent communication:
- Expose `/.well-known/agent.json` for agent discovery
- Support streaming responses
- Handle context management

### Execution Model

- Local execution only (in-memory storage, no deployment during development)
- Environment variables supplied at runtime (no `.env` files)
- AI Core available at runtime via LiteLLM

## Universal Constraints

These constraints apply to ALL agent implementations regardless of language:

### API Access

**NEVER call SAP APIs directly.** All SAP API consumption MUST go through MCP servers:
- No direct HTTP clients for SAP APIs
- No hand-rolled OData clients
- Agent consumes MCP tools, never raw HTTP calls

See [guidelines-agent-mcp.md](./guidelines-agent-mcp.md) for MCP integration patterns.

### Data Integrity

- Never fabricate, guess, or invent data
- Always use tools to retrieve live data
- Relay tool errors verbatim without embellishment

### Project Hygiene

- No Git operations during implementation
- No authentication setup
- No documentation/README generation
- Only use public APIs; mock private systems

## Business Instrumentation

ALL business logic steps MUST be instrumented:

1. **Structured Logging**: Each milestone emits log statements
   - Pattern: `[MILESTONE_ID].[achieved|missed]: [description]`
   - Example: `[M1.achieved]: Purchase order validated successfully`

2. **Telemetry Spans**: Each business step gets an OpenTelemetry span
   - Use milestones from PRD's "Milestones" section
   - If no PRD milestones, derive from project input

See language-specific guidelines for implementation details.

## Runtime Skills

Runtime skills provide task-specific instructions that don't belong in the system prompt:
- Multi-step workflows with decision trees
- Domain-specific constraints
- Reference material (templates, validation rules)

**When to create skills:** See [guidelines-agent-skills.md](./guidelines-agent-skills.md) for decision criteria and examples.

Skills are loaded on-demand via the `load(path)` tool — no extra wiring needed.

## Testing Requirements

- Coverage must be ≥ 70%
- Mock all external systems (AI Core, MCP servers, SAP APIs)
- Tests must run offline
- One unit test per tool
- One integration test for end-to-end flow

See language-specific guidelines for testing setup and execution.
