/**
 * A2A Client Service — Fastify entry point.
 *
 * Exposes two endpoints:
 *   GET  /health        – liveness probe (used by CF health check)
 *   POST /a2a/send      – proxy a message to a remote A2A server
 */

import Fastify, { type FastifyInstance } from 'fastify'
import sensible from '@fastify/sensible'
import { sendA2AMessage } from './a2aProxy.js' // relative import to avoid ESM / CJS issues in CF

// ---------------------------------------------------------------------------
// Request / Response schemas
// ---------------------------------------------------------------------------

const sendMessageSchema = {
  body: {
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
  },
} as const

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
