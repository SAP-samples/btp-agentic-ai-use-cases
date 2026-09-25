# OpenAPI Type to Mock Value Mapping

This reference defines how to generate appropriate mock values based on OpenAPI/JSON Schema types found in `api-spec.json`.

## Basic Type Mapping

| OpenAPI Type | JSON Type | Mock Strategy | Example Value |
|-------------|-----------|---------------|---------------|
| `string` | string | Field-appropriate value | `"MOCK-VALUE"` |
| `integer` | number | Reasonable whole number | `100` |
| `number` | number | Reasonable decimal | `1500.00` |
| `boolean` | boolean | Default to success case | `true` |
| `array` | array | 1-2 items with structure | `[{...}, {...}]` |
| `object` | object | Nested mock structure | `{...}` |

## String Type with Constraints

### By `maxLength`

| maxLength | Field Context | Mock Value |
|-----------|--------------|------------|
| 4 | FiscalYear | `"2026"` |
| 5 | Currency code | `"USD"` |
| 10 | Document number | `"5100000001"` |
| 16 | Reference | `"REF-MOCK-001"` |

### By `format`

| Format | Mock Strategy | Example |
|--------|---------------|---------|
| `decimal` | Numeric string | `"75000.00"` |
| `date` | ISO date | `"2026-04-15"` |
| `date-time` | ISO datetime | `"2026-04-15T10:30:00Z"` |
| `email` | Valid email | `"mock@example.com"` |
| `uri` | Valid URL | `"https://example.com/mock"` |

### By `example` in Schema

If the schema includes an `example` field, use a similar pattern:

```json
// Schema
"CreationDate": {
  "type": "string",
  "example": "/Date(1492041600000)/"
}

// Mock value: use same format
"CreationDate": "/Date(1744588800000)/"
```

## SAP-Specific String Patterns

| Field Name Pattern | Mock Value |
|-------------------|------------|
| `*Invoice` | `"5100000001"` |
| `*Year` | `"2026"` |
| `*Code` (Company) | `"1000"` |
| `*Currency` | `"USD"` |
| `*Party` | `"VENDOR-1001"` |
| `*Amount` | `"75000.00"` (string with format: decimal) |
| `*Date` | `/Date(1744588800000)/` (SAP format) |
| `*Status` | `"Pending"` or `"OPEN"` |

## Number Types

### Integer

| Context | Range | Example |
|---------|-------|---------|
| Count | 1-100 | `50` |
| Quantity | 1-1000 | `100` |
| Line number | 10, 20, 30... | `10` |
| Sequence | 1, 2, 3... | `1` |

### Number (Decimal)

| Context | Range | Example |
|---------|-------|---------|
| Amount | 1000-100000 | `75000.00` |
| Unit price | 1-1000 | `15.00` |
| Rate | 0-1 | `0.19` |
| Percentage | 0-100 | `19.5` |

**Note:** For SAP APIs, amounts are often `string` type with `format: decimal`.

## Array Types

### List Response

For operations that return collections:

```json
{
  "results": [
    { /* first item with all fields */ },
    { /* second item with varied values */ }
  ]
}
```

### Nested Arrays

For fields that are arrays within an object:

```json
"lines": [
  {
    "line_number": "10",
    "material": "MAT-001",
    "quantity": 100
  },
  {
    "line_number": "20",
    "material": "MAT-002",
    "quantity": 50
  }
]
```

## Object Types

Recursively apply type mapping to nested properties:

```json
// Schema
"address": {
  "type": "object",
  "properties": {
    "street": {"type": "string"},
    "city": {"type": "string"},
    "country": {"type": "string", "maxLength": 2}
  }
}

// Mock
"address": {
  "street": "123 Mock Street",
  "city": "Mock City",
  "country": "US"
}
```

## Nullable Fields

For fields marked `"nullable": true`:
- Include in mock with a value (not null) for the success case
- Null values are for error/edge case mocks

## Required vs Optional Fields

| Field Status | Mock Behavior |
|--------------|---------------|
| Required | Always include |
| Optional + nullable | Include with value |
| Optional + not common | May omit or include |

## Type Detection from api-spec.json

### Finding the Schema

1. Look up `openApiType.path` from translation.json
2. Find the path in `paths` section of api-spec.json
3. Follow `$ref` to `components/schemas/{SchemaName}`

### Example Lookup

```json
// translation.json
{
  "name": "list_supplier_invoices",
  "openApiType": {
    "path": "/A_SupplierInvoice",
    "operationId": "get"
  }
}

// api-spec.json path
"paths": {
  "/A_SupplierInvoice": {
    "get": {
      "responses": {
        "200": {
          "content": {
            "application/json": {
              "schema": {
                "properties": {
                  "results": {
                    "items": {
                      "$ref": "#/components/schemas/API_SUPPLIERINVOICE_PROCESS_SRV.A_SupplierInvoiceType"
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}

// Follow $ref to components/schemas
"components": {
  "schemas": {
    "API_SUPPLIERINVOICE_PROCESS_SRV.A_SupplierInvoiceType": {
      "type": "object",
      "properties": {
        "SupplierInvoice": {"type": "string", "maxLength": 10},
        "InvoiceGrossAmount": {"type": "string", "format": "decimal"}
        // ... more fields
      }
    }
  }
}
```

## Deterministic Values

For deterministic mocks, use consistent patterns:

| Field | Pattern | Example Values |
|-------|---------|----------------|
| IDs | `{PREFIX}-MOCK-{SEQ}` | `"PO-MOCK-001"` |
| Numbers | Start from 5100000001 | `"5100000001"`, `"5100000002"` |
| Vendors | `VENDOR-100{N}` | `"VENDOR-1001"`, `"VENDOR-1002"` |
| Materials | `MAT-00{N}` | `"MAT-001"`, `"MAT-002"` |
| Dates | Fixed timestamp | `"/Date(1744588800000)/"` |
| Amounts | Varied but reasonable | `"75000.00"`, `"12500.50"` |
