"""Template registry that records, but never assumes, official compatibility."""

from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, Field


class ReportTemplate(BaseModel):
    template_id: str = Field(min_length=1)
    path: Path
    required_placeholders: set[str] = Field(default_factory=set)
    synthetic_test_only: bool = False
    official_compatibility_verified: bool = False


class TemplateRegistry(Protocol):
    def get(self, template_id: str) -> ReportTemplate | None: ...


class InMemoryTemplateRegistry:
    def __init__(self, templates: list[ReportTemplate] | None = None) -> None:
        self._templates: dict[str, ReportTemplate] = {}
        for template in templates or []:
            self.register(template)

    def register(self, template: ReportTemplate) -> None:
        if template.template_id in self._templates:
            raise ValueError(f"duplicate report template: {template.template_id}")
        self._templates[template.template_id] = template

    def get(self, template_id: str) -> ReportTemplate | None:
        return self._templates.get(template_id)
