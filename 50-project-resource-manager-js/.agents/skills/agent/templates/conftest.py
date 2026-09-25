"""Root conftest.py — fixtures and pytest plugin for the IBD agent test suite.

When copied into /assets/<asset-name> this file:
  - sets IBD_TESTING=1 so mcp_providers.agw.get_mcp_tools() returns mock tools from
    mcp-mock.json instead of making real network calls
  - provides shared fixtures used by prebuilt_tests/ (agent path, server lifecycle)
  - registers custom markers
  - collects per-test results and writes test_report.json on session finish
"""

from __future__ import annotations

import os

# Set IBD_TESTING before anything else.
os.environ["IBD_TESTING"] = "1"

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

AGENT_ROOT = Path(__file__).parent


# Ordered list of (marker, display label, result-bucket key).
# Tests with no marker from this list fall into the "agent_tests" bucket.
# The server and structure markers must only be used by tests inside the prebuilt_tests/ module.
SECTIONS: list[tuple[str, str, str]] = [
    ("structure", "Structure Tests", "structure"),
    ("server", "Server Tests", "server"),
    ("", "Agent Tests", "agent_tests"),
]

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        s.listen(1)
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def agent_path() -> Path:
    """Root directory of the generated agent."""
    return AGENT_ROOT


@pytest.fixture(scope="session")
def agent_app_path(agent_path: Path) -> Path:
    """Path to the agent's app/ package directory."""
    return agent_path / "app"


@pytest.fixture(scope="session")
def add_agent_to_path(agent_app_path: Path):
    """Add app/ to sys.path so agent modules can be imported as peer-level imports.

    Only app/ is added because the runtime server (main.py) runs from inside app/,
    making modules like ``agent``, ``mcp_providers``, ``tools`` etc. top-level names.
    Do NOT add the agent root — that would make ``from app.xxx import ...`` resolve
    during tests but fail at runtime where only app/ is on the path.
    """
    p = str(agent_app_path)
    added = False
    if p not in sys.path:
        sys.path.insert(0, p)
        added = True
    yield
    if added and p in sys.path:
        sys.path.remove(p)


@pytest.fixture
def start_agent(agent_path: Path):
    """Start the agent server for each test, yield {process, port}, then shut down.

    Server stderr is streamed directly to the terminal so it appears inline
    in the test log alongside the test output.
    """
    port = _get_free_port()
    main_file = agent_path / "app" / "main.py"

    print(f"\n{"=" * 80}\nStarting A2A server on port {port}...\n{"=" * 80}\n")

    # Disable the OpenTelemetry SDK in the server subprocess.
    # stderr=None lets the server write directly to the terminal.
    server_env = {**os.environ, "OTEL_SDK_DISABLED": "true", "IBD_TESTING": "1"}

    process = subprocess.Popen(
        [sys.executable, str(main_file), "--port", str(port)],
        cwd=str(agent_path),
        env=server_env,
        stderr=None,  # stream directly to terminal
        text=True,
    )

    # Poll until the port is accepting connections (up to 30 s).
    deadline = time.monotonic() + 30
    ready = False
    while time.monotonic() < deadline:
        if process.poll() is not None:
            pytest.fail(f"Server process exited early (exit code: {process.poll()})")
        try:
            with socket.create_connection(("localhost", port), timeout=0.5):
                ready = True
                break
        except OSError:
            time.sleep(0.5)

    if not ready:
        process.terminate()
        pytest.fail(f"Server did not become ready on port {port} within 30 s")

    print(
        f"\n{"=" * 80}\nA2A server started on http://localhost:{port}\n{"=" * 80}\n"
    )

    yield {"process": process, "port": port}

    print(f"\n{"=" * 80}\nShutting down A2A server on port {port}...\n{"=" * 80}\n")
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()

    print("A2A server stopped.\n")


# ---------------------------------------------------------------------------
# pytest hooks — configuration
# ---------------------------------------------------------------------------


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "structure: Tests for file and module structure")
    config.addinivalue_line(
        "markers", "server: Tests for server startup and A2A endpoints"
    )


# ---------------------------------------------------------------------------
# Result collection
# ---------------------------------------------------------------------------

