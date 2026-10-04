"""Project paths and tailoring configuration."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL = "gemma4:12b"
DEFAULT_OLLAMA_URL = "http://localhost:11434"
REQUIREMENTS_PROMPT = ROOT / "src/prompts/01-extract-job-requirements.md"
RESUME_DATA = ROOT / "resume_data"
TEMPLATES = ROOT / "templates"
PROMPTS = ROOT / "src/prompts"
BASE_RESUME_TEMPLATE = TEMPLATES / "latex/00-resume-template.tex"
BASE_COVER_LETTER_TEMPLATE = TEMPLATES / "latex/05-cover-letter-template.tex"
COVER_LETTER_CONTENT_TEMPLATE = TEMPLATES / "latex/06-cover-letter-content-template.tex"
COVER_LETTER_PROMPT = PROMPTS / "06-cover-letter.md"
COVER_LETTER_ENDING = (
    r"\par\vspace{12pt} Thanks for your time, and I look forward to the conversation. "
    r"\par\vspace{12pt} Best regards,\par\vspace{6pt} \textbf{Chujia Guo}"
)


def _string_array_schema(*, max_items: int | None = None) -> dict[str, object]:
    schema: dict[str, object] = {"type": "array", "items": {"type": "string"}}
    if max_items is not None:
        schema["maxItems"] = max_items
    return schema


SKILLS_SCHEMA = {
    "type": "object",
    "properties": {name: _string_array_schema() for name in ("languages", "frameworks", "developer_tools", "libraries")},
    "required": ["languages", "frameworks", "developer_tools", "libraries"],
    "additionalProperties": False,
}
EDUCATION_SCHEMA = {
    "type": "object",
    "properties": {"entries": {"type": "array", "items": {
        "type": "object",
        "properties": {name: {"type": "string"} for name in ("institution", "location", "degree_and_field", "dates")},
        "required": ["institution", "location", "degree_and_field", "dates"],
        "additionalProperties": False,
    }}},
    "required": ["entries"], "additionalProperties": False,
}
EXPERIENCE_SCHEMA = {
    "type": "object",
    "properties": {"entries": {"type": "array", "items": {
        "type": "object",
        "properties": {
            **{name: {"type": "string"} for name in ("company", "dates", "role", "location")},
            "bullets": _string_array_schema(max_items=3),
        },
        "required": ["company", "dates", "role", "location", "bullets"],
        "additionalProperties": False,
    }}},
    "required": ["entries"], "additionalProperties": False,
}
PROJECTS_SCHEMA = {
    "type": "object",
    "properties": {"entries": {"type": "array", "items": {
        "type": "object",
        "properties": {
            **{name: {"type": "string"} for name in ("name", "dates", "role")},
            "links": {"type": "array", "items": {
                "type": "object",
                "properties": {"label": {"type": "string"}, "url": {"type": "string"}},
                "required": ["label", "url"], "additionalProperties": False,
            }},
            "bullets": _string_array_schema(max_items=3),
        },
        "required": ["name", "dates", "role", "links", "bullets"],
        "additionalProperties": False,
    }}},
    "required": ["entries"], "additionalProperties": False,
}
REQUIREMENTS_SCHEMA = {
    "type": "object",
    "properties": {
        "role": {"type": "string"},
        "company": {"type": "string"},
        "location": {"type": "string"},
        "minimum_requirements": {"type": "array", "items": {
            "type": "object",
            "properties": {name: {"type": "string"} for name in ("id", "category", "requirement", "evidence")},
            "required": ["id", "category", "requirement", "evidence"], "additionalProperties": False,
        }},
        "preferred_requirements": {"type": "array", "items": {
            "type": "object",
            "properties": {name: {"type": "string"} for name in ("id", "category", "requirement", "evidence")},
            "required": ["id", "category", "requirement", "evidence"], "additionalProperties": False,
        }},
        "notes": _string_array_schema(),
    },
    "required": ["role", "company", "location", "minimum_requirements", "preferred_requirements", "notes"],
    "additionalProperties": False,
}
COVER_LETTER_SCHEMA = {
    "type": "object",
    "properties": {
        "introduction": {"type": "string"},
        "examples": {"type": "array", "minItems": 2, "maxItems": 4, "items": {
            "type": "object",
            "properties": {"title": {"type": "string"}, "body": {"type": "string"}},
            "required": ["title", "body"], "additionalProperties": False,
        }},
        "company_motivation": {"type": "string"},
    },
    "required": ["introduction", "examples", "company_motivation"],
    "additionalProperties": False,
}

SECTION_CONFIGS = (
    {
        "key": "education",
        "title": "Education",
        "prompt": PROMPTS / "02-education.md",
        "data": RESUME_DATA / "education",
        "template": TEMPLATES / "latex/01-education-template.tex",
        "list_wrapper": True,
        "schema": EDUCATION_SCHEMA,
    },
    {
        "key": "skills",
        "title": "Technical Skills",
        "prompt": PROMPTS / "03-skills.md",
        "data": RESUME_DATA / "skills.md",
        "template": TEMPLATES / "latex/02-skills-template.tex",
        "list_wrapper": False,
        "schema": SKILLS_SCHEMA,
    },
    {
        "key": "experience",
        "title": "Experience",
        "prompt": PROMPTS / "04-experience.md",
        "data": RESUME_DATA / "experience",
        "template": TEMPLATES / "latex/03-experience-template.tex",
        "list_wrapper": True,
        "schema": EXPERIENCE_SCHEMA,
    },
    {
        "key": "projects",
        "title": "Projects",
        "prompt": PROMPTS / "05-projects.md",
        "data": RESUME_DATA / "projects",
        "template": TEMPLATES / "latex/04-projects-template.tex",
        "list_wrapper": True,
        "schema": PROJECTS_SCHEMA,
    },
)
