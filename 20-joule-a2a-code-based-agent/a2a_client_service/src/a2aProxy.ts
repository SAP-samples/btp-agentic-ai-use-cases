/**
 * A2A client proxy.
 *
 * Builds an authenticated A2A client pointing at a remote server whose URL
 * and credentials come from an SAP BTP destination, then forwards a message
 * and returns the raw A2A response (Message or Task).
 *
 * Authentication headers are injected via the SDK's AuthenticationHandler /
 * createAuthenticatingFetchWithRetry utility so the approach is
 * transport-agnostic and supports token refresh on 401.
 */

import {
  ClientFactory,
  ClientFactoryOptions,
  JsonRpcTransportFactory,
  createAuthenticatingFetchWithRetry,
  type AuthenticationHandler,
} from '@a2a-js/sdk/client'
import type {
  MessageSendParams,
  Message,
  Task,
  TaskStatusUpdateEvent,
  TaskArtifactUpdateEvent,
} from '@a2a-js/sdk'
import { v4 as uuidv4 } from 'uuid'
import { resolveDestination } from './destinationAuth.js'
import { streamViaHttps } from './a2aProxyHttps.js'

export interface SendMessageOptions {
  /** Optional A2A message ID (auto-generated when omitted). */
  messageId?: string
  /** Optional A2A context ID to continue an existing conversation. */
  contextId?: string
  /**
   * Optional A2A task ID to associate the message with an existing task on
   * the remote server.
   */
  taskId?: string
  /**
   * JWT of the calling user — forwarded to the BTP Destination Service for
   * OAuth2JWTBearer token exchange.
   */
  jwt?: string
}

// ---------------------------------------------------------------------------
// Shared auth-factory helper
// ---------------------------------------------------------------------------

/**
 * Builds an authenticated fetch wrapper + ClientFactory from a resolved
 * BTP destination.  Centralises the auth setup used by both `sendA2AMessage`
 * and `streamA2AMessage`.
 */
async function buildAuthFactory(destinationName: string, jwt?: string): Promise<{
  baseUrl: string
  authFetch: typeof fetch
  factory: InstanceType<typeof ClientFactory>
}> {
  const { baseUrl, authHeaders } = await resolveDestination(destinationName, jwt)

  const authHandler: AuthenticationHandler = {
    headers: async () => authHeaders,
    shouldRetryWithHeaders: async (_req: RequestInit, res: Response) => {
      if (res.status === 401) {
        const refreshed = await resolveDestination(destinationName, jwt)
        return refreshed.authHeaders
      }
      return undefined
    },
  }

  const authFetch = createAuthenticatingFetchWithRetry(
    fetch as typeof fetch,
    authHandler,
  ) as typeof fetch

  const factory = new ClientFactory(
    ClientFactoryOptions.createFrom(ClientFactoryOptions.default, {
      transports: [new JsonRpcTransportFactory({ fetchImpl: authFetch })],
    }),
  )

  return { baseUrl, authFetch, factory }
}

// ---------------------------------------------------------------------------
// Non-streaming send
// ---------------------------------------------------------------------------

/**
 * Sends a plain-text message to a remote A2A server identified by a BTP
 * destination name and returns the raw A2A response.
 *
 * @param destinationName - SAP BTP destination name.
 * @param messageText - Text content of the message to send.
 * @param options - Optional message identifiers and caller JWT.
 * @returns Raw A2A response — either a `Message` or a `Task` object.
 */
export async function sendA2AMessage(
  destinationName: string,
  messageText: string,
  options: SendMessageOptions = {},
): Promise<Message | Task> {
  const { messageId, contextId, taskId, jwt } = options

  const { baseUrl, factory } = await buildAuthFactory(destinationName, jwt)

  const client = await factory.createFromUrl(baseUrl)

  const sendParams: MessageSendParams = {
    message: {
      messageId: messageId ?? uuidv4(),
      role: 'user',
      parts: [{ kind: 'text', text: messageText }],
      kind: 'message',
      ...(contextId !== undefined ? { contextId } : {}),
    },
    ...(taskId !== undefined
      ? { configuration: { relatedTaskId: taskId } as Record<string, unknown> }
      : {}),
  }

  return (await client.sendMessage(sendParams)) as Message | Task
}

// ---------------------------------------------------------------------------
// Streaming
// ---------------------------------------------------------------------------

/**
 * Union of all event types that a remote A2A server can emit during streaming.
 * Mirrors the SDK's internal `A2AStreamEventData` type.
 */
export type A2AStreamEvent =
  | Message
  | Task
  | TaskStatusUpdateEvent
  | TaskArtifactUpdateEvent

/**
 * Streams events from a remote A2A server identified by a BTP destination name.
 *
 * Reuses the same auth setup as `sendA2AMessage`, discovers the JSON-RPC
 * endpoint via `A2AClient.getAgentCard()` (the same path that makes
 * `sendMessage` work), then POSTs a `message/stream` JSON-RPC request with
 * `Accept: text/event-stream` and yields each `result` from the SSE frames.
 *
 * @param destinationName - SAP BTP destination name.
 * @param messageText - Text content of the message to send.
 * @param options - Optional message identifiers and caller JWT.
 * @yields Raw A2A stream events — `Message`, `Task`, `TaskStatusUpdateEvent`,
 *   or `TaskArtifactUpdateEvent`.
 */
export async function* streamA2AMessage(
  destinationName: string,
  messageText: string,
  options: SendMessageOptions = {},
): AsyncGenerator<A2AStreamEvent, void, undefined> {
  const { messageId, contextId, taskId, jwt } = options

  // 1. Build auth + factory (same as sendA2AMessage).
  const { baseUrl, authFetch, factory } = await buildAuthFactory(
    destinationName,
    jwt,
  )

  // 2. Create client and discover the confirmed-working RPC endpoint via
  //    getAgentCard() — this is the exact URL that sendMessage uses.
  const client = await factory.createFromUrl(baseUrl)
  const agentCard = await client.getAgentCard()
  const rpcEndpoint: string = agentCard.url ?? baseUrl

  console.log(`[stream] rpcEndpoint=${rpcEndpoint}`)

  // 3. Build the A2A JSON-RPC streaming request body.
  const requestBody = {
    jsonrpc: '2.0',
    id: uuidv4(),
    method: 'message/stream',
    params: {
      message: {
        messageId: messageId ?? uuidv4(),
        role: 'user',
        parts: [{ kind: 'text', text: messageText }],
        kind: 'message',
        ...(contextId !== undefined ? { contextId } : {}),
      },
      ...(taskId !== undefined
        ? { configuration: { relatedTaskId: taskId } }
        : {}),
    },
  }

  // 4. Get auth headers for the HTTPS request (resolve them from authHandler)
  const { authHeaders } = await resolveDestination(destinationName, jwt)

  // 5. Use Node.js's https.request for reliable SSE streaming.
  //    (fetch/undici hangs after first chunk; https streams properly)
  yield* streamViaHttps({ rpcEndpoint, authHeaders, requestBody })
}
