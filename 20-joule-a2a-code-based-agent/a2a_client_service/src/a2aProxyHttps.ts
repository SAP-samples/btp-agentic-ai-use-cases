/**
 * HTTPS-based SSE streaming for A2A.
 *
 * Node.js's native `fetch` (undici) has issues streaming SSE responses in
 * real-time (hangs after first chunk). This module uses `https.request`
 * directly for reliable chunk-by-chunk SSE delivery.
 */

import https from 'node:https'
import type { IncomingMessage } from 'node:http'
import { URL } from 'node:url'
import type { A2AStreamEvent } from './a2aProxy.js'

// Singleton HTTPS agent with keepAlive for connection pooling
const httpsAgent = new https.Agent({
  keepAlive: true,
  keepAliveMsecs: 30000, // Send keepalive probes every 30 seconds
  maxSockets: 50,
  maxFreeSockets: 10,
})

interface StreamOptions {
  rpcEndpoint: string
  authHeaders: Record<string, string>
  requestBody: unknown
}

/**
 * Streams A2A events using Node.js's native `https.request`.
 *
 * Unlike `fetch`, `https.request` delivers SSE chunks immediately without
 * buffering, ensuring real-time event delivery from the remote A2A server.
 */
export async function* streamViaHttps(
  options: StreamOptions,
): AsyncGenerator<A2AStreamEvent, void, undefined> {
  const { rpcEndpoint, authHeaders, requestBody } = options

  const url = new URL(rpcEndpoint)
  const requestOptions = {
    hostname: url.hostname,
    port: url.port || (url.protocol === 'https:' ? 443 : 80),
    path: url.pathname + url.search,
    method: 'POST',
    headers: {
      ...authHeaders,
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
      Connection: 'keep-alive',
    },
    // Use singleton agent for connection pooling
    agent: httpsAgent,
  }

  const bodyStr = JSON.stringify(requestBody)

  // Wait for the HTTP response to start
  const res = await new Promise<IncomingMessage>((resolve, reject) => {
    const req = https.request(requestOptions, (response) => {
      console.log(`[https] status=${response.statusCode} content-type=${response.headers['content-type']}`)

      if (response.statusCode !== 200) {
        let errBody = ''
        response.on('data', (chunk) => {
          errBody += chunk.toString()
        })
        response.on('end', () => {
          reject(new Error(`HTTP ${response.statusCode}: ${errBody}`))
        })
        return
      }

      resolve(response)
    })

    req.on('error', (err) => {
      reject(err)
    })

    req.write(bodyStr)
    req.end()
  })

  // Now iterate the response stream and yield events
  yield* parseSSE(res)
}

/**
 * Parses SSE events from an HTTP response stream using event-driven approach.
 *
 * This uses manual event handling instead of `for await` to avoid async iterator
 * issues that can cause the stream to close prematurely.
 */
async function* parseSSE(
  res: IncomingMessage,
): AsyncGenerator<A2AStreamEvent, void, undefined> {
  let buffer = ''
  let eventCount = 0

  console.log(`[https] starting parseSSE with event-driven approach`)

  // Queue to buffer incoming chunks
  const chunks: Buffer[] = []
  let streamEnded = false
  let streamError: Error | null = null
  let resolveNext: (() => void) | null = null

  // Set up event handlers
  res.on('data', (chunk: Buffer) => {
    console.log(`[https] 'data' event: received ${chunk.length} bytes`)
    chunks.push(chunk)
    // Wake up the processing loop if it's waiting
    if (resolveNext) {
      const resolve = resolveNext
      resolveNext = null
      resolve()
    }
  })

  res.on('end', () => {
    console.log(`[https] 'end' event: stream closed cleanly by remote`)
    streamEnded = true
    // Wake up the processing loop
    if (resolveNext) {
      const resolve = resolveNext
      resolveNext = null
      resolve()
    }
  })

  res.on('error', (err: Error) => {
    console.log(`[https] 'error' event: ${err.message}`)
    streamError = err
    streamEnded = true
    // Wake up the processing loop
    if (resolveNext) {
      const resolve = resolveNext
      resolveNext = null
      resolve()
    }
  })

  res.on('close', () => {
    console.log(`[https] 'close' event: connection closed`)
  })

  // Process chunks as they arrive
  while (!streamEnded || chunks.length > 0) {
    // If error occurred, throw it
    if (streamError) {
      throw streamError
    }

    // If no chunks available and stream not ended, wait for next chunk
    if (chunks.length === 0 && !streamEnded) {
      await new Promise<void>((resolve) => {
        resolveNext = resolve
      })
      continue
    }

    // If no more chunks and stream ended, we're done
    if (chunks.length === 0 && streamEnded) {
      break
    }

    // Process the next chunk
    const chunk = chunks.shift()!
    const text = chunk.toString('utf-8')
    buffer += text

    // Split on SSE delimiter (handle \n\n and \r\n\r\n)
    const parts = buffer.split(/\r?\n\r?\n/)
    buffer = parts.pop() ?? ''

    for (const part of parts) {
      if (!part.trim()) continue

      for (const line of part.split(/\r?\n/)) {
        if (!line.startsWith('data: ')) continue

        const json = line.slice('data: '.length).trim()
        if (!json || json === '[DONE]') continue

        let envelope: { result?: A2AStreamEvent; error?: unknown }
        try {
          envelope = JSON.parse(json)
        } catch {
          continue
        }

        if (envelope.error !== undefined) {
          throw new Error(`A2A RPC error: ${JSON.stringify(envelope.error)}`)
        }

        if (envelope.result !== undefined) {
          eventCount++
          console.log(
            `[https] yielding event #${eventCount} kind=${(envelope.result as unknown as Record<string, unknown>)['kind'] ?? '?'}`,
          )
          yield envelope.result
        }
      }
    }
  }

  // Flush remainder
  if (buffer.trim()) {
    console.log(`[https] flushing final buffer: ${buffer.length} chars`)
    for (const line of buffer.split(/\r?\n/)) {
      if (!line.startsWith('data: ')) continue
      const json = line.slice('data: '.length).trim()
      if (!json) continue
      try {
        const envelope = JSON.parse(json) as {
          result?: A2AStreamEvent
          error?: unknown
        }
        if (envelope.result !== undefined) {
          eventCount++
          yield envelope.result
        }
      } catch {
        // skip
      }
    }
  }

  console.log(`[https] parseSSE complete, total events yielded: ${eventCount}`)
}
