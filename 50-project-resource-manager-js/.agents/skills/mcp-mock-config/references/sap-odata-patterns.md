# SAP OData Mock Patterns

This reference defines SAP-specific patterns for generating mock responses from SAP S/4HANA OData APIs.

## Response Structure Patterns

### List Operations (Collection)

When `openApiType.path` does NOT contain key parameters (e.g., `/A_SupplierInvoice`):

```json
{
  "results": [
    {
      "SupplierInvoice": "5100000001",
      "FiscalYear": "2026",
      "CompanyCode": "1000",
      ...
    },
    {
      "SupplierInvoice": "5100000002",
      "FiscalYear": "2026",
      "CompanyCode": "1000",
      ...
    }
  ]
}
```

**Key characteristics:**
- Wrapped in `{"results": [...]}`
- Include 2 items for variety
- Vary key fields between items (invoice numbers, vendors, amounts)

### Single Entity Operations (By Key)

When `openApiType.path` contains key parameters (e.g., `/A_SupplierInvoice(SupplierInvoice='{SupplierInvoice}',FiscalYear='{FiscalYear}')`):

```json
{
  "SupplierInvoice": "5100000001",
  "FiscalYear": "2026",
  "CompanyCode": "1000",
  ...
}
```

**Key characteristics:**
- Single object (no `results` wrapper)
- All fields populated
- Key fields match what would be passed as parameters

### Count Response

If `$count` parameter is supported and not deactivated:

```json
{
  "__count": "2",
  "results": [...]
}
```

## SAP Date Format

SAP OData uses a special date format:

```
/Date(timestamp)/
```

Where `timestamp` is milliseconds since Unix epoch.

### Converting Dates

| Human Date | Timestamp | SAP Format |
|------------|-----------|------------|
| 2026-04-15 | 1744675200000 | `/Date(1744675200000)/` |
| 2026-04-14 | 1744588800000 | `/Date(1744588800000)/` |
| 2026-04-13 | 1744502400000 | `/Date(1744502400000)/` |

### Detection

In api-spec.json, date fields have:
```json
"CreationDate": {
  "type": "string",
  "nullable": true,
  "example": "/Date(1492041600000)/"
}
```

## SAP Decimal Format

SAP OData uses string type for decimal values:

```json
"InvoiceGrossAmount": {
  "type": "string",
  "format": "decimal",
  "x-sap-precision": 14,
  "x-sap-scale": 3
}
```

**Mock value:** `"75000.00"` (string, not number)

### Common Amount Fields

| Field | Mock Value |
|-------|------------|
| `InvoiceGrossAmount` | `"75000.00"` |
| `TaxAmount` | `"5000.00"` |
| `NetAmount` | `"70000.00"` |
| `UnitPrice` | `"15.00"` |
| `TotalAmount` | `"1500.00"` |

## Common SAP Field Patterns

### Document Numbers

| Field | Pattern | Mock Values |
|-------|---------|-------------|
| `SupplierInvoice` | 10-digit | `"5100000001"`, `"5100000002"` |
| `PurchaseOrder` | 10-digit | `"4500000001"` |
| `SalesOrder` | 10-digit | `"0000000001"` |
| `AccountingDocument` | 10-digit | `"0100000001"` |

### Organizational Units

| Field | Pattern | Mock Value |
|-------|---------|------------|
| `CompanyCode` | 4-char | `"1000"` |
| `Plant` | 4-char | `"1000"` |
| `PurchasingOrganization` | 4-char | `"1000"` |
| `SalesOrganization` | 4-char | `"1000"` |

### Business Partners

| Field | Pattern | Mock Values |
|-------|---------|-------------|
| `InvoicingParty` | 10-char vendor | `"VENDOR-1001"` |
| `Supplier` | 10-char | `"0000001000"` |
| `Customer` | 10-char | `"0000010000"` |

### Dates and Time

| Field | Format | Mock Value |
|-------|--------|------------|
| `CreationDate` | SAP date | `/Date(1744588800000)/` |
| `PostingDate` | SAP date | `/Date(1744588800000)/` |
| `DocumentDate` | SAP date | `/Date(1744675200000)/` |
| `LastChangeDateTime` | Timestamp text | `"20260415103000"` |

### Status Fields

| Field | Common Values |
|-------|---------------|
| `SupplierInvoiceApprovalStatus` | `"Pending"`, `"Approved"`, `"Rejected"` |
| `DocumentStatus` | `"OPEN"`, `"CLOSED"`, `"BLOCKED"` |
| `PaymentStatus` | `"Not Paid"`, `"Partially Paid"`, `"Paid"` |

### Currency and Units

