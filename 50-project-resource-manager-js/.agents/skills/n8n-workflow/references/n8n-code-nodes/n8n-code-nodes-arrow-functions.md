# Arrow functions inside Edit Fields

This pattern handles "logic too gnarly for one line, but just data shaping" without a Code node. An immediately-invoked arrow function inside an Edit Fields expression.

## The shape

In an Edit Fields node, set a field's value to:

```ts
{{ (() => {
    // multi-line logic here
    const x = $json.someField
    const y = doSomething(x)
    return y
})() }}
```

Breakdown:

- `{{ ... }}`: n8n expression delimiter.
- `(() => { ... })()`: arrow function defined and immediately invoked.
- Inside: any JS function body.
- `return`: the field's value.

## What you can do inside

Pretty much anything in plain JS:

- Multiple `const` / `let`.
- `if/else`, `switch`.
- `for` / `while` (use sparingly — `map/filter/reduce` is usually cleaner).
- `try/catch`.
- Inline regex.
- Native JS stdlib: `Math`, `JSON`, `String`, `Array`, `Object`, `Number`, `Map`, `Set`. Prefer Luxon over `Date`.
- Luxon (`DateTime`, `Interval`, `Duration`).

What you **can't** do:

- `require()` external libs: Code-node-only.
- `await`: expressions are synchronous.

Edit Fields **can** call `$input.all()` and `$('Other Node').all()` — pair with the **Execute Once** toggle for cross-item aggregation without a Code node. See "Cross-item aggregation with Execute Once" below.

## When to use

Use arrow functions in Edit Fields when the logic is too long for one line, you need intermediate variables, you want comments, or you'd otherwise reach for Code. Works for both per-item logic (default mode) and cross-item aggregation (Execute Once toggled on).

Code is the right answer when the aggregation logic is too gnarly for an inline arrow function, you need external libs, or you need async.

## Performance: the main reason to prefer arrow functions

Code nodes run in a sandboxed JS runtime, separate from n8n's main process. Each invocation pays sandbox setup, value marshaling, and isolation overhead. Edit Fields arrow functions run in n8n's expression engine, in-process, with none of that.

The gap is large in practice: the same logic measures ~2ms in an Edit Fields arrow function vs ~600ms in a Code node. The exact ratio varies, but the order of magnitude is real.

For most workflows this doesn't matter — the Code node's overhead is a rounding error next to one HTTP call. But when it matters:

- **Hot paths.** High-frequency triggers (webhook per request, scheduled-every-minute).
- **Large item counts.** Per-item Code execution at 600ms × 10000 items adds up fast.
- **Latency-sensitive surfaces.** Synchronous chat replies, request-response webhooks where total time is user-visible.

In those cases, cramming what would naturally be a Code node into an Edit Fields arrow function can be worth the readability hit. A 50-line IIFE inside `{{...}}` is harder to read than a clean Code node — but if profiling shows the Code node is the bottleneck, the win is real and measurable. Deliberate trade, not a default.

## Examples

### Conditional field assembly

```ts
{{ (() => {
    const status = $json.status
    const dueDate = $json.due_date
        ? DateTime.fromISO($json.due_date)
        : null
    const isOverdue = dueDate
        && dueDate < DateTime.now()
        && status !== 'completed'

    if (isOverdue) {
        return `⚠️ OVERDUE: ${$json.title}`
    }
    if (status === 'in_progress') {
        return `🔄 ${$json.title}`
    }
    if (status === 'completed') {
        return `✅ ${$json.title}`
    }
    return $json.title
})() }}
```

### Building structured data for an email

