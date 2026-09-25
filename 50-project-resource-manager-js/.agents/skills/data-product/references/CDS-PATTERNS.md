# CDS Patterns and Validation

This document covers CDS syntax, cube format, query rules, SparkMV compatibility, and the unified self-check. Consult it **before writing any cube**.

---

## CDS Modification Rules

- NEVER modify existing entity definitions in the CDS file
- Append new CDS at the END of the file only
- One transformer view per transformation request unless the user explicitly asks for a separate output port
- **Comments: always use `//` syntax. Never use `--`. The CDS compiler rejects SQL-style `--` comments with a parse error.**

---

## Transformer View Format

```cds
@EndUserText.label                 : '<Human readable label>'
define view <TransformationPurposeCube> as select from ![<namespace:api:Resource:version>].<Entity> as <A>
  inner join ![<namespace:api:Resource:version>].<OtherEntity> as <B> on <B>.<fk> = <A>.<pk>
{
  key <A>.<primaryKeyField>   as <keyAlias>,
  <B>.<field>                 as <alias>,
  cast(<expression> as <Type>) as <computedAlias>
}
```

View name: based on the transformation purpose, not the data product name (e.g. `SalesByRegionCube`, `BillingStatusByCategoryCube`).

---

## Entity Name Syntax

### In `select from` and `join` clauses

Tool outputs return fully qualified names like:
```
your.namespace:apiResource:EntityName:v1.EntityObject
```

The generated CDS file uses:
```cds
entity <dotted.namespace>.![<colon:part>].<Entity>
```

The dot-separated namespace prefix stays as-is; only the colon-containing segment gets `![...]` wrapping.

### How to find the split point

Run this silently to find the first entity declaration — do not open the full file:

```bash
grep -m 1 "^entity " <session_folder>/transformation.cds
```

The first entity declaration gives you the pattern:
```cds
entity your.![namespace:apiResource:EntityName:v1].EntityObject
```
- Prefix before `![` → namespace prefix (e.g. `your`)
- Part inside `![...]` → everything up to the last dot (e.g. `namespace:apiResource:EntityName:v1`)
- After closing `]` → entity name (e.g. `EntityObject`)

Apply the same split to every entity FQN returned by the `csn-*` query tools. Never open the full CDS file to find this — the pattern is always identical across all entities in the same file.

---

## SQL Conventions

- UPPERCASE all SQL keywords: `SELECT FROM WHERE JOIN ON GROUP BY HAVING ORDER BY CASE WHEN THEN ELSE END AND OR NOT NULL AS DISTINCT COUNT SUM MIN MAX AVG`
- Qualify every column with its table alias: `P.code`, never bare `code`
- Each selected column on its own line
- Meaningful aliases from business name — never `T1`, `T2`, `Join1`
- Never `SELECT *` or `Alias.*` — list columns explicitly

### CASE format

```cds
CASE
  WHEN <condition> THEN <value>
  ELSE <default>
END as <alias>
```

Never a magic literal without an inline comment: `WHEN status = 'A' // A = Active`

### COALESCE preference

Use `COALESCE(expr, default)` over verbose `CASE WHEN IS NULL`. Both work; COALESCE is shorter and clearer.

---



**EVERY computed/derived column MUST have an explicit `cast(... as <Type>)`.**

This includes: arithmetic expressions, CASE/WHEN expressions, string concatenation with `concat()`, any expression that is not a bare field reference.

| Type | When to use |
|---|---|
| `Decimal(17,5)` | Numeric calculations |
| `String(<length>)` | String constructions |
| `Integer` | Integer calculations |
| Source field type | When result matches source type |

```cds
// WRONG:
(coalesce(A.amount, 0) - coalesce(A.baseAmount, 0)) as delta

// CORRECT:
cast((coalesce(A.amount, 0) - coalesce(A.baseAmount, 0)) as Decimal(17,5)) as delta
```

