# n8n Workflow Hooks Reference

This reference covers how to build n8n workflows that act as **pre/post hooks** in an A2A (Agent-to-Agent) pipeline for agent extension scenarios. Every hook workflow is triggered via an HTTP webhook (carrying an A2A message) and ends with a "Respond to Webhook" node. Between those two endpoints any number of intermediate nodes may appear.

All general steps (project setup, node catalog lookup, file creation, validation) from the parent skill still apply. This reference only adds hook-specific rules and examples.

> **⚠️ Important:** The examples below are illustrative templates only. Do NOT copy hardcoded values (IDs, webhook paths, names, message text, etc.) verbatim into generated workflows. Always derive values dynamically from the incoming request at runtime and generate fresh UUIDs, paths, and node names based on the guidelines and rules specified in this document, appropriate to the specific hook being built.

---

## A2A Message Protocol

### Incoming request structure
The webhook receives an n8n input item where the A2A message is in `body`:

```json
{
  "headers": {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream"
  },
  "query": {},
  "body": {
    "contextId": "18c5baef-01cd-4950-a439-2dc2a11cc9e2",
    "kind": "message",
    "messageId": "123",
    "parts": [
      {
        "kind": "text",
        "text": "What do you do?"
      }
    ],
    "role": "user",
    "taskId": "e5c2b27c-9665-4c33-938e-ce67293e7983"
  }
}
```

**Accessing parts of the incoming message inside n8n nodes:**

| What you need | n8n expression |
|---|---|
| Text of part at index N | `$input.first().json.body.parts[N].text` |
| Message ID | `$input.first().json.body.messageId` |
| All parts array | `$input.first().json.body.parts` |
| Role | `$input.first().json.body.role` |

> The index `N` depends on which part the hook needs — use `0` for the first part, `1` for the second, etc. Inspect the incoming A2A message to determine the correct index.

> When referencing the webhook input from a **later** node (not immediately after the webhook), use the webhook node's name instead of `$input`, e.g. `$('Webhook').first().json.body.parts[N].text`.

### Outgoing response structure (MANDATORY for all hook workflows)
For hook workflows, the "Respond to Webhook" node **MUST ALWAYS** return a valid A2A message object. Returning an empty response or a non-A2A payload is not allowed. The response body must be a JSON object with `messageId`, `role`, and `parts`:

```json
{
  "messageId": "msg-response-001",
  "role": "user",
  "parts": [
    {
      "kind": "text",
      "text": "<content to inject back into the agent context>"
    }
  ]
}
```

Build this inside a **Code (JavaScript)** node and pass its output to the "Respond to Webhook" node, OR build it inline in the "Respond to Webhook" `responseBody` using n8n expressions.

The `parts` array may contain any valid A2A part kind (`text`, `data`, `file`, etc.) — it is not limited to text parts.

If your hook has no extra content to return, still return a valid A2A message with an empty `parts` array:

```json
{
  "messageId": "msg-response-001",
  "role": "agent",
  "parts": []
}
```

### Short-circuiting agent execution from a hook
If a hook decides the agent should stop immediately (no further processing), return a normal A2A message plus `metadata.stop_execution: true`.

**Example response (template):**

```javascript
return {
  messageId: incomingMessageId,
  role: "agent",
  parts: [],
  metadata: {
    stop_execution: true,
    stop_execution_reason: "Policy blocked this request"
  }
};
```

Notes:
- Set `metadata.stop_execution` to `true` **only** when you explicitly want to short-circuit execution.
- `stop_execution_reason` should be a clear, contextual reason string and may vary by condition.
- When no content needs to be returned alongside the stop signal, use `parts: []`.

### Side-effect-only hooks still return A2A
If the hook is purely a side-effect hook (e.g. logging, sending a notification, writing to a database), it still **must** return a valid A2A message. Use an empty `parts` array (`parts: []`) if you do not need to add content.

---

## Hook-specific node parameter rules

In addition to the general node parameter rules from the parent skill, these rules apply specifically to hook workflows:

- **Webhook `responseMode` MUST be `"responseNode"`** for all hook workflows. This ensures the "Respond to Webhook" node controls the response.
- **Always connect every execution path to a "Respond to Webhook" node** — every branch must terminate at a respond node, otherwise the hook will hang.

---

## Examples

