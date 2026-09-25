# Data Product Generation Guidelines

Technical constraints and patterns for building SAP Derived Data Products. Follow these throughout specification execution.

## Tech Stack

- SAP Data Product Store (DPS)
- CDS (Core Data Services) transformation views
- SAP Data Product Generation workflow (`data-product` skill)
- `jl data-product` CLI plugin (installed in Step 0)

## Scope

**Derived Data Products only** — builds analytical products from existing primary data products via CDS transformation. Does not create primary data products or replicate raw data.

## Key Constraints

- **Never reuse identifiers, names, or values verbatim from examples** in this file or the `data-product` skill.
- All file tool paths (`write_file`, `read_file`, `list_files`, `delete_file`) are relative to the solution root — never pass absolute paths to file tools.
- `pwd` is the only command that uses absolute paths, solely for resolving MCP tool arguments.

## Naming Rules

- **Technical Name (`name`)**: 1–70 characters, no spaces, CamelCase (e.g. `SalesOrderAnalytics`)
- **Business Name (`title`)**: derived from `name` by adding spaces between words unless user specifies otherwise
- **Folder name**: convert `name` from CamelCase to kebab-case and append `-data-product` (e.g. `SalesOrderAnalytics` → `sales-order-analytics-data-product`)
- Folder name must be all lowercase, dashes only, no spaces, ends with `-data-product` — verify before any shell command

## Workflow

The full data product creation follows the `data-product` skill (Steps 0–7b). When invoked from `specification`, search and selection have already been completed during `intent-analysis` — run Step 0, then resume from Step 1a. Key integration points:

- **Step 0** — Install `jl data-product` CLI plugin (always run)
- **Step 1a** — Propose and approve properties (`name`, `title`, `shortDescription`, `description`)
- **Step 1b** — Create session folder and write `.ddp_metadata.json`
- **Step 2** — Fetch CSN, compile to CDS, and build the CSN graph in one call (`jl data-product fetch-and-prepare`)
- **Step 3** — Explore schema, detect enrichments, build analytical cube view
- **Step 4** — CDS self-check (slimmed pre-check + 3 correctness passes — silent; structural/syntax/SparkMV rules auto-enforced by the CLI at Step 5)
- **Step 5** — Generate interop definition (`jl data-product generate-interop`)
- **Step 6** — Setup solution: invoke `setup-solution` skill
- **Step 7** — Iterative refinement loop — exit only on explicit user approval
- **Step 7b** — Data preview (`jl data-product ddp-data-preview`)

## Mandatory Gates (cannot skip)

| Gate | Step |
|------|------|
| Properties approval | 1a |
| Session folder + metadata | 1b |
| Input DP confirmation (CSN fetch) | 2a |
| CDS self-check | 4 |
| Interop definition created | 5 |
| Setup Solution | 6 |
| Refinement approval | 7 |
| Data preview | 7b |

## Terminology

- Use **"Objects"** (not "Artifacts", "Entities", or "Tables")
- Use **"Columns"** for Relational Dataset semantic usage; use **"Attributes"** for Dimension, Fact, Text, Hierarchy
- Use **"Business Name"** instead of "Title"; **"Technical Name"** instead of "Name"
- Use **"create"** (not "generate") when creating a data product or object
- Do not use emojis