---

## Column Alias Rule

**Column alias MUST match the source column name exactly, including casing.**

`A.id AS id`, `P.code AS code`, `B.startDate AS startDate`. Never invent a name, add a prefix, abbreviate, or change case. **A name that combines the table name with the column name (e.g. `CategoryTextLanguage` from `CategoryText.Language`) is always WRONG — use the bare column name (`Language`).**

Exceptions:
- (a) the user explicitly requests a specific alias
- (b) it is a computed expression with no source column (e.g. `CASE ... END AS statusLabel`)
- (c) two joined tables have a column with the same name and both are selected — disambiguate with a minimal prefix (e.g. `BLanguage`) and add an inline comment documenting the collision

```cds
// WRONG (invented descriptive name):
CategoryText.Language AS CategoryTextLanguage

// WRONG (wrong case, abbreviated):
A.id AS rowId,
P.code AS Code

// CORRECT (bare column name):
CategoryText.Language AS Language,
A.id AS id,
P.code AS code
```
```

---

## Personal Data Annotations

`@PersonalData.*` annotations propagate **automatically** — the CDS compiler carries them from a source field to the cube element for any **direct column reference**: plain passthrough, renamed alias, a field from a joined entity, or a GROUP BY dimension. Do **not** manually re-declare them on directly-referenced columns.

**The one exception — computed columns.** A **computed** column (`concat`, `upper`, `CASE`, arithmetic, etc.) derived from a personal-data field becomes `@Core.Computed` and **loses** the source `@PersonalData.*` annotation, even though the derived value may still be personal data (an uppercased customer id is still a customer id; a concatenated first+last name is still a name). For such a column:

- If the derived value **is still personal data** → re-declare the `@PersonalData.*` annotation on the computed column.
- If it is **not** personal (a hash, a bucket, a boolean flag) → leave it off.

```cds
// direct ref — annotation propagates automatically, do NOT re-declare:
C.CustomerId                          as CustomerId,

// computed from a personal-data field — re-declare if still personal:
@PersonalData.isPotentiallyPersonal : true
@PersonalData.fieldSemantics        : #DATA_SUBJECT_ID
cast(concat(C.FirstName, C.LastName) as String(80)) as FullName
```

The validator surfaces this as a non-blocking `PD1` warning — it names the computed column and the personal-data source element, and leaves the decision to you. It never blocks and never auto-adds.

---

- Every view MUST have at least one element marked `key`
- Use the primary key field(s) of the driving (FROM) entity — obtain from `csn-get-schema`
- Mark: `key <Alias>.<pkField> as <alias>`
- **Skip any key field that has a `@virtual` annotation** — it is a pipeline-injected synthetic column that does not exist in the underlying Spark Delta table and will silently break at runtime. Do not reference it in SELECT lists, JOIN conditions, or as a `key` element in the cube.

When an entity has multiple key fields, prefer the one with a descriptive `@EndUserText.label` (e.g. "Person UUID", "Assignment UUID", "Cost Center"). A key field with label "Id" or "_id" and no business context is an internal row identifier — join on the parent entity's FK instead.

---

## Column Projection Rules

- Select only columns needed. Never use `SELECT *` or `Alias.*` — list explicitly
- Place each selected column on its own line in the projection block
- Order: `key` columns first → measures → dimensions → descriptive/label columns
- Qualify every column reference with its table alias (e.g. `P.companyCode`, not bare `companyCode`)

---

## JOIN Strategy

- Use **`left outer join`** as the default when a dimension/text entity may have no matching row
- Use **`inner join`** only when a match is guaranteed (key relationship confirmed in entity definition)
- Never use `cross join` unless there is truly no join condition and no FK exists
- Join on indexed key columns only — read `key` markers from the entity definition
- Never repeat the same join twice — resolve all needed columns in a single join per entity
- Never embed filter conditions inside `ON` clauses — use a standalone `WHERE` clause

**4+ tables:** wrap the first group in a subquery to stay within one nesting level:
```cds
SELECT FROM (
  SELECT FROM PrimaryEntity AS P
  LEFT OUTER JOIN SecondEntity AS S ON S.id = P.sId
  { P.key, P.field1, S.name }
) AS Base
LEFT OUTER JOIN FourthEntity AS F ON F.id = Base.key
{ Base.key, Base.field1, Base.name, F.detail }
```

---

## Filter and Aggregate Placement

**WHERE** — row-level filters only. Never embed in `ON` clauses.

**HAVING** — avoid. A `HAVING` filters on an aggregate that changes with every source delta, so SparkMV cannot maintain the cube incrementally — it degrades to full-refresh-only (significantly slower updates). Do not emit `HAVING`.

- **Row-level condition** (references only plain columns, no aggregate) → put it in `WHERE`, never `HAVING`.
- **Aggregate-level condition** (references `SUM`/`COUNT`/etc.) → do NOT filter it in the cube at all. Leave the aggregate unfiltered in the materialized cube and let the consuming query / BI tool apply the aggregate threshold at read time. Materializing an aggregate filter is exactly what forces full-refresh.

```cds
// WRONG: HAVING forces the cube to full-refresh-only
WHERE P.status = 'ACTIVE'
GROUP BY P.categoryCode
HAVING SUM(P.amount) > 0

