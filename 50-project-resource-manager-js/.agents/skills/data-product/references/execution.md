## Invocation Rule

**Do not invoke this skill directly from an end-user request.**

This skill is invoked only from `specification`. Requirement capture and data product search/selection are performed by `intent-analysis` before this skill is ever called.

> **Prerequisite:** Before this skill runs, `intent-analysis` must have completed and written `intent.md` with confirmed ORD ID(s). If `intent.md` does not exist or contains no confirmed ORD ID, stop and run `intent-analysis` first.

| Triggered by | Mode | Steps to execute | Then |
|---|---|---|---|
| `specification` | **Execution Mode** | Step 0 then Steps 1a onwards. Search and selection were completed during `intent-analysis` — use confirmed ORD ID(s) from `intent.md`. | Continue to completion |

### Execution Mode
Activated when called from `specification`. Search and selection have already been completed during `intent-analysis`. Run Step 0 if not already done, then resume from Step 1a using the ORD ID(s) confirmed in `intent.md`.

---

# Data Product Generation Skill — SAP Data Product Generator

Creates a derived data product from existing SAP primary data products via the `jl data-product` CLI.

**Read [references/TOOLING-CLI.md](references/TOOLING-CLI.md) before calling any `jl data-product` command.**

**See the worked example in [references/CDS-PATTERNS.md](references/CDS-PATTERNS.md) for correct cube format and annotation style.**

Execute this workflow in order. One step at a time. Never skip a gate.

---

## Fast Track Mode

- While executing the Data Product Skill in Fast Track Mode, you must do the following:
  - Execute the steps in the specified order
  - Never skip or bypass any [MANDATORY], [GATE], or [MANDATORY GATE] steps or questions
  - Never skip or bypass any steps that require user approval or input
  - Respect any pre-defined rules in this skill
  - If a step specifically mentions'FAST-TRACK EXEMPT', you must not skip it and will have to ask for user approval irrespective of any existing Fast Track Mode rules at all costs

## Behavior rules

- Never ask for information already in context
- Respond with the minimum needed: [GATE] questions, tool errors, one-sentence step status. No narration.
- Never surface technical internals to the user — pipeline mechanics, MV/refresh modes, system annotations, internal column names, CDS rules. Apply them silently. Explain only if the user explicitly asks.
- Only run shell commands for CLI tool calls or to create/move files — never to display info
- Never read or edit files inside `src/`
- Never overwrite the entire `transformation.cds` — always make surgical edits that target only the cube view section

### Language

Apply terminology and path rules from [references/TERMINOLOGY.md](references/TERMINOLOGY.md).

- Name, title, shortDescription, and description are business metadata — write them from the user's perspective, not the implementation's.

---

## Known failure modes

**Read [references/TROUBLESHOOTING.md](references/TROUBLESHOOTING.md) when a CLI call or CDS edit behaves unexpectedly.**

---

## Hard Rules

- Each step executes **at most once** unless explicitly re-requested (except Step 7: iterative refinement allowed)
- **Never ask for information already in context** — always review history first
- **Never skip a mandatory gate** (user approvals, properties approval, data product definition approval)
- **Never revert to a completed step**
- Be concise — lead with the result, no explanatory padding
- Never reuse identifiers, names, or values verbatim from examples in this file
- Check for validation rules
- Path handling: pwd is used solely to resolve absolute paths for MCP tool arguments. File tools (write_file, read_file, list_files, delete_file) are scoped to the solution root — always pass them relative paths only. Never pass an absolute path (e.g. /home/user/project/...) to a file tool.
- **Only JL CLI** should be used to call the remote MCP Tools mentioned in the steps

---

## Linear Execution Flow

```
0 → 1 → 2 → 3 → 4 → 5 → 5b → 6 → 7 → 7b
```

---

## Step 0 — Install Required Packages [MANDATORY]

Run once before anything else. No user output.

Where `<skill_dir>` is the absolute path to the `skills/data-product` directory within the repository. Resolve it with `find` or relative to `working_directory` if already known.

### Install `jl data-product` plugin

Always run — do not skip based on a prior install.

```bash
jl plugin add "<skill_dir>/packages/sap-joule-dp-gen-plugin-0.1.10.tgz"
```

On success: `jl data-product --help` should exit successfully, then proceed to Step 1a. On error: show the error and stop.

---

## Step 1a — Propose & Approve Properties [GATE]

**Only proceed after input DP confirmation from `intent-analysis` (ORD ID(s) confirmed in `intent.md`).**

Propose:

| Property          | Rule                                                            |
| ----------------- | --------------------------------------------------------------- |
| Technical Name    | CamelCase, 1–70 chars                                          |
| Business Name     | Derived from Technical Name with spaces                         |
| Short Description | 1–255 chars — describe what the data is about and who uses it |
| Description       | Any length — expand on the business purpose                    |
| Responsible       | Defaults to 'customer:vendor:Customer'. Regex Pattern: ^([a-z0-9]+):(vendor):([a-zA-Z0-9._\-]+) |

