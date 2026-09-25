# Generate eval scenarios

The main flow. Generates two artifacts from the source document, and writes a third that is
pure runtime configuration:

| File | Holds | Derived from |
|---|---|---|
| `aeval/eval.yaml` | The eval requirements — what the agent must do. | the source document |
| `aeval/testcases/<id>.yaml` | One dynamic conversation per scenario. This folder is the dataset. | the source document |
| `aeval/config.yaml` | Run parameters — lookback window, sampling rate, schedule. | **nothing** — user input or defaults |

One pass over the source produces both generated files.

**`eval.yaml` and the test cases are both generated directly from the source document.**
Neither derives from the other — see [One flow, two generated
artifacts](../SKILL.md#the-invariants). The eval requirements say what must be true; the
test cases say what situation to put the agent in. Write the tests from the source, not from
the eval requirements: the identifiers, the personas, and the edge case mentioned once in
prose do not survive abstraction into an eval requirement.

They are then cross-checked in two directions. **Against each other** — every eval
requirement covered by a test, every test covering an eval requirement. **Against the
source** — every requirement, acceptance criterion, milestone condition, and qualifying
metric in the document producing an eval requirement and being exercised by a test. Step 7
measures both and reports them as numbers rather than claims.

Both files are bounded: **5 eval requirements in each of the three categories, 10 maximum
each**, and **at least 3 test cases per applicable group, capped at 15 in total**. The eval
requirement bound is per category, never a total — see [the
invariants](../SKILL.md#the-invariants).

`config.yaml` is excluded from all of that. It is runtime configuration, holds no eval
requirements, and appears in no coverage figure.

For an agent extension with an existing base evaluation, this is the wrong operation — see
[extend-eval-scenarios](./extend-eval-scenarios.md).

---

## 1. Collect inputs

| Input | Required | Notes |
|---|---|---|
| Source document path | yes | The PRD or equivalent requirements document. |
| `mcp-mock.json` path | no | Located automatically per [tool-catalog](./tool-catalog.md). Used as is when found. |
| Number of test cases | never asked | **At least 3 per applicable group, at most 15 in total** — see [the budget](./design-test-cases.md#the-budget). |
| Number of eval requirements | never asked | **5 per category, 10 maximum each** — counted per category, not as a total. See [the budget](./derive-eval-requirements.md#the-budget). |
| Lookback duration, sampling rate, cron schedule | never asked | Runtime knobs, not derived from the source. Defaults applied in step 6. |

**Ask for nothing.** The test case count and the runtime parameters have defaults and are
applied silently — a question about either buys nothing and stalls the run. Ask only when
the request itself is ambiguous, or when nothing determines `output_dir`.

Then resolve `output_dir` per [paths](../SKILL.md#paths) — the agent's asset folder,
`<solution-root>/assets/<asset-name>/`. **Not the PRD's parent directory**, which is the
solution root and puts `aeval/` where the downstream scorer cannot see it.

### Read these files and no others

The source document, `mcp-mock.json`, and nothing else. **Do not read the agent's
implementation** — not its source modules, prompts, tests, notebooks, dependency manifests,
or deployment configuration. `mcp-mock.json` already carries every tool's description,
schema, and deterministic response, which is the whole of what a test needs to know about
the agent's capabilities. Reading further burns context and produces tests asserting what
the code happens to do rather than what the source document requires — step 7 deletes those.

The one exception is a run where no `mcp-mock.json` exists at all, which triggers the
fallback in [tool-catalog](./tool-catalog.md#fallback-no-mcp-mockjson). Even then, the scan
is narrow: `@tool`-decorated functions only.

---

## 2. Establish the agent architecture

It decides which categories apply and whether tool validations are meaningful at all.
Determine it from the source and the tool catalog, and **state which you concluded in the
report** — an orchestrator tested as an agent with tools produces `tool_validations` that
can never pass; an agent with tools tested as an orchestrator produces a suite with no tool
assertions at all, which passes trivially.

| Architecture | What to test |
|---|---|
| **Agent with tools** — calls tools directly | The full matrix: tool parameter and output correctness, safety, error handling, response information correctness. |
| **Sub-agent** — receives routed intent, calls tools | Same as agent with tools. |
| **Orchestrator (routing only)** — no direct tool access | Routing correctness only, inferred from response content. No `tool_validations`. |
| **Orchestrator with tools** | Both of the above. |

**Routing-only orchestrators.** Aeval cannot validate a routing decision directly, so every
response check must be specific enough that only the correct sub-agent's output could
satisfy it — a check any sub-agent's reply would pass asserts nothing about routing.
Enumerate the **routing paths**: every sub-agent reachable and the trigger that activates
it. They are the orchestration equivalent of user journeys, and each needs a correctness
test.

**Tool span instrumentation.** `tool_validations` are judged from OTel traces and need spans
carrying `gen_ai.operation.name = execute_tool`, `gen_ai.tool.name`,
`gen_ai.tool.call.arguments`, and `gen_ai.tool.call.result`. LangChain `create_agent`,
LangGraph `create_react_agent`, and PydanticAI `create_agent` emit these automatically;
anything else needs verifying. If unconfirmed, say so in the report — the validations are
still written, but may report as skipped on the first run.

---

## 3. Read the source and define the user journeys

From the source document extract requirements, milestones, and business metrics — the detail
is in [derive-eval-requirements](./derive-eval-requirements.md) step 1, which runs next.

Then define the **user journeys** per
[design-test-cases](./design-test-cases.md#define-the-user-journeys). They are the coverage
unit, and step 5 generates one goal-completion test per journey.

---

## 4. Resolve the tools and derive the eval requirements

**Tools.** Follow [tool-catalog](./tool-catalog.md). It reads `mcp-mock.json`, collects each
tool's name, description, `input_schema` and `mock_response`, and maps the dependencies that
govern `expected_tool_calls` ordering. Nothing is written. **Take the file as it stands** —
no cross-checking it against the agent's code, and no reading the implementation of a tool
to understand it better.

**Eval requirements.** Follow [derive-eval-requirements](./derive-eval-requirements.md). It
sorts every testable rule into the three categories, applies the metric target gate and the
`[BUSINESS_METRIC: …]` tagging, fills each category to [the
budget](./derive-eval-requirements.md#the-budget) of 5, and applies the trust boundary.
Create `{output_dir}/aeval/` in preparation, but **keep the derived requirements in working
memory**, shaped per [schemas](./schemas.md#shape) — step 7 writes them, once, after
validation.

**If a previous run left a complete evaluation, read its `eval.yaml` and do not re-derive.**
The test cases beside it were written and measured against those eval requirements;
replacing them with a second, slightly different reading of the source turns eval
requirements the tests satisfy into eval requirements nothing covers. Re-derive only when the
user asks or the source has changed, and say which you did.

**Complete means `eval.yaml` with a populated `testcases/` folder beside it.** An `eval.yaml`
standing alone is debris from a run that stopped before validation: it was never parity
checked and nothing covers it. Re-derive from the source, overwrite it, and say so — treating
it as authoritative carries an unvalidated file into every later run.

**Nothing is written at this step.** Step 5 adds an eval requirement whenever a test covers
something no eval requirement states, and step 7 adds any still missing at the parity check.
What this step establishes is the eval requirements the source states outright; the scenarios
surface the rest. Landing each category near 5 rather than at 10 leaves room for that — a
category already at its ceiling can only take a new entry by re-consolidating.

Keep the **source-to-requirements mapping**. Step 7 measures coverage against it, and it is
the only thing that can show a source requirement neither artifact ever picked up.

---

---

## 5. Design the test cases

Follow [design-test-cases](./design-test-cases.md#design-the-test-cases). It covers the
three test groups, [the budget](./design-test-cases.md#the-budget) and how to spend it, the
rules that apply to every test case, and the parity bookkeeping to maintain while designing.

---

## 6. Write `config.yaml`

Shape and values are in [schemas](./schemas.md#runtime-parameters--configyaml). **Write the
defaults** — `24h`, `0.5`, `0 2 * * *`. Do not ask the user, and derive nothing from the
source document.

---

## 7. Validate, write, and report

Follow [validate-and-report](./validate-and-report.md). It runs the validation checklist
over every generated test case, measures coverage, enforces parity, writes the files, and
reports.

**Do not write anything before running it.** Several of its checks change what gets written
— parity orphans add eval requirements to `eval.yaml`, and misplaced assertions are moved
between validation blocks.

---

## 8. Write environment management templates

If they do not already exist, write:
- `{output_dir}/aeval/testcases/000_pre_setup.yaml`
- `{output_dir}/aeval/testcases/zzz_post_teardown.yaml`

Use the templates from [schemas](./schemas.md#environment-management-templates).
Never overwrite existing files.
