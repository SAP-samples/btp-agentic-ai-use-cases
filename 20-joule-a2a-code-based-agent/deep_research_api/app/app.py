"""FastAPI application for the Deep Research Agent.

Exposes the deep research agent as a REST API with synchronous and
asynchronous endpoints so any application or agent can trigger deep research
on a given user query.
"""

import logging
import os
import uuid
from typing import Literal

from agent import DeepResearchAgent
from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 10000))

# In-memory job store — suitable for single-instance deployments
_jobs: dict[str, dict] = {}

# Shared agent instance (initialised once at startup)
_agent = DeepResearchAgent()

app = FastAPI(
    title="Deep Research Agent API",
    description=(
        "REST API for the deep research agent. Conducts comprehensive web "
        "research and returns structured Markdown reports with citations."
    ),
    version="1.0.0",
)

# ------------------------------------------------------------------
# Request / response models
# ------------------------------------------------------------------


class ResearchRequest(BaseModel):
    query: str


class ResearchResponse(BaseModel):
    query: str
    result: str
    status: Literal["completed"] = "completed"


class JobResponse(BaseModel):
    job_id: str
    query: str
    status: Literal["running", "completed", "failed"]
    result: str | None = None
    error: str | None = None


# ------------------------------------------------------------------
# Synchronous endpoint — blocks until research is complete
# ------------------------------------------------------------------


@app.post("/research", response_model=ResearchResponse)
async def research(request: ResearchRequest) -> ResearchResponse:
    """Run deep research synchronously and return the completed report.

    Blocks until research is complete. Deep research typically takes several
    minutes; use `POST /research/jobs` for non-blocking execution.
    """
    logger.info("Synchronous research request: %s", request.query)
    result = await _agent.run(request.query)
    return ResearchResponse(query=request.query, result=result)


# ------------------------------------------------------------------
# Asynchronous endpoints — submit job, poll for result
# ------------------------------------------------------------------


@app.post("/research/jobs", response_model=JobResponse, status_code=202)
async def create_research_job(
    request: ResearchRequest,
    background_tasks: BackgroundTasks,
) -> JobResponse:
    """Submit a deep research job for asynchronous execution.

    Returns immediately with a `job_id`. Poll `GET /research/jobs/{job_id}`
    to check status and retrieve the result when complete.
    """
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {
        "status": "running",
        "query": request.query,
        "result": None,
        "error": None,
    }
    background_tasks.add_task(_run_research_job, job_id, request.query)
    logger.info("Async research job created: job_id=%s query=%s", job_id, request.query)
    return JobResponse(job_id=job_id, query=request.query, status="running")


@app.get("/research/jobs/{job_id}", response_model=JobResponse)
async def get_research_job(job_id: str) -> JobResponse:
    """Retrieve the status and result of an asynchronous research job."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    return JobResponse(job_id=job_id, **job)


# ------------------------------------------------------------------
# Background task runner
# ------------------------------------------------------------------


async def _run_research_job(job_id: str, query: str) -> None:
    """Run the research agent in the background and update the job store.

    Args:
        job_id: Unique identifier of the job to update.
        query: Research question to investigate.
    """
    try:
        result = await _agent.run(query)
        _jobs[job_id].update({"status": "completed", "result": result})
        logger.info("Research job completed: job_id=%s", job_id)
    except Exception as e:
        msg = str(e)
        _jobs[job_id].update({"status": "failed", "error": msg})
        logger.exception("Research job failed: job_id=%s error=%s", job_id, msg)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=HOST, port=PORT)
