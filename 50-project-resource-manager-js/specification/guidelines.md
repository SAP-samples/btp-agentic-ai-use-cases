# Specification Execution Guidelines

Rules and constraints for executing specifications. Follow these throughout execution.

## Execution Rules

- Execute TODO items **sequentially** within each asset spec
- Follow ALL constraints in the referenced guidelines file of each asset spec
- If a TODO item references a skill, invoke that skill and complete its entire workflow
- Fix failures immediately before proceeding to next item

## Marking Items Complete

- **MANDATORY: Mark items complete (bulk processing per section), that means change `- [ ]` to `- [x]`**
- **MANDATORY: Also mark all matching items complete in every `specification/<asset-name>/specification.md`.** These files are the source of truth visible to the user.
- Run the validation checklist in the asset-specific guidelines (if any) before marking the final item complete
- If a TODO references a skill invocation, "complete" means the skill's entire workflow finished — not just that the skill was called
