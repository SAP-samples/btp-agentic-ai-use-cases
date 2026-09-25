"""Tests for MCP response trimming helpers in util.py."""
# pyright: reportMissingImports=false

import json

import pytest

pytestmark = pytest.mark.structure


class TestMinifyJson:
    def test_pretty_json_is_minified(self, add_agent_to_path):
        from util import minify_json
        pretty = json.dumps({"a": 1, "b": [1, 2, 3]}, indent=2)
        out = minify_json(pretty)
        assert out == '{"a":1,"b":[1,2,3]}'
        assert "\n" not in out
        assert len(out) < len(pretty)

    def test_minified_json_round_trips(self, add_agent_to_path):
        from util import minify_json
        original = {"name": "cost-center", "rows": [{"id": 1}, {"id": 2}]}
        out = minify_json(json.dumps(original, indent=4))
        assert json.loads(out) == original

    def test_non_json_passes_through_unchanged(self, add_agent_to_path):
        from util import minify_json
        text = "not json, just a plain string with  spaces"
        assert minify_json(text) == text

    def test_already_compact_json_is_stable(self, add_agent_to_path):
        from util import minify_json
        compact = '{"a":1}'
        assert minify_json(compact) == compact

    def test_unicode_is_preserved_not_escaped(self, add_agent_to_path):
        from util import minify_json
        out = minify_json('{"label": "Kostenstelle €"}')
        assert "Kostenstelle €" in out


class TestTruncateResponse:
    def test_short_text_is_unchanged(self, add_agent_to_path):
        from util import truncate_response
        text = "small payload"
        assert truncate_response(text, max_chars=100) == text

    def test_oversized_text_is_truncated_with_marker(self, add_agent_to_path):
        from util import truncate_response
        text = "x" * 500
        out = truncate_response(text, max_chars=100)
        assert out.endswith("...[truncated]")
        assert len(out) <= 100 + len("\n...[truncated]")

    def test_truncation_prefers_a_clean_boundary(self, add_agent_to_path):
        from util import truncate_response
        # A comma sits inside the back-off window (final 10%). Truncation should
        # cut at the comma, dropping the partial token that follows it.
        text = ("A" * 94) + "," + ("B" * 100)
        out = truncate_response(text, max_chars=100)
        body = out[: -len("\n...[truncated]")]
        assert body == "A" * 94  # backed up to the comma, dropped the partial B-run
        assert "B" not in body

    def test_default_cap_is_modest(self, add_agent_to_path):
        from util import MCP_MAX_RESPONSE_CHARS
        # Guards against the old 100k default silently returning.
        assert MCP_MAX_RESPONSE_CHARS <= 50_000

