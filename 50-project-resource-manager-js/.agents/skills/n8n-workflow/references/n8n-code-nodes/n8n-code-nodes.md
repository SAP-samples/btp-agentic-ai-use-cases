# n8n Code Nodes

The Code node is powerful and often the wrong tool. Real cases exist, but the moment a Code node handles logic an expression could, the workflow becomes harder to read, debug, and maintain. There's also a real perf gap: Code runs in a sandboxed JS runtime; expressions and Edit Fields run in-process. Per-invocation overhead: ~600ms in Code vs ~2ms for equivalent logic in an Edit Fields arrow function. For hot paths and large item counts, that compounds.

## Strong defaults

1. **Code node is a last resort.** Decision order: expression (`{{...}}`) → arrow function inside Edit Fields → Code node. The first two paths cover most "transform this data" tasks. Code earns its place for multi-source aggregation, external libraries, and the specific patterns documented below.

2. **Default to JavaScript.** Write JS unless the user explicitly asked for Python. Everywhere else in n8n (expressions, Edit Fields) is JS, and JS has a curated library allowlist (`lodash`, `crypto`, `luxon`).

## Decision tree (at a glance)

```
Need custom logic?
├── Is it a transformation of one or two fields?
│   └── Expression: {{ $json.foo.toUpperCase() }}
│
├── Is it multi-line, but pure data shaping (map, filter, reduce, conditional)?
│   └── Edit Fields with arrow function expression (see n8n-code-nodes-arrow-functions.md)
│
├── Does it need full statements, multiple data sources, or external libs?
│   ├── Are you SURE the above two don't work? Re-read. The bar is high.
│   └── Yes, genuinely needs it → Code node (see n8n-code-nodes-javascript-patterns.md)
│
└── Is it actually two separate transformations stitched together?
    └── Use two nodes (Edit Fields → Edit Fields). Composability beats one big Code block.
```

For the full decision logic with per-branch examples, see `./n8n-code-nodes-decision-tree.md`.

## What expressions can do that people forget

Common reaches-for-Code-node that should be expressions:

```ts
// ❌ Code node
return { name: $input.first().json.name.toUpperCase() }

// ✅ Expression in Edit Fields, "name" field
{{ $json.name.toUpperCase() }}
```

```ts
// ❌ Code node
const items = $input.first().json.items
return { tags: items.map(item => item.tag).filter(tag => tag).join(', ') }

// ✅ Expression
{{ $json.items.map(item => item.tag).filter(tag => tag).join(', ') }}
```

```ts
// ❌ Code node
const date = new Date($input.first().json.created_at)
return { formatted: date.toISOString().slice(0, 10) }

// ✅ Expression with n8n's date extension
{{ $json.created_at.toDateTime().format('yyyy-MM-dd') }}
```

For more, see `../n8n-expressions/n8n-expressions.md`.

## What arrow-functions-in-Edit-Fields can do

Edit Fields assigns field values via expression. Inline arrow functions get you most multi-line logic without the Code node:

```ts
// In Edit Fields, "summary" field:
{{ (() => {
    const items = $json.items
    const total = items.reduce((sum, item) => sum + item.price, 0)
    const tax = total * 0.08
    return `Total: $${(total + tax).toFixed(2)}`
})() }}
```

Right tool for "logic slightly too gnarly for a one-liner." See `./n8n-code-nodes-arrow-functions.md` for patterns, formatting, and cross-item aggregation with Execute Once.

## When the Code node IS the right answer

### Multi-source aggregation across the whole dataset

When a node needs to read from multiple upstream nodes simultaneously, compute statistics across all items at once, or apply multi-step logic with intermediate data structures (lookup maps, accumulators, ratios).

Most common valid case:

```ts
const testResults = $('Get Test Results').all().map(item => item.json)
const models = $('Get Models').all().map(item => item.json)
const categoryMap = $('Get Category Map').first().json.testCategoryMap

const categoryByTestId = Object.fromEntries(
    categoryMap.map(mapping => [mapping.testId, mapping.category])
)

const result = models.map(model => {
    const modelTests = testResults.filter(test => test.modelId === model.id)
    const stats = modelTests.reduce((acc, test) => {
        const cat = categoryByTestId[test.testId]
        if (!cat) return acc
        acc[cat] ??= { scored: 0, available: 0, count: 0 }
        acc[cat].scored += test.pointsScored ?? 0
        acc[cat].available += test.pointsAvailable ?? 0
        acc[cat].count += 1
        return acc
    }, {})

    const averages = Object.fromEntries(
        Object.entries(stats).map(([category, stat]) => [
            category,
            { avg: stat.available > 0 ? stat.scored / stat.available : 0, n: stat.count }
        ])
    )

    return { modelId: model.id, modelName: model.modelName, ...averages }
})

return result.map(json => ({ json }))
```

### External libraries

JS Code can `require` from a curated allowlist (lodash, etc.). Expressions can't.

**Always check for a native node first** before reaching for Code+library.

### Cryptographic operations: use the Crypto node, not Code

HMAC, signing, hashing, encryption: **n8n has a native Crypto node (`n8n-nodes-base.crypto`).** Use it. It handles SHA256, MD5, HMAC, encrypt/decrypt, and random generation without writing JavaScript.

```ts
// WRONG (recurring AI slip):
const crypto = require('crypto')
const hash = crypto.createHash('sha256').update(buf).digest('hex')

// RIGHT: configure the Crypto node with operation: 'hash', type: 'SHA256'
```

Also covers **binary hashing**: the Crypto node has a `binaryPropertyName` parameter — point it at the binary slot key and it hashes the buffer directly, no Code needed.

The remaining valid Code-for-crypto case: a non-standard signing scheme the Crypto node doesn't expose AND `httpCustomAuth` doesn't fit either. Rare.

### XML / SOAP / RSS parsing: use the XML node, not Code

**n8n has a native XML node (`n8n-nodes-base.xml`).** Once it parses XML to JSON, Edit Fields with arrow function expressions handles all field extraction, array normalization, and `.find()` logic.

```ts
// WRONG (recurring AI slip after XML node has already parsed):
const entry = $('Parse XML').item.json.feed.entry
const firstEntry = Array.isArray(entry) ? entry[0] : entry
return { json: { title: firstEntry.title, url: firstEntry.link.find(link => link.type === 'pdf').href } }

// RIGHT: Edit Fields with arrow function expressions
//   title:  ={{ (() => { const entry = $('Parse XML').item.json.feed.entry; return Array.isArray(entry) ? entry[0].title : entry.title; })() }}
//   pdfUrl: ={{ $('Parse XML').item.json.feed.entry.link.find(link => link.type === 'pdf')?.href }}
```

## Quick tests before reaching for Code

- **"Could I describe this Code node's job as 'take this one item and...'?"** If yes, wrong tool — use expression or Edit Fields.
- **"Is there a native node for this?"** Search via `search-nodes-catalog` first. Crypto, XML, JSON parsing, date math (Luxon), HTTP calls, file I/O, regex matching: all have native nodes or expression-level support.

## Return shape

The Code node must return an array of `{ json: ... }` objects:

```ts
// ✅ Correct
return [{ json: { foo: 'bar' } }]
return result.map(json => ({ json }))

// ❌ Wrong — raw object, not array-of-{json}
return { foo: 'bar' }
```

## Anti-patterns

| Anti-pattern | What goes wrong | Fix |
|---|---|---|
| Code node doing `return { x: $input.first().json.x.toUpperCase() }` | Whole node for one expression | Replace with an Edit Fields expression |
| Code node building HTML strings for an email body | The Email node's body field accepts expressions | Inline the expression into the email node |
| Code node using `new Date()` for date formatting | Loses to Luxon's clarity | Use Luxon in expression — see `../n8n-expressions/n8n-expressions.md` |
| Set node + Code node combo (Set builds inputs, Code transforms) | Two nodes for what should be one Edit Fields | Collapse into one Edit Fields with arrow function |
| Pasting credentials/tokens into Code node text | Leaks secrets into workflow JSON | Use credentials, not Code node |
| Code node for HMAC/hash | Native Crypto node does this | Use the Crypto node |
| Code node after XML parsing | Edit Fields handles field extraction | Use Edit Fields with arrow function |
