# Product Requirements Document (PRD)

**Title:** Project Resource Management AI Agent **Date:** 2026-09-23 **Owner:** Project / Resource Management Team **Solution Category:** AI Agent

* * *

## Product Purpose & Value Proposition

**Elevator Pitch:** Project managers and resource managers today spend up to 3 days manually searching for the right person to fill a resource gap — crossing between SAP S/4HANA Cloud for project data and SAP SuccessFactors for people data. Critically, employee time-off and leave data is not considered, leading to assignments of employees who are partially or fully unavailable. This AI Agent automates the entire staffing workflow: it queries active projects, finds open demands, retrieves employee availability, skills, and time-off records, filters out employees with leave conflicts, ranks the best-fit fully-available candidates with justification, and — once a manager confirms — executes the assignment directly in S/4HANA Cloud.

**Business Need:** Resource capacity gaps on projects are resolved manually today, requiring project managers to query multiple systems, compare data manually, and coordinate via email or meetings. Employee time-off data is not factored into the process, resulting in candidates being assigned who have approved leave during the project timeline. This is slow, error-prone, and creates project delivery risk. A unified AI Agent that orchestrates these steps — including time-off conflict detection — conversationally and intelligently is required.

**Expected Value:** Reduce average time-to-fill a resource gap from 3 days to same day, freeing project managers from system navigation and enabling faster project execution.

**Product Objectives (Prioritized):**

1.  Reduce time-to-fill a resource gap from 3 days to same day (< 1 day)
    
2.  Ensure all resource assignments are executed only after explicit manager confirmation (human-in-the-loop)
    
3.  Deliver accurate, justified candidate recommendations based on real-time availability, skills data, and time-off records — recommending only employees who are fully available during the project timeline
    

* * *

## Business Metrics

| Metric | Baseline | Target | Timeline | Process / Capability | Source |
| --- | --- | --- | --- | --- | --- |
| Time to fill a resource gap | 3 days | Same day (< 1 day) | — | Project Resource Staffing | user |

* * *

## User Profiles & Personas

### Primary Persona: Alex — Project Manager

Alex is a 38-year-old project manager responsible for delivering 3–5 concurrent customer-facing and internal projects. Each week, Alex encounters resource gaps when team members are unavailable or a new skill is suddenly required. Resolving a gap today means logging into S/4HANA Cloud to check project demands, then switching to SuccessFactors to browse employee profiles and availability — a process that takes 2–3 hours per gap and often stretches to 3 days due to back-and-forth communication. Alex is technically proficient but frustrated by system fragmentation. Success means quickly finding the right person and confirming the assignment without manual data wrangling.

**Goals:**

-   Identify and fill resource gaps on active projects the same day they arise
    
-   Have confidence that the candidate proposed is the right fit, with clear reasoning
    

**Key Tasks:**

-   Review active projects and their open resource requirements
    
-   Query employee availability for a given timeframe and skill set
    
-   Review ranked candidate recommendations and their justifications
    
-   Confirm a candidate to trigger the assignment
    

### Secondary Persona: Jordan — Resource Manager

Jordan is a 44-year-old resource manager who owns the workforce pool across multiple project teams. Jordan's role is to ensure optimal utilisation of the workforce — avoiding both overallocation and idle time. Today, Jordan spends significant time fielding ad-hoc staffing requests from project managers and manually resolving conflicts. Jordan needs visibility into the full picture of availability and demand, and wants to approve assignments before they are locked in.

**Goals:**

-   Maintain an accurate view of workforce utilisation and availability
    
-   Approve staffing decisions with confidence before assignments are executed
    

**Key Tasks:**

-   Review AI-proposed candidate recommendations
    
-   Confirm or reject a proposed resource assignment
    
-   Monitor resource allocation across active projects
    

* * *

## User Goals & Tasks

### For Alex (Project Manager):

**Goals:**

-   Resolve resource capacity gaps on the same day they are identified
    
-   Receive ranked, justified candidate recommendations without manual data lookups
    
-   Confirm assignment transactions.
    

**Key Tasks:**

-   Ask the agent to list active projects
    
-   Ask the agent to show open resource requirements for a selected project
    