### Example 1 — Pre-hook that returns an A2A message (fetches context to inject)

This is the most common pre-hook pattern. The workflow receives an A2A message, performs some work (here: build a weather context string), and responds with a new A2A message whose `text` part will be injected back into the agent context.

```json
{
  "name": "pre_fetch_weather_context",
  "description": "Pre-hook: fetches current date and city, builds a weather context prompt as an A2A message, and returns it to the agent pipeline.",
  "nodes": [
    {
      "parameters": {
        "httpMethod": "POST",
        "path": "fetch-weather-context",
        "responseMode": "responseNode",
        "options": {}
      },
      "type": "n8n-nodes-base.webhook",
      "typeVersion": 2.1,
      "position": [-80, 0],
      "id": "c1239fb2-f1cb-40aa-a902-fa904a0c89de",
      "name": "Webhook",
      "webhookId": "c5280f6d-8b33-46db-b1ec-dea79bf09b79"
    },
    {
      "parameters": {
        "jsCode": "const date = new Date();\nconst city = \"Bangalore\";\nconst incomingMessageId = $input.first().json.body.messageId ?? ('hook-' + Date.now());\n\nreturn {\n  messageId: incomingMessageId,\n  role: \"user\",\n  parts: [\n    {\n      kind: \"text\",\n      text: `Fetch the weather for ${city} for the date ${date}`\n    }\n  ]\n};"
      },
      "type": "n8n-nodes-base.code",
      "typeVersion": 2,
      "position": [112, 0],
      "id": "9e769779-92c6-4175-bcd9-e1f5d12ee2e8",
      "name": "Build A2A Response"
    },
    {
      "parameters": {
        "options": {}
      },
      "type": "n8n-nodes-base.respondToWebhook",
      "typeVersion": 1.5,
      "position": [320, 0],
      "id": "4ee06a97-fb74-44cd-9a06-6aeba942766b",
      "name": "Respond to Webhook"
    }
  ],
  "connections": {
    "Webhook": {
      "main": [[{ "node": "Build A2A Response", "type": "main", "index": 0 }]]
    },
    "Build A2A Response": {
      "main": [[{ "node": "Respond to Webhook", "type": "main", "index": 0 }]]
    }
  },
  "pinData": {},
  "active": true,
  "settings": {
    "executionOrder": "v1"
  }
}
```

**Key points:**
- The Code node returns a plain JS object (not wrapped in `json:`). n8n serialises this as the response body.
- The returned object IS the A2A message (`messageId`, `role`, `parts`). The agent runtime wraps it as needed.
- **Always read `messageId` dynamically** from the incoming request (`$input.first().json.body.messageId`). Never hardcode it.
- `responseMode: "responseNode"` on the Webhook is mandatory — do not omit it.

---

### Example 2 — Post-hook that reads from the agent's response A2A message

When a post-hook needs to process the agent's answer (e.g. to reformat, validate, or transform it before it reaches the caller), it reads from the incoming A2A message — which in this case carries the agent's response — and returns a modified A2A message.

For post-hooks, read the **last part** of the incoming A2A message using `parts[parts.length - 1]`. The target part may be `text`, `data`, or another kind — do not assume text-only.

