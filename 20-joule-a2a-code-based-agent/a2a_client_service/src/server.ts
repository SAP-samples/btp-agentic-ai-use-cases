/**
 * A2A Client Service — Fastify entry point.
 *
 * Exposes two endpoints:
 *   GET  /health        – liveness probe (used by CF health check)
 *   POST /a2a/send      – proxy a message to a remote A2A server
 */

import Fastify, { type FastifyInstance } from 'fastify'
import sensible from '@fastify/sensible'
import { sendA2AMessage, streamA2AMessage } from './a2aProxy.js'

// ---------------------------------------------------------------------------
// Request / Response schemas
// ---------------------------------------------------------------------------

/**
 * Shared JSON Schema for the request body used by both /a2a/send and
 * /a2a/stream endpoints.
 */
const messageBodySchema = {
  type: 'object',
  required: ['destinationName', 'message'],
  additionalProperties: false,
  properties: {
    /** Name of the SAP BTP destination pointing to the remote A2A server. */
    destinationName: { type: 'string', minLength: 1 },
    /** Plain-text message to forward to the remote agent. */
    message: { type: 'string', minLength: 1 },
    /** Optional A2A message ID (UUID). Auto-generated when omitted. */
    messageId: { type: 'string' },
    /** Optional A2A context ID to continue an existing conversation. */
    contextId: { type: 'string' },
    /** Optional A2A task ID to associate with an existing remote task. */
    taskId: { type: 'string' },
  },
} as const

const sendMessageSchema = { body: messageBodySchema } as const
const streamMessageSchema = { body: messageBodySchema } as const

const newLine = '  \n' // for consistent newlines in status updates and task events in markdown format

// ---------------------------------------------------------------------------
// JWT extraction
// ---------------------------------------------------------------------------

/**
 * Extracts a JWT from the incoming request headers using a two-step strategy:
 *
 * 1. `Authorization: Bearer <token>` — standard OAuth2 bearer token header.
 * 2. `X-user-token: <token>` — fallback header used by SAP BTP platform
 *    services to propagate the logged-in user's JWT downstream.
 *
 * @param headers - Fastify / Node.js `IncomingHttpHeaders` map.
 * @returns The raw JWT string, or `undefined` when neither header is present.
 */
function extractJwt(headers: Record<string, string | string[] | undefined>): string | undefined {
  // Step 1: try Authorization header (Bearer scheme)
  const authHeader = headers['authorization']
  if (typeof authHeader === 'string' && authHeader.startsWith('Bearer ')) {
    return authHeader.slice('Bearer '.length).trim()
  }

  // Step 2: fallback to X-user-token (SAP BTP platform propagation header)
  const userToken = headers['x-user-token']
  if (typeof userToken === 'string' && userToken.trim().length > 0) {
    return userToken.trim()
  }

  return undefined
}

// ---------------------------------------------------------------------------
// Event normalization
// ---------------------------------------------------------------------------

interface NormalizedMessage {
  message: {
    contextId: string
    taskId: string
    messageId: string
    kind: string
    name: string
    parts: Array<{ kind: string; text: string }>
  }
}

/**
 * Transforms A2A events into a unified message format.
 *
 * @param event - Raw A2A event (Task, TaskStatusUpdateEvent, or TaskArtifactUpdateEvent)
 * @returns Normalized message or null if event type is unknown
 */
function normalizeA2AEvent(event: any): NormalizedMessage | null {
  const kind = event.kind

  if (kind === 'task') {
    // Task event: extract task state and create status message
    return {
      message: {
        contextId: event.contextId,
        taskId: event.id,
        messageId: event.id,
        kind: 'task',
        name: 'task',
        parts: [
          {
            kind: 'text',
            text: `Task ${event.status.state} to remote A2A Agent${newLine}`,
          },
        ],
      },
    }
  }

  if (kind === 'status-update') {
    // Status update event: extract agent message text
    const statusMessage = event.status?.message
    if (!statusMessage) {
      return null
    }

    const text = statusMessage.parts?.[0]?.text || ''
    return {
      message: {
        contextId: event.contextId,
        taskId: event.taskId,
        messageId: statusMessage.messageId,
        kind: 'status-update',
        name: 'status-update',
        parts: [
          {
            kind: 'text',
            text: text + newLine, // Append newline for status updates
          },
        ],
      },
    }
  }

  if (kind === 'artifact-update') {
    // Artifact update event: extract artifact content
    const artifact = event.artifact
    if (!artifact) {
      return null
    }

    const text = artifact.parts?.[0]?.text || ''
    return {
      message: {
        contextId: event.contextId,
        taskId: event.taskId,
        messageId: artifact.artifactId,
        kind: 'artifact-update',
        name: artifact.name || 'artifact',
        parts: [
          {
            kind: 'text',
            text: text, // No newline appended for artifacts
          },
        ],
      },
    }
  }

  // Unknown event type
  return null
}