// CORRECT: row filter in WHERE; no aggregate filter in the cube (apply it downstream)
WHERE P.status = 'ACTIVE'
GROUP BY P.categoryCode
```

When filtering on a nullable column: use `IS NOT NULL` guards to prevent silent row drops on outer joins.

Pre-filter before a join when only a subset of the driving entity is needed — use a flat subquery with its own `WHERE` rather than filtering after the join.

---

## Statement Termination

- A view ending with `}` (projection list is the last thing, no trailing clause) does not need a `;`
- A view ending with **any trailing clause after `}`** — `where`, `group by`, `having`, or `order by` — MUST end with `;` after the last token of that clause. This includes aggregation cubes, which end on `group by`.

---

## Update vs New Cube

| Trigger | Action |
|---|---|
| Any transformation (filter, new field, join) | Modify **existing** cube in-place |
| User says "separate output table/port" or "another output for..." | Append **new** cube with unique name |

---

## SparkMV Compatibility Rules

The `.dpd` is consumed by the FOS/SparkMV pipeline. CDS that compiles cleanly can still break or silently degrade at the Spark layer.

### Category 1 — Hard Failures (MV creation fails entirely — do not use)

These patterns cause data product creation to fail. They are hard-blocked — do not use them under any circumstance. If a user requests a transformation that requires one, inform them: *"This change uses `<function>` which will cause data product creation to fail. Please use a field from the source entity instead."*

| Forbidden | Why | Alternative |
|---|---|---|
| `current_date()` | Non-deterministic | Use a source date column |
| `current_timestamp()` / `now()` | Non-deterministic | Use a stored timestamp from source |
| `rand()` / `uuid()` | Non-deterministic | No alternative — do not use |
| `unix_timestamp()` with no args | Time-dependent | Use `unix_timestamp(expr)` with a column arg |

### Category 2 — Performance Degradation (full-refresh forced)

These do not break MV creation but permanently force full-refresh, causing significantly slower data updates. Gate the user before using any of these patterns: *"This change is not recommended — it will cause significantly slower data updates. Would you like to proceed anyway, or try a different approach?"*

**DISTINCT** — not supported for incremental maintenance. Use GROUP BY with `COUNT(*)` instead.

**Subqueries (`EXISTS`, `NOT EXISTS`, FROM subquery)** — cannot be incrementally maintained. Replace with a JOIN:
```cds
// WRONG: EXISTS subquery (full-refresh only)
where exists (select 1 from ... as H where H.parentId = P.id)

