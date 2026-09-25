import re
from pathlib import Path

import yaml
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

_SKILLS_DIR = (Path(__file__).parent / "skills").resolve()
_LOAD_TOOL_NAME = "load"

def _validate_and_parse_frontmatter(text: str) -> tuple[str, str]:
    if not text.startswith("---"):
        raise ValueError("missing frontmatter opening '---'")
    closing_fence = re.search(r"\n---\s*(\n|$)", text[3:])
    if not closing_fence:
        raise ValueError("frontmatter is not closed with '---'")
    fm_text = text[3 : closing_fence.start() + 3]
    try:
        meta = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError as e:
        raise ValueError(f"invalid YAML in frontmatter: {e}") from e
    for field in ("name", "description"):
        if field not in meta:
            raise ValueError(f"frontmatter missing required field '{field}'")
        if not isinstance(meta[field], str):
            raise ValueError(f"frontmatter field '{field}' must be a string, got {type(meta[field]).__name__}")
    return meta["name"], meta["description"]

def _build_description() -> str:
    lines = ['This tool is used to load instructions ("skills"). Available are:']
    lines.append("")
    for entry in _SKILLS_DIR.iterdir():
        skill_md = entry / "SKILL.md"
        if not entry.is_dir() or not skill_md.exists():
            continue
        text = skill_md.read_text(encoding="utf-8")
        try:
            name, description = _validate_and_parse_frontmatter(text)
        except ValueError as e:
            raise ValueError(f"Skill '{entry.name}' has invalid frontmatter: {e}") from e
        lines.append(f"  name: {name} | description: {description} | path: {entry.name}")
    lines.append("")
    lines.append("To load additional resources, use load(path)")
    return "\n".join(lines)

async def _load(path: str) -> str:
    try:
        target = (_SKILLS_DIR / path).resolve()
    except (ValueError, OSError):
        return f"Error: invalid path '{path}'"
    if _SKILLS_DIR not in target.parents:
        return f"Error: invalid path '{path}'"
    if target.is_dir():
        target = target / "SKILL.md"
    if not target.exists():
        return f"Error: '{path}' not found"
    content = target.read_text(encoding="utf-8")
    return content

class _LoadInput(BaseModel):
    path: str = Field(description="Skill folder name or path to a specific resource within a skill (e.g. 'budget-queries' or 'budget-queries/references/api-guide.md')")

def get_load_skill_resource_tool() -> list[StructuredTool]:
    if not _SKILLS_DIR.is_dir() or not any(_SKILLS_DIR.iterdir()):
        return []
    return [StructuredTool(name=_LOAD_TOOL_NAME, description=_build_description(), args_schema=_LoadInput, coroutine=_load)]
