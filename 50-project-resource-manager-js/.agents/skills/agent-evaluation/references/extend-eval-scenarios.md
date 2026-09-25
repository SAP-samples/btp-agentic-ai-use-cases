# Extend eval scenarios

Generates the evaluation for an **extended agent**: reconciles what the extension now
requires against whatever the base agent already had, and rewrites both `eval.yaml` and the
test cases to match.

This operation writes the same three files as
[generate-eval-scenarios](./generate-eval-scenarios.md) — `eval.yaml`, `testcases/`, and
`config.yaml`. The difference is that it starts from a baseline and reconciles rather than
deriving from a clean sheet.

**It writes no reconciliation report file.** Everything about what changed is reported in
conversation — see [The baseline is an input, not a source to
quote](#the-baseline-is-an-input-not-a-source-to-quote).

---

## The baseline is an input, not a source to quote

The baseline arrives in the base agent's own format and voice. The files this operation
writes describe **the extended agent**, so they read as one document written for it — not as
a diff against something else.

- **Write no path from the baseline** — not its folder, its filenames, or anything beneath
  them. Refer to it by what it is: "the base agent's requirements", "the behaviour the base
  suite already checks".
- **Carry across no structure of its own** — environment names, config keys, or the
  distinction between its environments. None of it describes the extended agent.
- **Use none of its numbering**, for requirements or for tests. Working labels stay in
  working memory; identify a changed requirement or a carried test by what it covers.
- **Add no provenance.** A requirement does not say where it came from. Generated files state
  what must be true, not how they were assembled.
- **Read its test cases, never quote them.** The base suite is an input — it is where most of
  the agent's existing behaviour is actually checked, and an extension evaluation that
  ignores it silently drops that coverage. But it is written in another format and another
  voice, so **nothing survives verbatim**: every carried test is reconstructed per [Reconcile
  the test cases](#5-reconcile-the-test-cases). Read them through the index in
  [triage](#3-triage-the-base-test-cases) rather than opening all of them.

The same applies to every other artifact read here — name the notification workflow, the
extension definition, or the tool definitions by what they are, never by their path.

This is also why the operation writes no reconciliation summary file. A record of what
changed relative to the baseline is provenance, and it describes the assembly rather than the
agent.

Extension-side sources are different. The PRD, its requirement and milestone identifiers,
and the capability instructions were authored by the customer and are cited normally.

---

## Source precedence

When sources disagree, resolve highest priority first:

| Rank | Source | Why |
|---|---|---|
| 1 | `intent.md` and the extension PRD | Define how the user *wants* the agent extended. This is the contract. |
| 2 | `extension.yaml`, `mcp-mock.json` or the MCP translation files, n8n workflow definitions | Describe what was *built*. Implementation detail. |
| 3 | The baseline eval requirements and the base test suite | Describe the agent *before* this extension. |

Intent and PRD always win. When an implementation artifact contradicts them, generate from
the intent or PRD and raise the discrepancy with the user as implementation drift — do not
silently adopt the artifact's behaviour, and do not silently discard it. Drift is reported
in conversation, never written to a file.

### Precedence governs behaviour, not tool identity

**A tool's name, its parameters, and its schema always come from rank 2**, whatever the PRD
calls it. Only the built artifacts know what the agent can actually invoke.

A PRD routinely names a capability rather than a tool — "the `get-open-billing-items` tool" —
while the deployed tool is `list_openbillingitems_for_billing`. Writing the PRD's name
into a `tool_requirements` entry produces a requirement that fails on every run, and fails
looking like an agent defect. Take the obligation from the PRD and the identifier from
`extension.yaml` or the translation file.

This is not an exception to precedence — it is the same rule applied to the right question.
The PRD is authoritative on *what must happen*; it was never authoritative on *what the tool
is called*. Report the divergence as drift all the same: a PRD naming a tool that does not
exist is worth the reader knowing about.

---

## 1. Collect inputs and locate the baseline

| Input | Required | Notes |
|---|---|---|
| Extension path | yes | Any path inside the extension solution. `output_dir` is resolved from it per [paths](../SKILL.md#paths) — the extension's asset folder, `<solution-root>/assets/<asset-name>/`, identified by `type: agent-extension` in its `asset.yaml`. |
| Base aeval path | no | Defaults to `<solution-root>/aeval-base` — the **solution root**, not `output_dir`. The base agent ships it beside `assets/`, not inside the extension's asset folder. Supplies both the baseline requirements and the base test suite. |
| `mcp-mock.json` | no | Located automatically per [tool-catalog](./tool-catalog.md#which-source-applies). **Used when present** — it is the only source carrying mock values. |
| MCP translation files | no | `<solution-root>/assets/*/mcp-translation/translation.json`. Describe the tools **when no `mcp-mock.json` was found**. |
| Number of test cases, runtime parameters | never asked | Defaults only, and the reconciled result is bound by the same budget as a fresh run — **5 eval requirements per category (10 maximum each), at least 3 test cases per applicable group, 15 test cases maximum.** See [the invariants](../SKILL.md#the-invariants). |

**`mcp-mock.json` is optional here, and preferred when it exists.** Look for it per
[tool-catalog](./tool-catalog.md#which-source-applies); if one is found, it describes the
tools and supplies the mock values that let tests assert real returned data. Most extension
solutions do not carry one, and that is normal rather than a missing input — the MCP
translation files describe the tools instead, with no mock values.

**`extension.yaml` is read either way.** It states which tools the extended agent may call
and when it must call them, and no other source answers either question. A `mcp-mock.json`
supplements it; it never replaces it.

**Never generate a mock catalog, and never fall back to scanning Python.** The base agent's
implementation is not part of an extension solution, so the
[`@tool` fallback](./tool-catalog.md#fallback-no-mcp-mockjson) has nothing to scan and never
applies here.

Read the sources listed below and **nothing else**. In particular, do not read the agent's or
the extension's implementation code — the intent and PRD are the complete behavioural source,
and the extension artifacts are the complete tool source.

Note which optional sources were absent:

1. **`intent.md`** *(priority 1)* — business challenge, milestones, fit-gap analysis.
2. **The extension PRD** *(priority 1)* — requirements with acceptance criteria, milestones
   with their achieved and missed conditions, and a business metrics table if present.
3. **`assets/*/extension.yaml`** *(priority 2)* — per capability, the `instruction` block,
   the tool names the extension grants, and any hooks. Always read.
4. **The tool descriptions** *(priority 2)* — `mcp-mock.json` when one exists, otherwise the
   MCP translation files, via [tool-catalog](./tool-catalog.md#which-source-applies).
5. **n8n workflow definitions** *(priority 2)* — where hooks declare an n8n deployment.
6. **The base agent's requirements and test suite** *(priority 3)* — the baseline, located
   below and triaged in [step 3](#3-triage-the-base-test-cases).

### Locate the baseline

An agent can be extended more than once, so there are two possible baselines. Use the first
that exists:

| Order | Baseline | Format |
|---|---|---|
| 1 | `{output_dir}/aeval/eval.yaml` | This skill's own format — a previous extension ran against this asset. |
| 2 | `<solution-root>/aeval/eval.yaml` | This skill's own format, written at the **old location** before the output moved into the asset folder. Read it, then write the result to `{output_dir}/aeval/` and report that the location moved. |
| 3 | The baseline's production config under `{base_aeval_path}/configs/` | The baseline's own format — this is the first extension. |
| 4 | None exists | No baseline — see [No baseline](#no-baseline). |

**Prefer `aeval/eval.yaml` when it is present**, at either location. It already incorporates
every earlier extension, whereas `aeval-base/` describes the agent before any of them.
Reconciling a second extension against `aeval-base/` would silently revert the first
extension's changes.

**Check order 2 before concluding there is no baseline.** A run that misses a prior
`eval.yaml` at the old location treats every requirement as NEW, rewrites the whole file, and
reports a clean first extension — with no sign that an earlier one was discarded.

Also load the matching `aeval/testcases/` beside whichever `eval.yaml` was taken — those
tests are reconciled in step 5.

**Load the base test suite separately, whichever baseline was used.**
`{base_aeval_path}/testcases/` describes behaviour the base agent already checks, and it is
an input regardless of whether the requirement baseline came from a prior `eval.yaml` or from
the base config. It is triaged in [step 3](#3-triage-the-base-test-cases), not read whole.

#### Reading a prior `eval.yaml`

Already in this skill's format: a `requirements` map with the three `*_requirements`
category lists of plain strings. Preserve order. No mapping applies.

#### Reading the baseline config

The baseline ships one config per environment under `configs/`. **Read the production one and
ignore the rest** — it is the canonical set; the others describe the same agent under
non-production settings.

It nests its requirements one level down, under a top-level `online:` key. Parse
`online.requirements[]`; each entry carries a `category` and a `details` string. Preserve
order.

Every other key beside `requirements` in that block is runtime configuration for the
baseline's own scoring process — lookback, schedule, and infrastructure flags. **Drop all of
them** and report which were dropped: none describe the extended agent, and the run
parameters this skill writes go in `config.yaml`.

The baseline's category names are its own and are **not** carried across as written.
`eval.yaml` uses exactly the three suffixed names (see
[eval-schema](./schemas.md#eval-requirements--evalyaml)). Match the base `category` by
**prefix, case-insensitively**:

| Base category (prefix match) | `eval.yaml` category |
|---|---|
| `agent_response*` | `agent_response_requirements` |
| `tool*` — `tool`, `tool_call`, `tool_usage`, `tool_compliance` | `tool_requirements` |
| `rule_compliance*` | `rule_compliance_requirements` |

Prefix, not exact string — base agents vary in spelling. A base agent may use any subset of
the three; a missing category is normal, not an error.

**An empty `tool_requirements` in the baseline is expected, not a gap to carry forward.** A
routing-only base agent calls no tools directly, so its config has nothing to put there. The
category is filled from the extension's own tool source instead — which is usually the whole
point of the extension — and it still has to reach 5 per [the
budget](./derive-eval-requirements.md#the-budget). Do not conclude the category is
inapplicable just because the baseline was silent on it.

If a base category matches none of the three, **do not drop the requirement.** Place it in
`rule_compliance_requirements` and report the original category name so a human can confirm
the routing.

---

## 2. Derive the extension's eval requirements

Follow [derive-eval-requirements](./derive-eval-requirements.md) against the extension
sources from step 1, applying it to **every** source read there rather than only what looks
new. It returns the eval requirements and the **source-to-requirements mapping** without
writing; step 4 decides which of the eval requirements survive reconciliation, and the
mapping is what coverage is measured against at step 6.

Do not read an existing `eval.yaml` as the answer here — that file is the baseline being
reconciled against, and the point of this step is to establish what the extension *now*
requires, independently of it.

Derive from PRD acceptance criteria (both the success and the error branch), the numbered
steps in a capability `instruction` block, required MCP tool parameters, and milestone
conditions.

A hook's execution is generally invisible to the evaluator — derive only its agent-visible
consequences, never the server-side call itself. When a hook or milestone has no
agent-visible consequence at all, record it as unassertable and report it rather than
inventing a proxy, per
[writing-checks](./writing-checks.md#when-nothing-about-it-is-observable).

### Detect contradictions among the extension's own inputs

Separately from reconciling against the baseline, compare the extension's sources against
each other. The common case is the PRD describing one behaviour while `extension.yaml`, a
tool schema, or a workflow implements another.

Resolve each by source precedence — generate from intent or PRD — and record the divergence.
**Never resolve one silently.** A contradiction here usually means the extension was built
differently from how it was specified, so the finding is often worth more than the eval
requirement it produced.

---

## 3. Triage the base test cases

**Skip when the base ships no `testcases/` folder.**

The base suite is the fullest record of what the agent is currently checked for — often an
order of magnitude more tests than this operation will write. It is an input, but it cannot
be read the way the other inputs are: a base suite of a hundred-plus files is far larger than
everything else this skill reads put together, and opening all of it would leave no context
for the work.

**Read it in two passes.**

### Pass 1 — build the index

For every file under `{base_aeval_path}/testcases/`, read **only** `id`, `tags`, and
`description`. Nothing else: not the steps, not the checks, not the input messages.

That is enough to know what each test covers, and it costs roughly a tenth of reading the
files. A base suite whose descriptions are too thin to triage from is a finding — say so, and
sample a handful in full rather than opening the set.

Ignore the folder names. Base suites organise by their own taxonomy — `functional/`,
`semantic/`, `guardrails_and_safety/`, and subfolders beneath them — and that structure is
the base team's, not a coverage model this skill shares.

### Pass 2 — cluster by behaviour, then triage

Group the index into **behaviour clusters**: sets of tests that check the same thing under
different inputs. Clusters are usually far coarser than the folders suggest — a suite with
fifty error-handling tests is typically checking a handful of behaviours across many
parameters.

Give each cluster one verdict:

| Verdict | When |
|---|---|
| **CARRY** | The behaviour is still required after the extension, and losing the check would lose real coverage. |
| **DROP** | The extension superseded it, it never applied to the extended agent, or it is redundant with a cluster already carried. |

Then order the CARRY clusters by what it would cost to stop checking them — a guardrail or a
data-fabrication cluster above a formatting one — because [the
budget](./design-test-cases.md#the-budget) will not hold all of them.

**Only now read files in full**, and only for the clusters that will actually produce a test
or a check. One representative per cluster is normally enough; read a second only when the
cluster's members genuinely differ.

### The budget applies to the union

The finished suite holds at most 15 tests covering **both** the base behaviour and the
extension. The extension's own journeys come first — nothing in the base covers the new
capability — and the carried clusters take what is left.

This means a large base suite is **sampled, not absorbed.** Say so plainly in the report and
name every dropped cluster by behaviour, so the reader can see what is no longer checked and
decide whether the base suite needs to keep running alongside this one. A reduction nobody
was told about is the failure mode here; the reduction itself is the budget working as
specified.

---

## 4. Reconcile the eval requirements

**Skip this step when there is no baseline** — see [No baseline](#no-baseline).

Work through the baseline eval requirements one entry at a time. Each gets exactly one
verdict:

| Verdict | When |
|---|---|
| **KEEP** | Still asserts the same thing under the extension. Restated in this skill's voice. |
| **UPDATE** | Still relevant, but the extension changes **what it asserts** — or its wording exposes control internals and must be narrowed to the obligation. |
| **DELETE** | No longer describes required behaviour. |

Then add every candidate eval requirement from step 2 that no baseline entry already covers,
as **NEW**.

These rules govern the step:

**Where the sources disagree, the extension wins** — but only because it is backed by intent
and PRD. If an implementation artifact alone contradicts a baseline eval requirement while
intent and PRD are silent, prefer UPDATE over DELETE and flag it.

**Always restate; never copy across.** The baseline's wording is the base agent's, and it
carries its authors' phrasing, terminology, and internal references. Rewrite every carried
eval requirement in this skill's own voice so the finished file reads as one document rather
than two, and so nothing of the base agent's internals travels with the text.

**Restating changes the words, never the substance.** This is the rule that makes the
rewrite safe, and it is easy to lose:

- **Every stated number survives exactly.** An eval requirement saying "more than 150
  characters" still says 150. Never soften a figure into "reasonably detailed" — the figure
  is the testable part, and a vague restatement silently moves the bar.
- **Every enumerated value, named condition, and ordering survives.** If the original fires
  on three specific states, the restatement fires on the same three.
- **The verdict boundary survives.** Whatever made the original pass or fail must make the
  restatement pass or fail, on the same inputs.
- **Every tool name and parameter name survives verbatim.** They are catalog identifiers, not
  prose. Restating `list_EmployeeTime_for_sfodata` as "the time-off tool" turns a requirement
  a judge can decide into one satisfied by any tool or none. Rewrite the sentence around the
  name, never the name itself — and where the extension replaced a tool, that is an UPDATE
  carrying the new name, not a paraphrase.
- **A `[BUSINESS_METRIC: <name>]` tag is copied exactly.** The tag is the one piece of text
  that must not be reworded: a downstream scorer matches the name literally, so paraphrasing
  it silently detaches the eval requirement from the metric it reports on. Restate the
  sentence around the tag, never the name inside it.

If you cannot restate it without changing what it checks, that is a signal the eval
requirement is doing something the rewrite would break. Keep the substance and flag it
rather than approximating.

**KEEP versus UPDATE is about meaning, not wording.** Every carried eval requirement is
reworded, so rewording alone never makes something an UPDATE. KEEP means *this still checks
exactly what it checked before*; UPDATE means *what it checks has changed*. Recording a
changed check as a KEEP hides the change from the only report anyone reads.

**Sensitivity is judged on what the text reveals, not on conflict.** An eval requirement can
be perfectly accurate and still expose how to defeat a control. Rewrite it to the
obligation, preserving the check and dropping the exploitable detail. That is an UPDATE,
even when nothing else changed.

Never resolve sensitivity by silently dropping an eval requirement — that loses the check
and leaves no trace. Rewrite it, or delete it and record the deletion.

### The budget applies to the reconciled file

**5 to 10 eval requirements in each category after reconciliation** — the same per-category
band as a fresh run, applied to KEEP plus UPDATE plus NEW, and counted per category rather
than as a total.

DELETE frees slots, so work in verdict order: settle every KEEP, UPDATE, and DELETE first,
then add the NEW entries into whatever room is left. Count per category before writing.

**A DELETE can push a category under 5**, and the total will not show it. When it does,
re-mine that category against [where the 5 come
from](./derive-eval-requirements.md#where-the-5-come-from) against the *extension's* sources —
the capability the extension added usually supplies the missing error path, confirmation
rule, or tool obligation. Report the category as thin only after that.

When a category exceeds 10, consolidate — never drop a check:

| Look first at | Because |
|---|---|
| Baseline entries written at fixture grain — one per field, per record, per identifier | They are the cheapest to merge into a task-scoped entry, and the concrete values survive in the test case's checks. |
| A baseline entry and an extension entry asserting the same obligation over different tools or objects | One entry stating the obligation, enumerating both. |
| Baseline entries for behaviour the extension superseded | These are DELETEs miscategorised as KEEPs. Re-judge them. |
| An entry filed in the wrong category | Moving it relieves the full category and often fills a starved one. Check this before merging anything. |

Two things are never consolidated away: **a `[BUSINESS_METRIC: …]` entry**, whose tag a
downstream scorer matches literally, and **an obligation the extension's intent or PRD states
outright**, which outranks the baseline by [source precedence](#source-precedence).

If a category still will not hold every obligation inside 10, keep the ceiling, keep the
highest-priority entries per [spend the budget in this
order](./derive-eval-requirements.md#spend-the-budget-in-this-order), and report every
obligation left out **by what it covers** — never by its position in the base file.

Hold the reconciled set in working memory, shaped per
[eval-schema](./schemas.md#eval-requirements--evalyaml). Step 6 writes it, overwriting
whatever was there.

---

## 5. Reconcile the test cases

The test cases must now match the eval requirements, not the eval requirements they were
written against.

There are two sets in play, and they are handled differently:

| Set | Where from | Handling |
|---|---|---|
| **This skill's own prior tests** | `{output_dir}/aeval/testcases/` | Verdicts below, inherited from the eval requirements they cover. |
| **The base agent's tests** | The CARRY clusters from [step 3](#3-triage-the-base-test-cases) | Reconstructed, never edited in place. See [Reconstructing a carried base cluster](#reconstructing-a-carried-base-cluster). |

Work from the verdicts in step 4.

| Eval requirement verdict | Test case action |
|---|---|
| KEEP | Leave the covering test case as it is, unless the tools it calls changed. |
| UPDATE | **Update** the covering test case so its checks assert the changed eval requirement. |
| DELETE | **Delete** the test cases that existed only to cover it. |
| NEW | **Create** a test case, following [design-test-cases](./design-test-cases.md#design-the-test-cases). |

**Only this skill's own test cases are ever carried forward *as files*.** `KEEP` leaves a
test in place because a previous run of this operation wrote it and it is already in this
skill's voice. A base test is never edited, renamed, or copied — the behaviour it checks is
rebuilt from scratch, so no base-authored wording, id, or structure reaches a generated file.
See [The baseline is an input, not a source to quote](#the-baseline-is-an-input-not-a-source-to-quote).

**Every surviving test must conform to the current format, whatever its verdict.**
`aeval/testcases/` can legitimately hold tests this skill did not write in the current shape
— hand-written ones, or output from an earlier version. A `KEEP` verdict says the *eval
requirement* still holds; it does not exempt the test file from the schema. Any surviving
test that is not a single `dynamic_conversation` step, or that carries placeholders, or
whose id or tags do not match the current convention, is **rewritten to [the current
format](./schemas.md#test-cases--testcasesidyaml)** with its assertions preserved. Report
every test rewritten this way.

### Reconstructing a carried base cluster

A CARRY cluster names a behaviour that must still be checked. Decide first whether it needs a
file at all: if a test already in the suite puts the agent in the situation the behaviour
applies to, it becomes **checks on that test**, per [a new check is
cheap](./design-test-cases.md#a-new-check-is-cheap-a-new-file-is-not). Only a cluster needing
its own situation earns a file.

Where it does, rebuild it. Base suites are written in a different schema and a different
voice, so every element converts:

| Base | Becomes |
|---|---|
| `type: fixed_message` steps | One `type: dynamic_conversation` step with a `task_summary` |
| Several steps in one file | **Still one step.** The sequence moves into `task_summary` as what the simulated user works through — see [one step per test case](./schemas.md#one-step-per-test-case). |
| `input_message` | The persona, goal, and known values inside `task_summary`; `initial_message` only when the exact opening phrasing is part of the test |
| Its `id` | A fresh `<NN>_<Category>_<Short>` continuing this suite's sequence. **Base ids and numbering are never carried** — they are internal labels. |
| Its `tags` | At least one dimension tag from [the tag set](./schemas.md#the-tag-set); the base's own vocabulary survives only as free sub-topic tags where it is still meaningful |
| `expected_tool_calls: []` | Omitted entirely, then written fresh from the extension's tool source where the behaviour involves a tool |
| Its check wording | Restated in this skill's voice, preserving every number, enumerated value, and verdict boundary exactly — the same discipline as [restating a requirement](#4-reconcile-the-eval-requirements) |

**A base suite that asserts no tool calls is normal and is not evidence the agent has no
tools.** A routing-only base agent has nothing to assert; the extension is what gives it
direct calls. Write the tool validations the *extension* justifies, and do not infer from an
empty base block that none apply.

**Every reconstructed test must land on an eval requirement.** A carried cluster with no
corresponding entry in the rewritten `eval.yaml` is a parity orphan: either the requirement
it implies is missing and should be added, or the behaviour is not actually required and the
cluster should have been DROP. Resolve it now, not at validation.

These rules are specific to reconciling tests:

**The folder holds at most 15 test cases after reconciliation, and at least 3 per applicable
group.** Same bounds as a fresh run, applied to the surviving tests, the reconstructed base
clusters, and the new ones together. Deletions free slots, so apply every DELETE before
creating anything — and re-count per group afterwards, because a DELETE that empties a group
is how reconciliation drops below the floor without the total ever looking wrong. When a NEW
eval requirement needs coverage and the folder is full, add a check to the test whose
scenario already provokes it rather than a file — see [a new check is
cheap](./design-test-cases.md#a-new-check-is-cheap-a-new-file-is-not). A new file is
justified only by a situation no surviving test creates, which for an extension usually means
a genuinely new capability.

**A test covering several eval requirements is updated, not deleted.** Delete only when
every eval requirement a test targets was deleted. Otherwise strip the checks belonging to
the deleted eval requirement and keep the rest.

**New user journeys need goal-completion tests.** The extension usually adds a capability,
which is a new journey. Define it per
[design-test-cases](./design-test-cases.md#define-the-user-journeys) and give it a happy
path and at least one failure path — a new capability with only compliance tests has never
been shown to work end to end.

**Re-resolve the tools before updating anything.** The extension adds MCP tools, so the tool
source has changed. A test asserting a tool name the extension no longer grants fails for a
reason that looks like an agent bug. Re-read the catalog per
[tool-catalog](./tool-catalog.md#extension-tool-source) and update every affected
`tool_validations` block and every asserted value. Take tool names from
`extension.yaml`'s `mcpToolName` or the translation file's `tools[].name` — never from what
the PRD calls the capability.

**The deletion guardrail applies to all `expected_tool_calls` written or updated here** —
including UPDATEs and reconstructed base clusters, not only new test cases. See
[design-test-cases](./design-test-cases.md#applies-to-every-test-case).

**Ids stay stable where the test survives.** Keep the existing `<NN>_<Category>_<Short>` id
on a KEEP or UPDATE so a reader can follow a test across extensions. New tests and
reconstructed base clusters continue the `NN` sequence from the highest existing number.
Deleting a test leaves a gap in the sequence — leave it, and do not renumber the folder.

Then write `config.yaml` per [schemas](./schemas.md#runtime-parameters--configyaml), using
the defaults — unless one already exists, in which case leave it untouched. Never ask the
user for these values.

---

## No baseline

Neither `aeval/eval.yaml` nor the base agent's config exists. Do not ask for one and do not
stop.

- **Skip steps 3 and 4 entirely.** Nothing receives a KEEP, UPDATE, DELETE, CARRY or DROP
  verdict, because there is nothing to judge against. A base `testcases/` folder with no
  requirements config beside it is *not* "no baseline" — triage it per [step
  3](#3-triage-the-base-test-cases) and derive the requirements its carried clusters imply.
- **Treat every candidate from step 2 as NEW**, and run step 2 against every source read in
  step 1 — not only the material that looks new. With no baseline, the extension sources are
  the whole picture.
- **Generate the test cases fresh** per
  [design-test-cases](./design-test-cases.md#design-the-test-cases) rather than reconciling.

Tell the user the evaluation was generated without a baseline, so it describes the extended
agent's behaviour as the extension sources define it rather than as a delta.

Everything else applies unchanged: source precedence, [writing-checks](./writing-checks.md).

---

## 6. Validate, write, and report

Follow [validate-and-report](./validate-and-report.md) for the full checklist, the coverage
measurement, and the report. **Do not write anything before running it** — parity orphans
add eval requirements to `eval.yaml`, and misplaced assertions move between validation
blocks.

Three additional checks apply here, specific to reconciliation:

1. **Parity survives the reconciliation.** Every eval requirement in the rewritten
   `eval.yaml` is covered by at least one test, and every remaining test covers at least one
   eval requirement — [the parity rule](./validate-and-report.md#the-parity-rule) applied to
   the post-reconciliation state.

   Reconciliation is where parity breaks most easily, because both sides move at once. Two
   failures to look for specifically:

   - A test left behind by a **DELETE**, covering an eval requirement that no longer exists.
   - A **NEW** eval requirement that never got a test — the failure mode this whole
     operation exists to prevent.

   Check it against the rewritten file, not the baseline. A test that matched a baseline
   eval requirement is an orphan if the UPDATE moved what that eval requirement asserts.

   Fix every orphan before writing: write the missing test, or add the missing eval
   requirement, or delete the test if the extension genuinely no longer asks for it.

2. **The budget holds after reconciliation.** Count the rewritten `eval.yaml` **per
   category** against the band of 5 to 10, and the surviving plus new test files against the
   floor of 3 per applicable group and the cap of 15 in total. Outside any bound, resolve it
   per [the budget applies to the reconciled
   file](#the-budget-applies-to-the-reconciled-file), then re-check parity and extension
   coverage — a merge is exactly where a reconciliation loses a check without leaving a
   trace.

3. **Nothing carried verbatim from the baseline.** Search every finished file — `eval.yaml`,
   every test case, `config.yaml` — for any baseline path segment, and for any requirement
   label, test id, or numbering belonging to it. None may appear. See [The baseline is an
   input, not a source to quote](#the-baseline-is-an-input-not-a-source-to-quote).

   Reading the base test suite makes this check matter more. For every reconstructed cluster,
   confirm the finished test carries **none of the baseline's id, filename, folder name, tag
   vocabulary, or check wording**, and that it is a single `dynamic_conversation` step rather
   than the baseline's step type. A carried behaviour is correct; a carried sentence is not.

4. **The architecture was re-determined, not inherited.** An extension commonly changes it —
   a routing-only base agent that gains direct tool access becomes an orchestrator with
   tools, and its `tool_validations` become meaningful for the first time. Re-run [the
   architecture step](./generate-eval-scenarios.md#2-establish-the-agent-architecture)
   against the extended agent. An empty `expected_tool_calls` throughout the base suite is
   evidence about the *base*, never about the extended agent.

---

## 7. Report

Follow [the report](./validate-and-report.md#the-report) — the same short summary and the
same exceptions-only rule. All of it goes in conversation; **write no summary file.**

An extension adds **one line to the summary** and a few exception rows. It does not add a
second report. Resist the pull to narrate the reconciliation: most of it went fine, and the
reader only needs what changed and what was lost.

### One extra summary line

```
Base    <baseline described>; K keep / U update / D delete / N new · C clusters carried of T indexed
```

Describe the baseline, never name it by path — "the base agent's requirements", "the previous
extension's requirements", or "none". See [The baseline is an input, not a source to
quote](#the-baseline-is-an-input-not-a-source-to-quote).

### Extra exceptions — only when non-empty

| Report | When |
|---|---|
| **Changed** — each UPDATE and DELETE by *what it covers*, never by its position in the base file, with what changed and why | Any were |
| **Dropped base coverage** — each dropped cluster by behaviour, with its reason, and **budget** called out separately from superseded or not-applicable | Any cluster was dropped |
| **Drift** — an implementation artifact contradicted intent or PRD, and which won | Any did |
| **Input contradictions** — among the extension's own sources, and how each resolved | Any found |
| **Architecture changed** — the base's versus the extended agent's | It changed |
| **Reformatted** — tests rewritten to the current schema, by id | Any were |
| **Runtime keys dropped** from the base config | Any were |
| **New tools** granted by the extension, and the tests updated for them | Any were |

**A budget-driven drop is the one exception worth spelling out**, because it names coverage
the base suite has and this one does not. Two lines at most, and never phrased as though the
behaviour stopped mattering.

---

## 8. Write environment management templates

If they do not already exist, write:
- `{output_dir}/aeval/testcases/000_pre_setup.yaml`
- `{output_dir}/aeval/testcases/zzz_post_teardown.yaml`

Use the templates from [schemas](./schemas.md#environment-management-templates).
Never overwrite existing files.
