# n8n SAP Task Center Node Generation

## Overview

Ensures **stable and correct** generation of SAP Task Center nodes for human-in-the-loop (HITL) approval workflows. It enforces strict validation rules and mandatory structural patterns to prevent common errors.

**Critical Mission:** SAP Task Center nodes MUST always be followed by a switch node because they have only ONE output that contains the decision result.

---

## CRITICAL RULES (DO NOT SKIP)

### 1. **ALWAYS use MCP to get node metadata**

**BEFORE generating a SAP Task Center node:**
```javascript
// Call MCP tool
search-nodes-catalog("task center")
```

**Use the returned values:**
- `name` → use as `type` in workflow
- `version` → use as `typeVersion` in workflow
- `properties` → use to understand available parameters

**NEVER hardcode typeVersion** - always get it from MCP.

---

### 2. **ALWAYS Ask for the recipient first**

Before writing the Task Center node's parameters — before choosing subject, priority, or task definition — you must have an explicit recipient (email address **or** group ID) from the user.

**The ask.** Stop and ask the user, for example:

> "Who should receive this approval task in SAP Task Center? Please provide either the recipient's email address or a group ID."

**Bypass rule.** Only skip the ask if the *current* user prompt in this conversation already contains an unambiguous email address or group ID intended for this Task Center node. A recipient mentioned for a *previous* Task Center node in the same workflow does not carry over unless the user explicitly says so.

**Sufficient answer.** One of the two is enough — an explicit email (`userId`) **or** an explicit group ID (`groupId`) satisfies this rule. Do not ask for both once the user has provided one.

**Forbidden fallbacks — never do any of these:**

- ❌ `{ userId: "user@example.com" }` — generated placeholder
- ❌ `{ userId: "manager@company.com" }` — copied from this skill's example
- ❌ `{ userId: "={{ $json.body.email }}" }` — derived from input payload
- ❌ `{ userId: "={{ $('Webhook').item.json.requesterEmail }}" }` — derived from input payload
- ❌ Any other expression, guess, or heuristic
- ✅ Ask the user first, then set `{ userId: "<exact email provided>" }`
- ✅ If the user provides a group ID instead, set `{ groupId: "<exact group ID provided>" }`

---

### 3. **Mandatory Switch Node After Task Center**

SAP Task Center has **only ONE output** containing the decision in `$json.result.response`.

**Required pattern:**
```
Webhook → [Processing] → SAP Task Center → Switch Node → [Branches]
```

**Switch node configuration:**
```json
{
  "type": "<Switch node from MCP>",
  "typeVersion": "<from MCP>",
  "name": "Route Approval Decision",
  "parameters": {
    "mode": "rules",
    "rules": {
      "values": [
        {
          "conditions": {
            "options": {
              "caseSensitive": true,
              "leftValue": "",
              "typeValidation": "strict"
            },
            "conditions": [
              {
                "leftValue": "={{ $json.result.response }}",
                "rightValue": "approved",
                "operator": {
                  "type": "string",
                  "operation": "equals"
                }
              }
            ],
            "combinator": "and"
          },
          "renameOutput": true,
          "outputKey": "approved"
        },
        {
          "conditions": {
            "options": {
              "caseSensitive": true,
              "leftValue": "",
              "typeValidation": "strict"
            },
            "conditions": [
              {
                "leftValue": "={{ $json.result.response }}",
                "rightValue": "rejected",
                "operator": {
                  "type": "string",
                  "operation": "equals"
                }
              }
            ],
            "combinator": "and"
          },
          "renameOutput": true,
          "outputKey": "rejected"
        }
      ]
    }
  }
}
```

---

### 4. **Contextual Node Name (canvas `name`)**

The Task Center node's `name` field MUST describe the approval's purpose in the context of the surrounding solution — never the generic `"SAP Task Center"` or `"Task Center"`.

Choose a name that makes the step's intent obvious to anyone reading the workflow.

- ✅ Good: `"Approve Travel Expense"`, `"Review Budget Increase Request"`, `"Approve Leave Request"`, `"Approve Purchase Requisition"`.
- ❌ Bad: `"SAP Task Center"`, `"Approval"`, `"Task"`, `"Review Step"`.

---

### 5. **Mandatory Parameters**

**Always required:**
- `subject` (string) - Task title shown to user
- `priority` (enum) - One of: `"VERY_HIGH"`, `"HIGH"`, `"MEDIUM"`, `"LOW"`.
  - **Default to `"MEDIUM"` unless the user explicitly specified a different priority.**
