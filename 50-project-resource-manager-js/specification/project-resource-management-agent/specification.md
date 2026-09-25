# Specification: project-resource-management-agent

> **Guidelines**: Read all applicable guidelines before executing ANY tasks below:
> - [guidelines.md](../guidelines.md) — Universal execution rules
> - [guidelines-agent.md](../guidelines-agent.md) — Universal agent patterns
> - [guidelines-agent-python.md](../guidelines-agent-python.md) — Python implementation details
> - [guidelines-agent-skills.md](../guidelines-agent-skills.md) — Runtime skills patterns
> - [guidelines-agent-mcp.md](../guidelines-agent-mcp.md) — MCP integration patterns

---

## Basic Setup

- [x] Read `product-requirements-document.md` and `intent.md` for the full context of this solution
- [x] Bootstrap agent code in `assets/project-resource-management-agent/` using instructions from the `sap-agent-bootstrap` skill. Invoke from inside `assets/project-resource-management-agent/`, using copy commands — do NOT create files manually.
- [x] Install dependencies, validate the agent starts and responds at `/.well-known/agent.json`

---

## Runtime Skills

This agent requires two runtime skills for complex multi-step workflows:

- [x] Create `assets/project-resource-management-agent/app/skills/resource-matching/SKILL.md` with:
  - Frontmatter: `name: resource-matching`, `description: Multi-step workflow for cross-referencing project demands with employee availability, time-off records, and skills from S/4HANA Cloud and SuccessFactors to propose ranked best-fit candidates who are fully available during the project timeline`
  - Step-by-step instructions for: (1) extracting required role/skills from project demand, (2) filtering availability data by date window, (3) retrieving time-off/leave records from SuccessFactors and filtering out employees with approved time-off overlapping the project timeline, (4) cross-referencing SF skills per available employee, (5) scoring candidates by skills match + availability alignment + time-off clearance + employment status, (6) formatting ranked output with written justification per candidate (including time-off clearance confirmation), (7) flagging low-confidence recommendations when fewer than 2 of 4 criteria are available
  - Include table: confidence levels based on data completeness (all 4 criteria = high, 3 = medium, 2 or fewer = low)

- [x] Create `assets/project-resource-management-agent/app/skills/assignment-confirmation/SKILL.md` with:
  - Frontmatter: `name: assignment-confirmation`, `description: Human-in-the-loop confirmation gate for resource assignment — must obtain explicit yes/no confirmation before calling the assignment API`
  - Step-by-step instructions for: (1) presenting candidate summary before asking for confirmation, (2) exact confirmation prompt wording `"Do you confirm assigning [Employee Name] to [Project Name] for demand [Demand ID]? Please reply Yes or No."`, (3) handling Yes — proceed to call create_resource_assignment tool, (4) handling No — cancel assignment and offer to re-run recommendations, (5) never calling the assignment API without a recorded confirmation in the current session

---

## Project-Specific Tasks

### REQ-01 — List Active Projects

- [ ] Implement system prompt instruction directing the agent to use the `A_ProjectDemand` entity from the Project Demand MCP tool to retrieve active projects (filter by `ProjectDemandStatus` for active/open records), returning project ID, name, demand status, and dates
- [ ] Milestone M1 instrumentation: log `M1.achieved: active projects retrieved successfully — {count} projects returned from S/4HANA Cloud` on success; log `M1.missed: failed to retrieve active projects — API error or no projects found; user notified` on failure
- [ ] System prompt must instruct agent to handle case where no active projects are found: respond clearly rather than returning an empty result silently

### REQ-02 — Retrieve Open Resource Requirements

- [ ] Implement system prompt instruction directing the agent to use `A_ProjectDemandResource` and `A_ProjectDemandResourceRequest` entities from the Project Demand MCP tool, filtering by project UUID and `ProjDmndAssgmtStatus` for open/unassigned demands, returning role, activity type, required dates, and staffing instructions
- [ ] Milestone M2 instrumentation: log `M2.achieved: resource requirements identified — {count} open demands found for project {project_id}` on success; log `M2.missed: no open resource requirements found or API error for project {project_id}; user notified` on failure

### REQ-03 — Check Employee Availability

- [ ] Implement system prompt instruction directing the agent to use the `TimeOverviewSet` entity from the Workforce Daily Availability MCP tool, filtering by date range derived from resource demand dates, returning employee work agreement ID, planned working hours, absence hours, and non-working day flag per calendar date
- [ ] System prompt must instruct agent to aggregate daily availability into weekly/total capacity for a given time window before presenting to user
- [ ] Milestone M3 instrumentation (partial — combined with skills and time-off retrieval): log `M3.achieved: employee data retrieved — {count} employees with availability; SuccessFactors skills data: {available|partial|unavailable}; time-off data: {available|partial|unavailable}; {filtered_count} employees excluded due to time-off conflicts` when all queries complete; log `M3.missed: employee availability, skills, or time-off data retrieval failed; agent proceeding with partial data — user notified` when any fails

### REQ-03a — Check Employee Time-Off / Leave Data

