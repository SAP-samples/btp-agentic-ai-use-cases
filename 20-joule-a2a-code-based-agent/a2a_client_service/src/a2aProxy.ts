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
import type { MessageSendParams, Message, Task } from '@a2a-js/sdk'
import { v4 as uuidv4 } from 'uuid'
import { resolveDestination } from './destinationAuth.js'

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

  // 1. Resolve destination: get base URL + auth headers from SAP BTP.
  const { baseUrl, authHeaders } = await resolveDestination(destinationName, jwt)

  // 2. Build an AuthenticationHandler that injects destination credentials.
  //    On 401 we re-fetch the destination to get fresh tokens and retry once.
  const authHandler: AuthenticationHandler = {
    headers: async () => authHeaders,

    shouldRetryWithHeaders: async (_req: RequestInit, res: Response) => {
      if (res.status === 401) {
        // Destination credentials may have expired — re-fetch and retry.
        const refreshed = await resolveDestination(destinationName, jwt)
        return refreshed.authHeaders
      }
      return undefined
    },
  }

  // 3. Create an authenticated fetch wrapper and wire it into the transport.
  const authFetch = createAuthenticatingFetchWithRetry(
    fetch as typeof fetch,
    authHandler,
  )

  const factory = new ClientFactory(
    ClientFactoryOptions.createFrom(ClientFactoryOptions.default, {
      transports: [new JsonRpcTransportFactory({ fetchImpl: authFetch })],
    }),
  )

  // 4. Discover the remote agent card and create a typed A2A client.
  const client = await factory.createFromUrl(baseUrl)

  // 5. Build send parameters.
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

  // 6. Send and return the raw A2A response.
  return (await client.sendMessage(sendParams)) as Message | Task
}
