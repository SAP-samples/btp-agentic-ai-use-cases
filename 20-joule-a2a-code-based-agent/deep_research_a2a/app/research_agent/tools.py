"""Research tools for the deep research agent.

Provides web search via Tavily and a strategic reflection tool
for conducting structured web research.
"""

import httpx
from langchain_core.tools import InjectedToolArg, tool
from markdownify import markdownify
from tavily import TavilyClient
from typing_extensions import Annotated, Literal

tavily_client = TavilyClient()


def fetch_webpage_content(url: str, timeout: float = 10.0) -> str:
    """Fetch and convert webpage content to markdown.

    Args:
        url: URL to fetch.
        timeout: Request timeout in seconds.

    Returns:
        Webpage content converted to markdown, or an error message on failure.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/91.0.4472.124 Safari/537.36"
        )
    }
    try:
        response = httpx.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        return markdownify(response.text)
    except Exception as e:
        return f"Error fetching content from {url}: {e!s}"


@tool(parse_docstring=True)
def tavily_search(
    query: str,
    max_results: Annotated[int, InjectedToolArg] = 1,
    topic: Annotated[
        Literal["general", "news", "finance"], InjectedToolArg
    ] = "general",
) -> str:
    """Search the web for information on a given query.

    Uses Tavily to discover relevant URLs, then fetches and returns full
    webpage content as markdown.

    Args:
        query: Search query to execute.
        max_results: Maximum number of results to return.
        topic: Topic filter - 'general', 'news', or 'finance'.

    Returns:
        Formatted search results with full webpage content in markdown.
    """
    search_results = tavily_client.search(
        query,
        max_results=max_results,
        topic=topic,
    )

    result_texts = []
    for result in search_results.get("results", []):
        url = result["url"]
        title = result["title"]
        content = fetch_webpage_content(url)
        result_texts.append(f"## {title}\n**URL:** {url}\n\n{content}\n\n---\n")

    return f"🔍 Found {len(result_texts)} result(s) for '{query}':\n\n" + "\n".join(
        result_texts
    )


@tool(parse_docstring=True)
def think_tool(reflection: str) -> str:
    """Tool for strategic reflection on research progress and decision-making.

    Use this tool after each search to analyze results and plan next steps
    systematically. Creates a deliberate pause in the research workflow for
    quality decision-making.

    When to use:
    - After receiving search results to analyze what was found.
    - Before deciding next steps to assess whether enough information exists.
    - When identifying research gaps that still need to be filled.
    - Before concluding research to confirm the answer is complete.

    Reflection should address:
    1. Analysis of current findings - What concrete information has been gathered?
    2. Gap assessment - What crucial information is still missing?
    3. Quality evaluation - Is there sufficient evidence for a good answer?
    4. Strategic decision - Continue searching or provide the answer?

    Args:
        reflection: Detailed reflection on research progress, findings, gaps,
            and next steps.

    Returns:
        Confirmation that the reflection was recorded for decision-making.
    """
    return f"Reflection recorded: {reflection}"