```json
{
  "name": "post_format_agent_response",
  "description": "Post-hook: reads the agent's response text from the incoming A2A message, appends a disclaimer, and returns a new A2A message with the formatted text.",
  "nodes": [
    {
      "parameters": {
        "httpMethod": "POST",
        "path": "format-agent-response",
        "responseMode": "responseNode",
        "options": {}
      },
      "type": "n8n-nodes-base.webhook",
      "typeVersion": 2.1,
      "position": [-80, 0],
      "id": "aaaa0001-0000-0000-0000-000000000001",
      "name": "Webhook",
      "webhookId": "a1b2c3d4-0000-0000-0000-111122223333"
    },
    {
      "parameters": {
        "jsCode": "const parts = $input.first().json.body.parts ?? [];\nconst responsePart = parts.length > 0 ? parts[parts.length - 1] : null;\n\nlet responseText;\nif (!responsePart) {\n  responseText = '';\n} else if (responsePart.kind === 'text') {\n  responseText = responsePart.text ?? '';\n} else if (responsePart.kind === 'data') {\n  responseText = JSON.stringify(responsePart.data ?? {});\n} else {\n  responseText = JSON.stringify(responsePart);\n}\n\nconst incomingMessageId = $input.first().json.body.messageId ?? ('formatted-' + Date.now());\n\nreturn {\n  messageId: incomingMessageId,\n  role: 'agent',\n  parts: [\n    {\n      kind: 'text',\n      text: responseText + '\\n\\n_This response was generated by an AI and may contain inaccuracies._'\n    }\n  ]\n};"
      },
      "type": "n8n-nodes-base.code",
      "typeVersion": 2,
      "position": [112, 0],
      "id": "aaaa0002-0000-0000-0000-000000000002",
      "name": "Format Response"
    },
    {
      "parameters": {
        "options": {}
      },
      "type": "n8n-nodes-base.respondToWebhook",
      "typeVersion": 1.5,
      "position": [320, 0],
      "id": "aaaa0003-0000-0000-0000-000000000003",
      "name": "Respond to Webhook"
    }
  ],
  "connections": {
    "Webhook": {
      "main": [[{ "node": "Format Response", "type": "main", "index": 0 }]]
    },
    "Format Response": {
      "main": [[{ "node": "Respond to Webhook", "type": "main", "index": 0 }]]
    }
  },
  "pinData": {},
  "active": true,
  "settings": {
    "executionOrder": "v1"
  }
}
```

**Key points:**
- Post-hooks read the **last part** of `$input.first().json.body.parts` using `parts[parts.length - 1]`. This is robust regardless of how many parts the incoming message contains.
- The target part is not always text — branch by `kind` (`text`, `data`, or others) before reading the value.
- Preserve `messageId` dynamically from the incoming body when available (e.g. `$input.first().json.body.messageId`).

---

### Example 3 — Post-hook with side effects and minimal A2A return

When the hook only needs to perform a side effect (log, notify, store), it still returns a valid A2A message. A common pattern is to return the same incoming `messageId` with an empty text part.

```json
{
  "name": "post_log_result",
  "description": "Post-hook: logs the agent's final answer to an external system and returns a minimal valid A2A message with an empty text part.",
  "nodes": [
    {
      "parameters": {
        "httpMethod": "POST",
        "path": "log-result",
        "responseMode": "responseNode",
        "options": {}
      },
      "type": "n8n-nodes-base.webhook",
      "typeVersion": 2.1,
      "position": [-80, 0],
      "id": "bbbb0001-0000-0000-0000-000000000001",
      "name": "Webhook",
      "webhookId": "b9f1e2a3-cccc-dddd-eeee-ffff00001111"
    },
    {
      "parameters": {
        "method": "POST",
        "url": "https://my-logging-service.example.com/log",
        "sendBody": true,
        "bodyParameters": {
          "parameters": [
            {
              "name": "message",
              "value": "={{ $('Webhook').first().json.body.parts[0].text }}"
            }
          ]
        },
        "options": {}
      },
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.2,
      "position": [112, 0],
      "id": "bbbb0002-0000-0000-0000-000000000002",
      "name": "Log to External Service"
    },
    {
      "parameters": {
        "jsCode": "const incomingMessageId = $input.first().json.body.messageId ?? ('post-log-' + Date.now());\n\nreturn {\n  messageId: incomingMessageId,\n  role: 'agent',\n  parts: []\n};"
      },
      "type": "n8n-nodes-base.code",
      "typeVersion": 2,
      "position": [320, 0],
      "id": "bbbb0003-0000-0000-0000-000000000003",
      "name": "Build Minimal A2A Response"
    },
    {
      "parameters": {
        "options": {}
      },
      "type": "n8n-nodes-base.respondToWebhook",
      "typeVersion": 1.5,
      "position": [560, 0],
      "id": "bbbb0004-0000-0000-0000-000000000004",
      "name": "Respond to Webhook"
    }
  ],
  "connections": {
    "Webhook": {
      "main": [[{ "node": "Log to External Service", "type": "main", "index": 0 }]]
    },
    "Log to External Service": {
      "main": [[{ "node": "Build Minimal A2A Response", "type": "main", "index": 0 }]]
    },
    "Build Minimal A2A Response": {
      "main": [[{ "node": "Respond to Webhook", "type": "main", "index": 0 }]]
    }
  },
  "pinData": {},
  "active": true,
  "settings": {
    "executionOrder": "v1"
  }
}
```

