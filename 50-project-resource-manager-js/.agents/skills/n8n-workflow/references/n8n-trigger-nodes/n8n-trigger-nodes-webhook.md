# Webhook Trigger and Respond to Webhook

Entry and exit of webhook-shaped API workflows. Param shapes are version-dependent; `get_node_types` is canonical. This file covers what's *not* in the type def: runtime behavior, gotchas, and patterns.

---

## Webhook Trigger

### `responseMode`: behavioral differences

| Mode | `responseMode` value | n8n UI Label | Behavior |
|---|---|---|---|
| Immediate | `'onReceived'` (default) | Immediately | Returns 200 immediately. Workflow continues asynchronously. Caller doesn't see workflow output. |
| Last node | `'lastNode'` | When Last Node Finishes | Returns the last node's output. Synchronous. |
| Respond node | `'responseNode'` | Using 'Respond to Webhook' Node | Use `Respond to Webhook` nodes to control the response. Most flexible. |
| Streaming | `'streaming'` | Streaming | Stream data in real time from streaming-enabled nodes. |

For request/response API workflows, use `responseNode` paired with explicit Respond to Webhook nodes.


### Output structure (runtime)

The webhook trigger emits `{ headers, params, query, body, webhookUrl, executionMode }`, plus `binary` if `options.rawBody` is set, plus `jwtPayload` if JWT auth was used. `executionMode` is `'test'` or `'production'`.

Access POST body fields via `$json.body.*` paths.

---

## Respond to Webhook

### `responseBody` for `respondWith: 'json'`: pass the object, not a string

The type def accepts both `IDataObject` and `string`. If you pass `JSON.stringify(obj)`, n8n then JSON-serializes the *string*, producing an escaped, double-encoded body. Pass the object directly.

### `responseCode` defaults to 200, including on error paths

The most common Respond-to-Webhook bug: forgetting to change the response code on an error branch. Returning 200 with an error body is worst-of-both-worlds: the caller's HTTP client sees success while the body says failure.

Set the response code explicitly on every Respond branch.

### Multiple Respond nodes per workflow

A workflow can have multiple Respond nodes, one per response shape. n8n returns whichever fires first.

```
[Webhook] ─→ [Validate] ─→ [Process] ─→ [Respond 200 success]
            ├─→ [Respond 400 validation_error]
            ├─→ [Respond 401 unauthorized]
            └─→ (error outputs from process) ─→ [Respond 5xx]
```

---

## Common Errors to avoid.

### ERROR: Using `'lastNode'` when the workflow contains SAP Task Center

```
Webhook (lastNode) → ... → SAP Task Center → Switch → Respond
```

SAP Task Center is a human approval step that can block for minutes or hours. The HTTP request times out with a **502 Bad Gateway** long before the workflow completes. The caller receives an error even if the workflow eventually succeeds.

**Fix:** Use `'onReceived'` to acknowledge receipt instantly and let the workflow continue asynchronously — or use `'responseNode'` and place a `Respond to Webhook` node immediately after the webhook to confirm receipt before the long-running step begins.

---

### ERROR: Using `'responseNode'` without a `Respond to Webhook` node on every branch

```
Webhook (responseNode) → IF → [true branch: Respond to Webhook]
                             → [false branch: Set node]   // no respond node — caller hangs
```

If a branch never reaches a `Respond to Webhook` node, the caller waits until the request times out or fails on that path.

**Fix:** Ensure every execution branch that can be reached connects to a `Respond to Webhook` node. Apply the multiple-Respond-nodes pattern above: one per response shape.

---

### ERROR: Using `'lastNode'` expecting a specific response shape

```
Webhook (lastNode) → ... → Set { status: "ok" }
```

`'lastNode'` returns the raw output of the last node. If the workflow has multiple end nodes or the output shape changes, the response becomes unpredictable.

**Fix:** Use `'responseNode'` with a `Respond to Webhook` node to explicitly control the response payload.
