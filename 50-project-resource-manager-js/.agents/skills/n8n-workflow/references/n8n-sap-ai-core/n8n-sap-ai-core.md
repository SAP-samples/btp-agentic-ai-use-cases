# n8n SAP AI Core Node and SAP AI Core Chat Model Node Generation Guidelines

> **Prerequisite:** This reference assumes you have already read `execution.md`. All general rules (node catalog lookup, validation, credentials, single-write policy) apply here too.

## Overview

AI Core-specific rules and reference data for generating SAP AI Core nodes in n8n workflows. These nodes bring enterprise-grade LLM capabilities — with content filtering, data masking, and translation — directly into your automation.

**IMPORTANT:** When searching for the AI Core nodes in the catalog, use **only** the exact display names below as your search query — no extra words:
- `SAP AI Core` → finds `CUSTOM.sapOrchestration`
- `SAP AI Core Chat Model` → finds `CUSTOM.sapOrchestrationChatModel`

Adding any extra words (e.g. `"SAP AI Core Orchestration"`, `"SAP AI Core node"`) will return zero results.

**AIM:** Generate correct SAP AI Core node configurations — picking the right node type, model, parameters, and enterprise features — so the workflow connects to SAP's LLM infrastructure without errors.

#### There are Two AI Core Nodes

| Node Type | Display Name | Output Type |  Use Case | Key Features |
|-----------|--------------|----------|--------------|--------------|
| **CUSTOM.sapOrchestration** | SAP AI Core | `main` | Chat completion with enterprise features | Content filtering (Azure Content Safety), Data masking (SAP DPI), translation, multi-modal (image/file), JSON response, message history |
| **CUSTOM.sapOrchestrationChatModel** | SAP AI Core Chat Model | `AiLanguageModel` | Connect to any LangChain-based n8n nodes as a model input | Model selection, content filtering, data masking, translation |

- You cannot use the `CUSTOM.sapOrchestrationChatModel` node independently, it can only be connected to a node which accepts an input type as `AiLanguageModel` - Usually the AI Core Chat Model node is used in connection with langchain based nodes, like - Basic LLM Chain, Question and Answer Chain, Information Extractor, Sentiment Analysis, Text Classifier, Summarization Chain, Guardrails, etc.

- If Chat Trigger is not available in the catalog, for langchain based nodes which support `promptType` parameter, it's value would be `define` only.

- `CUSTOM.sapOrchestration` node having output type as `main` is easily pluggable (without having a dependency on any other node) in the n8n workflow.

---

## AI Core-Specific Rules

### 1. **Fetch supported parameters before generating**

Before generating any SAP AI Core node, call the required tools for knowing the node's supported parameters schema. Use the response as the primary source of truth for supported parameter names.

### 2. **Hidden parameters must not be used**

**IMPORTANT:** After fetching supported node parameters for AI Core nodes, parameters with `type: hidden` **must NOT be used** — these parameters don't have any functional use case from end-user perspective.

---

### 3. **AI Core node structure (`N8nNode`) inside `N8nWorkflow` JSON:**

**Parameter Reference:**

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `modelName` | Yes | - | Resource locator with `__rl: true`, `mode: "list"`. See "Supported Model Names" |
| `userMessage` | Yes | - | The main user prompt/message |
| `systemPrompt` | No | - | System-level instructions for model behavior |
| `messageHistory` | No | - | JSON-encoded conversation history |
| `modelParams` | No | `{}` | Model parameters: `max_tokens` (4096), `temperature` (0.7), `top_p` (1), `frequency_penalty` (0), `presence_penalty` (0) |
| `enableFiltering` | No | false | Enable AI content safety filtering |
| `filteringOptions` | No | - | Requires `enableFiltering: true`. Options: `ALLOW_SAFE`, `ALLOW_SAFE_LOW`, `ALLOW_SAFE_LOW_MEDIUM`, `ALLOW_ALL` |
| `enableMasking` | No | false | Enable sensitive data masking |
| `maskingOptions.method` | No | pseudonymization | `pseudonymization` or `anonymization` |
| `maskingOptions.entities` | No | - | Comma-separated entity types (e.g., `profile-person,profile-email`) |
| `enableFileInput` | No | false | Enable file input to model |
| `fileOptions` | No | - | Requires `enableFileInput: true`. Contains `fileUrl` and `filename` |
| `enableTranslation` | No | false | Enable input/output translation |
| `translationOptions` | No | - | Requires `enableTranslation: true`. See "Supported Translation Language Pairs" |
| `imageUrl` | No | - | Image URL or base64-encoded image |
| `responseFormat` | No | text | `text` or `json_object` |