// CORRECT: inner join (incremental)
inner join your.![namespace:apiResource:EntityName:v1].HierarchyNode as H
  on H.parentId = P.id and H.groupId = P.groupId
```

**Window functions** (`ROW_NUMBER`, `RANK`, `DENSE_RANK`, `LAG`, `LEAD`, `SUM() OVER (...)`) — no incremental alternative.

### Category 3 — OUTER JOIN Requirements

Apply whenever any `left outer join` / `right outer join` / `full outer join` is used.

**3.1** In `A left outer join B`, all of A's PK columns MUST appear in the SELECT list as `key` elements.

**3.2** The null-supplied side (B) MUST contribute at least one non-nullable column. **B's PK columns are always non-nullable and satisfy this — the safest default is to always include the joined entity's PK in the SELECT list.** If you are unsure which columns are non-nullable, include the joined entity's PK (confirmed from `csn-get-schema` key markers) — this always satisfies 3.2.

**3.3** The ON clause MUST reference columns from both sides:
```cds
// WRONG: only references one side
left outer join CategoryDim as CAT on CAT.categoryCode = 'A'

// CORRECT: references both sides
left outer join CategoryDim as CAT on CAT.categoryCode = P.categoryCode
```

**3.4** If any WHERE clause condition references a column from the null-supplied side (B) of a left outer join, wrap it with a null guard to prevent the outer join from being silently converted to an inner join:
```cds
// WRONG: silently drops rows where B had no match (converts outer join to inner join)
where CAT.categoryCode = 'A'

// CORRECT: preserves rows where B had no match
where (CAT.categoryCode = 'A' or CAT.categoryCode is null)
```

### Category 4 — Aggregation Cube Requirements

**4.1 Nullable `SUM` requires a paired count column:**
```cds
cast(SUM(A.quantity) as Decimal(17,5)) as totalQuantity,
cast(case when A.quantity is not null then 1 else 0 end as Integer) as quantityCount
```

**4.3** Aggregates cannot be nested in expressions — expose each as its own column.

**4.5 Semantic annotations — dimensions only.** Apply `@Analytics.dimension : true` to grouping attributes (codes, categories, dates, names, key columns). Apply silently, never ask the user:

```cds
@Analytics.dimension : true
key P.id                              as id,
@Analytics.dimension : true
    P.name                            as name,
    cast(SUM(A.quantity) as Decimal(17,5)) as totalQuantity
```

**4.6 Currency / unit-of-measure — group by it, never sum across it.** A summed amount is denominated in a currency; a summed quantity in a unit of measure. Summing across mixed currencies (USD + EUR) or units (kg + pallets) yields a meaningless number. When you `SUM`/`AVG` a field whose source carries `@Semantics.amount.currencyCode` or `@Semantics.quantity.unitOfMeasure`, project that currency/unit field and add it to the `GROUP BY` — per-currency / per-unit grain. Apply silently — do not ask. The user can iterate later to pin a single currency/unit (`WHERE Curr = 'USD'`) or add exchange-rate data to convert first, if a different shape is wanted.

```cds
@Analytics.dimension : true
    I.TransactionCurrency                as TransactionCurrency,   // ← currency in the grain
    cast(SUM(I.NetAmount) as Decimal(17,5)) as totalNetAmount
// ... group by ..., I.TransactionCurrency
```

### Category 5 — UNION ALL

Each UNION ALL block must include a unique constant string column so SparkMV can track which block each row came from. Use a short descriptive label that identifies the block's business meaning — the column name and value are your choice, they just must be unique across blocks:

```cds
// first block
cast('primary' as String(20)) as dataSource,

