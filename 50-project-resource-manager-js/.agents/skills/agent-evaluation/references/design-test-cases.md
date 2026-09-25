# Design test cases

The user journeys and the test cases that cover them. Called by
[generate-eval-scenarios](./generate-eval-scenarios.md) and, for new and changed tests, by
[extend-eval-scenarios](./extend-eval-scenarios.md).

Requires the eval requirements and the tool catalog to already be resolved.

---

## Define the user journeys

A user journey is a concrete, end-to-end interaction a user can have with the agent. These
are the coverage unit: a suite that covers every eval requirement but no complete journey
has never checked that the agent delivers anything.

If the source already documents journeys, milestones, or flows, use those. If it does not,
derive them and list them in the report so the reader can correct them.

```
User Journey ID: UJ-01
Name: Top Receivables Analysis
Trigger utterance: "Analyse my top receivables for customer C0001, company code F001"
Expected flow: fetch_accounts_receivable_data(company_code=F001, customer_account=C0001),
               then calculator for the disputed share
Expected outcome:
  - Summary identifies customer C0001 under company code F001
  - Total outstanding is approximately 12,922,923.98 - rounding acceptable
  - Disputed % of Outstanding is approximately 62.73%
  - Recommendation is specific to the overdue status, not generic
  - Actions include a Set Payment Block option with pre-filled document details
Edge cases: missing company code, unknown customer, large result volume
```