| Field | Mock Value |
|-------|------------|
| `DocumentCurrency` | `"USD"` |
| `LocalCurrency` | `"EUR"` |
| `BaseUnit` | `"EA"` |
| `OrderQuantityUnit` | `"PC"` |

## Complete Mock Example

Based on `A_SupplierInvoiceType` schema:

```json
{
  "results": [
    {
      "SupplierInvoice": "5100000001",
      "FiscalYear": "2026",
      "CompanyCode": "1000",
      "DocumentDate": "/Date(1744675200000)/",
      "PostingDate": "/Date(1744675200000)/",
      "CreationDate": "/Date(1744588800000)/",
      "SupplierInvoiceIDByInvcgParty": "INV-2026-001",
      "InvoicingParty": "VENDOR-1001",
      "DocumentCurrency": "USD",
      "InvoiceGrossAmount": "75000.00",
      "UnplannedDeliveryCost": "0.00",
      "ManualCashDiscount": "0.00",
      "PaymentTerms": "NT30",
      "DueCalculationBaseDate": "/Date(1744675200000)/",
      "CashDiscount1Days": "0",
      "CashDiscount2Days": "0",
      "NetPaymentDays": "30",
      "SupplierInvoiceApprovalStatus": "Pending",
      "IsResultOfAutomPosting": false,
      "AccountingDocumentType": "KR",
      "SupplierInvoiceStatus": "",
      "SupplierInvoiceOrigin": "1",
      "IsEUSalesWithoutVATLiability": false
    },
    {
      "SupplierInvoice": "5100000002",
      "FiscalYear": "2026",
      "CompanyCode": "1000",
      "DocumentDate": "/Date(1744588800000)/",
      "PostingDate": "/Date(1744588800000)/",
      "CreationDate": "/Date(1744502400000)/",
      "SupplierInvoiceIDByInvcgParty": "INV-2026-002",
      "InvoicingParty": "VENDOR-1002",
      "DocumentCurrency": "EUR",
      "InvoiceGrossAmount": "12500.50",
      "UnplannedDeliveryCost": "0.00",
      "ManualCashDiscount": "0.00",
      "PaymentTerms": "NT30",
      "DueCalculationBaseDate": "/Date(1744588800000)/",
      "CashDiscount1Days": "0",
      "CashDiscount2Days": "0",
      "NetPaymentDays": "30",
      "SupplierInvoiceApprovalStatus": "Pending",
      "IsResultOfAutomPosting": false,
      "AccountingDocumentType": "KR",
      "SupplierInvoiceStatus": "",
      "SupplierInvoiceOrigin": "1",
      "IsEUSalesWithoutVATLiability": false
    }
  ]
}
```

## OData Query Parameters

When translation.json includes parameters, map them correctly:

| Parameter | Description | Deactivate? |
|-----------|-------------|-------------|
| `$top` | Limit results | Usually active |
| `$filter` | Filter expression | Usually active |
| `$select` | Fields to return | Usually active |
| `$orderby` | Sort order | Usually active |
| `$skip` | Pagination offset | Often deactivated |
| `$count` | Include count | Often deactivated |

### Handling Deactivated Parameters

Check for `"deactivate": true`:

```json
{
  "name": "$skip",
  "deactivate": true
}
```

**Action:** Exclude from `input_schema.properties`

## API Path Patterns

### Collection Path (List)
```
/A_SupplierInvoice
```
→ Returns `{"results": [...]}`

### Single Entity Path (By Key)
```
/A_SupplierInvoice(SupplierInvoice='{SupplierInvoice}',FiscalYear='{FiscalYear}')
```
→ Returns single object

### Detection

```json
// List operation - no {key} in path
"openApiType": {
  "path": "/A_SupplierInvoice",
  "operationId": "get"
}

// Single entity - has {key} in path
"openApiType": {
  "path": "/A_SupplierInvoice(SupplierInvoice='{SupplierInvoice}',FiscalYear='{FiscalYear}')",
  "operationId": "get"
}
```

## Common SAP APIs

| API | Entity | Key Fields |
|-----|--------|------------|
| Supplier Invoice | `A_SupplierInvoice` | SupplierInvoice, FiscalYear |
| Purchase Order | `A_PurchaseOrder` | PurchaseOrder |
| Sales Order | `A_SalesOrder` | SalesOrder |
| Business Partner | `A_BusinessPartner` | BusinessPartner |
| Product | `A_Product` | Product |
| Material | `A_Material` | Material |

## Error Response Pattern (Optional)

For error case mocks (if needed):

```json
{
  "error": {
    "code": "SY/530",
    "message": {
      "lang": "en",
      "value": "Resource not found"
    }
  }
}
```