- [ ] Implement system prompt instruction directing the agent to use the `EmployeeTime` entity from the SF Time Off MCP tool, filtering by the project's required date range, retrieving approved time-off records including `timeType`, `startDate`, `endDate`, `quantityInDays`, and `approvalStatus` per employee
- [ ] System prompt must instruct agent to compare each candidate's approved time-off dates against the project timeline: if any approved leave overlaps the required date range, exclude the employee from the recommendation list or flag them as partially unavailable with the conflict dates shown
- [ ] System prompt must handle the case where time-off data is unavailable for an employee: flag with `[Time-off data unavailable — availability unconfirmed]` but do not exclude the candidate silently

### REQ-04 — Retrieve Employee Skills and Profiles

- [ ] Implement system prompt instruction directing the agent to use the `SkillProfile` and `RatedSkillMapping` entities from the SF Skills Management MCP tool, and `EmpJob` entity from the SF Employment Information MCP tool, retrieving skill names, proficiency levels, job title, department, location, and employment status per employee
- [ ] System prompt must instruct agent to use `EPPublicProfile` from the SF Employee Profile MCP tool for additional profile context (introduction, certifications)
- [ ] System prompt must explicitly handle the case where SkillProfile does not exist for an employee: flag this in the recommendation with `[Skills data unavailable]` rather than omitting the candidate silently

### REQ-05 — Propose Best-Fit Candidates with Justification

- [ ] Implement system prompt instruction to load the `resource-matching` skill when the user requests candidate recommendations, and apply the matching logic from that skill
- [ ] System prompt must instruct agent to: rank up to 3 candidates per demand, write justification covering (1) skills match percentage, (2) availability window alignment, (3) time-off clearance (confirm no leave conflicts during project timeline), (4) job profile relevance; flag low-confidence candidates explicitly
- [ ] System prompt must state: if a candidate has approved time-off overlapping the project timeline, exclude them from the ranked list entirely
- [ ] System prompt must state: if no suitable candidates are found (no availability, no matching skills, no profile data, or all candidates have time-off conflicts), report this clearly with the reason rather than recommending a poor fit
- [ ] Milestone M4 instrumentation: log `M4.achieved: candidate recommendations presented — {count} candidates proposed for demand {demand_id}` on success; log `M4.missed: no suitable candidates found for demand {demand_id}; user notified with reasons` on failure

### REQ-06 — Human-in-the-Loop Confirmation Gate

- [ ] Implement system prompt instruction to load the `assignment-confirmation` skill before calling any write operation, and follow its instructions strictly
- [ ] System prompt guardrail: add explicit instruction `"CRITICAL: NEVER call the resource assignment tool (create_resource_assignment or equivalent) without first receiving an explicit 'Yes' confirmation from the user in the current conversation turn. If the user says 'No', cancel the assignment and offer to re-run recommendations."`

### REQ-07 — Execute Resource Assignment in S/4HANA Cloud

- [ ] Implement system prompt instruction directing the agent to use the Resource Assignment Source MCP tool to create the assignment only after confirmation is recorded; include employee ID, project demand UUID, demand work UUID, quantity, unit, start date, end date
- [ ] System prompt must instruct agent: if the assignment API returns an error, report it verbatim, do NOT retry automatically, and await user instruction
- [ ] System prompt must instruct agent: confirm the assignment ID returned by the API and present it to the user as the audit confirmation
- [ ] Milestone M5 instrumentation: log `M5.achieved: resource assignment executed — employee {employee_id} assigned to project {project_id}; assignment ID: {assignment_id}` on success; log `M5.missed: resource assignment execution failed — API error {error_code}; no assignment created; user notified` on failure

### REQ-08 — Assignment Status Confirmation (High-Want)

- [ ] System prompt instruction: after a successful assignment, instruct agent to confirm the assignment was recorded and surface the assignment ID as an audit trail to the user

### REQ-09 — Re-run Recommendations with Adjusted Criteria (High-Want)

- [ ] System prompt instruction: when user asks to re-run recommendations with different criteria (different skill filter, different date range), agent should reload the resource-matching skill and apply the new filter parameters without requiring the user to restart the full workflow

### Business Guardrails in System Prompt

- [ ] Add prompt section: `"Data Integrity: You MUST use tools to retrieve live data from SAP S/4HANA Cloud and SAP SuccessFactors. Never fabricate, guess, or invent employee names, availability, skills, or project data."` 
- [ ] Add prompt section: `"Graceful Degradation: If data from one system (S/4HANA Cloud or SuccessFactors) is unavailable, communicate this clearly and continue with partial data rather than failing silently. Always tell the user what data is missing."`
- [ ] Add prompt section: `"Page Size: When calling tools that support pagination, always set the page size parameter (top, limit, pageSize, etc.) to a maximum of 100 items to prevent context overflow. Inform the user when this limit is applied."`
- [ ] Add prompt section: `"Confidence Threshold: If fewer than 2 of the 4 criteria (availability, skills, employment profile, time-off clearance) are available for a candidate, flag the recommendation as low-confidence and communicate the missing data to the user."`

---

## Business Instrumentation

