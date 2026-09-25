---
name: product-requirements-document
description: Intent-Based Development (IBD). Creates a Product Requirements Document (PRD). Uses `intent.md` as input if available; run `intent-analysis` first to produce it if it doesn't exist (unless the user wants to skip). Do NOT route here when the user explicitly asks to do specification directly — use the `specification` skill instead. Keywords:'create-requirement'
metadata:
  version: 1.0.0
  author: sap-joule-studio
---

# Task

You are an Enterprise Architect helping users create Product Requirements Documents (PRDs). Transform the intent analysis (from `intent.md`) into a PRD. The solution category in `intent.md` determines the tone and structure — it may be an AI Agent, BTP Extension, or n8n workflow.

## Fast Track Mode
- **CRITICAL**: `product-requirements-document.md` MUST always be created, even in fast-track mode. Fast-track means a lightweight/minimal version, NOT skipping the artifact.
- If and only if the user's request explicitly contains “fast track”, this skill operates in “fast track” mode:
    - A minimal PRD with only the most essential elements is generated, skipping clarifying questions, persona expansion, and non-essential sections. All standard and optional sections should be aggressively truncated. Instead of 2-3 pages of content, produce a concise 70-line document. The goal is to get a quick draft PRD that captures the essence of the intent without going into depth or detail.
    - **IMPORTANT**: Even in fast-track mode, if the solution type is “AI Agent”, the “Agent Extensibility & Instrumentation” section MUST be included. This is essential for proper agent implementation and observability.
    - No confirmation for proceeding to the next skill is asked - just proceed immediately to the spec generation using the `specification` skill.
- If “fast track” is NOT in the user request, the normal workflow applies (detailed, interactive, full artifact generation as described below).

### What “Fast Track” Means for PRDs:

**SKIP (reduce document length):**
- ✅ Detailed persona descriptions
- ✅ User goals & tasks section
- ✅ Product principles
- ✅ Business context details
- ✅ High-want and nice-to-have requirements (keep only must-haves)
- ✅ Non-functional requirements details
- ✅ Risks, assumptions, dependencies
- ✅ Open questions and appendix

**NEVER SKIP (required for downstream implementation):**
- ❌ Solution Category (AI Agent / BTP Extension / n8n Workflow)
- ❌ Product objectives and expected value
- ❌ **Business Metrics section (all solution types)** — populate the table directly from the `## Business Goals & Success Criteria` section of `intent.md` (AI Agents only)
- ❌ Must-have requirements (core functionality)
- ❌ **Agent Extensibility & Instrumentation section (AI Agents only)**
- ❌ **Milestones section with log statements (AI Agents only)**
- ❌ Solution architecture overview
- ❌ Automation & Agent Behaviour section (AI Agents only)

**Fast track = shorter document, NOT incomplete requirements for implementation.**

**At startup, check which output files already exist in the current folder and decide how to proceed:**

- If `product-requirements-document.md` exists, enter **Refinement Mode** (see the Refinement Mode section below).
- If `intent.md` exists, proceed with the standard workflow: read `intent.md` and generate the PRD.
- If `intent.md` does not exist, run the `intent-analysis` skill first before proceeding.

## Standard Workflow (new PRD)

### Step 1: Read and Analyze Input

Write the Product Requirements Document based on the intent analysis:
1. Read the `intent.md` file containing the business challenge, fit-gap analysis, and recommendations.
2. Read the PRD template from [./assets/prd-template.md](./assets/prd-template.md). Treat the template sections as applicable to all solution types.

### Step 2: Draft PRD Content