_results: dict[str, list[dict[str, Any]]] = {
    "structure": [],
    "server": [],
    "agent_tests": [],
}


def _section_for(item: pytest.Item) -> str:
    marker_names = {m.name for m in item.iter_markers()}
    for marker, _label, key in SECTIONS[:-1]:  # skip the catch-all "agent_tests" entry
        if marker in marker_names:
            return key
    return "agent_tests"


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(
    item: pytest.Item, call: pytest.CallInfo
) -> pytest.Generator:
    outcome = yield
    report: pytest.TestReport = outcome.get_result()

    # Attach the call-phase report to the item so fixtures can inspect it.
    if report.when == "call":
        item.rep_call = report  # type: ignore[attr-defined]

    if report.when == "call" or (report.when == "setup" and report.skipped):
        outcome_str = (
            "passed" if report.passed else ("failed" if report.failed else "skipped")
        )
        _results[_section_for(item)].append(
            {
                "name": report.nodeid.split("::")[-1],
                "outcome": outcome_str,
                "duration": round(getattr(report, "duration", 0.0), 4),
            }
        )


# ---------------------------------------------------------------------------
# Full-run detection
# ---------------------------------------------------------------------------


def _is_full_run(config: pytest.Config) -> bool:
    """Return True only when no narrowing filters are active.

    A partial run is detected when any of the following are present:
      -k  keyword filter
      -m  marker filter
      --lf  last-failed
      :: in a positional arg (node-id)
      a positional path that points *inside* a configured testpath dir
      a positional set that is a strict subset of the configured testpath roots
    """
    opt = config.option
    if getattr(opt, "keyword", ""):
        return False
    if getattr(opt, "markexpr", ""):
        return False
    if getattr(opt, "lf", False):
        return False

    positional = [
        a for a in config.invocation_params.args if not str(a).startswith("-")
    ]

    if not positional:
        return True  # no args → full suite via testpaths ini

    if any("::" in str(a) for a in positional):
        return False  # node-id selection

    rootdir = Path(config.rootdir)
    configured = {(rootdir / tp).resolve() for tp in config.getini("testpaths")}
    supplied = {
        (Path(config.invocation_params.dir) / str(a)).resolve() for a in positional
    }

    if supplied == configured:
        return True
    if supplied < configured:
        return False  # subset of testpath roots

    for sp in supplied:
        for tp in configured:
            if sp.is_relative_to(tp) and sp != tp:
                return False  # path inside a testpath dir

    return True


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Write test_report.json after a full run; skip for partial runs."""
    if not _is_full_run(session.config):
        return

    sections_out = []
    for _marker, label, key in SECTIONS:
        tests = _results[key]
        total = len(tests)
        passed = sum(1 for t in tests if t["outcome"] == "passed")
        failed = sum(1 for t in tests if t["outcome"] == "failed")
        skipped = sum(1 for t in tests if t["outcome"] == "skipped")

        section: dict[str, Any] = {
            "name": label,
            "marker": key,
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "score": round(passed / total * 100, 2) if total else 0.0,
            "tests": tests,
        }

        if key == "agent_tests":
            cov_path = AGENT_ROOT / "coverage.json"
            if cov_path.exists():
                try:
                    cov_data = json.loads(cov_path.read_text())
                    section["coverage"] = round(
                        cov_data["totals"]["percent_covered"], 2
                    )
                except Exception:
                    pass
            else:
                print(f"Coverage not found: {cov_path}")
            if total == 0:
                section["skipped_reason"] = "No agent tests found"

        sections_out.append(section)

    total_all = sum(s["total"] for s in sections_out)
    passed_all = sum(s["passed"] for s in sections_out)
    failed_all = sum(s["failed"] for s in sections_out)
    overall_score = round(passed_all / total_all * 100, 2) if total_all else 0.0

    report_path = AGENT_ROOT / "test_report.json"
    report_path.write_text(
        json.dumps(
            {
                "summary": {
                    "total": total_all,
                    "passed": passed_all,
                    "failed": failed_all,
                    "score": overall_score,
                },
                "sections": sections_out,
            },
            indent=2,
        )
    )
    print(f"\nReport written to {report_path}")