-   Ask the agent to find available candidates with the required skills
    
-   Review the ranked recommendation list and select a candidate
    
-   Confirm the assignment through the agent's human-in-the-loop prompt
    

### For Jordan (Resource Manager):

**Goals:**

-   Ensure no assignment is executed without explicit approval
    
-   Maintain accurate workforce allocation records in S/4HANA Cloud
    

**Key Tasks:**

-   Review agent-proposed candidates and justifications
    
-   Confirm or reject the assignment recommendation
    
-   Monitor that the assignment was correctly recorded in S/4HANA Cloud
    

* * *

## Product Principles

1.  **Human in the Loop**: No resource assignment is executed without explicit confirmation from a project manager or resource manager. The agent always proposes; humans always approve.
    
2.  **Data Before Reasoning**: All candidate matching is grounded in real-time SAP data. The agent never invents availability or skills — it reads them from S/4HANA Cloud and SuccessFactors.
    
3.  **Justify Every Recommendation**: Every candidate proposed must include a clear, readable justification explaining why they are a good fit (skills match, availability window, project history).
    
4.  **Single Source of Truth**: Project and resource data is read directly from the authoritative SAP systems. No caching or replicated data stores are used for decision-making.
    
5.  **Graceful Degradation**: If data from one system is unavailable or incomplete, the agent communicates this clearly and continues with partial data rather than failing silently.
    

* * *

## Business Context

**Current State:** Project managers manually log into SAP S/4HANA Cloud to view active projects and open resource demands, then separately navigate SAP SuccessFactors to check employee skills and availability. Matching is done manually in spreadsheets or via email. This process averages 3 days per gap and is highly dependent on individual knowledge of who is available and skilled.

**Strategic Alignment:** This solution supports the organisation's goal of improving project delivery speed and workforce utilisation efficiency. It aligns with the Lead to Cash for Project Based Services end-to-end process — specifically the "Initiate Projects" sub-process within Order to Fulfill.

**Success Criteria:** See the Business Metrics section for measurable, user-confirmed success targets.

* * *

## Goals and Non-Goals

### Goals (In Scope)

-   Track and list active projects from SAP S/4HANA Cloud
    
-   Query open resource requirements (demands) per project
    
-   Retrieve employee availability (daily/weekly) from SAP S/4HANA Cloud
    
-   Retrieve employee skills and profiles from SAP SuccessFactors
    
-   Apply AI reasoning to cross-reference demand and supply and rank best-fit candidates
    
-   Present ranked candidate recommendations with written justification
    
-   Implement human-in-the-loop confirmation before any assignment is made
    
-   Execute confirmed resource assignment write-back to SAP S/4HANA Cloud
    

### Non-Goals (Out of Scope)

-   Writing resource data back to SAP SuccessFactors
    
-   Financial or cost planning for projects
    
-   Project schedule or timeline management
    
-   Employee onboarding or offboarding workflows
    
-   Real-time calendar synchronisation or meeting scheduling
    
-   Cross-tenant or multi-system load balancing of resources
    

* * *

## Requirements

### Must-Have Requirements

**REQ-01: List Active Projects**

-   **Problem to Solve**: Project managers have no quick way to get an overview of their active projects without navigating S/4HANA Cloud manually.
    
-   **User Story**: As a project manager, I need to ask the agent to list my active projects so that I have an immediate overview of where resource gaps may exist.
    
-   **Acceptance Criteria**:
    
    -   Given the agent is running, when I ask "show me my active projects", then the agent returns a list of active projects with project ID, name, and status from SAP S/4HANA Cloud.
        
-   **Maps to Objective**: Objective 1 — reduce time-to-fill
    
-   **Priority Rank**: 1
    

**REQ-02: Retrieve Open Resource Requirements**

-   **Problem to Solve**: Identifying which projects have open resource demands requires manual navigation in S/4HANA Cloud.
    
-   **User Story**: As a project manager, I need the agent to query open resource requirements for a selected project so that I can immediately see what skills and capacity are needed.
    
-   **Acceptance Criteria**:
    
    -   Given an active project is identified, when I ask the agent to show resource requirements, then the agent returns open demands including required role, skill, and required dates from the Project Demand API.
        
