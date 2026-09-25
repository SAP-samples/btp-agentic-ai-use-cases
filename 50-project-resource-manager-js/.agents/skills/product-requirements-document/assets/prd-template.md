# Product Requirements Document (PRD)

**Title:** [Product Name]  
**Date:** {{CURRENT_DATE}}  
**Owner:** [Product Owner / Author]  
**Solution Category:** [AI Agent | BTP Extension | n8n Workflow]

## Product Purpose & Value Proposition

**Elevator Pitch:**  
[Explain in 30 seconds the problem this solution solves and why it matters.]

**Business Need:**  
[Describe the unmet business need. Explain why this solution is required.]

**Expected Value:**  
[State measurable business value. Specify which KPIs will improve and by how much.]

**Product Objectives (Prioritized):**
[What are the measurable goals? How will success be measured? Rank objectives (e.g., 1. ease of use, 2. retail price under $100, 3. compatibility)]
1. [Primary objective - e.g., "Reduce customer inquiry resolution time by 60%"]
2. [Secondary objective - e.g., "Achieve 90% accuracy on intent classification"]
3. [Tertiary objective - e.g., "Handle 10,000 queries per day autonomously"]

## Business Metrics [skip for fast track mode, EXCEPT for AI Agent solutions]

Measurable business goals the solution must achieve. Each row MUST have **Metric**, **Target**, and **Process / Capability**. Use `—` for unknown **Baseline** or **Timeline**. **Source** is one of `user` or `agent-derived`.

| Metric | Baseline | Target | Timeline | Process / Capability | Source |
|--------|----------|--------|----------|----------------------|--------|
| [e.g., AP exception rate] | [e.g., 4.6%] | [e.g., 2.0%] | [e.g., Q4] | [e.g., Invoice to Pay] | [user \| agent-derived] |

**Notes:** [optional free-text context that does not fit the table]

## User Profiles & Personas [skip for fast track mode]
[Create realistic, detailed personas for key user types. Include demographics, environment, technical proficiency, goals, pain points. Focus on 2-4 primary profiles; trying to please everyone pleases no one]

### Primary Persona: [Name/Role]

[Write a realistic persona. Include age, role, daily tasks, environment, frustrations, technical comfort, and success measures. Make this person real—specific details matter more than generic descriptions.]

> **Example:** Sarah the Customer Service Agent is a 29-year-old support specialist handling 40-60 customer inquiries daily via chat and email. She spends 20 minutes per inquiry searching through documentation, past tickets, and product specs. She's frustrated by repetitive questions and wishes she had instant access to accurate answers. She's comfortable with technology but skeptical of AI after a previous chatbot implementation that gave wrong answers. She needs tools that make her more efficient, not replace her.

### Secondary Persona: [Name/Role]

[Write another realistic persona.]

### Other User Types

- [List additional stakeholders briefly: approvers, compliance officers, administrators.]

## User Goals & Tasks [skip for fast track mode]