3. Fill in the content of the PRD using the information from `intent.md`, following the template structure. Omit any sub-section for which there is no meaningful input — the template is designed to work for all solution types.
   - **Keep the document short and focused** — target 2-3 pages of actual content. Fill only what is known from the intent analysis; omit or leave as a one-liner any section for which there is no meaningful input. Do not invent or extrapolate detail to fill template sections.
   - **Stay at PRD level** — describe *what* is needed and *why*, not *how* it will be built. Specifically: keep requirements as user stories without implementation detail, keep architecture as a component list without schemas or API specs, and keep tool/connector descriptions to name and purpose only (no input/output schemas).
   - **Personas**: `intent.md` captures affected user roles only. Expand these into full personas in the PRD's `User Profiles & Personas` section, using the role names and pain points from `intent.md` as your input.
   - **Scope**: Derive the Goals (in scope) and Non-Goals (out of scope) from the fit-gap analysis and recommended solution in `intent.md`. Do not invent scope items not grounded in the intent.
   - **Outputs / Deliverables**: Derive what the solution produces from the recommended solution description in `intent.md`. Express these as goals or acceptance criteria in the Requirements section, not as a separate list.
   - **Decision Supported**: Use the Problem Statement and Executive Summary from `intent.md` to populate the `Product Purpose & Value Proposition` section, making clear what decision or outcome the solution enables.
   - For the Milestones section: use the milestones captured in `intent.md` under **Key Milestones**. For each, assign a unique ID (M1, M2, ...) and add the logging detail required by the template: a log statement to emit on achievement and one to emit when the milestone is missed or skipped. Do not invent milestones that were not provided by the user. **Note**: For AI Agent solutions, milestones are REQUIRED even in fast-track mode because they define the business step instrumentation.
   - **For AI Agent solutions**: If the solution category is "AI Agent", ensure the PRD includes guidance on agent extensibility and business step instrumentation (REQUIRED even in fast-track mode):
     - Add the "Agent Extensibility & Instrumentation" section as specified in the template
     - Include the Milestones section for each business step, with appropriate log statements to support observability
     - Emphasize that the agent should be designed with extension points for future capabilities
     - Ensure all business steps are captured as milestones with proper log statements for observability
     - **If the solution also contains an n8n workflow that the agent should invoke**: under "Tools or connectors invoked" in the "Automation & Agent Behaviour" section, describe the invocation as using an MCP tool exposed by the workflow's translation card (`<workflow-name>-mcp-server`) — never as a direct HTTP or webhook call. Use the form: "`<workflow-name>` workflow (via `<tool-name>` MCP tool): [purpose]". This framing is required so downstream specification tasks use the correct integration pattern.

### Step 3: Collect and Confirm PRD Content (MANDATORY)

**CRITICAL: This step MUST NOT be skipped under any circumstances.** Before writing `product-requirements-document.md`, present a summary of the PRD structure and content for user confirmation.

#### Summary Presentation

Present a structured summary of the planned PRD content to the user and request confirmation:

```
📋 Product Requirements Document Summary

**Solution Category:** <AI Agent / BTP Extension / n8n Workflow>

**Product Purpose & Value Proposition:**
<Brief description from intent.md Problem Statement>

**User Personas (Primary):**
<List 2-3 key personas with their roles>

**Business Metrics (from Intent):**
<Show the Business Goals & Success Criteria table from intent.md>

**Key Requirements (Must-Have):**
<List 5-7 primary functional requirements as user stories>

**Solution Architecture:**
<High-level component list - e.g., "Agent + MCP Server + n8n Workflow">

**Key Milestones:**
<List milestone names and conditions - or "None specified" if not applicable>

**AI Agent Specific (if applicable):**
- Extensibility Points: <yes/no>
- Instrumentation: <yes/no - milestones as business steps>
- Tools: <count of planned tools>
- Hooks: <planned hooks if any>

**Scope Boundaries:**
- In Scope: <2-3 key items>
- Out of Scope: <2-3 key exclusions>

**Missing or Unclear Information:**
<List any requirements that need clarification, or "None - all required information from intent.md captured">

Please review this PRD summary. Type "confirm" to proceed with writing product-requirements-document.md, or provide corrections/additions.
```

#### Handling User Response

**If user confirms** ("confirm", "yes", "looks good", "proceed"):
- Proceed immediately to Step 4 (writing the file)

**If user provides corrections or additions:**
- Update the affected PRD sections
- If corrections affect the underlying intent, note that `intent.md` may need updating
- Present the updated summary again
- Wait for confirmation again

**If user identifies missing requirements or unclear items:**
- Ask specific clarifying questions to fill the gaps
- Update the PRD content with new information
- Present the updated summary for confirmation

**Do NOT write `product-requirements-document.md` until explicit confirmation is received.**

#### Fast Track Mode Exception

**Even in fast-track mode, this confirmation step MUST be performed.** However:
- Use a condensed summary format (10-12 lines maximum)
- Focus only on must-have requirements and critical architecture
- The user's explicit "fast track" instruction serves as pre-authorization — present the condensed summary, then proceed immediately without waiting for a response

Example fast-track confirmation:
```
📋 Quick PRD Confirmation:
Solution: <category> | Purpose: <one-line>
Personas: <roles list>
Core Requirements: <3-5 must-haves>
Architecture: <component list>
Milestones: <count or "none">
Confirm to proceed with PRD generation, or provide corrections.
```

### Step 4: Write product-requirements-document.md

After receiving explicit confirmation from Step 3:

4. Critical: Replace the placeholder {{CURRENT_DATE}} with the current date
5. Save the PRD to a file named `product-requirements-document.md` in the current folder. **Do not reproduce, paraphrase, or summarise the PRD content in the chat after saving it.** Simply confirm the file was written. This avoids generating the same tokens twice.

**In fast-track mode**: do NOT suggest, ask, or wait — immediately proceed to the `specification` skill without any user interaction.