-   **Maps to Objective**: Objective 1
    
-   **Priority Rank**: 2
    

**REQ-03: Check Employee Availability**

-   **Problem to Solve**: Checking whether a specific employee or pool of employees is available for a given time window requires manual lookup in S/4HANA Cloud.
    
-   **User Story**: As a project manager, I need the agent to retrieve employee availability for a given time period so that I can identify who is free to take on additional work.
    
-   **Acceptance Criteria**:
    
    -   Given a time window is specified, when the agent queries availability, then it returns employee names, available capacity (hours/days), and location from the Workforce Daily Availability API.
        
-   **Maps to Objective**: Objective 1
    
-   **Priority Rank**: 3
    

**REQ-03a: Check Employee Time-Off / Leave Data**

-   **Problem to Solve**: Employee time-off and leave records reside in SAP SuccessFactors and are not considered when checking availability, leading to recommendations of employees who have approved leave during the project timeline.
    
-   **User Story**: As a project manager, I need the agent to retrieve employee time-off records from SuccessFactors and filter out employees with leave conflicts during the project's required dates so that only truly available candidates are recommended.
    
-   **Acceptance Criteria**:
    
    -   Given a project's required date range, when the agent queries SuccessFactors Time Off API, then it returns approved time-off records (leave type, start date, end date, duration) for each candidate.
        
    -   Given a candidate has approved time-off overlapping with the project timeline, when the agent performs matching, then that candidate is excluded from the recommendation list or flagged as partially unavailable with the conflict dates shown.
        
-   **Maps to Objective**: Objective 3
    
-   **Priority Rank**: 4
    

**REQ-04: Retrieve Employee Skills and Profiles**

-   **Problem to Solve**: Skills data is in SuccessFactors and not visible alongside availability data, forcing manual cross-referencing.
    
-   **User Story**: As a project manager, I need the agent to retrieve the skills and profile of available employees from SuccessFactors so that I can assess their fit for a resource requirement.
    
-   **Acceptance Criteria**:
    
    -   Given a list of available employees, when the agent queries SuccessFactors, then it returns skill tags, proficiency levels, and employment information for each employee.
        
-   **Maps to Objective**: Objective 1
    
-   **Priority Rank**: 5
    

**REQ-05: Propose Best-Fit Candidates with Justification**

-   **Problem to Solve**: Matching the right person to a resource gap requires complex manual comparison of availability, skills, time-off data, and project context.
    
-   **User Story**: As a project manager, I need the agent to propose a ranked list of best-fit candidates for each open resource requirement, with clear justification for each recommendation, so that I can make an informed staffing decision quickly. Only candidates who are fully available (no time-off conflicts) during the project timeline should be recommended.
    
-   **Acceptance Criteria**:
    
    -   Given open resource requirements, employee availability, skills, and time-off data, when the agent performs matching, then it returns a ranked list of candidates (minimum 1, up to 3) with a written explanation per candidate covering skills match, availability alignment, time-off clearance, and any relevant context.
        
    -   Given a candidate has approved time-off overlapping the project timeline, then that candidate is excluded from the ranked list.
        
-   **Maps to Objective**: Objectives 1 and 3
    
-   **Priority Rank**: 6
    

**REQ-06: Human-in-the-Loop Confirmation Gate**

-   **Problem to Solve**: Automated systems that execute changes without approval create risk and erode trust.
    
-   **User Story**: As a resource manager, I need the agent to pause and explicitly ask for my confirmation before executing any resource assignment so that I maintain full control over staffing decisions.
    
-   **Acceptance Criteria**:
    
    -   Given the agent has proposed a candidate, when it is ready to assign, then it presents a clear confirmation prompt ("Do you confirm assigning \[Employee\] to \[Project\]? Yes / No") and waits for an explicit response before proceeding.
        
    -   If the response is "No", the agent cancels the assignment and offers to re-run the recommendation with different criteria.
        
-   **Maps to Objective**: Objective 2
    
-   **Priority Rank**: 7
    

**REQ-07: Execute Resource Assignment in S/4HANA Cloud**