[Identify what each persona needs to accomplish (goals), design tasks that help users accomplish their goals, features should support tasks that map to goals, eliminate any functionality that doesn't serve high-priority goals]

### For [Primary Persona Name]:

**Goals:**

- [State what this user must accomplish. Focus on outcomes, not features.]
- [Example: "Respond to customer inquiries with accurate information in under 2 minutes"]

**Key Tasks:**

- [List the essential tasks this user performs to reach their goals.]
- [Each task should directly support a stated goal.]

### For [Secondary Persona Name]:

**Goals:**

- [State this user's goals.]

**Key Tasks:**

- [List this user's essential tasks.]

## Product Principles [skip for fast track mode]

[Define 3-7 principles that drive decision-making throughout the project. Make principles specific to your product (e.g., TiVo: "It's entertainment, stupid", "Everything is smooth and gentle")]

1. **[Principle Name]**: [Explain briefly how this guides decisions.]
2. **[Principle Name]**: [Explain briefly how this guides decisions.]
3. **[Principle Name]**: [Explain briefly how this guides decisions.]

**Examples:**

- "Human-in-the-loop: AI proposes, humans approve high-risk actions"
- "Mobile-first: All core functions work on mobile devices"
- "Process harmonization: Align to SAP best practices, not legacy processes"

## Business Context [skip for fast track mode]

**Current State:**  
[Describe current processes, applications and key pain points. Explain why the current approach fails.]

**Strategic Alignment:**  
[Explain how this supports corporate strategy]

**Success Criteria:**  
See the Business Metrics section above for the measurable, user-confirmed success targets.

## Goals and Non-Goals [skip for fast track mode]

### Goals (In Scope)

- [State specific, measurable outcomes will be achieved.]
- [Make each outcome testable and concrete.]
- [Fewer, well-executed goals beat many mediocre ones.]

### Non-Goals (Out of Scope)

- [State explicitly what the solution will NOT do.]
- [Prevent scope creep. Manage expectations early.]

## Requirements

[State requirements at the interaction design and use case level. Be clear about WHAT each feature is and the desired user experience. Leave maximum flexibility for the engineering team on HOW. Map requirements to objectives (requirements traceability)]

### Must-Have Requirements

[Product should NOT ship without these. Map directly to core value proposition. Rank-order ruthlessly—sequence determines implementation priority.]

**[Requirement ID]**: [Requirement Name]

- **Problem to Solve**: [State the user problem. Do NOT describe the solution.]
- **User Story**: As a [persona], I need [capability] so that [business outcome]
- **Acceptance Criteria**:
  - Given [precondition], when [action], then [expected result]
- **Maps to Objective**: [Which product objective does this support?]
- **Priority Rank**: [1, 2, 3... Rank within this category. 1 = highest priority.]

[Repeat for each must-have requirement]

### High-Want Requirements [skip for fast track mode]

[Important but NOT ship-blockers. Include these only if they don't delay release. Rank-order within this category.]

**[Requirement ID]**: [Requirement Name]

- **Problem to Solve**: [State the problem, not the solution.]
- **User Story**: As a [persona], I need [capability] so that [business outcome]
- **Priority Rank**: [1, 2, 3...]

### Nice-to-Have Requirements [skip for fast track mode]

[Useful for planning future releases and architecture decisions. Rank-order for planning next releases.]

**[Requirement ID]**: [Requirement Name]

- **Problem to Solve**: [State the problem.]
- **Priority Rank**: [1, 2, 3...]

## Non-Functional Requirements [skip for fast track mode]

### Performance

- **Latency**: [Target response time, e.g., "95th percentile <3 seconds"]
- **Throughput**: [Expected query volume, e.g., "500 queries per hour"]

### Reliability

- **Availability**: [Uptime target]
- **Fallback**: [Behavior when service degrades]

### Cost

- **Budget Controls**: [Cost limits per tenant/user]
- **Optimization**: [Caching, batching strategies]

### Explainability

- **Traceability**: [How outputs or decisions can be traced back to their inputs or sources]
- **Decision Logging**: [What gets logged for auditability]
- **Uncertainty Communication**: [How the system signals low confidence or incomplete results to users]

## Solution Architecture [skip for fast track mode]

[Describe the high-level architecture. Include only components actually required by this solution. Add a Mermaid diagram if it aids clarity. Omit sub-sections that are not relevant.]

**Architecture Overview:**  
[Brief description of how the solution is structured and deployed.]

**Key Components:**

- [Component 1: name and purpose]
- [Component 2: name and purpose]
- [Component 3: name and purpose]

**Integration Points:**

- [System 1: integration purpose, data flow direction, frequency]
- [System 2: integration details]

**Deployment Environments:**

- [Dev / QA / Prod: purpose and data isolation approach per environment]

### Agent Extensibility & Instrumentation [AI Agent solution type only - REQUIRED even in fast track mode]

**IMPORTANT: When the solution type is "AI Agent", ensure the PRD includes the following (even in fast-track mode):**

**Agent Extensibility:**
- The agent should be designed to support extensibility through extension points
- Document which capabilities should be extensible and by whom

**Business Step Instrumentation:**
- All business logic steps must be properly instrumented with log statements
- Each significant business step should emit structured logs for observability
- Use the Milestones section (below) to define key business steps with their corresponding log statements
- Ensure log statements follow the pattern: `[MILESTONE_ID].[achieved|missed]: [description]`
- Note: Proper instrumentation enables monitoring and debugging of agent behavior in production

### Automation & Agent Behaviour

[Describe the degree of automation the solution introduces — from simple workflow automation through to autonomous AI agents. Fill only what applies; omit sub-items that are not relevant.]

**Automation Level:** [Rule-based / ML-assisted / Autonomous agent / Hybrid]

**Actions the system performs without human approval:**

- [Action 1]

**Actions that require human review or approval:**

- [Action 1]

**Model or engine used:** [e.g., "GPT-4o via SAP Generative AI Hub", "SAP Build Process Automation", "custom rule engine"]

**Knowledge & data sources accessed:**

- [Source: name, purpose, data stewardship]

> **If data products were identified** (i.e., the Fit Gap Analysis in `intent.md` contains a Data Product ORD ID column) **AND** the `data-product-generation` skill exists (check `skills/data-product-generation/SKILL.md`): add a **Data Products referenced** table here with columns: Business Name | Data Product ORD ID | Source System | Purpose. Populate one row per discovered data product. If no data products were found OR the data-product-generation skill is not available, omit this table.

**Tools or connectors invoked:**

- [Tool/connector name: purpose and side effects (read-only / write / high-risk)]

> **If the solution includes both an AI Agent and an n8n workflow that the agent should invoke**: document the invocation as an MCP tool call, not a direct webhook or HTTP call. Use the form: "`<workflow-name>` workflow (via `<tool-name>` MCP tool): [purpose — e.g., triggers the leave-request submission workflow]". The direct webhook URL must never be called by the agent.

**Guardrails & fail-safes:**

- [Prohibited action or constraint: e.g., "Never modify financial records autonomously"]
- [Escalation trigger: e.g., "Confidence below threshold routes to human"]
- [Fallback behaviour when the automation fails]

### Configuration & Data

[Cover any configuration, organisational data, master data, or migration work required. Omit sub-items that are not relevant to this solution.]

**Configuration Scope:**  
[High-level description of system or application configuration required.]

**Organisational & Master Data:**

- [Organisational structures to create or change: e.g., company codes, plants, cost centres]
- [Master data types to create or update, and their ownership]

**Data Migration & Cutover:**

- [Data in scope: master data and open transactions to migrate]
- [Data quality rules, cleansing ownership, and sign-off requirements]
- [Cutover plan: freeze windows, go-live sequence, rollback strategy]

## Governance, Risk & Compliance [skip for fast track mode]

**Data Handling:**

- [Data residency requirements]
- [PII/sensitive data handling and masking rules]
- [Data retention and deletion policies]

**Compliance Frameworks:**

- [Applicable regulations: GDPR, industry-specific requirements]
- [Internal policies and controls]

**Approval Flows:**

- [Who must approve high-risk actions and what evidence is required]

## Release Criteria [skip for fast track mode]

[Define minimum acceptable quality bars before go-live.]

- **Performance**: [Specific latency/throughput criteria]
- **Reliability**: [Availability and fallback validation]
- **Security**: [Security validation requirements]
- **Usability**: [How usability will be measured and the minimum bar]
- **Documentation**: [What documentation must be complete]
- **Monitoring**: [Observability dashboards and alerting operational]

## Schedule & Timeline Context [skip for fast track mode]

**Target Timeline:** [State time window. Provide context, not just a date.]

**Business Drivers:**  
[Explain why timing matters. State what drives the schedule:]

- [Driver 1: e.g., "Customer support costs will exceed budget in Q3"]
- [Driver 2: e.g., "Competitors are launching AI-enabled alternatives"]

**Key Milestones:** See the Milestones section for the full structured definition.

## Milestones [skip for fast track mode, EXCEPT for AI Agent solutions]

**Note:** For AI Agent solutions, milestones are REQUIRED even in fast-track mode to ensure proper business step instrumentation and observability.

### [M1]: [Milestone Name]

- **Description**: [What this milestone represents]
- **Achieved when**: [Condition or event that marks this milestone as complete]
- **Log on achievement**: [Log message to emit, e.g., "M1.achieved: intent classified successfully"]
- **Log on miss**: [Log message to emit when skipped or failed, e.g., "M1.missed: intent classification did not complete"]

[Repeat for each milestone]

## Risks, Assumptions, and Dependencies [skip for fast track mode]

### Risks

- [Risk 1: Describe the risk and its potential impact.]
- [Risk 2: e.g., "AI accuracy might not reach 90% on edge cases"]

### Assumptions (Validate These)

- [Assumption 1: State clearly what you haven't verified.]
- [Assumption 2: e.g., "Knowledge base content is accurate and current"]

### Dependencies

- [Dependency 1: State what external factors this relies on.]
- [Dependency 2: e.g., "CRM system API integration"]

## Open Questions [skip for fast track mode]

- [Question 1: Important question needing clarification]
- [Question 2: Another open question]
- [Question 3: Additional question]

## Appendix [skip for fast track mode] 

### Glossary [skip for fast track mode]

[Define solution-specific terms]

### References 

[Links to relevant documentation, SAP product pages, compliance frameworks]