**Key points:**
- Side-effect-only hooks still return a valid A2A message; this example returns an empty `parts` array.
- Notice how the webhook input is referenced as `$('Webhook').first().json...` in a downstream node (not `$input`).

---

### Example 4 — Pre-hook with conditional branching that always returns an A2A message

When the workflow branches (e.g. with an IF node), every branch **must** end at the "Respond to Webhook" node, and each branch must return a valid A2A message.

```json
{
  "name": "pre_conditional_context",
  "description": "Pre-hook: checks if the user's query mentions a city; if yes, adds today's date context; if no, returns a clarification prompt. Always returns an A2A message.",
  "nodes": [
    {
      "parameters": {
        "httpMethod": "POST",
        "path": "conditional-context",
        "responseMode": "responseNode",
        "options": {}
      },
      "type": "n8n-nodes-base.webhook",
      "typeVersion": 2.1,
      "position": [-300, 0],
      "id": "cccc0001-0000-0000-0000-000000000001",
      "name": "Webhook",
      "webhookId": "d4e5f6a7-1111-2222-3333-444455556666"
    },
    {
      "parameters": {
        "conditions": {
          "options": { "caseSensitive": false, "leftValue": "", "typeValidation": "strict" },
          "conditions": [
            {
              "id": "cond1",
              "leftValue": "={{ $json.body.parts[0].text }}",
              "rightValue": "bangalore",
              "operator": { "type": "string", "operation": "contains" }
            }
          ],
          "combinator": "and"
        },
        "options": {}
      },
      "type": "n8n-nodes-base.if",
      "typeVersion": 2.3,
      "position": [-80, 0],
      "id": "cccc0002-0000-0000-0000-000000000002",
      "name": "Mentions City?"
    },
    {
      "parameters": {
        "jsCode": "const today = new Date().toISOString().split('T')[0];\nreturn {\n  messageId: \"ctx-\" + Date.now(),\n  role: \"user\",\n  parts: [{ kind: \"text\", text: `Today is ${today}. Please answer for Bangalore.` }]\n};"
      },
      "type": "n8n-nodes-base.code",
      "typeVersion": 2,
      "position": [140, -80],
      "id": "cccc0003-0000-0000-0000-000000000003",
      "name": "Add Date Context"
    },
    {
      "parameters": {
        "jsCode": "return {\n  messageId: \"clarify-\" + Date.now(),\n  role: \"user\",\n  parts: [{ kind: \"text\", text: \"Please specify a city in your query.\" }]\n};"
      },
      "type": "n8n-nodes-base.code",
      "typeVersion": 2,
      "position": [140, 80],
      "id": "cccc0004-0000-0000-0000-000000000004",
      "name": "Ask for City"
    },
    {
      "parameters": {
        "options": {}
      },
      "type": "n8n-nodes-base.respondToWebhook",
      "typeVersion": 1.5,
      "position": [380, 0],
      "id": "cccc0005-0000-0000-0000-000000000005",
      "name": "Respond to Webhook"
    }
  ],
  "connections": {
    "Webhook": {
      "main": [[{ "node": "Mentions City?", "type": "main", "index": 0 }]]
    },
    "Mentions City?": {
      "main": [
        [{ "node": "Add Date Context", "type": "main", "index": 0 }],
        [{ "node": "Ask for City", "type": "main", "index": 0 }]
      ]
    },
    "Add Date Context": {
      "main": [[{ "node": "Respond to Webhook", "type": "main", "index": 0 }]]
    },
    "Ask for City": {
      "main": [[{ "node": "Respond to Webhook", "type": "main", "index": 0 }]]
    }
  },
  "pinData": {},
  "active": true,
  "settings": {
    "executionOrder": "v1"
  }
}
```

---

## Quick-reference: choosing the right response pattern

| Hook purpose | Response pattern |
|---|---|
| Inject context / enrich the prompt | Return A2A message from Code node (Examples 1 & 2) |
| Transform or rewrite the user message | Return A2A message with modified `parts[0].text` |
| Side-effect only (log, notify, write DB) | Return minimal A2A message with `parts: []` (Example 3) |
| Conditional — may enrich or redirect | All branches return A2A message (Example 4) |
| Fetch external data and surface it | HTTP Request → Code node builds A2A message → Respond |

````
