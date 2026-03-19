/**
 * SAP BTP Destination Service integration.
 *
 * Fetches a named destination from the BTP Destination Service and builds
 * the appropriate HTTP authorisation headers for its authentication type:
 *
 * - BasicAuthentication          → Authorization: Basic <base64(user:pass)>
 * - OAuth2ClientCredentials      → fetches token, Authorization: Bearer <token>
 * - OAuth2JWTBearer              → exchanges caller JWT, Authorization: Bearer <token>
 *
 * In Cloud Foundry the SDK reads VCAP_SERVICES automatically.
 * For local development provide a `default-env.json` file (see README).
 */

import {
  getDestination,
  buildHeadersForDestination,
  type Destination,
} from '@sap-cloud-sdk/connectivity'

export interface DestinationInfo {
  /** Base URL of the remote A2A server extracted from the destination. */
  baseUrl: string
  /** Ready-to-use Authorization (and other) headers for the destination. */
  authHeaders: Record<string, string>
}

/**
 * Resolves a BTP destination by name and returns its base URL together with
 * the fully-built authentication headers.
 *
 * @param destinationName - Name of the SAP BTP destination.
 * @param jwt - Optional JWT of the calling user; required for OAuth2JWTBearer.
 * @returns Destination base URL and authentication headers.
 * @throws Error when the destination cannot be found or the URL is missing.
 */
export async function resolveDestination(
  destinationName: string,
  jwt?: string,
): Promise<DestinationInfo> {
  const destination: Destination | null = await getDestination({
    destinationName,
    ...(jwt ? { jwt } : {}),
    useCache: false, // stateless — always fetch fresh credentials
  })

  if (!destination) {
    throw new Error(`BTP destination '${destinationName}' not found or inaccessible.`)
  }

  const rawUrl: string | undefined =
    destination.url ??
    (destination.originalProperties?.['URL'] as string | undefined)

  if (!rawUrl) {
    throw new Error(
      `BTP destination '${destinationName}' has no URL configured.`,
    )
  }

  // Normalise: strip trailing slash so A2A SDK path joining works correctly.
  const baseUrl = rawUrl.replace(/\/$/, '')

  // buildHeadersForDestination handles all supported auth types and returns
  // a plain object whose keys are HTTP header names.
  const rawHeaders = await buildHeadersForDestination(destination)
  const authHeaders: Record<string, string> = Object.fromEntries(
    Object.entries(rawHeaders).map(([k, v]) => [k, String(v)]),
  )

  return { baseUrl, authHeaders }
}