> **Note:** Some models don't support both `temperature` and `top_p` together - avoid using both unless explicitly required.

> **Masking entities:** `profile-person`, `profile-org`, `profile-university`, `profile-location`, `profile-phone`, `profile-address`, `profile-email`, `profile-sapids-internal`, `profile-sapids-public`, `profile-url`, `profile-username-password`, `profile-nationalid`, `profile-iban`, `profile-ssn`, `profile-credit-card-number`, `profile-passport`, `profile-driverlicense`, `profile-nationality`, `profile-religious-group`, `profile-political-group`, `profile-pronouns-gender`, `profile-gender`, `profile-sexual-orientation`, `profile-trade-union`, `profile-sensitive-data`, `profile-ethnicity`

```jsonc
{
  "nodes": [
    {
      "parameters": {
        "modelName": {
          "__rl": true,
          "value": "MODEL_ID",
          "mode": "list",
          "cachedResultName": "MODEL_DISPLAY_NAME"
        },
        "userMessage": "USER_MESSAGE",
        "systemPrompt": "SYSTEM_PROMPT",
        "messageHistory": "[{\"role\":\"user\",\"content\":\"MESSAGE\"}]",
        "modelParams": {
          "max_tokens": 4096,
          "temperature": 0.7,
          "top_p": 1,
          "frequency_penalty": 0,
          "presence_penalty": 0
        },
        "enableFiltering": true,
        "filteringOptions": {
          "hate": "ALLOW_SAFE",
          "violence": "ALLOW_SAFE",
          "sexual": "ALLOW_SAFE",
          "selfHarm": "ALLOW_SAFE",
          "promptShield": true
        },
        "enableMasking": true,
        "maskingOptions": {
          "method": "pseudonymization",
          "entities": "profile-person,profile-email"
        },
        "enableFileInput": true,
        "fileOptions": {
          "fileUrl": "FILE_URL",
          "filename": "FILE_NAME"
        },
        "enableTranslation": true,
        "translationOptions": {
          "inputSourceLanguage": "en-US",
          "inputTargetLanguage": "en-US",
          "outputSourceLanguage": "en-US",
          "outputTargetLanguage": "de-DE"
        },
        "imageUrl": "IMAGE_URL_OR_BASE64_URL",
        "responseFormat": "json_object"
      },
      "type": "CUSTOM.sapOrchestration",
      "typeVersion": 1,
      "position": [1280, 800],
      "id": "NODE_UUID",
      "name": "SAP AI Core"
    }
  ]
}
```

**Output Structure:**

The SAP AI Core node outputs the LLM response in the `output` field:
```json
{
  "output": "LLM response text here"
}
```

When `responseFormat: "json_object"` is used, the `output` field contains the **stringified JSON** (not a parsed object):

> **Important:** When using `responseFormat: "json_object"`, always include the word **"JSON"** somewhere in the `userMessage` or `systemPrompt`. Failing to do so may cause the model to error or return unexpected output.
```json
{
  "output": "{\"key\": \"value\", \"items\": [1, 2, 3]}"
}
```

To use the JSON response in subsequent nodes, parse it with `JSON.parse($json.output)` or use an expression like `{{ JSON.parse($json.output).key }}`.

#### When to Use Each Node

**For LLM Operations:**
- Use **SAP AI Core** (`sapOrchestration`) main node for direct chat completion with enterprise features.
- Use **SAP AI Core Chat Model** (`sapOrchestrationChatModel`) sub-node when connecting to LangChain-based n8n nodes (e.g., Basic LLM Chain, Question and Answer Chain, Information Extractor, Sentiment Analysis, Text Classifier, Summarization Chain, Guardrails, etc).

---

## **SAP AI Core Chat Model - sapOrchestrationChatModel**

SAP AI Core Chat Model (`CUSTOM.sapOrchestrationChatModel`) is a different version of the AI Core node seen above, with limited functionalities exposed as a Chat Model which can be connected to LangChain based nodes within n8n.