```ts
{{ (() => {
    const items = $json.line_items
    const subtotal = items.reduce((sum, item) => sum + item.price * item.qty, 0)
    const tax = subtotal * 0.08
    const total = subtotal + tax

    const rows = items
        .map(item => `<tr><td>${item.name}</td><td>${item.qty}</td><td>$${item.price.toFixed(2)}</td></tr>`)
        .join('\n')

    return `
        <h1>Invoice #${$json.invoice_id}</h1>
        <table>
            <thead><tr><th>Item</th><th>Qty</th><th>Price</th></tr></thead>
            <tbody>${rows}</tbody>
        </table>
        <p>Subtotal: $${subtotal.toFixed(2)}</p>
        <p>Tax: $${tax.toFixed(2)}</p>
        <p><strong>Total: $${total.toFixed(2)}</strong></p>
    `
})() }}
```

Historically gets written in a Code node and read into an email node. The arrow-function-in-Edit-Fields version keeps it in one place.

### Parsing freeform user input

```ts
{{ (() => {
    const text = $json.user_message.toLowerCase()

    const wantsHelp = /\b(help|stuck|how do i)\b/.test(text)
    const wantsCancel = /\b(cancel|unsubscribe|stop)\b/.test(text)
    const wantsContact = /\b(contact|reach|talk to)\b/.test(text)

    if (wantsCancel) return 'cancel'
    if (wantsHelp) return 'help'
    if (wantsContact) return 'contact'
    return 'unknown'
})() }}
```

### Sanitizing input

```ts
{{ (() => {
    let title = $json.title
    title = title.trim()
    title = title.replace(/\s+/g, ' ')         // collapse whitespace
    title = title.replace(/[^\w\s\-.]/g, '')   // strip non-alphanumeric (keep dash and dot)
    title = title.slice(0, 100)                // cap length
    return title
})() }}
```

## Formatting rules

Past ~5 lines, formatting matters. Indent generously, comment intent.

```ts
{{ (() => {
    // Compute stripe-style amount in cents from dollar amount
    const dollars = parseFloat($json.amount)
    if (isNaN(dollars) || dollars < 0) {
        return null
    }

    const cents = Math.round(dollars * 100)

    // Cap at Stripe's max (per their docs)
    return Math.min(cents, 99999999)
})() }}
```

4-space indents inside the function. Comments above non-obvious blocks.

For broader expression rules, see `../n8n-expressions/n8n-expressions.md`.

## Common mistakes

### Forgetting to invoke the function

```ts
// DON'T: defines but doesn't call
{{ () => {
    return $json.foo.toUpperCase()
} }}
```

The result of this expression is the function itself, not its return value. Always close with `()` to invoke:

```ts
{{ (() => {
    return $json.foo.toUpperCase()
})() }}
```

### Returning nothing

```ts
{{ (() => {
    const x = $json.foo
    x.toUpperCase()  // ← no return
})() }}
```

Evaluates to `undefined`. Always end with an explicit `return`.

### Cross-item aggregation with Execute Once

By default Edit Fields runs once per input item, so calling `$input.all()` inside an arrow function re-evaluates the same array N times. Toggle **Execute Once** on the node and the expression runs once total, producing one output item:

```ts
// Execute Once enabled on the Edit Fields node
{{ (() => {
    const items = $input.all().map(item => item.json)
    const total = items.reduce((sum, item) => sum + item.amount, 0)
    return `Processed ${items.length} items, total $${total.toFixed(2)}`
})() }}
```

The same shape works for `$('Other Node').all()`. Reach for a Code node only when the aggregation logic is too gnarly for an inline arrow function (joins, group-bys, multiple intermediate structures).

Without Execute Once, the expression still resolves — you just pay the cost N times and produce N identical output items, which is almost never what you want.

### Awaiting

```ts
// DON'T — expressions are synchronous
{{ (async () => {
    const data = await fetch(...)
})() }}
```

If you need async work, that's a separate node (HTTP Request, etc.), not an arrow function.

## When this gets too big

Past ~30 lines, ask:

1. Could this be split into multiple Edit Fields steps?
2. Is this genuinely a Code case? See `./n8n-code-nodes-decision-tree.md`.