Ask: "The responsible field will default to customer:vendor:Customer. Would you like to use a different value?"

**[GATE - FAST-TRACK EXEMPT] Wait for explicit user approval even in Fast Track mode. On change: update and re-propose.**

---

## Folder Name Computation

Given an approved `name` (CamelCase): insert a dash before each uppercase letter that follows a lowercase letter, lowercase everything, append `-data-product`. Verify result is all-lowercase, dashes only, ends with `-data-product`.

---

### After user approves — create folder and write metadata [MANDATORY]

Immediately after approval, before proceeding to Step 2:

Note: session_folder is an absolute path — ensure the file is written to that exact absolute path. Do not use tools that resolve paths relative to a project or solution root, as this will result in a nested duplicate folder.

**Before doing anything, compute `folder_name` as follows (MANDATORY):**

1. Take `approved_name` (CamelCase, e.g. `SalesOrderBillingStatus`)
2. Insert a dash before each uppercase letter that follows a lowercase letter, then lowercase everything (e.g. `SalesOrderBillingStatus` → `sales-order-billing-status`)
3. Append `-data-product` (e.g. `sales-order-billing-status-data-product`)
4. Store as `folder_name` — this is the only value used for folder and path operations below

**Example:** `approved_name = SalesOrderBillingStatus` → `folder_name = sales-order-billing-status-data-product`

**Self-check gate (run before any shell command):** Verify `folder_name` is all lowercase, uses only dashes (no spaces, no CamelCase), and ends with `-data-product`. If not, recompute before continuing.

---

## Step 1b — Create Session Folder & Write Metadata [MANDATORY GATE]

**Complete this in full before calling any `jl data-product` tool.**

- Note: working_directory is an absolute path — ensure the folder is created at that exact absolute path and not interpreted as relative to any project root. This may cause folder duplication.

1. Compute `folder_name` using the Folder Name Computation rule.
2. Check if `<working_directory>/<folder_name>` already exists.
   - **Yes**: ask *"A folder named `<folder_name>` already exists. Overwrite it or use a different name?"* **[GATE]** wait.
     - Overwrite: proceed.
     - Different name: ask user to propose a new Technical Name, recompute `folder_name`, re-check. Do not proceed until a free name is confirmed.
   - **No**: proceed.
3. Check if `<working_directory>/assets/<folder_name>` already exists.
   - If it exists
      - Ask the user to propose a new Technical Name, recompute `folder_name`, re-check. Do not proceed until a free name is confirmed.     
   - If it doesn't exist
     - Proceed to the next step 
5. Run `mkdir -p <working_directory>/<folder_name>` silently. On success: store the path as `session_folder`. On error: show error, ask how to proceed.
6. Create `<session_folder>/work/` subdirectory silently.
7. Write `.ddp_metadata.json` into `<session_folder>/work/`:

> `source_dp_fqdns` is constructed from the search result: take `id` and append `.minor.patch` from `version` (drop the major segment). Example: `id = sap.s4com:dataProduct:MeasurementDocument:v1`, `version = 1.9.9` → `sap.s4com:dataProduct:MeasurementDocument:v1.9.9`. Never use `id` alone or `id + "." + version` verbatim.

> `applicationNamespace` will initially have a placeholder value. This will be updated in Step 5

```json
{
  "derived_dp_name": "<approved_name>",
  "source_dp_fqdns": ["<full_versioned_id_from_intent_analysis>"],
  "created_at": "<current UTC timestamp ISO 8601>",
  "metadata_approved": true,
  "header": {
    "name": "<approved_name>",
    "title": "<approved_title>",
    "description": "<approved_description>",
    "type": "derived",
    "shortDescription": "<approved_short_description>",
    "version": "1.0.0",
    "applicationNamespace": "c.bdc.<solution-id-encoded>",
    "responsible": "<approved_responsible>"
  }
}
```

**Before proceeding to Step 2, verify all four:**

- `session_folder` in context = `<working_directory>/<folder_name>`
- `<session_folder>/work/` directory exists
- `.ddp_metadata.json` exists inside `<session_folder>/work/`
- `folder_name` ends with `-data-product`

**Then sync the specification folder name:**

If a specification/ subfolder exists with a different name than <folder_name>, rename it to match:

```
mv specification/<placeholder> specification/<folder_name>
```

---

## Revisions — User changes their mind at any point

Any field or decision can be revised at any time. Apply the path below and return to the step you were interrupted from.

### Change input DP (after selection in `intent-analysis`)