- [ ] Implement business step instrumentation for all 5 milestones from the PRD with structured logging pattern `[MILESTONE_ID].[achieved|missed]: [description]` and OpenTelemetry custom spans
- [ ] Extract all business logic from `stream()` into a plain async helper method (e.g. `_run_agent()`) to avoid `GeneratorExit` context errors with OpenTelemetry spans
- [ ] Verify `bootstrap(app)` is called after `app = server.build()` in `main.py`

---

## MCP Tool Integration

> Read [guidelines-agent-mcp.md](../guidelines-agent-mcp.md) — Path A applies: API spec files exist, no pre-deployed MCP servers.

- [ ] Verify `specification/project-resource-management-agent/api-specs/` contains all 7 EDMX files:
  - `project-demand.edmx` (ORD ID: `sap.s4:apiResource:API_PROJECTDEMAND_0001:v1`) — Project Demand API: active projects, open resource requirements
  - `resource-assignment-source.edmx` (ORD ID: `sap.s4:apiResource:CE_PROJDEMANDSOURCEOFSUPPLY_0001:v1`) — Resource Assignment Source API: write-back of confirmed assignments
  - `workforce-daily-availability.edmx` (ORD ID: `sap.s4:apiResource:API_MANAGE_WF_AVAILABILITY:v1`) — Workforce Daily Availability API: employee availability by date
  - `sf-skills-management.edmx` (ORD ID: `sap.sf:apiResource:ECSkillsManagement:v1`) — SuccessFactors Skills Management: skill profiles and ratings
  - `sf-employee-profile.edmx` (ORD ID: `sap.sf:apiResource:ECEmployeeProfile:v1`) — SuccessFactors Employee Profile: background and education
  - `sf-employment-information.edmx` (ORD ID: `sap.sf:apiResource:ECEmploymentInformation:v1`) — SuccessFactors Employment Information: job title, department, location
  - `sf-time-off.edmx` (ORD ID: `sap.sf:apiResource:ECTimeOff:v1`) — SuccessFactors Time Off: approved time-off/leave records with dates and durations for conflict detection

- [ ] Invoke `mcp-translation-file` skill for each of the 7 API spec files to generate MCP translation cards in `specification/project-resource-management-agent/mcps/<api-spec-stem>/`

- [ ] Invoke `setup-solution` skill to create MCP server assets for all generated translation files

- [ ] After `setup-solution` completes, read generated `asset.yaml` for each MCP server asset and copy exact ORD IDs verbatim into the agent's `asset.yaml` `requires` section — one entry per MCP server. NEVER invent or guess ORD IDs.

- [ ] Wire MCP tool loading in `app/agent.py` using `get_mcp_tools()` from the `mcp_tools` module. NEVER import directly from `sap_cloud_sdk.agentgateway`. NEVER create direct HTTP clients for SAP APIs.

- [ ] After `mcp-translation-file` and `setup-solution` complete, generate `mcp-mock.json` using the `mcp-mock-config` skill (required before tests can run)

---

## Testing

> See [guidelines-agent-python.md](../guidelines-agent-python.md) for Python testing setup and patterns.

- [ ] `conftest.py` only sets `IBD_TESTING=true` — do NOT branch on `IBD_TESTING` in application code; the fixture patches `mcp_tools.get_mcp_tools`
- [ ] Write unit tests in `assets/project-resource-management-agent/tests/` — one test per tool/capability area:
  - `test_get_active_projects.py` — mock Project Demand MCP, assert project list returned with expected fields
  - `test_get_resource_demands.py` — mock Project Demand MCP, assert open demands returned per project UUID
  - `test_get_workforce_availability.py` — mock Workforce Availability MCP, assert daily availability data returned and aggregated
  - `test_get_employee_skills.py` — mock SF Skills Management MCP, assert skill profiles and proficiency levels returned
  - `test_get_employee_profile.py` — mock SF Employee Profile MCP, assert profile data returned
  - `test_get_employment_info.py` — mock SF Employment Information MCP, assert job title, department, location returned
  - `test_get_employee_timeoff.py` — mock SF Time Off MCP, assert approved time-off records returned with dates and durations; assert employees with time-off overlapping project timeline are excluded from recommendations
  - `test_create_resource_assignment.py` — mock Resource Assignment Source MCP, assert assignment created only when confirmation is recorded; assert it is NOT called without confirmation
- [ ] Write one integration test `test_end_to_end_staffing_flow.py` — simulate full conversation: list projects → get demands → get availability → get time-off → get skills → propose candidates (verify time-off filtered) → confirm → execute assignment; mock LLM responses and all MCP tool responses; test must run offline
- [ ] Run `pytest` from `assets/project-resource-management-agent/` (no args); if coverage < 70%, add tests until threshold met
- [ ] Verify `assets/project-resource-management-agent/app/agent.py` has exactly 9 decorated functions — run `grep -c "^@agent_model\|^@agent_config\|^@prompt_section" assets/project-resource-management-agent/app/agent.py` and confirm it returns 9
- [ ] Run final `pytest` (no args) to generate `test_report.json`
- [ ] Verify `test_report.json` exists in `assets/project-resource-management-agent/`
