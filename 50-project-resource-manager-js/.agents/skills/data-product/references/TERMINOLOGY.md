# Terminology Rules

Use these conventions consistently throughout all interactions.

## Object Naming

- Use the generic term **"Objects"**. Do not use "Artifacts", "Entities", or "Tables".
- When describing the schema of an object whose **"Semantic Usage"** is **"Relational Dataset"**, use the term **"Columns"**.
- When semantic usage is **"Dimension"**, **"Fact"**, **"Text"**, **"Hierarchy"**, or **"Hierarchy with Directory"**, use the term **"Attributes"**.
- Never use the term "Fields".

## Data Product Properties

- Use **"Business Name"** instead of "Title"
- Use **"Technical Name"** instead of "Name"
- Use the noun **"properties"** when referring to data product properties. Do not use "Metadata".

## Action Verbs

- Use **"create"** when creating a data product, object, or solution. Do not use "generate".
- When something was created or registered without error: do not use the word "successfully". Simply state that it was created or registered.
- Do not echo tool `message` fields verbatim to the user. Translate to plain-language status consistent with these rules (e.g. "Data product definition created." not "Generated DDP Interop Successfully").

## Communication Style

- Do not start sentences with "Great", "Perfect", "Alright", "Excellent", or similar. Start directly with what you did or want to ask.
- Do not use emojis.
- Do not summarize the entire process after a data product has been registered.
- Do not narrate what you are about to do — just do it.

---

# Hard Rules

## Path Handling

- `working_directory` and `session_folder` are absolute paths — use them as-is for CLI tool arguments (`--session-dir`, `--agg-csn`, etc.)
- IDE/agent file tools (`write_file`, `read_file`, `list_files`, `delete_file`) are scoped to the solution root — pass them relative paths only
- These are two different systems. Never pass an absolute path to a file tool; never pass a relative path to a CLI tool argument.

## Search Term Extraction

- `dpca-mcp-server__ums_search_data_products` is called in Step 2 with a concise 2–4 word keyword phrase extracted in Step 1
- Make additional calls if a SAP technical name (CamelCase) was mentioned or if initial results are insufficient
- Merge and deduplicate results before presenting