# Troubleshooting Guide

Common errors and their solutions during data product generation.

---

## Step 2: Search Issues (handled in `intent-analysis`)

### `dpca-mcp-server__ums_search_data_products` returns no results

**Cause:** Search term too specific or data products not indexed.

**Solution:**
- Try a broader search term (e.g. "sales" instead of "sales order billing status")

### Stale/unserved version ID from search results

**Cause:** `search-data-products` sometimes returns older version IDs (e.g. `v1.0.0`) that the fetch step of `fetch-and-prepare` no longer serves. The fetch returns HTTP 200 but with empty or missing schema.

**Recovery:**
- Check existing DP folders in the workspace — any folder with `.ddp_metadata.json` will have `source_dp_fqdns` showing a version that previously worked. Try that version.
- Bump the patch version and retry (e.g. `v1.0.0` → `v1.0.1` → `v1.1.0`).
- Ask the user if they know a working version ID.

### Search returns incomplete results

**Cause:** Remote MCP server may have rate limits or partial data.

**Solution:**
- Try additional calls with different or broader terms
- Present the combined results to the user and let them decide

---

## Step 2: CSN/CDS Generation Issues

### Step 2: All domain schemas inactive

When all candidates for a business domain return 404 from `fetch-and-prepare`, follow this decision tree — do not terminate silently:

1. Try the next candidate from the search results from `intent-analysis` if any remain.
2. If all domain candidates are exhausted: call `dpca-mcp-server__ums_search_data_products` again with a broader or adjacent keyword derived from the user's original intent (e.g. "billing" instead of "sales tax", "order" instead of "real estate").
3. If still no active schema found: surface a blocker gate — *"All available schemas for [domain] are currently inactive in this landscape. Please provide an alternative data product name or ID, or confirm you want to wait for activation."* **[GATE]**

### Step 2: fetch-and-prepare error classification

`fetch-and-prepare` runs fetch → compile CDS → build graph in one call; failures usually originate in the fetch stage. Classify the error before surfacing to the user:
- Error contains "timeout" or "connection": retry once silently. If it fails again: *"The fetch timed out. Would you like to retry, or try a different data product?"*
- Error contains "unauthorized" or "401" or "403": *"Authentication failed — your API key may be expired. Check `~/.config/dp-gen/.env` and retry."*
- Error contains "invalid" or "not a valid ID" or "characters": *"The data product ID format is invalid. Check the search results from `intent-analysis` and confirm the exact ID."*
- Error contains "empty" or "0 definitions": the fetch succeeded but returned no schema — treat like a not-found and try a different data product or version.
- All other errors: show the error verbatim and ask: *"The data model could not be created. Would you like to try a different data product, or should we investigate the error?"*

### `fetch-and-prepare` fails with authentication error

**Cause:** Missing or invalid SAP BTP credentials.

**Solution:**
- Verify `.env` file exists with `MCP_URL` and `API_KEY`
- Check that API key is valid and not expired
- Confirm user has access to the requested data products

### `fetch-and-prepare` returns "Data product not found"

**Cause:** Invalid data product ID or version mismatch.

**Solution:**
- Verify the full versioned ID format: `<namespace>:dataProduct:<Name>:<version>` (e.g. `your.namespace:dataProduct:EntityName:v1.0.0`)
- Do NOT use the short form (e.g. `v1` instead of `v1.0.0`)
- Re-run the search in `intent-analysis` to get correct IDs

### `fetch-and-prepare` stops with "empty CSN / 0 definitions"

**Cause:** The fetch stage returned no usable schema, so `fetch-and-prepare` halts before compiling the CDS or building the graph (nothing is written).

**Solution:**
- The data product ID/version likely resolves to an empty or unserved schema — verify the ID and try a working version (see "Stale/unserved version ID" above)
- If the ID is correct, select a different source data product and re-run `fetch-and-prepare`

---

## Step 3: Schema Exploration Issues

### `csn-list-entities` returns empty list

**Cause:** CSN graph not generated or corrupted.

