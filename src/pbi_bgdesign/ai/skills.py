"""Load and manage Skill files from a directory."""
import re
from pathlib import Path


def _parse_frontmatter(content: str) -> dict:
    """Parse YAML frontmatter from markdown content."""
    match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if not match:
        return {}
    fm = {}
    for line in match.group(1).split("\n"):
        if ":" in line:
            key, _, value = line.partition(":")
            fm[key.strip()] = value.strip()
    return fm


class SkillLoader:
    """Load Skill files from a directory and provide access to their content."""

    def __init__(self, skills_dir: str):
        self.skills_dir = Path(skills_dir)
        self.skills: list[dict] = []
        self._content_cache: dict[str, str] = {}

    def load(self):
        """Scan skills directory and load all .md files."""
        self.skills = []
        self._content_cache = {}

        if not self.skills_dir.exists():
            return

        for path in sorted(self.skills_dir.glob("*.md")):
            content = path.read_text(encoding="utf-8")
            fm = _parse_frontmatter(content)
            if "name" not in fm:
                continue

            skill = {
                "name": fm["name"],
                "description": fm.get("description", ""),
                "whenToUse": fm.get("whenToUse", ""),
                "path": str(path),
            }
            self.skills.append(skill)
            self._content_cache[fm["name"]] = content

    def get_summary(self) -> str:
        """Generate a summary of all loaded skills for system prompt injection."""
        if not self.skills:
            return "No skills available."

        lines = ["Available skills:"]
        for s in self.skills:
            lines.append(f"- {s['name']}: {s['description']}")
            if s["whenToUse"]:
                lines.append(f"  TRIGGER — {s['whenToUse']}")
        lines.append("")
        lines.append("Use the load_skill tool to load a skill's full instructions when needed.")
        return "\n".join(lines)

    def get_skill_content(self, name: str) -> str | None:
        """Get the full content of a skill by name."""
        return self._content_cache.get(name)
