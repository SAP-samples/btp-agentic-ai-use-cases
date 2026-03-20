# A2A Client Service

A stateless **Fastify** REST proxy that routes messages to any remote [A2A](https://google-a2a.github.io/A2A) server on the fly. The target server URL and authentication credentials are resolved at request time from a named **SAP BTP Destination Service** entry, so no credentials are ever hard-coded in the service.

## Architecture

```
┌──────────────────────────────────────┐
│         API Client / Agent           │
│  POST /a2a/send  { destinationName,  │
│                    message, … }      │
└──────────────────┬───────────────────┘
                   │  HTTP / JSON
                   ▼
┌──────────────────────────────────────┐
│       a2a-client-service (Fastify)   │  src/server.ts
│                                      │
│  POST /a2a/send                      │
│  GET  /health                        │
└──────────────────┬───────────────────┘
                   │
                   ▼
┌──────────────────────────────────────┐
│   SAP BTP Destination Service        │  src/destinationAuth.ts
│   (@sap-cloud-sdk/connectivity)      │
│                                      │
│   BasicAuthentication                │
│   OAuth2ClientCredentials            │
│   OAuth2JWTBearer                    │
└──────────────────┬───────────────────┘
                   │  Auth
                   ▼
┌──────────────────────────────────────┐
│   A2A Client (@a2a-js/sdk/client)    │  src/a2aProxy.ts
│   ClientFactory + authFetch          │
│                                      │
│                                      │
└──────────────────┬───────────────────┘
                   │  A2A
                   ▼
┌──────────────────────────────────────┐
│         Remote A2A Server            │
│                                      │
│                                      │
│                                      │
└──────────────────────────────────────┘
```

## Key Files

| File | Purpose |
|------|---------|
| `src/server.ts` | Fastify server — endpoints, JWT extraction, error handling |
| `src/a2aProxy.ts` | A2A `ClientFactory` with auth-injected `fetch` |
| `src/destinationAuth.ts` | BTP destination resolution + `buildHeadersForDestination` |
| `manifest.yaml` | Cloud Foundry deployment manifest |
| `.env.example` | Local development environment template |

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
    "contextId": "session-abc-123",
    "tasktId": "task-abc-123"
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
cd a2a_client_service
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

Note down the deployment URL.

## Integrating a remote A2A Agent with Joule Studio via a2a-client-service

In this section, we'll integrate a remote A2A agent with Joule Studio through a custom Joule Skill leveraging the a2a-client-service, literally, it should be applicable to any A2A-compliant AI agent.

Let's take [deep-research-agent-a2a](../deep_research_a2a/) agent as the remote A2A agent.

### 1. Create a destination for the remote A2A agent

In your SAP BTP Sub Account where a2a-client-service is deployed, create a destination named `deep-research-agent-a2a` for the deep research agent deployed in Cloud Foundry, which will be used in a custom Joule Skill with Joule Studio
![destination](../resources/deep_research_a2a_destination.png) for integration with Joule.

#### 2. Create an Action Project for the a2a-client-service's REST APIs

![Action Project for a2a-client API](resources/a2a-client-service-action.png)
As the APIs are REST format, therefore you will need to create the action from scratch.

##### Action 1: Send Message via A2A

| Properties | Values |
| ------ | --------- |
| Name | Send Message via A2A |
| Http Method | POST |
| Endpoint | /a2a/send |
| Description | Proxy a message to a remote A2A server identified by a BTP destination |
| Input Body | sample json `{ "destinationName": "MY_A2A_SERVER_DEST", "message": "Research Joule Agent Integrate with Code-based Agent with A2A","contextId": "session-abc-123", "tasktId": "task-abc-123"}` |
| Output Body | A2A response from remote A2A Agent. Test the action and generate the output |

Make sure you have tested the actions with the destination deep-research-agent-a2a created in step 1. Once it all works as required, then release and publish the Action project

#### 2. Create a Skill to trigger the action Send Message A2A

![Research Skill](resources/research-skill-a2a-client.png)

**General**

| Properties | Values |
| ------ | --------- |
| Name | Research |
| Description | A skill to conduct research with a given query |
| Allow Joule to generate a response| Checked |
| Allow skill to be started directly by user | Checked |

**Skill Inputs**

| Properties | Values |
| ------ | --------- |
| Name | User Input |
| Description | User input |
| Type | String |
| Required | Checked |
| List | Unchecked |

**Skill Outputs**

| Properties | Values |
| ------ | --------- |
| Name | result of Send Message via A2A action |

**Send Message via A2A**
Create a destination variable as `a2a-client-service-dest`
![send-message-action](resources/send-message-action.png)

| Properties | Values |
| ------ | --------- |
| destinationName | `deep-research-agent-a2a` |
| message | `User Input` from skill input |

![send-message-action-inputs](resources/send-message-action-inputs.png)
#### 3. Test the skill

Once the joule client is launched, you can enter a research task like:<br/>
`Research use cases for SAP RPT-1`<br/>
`Research joule agent integration with A2A`<br/>
...<br/>

Simultaneously, open a terminal to stream the logs of your deep_research_a2a application

```sh
# stream the logs of your deep_research_a2a application
cf logs <your-deep-research-agent-a2a>
```

![Testing Research Skill](resources/research-skill-test.png)

#### 4. Deploy the skill

If the test works well, you can release and deploy the skill to a standalone env.

### 3. Known limitation

As highlighted in [the official help centre of about Action quota in Joule Studio here](https://help.sap.com/docs/Joule_Studio/45f9d2b8914b4f0ba731570ff9a85313/e29bb9c5fb1841b2b61f59b874ca0edd.html?locale=en-US)

* Connection timeout: 1 min
* Socket timeout: 3 mins
* Total execution time: 4 mins

Alternatively, you can have a long-running (>3 mins) A2A agent to be integrated with Joule through [this approach](../deep_research_api/README.md) of **asynchronous communication**.