-   **Problem to Solve**: After identifying the right candidate, the assignment still needs to be manually entered into S/4HANA Cloud.
    
-   **User Story**: As a resource manager, I need the agent to execute the confirmed resource assignment in SAP S/4HANA Cloud so that the system of record is updated immediately without manual data entry.
    
-   **Acceptance Criteria**:
    
    -   Given manager confirmation has been received, when the agent calls the Resource Assignment Source OData API, then the assignment is created in S/4HANA Cloud and the agent confirms success to the user.
        
    -   If the API call fails, the agent reports the error clearly and does not retry without user instruction.
        
-   **Maps to Objective**: Objectives 1 and 2
    
-   **Priority Rank**: 8
    

### High-Want Requirements

**REQ-08: Assignment Status Confirmation**

-   **Problem to Solve**: After an assignment is executed, users want to verify it was recorded correctly.
    
-   **User Story**: As a resource manager, I need the agent to confirm the assignment was successfully created in S/4HANA Cloud and provide the assignment ID so that I have an audit trail.
    
-   **Priority Rank**: 1
    

**REQ-09: Re-run Recommendation with Adjusted Criteria**

-   **Problem to Solve**: The first set of recommendations may not always be suitable; users may want to filter differently.
    
-   **User Story**: As a project manager, I need to ask the agent to re-run recommendations with adjusted filters (e.g., different skill, different availability window) so that I can explore alternatives without restarting the workflow.
    
-   **Priority Rank**: 2
    

### Nice-to-Have Requirements

**REQ-10: Resource Utilisation Summary**

-   **Problem to Solve**: Resource managers want a quick utilisation overview before making staffing decisions.
    
-   **User Story**: As a resource manager, I need a summary of current workforce utilisation across active projects so that I can avoid overallocation.
    
-   **Priority Rank**: 1
    

**REQ-11: Multi-gap Staffing in One Session**

-   **Problem to Solve**: Projects often have more than one open gap at a time.
    
-   **User Story**: As a project manager, I need the agent to process multiple open resource requirements in a single conversation so that I can resolve all gaps in one session.
    
-   **Priority Rank**: 2
    

* * *

## Non-Functional Requirements

### Performance

-   **Latency**: Agent must return candidate recommendations within 15 seconds of initiating a matching request.
    
-   **Throughput**: The agent must support concurrent sessions for at least 10 simultaneous users.
    

### Reliability

-   **Availability**: Agent should target 99% uptime during business hours.
    
-   **Fallback**: If a downstream SAP API is unavailable, the agent must surface a clear, actionable error message and not proceed with partial or stale data silently.
    

### Explainability

-   **Traceability**: Each candidate recommendation must include the data sources used (availability from S/4HANA, skills from SuccessFactors, time-off records from SuccessFactors) and the reasoning applied.
    
-   **Decision Logging**: All agent actions — tool calls, recommendations, confirmations, and assignment executions — must be logged with timestamps and session IDs.
    
-   **Uncertainty Communication**: If data is missing or ambiguous (e.g., no skills data found in SuccessFactors, time-off records unavailable), the agent must communicate this explicitly before presenting a recommendation.
    

* * *

## Solution Architecture

**Architecture Overview:** A pro-code Python AI Agent (A2A protocol), deployed on SAP BTP, that orchestrates resource staffing by calling SAP S/4HANA Cloud and SAP SuccessFactors APIs via MCP tools generated from API specifications. The agent maintains conversation state and enforces a human-in-the-loop gate before executing any write operations.

**Key Components:**

-   **Python AI Agent (A2A)**: Core reasoning and orchestration layer; manages conversation, tool invocation, candidate ranking, and confirmation flow
    