1. Delete `session_folder` contents (keep the folder).
2. Re-run the search — call `dpca-mcp-server__ums_search_data_products` with new terms, display results, and wait for confirmation **[GATE]**.
3. Update `source_dp_fqdns` in `.ddp_metadata.json`.
4. Re-run Steps 2–6.

### Change Technical Name (after Step 1b)

Follow the Name Change rule below.

### Change Business Name / title (at any point)

1. Update `header.title` in `.ddp_metadata.json`.
2. If Step 5 ran: re-run `jl data-product generate-interop`.

### Change shortDescription / description (at any point)

1. Targeted edit to changed fields only in `.ddp_metadata.json`.
2. If Step 5 ran: re-run `jl data-product generate-interop`. *"Data product definition updated."*

### Change namespace (at any point after Step 1b)

1. Not directly settable in this tooling — `source_dp_fqdns` determines the namespace. Confirm with user.

### Add enrichment / change source DPs (after schema was fetched)

1. Call `dpca-mcp-server__ums_search_data_products` for the new DP.
2. Re-run `jl data-product fetch-and-prepare` with expanded `--data-products` (add `{ordId, tenantId}` for each new DP, using `id` and `tenant_uuid` from search result). This re-fetches, recompiles `transformation.cds`, and rebuilds `csn_graph.json` in one call.
3. Update `source_dp_fqdns` in `.ddp_metadata.json` — apply the `id + minor.patch` construction rule for each new DP.
4. Re-run Steps 4–5.

### Change filters / transformation (after view written)

Follow the refinement loop in Step 7.

---

## Rule: Name Change After Folder Created

Compute new folder name → check existence → propose updated names **[GATE]** → `mv` old to new silently → rename specification/<old_folder_name> to specification/<new_folder_name> if it exists → update `session_folder` → update only `derived_dp_name`, `header.name`, `header.title` in `.ddp_metadata.json` in `<session_folder>/work/` → if Step 5 ran, re-run `jl data-product generate-interop` → return to the step that triggered this rule.

---

## Step 2 — Generate Aggregated CSN and CDS

**Prerequisite check:** confirm `session_folder` ends with `-data-product` and `.ddp_metadata.json` exists inside `<session_folder>/work/`. If either false, complete Step 1b first.

### Step 2a. Fetch CSN and Prepare (CSN + CDS + graph in one call)

```bash
jl data-product fetch-and-prepare \
  --data-products '[{"ordId":"<ord_id1>","tenantId":"<tenant_id1>"},{"ordId":"<ord_id2>","tenantId":"<tenant_id2>"}]' \
  --session-dir <session_folder>/work
```

This single command fetches the aggregated CSN, compiles `transformation.cds`, and builds `csn_graph.json` — replacing what were previously three separate calls. No user output.

`--data-products` is always a JSON array of `{ordId, tenantId}` pairs, even for a single DP. `ordId` is the `ord_id` field from the search result (major version, e.g. `v1`) — NOT the full versioned `id` field.
See [TOOLING-CLI.md](references/TOOLING-CLI.md) for full reference.

→ **On success (`success: true`):** store `output_path` as `file_name_agg_csn`, `transformation_cds` as `file_name_agg_cds` (will be `<session_folder>/transformation.cds`), and `csn_graph_path` for the `csn-*` query tools.

- If `not_available_ids` non-empty: *"The schema for [not_available_ids] is not currently available. Continue with [successful IDs] only, or select a different source data product?"* **[GATE]**

→ **On failure:** nothing was written — do not store any path. (The command stops before compiling if zero data products were fetched or the CSN is empty.)

- All 404: *"Schema for all selected data products is not currently available. Select a different source data product?"* **[GATE]** Re-run the search inline (call `dpca-mcp-server__ums_search_data_products`) or ask the user to provide a different DP ID.
- Domain inactive: follow [TROUBLESHOOTING.md](references/TROUBLESHOOTING.md) → "Step 2: All domain schemas inactive".
- Other errors: show verbatim, ask *"Try a different DP, use only one, or investigate?"* **[GATE]**. "Investigate" means: read [TROUBLESHOOTING.md](references/TROUBLESHOOTING.md) → Step 2 for a matching error pattern, verify the DP ID format is correct, and retry before re-running the search.

### Step 2b. Fetch AMS Policies

Run immediately after Step 2a — reuses the same inputs. No user output.

```bash
jl data-product fetch-ams-policy \
  --data-products '[{"ordId":"<ord_id1>","tenantId":"<tenant_uuid1>"},{"ordId":"<ord_id2>","tenantId":"<tenant_uuid2>"}]' \
  --session-dir <session_folder>/work
```

`--data-products` is a JSON array of `{ordId, tenantId}` pairs — same values used in `fetch-and-prepare`. Each DP uses the `tenant_uuid` from its own search result entry.

