# A2A Client Service

A stateless **Fastify** REST proxy that routes messages to any remote [A2A](https://google-a2a.github.io/A2A) server on the fly. The target server URL and authentication credentials are resolved at request time from a named **SAP BTP Destination Service** entry, so no credentials are ever hard-coded in the service.

## Architecture

```
┌──────────────────────────────────────┐
│         API Client / Agent           │
│  POST /a2a/send  { destinationName,  │
│                    message, … }      │
└───────────────┬──────────────────────┘
                │  HTTP / JSON
                ▼
┌──────────────────────────────────────┐
│       a2a-client-service (Fastify)   │  src/server.ts
│                                      │
│  POST /a2a/send                      │
│  GET  /health                        │
└──────────┬───────────────────────────┘
           │
           ▼
┌──────────────────────────────────────┐
│   SAP BTP Destination Service        │  src/destinationAuth.ts
│   (@sap-cloud-sdk/connectivity)      │
│                                      │
│   BasicAuthentication                │
│   OAuth2ClientCredentials            │
│   OAuth2JWTBearer                    │
└──────────┬───────────────────────────┘
           │  base URL + auth headers
           ▼
┌──────────────────────────────────────┐
│   A2A Client (@a2a-js/sdk/client)    │  src/a2aProxy.ts
│   ClientFactory + authFetch          │
│                                      │
│   → remote A2A server                │
└──────────────────────────────────────┘
```

## API

### `GET /health`

Liveness probe. Returns `200 OK` — used by CF health checks.

```json
{ "status": "ok" }
```

### `POST /a2a/send`

Proxy a message to a remote A2A server identified by a BTP destination.

**Request body**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `destinationName` | `string` | ✅ | Name of the SAP BTP destination |
| `message` | `string` | ✅ | Plain-text message to send to the remote agent |
| `messageId` | `string` | ❌ | A2A message ID (auto-generated UUID when omitted) |
| `contextId` | `string` | ❌ | A2A context ID to continue an existing conversation |
| `taskId` | `string` | ❌ | A2A task ID to associate with an existing remote task |

**JWT propagation for OAuth2JWTBearer destinations**

The service extracts the caller's JWT using the following priority:

1. `Authorization: Bearer <token>` — standard OAuth2 bearer header.
2. `X-user-token: <token>` — SAP BTP platform propagation header (fallback).

The JWT is forwarded to the BTP Destination Service, which exchanges it for an outbound token for `OAuth2JWTBearer`-typed destinations.

**Response**

Raw A2A response — either a [`Message`](https://google-a2a.github.io/A2A) or [`Task`](https://google-a2a.github.io/A2A) JSON object returned by the remote server.

**Example**

```bash
curl -X POST http://localhost:3000/a2a/send \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-jwt>" \
  -d '{
    "destinationName": "MY_A2A_SERVER_DEST",
    "message": "What is the weather in Berlin today?",
    "contextId": "session-abc-123"
  }'
```

## Supported Authentication Types

Authentication is handled automatically by the SAP Cloud SDK based on the destination configuration:

| Destination Auth Type | Mechanism |
|---|---|
| `BasicAuthentication` | `Authorization: Basic base64(user:password)` |
| `OAuth2ClientCredentials` | Fetches a client-credentials token from the token service URL |
| `OAuth2JWTBearer` | Exchanges the caller's JWT for an outbound access token |

## Local Development

### Prerequisites

- Node.js ≥ 20
- SAP BTP subaccount with a configured Destination Service instance
- A named destination pointing to your remote A2A server

### 1. Install dependencies

```bash
cd examples/a2a_client_service
npm install
```

### 2. Configure environment

```bash
cp .env.example .env
```

Create a `default-env.json` in the project root with your Destination Service credentials (see `.env.example` for instructions). The SAP Cloud SDK picks this file up automatically in non-production environments.

```json
{
  "VCAP_SERVICES": {
    "destination": [{
      "name": "destination-service",
      "credentials": {
        "clientid": "...",
        "clientsecret": "...",
        "uri": "https://destination-configuration.cfapps.<region>.hana.ondemand.com",
        "url": "https://<subaccount>.authentication.<region>.hana.ondemand.com"
      }
    }]
  }
}
```

### 3. Start the dev server

```bash
npm run dev
```

The server starts at `http://localhost:3000`.

### 4. Send a test message

```bash
curl -X POST http://localhost:3000/a2a/send \
  -H "Content-Type: application/json" \
  -d '{
    "destinationName": "MY_A2A_SERVER_DEST",
    "message": "Hello, remote agent!"
  }'
```

## Cloud Foundry Deployment

### 1. Build the project

```bash
npm run build
```

### 2. Copy and Configure `manifest.yaml`
```bash
cp  manifest.template manifest.yaml
```

Edit `manifest.yaml` and replace:
- `<YOUR_APP_NAME>` — your CF application name
- `<YOUR_DOMAIN>` — your CF / BTP domain (e.g. `cfapps.eu10.hana.ondemand.com`)

Ensure a Destination Service instance named `a2a-destination-service` exists in your CF space:

```bash
cf create-service destination lite a2a-destination-service
```

If your destinations use `OAuth2JWTBearer`, also bind an XSUAA instance (uncomment the line in `manifest.yaml`).

### 3. Deploy

```bash
cf push
```

## Key Files

| File | Purpose |
|------|---------|
| `src/server.ts` | Fastify server — endpoints, JWT extraction, error handling |
| `src/a2aProxy.ts` | A2A `ClientFactory` with auth-injected `fetch` |
| `src/destinationAuth.ts` | BTP destination resolution + `buildHeadersForDestination` |
| `manifest.template.yaml` | Cloud Foundry deployment manifest template |
| `.env.example` | Local development environment template |