**Note:** The Chat Model node uses `options` instead of `modelParams`, with camelCase keys (`maxTokens`, `topP`, `frequencyPenalty`, `presencePenalty`).

```json
{
  "nodes": [
    {
      "parameters": {
        "modelName": {
          "__rl": true,
          "value": "MODEL_ID",
          "mode": "list",
          "cachedResultName": "MODEL_DISPLAY_NAME"
        },
        "options": {
          "maxTokens": 4096,
          "temperature": 0.7,
          "topP": 1,
          "frequencyPenalty": 0,
          "presencePenalty": 0,
          "maxRetries": 2,
          "responseFormat": "json_object"
        },
        "enableFiltering": true,
        "filteringOptions": {
          "hate": "ALLOW_SAFE",
          "violence": "ALLOW_SAFE",
          "sexual": "ALLOW_SAFE",
          "selfHarm": "ALLOW_SAFE"
        },
        "enableTranslation": true,
        "translationOptions": {
          "inputSourceLanguage": "en-US",
          "inputTargetLanguage": "en-US",
          "outputSourceLanguage": "en-US",
          "outputTargetLanguage": "de-DE"
        },
        "enableMasking": true,
        "maskingOptions": {
          "method": "pseudonymization",
          "entities": "profile-person,profile-email"
        }
      },
      "type": "CUSTOM.sapOrchestrationChatModel",
      "typeVersion": 1,
      "position": [-192, -160],
      "id": "NODE_UUID",
      "name": "SAP AI Core Chat Model"
    }
  ]
}
```

**Output Structure:** When the SAP AI Core Chat Model is connected to LangChain-based nodes, the output structure is governed by the connected node.

---

## Supported Model Names

Use the `modelName` resource locator with values from the table below. Format: `"value": "<model-value>", "cachedResultName": "<display-name>"`

| Model Value | Display Name | Use Case | Supported Parameters |
|-------------|--------------|----------|----------------------|
| `gpt-4.1` | GPT-4.1 | Fast/light tasks | `max_tokens`, `temperature`, `top_p`, `frequency_penalty`, `presence_penalty`, `image_input` |
| `anthropic--claude-4.6-sonnet` | Claude 4.6 Sonnet | General chat, balanced | `max_tokens`, `temperature`, `top_p` ¹, `frequency_penalty`, `presence_penalty`, `image_input`, `file_input` |
| `anthropic--claude-4.8-opus` | Claude 4.8 Opus | Complex reasoning + Code generation | `max_tokens`, `frequency_penalty`, `presence_penalty`, `image_input`, `file_input` |
| `gpt-5` | GPT-5 | General chat, balanced | `max_tokens`, `image_input` |
| `gpt-5-mini` | GPT-5-Mini | Fast responses | `max_tokens`, `image_input` |
| `gpt-5-nano` | GPT-5-Nano | Cost-sensitive | `max_tokens`, `image_input` |
| `o3` | O3 | Complex reasoning | `max_tokens`, `image_input` |
| `gemini-2.5-pro` | Gemini 2.5 Pro | Document analysis, long context | `max_tokens`, `temperature`, `top_p`, `frequency_penalty`, `presence_penalty`, `image_input`, `file_input` |
| `gemini-3.6-flash` | Gemini 3.6 Flash | Fast responses | `max_tokens`, `temperature`, `top_p`, `image_input`, `file_input` |
| `amazon--nova-micro` | Nova Micro | Cost-sensitive | `max_tokens`, `temperature`, `top_p` ¹, `image_input` |

> ¹ `temperature` and `top_p` cannot be used together — use one or the other.


---

## Supported Translation Language Codes