Store `output_path` as `file_name_ams_policy`. No gate — proceed regardless of `policies_found` count (zero is valid; it means Scenario 2 will apply in Step 5b).

---

## Step 3 — Explore Schema, Detect Enrichments, and Build Cube

Recall transformation requirements from `intent-analysis` context.

### Schema Exploration (run silently — never show output to user)

An entity is relevant if: (a) its name or label contains words from the user's requirement, (b) it holds fields explicitly mentioned in the transformation, or (c) it is a FK join target of a primary relevant entity.

Call `csn-get-schema` **once**, passing **all** entities you plan to reference in a single `--entity-names '["<fqn1>","<fqn2>",...]'` array — do **not** call it separately per entity. The response is `{ "schemas": [ ... ] }`, one entry per entity. **Skip any `@virtual` field** — it does not exist in the Spark table and breaks at runtime.

For each planned join, **verify type compatibility before writing it**: check that the join key types on both sides match (e.g. String to String, Integer to Integer). If they differ — even if the column names look related — **do not write a silent broken join**. Surface it:

> *"[FieldA] on [EntityA] is [TypeA] but [FieldB] on [EntityB] is [TypeB] — they use different identifier systems and won't join meaningfully. Options:*
>
> - *Build from [EntityA] data only, grouped by the code as-is*
> - *Search for a bridging data product that maps [TypeA] → [TypeB]*
> - *Use a different source entity that shares the same identifier system"*
>
> **[GATE - FAST-TRACK EXEMPT] Wait for user choice even in Fast Track mode.**

For each planned `left outer join`: confirm the joined entity's PK from `csn-get-schema` key markers and include it in the SELECT list.

See [TOOLING-CLI.md](references/TOOLING-CLI.md) for the full `csn-*` command reference.

After exploration: state in one sentence which entities you will use and why, then continue.

### 3a. Detect Cross-DP References [GATE]

*(Run only if schema reveals unresolved FK signals. Skip to 3b if none.)*

Scan `file_name_agg_cds` for cross-DP FK signals from three sources:

**Source A — Annotated FKs:** `@EntityRelationship.reference` blocks with `referencedEntityType`. Check if the short name (part after last `:`) appears in `csn-list-entities` output. If not → unresolved.

**Source B — Composite references:** `compositeReferences` arrays with `referencedEntityType`. Same check.

**Source C — Unannotated FK fields:** Fields that are likely FKs if ALL of:

- Plain scalar type (String, Integer — not Composition or Association)
- Name or label suggests a distinct business object (Cost Center, Supplier, Plant, Company Code)
- That object is not in `csn-list-entities` output
- Value is clearly a code/ID, not descriptive text

Do NOT flag: date fields, amount/quantity fields, free-text descriptions, status codes. Ignore namespaces ending in `.gfn`. Deduplicate by `referencedEntityType`.

Only surface entries where joining the external DP provides a clear, concrete benefit to the user's stated requirement — e.g. resolving a code to a readable label, adding a missing dimension.

**If zero qualifying entries: skip to 3b.**

If qualifying entries found:

> **These columns link to external data that could improve your analytics. I haven't fetched those schemas yet — would you like me to explore them so I can give a definitive answer on what they add?**
>
> | Column in your data | Links to            | Likely benefit      |
> | ------------------- | ------------------- | ------------------- |
> | `<field label>`   | `<business name>` | *[plain English]* |
>
> *Explore, skip, or keep it simple?*

**[GATE - FAST-TRACK EXEMPT] Wait for answer even in Fast Track mode.**

- **Explore:** call `dpca-mcp-server__ums_search_data_products` for each entry. If zero results: *"No matching DP found for [entry] — skip it or try a different search term?"* **[GATE]**. If multiple: show as numbered cards, ask which to use **[GATE]**. Then re-run Steps 2a–3 with expanded `--data-products` (add `{ordId, tenantId}` for each new DP). Update `source_dp_fqdns` in `.ddp_metadata.json`. After fetching, confirm what was found and ask which to include.
- **Skip / keep it simple:** proceed to 3b.

### 3b. Suggest Enrichments [GATE]

*(Run only if associations point at entities already in `csn-list-entities` output **and** those associations provide a clear quality-of-life improvement for the stated requirement. Skip to 3c if none — do not manufacture suggestions.)*

Only suggest if it resolves a code to a readable label, adds a dimension the requirement implies but didn't name, or enables a meaningful aggregation otherwise impossible. If associations exist but none meet this bar, skip silently.

Use these exact commands — do not guess flag names:

**ALWAYS look up the exact flags in [TOOLING-CLI.md](references/TOOLING-CLI.md) before calling any `csn-*` command. Never infer or guess flag names — only use what is documented there.**

If qualifying associations exist:

> **Your schema already includes related data you could add:**
>
> - **`<Business name>`** — *[one line: what it concretely adds]*
>
> *Include any, or keep it simple?*