**Fill in the real values.** Take them from `mcp-mock.json`'s `mock_response` for the tools
the journey calls - see
[tool-catalog](./tool-catalog.md#mock-responses-are-the-expected-values). A journey written
with `<AMOUNT>` produces a test written with `<AMOUNT>`, and that test cannot run.

**Where no `mcp-mock.json` was found there is no `mock_response`**, which is the common case
on an extension. The values come from the sources that do exist, in this order:

| Take from | Gives |
|---|---|
| The capability `instruction` in `extension.yaml` | Filter constants the agent must use - a status code, a fixed flag - and the fields it must select |
| The worked example in a tool's `description` | A realistic identifier, often the only one available: `SalesOrganization eq '0001'` |
| The extension PRD and `intent.md` | Personas, scenarios, and any identifiers the document names |

Assert the parameters exactly; let the **output** check describe what the call must return in
kind rather than inventing a literal - see [Without a
`mock_response`](./tool-catalog.md#without-a-mock_response). Where no source supplies a
usable identifier, say in the report which tests need real data before they will pass. Never
invent one that looks plausible: it fails against the real backend and reads as an agent
defect.

Concrete values belong here, even when the corresponding `eval.yaml` requirement is broader.
Use the employee ID, customer ID, names, plan names, amounts, dates, and record counts from
the selected mock response in `task_summary` and the validations. Do not broaden a test
assertion into a vague shape check just because the reusable eval requirement is task-scoped.

---

## The budget

**At least 3 test cases per group, and at most 15 in total.** The three groups are defined
below - [goal completion](#goal-completion--is-the-agent-delivering-value),
[correctness and compliance](#correctness-and-compliance--is-the-agent-working-correctly),
and [business outcome](#business-outcome--does-behaviour-advance-the-committed-metrics). Nine
tests is therefore the usual floor and 15 the hard ceiling. Never ask the user for the
number.

The floor is per group because the groups answer different questions, and a suite that
satisfies one of them thoroughly while skipping another has a hole no total can reveal. Three
correctness tests and nothing else is a suite that never checks a guardrail.

| | |
|---|---|
| **Coverage** | Every user journey has a happy path and at least one failure path, every qualifying business metric has a business-outcome test, every eval requirement is covered, and every source requirement is exercised. |
| **Budget** | At least 3 per applicable group; at most 15 files in total. |

### The floor is per *applicable* group

A group that does not apply to this agent contributes nothing, and **is never padded to 3.**
Report it as not applicable with the reason.

| Group | Sized by | Does not apply when |
|---|---|---|
| Goal completion | The user journeys - one happy path plus one or two failure paths each | Never; every agent has at least one journey. A single-journey agent reaches 3 as one happy path plus two failure paths. |
| Correctness and compliance | The source's rules, constraints, and policy statements | Never in practice. A source with no rules at all is a finding about the PRD. |
| Business outcome | **One test per qualifying metric** - so 0, 2, or 6, whatever the table holds | The metrics table is absent, or no metric carries a committed target. |

The business-outcome group is the one that legitimately sits below 3, and often at 0. It is
driven entirely by the target gate in
[derive-eval-requirements](./derive-eval-requirements.md#which-metrics-qualify): two
qualifying metrics means two tests, never three. Inventing a third asserts behaviour no
metric asked for.

### A new check is cheap, a new file is not

**The budget counts files, not assertions.** A test case carries as many checks as its
scenario supports, and a check costs a line. So the first move for an uncovered requirement
is always to look for a test already putting the agent in a situation where that requirement
applies, and add the check there.

| The uncovered requirement is about… | Add |
|---|---|
| Something the agent must say or include, in a situation an existing test already creates | a check in that test's `agent_response_validations` |
| A constraint on what it may say or must refuse, in a situation an existing test already creates | a check in that test's `rule_compliance_validations` |
| A tool call an existing test already provokes | an entry or parameter in that test's `tool_validations` |
| A *situation no existing test creates* - a different journey, a different failure, a different adversarial framing | **a new test case** |

That last row is the only one that justifies a file. The question is never "is this a
different requirement" - it is "does checking this need the agent to be somewhere no test
puts it".

Do not stretch a scenario to fit. A check only belongs in a test whose conversation actually
triggers the behaviour: bolting an authentication-refusal check onto a happy-path receivables
test gives the judge nothing to decide, and it passes or fails at random. When the situation
does not arise in that conversation, it is a new test case and it was worth the file.

This is also how the per-group floor is met honestly. Reaching 3 in a group means three
genuinely distinct situations, not one scenario written out three times with the wording
changed.

### Spend the budget in this order

Satisfy the floors first, then spend what is left. Everything above a line gets a file before
anything below it does.

1. **One happy path per user journey** - without it, nothing shows the agent delivers
   anything.
2. **One business-outcome test per qualifying metric** - the scorer reports zero otherwise.
3. **One failure path per journey**, drawn from its edge cases and stated failure conditions.
4. **Up to the floor of 3 in each applicable group** - the second and third guardrail
   scenario, the second failure path.
5. **The remaining scenarios the source describes**, while files are left.

### When the floors and the cap collide

The floors demand 9 or more; the cap allows 15. A multi-journey agent with several metrics
can exceed that - four journeys at 3 files each plus five metrics is already 17.

Resolve it in this order, and **never by dropping a group below its floor silently**:

1. **Fold checks rather than adding files**, per the table above. A second failure path for
   one journey is often two more checks on the first.
2. **Cut the lowest-priority files** - items 5 then 4 in the order above, taking from the
   group furthest above its floor.
3. **If a group must go below 3**, say which, by how much, and what is consequently
   unchecked.

Then report every source requirement left uncovered by name, with the reason it did not fit.

---

## Design the test cases

Every test case is a single `dynamic_conversation` step. See
[testcase-schema](./schemas.md#test-cases--testcasesidyaml) for the shape, the id format,
and how to write `task_summary`.

**Work from the source document, not from `eval.yaml`.** Go back to the PRD for the
scenario: the user journeys, the acceptance criteria with their concrete examples, the
failure conditions, the policy prose, the persona the document had in mind. The eval
requirements are a checklist to measure against - they are not the material to write from,
because the detail that makes a scenario real does not survive being compressed into a
one-line rule.

**The source document and the tool source are the only material** - `mcp-mock.json` where it
exists, otherwise the translation files or the `@tool` scan, plus `extension.yaml` on an
extension. Scenarios come from the
source; concrete values come from the mocks. Not from the agent's code - a test written
against what the implementation does asserts the agent matches itself, which every agent
passes and no regression fails.

**How many test cases is decided by [the budget](#the-budget), never by the user.** At least
3 per applicable group, at most 15 in total.

**Expect every test to cover several eval requirements.** `eval.yaml` holds 15 or more
entries and the suite holds at most 15 files, so a one-requirement-per-test suite cannot
reach parity - it is not the shape to aim for. A single receivables happy path legitimately
covers a response requirement about the summary, another about how amounts are presented, a
tool requirement about the lookup and its parameters, and a compliance requirement about not
stating unretrieved figures. Four entries, one file, four checks.

**Maintain parity as you go.** Keep the eval requirements list open beside you. Mark each
eval requirement as a test covers it, and for each test you write, note which eval
requirement or requirements it covers. When a test does not land on any eval requirement -
which happens, because the source carries scenarios the eval requirements abstracted away -
**add that eval requirement to `eval.yaml` then and there**, provided its category is still
under its ceiling of 10. That is expected, not a correction: step 4 captures what the
source states outright, and designing the scenarios is what surfaces the rest. Fixing parity
while designing is cheap; leaving it to validation means auditing the whole suite at once.

An entry added this way often belongs in a category the first pass left short, which is why
this step is usually what carries a thin category up to 5.

**Track the source requirements too, not only the eval requirements.** Keep a second column:
each source requirement, acceptance criterion, milestone condition, and qualifying metric
against the test that exercises it. Parity between `eval.yaml` and the suite can be perfect
while a PRD requirement nobody turned into either is missing from both, and that is the gap
this column exists to catch.

Test cases fall into three groups, distinguished by the question each answers. **Each
applicable group holds at least 3 tests**, and the three together hold at most 15 - see [the
budget](#the-budget).

### Goal completion - *is the agent delivering value?*

One test per user journey, and per milestone where the source defines them.

- **Happy path**: the full flow to successful completion, asserting the journey's expected
  outcome field by field with the real values.
- **Failure paths**: one or two per journey, drawn from its edge cases and any stated
  milestone failure conditions - upstream errors, empty results, missing input, policy
  violations.

**Reaching the floor of 3.** A multi-journey agent passes it on journeys alone. A
single-journey agent reaches it as one happy path plus two distinct failure paths - two
different things going wrong, not the same failure phrased twice.

Tag `correctness`. Id `<NN>_Correctness_<Journey>`.

For a routing-only orchestrator, substitute routing paths for journeys, tag `orchestration`
plus `routing_correctness`, and omit `tool_validations`.

### Correctness and compliance - *is the agent working correctly?*

From the source document's rules, constraints, and policy statements. **At least 3**, and
enough that **every eval requirement in `eval.yaml` is covered by at least one test** and
every source rule is exercised somewhere - but write them as *situations*, not as one file
per rule. Group the rules that share a plausible conversation into one scenario and assert
each of them as its own check; a single well-chosen adversarial exchange routinely carries
four or five compliance checks.

Read the eval requirements to find out *what* must be covered; read the source to find out
*how* to provoke it. An eval requirement reading `WHEN the user is not authenticated, the
agent MUST refuse` tells you the assertion - the PRD tells you the scenario in which an
unauthenticated user plausibly turns up, and what they would say.

Focus on guardrails under pressure: bypass attempts, fabricated authority, invented data,
skipped verification. These are where a `TRAP:` line belongs - see
[testcase-schema](./schemas.md#adversarial-scenarios-the-trap-line). Write the trap as what
the user does, never as what the agent must do.

Tag by dimension - `hallucination`, `safety`, `security`, `memory`, `digression` - per
[test-dimensions](./schemas.md#test-dimensions). Id `<NN>_<Category>_<Scenario>`.

### Business outcome - *does behaviour advance the committed metrics?*

One test per business metric that qualified under the gate in
[derive-eval-requirements](./derive-eval-requirements.md#which-metrics-qualify).

**This group is sized by the metrics table, not by the floor of 3.** Two qualifying metrics
means two tests; none means the group is not applicable and is reported as such. Never invent
a third to reach the floor - it would assert behaviour no committed metric asked for.

Each is anchored to a specific `[BUSINESS_METRIC: …]` eval requirement in `eval.yaml`. The
test's `description`, `agent_response_validations`, and `rule_compliance_validations` derive
directly from that eval requirement - do not invent behaviour it does not imply - and **at
least one check names the metric and its target explicitly.**

```
description: Business Outcome - agent must advance AP exception rate toward 2.0% in Invoice to Pay.
id:          04_BusinessOutcome_ApExceptionRate
tags:        [correctness, business_outcome]
```

**These are never adversarial, and they carry no `TRAP:` line.** That absence is what marks
them. The scenario is a normal request inside the metric's governed process, and the test
asserts the agent does the work that moves the metric and communicates the result.

The eval requirement supplies the assertion; the **source supplies the scenario**. Take the
governed process from the metric's `process` column and the surrounding PRD narrative, so
the request the simulated user makes is one that process would actually receive.

Assert only observable behaviour - the actions taken and what was said, never the metric
value itself. A judge scoring one conversation cannot see an aggregate rate.

### Applies to every test case

- **One `dynamic_conversation` step** per test case.
- **Put the concrete values in `task_summary`** - the identifiers, codes, and amounts the
  simulated user knows, taken from `mcp-mock.json`.
- **Set `initial_message`** when the opening turn is part of the test - a specific phrasing,
  an adversarial framing, a particular entry point. Omit it for ordinary flows.
- **Set `max_turns` deliberately.** 2–3 for a single-request scenario or a stateless agent,
  5–8 where the agent must gather missing information. It is a safety limit, not a target.
- **Assert values, not shapes.** Every check names what the value must be. See
  [writing-checks](./writing-checks.md#information-correctness).
- **Assert both halves of every tool call** - parameters and output. The expected output is
  the tool's `mock_response`; where no `mcp-mock.json` was found, the parameters stay exactly
  asserted and only the output check softens to a description.
- **Do not include deletion-type tool calls in `expected_tool_calls`.**
- Treat a tool as deletion-type when its primary effect is to remove, delete, drop, deactivate,
  or archive an entity.
- If `crudOperation` is available in the tool catalog, it is the authoritative source - use it
  and ignore the tool name and `description`. Fall back to name and description only when
  `crudOperation` is absent.
- Read, create, and update operations are permitted.
- If a scenario is only meaningful when it includes a deletion step, exclude that scenario from
  the suite instead of writing a reduced version.
- **Respect tool dependencies** from [tool-catalog](./tool-catalog.md#tool-dependencies)
  when ordering `expected_tool_calls`, and include every required parameter.
- **Put each assertion in the block that can judge it** - tool-call claims in
  `tool_validations`, never in the response blocks.
- **Give each test a unique id** in the `<NN>_<Category>_<ShortDescription>` form, matching
  `^[a-zA-Z0-9_]+$` and equal to its filename stem.
- **Give every test at least one dimension tag** from
  [test-dimensions](./schemas.md#the-tag-set). Never leave a test untagged.
- **Make every test earn its file.** Before writing one, name the eval requirements and
  source requirements it covers. A test covering exactly what another already covers is
  redundancy inside a fixed budget - fold its distinctive check into that test instead.
- **Load each test to its scenario's capacity.** Once the agent is in a situation, assert
  everything that situation makes judgeable: the values, the refusals, the tool parameters
  and outputs, the ordering. Leaving a judgeable requirement unasserted means paying for a
  second file to check it.

Vary coverage across eval requirements, tool sequences, user personas, and adversarial
setups. Avoid a set of tests that differ only in wording.

---