Language codes follow [BCP 47 / IETF language tags](https://en.wikipedia.org/wiki/IETF_language_tag) format (ISO 639-1 language + ISO 3166-1 country).

**Supported codes:**

`ar-SA`, `bg-BG`, `ca-ES`, `cs-CZ`, `da-DK`, `de-DE`, `el-GR`, `en-US`, `es-ES`, `et-EE`, `fi-FI`, `fr-FR`, `he-IL`, `hi-IN`, `hr-HR`, `hu-HU`, `id-ID`, `it-IT`, `ja-JP`, `kk-KZ`, `ko-KR`, `lt-LT`, `lv-LV`, `ms-MY`, `nb-NO`, `nl-NL`, `pl-PL`, `pt-BR`, `ro-RO`, `ru-RU`, `sk-SK`, `sl-SI`, `sr-Latn-RS`, `sv-SE`, `th-TH`, `tr-TR`, `uk-UA`, `vi-VN`, `zh-CN`, `zh-TW`

**Translation routing:**
- `en-US` acts as the hub — all codes translate to/from English
- `de-DE` has direct pairs with: `bg-BG`, `zh-CN`, `hr-HR`, `cs-CZ`, `en-US`, `fr-FR`, `hu-HU`, `it-IT`, `pl-PL`, `ro-RO`, `ru-RU`, `sr-Latn-RS`, `sk-SK`, `sl-SI`, `es-ES`
- Other language pairs require English as an intermediate step

**Example: Japanese → German (via English bridge)**

```json
"enableTranslation": true,
"translationOptions": {
  "inputSourceLanguage": "ja-JP",
  "inputTargetLanguage": "en-US",
  "outputSourceLanguage": "en-US",
  "outputTargetLanguage": "de-DE"
}
```

---

## SAP AI Core Chat Model with LangChain

The Chat Model node connects to LangChain-based nodes. Before generating the connected LangChain node, you **must**:

1. **Fetch the full parameter schema** of the LangChain node (e.g. `@n8n/n8n-nodes-langchain.chainLlm`, `@n8n/n8n-nodes-langchain.informationExtractor`, etc.) by calling `search-nodes-catalog` with the node type.
2. **Use only parameters present in the schema** — do not invent or assume parameter names.
3. **Respect supported values** for each parameter — e.g. valid `promptType` options (`auto`, `define`), correct `messages` structure, valid output parser types, etc. Use the schema as the source of truth.
4. **Wire the `ai_languageModel` connection correctly** — the Chat Model node must be listed under `connections` with type `ai_languageModel`, not `main`.

```json
{
  "nodes": [
    {
      "parameters": {
        "modelName": {
          "__rl": true,
          "value": "anthropic--claude-4.5-haiku",
          "mode": "list",
          "cachedResultName": "Claude 4.5 Haiku"
        },
        "options": {}
      },
      "type": "CUSTOM.sapOrchestrationChatModel",
      "typeVersion": 1,
      "position": [-368, 208],
      "id": "UUID_1",
      "name": "SAP AI Core Chat Model"
    },
    {
      "parameters": {
        "promptType": "define",
        "text": "={{ $json.userMessage }}",
        "messages": { "messageValues": [] },
        "batching": {}
      },
      "type": "@n8n/n8n-nodes-langchain.chainLlm",
      "typeVersion": 1.9,
      "position": [-480, 0],
      "id": "UUID_2",
      "name": "Basic LLM Chain"
    }
  ],
  // connection between the AI Core Chat model and LangChain based node is important.
  "connections": {
    "SAP AI Core Chat Model": {
      "ai_languageModel": [[{ "node": "Basic LLM Chain", "type": "ai_languageModel", "index": 0 }]]
    }
  }
}
```

---

## Common Errors to Avoid

❌ **ERROR 1:** Wrong parameter names
```json
{
  "parameters": {
    "prompt": "Hello",           // WRONG - use "userMessage"
    "model": "gpt-4",            // WRONG - use "modelName" with resource locator
    "systemMessage": "...",      // WRONG - use "systemPrompt"
    "temperature": 0.7           // WRONG for sapOrchestration - use modelParams.temperature
  }
}
```

✅ **FIX:** Refer correct parameter names from the Node Definition, fetched by calling relevant mcp tools.

---


## AI Core-Specific Checklist

Before considering SAP AI Core nodes complete (general rules from `execution.md` still apply):

- [ ] Selected correct SAP AI Core node type:
  - **SAP AI Core** (`sapOrchestration`) for main chat operations
  - **SAP AI Core Chat Model** (`sapOrchestrationChatModel`) for LangChain-based node connections
- [ ] All mandatory parameters provided:
  - For `sapOrchestration`: `userMessage`, `modelName`
  - For `sapOrchestrationChatModel`: `modelName`
- [ ] `modelName` uses resource locator format with `__rl: true`
- [ ] Enterprise features configured correctly if needed:
  - `enableFiltering` + `filteringOptions` (with threshold strings like `ALLOW_SAFE`)
  - `enableMasking` + `maskingOptions` (with `method` and `entities`)
  - `enableTranslation` + `translationOptions`