**[GATE - FAST-TRACK EXEMPT] Wait for answer before writing the view, even in Fast Track mode.**

### 3c. WHERE Clause Confirmation [GATE]

If the requirement includes any filter condition:

**First — check for Category 1 SparkMV violations:** if any filter uses `current_date()`, `current_timestamp()`, `now()`, `rand()`, `uuid()`, or `unix_timestamp()` without args — do NOT include it. State: *"The filter `<expression>` uses a non-deterministic function which will cause data product creation to fail. Which source date field should I use instead?"* Resolve before proceeding.

**Then — present confirmed filters as a table:**

| Column            | Business Label          | Filter Value             | Warning |
| ----------------- | ----------------------- | ------------------------ | ------- |
| `<column name>` | `<label from schema>` | `<value or condition>` |         |

**DATE-LITERAL WARNING:** if any filter value is a hardcoded date (YYYY-MM-DD, YYYYMMDD, named month), add a mandatory warning row: "DATE-LITERAL WARNING — hardcoded date will not update automatically." Ask: *"Use a source date column instead, or proceed with this fixed value?"*

Ask: *"Please confirm these filters are correct."* **[GATE - FAST-TRACK EXEMPT] Do not write the WHERE clause until confirmed, even in Fast Track mode.**

### 3d. Write the Cube

**Read [references/CDS-PATTERNS.md](references/CDS-PATTERNS.md) before writing.**

State: *"Proceeding to write the Transformation."* then write the accurate, optimized and best executable CDS SQL for the business question. Write the best query first.

When a metric type is ambiguous (risk indicator, score, flag, index), pick the basis with the most supporting fields available in the source schema — do not ask.

When you `SUM`/`AVG` an amount or quantity that carries a currency or unit-of-measure (its source field has `@Semantics.amount.currencyCode` or `@Semantics.quantity.unitOfMeasure`), project that currency/unit field and add it to the `GROUP BY` — per-currency / per-unit grain — do not ask. Never sum across mixed currencies/units into one number. The user can iterate to pin a single currency/unit (a `WHERE` filter) or add exchange-rate data to convert first, if they want a different shape.

Write it right the first time:

- Every non-aggregated column in `GROUP BY` when any aggregate is present.
- Every joined table earns its place — columns projected or filtered. No "might be useful" joins.
- No flat `LEFT JOIN` to a finer-grained child under `SUM`/`COUNT` — that double-counts. **If you detect a fan-out join (ON matches only part of the key or a non-key column) under an additive aggregate, surface it as a business question before writing:** *"To get correct totals for [X], I need to summarise [Y] first — that's the more accurate approach. Want me to proceed?"* **[GATE - FAST-TRACK EXEMPT] Wait for confirmation before writing, even in Fast Track mode.** On yes: pre-aggregate the child. On no: proceed without the join.

After the SQL is correct, add `@Analytics.dimension : true` to every grouping/dimension column (codes, categories, dates, names, key columns). Apply silently — never ask the user about annotation choices.

