# Specification: {{asset-name}}

> **Guidelines**: Read [guidelines-data-product.md](../guidelines-data-product.md) before executing ANY tasks below. Follow all constraints described there throughout execution.

## Basic Setup

- [ ] Read the project input (`product-requirements-document.md`, `intent.md`, or the user prompt that triggered this specification)
- [ ] Run `pwd` and store the output as `working_directory`
- [ ] Invoke the `data-product` skill to execute the workflow from **Step 0** (search and selection were completed during `intent-analysis` — do not re-run them; after Step 0 completes, proceed to Step 1a). Pass the confirmed Data Product ORD ID(s) from `intent.md` as the input DP selection already in context.