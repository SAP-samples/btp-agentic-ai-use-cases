---
name: resource-matching
description: Multi-step workflow for cross-referencing project demands with employee availability, time-off records, and skills from S/4HANA Cloud and SuccessFactors to propose ranked best-fit candidates who are fully available during the project timeline
---

# Resource Matching Workflow

Use this skill when the user asks you to find, recommend, or propose candidates for an open resource requirement.

## Prerequisites

Before starting, you must have:
1. A specific resource demand (ProjectDemandWorkUUID or demand details) from a project
2. The required date window (start and end dates) from the demand
3. Availability data retrieved from the Workforce Daily Availability tool
4. Time-off/leave data retrieved from the SuccessFactors Time Off tool
5. Skills and profile data from SuccessFactors tools

## Step 1: Extract Demand Requirements

From the resource demand data, extract:
- Required role / activity type (ActivityType field)
- Required delivery organization (ProjDmndRequestedDeliveryOrg)
- Required start and end dates
- Staffing instruction text (ProjDmndStfngInstructionText) if available
- Assignment status (must be open/unassigned)

Note these requirements as your matching criteria.

## Step 2: Filter Availability by Date Window

Using the demand's start and end dates as your date range:
1. Query the TimeOverviewSet entity filtering by the date range
2. For each employee returned, calculate their total available capacity:
   - Sum `Plannedworkinghours` minus `Absencehours` for non-holiday, non-absence days
   - Exclude days where `Isnonworkingday = true`
3. Keep only employees with at least 20% available capacity during the demand window
4. Record each employee's: WorkAgreementExternalId, total available hours, and availability percentage

## Step 3: Check Time-Off / Leave Conflicts

For each available employee from Step 2:
1. Query the EmployeeTime entity from the SF Time Off tool, filtering by the project's required date range and the employee's user ID
2. Check for approved time-off records (`approvalStatus` = approved) where the leave dates (`startDate` to `endDate`) overlap with the project timeline
3. **If an employee has approved time-off overlapping the project timeline:**
   - **Exclude them** from the candidate pool entirely
   - Record the reason: `Excluded — approved time-off from [start] to [end] conflicts with project timeline`
4. **If time-off data is unavailable** for an employee, flag with `[Time-off data unavailable — availability unconfirmed]` but do NOT exclude them silently
5. Record the number of employees filtered out due to time-off conflicts

## Step 4: Cross-Reference SuccessFactors Skills

For each remaining employee (passed Steps 2 and 3):
1. Query SkillProfile using the employee's user ID (map from work agreement ID)
2. If SkillProfile exists, query RatedSkillMapping to get all rated skills with proficiency levels
3. Query EmpJob to get current job title, department, location, and employment status
4. Query EPPublicProfile for additional context (introduction, certifications)
5. If SkillProfile does NOT exist, flag this employee as `[Skills data unavailable]` — do NOT omit them

Compile a profile per candidate:
- Name / Employee ID
- Available hours and percentage
- Time-off clearance status (cleared / unavailable)
- Skills list with proficiency levels
- Job title and department
- Data completeness flags

## Step 5: Score Candidates

Score each candidate (0–100) using these weights:

| Criterion | Weight | How to Score |
|-----------|--------|--------------|
| Skills match | 40% | Count how many required skills (from demand role/activity) the candidate has, divided by total required skills x 40 |
| Availability alignment | 25% | Availability percentage x 25 |
| Time-off clearance | 15% | 15 if fully clear (no time-off conflicts and data confirmed), 8 if time-off data unavailable, 0 if any conflict detected |
| Employment profile fit | 20% | Job title relevance to demand role x 20 (use 10 if partially relevant, 5 if not relevant) |

**Confidence Levels Based on Data Completeness:**

| Data Available | Confidence Level |
|----------------|-----------------|
| All 4 criteria (availability + time-off clearance + skills + profile) | **High** |
| 3 of 4 criteria available | **Medium** — flag in output |
| 2 or fewer of 4 criteria available | **Low** — flag prominently in output |

If fewer than 2 criteria are available for any candidate, add: `Warning: Low-confidence recommendation — [state which data is missing]`

## Step 6: Format Ranked Output

Present the top 3 candidates (or fewer if fewer qualify) in ranked order:

```
## Candidate Recommendations for Demand [Demand ID]

Note: [X] employees were excluded due to approved time-off conflicts during the project timeline.

### Rank 1: [Employee Name] (Score: XX/100 | Confidence: High/Medium/Low)
**Availability:** XX hours available (XX%) during [date range]
**Time-Off Status:** No approved time-off during project timeline / [Time-off data unavailable — availability unconfirmed]
**Skills Match:** [list matching skills with proficiency levels]
**Job Profile:** [Job Title], [Department], [Location]
**Justification:** [2-3 sentences explaining why this person is a good fit — cover skills alignment, availability window, time-off clearance, and role relevance]

### Rank 2: [Employee Name] ...
### Rank 3: [Employee Name] ...
```

If no candidates qualify (all excluded due to time-off, no availability, or no skills match), report:
```
No suitable candidates found for demand [Demand ID].
Reason: [specific reason — e.g., "All available employees have approved time-off during the project timeline", "No employees with sufficient availability in the required date range", "Skills data unavailable for all available employees", etc.]
```

## Step 7: Offer Next Step

After presenting recommendations, ask the user:
"Would you like to proceed with assigning one of these candidates? If so, please confirm which candidate and I will guide you through the confirmation step."

Do NOT proceed to assignment without explicit user direction.
