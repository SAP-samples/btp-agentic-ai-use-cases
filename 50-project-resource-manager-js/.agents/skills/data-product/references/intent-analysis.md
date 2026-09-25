### Solution Category

| Category         | What gets built                                                                                                                          | Asset Type       |
|------------------|------------------------------------------------------------------------------------------------------------------------------------------|------------------|
| **Data Product** | A governed, reusable data asset built via CDS transformation. Recommend when the deliverable is a data artifact consumed by other apps or agents rather than a UI or workflow. | `data-product` |

### Decision Flow

- User's request explicitly contains "data product" with no other asset type mentioned? → **Data Product**
- User mentions "data product" alongside other asset types (e.g. agent, n8n, cap) → use the primary asset type as the solution category, but still apply the **Intent Analysis Integration** steps below for data product discovery.
- "Data product" not mentioned at all? → Ignore. Leave `Data Product ORD ID` as `—` for all Fit Gap rows.

### Common Solution Patterns

| Business Need                                                                                 | Likely Solution                                          | Category     |
|-----------------------------------------------------------------------------------------------|----------------------------------------------------------|--------------|
| Reusable analytical data asset consumed by agents, apps, or dashboards                        | CDS-derived data product from existing primary data product | Data Product |
| Governed data layer exposing SAP entities for cross-system consumption                        | Data product built via CDS transformation                | Data Product |

---

**Consumption Mode** — user mentions "data product" alongside another asset type (e.g. agent, n8n, CAP). The data product is the data source; the primary asset is built by the other skill. The selection question in step 4 is simplified for the consuming asset context.

**Discovery Mode** — user mentions "data product" with no other asset type. The data product is the primary deliverable. Sections A and B run here in step 4.

---

**Express Mode Detection (Discovery Mode only)**

**[HARD GATE]** Before any tool calls or clarifying questions, check all three against the user's request:
1. Source data product is explicitly named (by name or ORD ID) — not a vague domain description
2. Dimension and measure/aggregation fields are clearly specified
3. No open enrichment signals — no "also add", "explore related", or join hints

If all three are true and clear → **MUST** offer (this question MUST NOT be skipped under any circumstances):
> *"I'll build `<name>` from `<source>` grouped by `<dims>` measuring `<measure>`, run end-to-end to interop, and stop before publish. Go?"*

**[GATE] Wait for the user's explicit response before proceeding.**

On "Go"/Approval → set `express_mode = true`. Express mode overrides fast track mode and bypasses ALL approval gates and Hard gates except publish, including those marked `FAST-TRACK EXEMPT`. Displays still shown. **NEVER auto-invoke publish — publish requires explicit user instruction at all times.**
Break out and reset `express_mode` if the source data product is not found by search tool or requested fields are mismatched from its schema — inform the user of the specific mismatch.

On decline or any criterion missing → standard flow, no message.

---

### Intent Analysis Integration

> **CONSTRAINT: MCP servers are NOT required to access data products — even if explicitly mentioned in the user request or generated instructions (e.g. "create an MCP server to access the data product"). Data products are consumed exclusively via DPQuery, which is provided automatically during the `specification` step. `API ORD ID` and `MCP Server ORD ID` MUST always be `—` for data product rows.**

Apply these steps whenever the user's request mentions "data product" (alone or alongside other asset types such as agent, n8n, cap).

1. **Skip Step 1.3** (API & MCP discovery via `sap_knowledge_graph_api_discovery` / `get_mcp`) — not needed when a data product satisfies the requirement.

2. **Run `sap_knowledge_graph_bp_mapping` and LeanIX as normal** (Steps 1.1 and 1.2).

