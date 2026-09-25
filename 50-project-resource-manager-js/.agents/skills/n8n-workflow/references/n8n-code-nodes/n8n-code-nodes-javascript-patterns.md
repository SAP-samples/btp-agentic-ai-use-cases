# JavaScript Code node patterns

Once `./n8n-code-nodes-decision-tree.md` confirms Code is necessary, this covers patterns and gotchas.

## Run modes

Two execution modes. **Default to Run Once for All Items.** It's the standard shape and almost always what you want, even when the work is per-item: just `for (const item of $input.all())` or `.map()` inside.

### Run Once for All Items (default, use this)

Runs once with all items as `$input.all()`. Per-item logic just goes inside the loop.

```ts
const items = $input.all()
const totals = items.map(item => ({
    ...item.json,
    total: item.json.qty * item.json.price,
}))
return totals.map(json => ({ json }))
```

### Run Once for Each Item

Runs once per input item. `$input.first()` (or `$input.item`) is the current item.

```ts
const item = $input.first().json
return [{ json: { ...item, total: item.qty * item.price } }]
```

### Picking the mode

| Need | Mode |
|---|---|
| Anything aggregate / reduce across items | Run for All |
| Combine items conditionally | Run for All |
| Per-item transform | Run for All with a loop inside (Edit Fields is usually better) |
| Per-item with explicit error isolation per item | Run for Each, paired with `continueOnFail` |
| Fan-out: turn 1 input item into N output items | Run for All, return the expanded array |

## Return shape

The Code node must return an array of `{ json: ... }` objects. Variations:

```ts
// Single output item
return [{ json: { foo: 'bar' } }]

// Multiple output items
return [
    { json: { id: 1 } },
    { json: { id: 2 } },
]

// Item with binary
return [{
    json: { name: 'report.pdf' },
    binary: { data: { /* binary data */ } }
}]

// Empty output (skip downstream)
return []
```

Common mistake: returning the raw object instead of the array-of-`{json}` shape.

```ts
// ❌ DON'T
return { foo: 'bar' }

// ✅ DO
return [{ json: { foo: 'bar' } }]
```

## Available libraries

Curated list of pre-imported / requireable libraries. Reliably present:

- `crypto`: Node's crypto module.
- `lodash` (sometimes as `_`): `groupBy`, `chunk`, `keyBy` are handy.
- `moment`: deprecated. Prefer Luxon, available globally.

No HTTP client (`axios`, `node-fetch`, etc.) is bundled. Use the SAP MCP Client node for external API calls — hard line.

You cannot install new packages.

## Handling binary data

Binary lives in `item.binary[<key>]`, separately from `item.json`. Common patterns:

```ts
// Pass binary through unchanged
const items = $input.all()
return items.map(item => ({
    json: { ...item.json, processed: true },
    binary: item.binary,
}))
```

```ts
// Read binary as buffer (e.g., for hashing)
// NOTE: prefer the native Crypto node for hashing — it handles binaryPropertyName directly
const item = $input.first()
const buffer = await this.helpers.getBinaryDataBuffer(0, 'data')
const hash = crypto.createHash('sha256').update(buffer).digest('hex')
return [{ json: { hash }, binary: item.binary }]
```

## Common patterns that justify Code

### Aggregation that built-in nodes don't cover

```ts
// Compute median across input items
const values = $input.all().map(item => item.json.value).sort((a, b) => a - b)
const mid = Math.floor(values.length / 2)
const median = values.length % 2
    ? values[mid]
    : (values[mid - 1] + values[mid]) / 2

return [{ json: { median, count: values.length } }]
```

Check `search-nodes-catalog` for a built-in aggregation node first.

### HMAC signing

```ts
const crypto = require('crypto')

const item = $input.first().json
const body = JSON.stringify(item.payload)
const signature = crypto
    .createHmac('sha256', item.secret)
    .update(body)
    .digest('hex')

return [{ json: { ...item, signature } }]
```

The secret should come from a credential, not from input data.

## Things to avoid

### `console.log` for "debugging"

Goes to instance logs the user may not have access to. To surface debug info downstream:

```ts
return [{ json: { ...result, _debug: { stepCount: 3, intermediate } } }]
```

Strip `_debug` in a downstream Edit Fields before publishing.

### Long-running synchronous loops

A `for` loop doing HTTP calls or thousands of synchronous items blocks execution and may time out.

- HTTP calls: HTTP Request node + `SplitInBatches`.
- Many items: smaller batches + Aggregate to combine.

### Error swallowing

```ts
// DON'T — returns error as data, workflow continues as if all is well
try {
    return [{ json: doRiskyThing() }]
} catch (error) {
    return [{ json: { error: error.message } }]
}
```

Let Code throw, set `onError: 'continueErrorOutput'` and wire `output(1)` to an error branch.

### Re-implementing built-in functionality

If you're writing JS for HTTP calls, email sending, file uploads, date math, or XML parsing — use the corresponding native node or Luxon in expressions.

## Performance

Code runs in a sandboxed JS runtime. The same logic in an Edit Fields arrow function (in-process via the expression engine) can be ~100x faster. For most workflows the overhead is a rounding error next to one HTTP call. When it matters (hot paths, large item counts, latency-sensitive webhooks), see the performance section in `./n8n-code-nodes-arrow-functions.md`.

Profile via `get_workflow_execution` before optimizing — 99% of the time the bottleneck is upstream.

## Testing

Always run `test_workflow` after writing a Code node. Most error-prone single-node category in n8n: type errors, return-shape mistakes, library assumptions. Test before publish.
