# Deep Research Agent REST API

A sample [deep research agent](../deep_research/) built with the **deepagents SDK** and exposed as a
**FastAPI REST service**. Any application or agent can trigger deep research by calling the API.

The agent uses **SAP Generative AI Hub** through *SAP Cloud SDK for AI* for LLM access and
**Tavily** for web search.

## Architecture

```
┌─────────────────────────────────────┐
│        API Client / Agent           │
│  (any HTTP client)                  │
└───────────────┬─────────────────────┘
                │  HTTP  (REST / JSON)
                ▼
┌─────────────────────────────────────┐
│         FastAPI Application         │  app.py
│                                     │
│  POST /research          (sync)     │
│  POST /research/jobs     (async)    │
│  GET  /research/jobs/:id (poll)     │
└───────────────┬─────────────────────┘
                │
                ▼
┌──────────────────────────────────────┐
│         DeepResearchAgent            │  agent.py
│  create_deep_agent via deepagents SDK│
│  and SAP Cloud SDK for AI            │
│                                      │
│  Orchestrator ──delegates─► Sub-agent│
│  (plan, synthesise, report) (search) │
└──────────────────────────────────────┘
```

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/research` | **Synchronous** — runs research and returns the completed report. Blocks until done (typically several minutes). |
| `POST` | `/research/jobs` | **Asynchronous** — submits a research job, returns a `job_id` immediately (HTTP 202). |
| `GET` | `/research/jobs/{job_id}` | Poll job status (`running` / `completed` / `failed`) and retrieve the result. |

### Request body (both `POST` endpoints)

```json
{ "query": "Research the latest advances in AI agent frameworks" }
```

### Synchronous response

```json
{
  "query": "Research the latest advances in AI agent frameworks",
  "result": "# Research Report\n...",
  "status": "completed"
}
```

### Async job submission response (HTTP 202)

```json
{
  "job_id": "3f4a1b2c-...",
  "query": "Research the latest advances in AI agent frameworks",
  "status": "running"
}
```

### Job status / result response

```json
{
  "job_id": "3f4a1b2c-...",
  "query": "Research the latest advances in AI agent frameworks",
  "status": "completed",
  "result": "# Research Report\n...",
  "error": null
}
```

### Key files

| File | Purpose |
|------|---------|
| `app/agent.py` | `DeepResearchAgent` — builds the LangGraph multi-agent pipeline and exposes `stream()` and `run()` methods |
| `app/app.py` | FastAPI application with sync and async research endpoints |
| `app/manifest.yaml` | Cloud Foundry deployment manifest |
| `app/research_agent/` | Prompt templates and Tavily search tools |

## Prerequisites

- Python 3.11+
- Install [uv](https://docs.astral.sh/uv/) package manager
- An SAP AI Core instance with Generative AI Hub. by default, `gpt-4o-mini` model is used.
- [Tavily](https://tavily.com) API key (free tier available)

## Local development

### 1. Install dependencies

```sh
cd 20-joule-a2a-code-based-agent/deep_research_api

# create a virtual env for 20-joule-a2a-code-based-agent
uv venv

# activate the virtual env
source .venv/bin/activate

# install the dependencies
cd app
uv pip install -r requirements.txt
```

### 2. Configure environment

```sh
cp .env.example .env
```

Edit .env and fill in your SAP AI Core and Tavily credentials

### 3. Start the server

```sh
python app.py
```

The server starts at `http://localhost:10000`. Interactive API docs are available at
`http://localhost:10000/docs`.

### 4. Run synchronous research

```sh
curl -X POST http://localhost:10000/research \
  -H "Content-Type: application/json" \
  -d '{"query": "Research the latest advances in AI agent frameworks"}'
```

### 5. Run asynchronous research

```sh
# Submit job
curl -X POST http://localhost:10000/research/jobs \
  -H "Content-Type: application/json" \
  -d '{"query": "Research the latest advances in AI agent frameworks"}'

# Poll result (replace <job_id> with the returned job_id)
curl http://localhost:10000/research/jobs/<job_id>
```

### 6. Run the test client

```sh
python test_client.py
```

## Cloud Foundry deployment

### 1. Update `app/manifest.yaml`

Fill in all `<placeholder>` values with your actual SAP AI Core credentials and
the intended application URL.

### 2. Deploy

```sh
cd examples/deep_research_api/app
cf push
```

## How it works

1. **Client sends a research query** via `POST /research` or `POST /research/jobs`.
2. **Orchestrator plans** the research by creating a todo list.
3. **Orchestrator delegates** one or more parallel research tasks to the
   `research-agent` sub-agent.
4. **Sub-agent searches the web** using Tavily, reflects using `think_tool`,
   and returns structured findings with citations.
5. **Orchestrator synthesises** all findings, consolidates citations, and
   writes a comprehensive Markdown report.
6. **Report is returned** in the API response or stored in the job store for polling.

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `AICORE_AUTH_URL` | ✅ | SAP AI Core OAuth token endpoint |
| `AICORE_CLIENT_ID` | ✅ | SAP AI Core client ID |
| `AICORE_CLIENT_SECRET` | ✅ | SAP AI Core client secret |
| `AICORE_RESOURCE_GROUP` | ✅ | Resource group (default: `default`) |
| `AICORE_BASE_URL` | ✅ | SAP AI Core API base URL |
| `TAVILY_API_KEY` | ✅ | Tavily search API key |
| `SUPPLIER_API_URL` | ❌ | Ariba OData supplier search endpoint (default: `https://xyz.hana.ondemand.com/Ariba_SearchSupplier/Suppliers`) |
| `SUPPLIER_AUTH_URL` | ❌ | OAuth 2.0 token endpoint for the supplier API (default: `https://xyz.authentication.eu10.hana.ondemand.com`) |
| `SUPPLIER_CLIENT_ID` | ❌ | Client ID for supplier API authentication |
| `SUPPLIER_CLIENT_SECRET` | ❌ | Client secret for supplier API authentication |
| `HOST` | ❌ | Server bind host (default: `0.0.0.0`) |
| `PORT` | ❌ | Server bind port (default: `10000`) |