**Solution:**
- Verify `csn_graph.json` exists in `<session_folder>/work/`
- Re-run Step 2a (`fetch-and-prepare`) to regenerate the CSN, CDS, and graph together

### `csn-get-schema` returns "Entity not found"

**Cause:** Entity FQN doesn't match CSN graph entries.

**Solution:**
- Run `csn-list-entities` first to get exact FQN
- Copy/paste the FQN exactly as returned (case-sensitive)

### Cannot find fields by label

**Cause:** Field labels may not match expected names.

**Solution:**
- Use `csn-search-fields` with partial substring
- Search by technical field name if label search fails
- Use `csn-get-schema --include-enums` to see all fields

---

## Step 4: CDS Validation Failures

### Assertion fails: Missing cast on computed column

**Solution:**
```cds
-- WRONG:
(A.price * A.quantity) as total

-- CORRECT:
cast((A.price * A.quantity) as Decimal(17,5)) as total
```

### Assertion fails: Unescaped colons in entity names

**Solution:**
```cds
-- WRONG:
select from your.namespace:apiResource:EntityName:v1.EntityObject

-- CORRECT:
select from your.![namespace:apiResource:EntityName:v1].EntityObject
```

### Assertion fails: Missing semicolon after WHERE clause

**Solution:**
```cds
define view MyCube as select from Entity as E
{
  key E.id as id,
  E.name as name
}
where E.status = 'ACTIVE';
```

---

## Step 5: DPD Generation Issues

### `generate-interop` returns "No transformed entities found"

**Cause:** No `define view` with a SELECT block was found in the compiled CDS.

**Solution:**
- Run `grep -m 1 "^define view" <file>` internally to confirm the transformer view exists in the CDS file
- If missing: the view was not written or not saved — re-run Step 3d
- If present: the view body is empty or failed to compile — ensure the `define view` has a non-empty SELECT block and re-run Step 4 self-check before retrying

### `generate-interop` fails with "Invalid CDS syntax" or artifact not found

**First — determine where the error line is:**

- **Error line is inside the transformer view** (line number ≥ the `define view` line): apply a targeted fix to that specific line only — never rewrite the full cube. State: "CDS parse error on line N — correcting." If the error says an artifact or entity was not found: verify the FQN against `csn-list-entities` output — the issue is almost always a wrong version number or missing `![...]` wrapper.
- **Error line is inside the source entity definitions** (line number < the `define view` line): this is an unresolvable schema issue in the source data product — do not attempt to fix it. State: *"The source data product schema contains an internal reference that cannot be compiled in this context. Please select a different source data product."* Re-run the search in `intent-analysis` to select a different source data product.

### DPD file generated but missing output entities

**Cause:** Transformer view body is empty or has no SELECT fields.

**Solution:**
- Verify the `define view` has a non-empty field selection block
- Re-run Step 4 self-check and Step 5 (generate-interop)

---

## Step 6: Solution Setup Issues

### Ghost/phantom folders remain after solution setup

**Cause:** Solution tracking not updated after filesystem move.

**Solution:**
1. Check filesystem: `ls -la <working_directory>`
2. Check solution tracking independently (solution-specific command) — do not infer tracking state from filesystem
3. If old session folder name appears in solution tracking: explicitly remove it from there
4. Re-inspect solution tracking to confirm removal
5. Verify DP folder only appears inside `assets/` in both filesystem and solution tracking

### `asset.yaml` not found in expected location

**Solution:**
- Verify files exist in `assets/<folder_name>/`
- Check that folder name follows kebab-case convention
- Re-run setup with correct parameters

---

## General Issues

### CLI commands not found (`jl data-product: command not found`)

**Solution:**
- Run: `jl plugin add "<skill_dir>/packages/sap-joule-dp-gen-plugin-0.1.10.tgz"` (where `<skill_dir>` is the absolute path to `skills/data-product`)
- Verify Node.js >= 20 is installed
- Verify `jl data-product --help` works after install

### Session folder path issues

**Solution:**
- Always use absolute paths from `working_directory` for CLI arguments
- Always use relative paths for IDE/agent file tools
- Never mix the two systems
