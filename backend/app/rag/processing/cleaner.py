"""Conservative text cleanup for Vietnamese administrative documents."""

from __future__ import annotations

import re
import unicodedata
from collections import Counter, defaultdict

from app.rag.models import BlockType, DocumentBlock, ParsedDocument, ParserWarning

_PAGE_NUMBER = re.compile(
    r"^\s*(?:[-–—]\s*)?(?:trang\s+)?\d{1,4}(?:\s*/\s*\d{1,4})?(?:\s*[-–—])?\s*$", re.I
)
_LEGAL_LINE = re.compile(
    r"^\s*(?:Phần|Chương|Mục|Điều|Khoản|Điểm)\s+[\wÀ-ỹ.-]+|^\s*\d+[.)]\s+|^\s*[a-zđ][.)]\s+",
    re.I,
)
_DOCUMENT_NUMBER = re.compile(r"\b(?:Số|Số hiệu)\s*:\s*[\w./-]+", re.I)
_FIELD_NAME = re.compile(r"(?:\.{3,}|_{3,}|\[[^\]]+\]|\{[^}]+\})")
_SENTENCE_END = re.compile(r"[.!?:;…]\s*$")


class TextCleaner:
    """Normalize text while retaining legal and template semantics."""

    def clean(self, document: ParsedDocument) -> ParsedDocument:
        edge_repetitions = self._repeated_page_edges(document.blocks)
        cleaned_blocks: list[DocumentBlock] = []
        warnings = list(document.warnings)
        for block in document.blocks:
            if block.block_type == BlockType.PAGE_BREAK or block.table is not None:
                cleaned_blocks.append(block)
                continue
            normalized = self.clean_text(block.text)
            edge_key = self._comparison_key(normalized)
            if edge_key in edge_repetitions:
                warnings.append(
                    ParserWarning(
                        code="repeated_page_edge_removed",
                        message=f"Removed repeated header/footer: {normalized[:80]}",
                        page_number=block.page_number,
                        block_index=block.source_order,
                    )
                )
                continue
            if self._is_isolated_page_number(normalized):
                warnings.append(
                    ParserWarning(
                        code="isolated_page_number_removed",
                        message=f"Removed isolated page marker: {normalized}",
                        page_number=block.page_number,
                        block_index=block.source_order,
                    )
                )
                continue
            if normalized:
                cleaned_blocks.append(block.model_copy(update={"text": normalized}))
        reindexed = [
            block.model_copy(update={"source_order": index})
            for index, block in enumerate(cleaned_blocks)
        ]
        return document.model_copy(update={"blocks": reindexed, "warnings": warnings})

    def clean_text(self, text: str) -> str:
        text = unicodedata.normalize("NFC", text)
        text = text.replace("\u00a0", " ").replace("\u200b", "")
        text = re.sub(r"[ \t]+", " ", text)
        lines = [line.strip() for line in text.splitlines()]
        repaired: list[str] = []
        for line in lines:
            if not line:
                if repaired and repaired[-1]:
                    repaired.append("")
                continue
            if repaired and repaired[-1] and self._should_join(repaired[-1], line):
                if repaired[-1].endswith("-") and line[:1].islower():
                    repaired[-1] = repaired[-1][:-1] + line
                else:
                    repaired[-1] += " " + line
            else:
                repaired.append(line)
        return "\n".join(repaired).strip()

    def _should_join(self, previous: str, current: str) -> bool:
        if _LEGAL_LINE.match(current) or _LEGAL_LINE.match(previous):
            return False
        if _DOCUMENT_NUMBER.search(previous) or _FIELD_NAME.search(previous + current):
            return False
        if _SENTENCE_END.search(previous):
            return False
        if previous.isupper() or current.isupper():
            return False
        return current[:1].islower() or previous.endswith("-")

    def _repeated_page_edges(self, blocks: list[DocumentBlock]) -> set[str]:
        pages: dict[int, list[DocumentBlock]] = defaultdict(list)
        for block in blocks:
            if block.page_number is not None and block.block_type != BlockType.PAGE_BREAK:
                pages[block.page_number].append(block)
        if len(pages) < 2:
            return set()
        edge_occurrences: Counter[str] = Counter()
        for page_blocks in pages.values():
            candidates = page_blocks[:1] + page_blocks[-1:]
            for block in {item.block_id: item for item in candidates}.values():
                if block.table is None:
                    key = self._comparison_key(self.clean_text(block.text))
                    if key and len(key) <= 160 and not _DOCUMENT_NUMBER.search(key):
                        edge_occurrences[key] += 1
        threshold = max(2, (len(pages) + 1) // 2)
        return {text for text, count in edge_occurrences.items() if count >= threshold}

    @staticmethod
    def _comparison_key(text: str) -> str:
        return re.sub(r"\s+", " ", text).strip().casefold()

    @staticmethod
    def _is_isolated_page_number(text: str) -> bool:
        return bool(_PAGE_NUMBER.fullmatch(text))
