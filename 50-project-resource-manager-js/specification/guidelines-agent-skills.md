# Runtime Skills Guidelines

Runtime skills are task-specific instructions and resources that live alongside your agent code. They enable complex workflows without bloating the system prompt.

For universal agent patterns, see [guidelines-agent.md](./guidelines-agent.md).

## What are Runtime Skills?

Runtime skills provide:
- Multi-step workflows with decision trees
- Domain-specific instructions and constraints
- Reference material (templates, JSON examples, documentation)
- Task-specific validation rules

Skills are **language-agnostic** — the same skill format works regardless of agent implementation language.

## When to Create Runtime Skills

**Create a runtime skill when ANY of these apply:**

| Scenario | Example |
|----------|---------|
| Complex multi-step workflows | Approval processes with escalation paths |
| Domain-specific knowledge | Industry compliance rules, regulatory constraints |
| Task-specific instructions | Report formatting, data validation rules |
| Reference material needed | Templates, lookup tables, example payloads |
| Conditional logic trees | Different handling based on amount, category, region |
| Instructions that don't belong in system prompt | Too detailed, too specific, or would bloat the prompt |

**Skip runtime skills when:**
- Instructions are simple enough for the system prompt
- The task is a one-liner with no branching logic
- No reference material is needed

### Decision Examples

| PRD Requirement | Runtime Skill? | Reasoning |
|-----------------|----------------|-----------|
| "Approve purchase orders over $10K with manager sign-off" | **Yes** | Multi-step workflow with conditional logic |
| "Validate expense reports against company policy" | **Yes** | Domain-specific rules, reference material |
| "Summarize meeting notes" | No | Simple task, no complex logic |
| "Look up customer information" | No | Single tool call, no workflow |
| "Generate quarterly reports with regional breakdowns" | **Yes** | Complex formatting, templates needed |
| "Process refund requests with fraud detection" | **Yes** | Decision tree, multiple paths |

## Example Skill File Structure

```
assets/<asset-name>/app/skills/
├── workflow-approval/
│   ├── SKILL.md                    # Skill instructions (frontmatter + body)
│   ├── references/
│   │   ├── approval-matrix.md      # Lookup tables, rules
│   │   └── templates/
│   │       └── approval-email.txt  # Output templates
│   └── examples/
│       └── sample-request.json     # Example payloads
└── data-validation/
    ├── SKILL.md
    └── assets/
        └── validation-rules.json
```

## SKILL.md Format

Every skill requires a `SKILL.md` file with YAML frontmatter:

```markdown
---
name: workflow-approval
description: Multi-step approval workflow for purchase orders with escalation rules
---

# Purchase Order Approval Workflow

## When to Use This Skill

Load this skill when the user requests approval for a purchase order, or when processing PO-related tasks that require authorization.

## Prerequisites

Before starting:
- Verify the PO exists in the system
- Confirm the requester has submission rights

## Instructions

### Step 1: Validate Request

1. Retrieve PO details using the procurement tool
2. Verify all required fields are populated:
   - Vendor ID
   - Line items with quantities and prices
   - Cost center
   - Requested delivery date

### Step 2: Determine Approval Path

Based on total PO value:

| Amount | Approval Required |
|--------|-------------------|
| < $1,000 | Auto-approve |
| $1,000 - $10,000 | Manager approval |
| $10,000 - $50,000 | Director approval |
| > $50,000 | VP approval + Finance review |

### Step 3: Route for Approval

[Detailed routing instructions...]

## Error Handling

If the PO is incomplete:
1. List missing fields
2. Return to requester with specific instructions
3. Do NOT proceed with approval routing
```

## Agent Integration

The agent loads skills on-demand via the `load(path)` tool:

```python
# Agent can load any skill file
skill_content = load("skills/workflow-approval/SKILL.md")

# And any companion asset files
approval_matrix = load("skills/workflow-approval/references/approval-matrix.md")
email_template = load("skills/workflow-approval/references/templates/approval-email.txt")
sample = load("skills/workflow-approval/examples/sample-request.json")
```

**No extra wiring needed** — the `load(path)` tool is automatically available from the bootstrap.

## Best Practices

### 1. Keep Skills Focused

One skill per cohesive task domain. Don't create a "mega-skill" that handles everything.

**Good:** `expense-validation`, `travel-booking`, `invoice-processing`
**Bad:** `all-finance-tasks`

### 2. Use Clear Frontmatter

The `name` and `description` fields guide the agent when deciding which skill to load:

```yaml
---
name: expense-validation
description: Validates expense reports against company policy including per-diem limits, receipt requirements, and category restrictions
---
```

### 3. Write Imperative Instructions

Use direct, actionable language. The agent follows these instructions literally.

**Good:** "Retrieve the customer record. Verify the account is active. If inactive, stop and inform the user."
**Bad:** "You might want to check if the customer exists and maybe verify their status."

### 4. Include Decision Criteria

Make branching logic explicit with tables or numbered conditions:

```markdown
## Escalation Rules

| Condition | Action |
|-----------|--------|
| Amount > $50K | Escalate to VP |
| Vendor is new | Require compliance review |
| Rush request | Add expedite flag, notify procurement |
```

### 5. Separate Data from Instructions

Keep reference data in companion files, not inline in `SKILL.md`:

```
skills/expense-validation/
├── SKILL.md                      # Instructions only
├── assets/
│   ├── per-diem-rates.json       # Data: rates by city
│   └── category-limits.json      # Data: spending limits
└── references/
    └── required-receipts.md      # Reference: receipt rules
```

### 6. Provide Examples

Show the agent what good input/output looks like:

```markdown
## Example

**Input:** "Process expense report EXP-2024-1234"

**Expected Flow:**
1. Load expense report EXP-2024-1234
2. Validate against policy (see references/policy-rules.md)
3. Flag items exceeding per-diem (assets/per-diem-rates.json)
4. Return validation summary
```