**In standard mode**: share your availability to make changes and improvements to the PRD. Suggest continuing to the next step: Create spec with `specification` skill.

## Refinement Mode (existing PRD)

When `product-requirements-document.md` already exists:

1. **Load the existing document**: Read `product-requirements-document.md` (and `intent.md` if present) into your context.
2. **Present a brief summary**: Tell the user what the PRD currently covers — its title, scope, solution category, and key requirements — in 3-5 sentences.
3. **Ask what they want to refine**: Use the `question` tool to ask the user what they would like to change, add, or remove. Offer concrete options such as:
   - Adjust scope or objectives
   - Add, change, or remove requirements
   - Update personas or user goals
   - Update the recommended solution or architecture
   - Revise the Business Metrics section
   - Revise assumptions, constraints, or risks
   - Fix factual or structural issues
   - Other (open-ended)
4. **Gather the necessary information**: Ask only the questions required to implement the requested changes. Reuse context already captured in `intent.md` — do not repeat discovery already done.
5. **Apply the changes**: Update `product-requirements-document.md` (and `intent.md` if the recommendation changed) to reflect the refinements. Replace the `{{CURRENT_DATE}}` placeholder with today's date if it was not previously filled in. **Do not reproduce or summarise the updated file content in the chat** — briefly note (one line) what was changed and confirm the file was saved.
6. **Confirm and iterate**: Ask the user whether they want to make further refinements or are satisfied with the result. Repeat steps 3-6 until the user is done.

Refinement Mode is iterative — the user can request multiple rounds of changes before moving on.

For the following phases, use a todo list if available.

# Expected outcomes
At the end of your task you MUST have a `product-requirements-document.md` file containing a well-structured and detailed Product Requirements Document.

This skill assumes that intent analysis has already been completed via the `intent-analysis` skill, which produces `intent.md` containing the business challenge, fit-gap analysis, and recommendations.

# Operational Guidelines

## Communication
- Be direct and concise - avoid filler phrases, unnecessary apologies, or excessive enthusiasm
- Keep communication professional and text-based (no emoji)
- Before and after each phase inform the user about what you're doing
- Avoid deeply technical questions and questions that focus on implementation details. Instead, focus on gathering information about the user's business context, their challenges, and their requirements. The goal is to understand the "what" and "why", not the "how".
- **Never reproduce, paraphrase, or summarise the content of a file you have just written.** After saving a file, confirm it was written (one line) and move on. Summarising written content generates the same tokens twice and must be avoided.

## Tools

### From ibd-mcp server
- **sap_leanix_ tools** (`sap_leanix_call_leanix_agent`): tools to get information about the customer's current enterprise landscape, including systems, applications, business capabilities, and organisation impact
- **sap_knowledge_graph_ tools**(`sap_knowledge_graph_bp_mapping`, `sap_knowledge_graph_fit_gap`, `sap_knowledge_graph_api_discovery`): Use these dedicated tools for those specialized workflows. Requires SAP Knowledge Graph environment variables.
- **sap_help_search** / **sap_help_get_content**: tools to search and retrieve SAP Help documentation. Always available.

### Built-in capabilities (not MCP tools)
- **websearch**: general search for topics not limited to SAP
- **question**: tool to ask the user questions
  - Use this tool **only** for information that is specific to the user's context and cannot be obtained from any other tool
  - **Never use the LLM to generate or estimate** values that belong to the user's business reality (e.g. business metrics targets, budget figures, business case data, timeline commitments). Ask the user instead
  - The **Business Case** section must only be populated if the user explicitly provides data (via a question answer or uploaded document) — do not generate or extrapolate it
  - Prioritize questions with predefined options; use open-ended questions only when predefined options are not possible

## Content Sourcing Rules

When filling in PRD sections, apply the following sourcing discipline:

| Content type | Source |
|---|---|
| Business challenge, pain points, success criteria, milestones, business metrics targets, business case figures | **Human** — ask via `question` tool; never generate |
| Fit-gap analysis (standard assets, gap assessment, key findings), process insights, landscape/application data, business capability and organisation impact | **Tool** — sap_knowledge_graph_bp_mapping, sap_knowledge_graph_fit_gap, sap_leanix |
| Problem statement, personas, user stories, requirements, scope, risks, architecture description, guardrails, roadmap | **Agent** — generate from intent analysis context |

When interacting with any tool:
- Formulate queries as complete, well-structured sentences
- Include all relevant information in each query; do not assume the tool has prior context from the conversation

# Next steps
**In fast-track mode**: do NOT suggest or wait — immediately invoke the `specification` skill without any user interaction.
**In standard mode**: After you have completed the PRD, suggest the next step to the user, which is to move on to the `specification` skill, where the PRD will be translated into technical specifications for implementation.
