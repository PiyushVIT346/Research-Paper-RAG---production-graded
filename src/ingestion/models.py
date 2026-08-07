"""
Plain dataclasses for parsed paper content, kept separate from
`docling_parser.py` so modules like the chunker can be unit-tested
without requiring the (heavy) `docling` dependency to be installed.
"""
from dataclasses import dataclass, field
from typing import List


@dataclass
class Section:
    heading: str
    level: int
    text: str


@dataclass
class Table:
    caption: str
    markdown: str


@dataclass
class Figure:
    caption: str


@dataclass
class ParsedPaper:
    arxiv_id: str
    full_text: str
    sections: List[Section] = field(default_factory=list)
    tables: List[Table] = field(default_factory=list)
    figures: List[Figure] = field(default_factory=list)