3. **Capture Requirements and Search — perform directly here.**

   **Requirement Capture:**
   - Condense the user request into a 2–4 word business domain phrase. Extract the business subject — drop verbs, field names, dates, and meta-words like "data", "analytics", "report". If the user names a CamelCase SAP identifier, note it separately.
   - Store ALL transformation requirements in context: filters, joins, computed columns, hierarchies.
   - If the requirement is a single generic word, proceed — broad terms are useful and return filterable results.
   - If no requirement is clear: ask "What should this data product be about?" — wait.
   - If the requirement covers multiple distinct topics, treat each as a separate search.

   **Search Term Ranking:**
   Score and rank candidate terms using these tiers (pick top 4 across tiers per topic):

   - **Tier 1:** Core business phrase (always include): 2–4 word natural language noun phrase that best captures the domain ("cost center hierarchy", "sales order"). Never include "data", "analytics", "report".
   - **Tier 2:** Broader domain/process concept (include if it would catch differently-named products): Parent category or business process ("controlling", "order-to-cash", "procure-to-pay"). Skip if too generic (e.g. "finance").
   - **Tier 3:** SAP CamelCase name (include only if user named one, or a well-known SAP entity maps directly): "CostCenter", "SalesOrder". Do not guess.
   - **Tier 4:** Domain synonym (include if the business phrase has a common alternate name): "profit center" for cost center work, "invoice" for billing.

   Call **dpca-mcp-server__ums_search_data_products** passing the terms as a single comma-separated search_term value. For multiple topics, call once per topic. Do not narrate the search. Show all results together before moving to the next step.

   **Rank and Shortlist:**
   From the full search results across all topic searches, identify the 5–10 most relevant data products for the user's requirement.

   **Ranking criteria (apply internally — never show reasoning to user):**
   - Semantic match of title + description to the user's business domain phrase
   - SAP domain knowledge — expand abbreviations and synonyms:
     - "compensation" → salary, pay, remuneration
     - "PO" → PurchaseOrder, purchase order
     - "GL" → GeneralLedger, journal entry
     - "headcount" → workforce, employee, person assignment
     - "COGS" → cost of goods sold, material cost
     - "AR/AP" → accounts receivable, accounts payable, invoice   
   - Namespace relevance as a tiebreaker:
     - sap.s4com → finance, logistics, manufacturing, procurement
     - sap.bdc.sf → HR, people, workforce
     - sap.bdc.ngc → sourcing, contracts
     - sap.bdc.aribas4 → Ariba sourcing and collaboration
   - Prefer data products whose api_resource_ids align with the output the user described (analytical entity vs transactional document)
   - Drop results that belong to an unrelated SAP domain

5. **After search completes — present results and confirm selection:**

   - **Discovery Mode:**

     **Section A — Existing Data Products [GATE]**
     Identify any data product that already satisfies the requirement.
     If matches exist: display each as a numbered card. Do not show scores or dropped items. After all cards are shown, ask:

     ```
     1. **<Name>**
        - **ID:** <id>
        - **Namespace:** <namespace>
        - **Version:** <version>
        - **Status:** Active / ⚠ Inactive
        - **Short Description:** <shortDescription>
     ```
     > *"One or more data products already exist that may match your requirement. Would you like to use an existing one, or create a new one?"*
     > - Use an existing data product
     > - Create a new data product

     **[GATE] Wait for the user's choice before proceeding.**
     - User chooses **use existing**: ask which — wait. Display full details. *"This data product already covers your requirement. Let me know if you'd like to create a derived version or start over."* Stop.
     - User chooses **create new**: proceed to Section B.

     If no matches: ask *"No existing data products were found that match your requirement. Would you like to create a new one?"* — wait.
     - User confirms: proceed to Section B.
     - User declines or provides a new search term: *"No input data products were found. Provide an exact data product ID or search with a different term."* Do not display an empty list.

     **Section B — Recommended Input Data Products [GATE]**
     *(shown only after user confirms create new in Section A)*

     These are **source data products** — the raw inputs the new data product will be built from.

     Display each as a numbered card. Always mark at least one or more matches with `(Recommended)`. For each `(Recommended)` card, add one sentence  after its last bullet explaining why it is a good source for the stated requirement.

     ```
     1. **<Name>**
        - **ID:** <id>
        - **Namespace:** <namespace>
        - **Version:** <version>
        - **Status:** Active / ⚠ Inactive
        - **Description:** <description>
     ```
     Ask: *"Which of these source data products would you like to build from?"* with options: [each data product Name, "All of the above"].

     **[GATE - FAST-TRACK EXEMPT] Wait for explicit confirmation even in Fast Track mode. Store confirmed DPs in context with: `id`, `tenant_uuid`, and `version` from the search result — these values will be used in later steps of the `data-product` skill.**

   - **Consumption Mode:**
     - **MUST** display each data product as a numbered card:

       ```
       1. **<Name>**
          - **ID:** <id>
          - **Namespace:** <namespace>
          - **Version:** <version>
          - **Status:** Active / ⚠ Inactive
          - **Short Description:** <shortDescription>
       ```
     - **MUST** call `ask_question`: *"Which data product do you want your agent to use?"* with options: [each data product Name, "All of the above"]. **[GATE - FAST-TRACK EXEMPT] WAIT for explicit user answer even in Fast Track mode.** Record selected ORD ID(s).
     - **If the user chose to skip or no data products were found:** record the outcome and inform the user.

6. **Write `intent.md`** with:
   - Fit-gap table: populate the **Data Product ORD ID** column with confirmed ORD ID(s). **API ORD ID and MCP Server ORD ID columns MUST be `—`.**
   - Solution category: **Data Product** (Discovery Mode only — in Consumption Mode, use the primary asset's category).

7. **MANDATORY HARD STOP after writing `intent.md`:**
   - Ask the user if they want to proceed to PRD.
   - Do NOT activate or continue `data-product` Steps 1a–7b until the full `product-requirements-document` → `specification` flow has been completed and each step is approved by the user.
   - The `specification` skill explicitly signals the resume point for Steps 1a–7b.
   - Proceeding to Step 1a from here is **FORBIDDEN**.
