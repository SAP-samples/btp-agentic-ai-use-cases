"""Tests for agent file structure and module validity."""

import json
import subprocess
import sys

import pytest


@pytest.mark.structure
class TestRequiredFiles:
    """Test that all required files exist."""

    def test_agent_directory_exists(self, agent_path):
        """Test that the generated_agent directory exists."""
        assert agent_path.exists(), f"Agent directory not found: {agent_path}"
        assert agent_path.is_dir(), f"Agent path is not a directory: {agent_path}"

    def test_app_directory_exists(self, agent_app_path):
        """Test that the app directory exists."""
        assert agent_app_path.exists(), f"App directory not found: {agent_app_path}"
        assert agent_app_path.is_dir(), f"App path is not a directory: {agent_app_path}"

    def test_requirements_txt_exists(self, agent_path):
        """Test that requirements.txt exists."""
        req_file = agent_path / "requirements.txt"
        assert req_file.exists(), "requirements.txt is missing"
        assert req_file.stat().st_size > 0, "requirements.txt is empty"

    def test_no_pylint_errors(self, agent_app_path):
        """Verify all app modules have no pylint errors (category E)."""
        init_hook = f"import sys; sys.path.insert(0, '{agent_app_path}')"
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pylint",
                str(agent_app_path),
                "--disable=all",
                "--enable=E",
                "--output-format=text",
                f"--init-hook={init_hook}",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode in (0, 1), (
            f"pylint exited with unexpected code {result.returncode}\n"
            + (f"stderr:\n{result.stderr}" if result.stderr.strip() else "")
        )
        errors = [line for line in result.stdout.splitlines() if ": E" in line]
        if result.stderr.strip():
            errors.append(f"[stderr] {result.stderr.strip()}")
        assert not errors, "Pylint errors found:\n" + "\n".join(errors)

    def test_imports_resolvable(self, agent_app_path):
        """Verify all app imports resolve in the current environment."""
        result = subprocess.run(
            [sys.executable, "-m", "pyright", str(agent_app_path), "--outputjson"],
            capture_output=True,
            text=True,
            check=False,
        )
        try:
            data = json.loads(result.stdout)
            errors = [
                f"{d['file']}:{d['range']['start']['line']}: {d['message']}"
                for d in data.get("generalDiagnostics", [])
                if d["severity"] == "error" and d.get("rule") == "reportMissingImports"
            ]
        except (json.JSONDecodeError, KeyError):
            errors = [
                line for line in result.stdout.splitlines()
                if "error" in line.lower() and "import" in line.lower()
            ]
        assert not errors, "Missing imports found:\n" + "\n".join(errors)