-   **MCP Translation Files (x6)**: Generated from EDMX/OpenAPI specs; expose each SAP API as a typed tool the agent can call
    
    -   Project Demand MCP tool (`sap.s4:apiResource:API_PROJECTDEMAND_0001:v1`)
        
    -   Resource Assignment Source MCP tool (`sap.s4:apiResource:CE_PROJDEMANDSOURCEOFSUPPLY_0001:v1`)
        
    -   Workforce Daily Availability MCP tool (`sap.s4:apiResource:API_MANAGE_WF_AVAILABILITY:v1`)
        
    -   SuccessFactors Skills Management MCP tool (`sap.sf:apiResource:ECSkillsManagement:v1`)
        
    -   SuccessFactors Employee Profile & Employment Information MCP tools (`sap.sf:apiResource:ECEmployeeProfile:v1`, `sap.sf:apiResource:ECEmploymentInformation:v1`)
        
    -   SuccessFactors Time Off MCP tool (`sap.sf:apiResource:ECTimeOff:v1`)
        
-   **SAP Generative AI Hub**: LLM backend (GPT-4o or equivalent) for candidate matching reasoning and justification generation
    
-   **SAP S/4HANA Cloud**: Source of project data, workforce availability, and target for assignment write-back
    
-   **SAP SuccessFactors**: Source of employee skills and profile data
    

**Integration Points:**

-   S/4HANA Cloud OData APIs: read project demands, workforce availability; write resource assignments (bidirectional)
    
-   SuccessFactors OData APIs: read employee profiles, skills, employment information, and time-off/leave records (read-only)
    

**Deployment Environments:**

-   Dev: isolated BTP space with sandbox S/4HANA and SuccessFactors tenants for development and unit testing
    
-   QA: BTP space connected to non-production SAP systems for integration and acceptance testing
    
-   Prod: BTP space connected to live S/4HANA Cloud and SuccessFactors instances
    

### Agent Extensibility & Instrumentation

**Agent Extensibility:** The agent is designed with extension points to support future capabilities without re-architecting the core:

-   **New tools**: Additional MCP tools (e.g., cost rate APIs, learning history from SuccessFactors Learning) can be registered without modifying the agent's core logic
    
-   **New skills**: Future capabilities (e.g., resource risk scoring, project cost impact analysis) can be added as agent skills loaded at runtime
    
-   **Configurable system prompt**: The agent's persona, guardrails, and tone can be updated via configuration without code changes
    

**Business Step Instrumentation:** All five key business steps are instrumented with OpenTelemetry spans and structured log statements to enable production monitoring and debugging. See the Milestones section for the full log definitions.

### Automation & Agent Behaviour

**Automation Level:** Autonomous agent with mandatory human-in-the-loop gate on write operations

**Actions the system performs without human approval:**

-   Reading active projects from S/4HANA Cloud
    
-   Querying open resource demands from S/4HANA Cloud
    
-   Querying employee availability from S/4HANA Cloud
    
-   Fetching employee skills and profiles from SuccessFactors
    
-   Fetching employee time-off/leave records from SuccessFactors
    
-   Filtering out employees with time-off conflicts during the project timeline
    
-   Generating and presenting candidate recommendations
    

**Actions that require human review or approval:**

-   Executing resource assignment write-back to S/4HANA Cloud (requires explicit "confirm" from project manager or resource manager)
    

**Model or engine used:** GPT-4o (or equivalent) via SAP Generative AI Hub

**Knowledge & data sources accessed:**

-   SAP S/4HANA Cloud — Project Demand API: active projects and open resource requirements (read)
    
-   SAP S/4HANA Cloud — Workforce Daily Availability API: employee availability by date range (read)
    
-   SAP S/4HANA Cloud — Resource Assignment Source API: resource assignment write-back (write)
    
-   SAP SuccessFactors — Skills Management API: employee skill tags and proficiency (read)
    
-   SAP SuccessFactors — Employee Profile API: employee profile details (read)
    
-   SAP SuccessFactors — Employment Information API: employment status and position details (read)
    
-   SAP SuccessFactors — Time Off API: approved time-off/leave records with dates and durations for conflict detection (read)
    

**Tools or connectors invoked:**

-   `get_active_projects` (S/4HANA Project Demand MCP tool): retrieves list of active projects — read-only
    
-   `get_resource_demands` (S/4HANA Project Demand MCP tool): retrieves open resource requirements per project — read-only
    
-   `get_workforce_availability` (S/4HANA Workforce Availability MCP tool): retrieves employee availability for a date range — read-only
    
