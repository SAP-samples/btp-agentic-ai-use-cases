---
name: assignment-confirmation
description: Human-in-the-loop confirmation gate for resource assignment — must obtain explicit yes/no confirmation before calling the assignment API
---

# Assignment Confirmation Gate

Load this skill whenever you are about to execute a resource assignment. This is a mandatory gate — no assignment is ever executed without completing this workflow.

## CRITICAL RULE

**NEVER call the resource assignment tool without explicit "Yes" confirmation in the current conversation turn.**
If you are uncertain whether confirmation was given, ask again. Do not infer confirmation from context.

## Step 1: Present Assignment Summary

Before asking for confirmation, present a clear summary of what will be assigned:

```
## Resource Assignment Summary

📋 **Project:** [Project Name] ([Project ID])
👤 **Candidate:** [Employee Full Name] ([Employee ID])
📅 **Assignment Period:** [Start Date] to [End Date]
🔧 **Demand:** [Demand Name/ID] — [Role/Activity Type]
⏱️ **Quantity:** [Hours/Days] [Unit]

**Candidate Justification:**
[Brief reminder of why this candidate was recommended — top 2 reasons]
```

## Step 2: Ask for Explicit Confirmation

After presenting the summary, ask exactly this question:

> **"Do you confirm assigning [Employee Name] to [Project Name] for demand [Demand ID]? Please reply Yes or No."**

Then STOP and wait for the user's response. Do not proceed until you receive a clear answer.

## Step 3: Handle the Response

### If user responds "Yes" (or clear affirmative):

1. Record the confirmation: note in your reasoning that explicit confirmation was received
2. Proceed to call the resource assignment tool with these parameters:
   - `ProjectDemandWorkUUID`: the work demand UUID
   - `ProjectDemandUUID`: the project demand UUID
   - `ProjDmndRsceAssgmt`: the employee personnel number
   - `ProjDmndRsceAssgmtQuantity`: assigned hours/days
   - `ProjDmndRsceAssgmtQuantityUnit`: unit of measure (e.g., "H" for hours)
   - `ProjDmndRsceAssgmtStartDate`: assignment start date
   - `ProjDmndRsceAssgmtEndDate`: assignment end date

3. If the API call succeeds, confirm to the user:
   ```
   ✅ Assignment successfully created!
   Assignment ID: [assignment_id]
   Employee [Name] has been assigned to [Project Name] for demand [Demand ID].
   Please keep this Assignment ID for your audit records.
   ```

4. If the API call fails, report the error exactly as received:
   ```
   ❌ Assignment failed.
   API Error: [exact error message]
   No assignment was created. Please review the error and let me know how you would like to proceed.
   ```
   Do NOT retry automatically. Wait for user instruction.

### If user responds "No" (or clear negative):

1. Cancel the assignment immediately
2. Respond:
   ```
   Assignment cancelled. No changes have been made to S/4HANA Cloud.
   Would you like me to:
   - Re-run the candidate recommendations with different criteria?
   - Choose a different candidate from the existing recommendations?
   - Start over with a different project or demand?
   ```

### If user responds with something unclear:

Ask again with the exact confirmation question from Step 2. Never assume confirmation from an ambiguous response.

## Error Handling

- If the assignment tool is not available, report: "The resource assignment tool is currently unavailable. No assignment was made."
- If required parameters are missing, ask the user to provide them before proceeding
- Always confirm the outcome — success or failure — explicitly to the user
