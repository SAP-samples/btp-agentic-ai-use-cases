/**
 * Test client for a2a-client-service.
 *
 * Exercises both endpoints:
 *   POST /a2a/send   — blocking JSON response
 *   POST /a2a/stream — Server-Sent Events stream
 *
 * Usage:
 *   npx tsx src/test_client.ts
 *
 * Configure via environment variables:
 *   SERVICE_URL        Base URL of the running service   (default: http://localhost:3000)
 *   DESTINATION_NAME   SAP BTP destination name          (required)
 *   MESSAGE            Message text to send              (default: "Hello, agent!")
 *   BEARER_TOKEN       Bearer JWT for OAuth2JWTBearer    (optional)
 */

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------

const SERVICE_URL = (process.env.SERVICE_URL ?? 'http://localhost:3000').replace(/\/$/, '')
const DESTINATION_NAME = process.env.DESTINATION_NAME ?? 'deep-research-agent-a2a'
const MESSAGE = process.env.MESSAGE ?? 'Research use cases of SAP RPT-1'
const BEARER_TOKEN = process.env.BEARER_TOKEN

if (!DESTINATION_NAME) {
  console.error('❌  DESTINATION_NAME environment variable is required.')
  console.error('   Example: DESTINATION_NAME=MY_A2A_DEST npx tsx src/test_client.ts')
  process.exit(1)
}

const commonHeaders: Record<string, string> = {
  'Content-Type': 'application/json',
  ...(BEARER_TOKEN ? { Authorization: `Bearer ${BEARER_TOKEN}` } : {}),
}

const requestBody = {
  destinationName: DESTINATION_NAME,
  message: MESSAGE,
}

// ---------------------------------------------------------------------------
// Helper: parse SSE text chunk into individual data payloads
// ---------------------------------------------------------------------------

function parseSseChunk(chunk: string): unknown[] {
  const events: unknown[] = []
  // Each SSE event ends with \n\n; individual lines start with "data: "
  for (const line of chunk.split('\n')) {
    const trimmed = line.trim()
    if (trimmed.startsWith('data: ')) {
      const json = trimmed.slice('data: '.length)
      try {
        events.push(JSON.parse(json))
      } catch {
        // partial chunk — will be completed in next read cycle
        events.push({ raw: json })
      }
    }
  }
  return events
}

// ---------------------------------------------------------------------------
// Test 1: POST /a2a/send  (blocking)
// ---------------------------------------------------------------------------

async function testSend(): Promise<void> {
  console.log('\n━━━ POST /a2a/send ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
  console.log(`→  destination : ${DESTINATION_NAME}`)
  console.log(`→  message     : ${MESSAGE}`)

  const resp = await fetch(`${SERVICE_URL}/a2a/send`, {
    method: 'POST',
    headers: commonHeaders,
    body: JSON.stringify(requestBody),
  })

  const body: unknown = await resp.json()

  if (!resp.ok) {
    console.error(`✗  HTTP ${resp.status}`)
    console.error(JSON.stringify(body, null, 2))
    return
  }

  console.log(`✓  HTTP ${resp.status}`)
  console.log(JSON.stringify(body, null, 2))
}

// ---------------------------------------------------------------------------
// Test 2: POST /a2a/stream  (SSE)
// ---------------------------------------------------------------------------

async function testStream(): Promise<void> {
  console.log('\n━━━ POST /a2a/stream ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
  console.log(`→  destination : ${DESTINATION_NAME}`)
  console.log(`→  message     : ${MESSAGE}`)

  const resp = await fetch(`${SERVICE_URL}/a2a/stream`, {
    method: 'POST',
    headers: commonHeaders,
    body: JSON.stringify(requestBody),
  })

  if (!resp.ok) {
    const errBody: unknown = await resp.json().catch(() => ({}))
    console.error(`✗  HTTP ${resp.status}`)
    console.error(JSON.stringify(errBody, null, 2))
    return
  }

  console.log(`✓  HTTP ${resp.status}  (${resp.headers.get('content-type')})`)
  console.log('   Streaming events:')

  if (!resp.body) {
    console.error('   ✗  Response body is null — streaming not supported by this runtime.')
    return
  }

  const reader = resp.body.getReader()
  const decoder = new TextDecoder()
  let eventIndex = 0
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })

    // Process complete SSE events (terminated by \n\n)
    const parts = buffer.split('\n\n')
    // Keep the last (potentially incomplete) part in the buffer
    buffer = parts.pop() ?? ''

    for (const part of parts) {
      const trimmed = part.trim()
      if (!trimmed) continue

      if (trimmed.startsWith('data: ')) {
        const json = trimmed.slice('data: '.length)
        try {
          const event = JSON.parse(json) as Record<string, unknown>
          eventIndex++
          const kind = event['kind'] ?? (event['error'] ? 'error' : '?')
          console.log(`   [${eventIndex}] kind=${kind}`)
          console.log('       ' + JSON.stringify(event, null, 2).replace(/\n/g, '\n       '))
        } catch {
          console.log(`   [raw] ${trimmed}`)
        }
      }
    }
  }

  // Flush any remaining buffer content
  if (buffer.trim()) {
    for (const event of parseSseChunk(buffer)) {
      eventIndex++
      console.log(`   [${eventIndex}] ${JSON.stringify(event)}`)
    }
  }

  console.log(`\n   ── stream ended (${eventIndex} event${eventIndex === 1 ? '' : 's'}) ──`)
}

// ---------------------------------------------------------------------------
// Health check
// ---------------------------------------------------------------------------

async function checkHealth(): Promise<boolean> {
  try {
    const resp = await fetch(`${SERVICE_URL}/health`)
    if (resp.ok) {
      console.log(`✓  ${SERVICE_URL}/health → OK`)
      return true
    }
    console.error(`✗  /health returned HTTP ${resp.status}`)
    return false
  } catch (err) {
    console.error(`✗  Could not reach ${SERVICE_URL} — is the service running?`)
    console.error(`   ${err instanceof Error ? err.message : String(err)}`)
    return false
  }
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

console.log('━━━ a2a-client-service test client ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
console.log(`   service : ${SERVICE_URL}`)

const healthy = await checkHealth()
if (!healthy) process.exit(1)

//await testSend()
await testStream()

console.log('\n━━━ done ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n')