-   `get_employee_skills` (SuccessFactors Skills Management MCP tool): retrieves skill tags and proficiency per employee — read-only
    
-   `get_employee_profile` (SuccessFactors Employee Profile MCP tool): retrieves employee profile and employment info — read-only
    
-   `get_employee_timeoff` (SuccessFactors Time Off MCP tool): retrieves approved time-off/leave records (dates, durations, leave types) for conflict detection against project timelines — read-only
    
-   `create_resource_assignment` (S/4HANA Resource Assignment Source MCP tool): creates a confirmed assignment in S/4HANA Cloud — **write / high-risk** — only called after explicit human confirmation
    

**Guardrails & fail-safes:**

-   The agent must never call `create_resource_assignment` without a recorded, explicit user confirmation in the current conversation turn
    
-   If the assignment API returns an error, the agent must not retry automatically — it must report the error to the user and await instruction
    
-   If skills data is unavailable from SuccessFactors for a candidate, the agent must flag this in the recommendation and not omit the candidate silently
    
-   If no suitable candidates are found, the agent must communicate this clearly rather than recommending a poor fit
    
-   If a candidate has approved time-off overlapping the project timeline, the agent must exclude them from the recommendation list or clearly flag the conflict — never recommend an employee with a leave conflict as fully available
    
-   Confidence threshold: if fewer than 2 of the 4 criteria (availability, skills, profile, time-off clearance) are available for a candidate, the agent must flag the recommendation as low-confidence
    

* * *

## Governance, Risk & Compliance

**Data Handling:**

-   Employee personal data (names, skills, availability) is accessed in-session only and not persisted by the agent
    
-   All API calls are authenticated via the existing SAP BTP credential store; no credentials are hardcoded
    
-   Data residency follows the BTP region configuration of the deployed tenant
    

**Approval Flows:**

-   Resource assignment execution requires an in-conversation, explicit confirmation from a project manager or resource manager (logged with timestamp and user identity)
    

* * *

## Release Criteria

-   **Functionality**: All REQ-01 through REQ-07 pass acceptance criteria in QA environment
    
-   **Performance**: Candidate recommendations returned within 15 seconds in 95% of test runs
    
-   **Reliability**: No silent failures — all API errors surface as clear user-facing messages
    
-   **Security**: No credentials hardcoded; all API calls use BTP managed credentials
    
-   **Instrumentation**: All 5 milestones emit correct log statements in QA
    
-   **Human-in-the-loop**: 100% of assignment executions in test scenarios require and record explicit confirmation
    
-   **Time-off filtering**: 100% of candidates with approved time-off overlapping the project timeline are excluded or flagged in test scenarios
    

* * *

## Milestones

### M1: Active Projects Retrieved

-   **Description**: The agent has successfully queried and returned the list of active projects from SAP S/4HANA Cloud.
    
-   **Achieved when**: The Project Demand API returns at least one active project and the agent presents it to the user.
    
-   **Log on achievement**: `M1.achieved: active projects retrieved successfully — {count} projects returned from S/4HANA Cloud`
    
-   **Log on miss**: `M1.missed: failed to retrieve active projects — API error or no projects found; user notified`
    

### M2: Resource Requirements Identified

-   **Description**: The agent has queried and surfaced open resource demands for a selected project.
    
-   **Achieved when**: The agent returns at least one open resource requirement (role, skills, dates) for the selected project.
    
-   **Log on achievement**: `M2.achieved: resource requirements identified — {count} open demands found for project {project_id}`
    
-   **Log on miss**: `M2.missed: no open resource requirements found or API error for project {project_id}; user notified`
    

### M3: Employee Availability, Skills, and Time-Off Queried

-   **Description**: The agent has retrieved employee availability from S/4HANA Cloud, skills/profile data from SuccessFactors, and time-off/leave records from SuccessFactors for the candidate pool. Employees with time-off conflicts during the project timeline have been filtered out.
    
-   **Achieved when**: The agent has results from the Workforce Daily Availability API, at least one of the SuccessFactors APIs (Skills Management or Employee Profile), and the Time Off API. Employees with leave conflicts are excluded.
    