One view per workflow; if a prior view exists (identified by the `@EndUserText.label` annotation stamped during a previous iteration's Step 4), replace it in-place — never add a second. If annotation is missing or multiple annotated views are found: stop, state "CDS structure error — fix or rewrite view before continuing", do not call `jl data-product generate-interop`.

**To replace an existing view:** find `@EndUserText.label`, replace the entire block from that annotation line through the closing `}` (or `};`) with the new view body only (no annotations). The annotation is re-stamped at the end of this iteration's Step 4.

Append the new view to the END of `file_name_agg_cds`. See [CDS-PATTERNS.md](references/CDS-PATTERNS.md) for entity syntax, cast rules, SparkMV compatibility rules, alias rules, and JOIN guidance.

**If a schema issue prevents writing the planned view:** either (a) write a reduced view using only entities that work and surface a one-sentence note, OR (b) ask: *"I encountered a schema issue with [entity] — proceed without it, or select a different source data product?"* **[GATE]** Never call `jl data-product generate-interop` without a `define view` appended.

---

## Step 4 — CDS Self-Check [MANDATORY GATE — silent]

Run the (slimmed) self-check from [CDS-PATTERNS.md](references/CDS-PATTERNS.md) internally. **Do not display or output the list, checkmarks, or intermediate results.**

> Structural, syntax, and SparkMV rules are now **enforced automatically** — `dp-gen cds-to-sql` (Step 11) and `dp-gen generate-interop` (Step 8) compile the CDS and run AST assertions, failing with the exact rule and line if the cube is invalid. Step 7 only pre-checks the handful of items the tool cannot judge (file position, alias naming, correlated subqueries,join type-compatibility) **plus the Intent-match group — whether the cube's grain, measures, and relative metrics actually deliver the approved spec. A cube can compile clean and still answer the wrong question; the compiler cannot see this, so the self-check must.**

> **Run the check by citation, not by ticking.** For every assertion marked **[CITE]** in the list, resolve it by quoting the specific cube token(s) that satisfy it (the `key`/`GROUP BY` element, the `source AS alias` pair, the approved-spec line, the `OVER(...)` denominator). If you cannot quote the tokens, it FAILS. If the quoted tokens contradict the promise (declared grain "by County" but the only `key` is `S.Supplier`), that is a FAIL — fix the cube, do not re-tick. A checkmark is satisfiable by a misread; a citation is not.

- **All pass:** state "CDS validated." then proceed to Step 5.
- **Any fail (Step 4 pre-check, OR the automated gate at Step 5):** state which rule failed and what you changed, fix it, re-run.
- **Same failure after 2 attempts:** stop. State what is failing and what was tried. Ask: *"I was unable to satisfy [rule] — would you like to simplify the cube or adjust the transformation?"*

After the Step 4 pre-check, run the three correctness passes from [references/CDS-PATTERNS.md](references/CDS-PATTERNS.md) as silent internal reasoning:

- **Pass 1 — Semantic**: column binding, type sanity, aggregate nesting, NULL semantics
- **Pass 2 — Join minimization**: DROP dead joins, FLAG suspicious ones, re-run to fixpoint
- **Pass 3 — Fan-out reshaping**: detect partial-key joins under aggregates; surface RESHAPE question if found, apply answer

Fix in place after each pass. Re-run Pass 1 after any Pass 2 DROP or Pass 3 reshape.

Stamp `@EndUserText.label` immediately before `define view` — no gap, no other annotations between them:

```cds
@EndUserText.label : '<Human readable label>'
define view <TransformationPurposeCube> as select from ...
```

---

## Step 5 — Create Data Product Definition [MANDATORY GATE]

## Step 5a — Data Product Definition Interop Generation [MANDATORY GATE]

**Namespace Construction Steps**

1. Retrieve the Solution ID (UUID) from the current session context
2. Strip hyphens from the solution UUID to get a 32-char hex string
3. Convert the hex string to a base-10 integer
4. Encode the integer in Base36 (lowercase a-z + 0-9)
5. Compose the namespace as c.bdc.<base36>

Update `applicationNamespace` in `.ddp_metadata.json` using the newly computed namespace

Only call `jl data-product generate-interop` after ALL true:

1. `file_name_agg_cds` was modified in Step 3d
2. The Step 4 pre-check passed
3. `applicationNamespace` in `.ddp_metadata.json` has been updated and no longer uses a placeholder value

`jl data-product generate-interop` validates the CDS itself (compile + AST assertions) before producing the `.dpd` — if the cube is invalid it returns `{"success":false,"error":"CDS validation failed: ..."}` naming the exact rule/line. Read that, fix the cube, and re-run. **`jl data-product generate-interop` is the ONLY valid way to produce the interop file. Never construct it manually.**

```bash
jl data-product generate-interop \
  --modified-cds <file_name_agg_cds> \
  --agg-csn      <file_name_agg_csn>
```

Store `output_interop_path` from the response.

**If "No transformed entities found":** run `grep -m 1 "^define view" <file_name_agg_cds>` internally. If missing: view was not written — re-run Step 3d. If present: view body is empty — re-run Step 4 before retrying.

**If CDS parse or syntax error:** read the line number. If inside the transformer view (≥ `define view` line): targeted fix only — never rewrite the full cube. If inside source entity definitions (< `define view` line): unresolvable schema issue — ask user to select a different source DP. See [TROUBLESHOOTING.md](references/TROUBLESHOOTING.md) → Step 5.

**If a DPD Validation error occurs**: Read and understand the validation errors. **Do not directly modify the DPD Interop File.** If the validation is failing in the header section, please check the **.ddp_metadata.json** file, make the changes to the fields accordingly, and regenerate the interop. If the validation is failing elsewhere, please only inform the user.

**If a CSN Validation error occurs**: Read and understand the validation errors. **Do not directly modify the DPD Interop File.** Please refer to [CDS-PATTERNS.md](references/CDS-PATTERNS.md) and [TROUBLESHOOTING.md](references/TROUBLESHOOTING.md) to diagnose the issue. Based on the issues identified, make the changes to the CDS file and regenerate the interop.

**If same error recurs after 2 fix attempts:** remove the cube view, state the problem, ask: *"I was unable to resolve this. Simplify the transformation or use different source entities?"*

State: "Data product definition created." then proceed to Step 5b.

---

## Step 5b — Authorization Management Service Base Policy [MANDATORY GATE]

Run immediately after `generate-interop` succeeds. No user prompt needed — proceed automatically.

### Step 5b-i — Fetch Candidates

```bash
jl data-product fetch-ams-candidates \
  --dpd <output_interop_path> \
  --policy-file <file_name_ams_policy>
```

Use `file_name_ams_policy` stored in Step 2b. See [TOOLING-CLI.md](references/TOOLING-CLI.md) for full reference.

**On success:**

- If `recommended`, `alsoRecommended`, and `available` are all empty: state *"No authorization-eligible fields found — AMS policy skipped."* Proceed to Step 6.
- Otherwise: present the results as follows.

---

#### Display format — `source: "input-policy"`

Open with:
> **Authorization Policies in Authorization Management Service** - Title
> "Authorization Policies control who can access data in your data product. Based on your source data products, **N column(s)** were already exposed to authorization policies and have been carried forward:"

Display the `recommended` fields **grouped by source DP business name** (derive the business name from `sourceDP`, e.g. `sap.s4com:dataProduct:SalesOrder:v1` → "Sales Order", `sap.s4com:dataProduct:BillingDocument:v1` → "Billing Document"). Within each group, list each field using a **continuous number** (never reset per group) using the `label` (or `field` if label is absent). Ensure that each field is displayed on a **separate line as part of a numbered list**. If two fields share the same label, disambiguate by appending the field name in parentheses:

**Rendering Note:** Use escaped numbering (1\., 2\.) to maintain continuous count across groups. Place a blank line between each item to ensure each field renders on its own separate line.

```
**<Source DP Business Name>**

1. <label or field>
2. <label or field>

**<Source DP Business Name>**

3. <label or field> (shared with <Other DP Name> — attributed once above)
```

Numbering is continuous across all groups — `recommended` starts at 1, `alsoRecommended` continues from where `recommended` left off. This lets users select by number without ambiguity (e.g. "use 1, 3, 7").

If a field from one source DP duplicates a field already listed under another source DP, show it with a note: *(shared with \<Other DP Name\> — attributed once above)*.

If a source DP's policy fields were not projected into the cube, add a note below that group:
> Note: `<FieldName>` is in the \<Source DP Name\> policy but was not projected into the cube, so it cannot be carried forward.

If `alsoRecommended` is non-empty, follow with:
> "I'm also recommending **N additional column(s)**:"

Display `alsoRecommended` in the same grouped format.

Then always close with:
> *"Should I expose these? Or do you have other columns in mind? There are also **N additional columns** available that can be part of the AMS policy — would you like to see those?"*

Where N = count of dimension-only fields in `available` (exclude any field annotated with `@Aggregation.default` — measures are not meaningful AMS candidates).

---

#### Display format — `source: "derived-dp"`

Open with:
> "No existing Authorization Management Service policy was found in your source data products. Based on your cube, I'm recommending the following dimension fields for authorization:"

Display `recommended` grouped by `outputObject` (same bullet format as above).

Ask:
> *"Should I expose these for authorization? Or do you have other columns in mind?"*

---

#### "Show all columns" response

If the user asks to see all columns or asks what else is available:

State:
> *"Here are all the columns available across your output objects. Let me know which you'd like to expose to authorization policies (e.g. `A1` or `all from A`):"*

Combine ALL candidates (`recommended` + `alsoRecommended` + `available`) into one flat list — **`recommended` fields MUST be included here even if already shown above**. Then **exclude measure fields** (any field annotated with `@Aggregation.default` — SUM, COUNT, NOP — is not a meaningful AMS candidate and must not appear), then group the remaining dimension fields by `outputObject`. Assign a letter prefix (A, B, C…) to each group in the order they appear. Number fields within each group starting at 1. Use business labels (not technical field names) in the list. **Ensure that the list follows the below given format**:

```
**A. <Output Object Business Name>**

 1. <label>
 2. <label>

**B. <Output Object Business Name>**

 1. <label>
 2. <label>

**C. <Output Object Business Name>**

 1. <label>
```

Accept any of these selection formats (alone or comma-separated):
- `A1` — field 1 from group A
- `all from B` — all fields in group B
- `all` — every field across all groups
- `A1, A3, all from B` — mix

---

**[GATE] Wait for explicit selection. Resolve the selection to a flat list of field names. Store as `ams_approved_fields`.**

### Step 5b-ii — Inject Policy

```bash
jl data-product inject-ams-policy \
  --dpd <output_interop_path> \
  --fields '<ams_approved_fields as JSON array>'
```

**On success:** state *"AMS policy injected."* Proceed to Step 6.

**On error:** show error verbatim. Ask: *"Retry with a different field selection?"*
- Yes: return to Step 5b-i display (re-use already-fetched candidates, do not re-call `fetch-ams-candidates`).
- No: state *"AMS policy skipped."* Proceed to Step 6.

---

## Step 6 - Setup of Solution [MANDATORY GATE]

1. **External skill (preferred):** Call the `setup-solution` skill to create the required solution folder structure and files.

### Self-Check (run internally — do not show to user)

Verify: (a) old session folder deleted from filesystem, (b) solution tracking inspected independently, (c) old folder name absent from tracking, (d) if still present: remove explicitly and re-inspect, (e) DP folder inside `assets/` in filesystem, (f) DP folder inside `assets/` in solution tracking.

State "Solution structure verified." on pass. On failure: state what is wrong and fix it. See [TROUBLESHOOTING.md](references/TROUBLESHOOTING.md) → Step 6 for phantom folder recovery.

#### Example of 'Ghost Entry/Phantom' folder and how the folder structure SHOULD NOT look like

If the old session folder still exists somewhere in the file system or solution apart from the assets folder, please delete it.

```
├── assets/
│   └── data-product/    # Contains product-specific data files
│       ├── work/
│       │   └── CSN JSON Files
│       ├── DPD Interop File
│       ├── CDS Transformation File
│       └── asset.yaml
├── data-product/        # Old Session Folder
└── solution.yaml
```

---

## Step 7 - Iterative Refinement Loop [MANDATORY GATE]

Ask: *"Would you like to preview the data, make changes, or is it ready to approve?"*

### SparkMV Gate [check before every CDS change]

**Category 1 — Hard failures (do not proceed):** `current_date`, `current_timestamp`, `now`, `rand`, `uuid`, `unix_timestamp` without args. If change uses any: *"This change uses `<function>` which will cause data product creation to fail. Use a field from the source entity instead."* Do not apply.

**Category 2 — Performance degradation (gate required):** `DISTINCT`, subqueries (`EXISTS`, `NOT EXISTS`, FROM subquery), window functions, `HAVING` clause. If change uses any: *"This change will cause significantly slower data updates. Proceed, or use an alternative?"* **[GATE] Wait for confirmation.** If user declines: propose an incremental-compatible alternative (for `HAVING`: move a row condition to `WHERE`, or apply an aggregate condition downstream instead of in the cube). If none exists: *"No incremental alternative — this will always do a full recompute. Proceed anyway?"* **[GATE]**

### On CDS change request (filter, join, new field, transformation)

1. If change involves entities/fields not yet explored, re-enter the Step 3 exploration sequence first.
2. State in one sentence what changes and why.
3. Apply change — modify existing cube in-place, or append new cube only if user explicitly asked for a separate output port.
4. Write updated cube to `file_name_agg_cds` — modify only the transformer view; never touch entity definitions above it.
5. Re-run Step 4 self-check internally.
6. Run `jl data-product generate-interop --modified-cds <file_name_agg_cds> --agg-csn <file_name_agg_csn>`. Store updated `output_interop_path`. Do not ask the user before calling this — proceed directly. If `ams_approved_fields` is in context, re-run Step 5b in full (fetch-ams-candidates → present updated recommendations → wait for re-approval → inject) — the DPD has changed and the previous field selection may be stale. Clear `ams_approved_fields` from context before re-entering Step 5b so the user is prompted for a fresh selection.
7. Check that `description` and `shortDescription` in `.ddp_metadata.json` still accurately describe what the cube now does. If either has drifted, show current vs. proposed for the changed field(s) and ask *"Update the description to match?"* **[GATE - FAST-TRACK EXEMPT]** — on yes, edit only the drifted field(s) and re-run `generate-interop` once more (do not re-run this check on that regeneration). If both still fit, say nothing.
8. State: "Data product definition updated. Please review." Ask: *"Does this look right, or would you like further changes?"*

### On metadata change (title, description, shortDescription)

Follow the title/description revision procedure in the Revisions section above.

### On name change

Follow the Name Change rule above, then return to Step 7.

### Exit only when

User uses an unambiguous approval phrase: "looks good", "approve", "approved", "done", "ship it", or equivalent affirmative. Do not treat "ok", "fine", "sure", or silence as approval.

Once approved: proceed to Step 7b.

## Step 7b — Data Preview [MANDATORY GATE]

Ask the user if they would like to preview the data

Data preview is not available via the `jl data-product` plugin.

You **must** not read the DPD Interop or CDS Files directly as this will use up the context

Execute the following Python Script to retrieve the Target and Transformation sections of the DPD. 

Set $DPD_FILE to the path of the .dpd file found in the asset folder

```bash
python3 -c "import json; d=json.load(open('$DPD_FILE')); print(json.dumps({k:d['definition'][k] for k in ['target','transformation']}, indent=2))"
```

Analyze the retrieved sections and generate **only 5** rows of realistic mock preview data

Display the table in the chat for the user. Fields are ALWAYS columns (headers). Records are ALWAYS rows. Never transpose.

After user approval: *"Data product has been created. Use the deploy option in Joule Studio to deploy."*