- Configure at least one non-empty recipient target:
  - `recipients.recipientValues: [{ "userId": "email@example.com" }]`
  - `recipientGroups.recipientGroupValues: [{ "groupId": "group-id" }]`
- You may configure both at the same time.
- Do not emit empty arrays for either field.

**Optional:**
- `taskDefinition.definitionName` (string) - Name displayed in SAP Task Center. If the user hasn't specified an explicit definition name, set this to the same value as the node's canvas `name` (see **Contextual Node Name**).

**Example:**
```json
{
  "name": "Approve Travel Expense",
  "parameters": {
    "subject": "Travel Expense Approval Request",
    "priority": "MEDIUM",
    "recipients": {
      "recipientValues": [
        { "userId": "manager@company.com" }
      ]
    },
    "recipientGroups": {
      "recipientGroupValues": [
        { "groupId": "finance-approvers" }
      ]
    },
    "taskDefinition": {
      "definitionName": "Approve Travel Expense"
    }
  }
}
```

---

### 6. **Recipient Email — Must Be Explicitly Provided by the User**

**NEVER generate, guess, or derive recipient emails from the input payload.**

The recipient email must come from an explicit user instruction in the conversation.
If the user has already provided the recipient email, use that exact value.
If the user has not provided it yet, stop and ask before emitting the Task Center node.

```
❌ WRONG: { userId: "user@example.com" }                          // generated placeholder
❌ WRONG: { userId: "={{ $json.body.email }}" }                   // derived from input payload
❌ WRONG: { userId: "={{ $('Webhook').item.json.requesterEmail }}" } // derived from input payload
✅ RIGHT: Ask the user "Who should receive this approval task? Please provide their email address."
✅ RIGHT: After the user replies, set: { userId: "<the exact email they provided>" }
```

---

### 7. **Post-Decision SAP Actions MUST Use SAP MCP Client**

After the Switch node routes the approval decision, each branch MUST execute the actual SAP action using a `CUSTOM.sapMcpClient` node. A Set node that builds a response object does **NOT** post anything to SAP.

❌ **Wrong — both branches end in Set nodes; nothing was written to SAP:**
```
Switch (approved) → Set Manager Approved { status: "approved" } → Respond
Switch (rejected) → Set Manager Rejected { status: "rejected" } → Respond
```

✅ **Correct — each branch calls SAP before responding:**
```
Switch (approved) → SAP MCP Client (execute SAP approval action) → Respond
Switch (rejected) → SAP MCP Client (execute SAP rejection action) → Respond
```

**Exception:** When the workflow's only purpose is to relay a decision back to the calling system and no SAP write is needed (e.g. a pure notification relay), a Set node before `respondToWebhook` is acceptable for shaping the response payload. But if the user's intent includes recording the decision in SAP, creating a document, updating a record, or triggering a downstream SAP process, that step must be a `CUSTOM.sapMcpClient` node.

---

## Common Errors to Avoid

❌ **ERROR 1:** Missing switch node after Task Center
```
Task Center → Respond to Webhook  // WRONG - no branching
```
✅ **FIX:** Add switch
```
Task Center → Switch → [approved/rejected branches]
```

---

❌ **ERROR 2:** Recipient not explicitly provided by the user
```json
"recipientValues": [{ "userId": "user@example.com" }]                     // WRONG — generated placeholder
"recipientValues": [{ "userId": "={{ $json.body.email }}" }]              // WRONG — bound to input payload
"recipientValues": [{ "userId": "={{ $('Webhook').item.json.email }}" }]  // WRONG — bound to input payload
"recipientGroupValues": [{ "groupId": "finance-approvers" }]              // WRONG — guessed or copied value
```
✅ **FIX:** Stop and ask the user for a recipient email address or group ID (either is fine — see **ALWAYS Ask for the recipient first**).

---

❌ **ERROR 3:** Generic Task Center node name
```json
"name": "SAP Task Center"  // WRONG — unclear to workflow readers and maintainers
```
✅ **FIX:** Rename to reflect the approval purpose, e.g. `"Approve Travel Expense"`.

---

❌ **ERROR 4:** Ending approval/rejection branches with Set nodes instead of SAP MCP Client calls
```
Switch (approved) → Set Manager Approved { status: "approved" } → Respond
```
Nothing was posted to SAP. The approval exists only inside n8n.

