---
name: mcp-mock-config
description: Generate mcp-mock.json from agent specifications (translation.json, serverCard.json, or mcp-spec-*.json). Use when user wants to "generate mcp mock config", "create mcp-mock.json", "mock MCP tools/server responses", "set up deterministic test data", or "test agent without real MCP servers".
metadata:
  version: 1.0.0
  author: sap-joule-studio
---

Generates a single `mcp-mock.json` from agent MCP specifications. Two input paths:

- **Path A — New MCP servers**: reads `translation.json` (and optionally `serverCard.json`) produced by the `mcp-translation-file` skill for APIs that don't yet have an MCP server
- **Path B — Existing MCP servers**: reads `mcp-spec-<server>-<tool>.json` files discovered during the specification phase via `get_mcp_tool_details` (these servers are referenced by ORD ID in the agent's asset YAML and require no creation process)

Both paths produce the same `mcp-mock.json` format, and both can be combined in a single run.

## Prerequisites

- **Ordering constraint:** This skill MUST be invoked AFTER `mcp-translation-file` and `setup-solution` have completed (for Path A). The required chain is: `mcp-translation-file` → `setup-solution` → `mcp-mock-config`. Never invoke this skill before the translation files and MCP server assets exist. **Exception:** If `mcp-translation-file` is unavailable in the environment and was skipped, Path A does not apply — invoke this skill using only Path B inputs (existing MCP specs). If neither Path A nor Path B inputs exist, skip this skill entirely.
- Agent project directory with MCP tool specifications
- At least one specification file from either path:
  - **Path A**: `translation.json` — tool names, descriptions, parameters (one per new MCP server asset)
  - **Path B**: `specification/<asset-name>/mcp-specs/mcp-spec-<server>-<tool>.json` — one file per tool, from existing/discovered MCP servers

## Inputs

**Path A — New MCP server (translation.json / serverCard.json):**
- `translation.json` containing:
  - `serverInfo`: name, description, version
  - `tools[]`: name, description, parameters, openApiType
- `serverCard.json` (optional) — Similar to `translation.json`, but with richer schema details. Some metadata is stored at the root level, while tools remain nested. When available, use it alongside `translation.json` for more accurate mock response generation.

**Path B — Existing MCP server (mcp-spec-*.json):**
- `specification/<asset-name>/mcp-specs/mcp-spec-<server>-<tool>.json` files, one per tool, containing:
  - `name` — tool name
  - `description` — tool description
  - `inputSchema` — JSON Schema for input parameters
  - `outputSchema` (optional) — JSON Schema for response structure

The `<server>` part of the filename is the server slug; all tools sharing the same server slug are grouped into one server entry in `mcp-mock.json`.

**Optional for both paths:**
- Custom mock value overrides from user

**Input Assumptions:**
- `translation.json` follows SAP's translation file format / specification
- `serverCard.json` follows standard MCP Server Card specification (if present)
- `mcp-spec-*.json` files contain full tool details as returned by `get_mcp_tool_details`
- Parameters with `"deactivate": true` should be excluded (Path A only)

## Output

**Primary Artifact:** Single `mcp-mock.json` file

**Structure (servers and tools as hashmaps for O(1) lookup):**
```json
{
  "servers": {
    "server-slug-1": {
      "mcp_server_name": "full.server.name/API_NAME",
      "description": "Server description",
      "tools": {
        "tool_name_1": {
          "description": "tool description",
          "input_schema": { ... },
          "mock_response": { ... }
        },
        "tool_name_2": {
          "description": "tool description",
          "input_schema": { ... },
          "mock_response": { ... }
        }
      }
    },
    "server-slug-2": {
      "mcp_server_name": "another-server",
      "description": "Another server description",
      "tools": {
        "tool_name_3": { ... }
      }
    }
  },
  "metadata": {
    "version": "1.0.0",
    "created_for_agent": "agent-name",
    "mock_mode": true,
    "deterministic": true,
    "total_servers": 2,
    "total_tools": 3,
    "generated_from": ["translation.json", "serverCard.json", "mcp-spec-*.json"],
    "generation_date": "YYYY-MM-DD"
  }
}
```

**Key Design Decisions:**
- **Single file**: One `mcp-mock.json` for the entire agent
- **Servers as hashmap**: `servers` is an object keyed by server slug for O(1) lookup
- **Tools as hashmap**: `tools` within each server is an object keyed by tool name for O(1) lookup
- **Double O(1) lookup**: `mockData.servers["server-slug"].tools["tool-name"]`

**Done Criteria:**
- [ ] Single `mcp-mock.json` created in agent directory
- [ ] All servers stored as hashmap (object, not array)
- [ ] All tools within each server stored as hashmap
- [ ] All tools from all `translation.json` files included
- [ ] Mock responses match expected schema structure
- [ ] JSON is valid (parseable)
- [ ] No agent code modified

## Workflow

### Step 1: Discover Specification Files

**Actions:**
1. Search for specification files from both paths:
   - **Path A**: `assets/**/translation.json`, `assets/**/serverCard.json`
   - **Path B**: `specification/**/mcp-specs/mcp-spec-*.json`
2. For each `translation.json` found (Path A), extract:
   - `serverInfo.name` → server key (slugified)
   - `serverInfo.description` → description
   - `tools[]` array
3. For each `mcp-spec-<server>-<tool>.json` found (Path B), extract:
   - Server slug from filename: `mcp-spec-<server>-<tool>.json` → `<server>`
   - Tool entry from file content: `name`, `description`, `inputSchema`, `outputSchema`
   - Group all tools with the same `<server>` slug into one server entry
4. Index all `serverCard.json` files by server slug for fast lookup in Step 2.

**Validation:**
- At least one `translation.json` (Path A) OR at least one `mcp-spec-*.json` (Path B) found
- Path A: each `translation.json` has `serverInfo` section and `tools` array with at least one entry
- Path B: each `mcp-spec-*.json` has `name` and `description` fields

**If validation fails:** Ask user for specification file location

### Step 2: Extract Tool Schemas

**Path A — translation.json tools:**

1. For each server's `tools[]`:
   - Extract `name`, `description`, `title`
   - Extract `parameters[]` (filter out `deactivate: true`)
   - Note `openApiType.path` for schema lookup

2. Build `input_schema` from parameters:
   ```json
   {
     "type": "object",
     "properties": {
       "param_name": {
         "type": "string",
         "description": "param description"
       }
     },
     "required": []
   }
   ```

3. Resolve response schema from the **best available source** (in priority order):
   - **`serverCard.json`**
      — Use `inputSchema` directly as `input_schema` — no transformation needed
      — Use `outputSchema` (if present) to drive mock response generation in Step 3
   - **`translation.json` parameters only** — fallback when no external schema exists

**Path B — mcp-spec-*.json tools:**

1. For each `mcp-spec-<server>-<tool>.json` file:
   - Use `inputSchema` directly as `input_schema` — no transformation needed
   - Use `outputSchema` (if present) to drive mock response generation in Step 3
   - Use `name` and `description` directly
2. Derive server `mcp_server_name` from the `<server>` slug by reversing slug rules (or use a `serverInfo` field if present in any of the grouped files)

**Validation:**
- All tools have name and description
- Input schemas present for all tools
- Schema source recorded per tool (for `generated_from` metadata)

### Step 3: Generate Mock Responses

**Actions:**
1. For each tool, generate mock response based on the best available schema source:
   - **Path A**: response schema from `serverCard.json` → type mapping rules → fallback to parameter types
   - **Path B**: `outputSchema` from `mcp-spec-*.json` → type mapping rules → fallback to empty object

2. Apply type-specific mock values (see `references/type-mapping.md` and `references/sap-odata-patterns.md`):
   - `string` → field-appropriate value
   - `string` + `format: decimal` → `"75000.00"`
   - `string` + date example → `/Date(timestamp)/`
   - `integer` → reasonable number
   - `array` → 1-2 mock items with full structure
   - `object` → nested mock structure

3. Determine response wrapper:
   - **Path A**: list operations (path ends without key parameter) → wrap in `{"results": [...]}` with 2 items; single-entity → return single object
   - **Path B**: infer from tool name prefix (`list_`, `get_`, `create_`, etc.) — `list_*` → wrap in `{"results": [...]}` with 2 items; others → single object

**Validation:**
- Mock response has all required fields from schema
- Data types match schema definitions
- Arrays have at least one item

### Step 4: Write mcp-mock.json

**Actions:**
1. Build unified structure merging servers from both Path A and Path B
2. Generate server slugs:
   - **Path A** — from `serverInfo.name`: `com.sap.s4/API_SUPPLIERINVOICE_PROCESS_SRV` → `s4-supplier-invoice`
   - **Path B** — from filename `<server>` part: already a slug, use as-is
3. Add metadata with totals; set `generated_from` to list the actual source files used
4. Write single `mcp-mock.json` file to agent root
5. Validate JSON syntax

**Slug Generation Rules (Path A):**
- Remove common prefixes (`com.sap.`, `API_`, etc.)
- Extract meaningful name
- Convert to kebab-case
- Ensure uniqueness (append numeric suffix on collision)

**Validation:**
- File created at agent root
- JSON is valid (can be parsed)
- Confirm before overwriting existing file

## References

Domain-specific patterns are in the `references/` folder:
- `references/output-schema.json` - JSON schema for mcp-mock.json validation
- `references/type-mapping.md` - OpenAPI type to mock value rules
- `references/sap-odata-patterns.md` - SAP-specific mock patterns

## Guardrails

### Communication Guidelines

- Report discovered specification files before proceeding
- Show number of servers and tools found for confirmation
- Display output file location when complete
- Ask before overwriting existing mcp-mock.json

### Safety Guardrails

**CRITICAL - This skill MUST NOT:**
- ❌ Modify any agent code (agent.py, tools.py, main.py)
- ❌ Edit translation.json, serverCard.json, or mcp-spec-*.json
- ❌ Create Python files, proxy code, tool wrappers, or decorators
- ❌ Modify .mcp.json configuration

**Only output:** Single `mcp-mock.json` configuration file (consumed by a proxy in the agent's sandbox that intercepts MCP calls and returns mock responses).

## Gotchas / Pitfalls

### 1. Deactivated Parameters
**Problem:** Including parameters marked `"deactivate": true`
**Detection:** Check each parameter for deactivate flag
**Solution:** Filter out deactivated parameters from input_schema

### 2. Wrong Response Structure
**Problem:** List operations not wrapped in `{"results": [...]}`
**Detection:** Check if `openApiType.path` has key parameters
**Solution:** Use `results` wrapper for list operations, single object for by-key operations

### 3. SAP Date Format
**Problem:** Using ISO date format instead of SAP `/Date(timestamp)/`
**Detection:** Check for `example: "/Date(...)/` in translation.json or serverCard.json
**Solution:** Use SAP date format for all date fields

### 4. Decimal as Number
**Problem:** Using JSON number for decimal amounts
**Detection:** Check `format: decimal` in translation.json or serverCard.json
**Solution:** SAP uses string type for decimals: `"75000.00"`

### 5. Missing Schema Fields
**Problem:** Mock response missing required fields from schema
**Detection:** Compare mock fields to serverCard.json properties
**Solution:** Include all non-nullable fields from schema

### 6. Duplicate Server Slugs
**Problem:** Two servers generate the same slug
**Detection:** Check for slug collisions after generation
**Solution:** Append numeric suffix: `sap-invoice`, `sap-invoice-2`

### 7. Path B: Missing Server Name
**Problem:** `mcp-spec-*.json` files have no `serverInfo` — server name cannot be recovered from slug alone
**Detection:** Slug like `cost-center` doesn't map back to a full server name
**Solution:** Use the slug as `mcp_server_name` directly; it is informational only

### 8. Path B: No outputSchema
**Problem:** `mcp-spec-*.json` has no `outputSchema` — cannot derive mock response structure
**Detection:** `outputSchema` key absent from file
**Solution:** Generate a minimal mock response `{}` and warn user to fill it in manually

### 9. Path B: Ambiguous Server Grouping
**Problem:** Filename pattern `mcp-spec-<server>-<tool>.json` — tool names containing `-` can make parsing ambiguous
**Detection:** Multiple possible splits of `<server>` vs `<tool>`
**Solution:** Use the full prefix up to the last known tool name segment; when ambiguous, treat the longest prefix as the server slug

## Examples

### Example 1: Single MCP Server

**Input:** User asks to "generate mcp mock config" for invoice-monitor agent

**Discovered files:**
- `assets/s4-supplier-invoice-mcp-server/mcp-translation/translation.json`
- `assets/s4-supplier-invoice-mcp-server/mcp-translation/serverCard.json`

**Output:** `mcp-mock.json`
```json
{
  "servers": {
    "s4-supplier-invoice": {
      "mcp_server_name": "com.sap.s4/API_SUPPLIERINVOICE_PROCESS_SRV",
      "description": "MCP server for reading supplier invoice data...",
      "tools": {
        "list_supplier_invoices": {
          "description": "Retrieve a list of supplier invoices...",
          "input_schema": {
            "type": "object",
            "properties": {
              "$top": {"type": "string", "description": "Maximum number..."},
              "$filter": {"type": "string", "description": "OData filter..."},
              "$select": {"type": "string", "description": "Fields to return..."},
              "$orderby": {"type": "string", "description": "Sort order..."}
            },
            "required": []
          },
          "mock_response": {
            "results": [
              {
                "SupplierInvoice": "5100000001",
                "FiscalYear": "2026",
                "CompanyCode": "1000",
                "InvoiceGrossAmount": "75000.00",
                "DocumentCurrency": "USD",
                "CreationDate": "/Date(1744588800000)/",
                "SupplierInvoiceApprovalStatus": "Pending",
                "InvoicingParty": "VENDOR-1001"
              }
            ]
          }
        },
        "get_supplier_invoice_by_key": {
          "description": "Retrieve a single supplier invoice...",
          "input_schema": {
            "type": "object",
            "properties": {
              "SupplierInvoice": {"type": "string", "description": "Invoice number"},
              "FiscalYear": {"type": "string", "description": "Fiscal year"}
            },
            "required": ["SupplierInvoice", "FiscalYear"]
          },
          "mock_response": {
            "SupplierInvoice": "5100000001",
            "FiscalYear": "2026",
            "CompanyCode": "1000",
            "InvoiceGrossAmount": "75000.00",
            "DocumentCurrency": "USD",
            "CreationDate": "/Date(1744588800000)/",
            "SupplierInvoiceApprovalStatus": "Pending",
            "InvoicingParty": "VENDOR-1001"
          }
        }
      }
    }
  },
  "metadata": {
    "version": "1.0.0",
    "created_for_agent": "invoice-monitor",
    "mock_mode": true,
    "deterministic": true,
    "total_servers": 1,
    "total_tools": 2,
    "generated_from": ["translation.json", "serverCard.json"],
    "generation_date": "2026-04-15"
  }
}
```

**Usage - O(1) Lookup:**
```javascript
const mockData = require('./mcp-mock.json');

// Direct access: server → tool → response
const tool = mockData.servers["s4-supplier-invoice"].tools["list_supplier_invoices"];
const response = tool.mock_response;
```

### Example 2: Multiple MCP Servers

**Input:** Agent uses multiple MCP servers (SAP + n8n + ibd)

**Discovered files:**
- `assets/s4-supplier-invoice-mcp-server/mcp-translation/translation.json`
- `assets/n8n-workflow-mcp/mcp-translation/translation.json`
- `.mcp.json` referencing `ibd` server

**Output:** Single `mcp-mock.json` with all servers:
```json
{
  "servers": {
    "s4-supplier-invoice": {
      "mcp_server_name": "com.sap.s4/API_SUPPLIERINVOICE_PROCESS_SRV",
      "description": "SAP S/4HANA supplier invoice operations",
      "tools": {
        "list_supplier_invoices": { ... },
        "get_supplier_invoice_by_key": { ... }
      }
    },
    "n8n-workflow": {
      "mcp_server_name": "n8n-workflow-mcp",
      "description": "n8n workflow automation",
      "tools": {
        "trigger_workflow": { ... },
        "get_workflow_status": { ... },
        "list_workflows": { ... }
      }
    },
    "ibd": {
      "mcp_server_name": "ibd-mcp-server",
      "description": "Intent-based development tools",
      "tools": {
        "create_intent": { ... },
        "analyze_code": { ... }
      }
    }
  },
  "metadata": {
    "version": "1.0.0",
    "created_for_agent": "multi-server-agent",
    "mock_mode": true,
    "deterministic": true,
    "total_servers": 3,
    "total_tools": 7,
    "generated_from": ["translation.json", "serverCard.json"],
    "generation_date": "2026-04-15"
  }
}
```

**Usage:**
```javascript
const mockData = require('./mcp-mock.json');

// Access any server's tool directly
const sapTool = mockData.servers["s4-supplier-invoice"].tools["list_supplier_invoices"];
const n8nTool = mockData.servers["n8n-workflow"].tools["trigger_workflow"];
const ibdTool = mockData.servers["ibd"].tools["create_intent"];

// Iterate all servers
for (const [serverSlug, server] of Object.entries(mockData.servers)) {
  console.log(`Server: ${server.mcp_server_name}`);
  for (const [toolName, tool] of Object.entries(server.tools)) {
    console.log(`  Tool: ${toolName}`);
  }
}
```

### Example 3: Existing MCP Server (Path B only)

**Input:** Agent uses an existing MCP server; `mcp-spec-*.json` files were saved during spec phase.

**Discovered files:**
- `specification/cost-center-agent/mcp-specs/mcp-spec-cost-center-list_cost_centers.json`
- `specification/cost-center-agent/mcp-specs/mcp-spec-cost-center-get_cost_center_by_id.json`

**mcp-spec-cost-center-list_cost_centers.json:**
```json
{
  "name": "list_cost_centers",
  "description": "Returns a list of cost centers for a given controlling area.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "ControllingArea": {"type": "string", "description": "Controlling area ID"},
      "$top": {"type": "integer", "description": "Max results"}
    },
    "required": ["ControllingArea"]
  },
  "outputSchema": {
    "type": "object",
    "properties": {
      "results": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "CostCenter": {"type": "string"},
            "ControllingArea": {"type": "string"},
            "CostCenterName": {"type": "string"},
            "ValidityEndDate": {"type": "string"}
          }
        }
      }
    }
  }
}
```

**Output:** `mcp-mock.json`
```json
{
  "servers": {
    "cost-center": {
      "mcp_server_name": "cost-center",
      "description": "Existing MCP server for cost center data",
      "tools": {
        "list_cost_centers": {
          "description": "Returns a list of cost centers for a given controlling area.",
          "input_schema": {
            "type": "object",
            "properties": {
              "ControllingArea": {"type": "string", "description": "Controlling area ID"},
              "$top": {"type": "integer", "description": "Max results"}
            },
            "required": ["ControllingArea"]
          },
          "mock_response": {
            "results": [
              {
                "CostCenter": "CC-1000",
                "ControllingArea": "A000",
                "CostCenterName": "Corporate IT",
                "ValidityEndDate": "/Date(9999999999000)/"
              },
              {
                "CostCenter": "CC-2000",
                "ControllingArea": "A000",
                "CostCenterName": "Finance",
                "ValidityEndDate": "/Date(9999999999000)/"
              }
            ]
          }
        },
        "get_cost_center_by_id": {
          "description": "...",
          "input_schema": {...},
          "mock_response": {...}
        }
      }
    }
  },
  "metadata": {
    "version": "1.0.0",
    "created_for_agent": "cost-center-agent",
    "mock_mode": true,
    "deterministic": true,
    "total_servers": 1,
    "total_tools": 2,
    "generated_from": ["mcp-spec-cost-center-list_cost_centers.json", "mcp-spec-cost-center-get_cost_center_by_id.json"],
    "generation_date": "2026-04-26"
  }
}
```

### Example 4: Mixed (Path A + Path B)

**Discovered files:**
- `assets/s4-supplier-invoice-mcp-server/mcp-translation/translation.json` (Path A — new MCP server)
- `specification/my-agent/mcp-specs/mcp-spec-cost-center-list_cost_centers.json` (Path B — existing)

**Output:** Single `mcp-mock.json` with both servers merged:
```json
{
  "servers": {
    "s4-supplier-invoice": { ... },
    "cost-center": { ... }
  },
  "metadata": {
    "total_servers": 2,
    "total_tools": 3,
    "generated_from": ["translation.json", "mcp-spec-cost-center-list_cost_centers.json"]
  }
}
```

## Related Skills

- `sap-agent-bootstrap`: Bootstrap SAP agents with mocking ready

## Next Steps

After generating `mcp-mock.json`:
1. Inform user of file location, server count, and tool count
2. Suggest: \"Test agent behavior with mock data\"
3. Optional: \"Generate additional mock scenarios (error cases)\"