// ---------------------------------------------------------------------------
// Server factory
// ---------------------------------------------------------------------------

async function buildServer(): Promise<FastifyInstance> {
  const server = Fastify({
    logger: {
      level: process.env.LOG_LEVEL ?? 'info',
    },
  })

  await server.register(sensible)

  // ── Health check ──────────────────────────────────────────────────────────
  server.get('/health', async (_req, reply) => {
    return reply.send({ status: 'ok' })
  })

  // ── A2A stream (SSE) ──────────────────────────────────────────────────────
  /**
   * Proxies a remote A2A server's streaming response back to the caller as
   * Server-Sent Events (SSE).
   *
   * Each A2A event (task creation, status update, artifact update) is forwarded
   * as a single SSE `data:` frame containing the raw JSON of the event.
   *
   * The connection stays open until the remote stream finishes or an error
   * occurs.  Clients should consume the stream with `EventSource` or any
   * fetch-based SSE reader.
   *
   * Example frame sequence:
   *   data: {"kind":"task","id":"…","status":{"state":"submitted"}}\n\n
   *   data: {"kind":"status-update","taskId":"…","status":{"state":"working"},"final":false}\n\n
   *   data: {"kind":"artifact-update","taskId":"…","artifact":{…}}\n\n
   *   data: {"kind":"status-update","taskId":"…","status":{"state":"completed"},"final":true}\n\n
   */
  server.post<{
    Body: {
      destinationName: string
      message: string
      messageId?: string
      contextId?: string
      taskId?: string
    }
  }>('/a2a/stream', { schema: streamMessageSchema }, async (request, reply) => {
    const { destinationName, message, messageId, contextId, taskId } =
      request.body

    const jwt = extractJwt(
      request.headers as Record<string, string | string[] | undefined>,
    )

    // Hijack the response: Fastify will no longer attempt to serialise or send
    // a response body, giving us full control over reply.raw.
    reply.hijack()

    // Set SSE response headers before writing any data.
    reply.raw.statusCode = 200
    reply.raw.setHeader('Content-Type', 'text/event-stream; charset=utf-8')
    reply.raw.setHeader('Cache-Control', 'no-cache, no-transform')
    reply.raw.setHeader('Connection', 'keep-alive')
    // Disable proxy / nginx buffering so events reach the client immediately.
    reply.raw.setHeader('X-Accel-Buffering', 'no')
    reply.raw.flushHeaders()

    // Detect early client disconnect so we can stop reading the upstream stream.
    let clientGone = false
    request.raw.on('close', () => {
      clientGone = true
    })

    try {
      const gen = streamA2AMessage(destinationName, message, {
        messageId,
        contextId,
        taskId,
        jwt,
      })

      let eventsSent = 0
      for await (const event of gen) {
        eventsSent++
        server.log.info(`[server] writing SSE event #${eventsSent}`)

        // Write the event - will throw EPIPE if client disconnected
        reply.raw.write(`data: ${JSON.stringify(event)}\n\n`)

        server.log.info(`[server] SSE event #${eventsSent} written, awaiting next event`)
      }
      server.log.info(`[server] generator exhausted, sent ${eventsSent} events total`)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err)
      server.log.error({ err }, 'A2A stream error')

      // Write a terminal error event so the client knows the stream failed.
      if (!clientGone) {
        reply.raw.write(
          `data: ${JSON.stringify({ error: msg })}\n\n`,
        )
      }
    } finally {
      reply.raw.end()
    }

    // Do NOT return anything — reply.hijack() means Fastify is out of the picture.
  })

  // ── A2A stream normalised (SSE) ───────────────────────────────────────────
  /**
   * Proxies a remote A2A server's streaming response with normalized message format.
   *
   * Transforms all A2A events (task, status-update, artifact-update) into a unified
   * message structure for consistent client consumption.
   *
   * Normalized format:
   *   {
   *     "message": {
   *       "contextId": string,
   *       "taskId": string,
   *       "messageId": string,
   *       "kind": "task" | "status-update" | "artifact-update",
   *       "name": string,
   *       "parts": [{"kind": "text", "text": string}]
   *     }
   *   }
   */
  server.post<{
    Body: {
      destinationName: string
      message: string
      messageId?: string
      contextId?: string
      taskId?: string
    }
  }>('/a2a/stream_normalised', { schema: streamMessageSchema }, async (request, reply) => {
    const { destinationName, message, messageId, contextId, taskId } =
      request.body

    const jwt = extractJwt(
      request.headers as Record<string, string | string[] | undefined>,
    )

    reply.hijack()

    reply.raw.statusCode = 200
    reply.raw.setHeader('Content-Type', 'text/event-stream; charset=utf-8')
    reply.raw.setHeader('Cache-Control', 'no-cache, no-transform')
    reply.raw.setHeader('Connection', 'keep-alive')
    reply.raw.setHeader('X-Accel-Buffering', 'no')
    reply.raw.flushHeaders()

    let clientGone = false
    request.raw.on('close', () => {
      clientGone = true
    })

    try {
      const gen = streamA2AMessage(destinationName, message, {
        messageId,
        contextId,
        taskId,
        jwt,
      })

      let eventsSent = 0
      for await (const event of gen) {
        eventsSent++
        server.log.info(`[server] normalizing and writing SSE event #${eventsSent}`)

        // Transform A2A event to normalized message format
        const normalized = normalizeA2AEvent(event)

        if (normalized) {
          reply.raw.write(`data: ${JSON.stringify(normalized)}\n\n`)
          server.log.info(`[server] normalized event #${eventsSent} written`)
        } else {
          server.log.warn(`[server] skipped unknown event type: ${(event as any).kind}`)
        }
      }
      server.log.info(`[server] normalized stream complete, sent ${eventsSent} events`)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err)
      server.log.error({ err }, 'A2A normalized stream error')

      if (!clientGone) {
        reply.raw.write(
          `data: ${JSON.stringify({ error: msg })}\n\n`,
        )
      }
    } finally {
      reply.raw.end()
    }
  })

  // ── A2A send ──────────────────────────────────────────────────────────────
  server.post<{
    Body: {
      destinationName: string
      message: string
      messageId?: string
      contextId?: string
      taskId?: string
    }
  }>('/a2a/send', { schema: sendMessageSchema }, async (request, reply) => {
    const { destinationName, message, messageId, contextId, taskId } =
      request.body

    // Extract JWT for OAuth2JWTBearer destination support:
    // prefer Authorization: Bearer, then fall back to X-user-token.
    const jwt = extractJwt(request.headers as Record<string, string | string[] | undefined>)

    try {
      const a2aResponse = await sendA2AMessage(destinationName, message, {
        messageId,
        contextId,
        taskId,
        jwt,
      })

      return reply.send(a2aResponse)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err)

      // Destination not found / mis-configured → 400 Bad Request
      if (
        msg.includes('not found') ||
        msg.includes('inaccessible') ||
        msg.includes('no URL')
      ) {
        return reply.badRequest(msg)
      }

      // Remote A2A server unreachable / returned an error → 502 Bad Gateway
      server.log.error({ err }, 'A2A proxy error')
      return reply.code(502).send({
        error: 'Bad Gateway',
        message: `Remote A2A server error: ${msg}`,
      })
    }
  })

  return server
}

// ---------------------------------------------------------------------------
// Start
// ---------------------------------------------------------------------------

const port = parseInt(process.env.PORT ?? '3000', 10)
const host = process.env.HOST ?? '0.0.0.0'

buildServer()
  .then((server) =>
    server.listen({ port, host }, (err) => {
      if (err) {
        server.log.error(err)
        process.exit(1)
      }
    }),
  )
  .catch((err: unknown) => {
    console.error('Failed to start server:', err)
    process.exit(1)
  })
