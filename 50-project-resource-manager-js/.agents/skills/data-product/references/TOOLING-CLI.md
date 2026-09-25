# Tooling Reference

All CLI commands are provided via `jl data-product`.

---

## Command Reference

### fetch-and-prepare  ← preferred; use this for session prep

```bash
jl data-product fetch-and-prepare \
  --data-products '[{"ordId":"<ord_id1>","tenantId":"<tenant_id1>"},{"ordId":"<ord_id2>","tenantId":"<tenant_id2>"}]' \
  --session-dir <session_folder>/work
```

Does the full session preparation in **one call**: fetches + aggregates the CSN, compiles `transformation.cds`, and builds `csn_graph.json`. Use this instead of calling `fetch-agg-csn` → `generate-agg-cds` → `generate-csn-graph` separately.

- `--data-products`: JSON array of `{ordId, tenantId}` pairs — always a JSON array, even for a single DP
- `--session-dir`: absolute path to session work directory
- Stops before compiling if zero data products fetch successfully, or if the aggregated CSN has no definitions — nothing is written in that case.
- Outputs: `<session_folder>/work/aggregated_csn.json`, `<session_folder>/transformation.cds`, `<session_folder>/work/csn_graph.json`
- Returns: `{"success": true, "output_path": "...", "transformation_cds": "...", "csn_graph_path": "...", "data_products_fetched": N, "total_definitions": N, "not_available_ids": [...], "error_ids": [...]}`

---

### csn-list-entities

```bash
jl data-product csn-list-entities --csn-graph-path <session_folder>/work/csn_graph.json
```

Returns all entity FQNs in the graph.

---

### csn-list-views

```bash
jl data-product csn-list-views --csn-graph-path <session_folder>/work/csn_graph.json
```

Returns all view FQNs in the graph.

---

### csn-get-schema

```bash
jl data-product csn-get-schema \
  --csn-graph-path <session_folder>/work/csn_graph.json \
  --entity-names '["<fqn1>","<fqn2>"]' \
  [--include-enums]
```

Returns field names, types, labels, and keys for **one or more** entities. Add `--include-enums` to inline enum value lists.

- `--entity-names`: JSON array of entity FQNs — always a JSON array, even for a single entity. Pass all entities you need in one call to avoid round-trips.
- Returns: `{"success": true, "schemas": [ { "entity": "<fqn>", "label": "...", "fields": {...} }, ... ]}` — one entry per entity, in input order.

---

### csn-get-enum-values

```bash
jl data-product csn-get-enum-values \
  --csn-graph-path <session_folder>/work/csn_graph.json \
  --fields '[{"entity":"<fqn1>","field":"<fieldName1>"},{"entity":"<fqn2>","field":"<fieldName2>"}]'
```

Returns allowed enum values for **one or more** (entity, field) pairs. Use when filtering on specific field values (e.g. resolving the codes for "approval status = Approved" and "payment status = Paid" in a single call).

- `--fields`: JSON array of `{entity, field}` objects — always a JSON array, even for a single pair. Pairs may span different entities.
- Returns: `{"success": true, "values": [ { "entity": "<fqn>", "field": "<name>", "label": "...", "type": "...", "values": [...] }, ... ]}` — one entry per pair, in input order.
- A pair whose field is not an enum returns `{ "error": "'<field>' is not an enum field" }` **inline** for that entry; other pairs still resolve.

---

### csn-get-semantic-relations

```bash
jl data-product csn-get-semantic-relations \
  --csn-graph-path <session_folder>/work/csn_graph.json \
  --entity-names '["<fqn1>","<fqn2>"]'
```

Returns semantic amount/unit pairings for **one or more** entities.

- `--entity-names`: JSON array of entity FQNs — always a JSON array, even for a single entity. Pass all entities you need in one call to avoid round-trips.
- Returns: `{"success": true, "relations": [ { "entity": "<fqn>", "relations": { "amounts": [...], "quantities": [...], ... } }, ... ]}` — one entry per entity, in input order.

---

### csn-search-fields

```bash
jl data-product csn-search-fields \
  --csn-graph-path <session_folder>/work/csn_graph.json \
  --query <substring> \
  [--entity-filter <fqn>]
```

Searches fields by name or label substring.

---

### generate-interop

```bash
jl data-product generate-interop \
  --modified-cds <session_folder>/transformation.cds \
  --agg-csn      <session_folder>/work/aggregated_csn.json
```

Generates the data product interop definition (`.dpd`) from the modified CDS.

- Returns: `{"success": true, "message": "...", "output_interop_path": "..."}`
- Store `output_interop_path` from the response
- If returns "No transformed entities found": the transformer view is missing or empty — diagnose per SKILL.md Step 7

---

### fetch-ams-policy

```bash
jl data-product fetch-ams-policy \
  --data-products '[{"ordId":"<ord_id1>","tenantId":"<tenant_uuid1>"},{"ordId":"<ord_id2>","tenantId":"<tenant_uuid2>"}]' \
  --session-dir <session_folder>/work
```

Fetches AMS policies for input data products from UMS and saves them to a policy file.
Run immediately after `fetch-and-prepare` — pass the same ORD IDs and tenant IDs.

- `--data-products`: JSON array of `{ordId, tenantId}` pairs — same values used in `fetch-and-prepare`
- `--session-dir`: session work directory (same as `fetch-and-prepare`)
- Output: `<session_folder>/work/input-dp-ams-policy.json`
- Returns:
  ```json
  {
    "output_path": "...",
    "data_products_queried": N,
    "data_products_with_policy": N,
    "not_available_ids": [...],
    "error_ids": [...]
  }
  ```

---

### fetch-ams-candidates

```bash
jl data-product fetch-ams-candidates \
  --dpd <output_interop_path> \
  --policy-file <session_folder>/work/input-dp-ams-policy.json
```

Computes AMS authorization candidates for a derived DP by cross-referencing the pre-fetched policy file against the derived DP's cube.

- `--dpd`: path to the derived DP's `.dpd` file (`output_interop_path` from `generate-interop`)
- `--policy-file`: path to the `input-dp-ams-policy.json` file produced by `fetch-ams-policy`
- Returns: `{ "source": "input-policy" | "derived-dp", "recommended": [...], "alsoRecommended": [...], "available": [...] }`
  - `source: "input-policy"` — at least one input DP has an AMS policy; fields from that policy present in the derived DP go into `recommended`, additional recommended fields go into `alsoRecommended`, all remaining derived DP fields go into `available`
  - `source: "derived-dp"` — no input DP has a policy; dimension/key fields (non-measures) go into `recommended`, all remaining derived DP fields go into `available`
  - Each entry in all arrays: `{ "field": "<name>", "label": "<text or omitted>", "sourceDP": "<id, input-policy only>" }`

---

### inject-ams-policy

```bash
jl data-product inject-ams-policy \
  --dpd <output_interop_path> \
  --fields '["Field1", "Field2"]'
```

Builds an AMS DCL policy from approved fields and injects it into the `.dpd` file in-place.

- `--dpd`: path to the `.dpd` file (produced by `generate-interop`). Overwritten in-place.
- `--fields`: JSON array of field names to include in the AMS policy WHERE clause
- Returns: `{ "success": true, "message": "AMS base policy injected.", "dpd": "<path>" }`
