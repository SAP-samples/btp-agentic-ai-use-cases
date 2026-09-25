"""Tests for load_skill_resources.py — skill tool loading."""
# pyright: reportMissingImports=false

import os

import pytest


def _make_skill(tmp_path, folder_name: str, content: str) -> None:
    skill_dir = tmp_path / folder_name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")


@pytest.mark.structure
class TestValidateAndParseFrontmatter:
    def test_valid_frontmatter_returns_name_and_description(self, add_agent_to_path):
        from load_skill_resources import _validate_and_parse_frontmatter
        name, description = _validate_and_parse_frontmatter("---\nname: my-skill\ndescription: Does something\n---\n# Body")
        assert name == "my-skill"
        assert description == "Does something"

    def test_invalid_frontmatter_missing_opening_fence(self, add_agent_to_path):
        from load_skill_resources import _validate_and_parse_frontmatter
        with pytest.raises(ValueError, match="missing frontmatter opening"):
            _validate_and_parse_frontmatter("name: my-skill\ndescription: foo")

    def test_invalid_frontmatter_missing_closing_fence(self, add_agent_to_path):
        from load_skill_resources import _validate_and_parse_frontmatter
        with pytest.raises(ValueError, match="not closed"):
            _validate_and_parse_frontmatter("---\nname: my-skill\ndescription: foo")

    def test_invalid_frontmatter_invalid_yaml(self, add_agent_to_path):
        from load_skill_resources import _validate_and_parse_frontmatter
        with pytest.raises(ValueError, match="invalid YAML"):
            _validate_and_parse_frontmatter("---\nkey: [unclosed\n---\n# Body")

    def test_invalid_frontmatter_missing_name(self, add_agent_to_path):
        from load_skill_resources import _validate_and_parse_frontmatter
        with pytest.raises(ValueError, match="missing required field 'name'"):
            _validate_and_parse_frontmatter("---\ndescription: foo\n---\n# Body")

    def test_invalid_frontmatter_missing_description(self, add_agent_to_path):
        from load_skill_resources import _validate_and_parse_frontmatter
        with pytest.raises(ValueError, match="missing required field 'description'"):
            _validate_and_parse_frontmatter("---\nname: my-skill\n---\n# Body")

    def test_invalid_frontmatter_non_string_name(self, add_agent_to_path):
        from load_skill_resources import _validate_and_parse_frontmatter
        with pytest.raises(ValueError, match="'name' must be a string"):
            _validate_and_parse_frontmatter("---\nname:\n  - not\n  - a string\ndescription: foo\n---\n# Body")

    def test_invalid_frontmatter_non_string_description(self, add_agent_to_path):
        from load_skill_resources import _validate_and_parse_frontmatter
        with pytest.raises(ValueError, match="'description' must be a string"):
            _validate_and_parse_frontmatter("---\nname: my-skill\ndescription:\n  key: value\n---\n# Body")


@pytest.mark.structure
class TestGetLoadSkillResourceTool:

    def test_get_load_tool_with_valid_skill(self, tmp_path, add_agent_to_path, monkeypatch):
        import load_skill_resources
        skills_dir = tmp_path / "skills"
        _make_skill(skills_dir, "my-skill", "---\nname: my-skill\ndescription: A valid skill\n---\n# Body")
        monkeypatch.setattr(load_skill_resources, "_SKILLS_DIR", skills_dir)
        tools = load_skill_resources.get_load_skill_resource_tool()
        assert len(tools) == 1
        assert tools[0].name == "load"
        assert "my-skill" in tools[0].description
        assert "A valid skill" in tools[0].description

    def test_get_load_tool_with_invalid_skill(self, tmp_path, add_agent_to_path, monkeypatch):
        import load_skill_resources
        skills_dir = tmp_path / "skills"
        _make_skill(skills_dir, "bad-skill", "---\nname: bad-skill\n---\n# Missing description")
        monkeypatch.setattr(load_skill_resources, "_SKILLS_DIR", skills_dir)
        with pytest.raises(ValueError, match="bad-skill"):
            load_skill_resources.get_load_skill_resource_tool()

    def test_actual_skills_load_without_error(self, add_agent_to_path):
        import load_skill_resources
        tools = load_skill_resources.get_load_skill_resource_tool()
        assert isinstance(tools, list)


@pytest.mark.structure
class TestLoadPathTraversal:

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path, add_agent_to_path, monkeypatch):
        import load_skill_resources

        skills_dir = (tmp_path / "skills").resolve()
        _make_skill(skills_dir, "skill1", "---\nname: skill1\ndescription: d\n---\n# Body\nLEGIT")

        self.external = tmp_path / "secret.txt"
        self.external.write_text("SECRET", encoding="utf-8")

        monkeypatch.setattr(load_skill_resources, "_SKILLS_DIR", skills_dir)
        self.skills_dir = skills_dir
        self.load = load_skill_resources._load

    async def test_dot_dot_traversal(self):
        result = await self.load("../secret.txt")
        assert result.startswith("Error:")
        assert "SECRET" not in result

    async def test_multi_level_traversal(self):
        result = await self.load("../../etc/passwd")
        assert result.startswith("Error:")

    async def test_absolute_path_injection(self):
        result = await self.load(str(self.external))
        assert result.startswith("Error:")
        assert "SECRET" not in result

    async def test_dot_resolves_to_base_is_rejected(self):
        result = await self.load(".")
        assert result.startswith("Error:")

    async def test_empty_path_is_rejected(self):
        result = await self.load("")
        assert result.startswith("Error:")

    async def test_climb_to_base_via_dotdot_is_rejected(self):
        result = await self.load("skill1/..")
        assert result.startswith("Error:")

    async def test_symlink_to_external_file_is_rejected(self):
        sym = self.skills_dir / "skill1" / "evil.md"
        os.symlink(str(self.external), str(sym))
        result = await self.load("skill1/evil.md")
        assert result.startswith("Error:")
        assert "SECRET" not in result

    async def test_null_byte_does_not_leak(self):
        result = await self.load("skill1/SKILL.md\x00../../secret.txt")
        assert "SECRET" not in result