-   **Log on achievement**: `M3.achieved: employee data retrieved — {count} employees with availability; SuccessFactors skills data: {available|partial|unavailable}; time-off data: {available|partial|unavailable}; {filtered_count} employees excluded due to time-off conflicts`
    
-   **Log on miss**: `M3.missed: employee availability, skills, or time-off data retrieval failed; agent proceeding with partial data — user notified`
    

### M4: Best-Fit Candidates Proposed

-   **Description**: The agent has completed its AI-driven matching and presented a ranked list of candidates with justification.
    
-   **Achieved when**: The agent presents at least one ranked candidate recommendation with a written justification covering skills match and availability.
    
-   **Log on achievement**: `M4.achieved: candidate recommendations presented — {count} candidates proposed for demand {demand_id}`
    
-   **Log on miss**: `M4.missed: no suitable candidates found for demand {demand_id}; user notified with reasons`
    

### M5: Resource Assignment Executed

-   **Description**: Following explicit manager confirmation, the agent has successfully written the resource assignment to SAP S/4HANA Cloud.
    
-   **Achieved when**: The Resource Assignment Source OData API returns a success response and the agent confirms the assignment ID to the user.
    
-   **Log on achievement**: `M5.achieved: resource assignment executed — employee {employee_id} assigned to project {project_id}; assignment ID: {assignment_id}`
    
-   **Log on miss**: `M5.missed: resource assignment execution failed — API error {error_code}; no assignment created; user notified`
    

* * *

## Risks, Assumptions, and Dependencies

### Risks

-   **MCP translation file quality**: Since no pre-deployed MCP servers exist for the required APIs, translation files must be generated from EDMX/OpenAPI specs. Incomplete or inaccurate translations could reduce tool reliability.
    
-   **Cross-system data consistency**: Availability data resides in S/4HANA Cloud while skills and time-off data reside in SuccessFactors. If employee IDs or keys do not align between systems, cross-referencing may fail or produce incorrect matches. The agent must reconcile workforce daily availability with approved time-off periods to avoid conflicts.
    
-   **LLM reasoning quality**: The accuracy of candidate recommendations depends on the quality of the AI model's reasoning. Edge cases (e.g., partial availability, overlapping project demands) may produce suboptimal suggestions.
    

### Assumptions (Validate These)

-   SAP S/4HANA Cloud and SAP SuccessFactors are connected to the same BTP tenant and accessible via OData APIs with appropriate credentials.
    
-   Employee identifiers (e.g., personnel number) are consistent across S/4HANA Cloud and SuccessFactors, enabling cross-system joins.
    
-   Project managers and resource managers have been granted appropriate authorisation to read project and workforce data via the agent.
    
-   The organisation uses SAP Project and Resource Management (ProjRM) capabilities within S/4HANA Cloud for project demand and assignment management.
    

### Dependencies

-   SAP BTP deployment environment with access to SAP Generative AI Hub (LLM)
    
-   Live or sandbox access to SAP S/4HANA Cloud OData APIs (Project Demand, Workforce Availability, Resource Assignment Source)
    
-   Live or sandbox access to SAP SuccessFactors OData APIs (Employee Profile, Skills Management, Employment Information, Time Off)
    
-   MCP translation files generated from EDMX/OpenAPI specifications for all 7 APIs
    

* * *

## Appendix

### References

-   SAP Project and Resource Management: [https://help.sap.com/docs/SAP\_S4HANA\_CLOUD/project-resource-management](https://help.sap.com/docs/SAP_S4HANA_CLOUD/project-resource-management)
    
-   SAP SuccessFactors Employee Central APIs: [https://help.sap.com/docs/SAP\_SUCCESSFACTORS\_EMPLOYEE\_CENTRAL](https://help.sap.com/docs/SAP_SUCCESSFACTORS_EMPLOYEE_CENTRAL)
    
-   SAP BTP AI Agent (A2A): SAP Build Joule Studio Runtime documentation
    
-   SAP Generative AI Hub: [https://help.sap.com/docs/sap-ai-core/generative-ai-hub](https://help.sap.com/docs/sap-ai-core/generative-ai-hub)
    
-   RBA Sub-Process: BPS-361\_009 — Initiate projects (project based services)