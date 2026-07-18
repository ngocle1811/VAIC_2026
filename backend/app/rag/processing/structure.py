"""Deterministic Vietnamese administrative-document structure analysis."""

from __future__ import annotations

import re

from app.rag.models import (
    BlockType,
    DocumentBlock,
    ParsedDocument,
    StructureKind,
    StructureMatch,
)

_RULES: tuple[tuple[StructureKind, int, re.Pattern[str]], ...] = (
    (
        StructureKind.PART,
        1,
        re.compile(r"^PHẦN\s+([A-ZÀ-Ỹ0-9IVXLCDM]+)\b(?:[.:-]?\s*(.*))?$", re.I),
    ),
    (
        StructureKind.CHAPTER,
        2,
        re.compile(r"^CHƯƠNG\s+([A-ZÀ-Ỹ0-9IVXLCDM]+)\b(?:[.:-]?\s*(.*))?$", re.I),
    ),
    (
        StructureKind.SECTION,
        3,
        re.compile(r"^MỤC\s+([A-ZÀ-Ỹ0-9IVXLCDM]+)\b(?:[.:-]?\s*(.*))?$", re.I),
    ),
    (StructureKind.ARTICLE, 4, re.compile(r"^Điều\s+(\d+[a-zA-ZĐđ]?)\s*[.:-]?\s*(.*)$", re.I)),
    (StructureKind.CLAUSE, 5, re.compile(r"^(\d+)\s*[.)]\s+(.+)$")),
    (StructureKind.POINT, 6, re.compile(r"^([a-zđ])\s*[.)]\s+(.+)$", re.I)),
    (
        StructureKind.APPENDIX,
        1,
        re.compile(r"^(?:PHỤ\s+LỤC|APPENDIX)\s*([A-ZÀ-Ỹ0-9IVXLCDM.-]*)\s*(.*)$", re.I),
    ),
)
_TEMPLATE_SECTION = re.compile(
    r"^(?:I{1,3}|IV|V|VI{0,3}|IX|X|\d+)\s*[.)-]\s*"
    r"(THÔNG TIN|NỘI DUNG|KẾT QUẢ|KIẾN NGHỊ|ĐÁNH GIÁ|TÌNH HÌNH).*$",
    re.I,
)


class VietnameseStructureAnalyzer:
    """Label Phần/Chương/Mục/Điều/Khoản/Điểm and template structure."""

    def classify(self, text: str) -> StructureMatch | None:
        normalized = re.sub(r"\s+", " ", text).strip()
        if _TEMPLATE_SECTION.match(normalized):
            return StructureMatch(kind=StructureKind.TEMPLATE_SECTION, label=normalized, level=2)
        for kind, level, pattern in _RULES:
            match = pattern.match(normalized)
            if match:
                identifier = match.group(1) or None
                title = (
                    match.group(2).strip() if len(match.groups()) > 1 and match.group(2) else None
                )
                return StructureMatch(
                    kind=kind,
                    label=normalized,
                    level=level,
                    identifier=identifier,
                    title=title,
                )
        if self._looks_like_heading(normalized):
            return StructureMatch(kind=StructureKind.HEADING, label=normalized, level=3)
        return None

    def analyze(self, document: ParsedDocument) -> ParsedDocument:
        hierarchy: dict[int, str] = {}
        parents: dict[int, str] = {}
        current_article: str | None = None
        current_clause: str | None = None
        current_point: str | None = None
        analyzed: list[DocumentBlock] = []
        for block in document.blocks:
            if block.block_type in {BlockType.PAGE_BREAK, BlockType.TABLE}:
                analyzed.append(
                    block.model_copy(
                        update={
                            "heading_hierarchy": [hierarchy[level] for level in sorted(hierarchy)],
                            "article": current_article,
                            "clause": current_clause,
                            "point": current_point,
                            "parent_block_id": parents[max(parents)] if parents else None,
                        }
                    )
                )
                continue
            match = self.classify(block.text)
            update: dict[str, object] = {}
            if match:
                level = match.level
                hierarchy = {key: value for key, value in hierarchy.items() if key < level}
                parents = {key: value for key, value in parents.items() if key < level}
                hierarchy[level] = match.label
                parent_id = parents[max(parents)] if parents else None
                parents[level] = block.block_id
                update.update(
                    block_type=BlockType(match.kind.value),
                    heading_level=level,
                    parent_block_id=parent_id,
                )
                if match.kind == StructureKind.ARTICLE:
                    current_article, current_clause, current_point = match.identifier, None, None
                elif match.kind == StructureKind.CLAUSE:
                    current_clause, current_point = match.identifier, None
                elif match.kind == StructureKind.POINT:
                    current_point = match.identifier
            update.update(
                heading_hierarchy=[hierarchy[level] for level in sorted(hierarchy)],
                article=current_article,
                clause=current_clause,
                point=current_point,
            )
            analyzed.append(block.model_copy(update=update))
        return document.model_copy(update={"blocks": analyzed})

    @staticmethod
    def _looks_like_heading(text: str) -> bool:
        if not text or len(text) > 140 or text.endswith((".", ";", ",")):
            return False
        letters = [char for char in text if char.isalpha()]
        return len(letters) >= 4 and (text.isupper() or text.istitle())
