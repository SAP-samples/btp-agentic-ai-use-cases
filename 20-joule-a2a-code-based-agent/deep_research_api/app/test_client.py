"""Test client for the Deep Research Agent REST API.

Demonstrates both the synchronous and asynchronous research endpoints.

Usage:
    # Start the server first:
    #   uvicorn app:app --port 10000
    #
    # Then run this client:
    #   python test_client.py

    # To test against a deployed instance set BASE_URL:
    #   BASE_URL=https://deep-research-agent.cfapps.sap.hana.ondemand.com python test_client.py
"""

import asyncio
import logging
import os
import time

import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = os.getenv("BASE_URL", "http://localhost:10000")

# RESEARCH_QUESTION = (
#     "Research different approaches to custom AI Agent development with "
#     "Joule Studio Agent Builder, Joule Studio Code Editor and SAP Cloud SDK for AI"
# )
RESEARCH_QUESTION = """Find out a super-tasteful orange berry typical of Scandinavia, and its supplier from the Ariba catalog."""

# Polling interval and maximum wait time for async jobs (seconds)
_POLL_INTERVAL = 10
_POLL_TIMEOUT = 600


async def test_sync_endpoint(client: httpx.AsyncClient) -> None:
    """Call POST /research and print the result.

    Blocks until the research is complete.

    Args:
        client: Shared async HTTP client.
    """
    print("\n" + "=" * 60)
    print("SYNCHRONOUS ENDPOINT  POST /research")
    print("=" * 60)
    print(f"Query: {RESEARCH_QUESTION}")
    print("-" * 60)

    response = await client.post(
        f"{BASE_URL}/research",
        json={"query": RESEARCH_QUESTION},
    )
    response.raise_for_status()
    data = response.json()

    print(f"Status : {data['status']}")
    print(f"Query  : {data['query']}")
    print("\nResult:")
    print(data["result"])
    print("...")


async def test_async_endpoint(client: httpx.AsyncClient) -> None:
    """Call POST /research/jobs then poll GET /research/jobs/{job_id}.

    Submits the job, prints the job_id, then polls until complete.

    Args:
        client: Shared async HTTP client.
    """
    print("\n" + "=" * 60)
    print("ASYNCHRONOUS ENDPOINT  POST /research/jobs")
    print("=" * 60)
    print(f"Query: {RESEARCH_QUESTION}")
    print("-" * 60)

    # Submit job
    response = await client.post(
        f"{BASE_URL}/research/jobs",
        json={"query": RESEARCH_QUESTION},
    )
    response.raise_for_status()
    job = response.json()
    job_id = job["job_id"]
    print(f"Job submitted — job_id: {job_id}  status: {job['status']}")

    # Poll until done
    print(f"\nPolling GET /research/jobs/{job_id} every {_POLL_INTERVAL}s ...")
    deadline = time.monotonic() + _POLL_TIMEOUT
    while time.monotonic() < deadline:
        await asyncio.sleep(_POLL_INTERVAL)
        status_response = await client.get(f"{BASE_URL}/research/jobs/{job_id}")
        status_response.raise_for_status()
        status = status_response.json()
        print(f"  status: {status['status']}")

        if status["status"] == "completed":
            print("\nResult:")
            print(status["result"])
            print("...")
            break

        if status["status"] == "failed":
            print(f"\nJob failed: {status.get('error')}")
            break
    else:
        print(f"\nTimed out after {_POLL_TIMEOUT}s — job may still be running.")


async def main() -> None:
    """Run synchronous and asynchronous endpoint tests."""
    async with httpx.AsyncClient(timeout=httpx.Timeout(620.0)) as client:
        await test_sync_endpoint(client)
        await test_async_endpoint(client)


if __name__ == "__main__":
    asyncio.run(main())
