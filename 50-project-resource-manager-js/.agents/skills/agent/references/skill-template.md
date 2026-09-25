---
name: template-skill
description: |
  [WHAT] One sentence describing what this skill enables the agent to do.
  [WHEN] Use when the user wants to <specific task A>, <specific task B>, or asks about <topic C>.
  [NOT] Do not use for <near-miss scenario> — use <other-skill-name> instead.
  Key terms: term-one, term-two, term-three.
allowed-tools:
  - Read
  - Bash
metadata:
  author: team-or-email@example.com
  version: 0.1.0
  tags:
    - tag-one
    - tag-two
  user-context-dependent: false
  requires-rbac-scope: false
---

# Example Skill Title

## Purpose

Replace this section with 2–3 sentences describing what the skill does and why it exists.
Focus on the user goal it solves, not on the technology it uses.

This skill is an **encoded preference** — it captures a team convention that an agent would otherwise
have to guess (e.g. naming rules, output format, workflow ordering). Replace with **capability uplift**
if the skill teaches the agent something outside its base knowledge.

## When to use

- Trigger condition one — specific user intent or phrasing that should activate this skill
- Trigger condition two
- Trigger condition three

## When NOT to use

- Near-miss scenario A — direct the user to `other-skill-name` instead
- Near-miss scenario B — this is handled by the MCP tool layer, not a skill
- Out-of-scope topic C

---

## Instructions

### Step 1 — Understand the context

Before acting, read the relevant files and collect the inputs required by this skill.
If a required input is missing, ask the user rather than assuming a value.

| Situation | Action |
|---|---|
| Input is present and unambiguous | Proceed to Step 2 |
| Input is present but ambiguous | Clarify with the user before continuing |
| Input is missing entirely | Ask the user for it; do not fabricate a default |

### Step 2 — Apply the rule deterministically

Describe what the agent must do in this step. Use imperative language and explicit if/else
branches — never say "usually", "try to", or "in most cases", as those phrases let each LLM
interpret the rule differently.

If a deterministic rule must be validated, offload it to a script rather than describing it
in natural language:

```bash
# Run the validation script — do not re-implement this logic inline
bash scripts/check-rule.sh --input "$VALUE"
```

### Step 3 — Produce the output

Describe the exact output format expected from the agent.

```
# [PLACEHOLDER — replace with a representative output example]
<output-format-here>
```

After producing the output, verify it passes the constraints listed in Step 2 before
returning it to the user.

---

## Examples

### Example 1 — Typical case

**Input:**
```
<representative input>
```

**Output:**
```
<expected output>
```

### Example 2 — Edge case

**Input:**
```
<edge-case input>
```

**Output:**
```
<expected output for the edge case>
```

---

## Gotchas

- **Pitfall name** — Describe a concrete failure mode and the correct behaviour. Be specific: name
  the file, command, or field that trips agents up. Avoid vague warnings.

- **Another pitfall** — Each entry should follow the pattern: when X happens, do Y instead of Z.

- **Version-specific behaviour** — If a tool or API behaves differently across versions, document
  the affected versions and the workaround here.