✅ **FIX:** Use SAP MCP Client after the Switch to execute the SAP action, then respond:
```
Switch (approved) → SAP MCP Client (post_expense_decision, { decision: "approved" }) → Respond
```

---

## Example: Travel Expense Approval with SAP Task Center

```json
{
  "name": "Travel Expense Approval",
  "description": "Handles travel expense approval requests. Automatically approves expenses below 50 EUR; routes higher amounts to a manager via SAP Task Center for manual approval or rejection. Responds to the requester with the final decision.",
  "nodes": [
    {
      "parameters": {
        "httpMethod": "POST",
        "path": "expense-submitted",
        "responseMode": "responseNode",
        "options": {}
      },
      "id": "f87b684f-c68e-4019-b22e-53a8b75d6cf4",
      "name": "Expense Submitted",
      "type": "n8n-nodes-base.webhook",
      "typeVersion": 2.1,
      "position": [-416, -48],
      "webhookId": "e57d9e77-30a3-4b7f-bad5-1e3288f68617"
    },
    {
      "parameters": {
        "conditions": {
          "options": {
            "caseSensitive": true,
            "leftValue": "",
            "typeValidation": "strict"
          },
          "conditions": [
            {
              "id": "condition1",
              "leftValue": "={{ $json.body.amount }}",
              "rightValue": 50,
              "operator": {
                "type": "number",
                "operation": "lt"
              }
            }
          ],
          "combinator": "and"
        },
        "options": {}
      },
      "id": "1ef04aff-4ebe-45e1-9ebc-05874cb79392",
      "name": "Amount Below 50 EUR?",
      "type": "n8n-nodes-base.if",
      "typeVersion": 2.3,
      "position": [-176, -48]
    },
    {
      "parameters": {
        "assignments": {
          "assignments": [
            { "id": "field1", "name": "status", "value": "approved", "type": "string" },
            { "id": "field2", "name": "message", "value": "=Expense of {{ $('Expense Submitted').item.json.body.amount }} EUR auto-approved (below 50 EUR threshold).", "type": "string" },
            { "id": "field3", "name": "expenseId", "value": "={{ $('Expense Submitted').item.json.body.expenseId }}", "type": "string" }
          ]
        },
        "options": {}
      },
      "id": "4ceabcf2-ae77-4179-a5a0-7d86e38ea32a",
      "name": "Set Auto-Approved",
      "type": "n8n-nodes-base.set",
      "typeVersion": 3.4,
      "position": [416, -192]
    },
    {
      "parameters": {
        "subject": "=Approve Travel Expense for {{ $('Expense Submitted').item.json.body.employeeName }}",
        "priority": "MEDIUM",
        "description": "=Travel expense of {{ $('Expense Submitted').item.json.body.amount }} EUR submitted for approval.",
        "dueDate": "2026-04-30T00:00:00",
        "recipients": {
          "recipientValues": [
            {
              "userId": "manager@company.com"
            }
          ]
        },
        "taskDefinition": {
          "definitionName": "Approve Travel Expense"
        }
      },
      "type": "CUSTOM.sapTaskCenter",
      "typeVersion": 1,
      "position": [192, 48],
      "id": "29656fda-7d54-4279-8362-c034b6085a3c",
      "name": "Approve Travel Expense",
      "webhookId": "515abf90-3602-472a-96e6-4163feeba231"
    },
    {
      "parameters": {
        "rules": {
          "values": [
            {
              "conditions": {
                "options": {
                  "caseSensitive": true,
                  "leftValue": "",
                  "typeValidation": "strict"
                },
                "conditions": [
                  {
                    "leftValue": "={{ $json.result.response }}",
                    "rightValue": "approved",
                    "operator": {
                      "type": "string",
                      "operation": "equals"
                    }
                  }
                ],
                "combinator": "and"
              },
              "renameOutput": true,
              "outputKey": "Approved"
            },
            {
              "conditions": {
                "options": {
                  "caseSensitive": true,
                  "leftValue": "",
                  "typeValidation": "strict"
                },
                "conditions": [
                  {
                    "leftValue": "={{ $json.result.response }}",
                    "rightValue": "rejected",
                    "operator": {
                      "type": "string",
                      "operation": "equals"
                    }
                  }
                ],
                "combinator": "and"
              },
              "renameOutput": true,
              "outputKey": "Rejected"
            }
          ]
        },
        "options": {}
      },
      "type": "n8n-nodes-base.switch",
      "typeVersion": 3.4,
      "position": [416, 48],
      "id": "8c69ea2e-e2a8-4dcb-92d3-28a3b9af0a68",
      "name": "Approval Decision"
    },
    {
      "parameters": {
        "assignments": {
          "assignments": [
            { "id": "field1", "name": "status", "value": "approved", "type": "string" },
            { "id": "field2", "name": "message", "value": "=Expense of {{ $('Expense Submitted').item.json.body.amount }} EUR approved by manager.", "type": "string" },
            { "id": "field3", "name": "expenseId", "value": "={{ $('Expense Submitted').item.json.body.expenseId }}", "type": "string" }
          ]
        },
        "options": {}
      },
      "id": "60bc7ca5-3c6c-4440-b64b-55677c90a05a",
      "name": "Set Manager Approved",
      "type": "n8n-nodes-base.set",
      "typeVersion": 3.4,
      "position": [688, -32]
    },
    {
      "parameters": {
        "assignments": {
          "assignments": [
            { "id": "field1", "name": "status", "value": "rejected", "type": "string" },
            { "id": "field2", "name": "message", "value": "=Expense of {{ $('Expense Submitted').item.json.body.amount }} EUR rejected by manager.", "type": "string" },
            { "id": "field3", "name": "expenseId", "value": "={{ $('Expense Submitted').item.json.body.expenseId }}", "type": "string" }
          ]
        },
        "options": {}
      },
      "id": "39f2460c-6635-41a0-8015-9c8dc072e01e",
      "name": "Set Manager Rejected",
      "type": "n8n-nodes-base.set",
      "typeVersion": 3.4,
      "position": [688, 144]
    },
    {
      "parameters": {
        "respondWith": "json",
        "responseBody": "={{ JSON.stringify({ expenseId: $json.expenseId, status: $json.status, message: $json.message }) }}",
        "options": {
          "responseCode": 200
        }
      },
      "id": "e92a8cbd-de06-42ff-a44b-e461b766f6e2",
      "name": "Respond to Requester",
      "type": "n8n-nodes-base.respondToWebhook",
      "typeVersion": 1.5,
      "position": [1040, -128]
    }
  ],
  "connections": {
    "Expense Submitted": {
      "main": [[{ "node": "Amount Below 50 EUR?", "type": "main", "index": 0 }]]
    },
    "Amount Below 50 EUR?": {
      "main": [
        [{ "node": "Set Auto-Approved", "type": "main", "index": 0 }],
        [{ "node": "Approve Travel Expense", "type": "main", "index": 0 }]
      ]
    },
    "Approve Travel Expense": {
      "main": [
        [{ "node": "Approval Decision", "type": "main", "index": 0 }]
      ]
    },
    "Approval Decision": {
      "main": [
        [{ "node": "Set Manager Approved", "type": "main", "index": 0 }],
        [{ "node": "Set Manager Rejected", "type": "main", "index": 0 }]
      ]
    },
    "Set Auto-Approved": {
      "main": [[{ "node": "Respond to Requester", "type": "main", "index": 0 }]]
    },
    "Set Manager Approved": {
      "main": [[{ "node": "Respond to Requester", "type": "main", "index": 0 }]]
    },
    "Set Manager Rejected": {
      "main": [[{ "node": "Respond to Requester", "type": "main", "index": 0 }]]
    }
  },
  "pinData": {},
  "meta": {
    "templateCredsSetupCompleted": true
  }
}
```

---

## Testing Checklist

Before considering a Task Center workflow complete:

- [ ] Used MCP `search-nodes-catalog` to get typeVersion
- [ ] Task Center node has a contextual canvas `name` describing the approval purpose (not generic `"SAP Task Center"`)
- [ ] `taskDefinition.definitionName` is set — defaults to the node's canvas `name` unless the user specified a different label
- [ ] Task Center node has all mandatory parameters (`subject`, `priority`, at least one recipient or recipient group)
- [ ] Switch node placed immediately after Task Center
- [ ] Switch branches on `$json.result.response`
- [ ] At least one `userId` or `groupId` was explicitly provided by the user in this conversation
- [ ] No placeholder values, payload expressions, or example-derived recipient values are used
- [ ] No `credentials` block included in the workflow JSON — credentials are resolved automatically during deployment
- [ ] Each post-approval/rejection branch uses SAP MCP Client to execute the SAP action
- [ ] Set nodes, if present, are used only for shaping response payloads — not as substitutes for SAP calls
- [ ] Workflow validates with `validate-n8n-workflow` MCP