// second block
cast('secondary' as String(20)) as dataSource
```

The column name (`dataSource` above) and each block's value (`'primary'`, `'secondary'`) can be anything meaningful — avoid generic names like `mv_union_unique_column` or `block_a`.

### SparkMV Decision Table

| Pattern | Incremental? | Action |
|---|---|---|
| `current_date()` / `current_timestamp()` | BROKEN — hard failure | Hard block. Inform user, do not proceed. |
| `rand()` / `uuid()` / `unix_timestamp()` no args | BROKEN — hard failure | Hard block. Inform user, do not proceed. |
| `DISTINCT` | Full-refresh only | Gate user before proceeding |
| `EXISTS` / `NOT EXISTS` subquery | Full-refresh only | Gate user; prefer INNER JOIN / LEFT JOIN + NULL check |
| FROM subquery (inline view) | Full-refresh only | Gate user; prefer flattened JOINs |
| Window functions (incl. `SUM() OVER (...)` as a measure) | Full-refresh only | Gate user; no incremental alternative |
| `HAVING` clause | Full-refresh only | Do not emit. Row condition → `WHERE`; aggregate condition → apply downstream, not in the cube |
| `left outer join` | Incremental ✓ | Cat 3 requirements apply |
| OUTER JOIN ON clause | Incremental ✓ | Must reference both sides |
| Aggregation cube (GROUP BY) | Incremental ✓ | Must include `COUNT(*)` measure; nullable SUM needs paired COUNT |
| `SUM`/`AVG` of amount/quantity with `@Semantics` currency/unit | Incremental ✓ | Project the currency/unit field and add it to `GROUP BY` (per-currency/unit grain) — never sum across mixed currencies/units |
| `SUM(A) + SUM(B)` as one column | Full-refresh only | Emit each SUM as its own column |
| UNION ALL | Incremental ✓ | Each block needs a unique constant string column with a meaningful name and value |
| `inner join` | Incremental ✓ | No special requirements |
| `CASE WHEN`, `COALESCE`, `CAST` | Incremental ✓ | No restrictions |
| Standard WHERE filters | Incremental ✓ | AND / OR / IN / BETWEEN / IS NULL — all fine |

---

## Unified CDS Self-Check (Step 4)
Run these assertions internally before calling `jl data-product generate-interop`.Run this SILENTLY — do not output the list or checkmarks to the user.

**How to run this check — cite, do not tick.** A checkmark is satisfiable by a misread: you can tick "key present" while the key is the wrong one. For every assertion marked **[CITE]** below, you MUST resolve it by quoting the specific token(s) from the cube — the actual column, alias, `key` element, `GROUP BY` list, or approved-spec line — that satisfy it. If you cannot quote the tokens, the assertion FAILS. An assertion is passed by evidence you can point at, never by assertion alone. This is internal reasoning; do not print the citations, but do not skip forming them. When a **[CITE]** assertion's quoted tokens contradict what the product promises (e.g. the declared grain is "by County" but the only `key` you can quote is `S.Supplier`), that is a FAIL — fix the cube, do not re-tick.

1. **No existing entity definitions were modified** — only the cube view was appended.
2. **The cube view is appended at the END of the file**, after all entity definitions.
3. **[CITE] Every column alias matches the source column name exactly** — no invented prefix/suffix. Quote each `source AS alias` pair. WRONG: `CategoryText.Language AS CategoryTextLanguage`. CORRECT: `CategoryText.Language AS Language`. Only when two joined tables share an identical column name, use a minimal prefix and add an inline comment.
4. **A non-nullable column from the null-supplied side of each outer join is in the SELECT list** — the joined entity's PK always satisfies this (beyond the PK-as-key that the gate checks).
5. **No correlated subqueries** (a subquery referencing an outer alias in its WHERE).
6. **Personal-data for a **computed** column derived from a personal-data source field: if the derived value is still personal, the `@PersonalData.*` annotation is re-declared on it (the compiler drops it otherwise). Validator `PD1` surfaces any that are missing.
7. **Every join key is type-compatible on both sides** — if types differ (e.g. Integer vs String), the join was not written silently; the user was asked how to proceed.

**Intent match (does the cube deliver what the product promised — the checks a clean-compiling cube still fails):**
8. **[CITE]** *Grain matches the declared dimension.* If the product name or approved spec asserts "by X" (e.g. "by County", "per Region"), the `GROUP BY` list and the `key` elements MUST lead with X. Quote the declared dimension from the name/spec, then quote the `GROUP BY` / `key` tokens. FAIL if X is merely projected as a passthrough column while the grain is some other entity (e.g. a "by County" cube grouped/keyed on `Supplier`). This is the canonical silent defect — a cube can compile clean and still answer the wrong question.
9. **[CITE]** *Measures match the approved spec.* Every measure in the approved measure list is present in the cube's projected columns under a name that matches the promise; no approved measure was silently dropped, and no measure was silently substituted by a differently-computed column. Quote each approved measure ↔ the cube column that delivers it. FAIL on any dropped measure (e.g. promised `SpendConcentrationPct` absent) or silent substitution (e.g. `SupplierCount` delivered as `SpendAmountCount`). A renamed-but-equivalent column is a FAIL unless the rename was approved.
10. *Ratio / share / concentration metrics are relative.* If any measure is named or described as a percentage, share, ratio, or concentration, it MUST be computed by dividing by a total (window function or subquery), not by bucketing an absolute value against a threshold. Detect the keyword in the measure name/description; if found, **[CITE]** the denominator (the `OVER (...)` window or subquery total) that makes it relative. If no relative denominator exists, auto-pick the most data-rich relative basis available from the source schema and proceed silently

**Structural assertions (countable — resolve by quoting tokens, not by reasoning):**

11. **[CITE] `@Analytics.dimension` count matches GROUP BY count.** Count the `@Analytics.dimension : true` annotations in the cube. Count the entries in the `GROUP BY` clause. The counts MUST be equal. Quote both counts. FAIL if any `GROUP BY` column lacks the annotation, or any non-`GROUP BY` column has it. (Catches validator rule D1.)

12. **[CITE] `COUNT(*)` measure present in every grouped cube.** If the cube has a `GROUP BY` clause, quote the `COUNT(*)` expression in the projected columns. FAIL if absent. SparkMV requires a per-group row count for incremental maintenance. (Catches validator rule G4.)

13. **[CITE] Every projected expression is aggregated or grouped.** For each projected column, classify it as one of: [AGG] — the outermost call is `SUM`/`COUNT`/`MIN`/`MAX`/`AVG`; or [GRP] — the column appears in the `GROUP BY` list. A `CASE`/`CAST`/arithmetic expression is NOT an aggregate unless its outermost function is one of those five. Quote each projected column with its classification. FAIL on any column that is neither [AGG] nor [GRP]. (Catches validator rule G1; sharpens Pass 1 item 1.)

    **Common pitfall — paired-count columns for nullable SUMs (Cat 4.1).** The paired count `CASE WHEN X IS NOT NULL THEN 1 ELSE 0 END` is a bare `CASE`, so it is neither [AGG] nor [GRP] by itself. It MUST be wrapped in `SUM(...)` to become [AGG]: `cast(SUM(CASE WHEN X IS NOT NULL THEN 1 ELSE 0 END) as Integer) AS XCount`. Same rule for AVG-as-SUM+count rewrites (Cat 4.4).

14. **[CITE] Currency/unit companion in GROUP BY for every additive amount/quantity SUM (or WHERE-pinned).** For each `SUM(<alias>.<field>)` or `AVG(<alias>.<field>)` projected column, look up the source field's `@Semantics.amount.currencyCode` or `@Semantics.quantity.unitOfMeasure` companion in the entity schema. That companion field, referenced on the **same alias** as the measure's argument (i.e. `<alias>.<companion>`), MUST appear in the `GROUP BY` list — OR the WHERE clause MUST pin it to a single literal value (`= 'USD'` or `IN ('USD')`). Quote the measure, its companion field, and the matching `GROUP BY`/`WHERE` token. FAIL if neither is present, or if the companion is grouped on a *different* alias (e.g. `P.DocumentCurrency` in GROUP BY while the SUM reads `I.NetAmount` whose currency lives on alias `I`). (Catches validator rule G2 — aggregating across mixed currencies/units is meaningless.)

## Correctness Passes (run before interop, as silent internal reasoning)

Run after writing the view, before calling `generate-interop`. Fix in place — do not print or narrate. Re-run a pass after any fix it triggers.

### Pass 1 — Semantic (compiles but fails at runtime)

Build a catalog: per entity used, its fields + types + `key` markers. Then:

1. **Aggregate / GROUP BY.** For each projected column, classify it as [AGG] (outermost call is `SUM`/`COUNT`/`MIN`/`MAX`/`AVG`) or [GRP] (appears in `GROUP BY`). A `CASE`/`CAST`/arithmetic expression is NOT an aggregate unless its outermost function is one of those five. FAIL if any column is neither [AGG] nor [GRP], or if there are any aggregates but no `GROUP BY` at all. (See assertion 13 in the self-check above.)
2. **Column binding.** Every `Alias.field` resolves to a declared field on that alias's entity. FAIL on typos/wrong alias, or a bare unqualified column existing on >1 joined entity (ambiguous).
3. **Type sanity.** `SUM`/`AVG` over non-numeric → FAIL. `ON`/`WHERE` comparing mismatched types → FLAG.
4. **Nesting.** `SUM(COUNT(...))` → FAIL. Aggregate in `WHERE` → FAIL (use `HAVING`). `SUM(a)+b` with bare ungrouped `b` → FAIL.
5. **NULL semantics.** Filter on nullable column without `IS NOT NULL` where logic assumes presence → FLAG.

Any FAIL → fix, re-run. FLAG = divergence risk; proceed only if intentional.

### Pass 2 — Join Minimization

A join is **dead** if its alias appears nowhere outside its own `ON` (not in SELECT/WHERE/GROUP BY/HAVING).

| Dead join type | Verdict |
|---|---|
| `LEFT`/`OUTER` on right side's `key` (unique) | **DROP** |
| `LEFT`/`OUTER` on non-key column (may fan out) | **FLAG** |
| `CROSS` | **DROP** |
| `INNER` | **FLAG** — may be an intentional existence filter |
| `RIGHT`/`FULL` | **FLAG** |

Never drop the `from` table. A join used only in `GROUP BY` or feeding a projected computed/CASE column is **live** — trace expressions. After each DROP, re-run to fixpoint, then re-run Pass 1.

### Pass 3 — Join Reshaping (fan-out double-counting)

A flat join to a finer-grained child under `SUM`/`COUNT` replicates each parent row per child match → inflated totals. Compiles clean, GROUP BY valid — just wrong numbers.

- `ON` matches the right entity's **full key** → dimension lookup, does not fan out. **Safe.**
- `ON` matches only **part** of the key (or a non-key column) → finer-grained, **fans out**.

**RESHAPE when** a fan-out join exists AND an additive aggregate runs over the coarser side, or when two fact tables are joined directly then aggregated.

Fix — pre-aggregate the child to the join grain first:
```cds
SELECT P.id AS id, LineAgg.total AS total
FROM PrimaryEntity AS P
LEFT OUTER JOIN (
  SELECT L.parentId AS parentId, SUM(L.amount) AS total
  FROM LineItems AS L GROUP BY L.parentId
) AS LineAgg ON LineAgg.parentId = P.id
{ P.id, LineAgg.total }
```

Surface RESHAPE as a business question — ask once before applying: *"To get correct totals for [X], I need to summarise [Y] first — that's the more accurate approach. Want me to proceed?"* Re-run Pass 1 after reshaping.
